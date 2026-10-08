# TPV 测试项目总览

本文档基于 `Test/` 目录下全部 77 个测试项目（原 68 个 + 2026-10 补录 9 个）的源码总结其功能，并**按实现难度升序**排列（简单在前、困难在后），供编译器开发按序推进。另有 `NegativeTest`（负向测试容器）不计入难度序列。

> 测试框架：几乎所有项目使用 `testcheck` 库（`begin`/`section`/`check`/`ok`/`end`）输出 PASS/FAIL 并汇总。多数项目还依赖 `memhub` 内存分配器与 `t.CInt`/`t.CExport` 等 C 互操作类型。

---

## 一、全部测试功能一览（按实现难度升序）

### 难度：简单（16 个）—— 基础语法、库 API 直接调用

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 1 | [FuncTest](FuncTest/App/main.vp) | 函数调用基准：多参数、递归阶乘、双递归斐波那契、指针参数、u64/bool 返回、嵌套调用 | 函数定义/调用、递归、指针参数 |
| 2 | [LoopTest](LoopTest/App/main.vp) | 循环基准：for/while/Collatz/嵌套 for/break/continue/带步长 range/u64 计数 | 循环、break/continue、range 步长 |
| 3 | [StringTest](StringTest/App/main.vp) | string 库：strlen/strcpy/strcat/strcmp/strncpy/下标取字符/snprintf | string 库、C 字符串指针 |
| 4 | [StructTest](StructTest/App/main.vp) | 结构体：字段读写、嵌套（`Rect.origin.x`）、取地址修改、传值参数、数组布局 | t.Struct、嵌套结构体、结构体指针/数组 |
| 5 | [EqTest](EqTest/App/main.vp) | 比较语义：str 的 `==` 是指针地址比较（值比较须 strcmp）、`is` 身份比较、与 None 比较 | 比较运算符、None、string.strcmp |
| 6 | [ShortCircuitTest](ShortCircuitTest/App/main.vp) | 短路求值：`and`/`or`/`not` 的求值顺序与副作用检测 | 短路语义、副作用函数 |
| 7 | [IterTest](IterTest/App/main.vp) | `for ch in str` 逐字符迭代：求和字符码、写入数组、手动 strcpy | for-in 指针迭代、联合类型 |
| 8 | [Extern2Test](Extern2Test/App/main.vp) | 回归：CExtern/CExport/State 声明函数只生成一次 declare 不重复 define | 外部声明修饰符、声明去重 |
| 9 | [SlotsBugTest](SlotsBugTest/App/main.vp) | 回归：`__slots__` + 可识别类型注解不再误判崩溃（以编译通过为准） | __slots__、类型注解解析 |
| 10 | [ListTest](ListTest/App/main.vp) | `list[int]` 容器：append/get/len/set/pop/clear/扩容/复用 | 泛型 list、特殊方法 |
| 11 | [MpoolOopTest](MpoolOopTest/App/main.vp) | MemPool（bump）/MemSlab（定长块）OOP 测试：alloc/reset/free 复用、viperio.Buf | memhub 库、with 上下文、句柄类型 |
| 12 | [DocTest](DocTest/App/main.vp) | `__doc__` 魔法字符串：本模块与跨模块函数/类/方法 docstring 读取 | docstring、__doc__ 属性 |
| 13 | [ForAndLoopTest](ForAndLoopTest/App/main.vp) | 迭代器组合：range/zip/enumerate 遍历 list/str/range，元组解包 | 内置迭代器、元组解包 |
| 14 | [VRandomTest](VRandomTest/App/main.vp) | vrandom 库：RDRAND 硬件随机数 + 10 种统计分布采样 | vrandom 库、硬件随机数 |
| 15 | [VariadicTest](VariadicTest/App/main.vp) | 变参 printf/snprintf：整数提升匹配 %u/%lu/%d/%x、边界值 | 变参 ABI、整数提升、格式串 |
| 16 | [ClosureCallTest](ClosureCallTest/App/main.vp) | 最小复现：闭包返回 `t.CPtr` 函数指针后直接 `f()` 调用 | 闭包、函数指针直接调用 |

