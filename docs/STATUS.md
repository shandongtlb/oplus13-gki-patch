# 当前状态

更新基准：common `f34864787733a55f7fba20ca65eda7c674e1d43e`，对应发布树目标 tree `7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`。

## 已完成

- 以官方公开 HMBIRD 回退提交 `c7bef25f9416d6a0f87ce551be9c25729f7dae6c` 的 parent `f2223b938963c24e8ad9ac2e4491c8bb718e3eb5` 作为旧源码基线，恢复 built-in HMBIRD/common 接入。
- 通过 stock BTF、符号、ARM64 机器码和实际构建对象，恢复了 HMBIRD 生命周期、CPU 选择、RT/超时、uclamp、shadow tick、任务生命周期以及若干 block/EROFS/MM/xHCI/cert stock 差异。
- 22 个 common 补丁逐步 tree 重放通过；源码目标 tree 见 README。
- 候选曾完成启动、Wi-Fi/蓝牙基本使用、王者 HMBIRD 接管与关闭/重开等有限测试；用户随后报告已经恢复 stock 内核并成功开机。该报告尚未重新读取设备身份，不能替代新的 stock 证据。

## 尚未等价或待复核

- 王者场景中出现过两类 scheduler warning：`!migration_pending` 和 `rq->balance_callback`。离线分析已经定位到可达的 RT pull 回调、HMBIRD 启停与迁移/队列锁生命周期，但没有证明它们是候选独有，也没有足够证据修改官方路径。stock 同代码路径存在；实际 stock 同场景复现仍未完成。
- 有限运行测试不能覆盖所有 HMBIRD 并发、异常回滚、热插拔、长时间负载和调度器切换组合。
- F2FS 只做过有限用户态读写/校验；不能据此宣称断电持久化、冷缓存、强制 GC、checkpoint 或长期写回完全等价。
- system_dlkm 保留 stock 模块的方案通过签名、版本和依赖检查；候选运行时696个模块名称与stock相同，仍不能据此认定所有模块功能等价。
- 当前保持 `CONFIG_SYSVIPC=n`，此仓库不提供 SYSVIPC 补丁。

## 产物边界

本仓库不发布官方签名 boot，也不保证任意 Android 版本、任意 slot 或任意新基线可以直接刷写。编译出的 Image、boot、vmlinux、raw BTF、运行日志和设备备份应保存在本地证据目录，不应提交到本仓库。
