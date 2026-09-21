# 离线分析脚本

这四个脚本来自本项目实际分析工具，保留原比较算法，将研究目录改成显式输入参数。它们读取本地文件，不连接手机、不编译内核。原始输入和输出可放仓库内被忽略的 `local/`；镜像、日志及分析结果不会随脚本上传。

需要 Python 3。函数比较另需 `pyelftools`；BTF 转 JSON 需要本机 `bpftool`。脚本使用断言检查格式，请不要用 `python -O` 或 `PYTHONOPTIMIZE` 运行。下方路径均为示例，输入须由使用者提供。

## 1. 恢复 Image 符号

输入必须是解包后的未压缩 ARM64 `Image`，不是 `boot.img` 或 ELF `vmlinux`。仅支持已检查的 Linux 6.6、小端、64 位、base-relative 且非 ABSOLUTE_PERCPU 的 kallsyms 表示，不是通用内核解码器。`--btf-offset` 是独立确认的 `__start_BTF` 文件偏移，不能随意猜测。

```bash
python3 scripts/recover_kallsyms.py \
  --image local/stock/Image --btf-offset 24244004 \
  --output local/symbols
```

`24244004` 只对应本项目 stock Image（SHA-256：`0b4b3aadd775009d88f39d0738ee7fa1a8a053444f668c2a762d0ea31f86e6a5`）；其他版本要重新确认。输出 `kallsyms.json`、`System.map.recovered`、HMBIRD 符号清单和格式验证报告。地址是链接地址，不是运行时 KASLR 地址。

## 2. 提取导出符号和 CRC

```bash
python3 scripts/extract_stock_exports.py \
  --image local/stock/Image --kallsyms local/symbols/kallsyms.json \
  --config local/stock/kernel.config --source /path/to/kernel_platform/common \
  --output local/stock-exports.json
```

配置应来自同一 stock Image。`--source` 用于记录导出格式与模块加载器的参考源码哈希。脚本核对 PREL32 导出表、直接 u32 CRC 表、符号名、命名空间及普通/GPL 分组，CRC 从 Image 读取。CRC 一致不能单独证明布局、行为或完整 kABI。

## 3. 比较 BTF 类型布局

先将 raw BTF 或含 `.BTF` 的 ELF 转成 `bpftool` JSON：

```bash
bpftool -j btf dump file local/stock/vmlinux.btf format raw > local/stock-btf.json
bpftool -j btf dump file local/candidate/vmlinux format raw > local/candidate-btf.json
python3 scripts/compare_common_type_projections.py \
  --stock local/stock-btf.json --candidate local/candidate-btf.json \
  --output local/type-comparison.json
```

`--candidate` 可以重复指定。仅用于双方都是 64 位 ARM64、指针宽度 8 字节的输入。按名称和种类匹配 struct、union、enum，递归比较按值成员、数组和标量，指针只比较表示，不追踪指向类型。重复名称、缺失类型和不匹配项会保留在报告；只有已比较类型不匹配会返回非零，缺失类型须另查报告。比较范围由输入实际包含的类型决定，不能替代函数原型、对齐、CRC 或运行验证。

## 4. 比较函数指令

```bash
python3 scripts/compare_stock_function.py \
  --image local/stock/Image --kallsyms local/symbols/kallsyms.json \
  --object local/candidate/build_policy.o --function switched_from_rt \
  --output local/function-comparison.json
```

对象必须是 AArch64 可重定位 ELF（`.o`）；`--function` 可重复指定。stock 名称重复时，单函数可用 `--stock-address 0x...` 指定已恢复的地址。脚本核对支持的重定位与调用目标；歧义目标、section 符号和不支持的重定位保持 unresolved。

`exact_relocated_body` 只表示候选 ELF 声明长度内的指令匹配，仍须独立核对 stock 函数边界。它不自动完成 alternatives、jump labels、链接器转换、外部调用链或并发语义审计。不同指令不自动代表行为不同；退出码 0 也不表示函数相同，必须检查 JSON 的 `status`、`mismatches` 和 `unresolved_relocations`。

这些脚本是复核入口；完整研究结论和边界见[研究过程](RESEARCH.md)，不能用一次脚本执行代替全部审计。

发布前用原有样本检查：恢复的 110092 个符号及配套文件与研究原件逐字节一致；9003 个导出记录一致；policy/core 两个对象的 BTF 比较记录分别为 538/538、646/646 匹配，缺失均为 0。函数示例与原脚本输出一致：26 个指令词匹配、4 处重定位 unresolved、0 处 mismatch；这验证脚本迁移保留原结果，不是该函数已完成全部核对的证明。