### 难度：简单 → 中等（3 个）—— 泛型入门

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 17 | [GenericTest](GenericTest/App/main.vp) | 泛型基础：泛型函数/多类型参数/泛型类/多次特化/嵌套调用/CArray | 泛型函数与类、特化、t.CArray |
| 18 | [GenericTest3](GenericTest3/App/main.vp) | 泛型函数手动传类型参数 `double[t.CInt](21)` | 显式类型参数调用语法 |
| 19 | [GenericTest4](GenericTest4/App/main.vp) | 泛型类手动传类型参数 `Box[t.CInt](42)`（GenericTest3 的类版本） | 泛型类显式特化语法 |

### 难度：中等（21 个）—— 类型系统、容器、基础 OOP

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 20 | [TypeCastTest](TypeCastTest/App/main.vp) | 类型转换：zext/sext/trunc、C 语义运算（-100//7=-14）、CDefine、指针整数互转 | C 整数体系、C 语义运算规则 |
| 21 | [PointerTest](PointerTest/App/main.vp) | 指针操作：global 语义/指针算术/数组退化/CVoid↔CUInt32T/字节偏移/大小端 | 指针类型体系、global、大小端 |
| 22 | [LoopMathTest](LoopMathTest/App/main.vp) | while + 数学运算：四则/取模/位运算/复合赋值/三元/优先级/跨模块宏 | 运算全套、运算符优先级、宏引用 |
| 23 | [StringIterTest](StringIterTest/App/main.vp) | 指针迭代/算术、c.Deref/Set/Addr、多级指针、手动 strcpy；@t.Object 内联数组 | 指针算术、内联结构体数组 |
| 24 | [ExpandKeywordsTest](ExpandKeywordsTest/App/main.vp) | 软关键字 fn/fun/func/function 与 def 等价、PEP 695 泛型函数 | 软关键字解析、泛型函数 |
| 25 | [SprintfTest](SprintfTest/App/main.vp) | viperlib.snprintf：%a/%A 十六进制浮点与 glibc 对照、%g 精度 bug、多 int 变参 | 浮点格式化、变参 ABI |
| 26 | [FormatStringTest](FormatStringTest/App/main.vp) | f-string 格式说明符：0x/016X/d/.2f、str 指针算术、CArray[u64]、ctraits.isptr | f-string、格式说明符、编译期类型判断 |
| 27 | [ClassArrayTest](ClassArrayTest/App/main.vp) | 类与数组基础：数据类/三维点/带 __init__ 类/栈堆分配/各类数组/退化指针 | OOP、t.CArray、堆管理 |
| 28 | [BuiltinDecoratorTest](BuiltinDecoratorTest/App/main.vp) | 内置装饰器：@property/getter/setter/deleter、@staticmethod、@classmethod 及混用 | 装饰器全套访问器 |
| 29 | [OopInheritTest](OopInheritTest/App/main.vp) | OOP 继承多态：@t.CVTable 虚方法覆盖、链式调用、运算符重载、三层继承 | 虚分派、运算符重载、链式调用 |
| 30 | [MemhubTest](MemhubTest/App/main.vp) | MemManager 多态：基类指针虚分派 alloc/free、calloc 内部调虚函数 | 虚方法多态、继承体系 |
| 31 | [EnumTest](EnumTest/App/main.vp) | 枚举：CEnum 取值 + REnum 携带数据变体，match/case 解构字段 | CEnum、REnum、match 解构 |
| 32 | [DefineTest](DefineTest/App/main.vp) | 编译期宏：CDefine 常量/宏函数、`cif`/`celif`/`celse` 条件编译（`defined()` 谓词）、platmacro 平台宏 | 编译期宏、条件编译、平台探测 |
| 33 | [ClosureTest](ClosureTest/App/main.vp) | 闭包作用域：global/nonlocal 嵌套/lambda 捕获/循环变量/global 数组 | 闭包、nonlocal/global、lambda |
| 34 | [ClosureTest2](ClosureTest2/App/main.vp) | 闭包进阶：nonlocal 条件分支/多变量 swap/引用 vs 值捕获/三层嵌套/结构体修改 | 引用捕获语义、多层级 nonlocal |
| 35 | [G3](G3/App/main.vp) | GSListNode F-bounded 泛型继承：`class Node(GSListNode[Node])` 链遍历求和 | 递归泛型/自引用特化 |
| 36 | [G6](G6/App/main.vp) | atom 模块内联汇编原子操作：test_and_set/clear/fence/is_lock_free/spinlock | 内联汇编原子操作 |
| 37 | [VectorGenericTest](VectorGenericTest/App/main.vp) | 泛型容器 vector.Vector（MemPool 池化）：Vector[int]/Vector[double] | 泛型容器、内存池 |
| 38 | [DictTest](DictTest/App/main.vp) | dict 库：set/get/下标/len/contains/迭代/扩容/JSON dumps-loads/嵌套/get_vtype | dict 库、JSON、c.Deref |
| 39 | [HashLibTest](HashLibTest/App/main.vp) | hashlib md5/sha1/sha256/sha512、base64 往返、binascii 全套、默认参数函数 | 哈希/编码库、默认参数 |
| 40 | [ArgparseTest](ArgparseTest/App/main.vp) | argparse 库：手工 argv 解析、STORE/STORE_TRUE/COUNT 动作、--name=value、默认值 | argparse、内存布局 |

