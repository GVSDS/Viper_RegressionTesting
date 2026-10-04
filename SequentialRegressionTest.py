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
        return f'"{args.exe}" --project {{project}} --clean{suffix}'
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
    """收集候选输出目录（兼容 TPC 与 TPV 布局）

    - {output_dir}（默认 output，TPC/旧布局）
    - {build_dir}/{output_dir}（build_dir 默认 .tpv_build）
    - {build_dir}/output（TPV 布局：.tpv_build/output）
    - 以上各项的 *_mlir 变体（单端 MLIR 布局：OutputDir = {BuildDir}/output_mlir，
      见 TransPyV/App/lib/Projectrans/Config.vp 的 mlir_dir_suffix()）
    保序去重返回。

    注意：ZlibDbg 等项目的 project.json 既无 output_dir 也无 build_dir，
    此时必须仍把 .tpv_build/output 纳入候选，否则 TPV 编译成功的 exe
    定位不到（报"无可执行二进制文件"）。
    单端 MLIR 后 exe 落在 {BuildDir}/output_mlir（非 output），且旧 LLVM 布局
    的 output/ 可能残留同名旧 exe，故 *_mlir 变体**优先**探测。
    """
    od = proj_config.get('output_dir') or 'output'
    bd = proj_config.get('build_dir') or '.tpv_build'
    # 单端 MLIR 目录后缀（与 Config.mlir_dir_suffix() 同口径，当前恒为 "_mlir"）
    mlir_suf = '_mlir'
    base = [
        os.path.abspath(os.path.join(proj_dir, od)),
        os.path.abspath(os.path.join(proj_dir, bd, od)),
        os.path.abspath(os.path.join(proj_dir, bd, 'output')),
    ]
    dirs = [d + mlir_suf for d in base] + base
    seen = set()
    uniq = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


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
    args = parser.parse_args()
    compile_cmd = build_compile_cmd(args)

    print("=" * 70)
    print("TransPyC 顺序回归测试（按 README.md 顺序，失败即停）")
    print("=" * 70)
    print()

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
        proj_dir = os.path.join(TEST_DIR, name)
        proj_json = os.path.join(proj_dir, "project.json")

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
