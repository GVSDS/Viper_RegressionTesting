#!/usr/bin/env python3
"""TransPyC 顺序回归测试脚本

与 regression_test.py 的区别：
1. 按 Test/README.md「建议实现顺序」节（难度升序，68 个项目）逐个编译
2. 每个项目编译成功后立即运行其可执行文件
3. 编译或运行失败立刻结束（fail-fast），退出码非 0
"""
import os
import sys
import json
import time
import re
import subprocess
import argparse

# 强制 stdout/stderr 使用 UTF-8 编码，避免 Windows GBK 编码在打印含替换字符的输出时崩溃
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ============================================================
# 路径
# ============================================================
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根目录（含 TransPyC/、TransPyV/、Test/ 等同级目录）
PROJECT_ROOT = os.path.dirname(TEST_DIR)
# Projectrans.py 路径：编译器入口在 <root>/TransPyC/Projectrans.py
# （旧值 <root>/Projectrans.py 已不存在，与 regression_test.py:45-48 同一条记录）
PROJECTRANS = os.path.join(PROJECT_ROOT, "TransPyC", "Projectrans.py")
# README.md 路径（顺序来源，原 TestsOverview.md）
OVERVIEW = os.path.join(TEST_DIR, "README.md")

# ============================================================
# 单独运行支持：--escape / --only
# ============================================================
# escape 相关项目（生命期/逃逸检查 + M2.4 new 描述符 + M3 owned slife RAII + §3.6 析构）：
#   Test/ 下：NewTest、NewLifetimeTest（正向）、NewLifetimeFreeTest / NewLifetimeAsyncTest（负向）；
#   仓库根下：EscapeTest/EscapeOkTest/EscapeMethodTest/EscapeXmodTest
ESCAPE_PROJECTS = ["EscapeTest", "EscapeOkTest", "EscapeMethodTest", "EscapeXmodTest", "NewTest", "NewLifetimeTest", "NewLifetimeFreeTest", "NewLifetimeAsyncTest"]

# 负向项目：**期望编译失败**且输出含指定关键字（反向判定，且不运行可执行文件）。
# 这些项目里的用例故意交出本帧栈地址（或跨模块摘要路径），必须被 M1–M2.3 的
# 逃逸检查拒绝；编译成功 = 编译器漏检（判 FAIL 并终止）。
#   注：EscapeMethodTest / EscapeXmodTest 内含多条互斥用例（编译在第一个错误处终止），
#   故只保证"至少触发一条"。
NEGATIVE_PROJECTS = {
    "EscapeTest": "LifetimeError",
    "EscapeMethodTest": "LifetimeError",
    "EscapeXmodTest": "LifetimeError",
    # M3 §4.3 判据5：对 slife 对象手动 free → LifetimeError
    "NewLifetimeFreeTest": "LifetimeError",
    # M3 §4.2：协程体（async）里的 `new heap slife` → 释放点无法确定，fail-fast
    "NewLifetimeAsyncTest": "LifetimeError",
}

# IR 断言：项目名 → 生成 IR 中**必须出现**的子串。
# 动机：M3 owned slife 的"出口释放"只靠"运行不崩"是证明不了的（漏了释放 = 纯泄漏，
# 进程照样退出码 0），必须直接断言生成的 IR 里出现了释放调用。
# 形式注意：`{build_dir}/temp/**.ll` 里是 **LLVM dialect 文本**（mlir-opt 的输入），
# 调用长这样 `llvm.call @free(%9) : (!llvm.ptr) -> ()`，不是经典 IR 的 `call void @free`；
# 用 `llvm.call @free` 才能匹配到调用（`llvm.func @free` 是声明那一行，不会被匹配）。
# 约定：纳入 IR 断言的项目**不得**自己写 free，否则用户代码的 free 会把断言蒙混过关
# （NewLifetimeTest 正是因此不含任何用户级 free）。
IR_EXPECT = {
    "NewLifetimeTest": ["llvm.call @free"],
}


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