### 难度：较难（26 个）—— 泛型进阶、多继承、闭包难点、编译器自身库

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 41 | [GenericTest2](GenericTest2/App/main.vp) | 高级泛型：Stack[T]/Range[T]/Container[T]/泛型指针交换/__sizeof__ 特化语义 | 泛型+指针+sizeof 特化 |
| 42 | [G4](G4/App/main.vp) | includes 泛型继承（Phase1 stub 路径）+ 多模块（3 caller 交叉引用）链操作 | 泛型继承展平、多模块编译 |
| 43 | [G5](G5/App/main.vp) | GSList[T] opaque 降级问题 + 访问器方案、泛型类作字段类型 | 泛型容器 opaque、跨模块 stub |
| 44 | [G7](G7/App/main.vp) | 最小复现：类名 Value 与全局变量冲突导致 struct body 不完整 | 符号表命名冲突 |
| 45 | [GenericOopTest](GenericOopTest/App/main.vp) | 泛型+OOP 组合：泛型函数互调、泛型类方法调泛型函数、多类型参数 | 泛型嵌套、联合类型强转语法 |
| 46 | [EdgeCaseTest](EdgeCaseTest/App/main.vp) | 类型系统边界：import 别名作基类、前向引用继承、三层 CVTable 传播、BigEndian | 类型别名、前向引用、字节序 |
| 47 | [MultiInheritTest](MultiInheritTest/App/main.vp) | 多继承：字段合并展平、菱形去重、MRO、CVTable 多继承、运算符重载继承 | 多继承布局、菱形、MRO |
| 48 | [SuperTest](SuperTest/App/main.vp) | super() 语义：__init__ 传递、静态绑定父类方法、三层链、MRO 查找 | super、虚表继承、MRO |
| 49 | [IsinstanceTest](IsinstanceTest/App/main.vp) | isinstance 运行时 vtable 继承链比较、元组类型、多继承、跨模块虚分派 | isinstance、运行时类型系统 |
| 50 | [NoVTableTest](NoVTableTest/App/main.vp) | @t.NoVTable 继承：双向/单向链表库、显式向下转型、递归泛型 | 无 vptr 布局、跨模块继承 |
| 51 | [HashTableTest](HashTableTest/App/main.vp) | hashtable 库全生命周期：插入/更新/删除/迭代/50 元素扩容/空表 | 哈希表、Python 风格特殊方法 |
| 52 | [JsonTest](JsonTest/App/main.vp) | json 库：构造/解析/序列化/嵌套取值/转义/内存复用 | json 库、条件表达式、转义 |
| 53 | [LogicFlowTest](LogicFlowTest/App/main.vp) | 控制流组合：for/while 嵌套、match 元组/守卫/穿透、c.Break/c.NoBreak | match 语法面、控制流代码生成 |
| 54 | [FakeDuckTest](FakeDuckTest/App/main.vp) | str 扩展方法全套 + 魔法字段 __data__/__mbuddy__ 注入 + split 8 种边界 + zip | 扩展方法、魔法字段注入、迭代器 |
| 55 | [DecoratorTest](DecoratorTest/App/main.vp) | 自定义装饰器 v4 约定：双阶段钩子、返回语义、@repeat(3)、递归保护 | 装饰器运行时机制 |
| 56 | [BuddyTest](BuddyTest/App/main.vp) | MemBuddy 伙伴分配器压力测试：alloc/free/合并/calloc/realloc/边界/4 线程并发/OOM | 内存分配器、多线程、边界 |
| 57 | [AstTest](AstTest/App/main.vp) | AST 解析/遍历：tokenize/parse/dump、递归遍历、运行时 isinstance 区分节点 | ast 库、运行时 isinstance |
| 58 | [NewAstTest](NewAstTest/App/main.vp) | ast 模块 93 项全面测试：手工构造节点 + parse 大量语法（match/async/lambda/f-string） | ast 库、语法面最广 |
| 59 | [LLvmLiteTest](LLvmLiteTest/App/main.vp) | llvmlite 库 27 节：类型/指令/模块打印/phi/switch/select/原子操作/SSA 验证 | llvmlite、LLVM IR 全套 |
| 60 | [TestFBProject](TestFBProject/App/main.vp) | 异常继承体系 10 场景 + c.LLVMIR 内联 IR + t.CDefine 内联函数宏 | 异常机制、内联 LLVM IR |
| 61 | [FileIoTest](FileIoTest/App/main.vp) | Win32 文件 IO：CreateFile/Write/Read 底层 + OOP File 封装 + 宽字符中文 UTF-16 | Win32 绑定、OOP 封装、宽字符串 |
| 62 | [SysLibTest](SysLibTest/App/main.vp) | 系统库：os.path/os/shutil/sys/subprocess 真实文件与子进程 I/O、平台宏分发 | 标准库集成、子进程、跨平台 |
| 63 | [NumpyTest](NumpyTest/App/main.vp) | numpy 库约 30 组：创建/统计/运算符重载/数学函数/矩阵运算/边界/性能 | numpy、运算符重载、性能 |
| 64 | [SimdTest](SimdTest/App/main.vp) | vipersimd SIMD：AVX2 向量正确性/批量运算/标量精确函数/SIMD 加速比 | SIMD、性能基准 |
| 65 | [ZlibTest](ZlibTest/App/main.vp) | zlib 库约 17 项：压缩往返/级别/增量对象/gzip/raw/zdict/Huffman 树/校验和 | zlib、Huffman、位写入器 |
| 66 | [CPythonTest](CPythonTest/App/main.vp) | CPython C API 绑定 + 包装类运算符重载：PyLong/Float/Unicode/List/Dict/PyRun/Import | CPython 嵌入、运算符重载、引用计数 |

