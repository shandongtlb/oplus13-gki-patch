# OnePlus 13 stock GKI/common 复原补丁

尽量恢复 OnePlus 13 / SM8750 官方 stock common 内核的行为、ABI 和 built-in HMBIRD/风驰调度。仓库包含 **22 个完整逆向恢复补丁、研究过程说明和四个离线分析脚本**。

## 应用

适用官方源码：[OnePlusOSS/android_kernel_common_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750)。

在干净的 common 源码仓库中，从以下基线新建分支，再按文件名顺序应用：

```bash
git switch -c stock-recreation e1b346b6b4f4096eb342ae3684838a942fd6f6c4
git am --keep-cr /path/to/oplus13-gki-patch/source/patches/*.patch
git rev-parse 'HEAD^{tree}'
```

预期源码 tree：`7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`，与当前候选源码 `f34864787733a55f7fba20ca65eda7c674e1d43e` 相同。`--keep-cr` 保留原始补丁里的换行；Git 提交 ID 可能因提交者及时间不同而变化，按 tree 核对。

22 个补丁已逐步重放，每一步源码 tree 都与原提交一致。新版本源码需要重新适配，不能保证直接应用。

## 范围与状态

恢复内容包括 HMBIRD/common 接入、shadow tick、CPU 选择、超时、uclamp、启停与诊断，以及已确认的 block、EROFS、swap hook、xHCI 和 stock 公钥信任差异。

候选已成功启动，Wi-Fi/蓝牙及王者 HMBIRD 启停做过有限验证。仍有两类 scheduler warning 待确认来源，不能称全内核等价。详见[当前状态](docs/STATUS.md)和[来源说明](docs/PROVENANCE.md)。

[研究过程](docs/RESEARCH.md)记录证据方法、核对范围及未解决问题；[脚本说明](docs/SCRIPTS.md)给出符号恢复、导出 CRC、BTF 布局和函数指令比较的用法。

不包含 SYSVIPC 补丁或构建入口改动，不加入第三方性能优化。镜像、原始手机日志、完整源码及构建缓存保留在本地，不上传。