# 编译超时（秒）
COMPILE_TIMEOUT = 300
# 运行超时（秒）
RUN_TIMEOUT = 30


def read_test_order():
    """从 README.md「建议实现顺序」节提取项目名（难度升序）"""
    with open(OVERVIEW, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'##\s*二、\s*建议实现顺序(.*?)##\s*三、', text, re.S)
    if not m:
        raise SystemExit("README.md 中找不到「建议实现顺序」节")
    section = m.group(1)
    order = []
    for line in section.splitlines():
        mm = re.match(r'\s*\d+\.\s*\*\*(.+?)\*\*', line)
        if mm:
            order.append(mm.group(1))
    if not order:
        raise SystemExit("「建议实现顺序」节中未解析到任何项目名")
    return order


def build_compile_cmd(args):
    """根据 --exe/--compiler 构建编译命令模板（{project} 为项目 json 路径占位）

    --exe 指定编译器可执行文件（如 TransPyV.exe），优先于 --compiler；
    两者都未指定时使用 TPC（python Projectrans.py）。
    --rebuild-includes 时追加 --rebuild-includes（全量重编 includes，
    修复 includes.binary 缓存不一致导致的 undefined symbol）。
    """
    suffix = " --rebuild-includes" if args.rebuild_includes else ""
    if args.exe:
        # 必须绝对化：每个项目都在自己的目录里执行（cwd=项目目录），相对 --exe 会按各自
        # 层级解析到不同位置——根级 escape 项目只深一层能命中，Test/NewTest 深两层就报
        # "The system cannot find the path specified."（实测踩过）。
        exe_abs = os.path.abspath(args.exe)
        return f'"{exe_abs}" --project {{project}} --clean{suffix}'
    if args.compiler:
        return args.compiler
    return f'D:\\Python312\\python.exe -u "{PROJECTRANS}" --project {{project}} --clean{suffix}'


def compile_project(cmd, proj_dir):
    """编译单个测试项目，返回 (success, elapsed, combined_output)"""
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

    combined = (result.stdout or "") + (result.stderr or "")
    return (result.returncode == 0, elapsed, combined)


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


def find_output_dirs(proj_dir, proj_config):
    """收集候选输出目录（TPC 与 TPV 布局一致：{build_dir}/output）

    - {output_dir}（默认 output）
    - {build_dir}/{output_dir}（build_dir 默认 .tpv_build）
    - {build_dir}/output
    保序去重返回。

    注意：ZlibDbg 等项目的 project.json 既无 output_dir 也无 build_dir，
    此时必须仍把 .tpv_build/output 纳入候选，否则 TPV 编译成功的 exe
    定位不到（报"无可执行二进制文件"）。
    """
    od = proj_config.get('output_dir') or 'output'
    bd = proj_config.get('build_dir') or '.tpv_build'
    dirs = [
        os.path.abspath(os.path.join(proj_dir, od)),
        os.path.abspath(os.path.join(proj_dir, bd, od)),
        os.path.abspath(os.path.join(proj_dir, bd, 'output')),
    ]
    seen = set()
    uniq = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def find_ll_files(proj_dir, proj_config):
    """收集项目构建目录下的所有 .ll（TPV 布局：{build_dir}/temp/<xx>/<sha1>.ll）"""
    bd = proj_config.get('build_dir') or '.tpv_build'
    root = os.path.abspath(os.path.join(proj_dir, bd))
    if not os.path.isdir(root):
        return []
    out = []
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if fn.endswith('.ll'):
                out.append(os.path.join(dp, fn))
    return out