### 难度：环境依赖 / 回归（2 个）

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 67 | [WebTest](WebTest/App/main.vp) | 网络栈：socket OOP、DNS 解析、requests.get HTTP 请求（依赖真实网络） | socket/requests、真实网络 I/O |
| 68 | [NoVTableCrossMixinTest](NoVTableCrossMixinTest/App/main.vp) | 回归：@t.NoVTable 多继承下跨 Mixin `self.` 方法调用——BaseB 内 `self.helper()` 调兄弟 Mixin BaseA.helper，须按定义类解析 + this 前移 sizeof(定义类) | 跨 Mixin 调用、NoVTable 多继承、this 调整 |

### 难度：补录（9 个，2026-10 补入）—— 新库 / 专项 / 探针

| # | 项目 | 功能概述 | 关键特性 |
|---|------|---------|---------|
| 69 | [CharTest](CharTest/App/main.vp) | `char`（= `t.CChar` = `i8`）标量语义：注解、`char()` 截断、函数返回、字符字面量、比较 | char 标量类型、i8 截断 |
| 70 | [RawArrayTest](RawArrayTest/App/main.vp) | `rawarray[T, N]` 定长数组：模块级全局、局部写读、struct 内嵌字段、数组退化 | rawarray、定长数组布局 |
| 71 | [DefaultArgTest](DefaultArgTest/App/main.vp) | 默认参数与命名/乱序实参：同模块与跨模块（`remote.vp`）的尾随默认值 | 默认参数、命名实参 |
| 72 | [CoroTest](CoroTest/App/main.vp) | 协程 `async`/`await`：`try`/`finally` 与异常传播（`coro` 模块） | 协程状态机、异常传播 |
| 73 | [ThreadingTest](ThreadingTest/App/main.vp) | vthreading 专项：`Thread`/`Lock`/`Event`/`Condition`/`RWLock`/TLS 线程局部存储 | 多线程同步原语 |
| 74 | [ZlibDbg](ZlibDbg/App/main.vp) | zlib 调试：`pyzlib`/`zdeflate`/`zinflate` 多 seed / size / wbits 往返 | zlib 往返、位宽变体 |
| 75 | [MLIRLiteTest](MLIRLiteTest/App/main.vp) | `mlirlite` 库：生成 MLIR 文本并落盘 `output/*.mlir`，供 `mlir-opt` 离线验收 | MLIR 文本生成 |
| 76 | [PtrOpProbe](PtrOpProbe/App/main.vp) | 指针操作符全形态自检：`*p = v` 等赋值形态必须真正落内存（防被静默丢弃） | 指针算子赋值、静默丢弃回归 |
| 77 | [ProbeGen](ProbeGen/App/main.vp) | 代际不稳定性最小探针：同一份源码由两代编译器各编一次并比对 IR（**勿当普通功能测试改动**） | 自举代际一致性 |

