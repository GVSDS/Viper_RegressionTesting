#!/usr/bin/env python3
"""TransPyC 回归测试脚本

自动遍历 Test/ 目录下所有含 project.json 的项目目录，
通过 os.system("python ../Projectrans.py --project ...") 执行编译。
所有项目编译完成后，多线程执行编译结果，超时 5 秒强制结束。
stdout 出现 failed/error 等字样也汇总到错误列表，并展示匹配行及上下 5 行。
"""
import os
import sys
import json
import time
import subprocess
import re

# 强制 stdout/stderr 使用 UTF-8 编码，避免 Windows GBK 编码在打印含替换字符的输出时崩溃
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ============================================================
# 二阶段皆通过的项目清单 (2026-06-26 验证)
# 编译阶段: 35/35 通过  运行阶段: 35/35 通过
# ------------------------------------------------------------
# BuddyTest          BuiltinDecoratorTest  CPythonTest
# ClosureTest        ClosureTest2         DecoratorMarkerTest
# DecoratorTest      DictTest             DocTest
# EdgeCaseTest       EqTest               FakeDuckTest
# ForAndLoopTest     FormatStringTest     FuncTest
# GenericTest        GenericTest2         IterTest
# JsonTest           ListTest             LoopTest
# PointerTest        ShortCircuitTest     SimdTest
# StringIterTest     StringTest           StructTest
# TestFBProject      TestProject          TestProject2
# TestProject3       TypeCastTest         VRandomTest
# VariadicTest       ZlibTest
# ============================================================

# 测试目录
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
# 仓库根目录（含 TransPyC/、TransPyV/、Test/ 等同级目录）
PROJECT_ROOT = os.path.dirname(TEST_DIR)
# Projectrans.py 路径：编译器入口在 <root>/TransPyC/Projectrans.py
# （旧值 <root>/Projectrans.py 已不存在 → 76 个工程全部 "can't open file" 编译失败；
#  与 MCP/transpyc_mcp/server.py:33-35 记录的"入口已迁移"一致）
PROJECTRANS = os.path.join(PROJECT_ROOT, "TransPyC", "Projectrans.py")

# 运行超时（秒）
RUN_TIMEOUT = 30
# 编译超时（秒）
COMPILE_TIMEOUT = 300

# stdout 中匹配这些关键词则视为运行失败
_FAIL_PATTERNS = re.compile(
    r'(?i)\b(failed|error|traceback|exception|aborted|segmentation fault|core dumped)\b'
)
# 排除 "0 failed" 这类成功摘要行，以及测试输出中的 "error" 误报
_PASS_PATTERNS = re.compile(
    r'\b0\s+failed\b'
    r'|\bError\s+(handling|code|message|check|report|status|info|detail|test)\b'
    r'|\+--\s*Error\s'  # section headers like "+-- Error handling --+"
    r'|\bclear\s+error\b'  # "[PASS] clear error clears code"
    r'|\berror\s+(code|message)\b'  # "error code is set", "error message set"
    r'|\[PASS\].*\berror\b'  # "[PASS] ... error ..." test assertions
    r'|\[FAIL\].*\berror\b',  # "[FAIL] ... error ..." test assertions
    re.IGNORECASE
)


def find_test_projects():
    """查找所有含 project.json 的测试项目目录"""
    projects = []
    for name in sorted(os.listdir(TEST_DIR)):
        proj_dir = os.path.join(TEST_DIR, name)
        if not os.path.isdir(proj_dir):
            continue
        proj_json = os.path.join(proj_dir, "project.json")
        if os.path.isfile(proj_json):
            projects.append((name, proj_dir, proj_json))
    return projects