def check_ir_expect(proj_dir, proj_config, name):
    """IR 断言：在生成的 .ll 里检查 IR_EXPECT[name] 的每个子串都出现。

    返回 (ok, 说明)。未配置 IR_EXPECT 的项目恒 (True, "")。
    找不到任何 .ll 视为**失败**（fail-fast：静默跳过等于没断言）。
    """
    wants = IR_EXPECT.get(name)
    if not wants:
        return True, ""
    lls = find_ll_files(proj_dir, proj_config)
    if not lls:
        return False, f"IR 断言失败：{name} 的构建目录下找不到任何 .ll（检查 build_dir 配置）"
    text = ""
    for p in lls:
        try:
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                text += f.read()
        except Exception as e:
            return False, f"IR 断言失败：读取 {p} 出错: {e}"
    missing = [w for w in wants if w not in text]
    if missing:
        return False, f"IR 断言失败：{name} 生成的 .ll 中未见 {missing}（共 {len(lls)} 个 .ll）"
    return True, f"IR 断言通过（{len(wants)} 项 / {len(lls)} 个 .ll）"


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


def print_tail(output, max_lines=40):
    """打印输出尾部（编译/运行失败时的诊断信息）"""
    lines = output.strip().splitlines()
    if len(lines) > max_lines:
        print(f"  ... (省略前 {len(lines) - max_lines} 行) ...")
        lines = lines[-max_lines:]
    for line in lines:
        print(f"  {line}")