> 另有 [NegativeTest](NegativeTest/App/main.vp)：**负向测试容器**——`App/cases/` 下 9 个故意编译失败的用例（`call_too_few` / `call_too_many` / `call_wrong_type` / `call_float_to_int` / `missing_return` / `undefined_func` / `import_missing_module` / `import_wrong_path` / `import_stale_path`），由 `run_negative_tests.py` 驱动，不计入难度序列。

---

## 一·附、生命期 / 逃逸（escape）相关测试

验证 M1–M3 的生命期检查（栈地址逃逸、借用传播、函数逃逸摘要）、`new` 描述符分配，
以及 `new heap slife` 的 RAII 自动释放（M3）。因历史原因前 4 个位于**仓库根**（不在 `Test/` 下）：

| 项目 | 位置 | 期望结果 |
|---|---|---|
| EscapeTest | 仓库根 `EscapeTest/` | **编译失败**：`return Mid(&l)` → `LifetimeError`（v2 传递闭包） |
| EscapeOkTest | 仓库根 `EscapeOkTest/` | 编译通过并输出 `Hi/hello/AB/x/aa/loop`（值拷贝/静态/帧内使用等豁免不得误报） |
| EscapeMethodTest | 仓库根 `EscapeMethodTest/` | **编译失败**：方法 / `__init__` / 嵌套函数交出栈地址 → `LifetimeError`（三用例互斥，一次开一条） |
| EscapeXmodTest | 仓库根 `EscapeXmodTest/` | **编译失败**：跨模块摘要（`.vpi` 落盘 `# esc=`）路径 → `LifetimeError` |
| NewTest | [Test/NewTest/](NewTest/App/main.vp) | 编译通过并输出 4 行：`stack`(显式 slife) / `heap` / `stack默认slife`（验证**缺省规则**：省略生命期时 stack→slife、heap/memgr→hlife）/ `memgr` |
| NewLifetimeTest | [Test/NewLifetimeTest/](NewLifetimeTest/App/main.vp) | 编译通过、退出码 0（**M3 owned slife RAII**：出口释放 / 循环内覆盖释放 / 别名只释放一次 / 嵌套函数登记隔离 / early return / void 裸 return / 仅分支里 new 时 `free(NULL)` / stack slife 不释放；**§3.6 析构调度**：出口释放恰好 1 次 `__del__`、循环 3 轮共 3 次）。**另含 IR 断言**：IR 中必须出现 `llvm.call @free` |
| NewLifetimeFreeTest | [Test/NewLifetimeFreeTest/](NewLifetimeFreeTest/App/main.vp) | **编译失败**：对 `slife` 对象手动 `stdlib.free(p)` → `LifetimeError`（§4.3 判据5，编译器独占释放；手动 `del p` 同样被拒） |
| NewLifetimeAsyncTest | [Test/NewLifetimeAsyncTest/](NewLifetimeAsyncTest/App/main.vp) | **编译失败**：协程体（`async`）里的 `new heap slife` → `LifetimeError`（§4.2：状态机拆分 body，释放点无法确定；`new stack` / `new … hlife` 不受限） |
| NewLifetimeWillFreeTest | [Test/NewLifetimeWillFreeTest/](NewLifetimeWillFreeTest/App/main.vp) | **编译失败**：P2 `@life(willFree(p))` 标注驱动 —— `free(p)` 之后再 `free(p)` → `LifetimeError`（二次释放） |
| NewLifetimeUseAfterFreeTest | [Test/NewLifetimeUseAfterFreeTest/](NewLifetimeUseAfterFreeTest/App/main.vp) | **编译失败**：P2 —— `free(p)` 之后读/传 `p` → `LifetimeError`（使用已释放变量） |
| NewLifetimeWillFreeOkTest | [Test/NewLifetimeWillFreeOkTest/](NewLifetimeWillFreeOkTest/App/main.vp) | **编译成功 + 退出码 0**：P2 合法用法 —— 首次 `free` 本身合法；同名变量**重新赋值**会清除失效态，其后可再用、再 `free`（防误报） |