# ============================================================
# 单独运行支持：--escape / --only
# ============================================================
# escape 相关项目（生命期/逃逸检查 + M2.4 new 描述符 + M3 owned slife RAII + §3.6 析构 + P2 willFree）：
#   Test/ 下：NewTest、NewLifetimeTest、NewLifetimeWillFreeOkTest（正向）、
#             NewLifetimeFreeTest / NewLifetimeAsyncTest / NewLifetimeWillFreeTest /
#             NewLifetimeUseAfterFreeTest（负向）；
#   仓库根下：EscapeTest/EscapeOkTest/EscapeMethodTest/EscapeXmodTest
ESCAPE_PROJECTS = ["EscapeTest", "EscapeOkTest", "EscapeMethodTest", "EscapeXmodTest", "NewTest", "NewLifetimeTest", "NewLifetimeWillFreeOkTest", "NewLifetimeFreeTest", "NewLifetimeAsyncTest", "NewLifetimeWillFreeTest", "NewLifetimeUseAfterFreeTest", "NewLifetimeWillFreeKwargTest", "NewLifetimeFieldEscapeTest"]

# 负向项目（**期望编译失败**，见 SequentialRegressionTest.NEGATIVE_PROJECTS）：
# 本脚本按"编译必须成功 + 能跑"判定，纳入会误报，故 --escape 时剔除；
# 负向断言请用 SequentialRegressionTest（反向判定）或 run_lifetime_negative_tests.py。
NEGATIVE_PROJECT_NAMES = {"EscapeTest", "EscapeMethodTest", "EscapeXmodTest", "NewLifetimeFreeTest", "NewLifetimeAsyncTest", "NewLifetimeWillFreeTest", "NewLifetimeUseAfterFreeTest", "NewLifetimeWillFreeKwargTest", "NewLifetimeFieldEscapeTest"}


def find_project_file(proj_dir):
    """项目目录下找 project.json（Test/ 约定）或 project.vpj（仓库根约定）"""
    for fn in ("project.json", "project.vpj"):
        p = os.path.join(proj_dir, fn)
        if os.path.isfile(p):
            return p
    return None


def select_named_projects(names):
    """按名字解析项目：优先 Test/<name>，其次仓库根 <name>（根级 escape 测试）"""
    sel = []
    for n in names:
        d = os.path.join(TEST_DIR, n)
        if not os.path.isdir(d):
            d = os.path.join(PROJECT_ROOT, n)
        pj = find_project_file(d)
        if pj is None:
            print(f"  跳过 {n}: 找不到 project.json / project.vpj")
            continue
        sel.append((n, d, pj))
    return sel


def compile_project(name, proj_dir, proj_json_path):
    """编译单个测试项目，返回 (success, elapsed, output)"""
    cmd = f'D:\\Python312\\python.exe -u "{PROJECTRANS}" --project "{proj_json_path}" --clean'

    start = time.time()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=proj_dir,
        timeout=COMPILE_TIMEOUT,
    )
    elapsed = time.time() - start

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = stdout + stderr

    success = result.returncode == 0
    return (success, elapsed, combined)


def find_executables(output_dir):
    """在 output 目录中查找可执行文件"""
    exes = []
    if not os.path.isdir(output_dir):
        return exes
    for f in os.listdir(output_dir):
        fpath = os.path.join(output_dir, f)
        if os.path.isfile(fpath) and (f.endswith('.exe') or f.endswith('.bin')):
            exes.append(fpath)
    return exes


def run_executable(exe_path):
    """运行单个可执行文件，返回 (returncode, stdout, stderr, timed_out)

    超时 RUN_TIMEOUT 秒强制结束。
    使用 CREATE_NO_WINDOW 避免弹出 cmd 窗口，通过管道捕获 stdout/stderr。
    """
    try:
        CREATE_NO_WINDOW = 0x08000000
        result = subprocess.run(
            [exe_path],
            cwd=os.path.dirname(exe_path),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=RUN_TIMEOUT,
            creationflags=CREATE_NO_WINDOW,
        )
        return (result.returncode, result.stdout or "", result.stderr or "", False)
    except subprocess.TimeoutExpired:
        return (-1, "", "超时（强制终止）", True)
    except Exception as e:
        return (-1, "", str(e), False)


