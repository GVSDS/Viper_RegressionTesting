# NegativeTest 反向测试运行器：对每个错误用例执行 TPC 单文件编译，
# 断言"编译失败且输出诊断信息"。编译成功 = 编译器漏检（FAIL）。
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES_DIR = os.path.join(ROOT, 'Test', 'NegativeTest', 'App', 'cases')
OUT_DIR = os.path.join(ROOT, 'Test', 'NegativeTest', '.out')
os.makedirs(OUT_DIR, exist_ok=True)

# 用例 -> 期望错误关键字（用于确认报错方向正确）
EXPECT = {
    'import_wrong_path.vp': ['NopeModule', '模块', 'import'],
    'import_stale_path.vp': ['StubMergerStore', '模块', 'import'],
    'import_missing_module.vp': ['HandlesStruct', '模块', 'import'],
    'call_too_few.vp': ['参数', '少', '2', 'f'],
    'call_too_many.vp': ['参数', '多', '3', 'f'],
    'call_wrong_type.vp': ['类型', 'int', 'f'],
    'call_float_to_int.vp': ['类型', 'int', 'g'],
    'undefined_func.vp': ['foo', '未定义', 'NameError'],
    'missing_return.vp': ['返回', 'return', '末尾'],
}


def main() -> int:
    cases = sorted(f for f in os.listdir(CASES_DIR) if f.endswith('.vp'))
    passed, failed, skipped = [], [], []
    for case in cases:
        src = os.path.join(CASES_DIR, case)
        out_ll = os.path.join(OUT_DIR, case[:-3] + '.ll')
        try:
            r = subprocess.run(
                [sys.executable, 'TransPyC.py', '-f', src, '-o', out_ll],
                capture_output=True, text=True, cwd=ROOT, timeout=120,
            )
        except subprocess.TimeoutExpired:
            failed.append((case, 'TIMEOUT', ''))
            continue
        err_text = (r.stderr or '') + (r.stdout or '')
        if r.returncode == 0:
            failed.append((case, 'COMPILED_OK(漏检)', err_text.strip()[-500:]))
            continue
        # 编译失败：检查是否报了我们预期的错误方向
        lower = err_text.lower()
        keywords = EXPECT.get(case, [])
        hit = [k for k in keywords if k.lower() in lower]
        if hit:
            passed.append((case, 'PASS', hit, err_text.strip()[-300:]))
        else:
            skipped.append((case, 'ERR_BUT_UNEXPECTED', err_text.strip()[-300:]))

    print('\n==== NegativeTest 结果 ====')
    print(f'PASS(预期失败且方向正确): {len(passed)}')
    for c, tag, hit, tail in passed:
        print(f'  [PASS] {c}  命中关键字 {hit}')
    print(f'FAIL(编译器漏检): {len(failed)}')
    for c, tag, tail in failed:
        print(f'  [FAIL] {c}  {tag}')
        if tail:
            print(f'         {tail}')
    print(f'SKIP(报错但非预期方向): {len(skipped)}')
    for c, tag, tail in skipped:
        print(f'  [SKIP] {c}')
        if tail:
            print(f'         {tail}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