单独运行（`regression_test.py` 与 `SequentialRegressionTest.py` 都支持）：

```bash
python Test/regression_test.py --escape            # 只跑上表全部项目
python Test/regression_test.py --only NewTest      # 只跑指定项目（逗号分隔可多个）
python Test/SequentialRegressionTest.py --escape --exe <TransPyV.exe> --rebuild-includes
python Test/SequentialRegressionTest.py --only NewLifetimeTest --exe <TransPyV.exe>
```

> `--escape` / `--only` 会在 `Test/<名>` 与**仓库根** `<名>` 两处查找 `project.json` / `project.vpj`，所以根级 escape 项目也能直接跑；`--escape` 会忽略 README 的难度顺序。

**IR 断言**：`SequentialRegressionTest.py` 的 `IR_EXPECT`（项目名 → 生成 IR 中必须出现的子串）在编译成功后、运行前，把 `{build_dir}` 下所有 `.ll` 拼起来做子串检查；找不到 `.ll` 视为断言失败（fail-fast，不静默跳过）。
> `{build_dir}/temp/**.ll` 里是 **LLVM dialect 文本**（mlir-opt 的输入），调用形如 `llvm.call @free(%9) : (!llvm.ptr) -> ()`（不是经典 IR 的 `call void @free`），所以断言串用 `llvm.call @free`（`llvm.func @free` 是声明行，不会被匹配）。
> 之所以加 IR 断言：M3 的"出口释放"只靠"运行没崩"证明不了——**漏了释放是纯泄漏，进程照样退出码 0**；必须直接断言释放调用出现过。
> 因此纳入该断言的项目**不得自己写 free**（否则用户代码的 `free` 会蒙混过关）：`NewLifetimeTest` 正是刻意不含任何用户级 `free`。

**负向断言**（"应报 `LifetimeError`"）需要 TransPyV 编译——`NegativeTest/run_negative_tests.py` 用的是 TPC，而 `new` 描述符与 `LifetimeError` 只在 TPV 侧实现，故单独提供：

```bash
python Test/run_lifetime_negative_tests.py --exe .\TransPyV\output\TransPyV.exe
python Test/run_lifetime_negative_tests.py --exe .\TransPyV\output\TransPyV.exe --only EscapeMethodTest
```

> 默认跑 `EscapeTest` / `EscapeMethodTest` / `EscapeXmodTest` / `NewLifetimeFreeTest` / `NewLifetimeAsyncTest` / `NewLifetimeWillFreeTest` / `NewLifetimeUseAfterFreeTest`：断言**编译失败且输出含 `LifetimeError`**；编译成功 = 漏检（FAIL），报错但方向不符 = SKIP。

负向项目在 `SequentialRegressionTest.py` 里是**反向判定**（`NEGATIVE_PROJECTS`）：编译失败且输出含 `LifetimeError` 才算通过，且**不再进入运行阶段**；编译成功 = 漏检，直接终止。`regression_test.py --escape` 会**剔除**这些项目（该脚本要求"编译成功 + 能跑"），负向断言请用 `SequentialRegressionTest.py --escape` 或上面的 `run_lifetime_negative_tests.py`。

---

## 二、建议实现顺序（难度升序，共 68 步）

按"先基础语法 → 再类型系统 → 再容器/OOP → 再泛型/闭包难点 → 最后编译器自身库与外部集成"推进，每步按依赖关系排序。

### 第 1 层：基础语法与函数（8 个，建立编译最小可用）
1. **FuncTest** — 函数定义/调用/递归（编译器最基础能力）
2. **LoopTest** — for/while/break/continue（控制流基础）
3. **StringTest** — string 库（字符串是几乎所有测试的依赖）
4. **StructTest** — 结构体基础（OOP 的根基）
5. **EqTest** — 比较语义边界（==/is/None）
6. **ShortCircuitTest** — 短路求值（布尔逻辑正确性）
7. **IterTest** — for-in 字符串迭代
8. **SlotsBugTest** — 编译期回归（编译通过即达标）