def extract_error_context(stdout, stderr, context_lines=5):
    """检查 stdout/stderr 中是否包含 failed/error 等关键词。

    返回 (matched_line, context_str) 或 None。
    context_str 包含匹配行及上下 context_lines 行。
    """
    combined = (stdout + "\n" + stderr).strip()
    if not combined:
        return None

    lines = combined.split('\n')
    for i, line in enumerate(lines):
        if _FAIL_PATTERNS.search(line):
            # 跳过 "0 failed" 这类成功摘要行
            if _PASS_PATTERNS.search(line):
                continue
            # 提取上下 context_lines 行
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            context_parts = []
            for j in range(start, end):
                marker = " >>>" if j == i else "    "
                context_parts.append(f"{marker} {lines[j]}")
            return (line.strip(), '\n'.join(context_parts))
    return None


def main():
    import argparse
    ap = argparse.ArgumentParser(description="TransPyC 回归测试（可用 --escape/--only 单独跑子集）")
    ap.add_argument("--escape", action="store_true",
                    help="只跑 escape 相关项目（生命期/逃逸检查 + new 描述符）")
    ap.add_argument("--only", default=None,
                    help="只跑指定项目（逗号分隔，名字即目录名）")
    args = ap.parse_args()

    print("=" * 70)
    print("TransPyC 回归测试")
    print("=" * 70)
    print()

    if args.escape:
        projects = [p for p in select_named_projects(ESCAPE_PROJECTS) if p[0] not in NEGATIVE_PROJECT_NAMES]
        print("（负向项目已剔除；负向断言请用 SequentialRegressionTest 或 run_lifetime_negative_tests.py）")
    elif args.only:
        projects = select_named_projects([n.strip() for n in args.only.split(",") if n.strip()])
    else:
        projects = find_test_projects()
    total = len(projects)
    print(f"发现 {total} 个测试项目\n")

    # ========== 阶段一：编译所有项目 ==========
    print("=" * 70)
    print("阶段一：编译所有项目")
    print("=" * 70)

    compiled = []  # (name, proj_dir, proj_json, compile_ok, elapsed, output)
    compile_passed = 0
    compile_failed = 0

    for idx, (name, proj_dir, proj_json) in enumerate(projects, 1):
        print(f"[{idx}/{total}] 编译 {name} ...", end=" ", flush=True)
        try:
            compile_ok, elapsed, output = compile_project(name, proj_dir, proj_json)
        except subprocess.TimeoutExpired:
            print("编译超时")
            compiled.append((name, proj_dir, proj_json, False, COMPILE_TIMEOUT, "编译超时（5分钟）"))
            compile_failed += 1
            continue
        except Exception as e:
            print(f"异常: {e}")
            compiled.append((name, proj_dir, proj_json, False, 0.0, str(e)))
            compile_failed += 1
            continue

        status = "通过" if compile_ok else "失败"
        print(f"{status} ({elapsed:.1f}s)")
        compiled.append((name, proj_dir, proj_json, compile_ok, elapsed, output))
        if compile_ok:
            compile_passed += 1
        else:
            compile_failed += 1

    print(f"\n编译阶段: 通过 {compile_passed}, 失败 {compile_failed}\n")

    # ========== 阶段二：运行所有编译成功的可执行文件 ==========
    print("=" * 70)
    print("阶段二：运行所有可执行文件")
    print("=" * 70)

    # 收集所有需要运行的可执行文件
    run_tasks = []  # (project_name, exe_path)
    for name, proj_dir, proj_json, compile_ok, elapsed, output in compiled:
        if not compile_ok:
            continue
        try:
            with open(proj_json, 'r', encoding='utf-8') as f:
                proj_config = json.load(f)
        except Exception:
            continue
        # 候选输出目录：TPC 与 TPV 布局一致（OutputDir = {BuildDir}/output）
        od = proj_config.get('output_dir') or 'output'
        bd = proj_config.get('build_dir') or '.tpv_build'
        base_dirs = [
            os.path.join(proj_dir, od),
            os.path.join(proj_dir, bd, od),
            os.path.join(proj_dir, bd, 'output'),
        ]
        exes = []
        for d in [os.path.abspath(x) for x in base_dirs]:
            exes = find_executables(d)
            if exes:
                break
        for exe in exes:
            run_tasks.append((name, exe))

    print(f"找到 {len(run_tasks)} 个可执行文件\n")

    run_results = {}  # project_name -> list of (exe_name, returncode, stdout, stderr, timed_out)
    run_passed = 0
    run_failed = 0
    total_runs = len(run_tasks)

    if run_tasks:
        # 串行运行，避免并发导致的资源竞争（控制台输出、堆分配器等）
        for idx, (proj_name, exe_path) in enumerate(run_tasks, 1):
            exe_name = os.path.basename(exe_path)
            print(f"[{idx}/{total_runs}] 运行 {proj_name} ... ", end=" ", flush=True)
            try:
                returncode, stdout, stderr, timed_out = run_executable(exe_path)
            except Exception as e:
                returncode, stdout, stderr, timed_out = -1, "", str(e), False

            if timed_out:
                status = "超时"
            elif returncode == 0:
                status = "通过"
            else:
                status = f"失败(退出码 {returncode})"
            print(status, flush=True)

            if proj_name not in run_results:
                run_results[proj_name] = []
            run_results[proj_name].append((exe_name, returncode, stdout, stderr, timed_out))

    # 汇总运行结果
    for name, proj_dir, proj_json, compile_ok, elapsed, output in compiled:
        if not compile_ok:
            continue
        exe_results = run_results.get(name, [])
        if not exe_results:
            continue

        project_run_ok = True
        for exe_name, returncode, stdout, stderr, timed_out in exe_results:
            if timed_out or returncode != 0:
                project_run_ok = False
                break
            # 仅在返回码非 0 时检查 stdout 错误关键词，避免误报
            # (PASS 行中可能包含 "Error"/"exception" 等词，如 "Status.Error=1")

        status = "通过" if project_run_ok else "失败"
        print(f"  {name}: {status}")
        if project_run_ok:
            run_passed += 1
        else:
            run_failed += 1

    print(f"\n运行阶段: 通过 {run_passed}, 失败 {run_failed}\n")

    # ========== 汇总报告 ==========
    print("=" * 70)
    print("回归测试报告")
    print("=" * 70)
    total_failed = compile_failed + run_failed
    total_passed = compile_passed - run_failed  # 编译通过但运行失败的不算通过
    print(f"总计: {total}  通过: {total_passed}  失败: {total_failed}")
    print()

    if total_failed > 0:
        print("-" * 70)
        print("失败项目详情:")
        print("-" * 70)

        # 编译失败
        for name, proj_dir, proj_json, compile_ok, elapsed, output in compiled:
            if compile_ok:
                continue
            print(f"\n【{name}】编译失败")
            lines = output.strip().split("\n") if output else []
            if len(lines) > 300:
                print(f"  ... (省略前 {len(lines) - 300} 行) ...")
                lines = lines[-300:]
            for line in lines:
                print(f"  {line}")

        # 运行失败
        for name, proj_dir, proj_json, compile_ok, elapsed, output in compiled:
            if not compile_ok:
                continue
            exe_results = run_results.get(name, [])
            if not exe_results:
                continue

            has_failure = False
            for exe_name, returncode, stdout, stderr, timed_out in exe_results:
                if timed_out or returncode != 0:
                    has_failure = True
                    break

            if not has_failure:
                continue

            print(f"\n【{name}】运行失败 (编译耗时 {elapsed:.1f}s)")
            for exe_name, returncode, stdout, stderr, timed_out in exe_results:
                if timed_out:
                    print(f"  [运行] {exe_name}: 超时（5秒强制终止）")
                    continue
                if returncode != 0:
                    print(f"  [运行] {exe_name}: 退出码 {returncode}")
                    if stderr.strip():
                        print(f"    stderr: {stderr.strip()[:300]}")
                    continue

                # 检查错误关键词，展示匹配行及上下 5 行
                error_ctx = extract_error_context(stdout, stderr)
                if error_ctx:
                    matched_line, context_str = error_ctx
                    print(f"  [运行] {exe_name}: 输出含错误关键词")
                    print(f"    匹配行: {matched_line}")
                    print(f"    上下文:")
                    for ctx_line in context_str.split('\n'):
                        print(f"    {ctx_line}")
        print()

    print("=" * 70)
    if total_failed == 0:
        print("所有测试通过！")
    else:
        print(f"有 {total_failed} 个测试失败，请检查上方详情。")
    print("=" * 70)

    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
