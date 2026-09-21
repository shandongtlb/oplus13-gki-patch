# 当前状态

更新基准：common `f34864787733a55f7fba20ca65eda7c674e1d43e`，对应发布树目标 tree `7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`。

## 已完成

- 以官方公开 HMBIRD 回退提交 `c7bef25f9416d6a0f87ce551be9c25729f7dae6c` 的 parent `f2223b938963c24e8ad9ac2e4491c8bb718e3eb5` 作为旧源码基线，恢复 built-in HMBIRD/common 接入。
- 通过 stock BTF、符号、ARM64 机器码和实际构建对象，恢复了 HMBIRD 生命周期、CPU 选择、RT/超时、uclamp、shadow tick、任务生命周期以及若干 block/EROFS/MM/xHCI/cert stock 差异。
- 22 个 common 补丁逐步 tree 重放通过；源码目标 tree 见 README。
- 候选曾完成启动、Wi-Fi/蓝牙基本使用、王者 HMBIRD 接管与关闭/重开等有限测试。
- 2026-09-21 重新连接设备，恢复后的 stock release、notes、BTF 和配置均已实采匹配。只读王者测试记录到两次 HMBIRD 启用、两次关闭 finished；用户确认重进大厅画面与操作正常，最终息屏，采集前后为同一次启动。

## 尚未等价或待复核

- 候选王者场景曾出现 `rq->balance_callback` 警告。2026-09-21 第一轮 stock 测试未使用 probe，在自然启停中新增 1 条相同 `rq_pin_lock` 不变量警告，证明这一类告警并非候选独有。stock 报点在 `__schedule`，候选此前报点在 `task_rq_lock` / HMBIRD 关闭 worker。第二轮另捕获 2 条同条件警告，报点为 `android_rvh_try_to_wake_up` 和 `scheduler_tick_no_balance`，均发生在短时 probe 已结束后的关闭附近。这些 stock 现场的 callback 身份、排队者及完整因果尚未证明，不能与候选现场视为完全相同，也未据此修改或隐藏警告。
- `!migration_pending` 已在候选和 stock 的相同专用监听、相同王者流程中分别捕获。候选现场为 `cableThread`/CPU4，stock现场为 `pcdn_http`/CPU3；两边均为 `pending=NULL`、普通 mask `0xc0`、目标 CPU6、flags4、`migration_disabled=1`。stock 本轮还实际打印了同一 `__set_cpus_allowed_ptr_locked+0x4b0/0x640` WARN。因此不能把该告警归因于候选 HMBIRD 恢复；没有为此新增补丁，也不隐藏 WARN 或改变迁移语义。完整现场见研究仓库的专项报告。
- 2026-09-21 后续仅对迁移 pending 做离线追查。新增核对11个完整函数、1124个指令词，未见这些 owner 的新 stock 逻辑差距。找到另一个条件时序：旧迁移请求尚未完成，任务已合法换核并重新 pin，另一亲和性请求收窄普通 mask；旧 CPU stopper 可能按临时 `cpus_ptr` 提前清 pending。它与“pin 前已在普通 mask 外”及“清 pending 后迁移被拒绝”分别保留，均未取得现场历史，不能认定根因。原探针在唯一 WARN 之前，once 不解释0命中；精确采集边界与全局 arm 状态仍缺。下一轮应优先取得异常任务身份及 pending 清空前的两种 mask，未新增补丁或开始设备测试。
- 有限运行测试不能覆盖所有 HMBIRD 并发、异常回滚、热插拔、长时间负载和调度器切换组合。
- F2FS 只做过有限用户态读写/校验；不能据此宣称断电持久化、冷缓存、强制 GC、checkpoint 或长期写回完全等价。
- system_dlkm 保留 stock 模块的方案通过签名、版本和依赖检查；候选运行时696个模块名称与stock相同，仍不能据此认定所有模块功能等价。
- 当前保持 `CONFIG_SYSVIPC=n`，此仓库不提供 SYSVIPC 补丁。

## 产物边界

本仓库不发布官方签名 boot，也不保证任意 Android 版本、任意 slot 或任意新基线可以直接刷写。编译出的 Image、boot、vmlinux、raw BTF、运行日志和设备备份应保存在本地证据目录，不应提交到本仓库。
