# OnePlus 13 stock GKI/common 复原与 SYSVIPC

尽量恢复 OnePlus 13 / SM8750 官方 stock common 内核的行为、ABI 和 built-in HMBIRD/风驰调度，只额外增加 System V IPC。仓库包含 **22 个完整逆向恢复补丁 + 1 个 SYSVIPC ABI 补丁**，以及研究过程说明和四个离线分析脚本。

## 应用

适用官方源码：[OnePlusOSS/android_kernel_common_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750)。

在包含 `kernel_platform/` 的工程根目录执行，目标 `kernel_platform/common` 必须是干净的 common Git 仓库。从以下基线新建分支，再按文件名顺序应用；将 `/path/to/oplus13-gki-patch` 替换为补丁仓库的实际绝对路径：

```bash
git -C kernel_platform/common switch -c stock-recreation e1b346b6b4f4096eb342ae3684838a942fd6f6c4
git -C kernel_platform/common am --keep-cr /path/to/oplus13-gki-patch/source/patches/*.patch
git -C kernel_platform/common rev-parse 'HEAD^{tree}'
```

补丁内部的文件路径相对于 common 仓库根目录；`-C kernel_platform/common` 指定应用位置。若只单独克隆了 common，把该参数替换为实际源码目录即可。

应用全部 23 个补丁后的源码 tree：`f50f02f8976716270ecae9c58560deabd021587a`，与当前源码 `83e4d6950a2d2fb62482e6391466d66fc8906370` 相同。`--keep-cr` 保留原始补丁里的换行；Git 提交 ID 可能因提交者及时间不同而变化，按 tree 核对。

23 个补丁已逐步重放，每一步源码 tree 都与原提交一致。原来的 22 个恢复补丁保持原样；已应用它们的源码只需继续应用 `0023`。新版本源码需要重新适配，不能保证直接应用。

## 范围与状态

恢复内容包括 HMBIRD/common 接入、shadow tick、CPU 选择、超时、uclamp、启停与诊断，以及已确认的 block、EROFS、swap hook、xHCI 和 stock 公钥信任差异。

前 22 个恢复补丁的候选已成功启动，Wi-Fi/蓝牙及王者 HMBIRD 启停做过有限验证。rq callback 和 `!migration_pending` 两类警告随后均在 stock 对照中出现，没有为此改变官方迁移语义或隐藏警告。

第 23 个补丁使用 cctv 的 reserve 6/7/8 方案，开启 SYSVIPC 并保持原 task_struct 布局。配置、选定对象和 ABI 检查通过；这个精简后的最终版本尚未完整构建或上机。不包含 DroidSpaces 扩展。详见 [SYSVIPC 说明](docs/SYSVIPC.md)、[当前状态](docs/STATUS.md)和[来源说明](docs/PROVENANCE.md)。

[研究过程](docs/RESEARCH.md)记录证据方法、核对范围及未解决问题；[脚本说明](docs/SCRIPTS.md)给出符号恢复、导出 CRC、BTF 布局和函数指令比较的用法。

不包含构建入口改动或第三方性能优化。镜像、原始手机日志、完整源码及构建缓存保留在本地，不上传。
