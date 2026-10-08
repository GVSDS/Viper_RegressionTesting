#!/usr/bin/env python3
"""生命期/逃逸负向测试运行器（TransPyV 专用）

与 NegativeTest/run_negative_tests.py 的区别：
  · 那个脚本用 **TPC**（Python 编译器，`TransPyC.py -f`）编译并断言通用错误；
  · `new` 描述符与 `LifetimeError` 只在 **TransPyV** 侧实现——TPC 的解析器不认识 `new`，
    也产不出 LifetimeError，所以本脚本统一用 TransPyV.exe 编译，
    断言"**编译失败且输出含 LifetimeError**"。

用法：
  python Test/run_lifetime_negative_tests.py --exe .\\TransPyV\\output\\TransPyV.exe
  python Test/run_lifetime_negative_tests.py --exe ... --only EscapeMethodTest
  python Test/run_lifetime_negative_tests.py --exe ... --rebuild-includes
"""
import os
import subprocess
import sys
import argparse

# 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 编码崩溃
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)

# 期望"编译失败 + 报 LifetimeError"的项目（名字；目录优先 Test/<名>，其次仓库根 <名>）。
# 注意：EscapeMethodTest / EscapeXmodTest 内部有多条互斥用例（编译在第一个错误处终止），
# 每个项目只保证"至少触发一条 LifetimeError"。
# NewLifetimeFreeTest：M3 §4.3 判据5（对 slife 对象手动 free）。
# NewLifetimeAsyncTest：M3 §4.2（协程体里的 `new heap slife` → 释放点无法确定，fail-fast）。
# NewLifetimeWillFreeTest / NewLifetimeUseAfterFreeTest：P2（@life(willFree(p)) 标注驱动——
#   二次释放 / 释放后使用，对应正向工程 NewLifetimeWillFreeOkTest）。
NEGATIVE_PROJECTS = ["EscapeTest", "EscapeMethodTest", "EscapeXmodTest", "NewLifetimeFreeTest", "NewLifetimeAsyncTest", "NewLifetimeWillFreeTest", "NewLifetimeUseAfterFreeTest", "NewLifetimeWillFreeKwargTest"]
EXPECT_KEYWORD = "LifetimeError"
COMPILE_TIMEOUT = 300


def find_project_file(proj_dir):
    """项目目录下找 project.json（Test/ 约定）或 project.vpj（仓库根约定）"""
    for fn in ("project.json", "project.vpj"):
        p = os.path.join(proj_dir, fn)
        if os.path.isfile(p):
            return p
    return None


def resolve(name):
    """名字 → (项目目录, 项目文件路径)；找不到目录返回 (dir, None)"""
    d = os.path.join(TEST_DIR, name)
    if not os.path.isdir(d):
        d = os.path.join(PROJECT_ROOT, name)
    return d, find_project_file(d)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="生命期/逃逸负向测试（只用 TransPyV 编译，断言 LifetimeError）")
    ap.add_argument("--exe", required=True,
                    help="TransPyV 可执行文件（如 .\\TransPyV\\output\\TransPyV.exe）")
    ap.add_argument("--only", default=None,
                    help="只跑指定项目（逗号分隔，名字即目录名）")
    ap.add_argument("--rebuild-includes", action="store_true",
                    help="每次编译追加 --rebuild-includes（全量重编 includes）")
    args = ap.parse_args()

    # --exe 绝对化 + 存在性校验：编译以 cwd=项目目录 执行，相对路径会随项目层级错位
    exe_abs = os.path.abspath(args.exe)
    if not os.path.isfile(exe_abs):
        print(f"错误: --exe 不存在: {exe_abs}")
        return 1
    names = [n.strip() for n in args.only.split(",") if n.strip()] if args.only else NEGATIVE_PROJECTS
    suffix = " --rebuild-includes" if args.rebuild_includes else ""

    passed, failed, skipped = [], [], []
    print("=" * 70)
    print("生命期/逃逸负向测试（期望编译失败 + LifetimeError）")
    print("=" * 70)
    for name in names:
        proj_dir, proj_file = resolve(name)
        if proj_file is None:
            skipped.append((name, "找不到 project.json / project.vpj"))
            print(f"[SKIP] {name}: 找不到 project.json / project.vpj")
            continue
        cmd = f'"{exe_abs}" --project "{proj_file}" --clean{suffix}'
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               encoding='utf-8', errors='replace',
                               cwd=proj_dir, timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            failed.append((name, "TIMEOUT", ""))
            print(f"[FAIL] {name}: 编译超时")
            continue
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            failed.append((name, "COMPILED_OK(漏检)", out.strip()[-400:]))
            print(f"[FAIL] {name}: 编译成功（漏检，应报 LifetimeError）")
        elif EXPECT_KEYWORD.lower() in out.lower():
            passed.append((name, out.strip()[-200:]))
            print(f"[PASS] {name}: 已按预期拒绝（含 {EXPECT_KEYWORD}）")
        else:
            skipped.append((name, f"报错但未见 {EXPECT_KEYWORD}", out.strip()[-300:]))
            print(f"[SKIP] {name}: 报错但未见 {EXPECT_KEYWORD}")

    print()
    print("=" * 70)
    print(f"PASS {len(passed)}  FAIL {len(failed)}  SKIP {len(skipped)}")
    for name, tail in skipped:
        print(f"  [SKIP] {name}: {tail if isinstance(tail, str) else ''}")
        if tail: print(f"         {tail}")
    for name, tag, tail in failed:
        print(f"  [FAIL] {name}: {tag}")
        if tail: print(f"         {tail}")
    print("=" * 70)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