### 第 2 层：类型系统、运算与声明（9 个）
9. **TypeCastTest** — 类型转换/C 语义运算（后续所有运算正确性的前提）
10. **PointerTest** — 指针操作/算术
11. **LoopMathTest** — 数学/位运算/复合赋值/优先级
12. **StringIterTest** — 指针迭代/算术/c.Deref/Set/Addr
13. **ExpandKeywordsTest** — 软关键字 fn/fun/func
14. **VariadicTest** — 变参 printf/snprintf
15. **SprintfTest** — 浮点格式化 %a/%g（格式化正确性）
16. **FormatStringTest** — f-string 格式说明符
17. **Extern2Test** — 外部声明去重

### 第 3 层：容器与内存（8 个）
18. **ListTest** — list[int] 基础容器（泛型 + 联合下标）
19. **MpoolOopTest** — MemPool/MemSlab（后续大量测试依赖 memhub）
20. **MemhubTest** — MemManager 多态（虚分派正确性）
21. **DictTest** — dict 库 + JSON 往返
22. **HashLibTest** — hashlib/base64/binascii
23. **VRandomTest** — vrandom 库（结构重复、快速验证）
24. **VectorGenericTest** — 泛型容器（初步接触泛型）
25. **ArgparseTest** — argparse（内存布局 + 解析器）

### 第 4 层：泛型（10 个，编译器核心难点之一）
26. **GenericTest** — 泛型基础（先建立泛型可用性）
27. **GenericTest3** — 泛型函数显式类型参数
28. **GenericTest4** — 泛型类显式类型参数
29. **G3** — F-bounded 泛型继承（GSListNode[Node]）
30. **G6** — atom 原子操作（无泛型，穿插放松）
31. **GenericTest2** — 高级泛型 + __sizeof__ 特化语义
32. **G4** — includes 泛型继承 + 多模块引用
33. **G5** — GSList[T] opaque 降级/访问器
34. **G7** — 符号冲突回归（较难，可后置）
35. **GenericOopTest** — 泛型 + OOP 组合

### 第 5 层：OOP 与继承（9 个）
36. **ClassArrayTest** — 类与数组基础
37. **OopInheritTest** — 继承/虚方法/运算符重载/链式调用
38. **BuiltinDecoratorTest** — property/staticmethod/classmethod
39. **EnumTest** — CEnum/REnum + match 解构
40. **EdgeCaseTest** — 类型别名/前向引用/多层继承（类型系统边界）
41. **IsinstanceTest** — isinstance vtable 链（运行时类型系统）
42. **MultiInheritTest** — 多继承/菱形/MRO
43. **NoVTableTest** — @t.NoVTable 继承 + 链表库
44. **SuperTest** — super() 静态绑定/MRO

### 第 6 层：闭包与控制流进阶（5 个）
45. **ClosureCallTest** — 闭包函数指针调用（最小复现）
46. **ClosureTest** — nonlocal/global/lambda 基础
47. **ClosureTest2** — 引用 vs 值捕获/多层级（闭包难点）
48. **ForAndLoopTest** — zip/enumerate 迭代器
49. **LogicFlowTest** — match 元组/守卫/控制流组合

### 第 7 层：编译器自身库与综合（8 个）
50. **AstTest** — AST 解析/遍历/isinstance
51. **NewAstTest** — ast 模块 93 项全面回归
52. **LLvmLiteTest** — llvmlite IR 生成（自举关键，27 节）
53. **BuddyTest** — 内存压力 + 多线程（可并行验证健壮性）
54. **FakeDuckTest** — str 扩展方法 + 魔法字段注入
55. **DocTest** — __doc__ 跨模块
56. **DefineTest** — 编译期宏/条件编译/platmacro
57. **DecoratorTest** — 自定义装饰器 v4 约定（运行时机制）

### 第 8 层：外部库与真实环境（10 个）
58. **HashTableTest** — 哈希表全生命周期
59. **JsonTest** — json 构造/解析/序列化
60. **TestFBProject** — 异常体系 + 内联 LLVM IR
61. **FileIoTest** — Win32 文件 IO/宽字符
62. **SysLibTest** — os/shutil/sys/subprocess 真实 I/O
63. **NumpyTest** — numpy 数值库（运算符重载大考）
64. **SimdTest** — SIMD 向量 + 性能基准
65. **ZlibTest** — zlib/Huffman（代码量最大）
66. **CPythonTest** — CPython C API 嵌入（依赖 Python 运行时）
67. **WebTest** — socket/requests（依赖真实网络，最后跑）
68. **NoVTableCrossMixinTest** — @t.NoVTable 跨 Mixin self. 调用（编译器缺陷回归）