def main():
    parser = argparse.ArgumentParser(
        description="TransPyC 顺序回归测试（按 README.md 顺序，失败即停）")
    parser.add_argument("--exe", default=None,
                        help="编译器可执行文件（如 TransPyV.exe），用它编译测试项目（替代 TPC）")
    parser.add_argument("--compiler", default=None,
                        help="自定义编译命令模板，用 {project} 表示项目 json 路径；默认 TPC python")
    parser.add_argument("--rebuild-includes", action="store_true",
                        help="每次编译追加 --rebuild-includes：清空 includes.binary 全量重编（修复缓存不一致）")
    parser.add_argument("--number", type=int, default=1,
                        help="从第几个案例开始（1 开始编号），编译该编号及之后的项目；默认 1")
    parser.add_argument("--escape", action="store_true",
                        help="只跑 escape 相关项目（生命期/逃逸检查 + new 描述符），忽略 README 顺序")
    parser.add_argument("--only", default=None,
                        help="只跑指定项目（逗号分隔，名字即目录名），忽略 README 顺序")
    args = parser.parse_args()
    if args.exe and not os.path.isfile(os.path.abspath(args.exe)):
        print(f"错误: --exe 不存在: {os.path.abspath(args.exe)}")
        return 1
    compile_cmd = build_compile_cmd(args)

    print("=" * 70)
    print("TransPyC 顺序回归测试（按 README.md 顺序，失败即停）")
    print("=" * 70)
    print()

    if args.escape:
        order = [n for (n, d, pj) in select_named_projects(ESCAPE_PROJECTS)]
        args.number = 1
    elif args.only:
        order = [n for (n, d, pj) in select_named_projects([x.strip() for x in args.only.split(",") if x.strip()])]
        args.number = 1
    else:
        order = read_test_order()
    total = len(order)

    start = max(1, args.number)
    if start > total:
        print(f"错误: --number {args.number} 超出总项目数 {total}")
        return 1
    print(f"按顺序共 {total} 个项目，从第 {start} 个（{order[start - 1]}）开始")
    print(f"编译命令: {compile_cmd}\n")

    passed = 0
    for idx, name in enumerate(order, 1):
        if idx < start:
            continue
        # 项目目录：优先 Test/<name>，其次仓库根 <name>（根级 escape 项目）
        proj_dir = os.path.join(TEST_DIR, name)
        if not os.path.isdir(proj_dir): proj_dir = os.path.join(PROJECT_ROOT, name)
        proj_json = find_project_file(proj_dir)
        if proj_json is None:
            print(f"  [SKIP] {name}: 找不到 project.json / project.vpj")
            continue

        if not os.path.isfile(proj_json):
            print(f"[{idx}/{total}] {name}: 缺少 project.json，跳过")
            continue

        # ---------- 编译 ----------
        print(f"[{idx}/{total}] 编译 {name} ...", end=" ", flush=True)
        cmd = compile_cmd.format(project=proj_json)
        try:
            compile_ok, elapsed, output = compile_project(cmd, proj_dir)
        except subprocess.TimeoutExpired:
            print("编译超时（5 分钟）")
            print_tail("编译超时（5 分钟）")
            print(f"\n在 {name} 编译超时，立即终止。")
            return 1
        except Exception as e:
            print(f"异常: {e}")
            print_tail(str(e))
            print(f"\n在 {name} 编译异常，立即终止。")
            return 1

        # ---------- 负向项目：反向判定（期望失败），且不进入运行阶段 ----------
        if name in NEGATIVE_PROJECTS:
            want_kw: str = NEGATIVE_PROJECTS[name]
            if compile_ok:
                print(f"漏检 ({elapsed:.1f}s)：负向项目竟编译成功，应报 {want_kw}")
                print_tail(output)
                print(f"\n在 {name} 漏检（应拒绝却通过），立即终止。")
                return 1
            if want_kw.lower() in output.lower():
                print(f"通过（已按预期拒绝: {want_kw}, {elapsed:.1f}s）")
                passed += 1
                continue
            print(f"失败（报错方向不符，未见 {want_kw}）")
            print_tail(output)
            print(f"\n在 {name} 报错方向不符，立即终止。")
            return 1

        if not compile_ok:
            print(f"失败 ({elapsed:.1f}s)")
            print_tail(output)
            print(f"\n在 {name} 编译失败，立即终止。")
            return 1
        print(f"通过 ({elapsed:.1f}s)")

        # ---------- 编译成功后立即运行 ----------
        # project.json 解析失败必须**立刻终止并报错**：静默退化成 {} 会让下面拿不到
        # build_dir（TPV 布局 .tpv_build/output），只在 <项目>/output 里找可执行文件，
        # 于是明明编译成功却被判成"未找到可执行文件"。实测踩过：LLvmLiteTest 的
        # project.json 有一个尾逗号（第 18 行 `],`）——标准 JSON 非法（TPV 自带解析器
        # 宽容才编得过），此处不再吞异常。
        try:
            with open(proj_json, 'r', encoding='utf-8') as f:
                proj_config = json.load(f)
        except Exception as e:
            print(f"  [运行] project.json 解析失败: {e}")
            print(f"\n在 {name} 读取 project.json 失败，立即终止（请修正该文件后重跑）。")
            return 1

        # ---------- IR 断言（可选，见 IR_EXPECT） ----------
        ir_ok, ir_msg = check_ir_expect(proj_dir, proj_config, name)
        if not ir_ok:
            print(f"  [IR] {ir_msg}")
            print(f"\n在 {name} IR 断言失败，立即终止。")
            return 1
        if ir_msg:
            print(f"  [IR] {ir_msg}")

        output_dirs = find_output_dirs(proj_dir, proj_config)
        exes = []
        for od in output_dirs:
            exes = find_executables(od)
            if exes:
                break

        if not exes:
            print(f"  [运行] 未找到可执行文件（候选: {'; '.join(output_dirs)}），视为运行失败")
            return 1

        run_ok = True
        for exe_path in exes:
            exe_name = os.path.basename(exe_path)
            print(f"  [运行] {exe_name} ...", end=" ", flush=True)
            returncode, stdout, stderr, timed_out = run_executable(exe_path)

            if timed_out:
                print("超时")
                print_tail(stdout + stderr)
                run_ok = False
            elif returncode == 0:
                print("通过")
            else:
                print(f"失败(退出码 {returncode})")
                print_tail(stdout + stderr)
                run_ok = False

            if not run_ok:
                break

        if not run_ok:
            print(f"\n在 {name} 运行失败，立即终止。")
            return 1

        passed += 1

    print()
    print("=" * 70)
    print(f"全部 {passed} 个项目编译并运行通过！")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