### 第 9 层：补录（9 个，2026-10）

69. **CharTest** — `char`（i8）标量语义
70. **RawArrayTest** — `rawarray[T, N]` 定长数组
71. **DefaultArgTest** — 默认参数 / 命名实参
72. **CoroTest** — 协程 `async`/`await` 与异常传播
73. **ThreadingTest** — vthreading 多线程同步原语
74. **ZlibDbg** — zlib 多 seed/size/wbits 往返调试
75. **MLIRLiteTest** — `mlirlite` 生成 MLIR 文本供 `mlir-opt` 验收
76. **PtrOpProbe** — 指针算子赋值形态（防静默丢弃回归）
77. **ProbeGen** — 自举代际一致性探针（比对两代编译器 IR）

---

## 三、按主题分组（索引）

### 基础语法与函数
FuncTest、LoopTest、LoopMathTest、ShortCircuitTest、ExpandKeywordsTest、TypeCastTest、EqTest、PointerTest

### 字符串与格式化
StringTest、StringIterTest、FormatStringTest、VariadicTest、SprintfTest、IterTest、FakeDuckTest（str 扩展方法）

### 容器与数据结构
ListTest、DictTest、HashTableTest、VectorGenericTest、JsonTest、HashLibTest

### OOP 与继承
StructTest、ClassArrayTest、OopInheritTest、MultiInheritTest、SuperTest、NoVTableTest、IsinstanceTest、BuiltinDecoratorTest、DecoratorTest

### 泛型
GenericTest、GenericTest2、GenericTest3、GenericTest4、GenericOopTest、G3、G4、G5、G7

### 闭包
ClosureCallTest、ClosureTest、ClosureTest2

### 控制流
LoopTest、LoopMathTest、LogicFlowTest、ForAndLoopTest、EnumTest（match 解构）、EdgeCaseTest

### 内存管理
BuddyTest、MpoolOopTest、MemhubTest

### 编译期机制
DefineTest、Extern2Test、SlotsBugTest、TestFBProject（部分）

### 编译器自身库（自举用）
AstTest、NewAstTest、LLvmLiteTest、BuddyTest、DictTest、HashTableTest、JsonTest

### 外部库/系统集成
FileIoTest、SysLibTest、WebTest、ZlibTest、NumpyTest、SimdTest、CPythonTest、ArgparseTest、VRandomTest

### 回归复现（缺陷最小化）
G7（符号冲突）、ClosureCallTest（闭包指针调用）、Extern2Test（声明去重）、SlotsBugTest（注解崩溃）、SprintfTest（%g 精度/变参）、PtrOpProbe（指针算子赋值静默丢弃）、NoVTableCrossMixinTest（跨 Mixin self. 调用）

### 补录（2026-10）
CharTest（char 标量）、RawArrayTest（rawarray）、DefaultArgTest（默认参数）、CoroTest（协程）、ThreadingTest（多线程）、ZlibDbg（zlib 调试）、MLIRLiteTest（MLIR 生成）、PtrOpProbe、ProbeGen（代际一致性）

### 负向测试（不计入难度序列）
NegativeTest（9 个故意编译失败用例 + `run_negative_tests.py`）

---

## 四、排序原则说明

1. **依赖优先**：`FuncTest`/`TypeCastTest` 保证基础运算 → `MpoolOopTest`/`ListTest` 建立 memhub/容器 → 所有依赖它们的测试。
2. **先面后点**：先用每主题"基础版"（GenericTest、ClosureTest、OopInheritTest）验证可用，再用进阶版（GenericTest2、ClosureTest2、MultiInheritTest）压边界。
3. **难点靠后**：泛型（G4/G5/G7）、多继承（MultiInheritTest/SuperTest）、闭包值捕获（ClosureTest2）、装饰器运行时（DecoratorTest）等语义深处放中后段。
4. **编译器自举相关后置**：AstTest/NewAstTest/LLvmLiteTest 验证编译器自身依赖的库，是自举实验的前置检查。
5. **环境依赖最后**：WebTest（真实网络）、CPythonTest（Python 运行时）、FileIoTest/SysLibTest（真实文件系统）放最后，避免环境问题干扰核心编译器验证。
6. **回归复现型穿插**：G7/ClosureCallTest/Extern2Test/SlotsBugTest 等最小复现用例可随时单独运行验证特定修复。
