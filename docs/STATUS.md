# 当前状态

2026-09-22 更新：common `83e4d6950a2d2fb62482e6391466d66fc8906370`，全部23个补丁目标 tree `f50f02f8976716270ecae9c58560deabd021587a`。前22个stock恢复提交截止f348；第23个只增加SYSVIPC。下面的历史stock/候选运行结果对应前22个补丁，不等于新版本已上机。

## SYSVIPC 当前结果

- 保留cctv reserve6/7/8布局方案，新增SYSVIPC及自动compat/sysctl，其余DroidSpaces扩展撤回。
- 21个指定ARM64对象目标检查通过，n/y的task_struct均为4800字节，原218个字段保持；所检1945个导出CRC完全一致，savedefconfig及全部23个补丁逐步tree重放通过。
- 之前较宽配置的实验版本中，PostgreSQL18.6的2048行数据、事务提交/回滚及三轮正常重启通过，采到实际SysV共享内存段。但DroidSpaces容器启动期间手机重启，原因未确定；用户已停止该方向，相关扩展不在本仓库补丁中。
- 精简后的83e4d6950已于2026-09-22完成一轮空缓存完整构建（112.28秒）及boot封装；9003原导出、stock证书、96个stock系统模块签名/5208版本记录通过，最终task4800/218原字段保持。尚未上机。详见[SYSVIPC](SYSVIPC.md)。

## 已完成

- 以官方公开 HMBIRD 回退提交 `c7bef25f9416d6a0f87ce551be9c25729f7dae6c` 的 parent `f2223b938963c24e8ad9ac2e4491c8bb718e3eb5` 作为旧源码基线，恢复 built-in HMBIRD/common 接入。
- 通过 stock BTF、符号、ARM64 机器码和实际构建对象，恢复了 HMBIRD 生命周期、CPU 选择、RT/超时、uclamp、shadow tick、任务生命周期以及若干 block/EROFS/MM/xHCI/cert stock 差异。
- 22 个 stock 恢复补丁的静态及有限运行结果保留；包含SYSVIPC的最新源码目标 tree 见 README。
- 候选曾完成启动、Wi-Fi/蓝牙基本使用、王者 HMBIRD 接管与关闭/重开等有限测试。
- 2026-09-21 重新连接设备，恢复后的 stock release、notes、BTF 和配置均已实采匹配。只读王者测试记录到两次 HMBIRD 启用、两次关闭 finished；用户确认重进大厅画面与操作正常，最终息屏，采集前后为同一次启动。

## 尚未等价或待复核

- 候选王者场景曾出现 `rq->balance_callback` 警告。2026-09-21 第一轮 stock 测试未使用 probe，在自然启停中新增 1 条相同 `rq_pin_lock` 不变量警告，证明这一类告警并非候选独有。stock 报点在 `__schedule`，候选此前报点在 `task_rq_lock` / HMBIRD 关闭 worker。第二轮另捕获 2 条同条件警告，报点为 `android_rvh_try_to_wake_up` 和 `scheduler_tick_no_balance`，均发生在短时 probe 已结束后的关闭附近。这些 stock 现场的 callback 身份、排队者及完整因果尚未证明，不能与候选现场视为完全相同，也未据此修改或隐藏警告。
- `!migration_pending` 已在候选和 stock 的相同专用监听、相同王者流程中分别捕获。候选现场为 `cableThread`/CPU4，stock现场为 `pcdn_http`/CPU3；两边均为 `pending=NULL`、普通 mask `0xc0`、目标 CPU6、flags4、`migration_disabled=1`。stock 本轮还实际打印了同一 `__set_cpus_allowed_ptr_locked+0x4b0/0x640` WARN。因此不能把该告警归因于候选 HMBIRD 恢复；没有为此新增补丁，也不隐藏 WARN 或改变迁移语义。完整现场见研究仓库的专项报告。
- 2026-09-21 后续仅对迁移 pending 做离线追查。新增核对11个完整函数、1124个指令词，未见这些 owner 的新 stock 逻辑差距。找到另一个条件时序：旧迁移请求尚未完成，任务已合法换核并重新 pin，另一亲和性请求收窄普通 mask；旧 CPU stopper 可能按临时 `cpus_ptr` 提前清 pending。它与“pin 前已在普通 mask 外”及“清 pending 后迁移被拒绝”分别保留，均不能单凭源码认定根因。随后候选和 stock 已在相同专用监听及王者流程中分别捕获同一前置现场，stock还实际打印对应 WARN；该专项已闭合，未新增补丁。
- 有限运行测试不能覆盖所有 HMBIRD 并发、异常回滚、热插拔、长时间负载和调度器切换组合。
- F2FS 只做过有限用户态读写/校验；不能据此宣称断电持久化、冷缓存、强制 GC、checkpoint 或长期写回完全等价。
- system_dlkm 保留 stock 模块的方案通过签名、版本和依赖检查；候选运行时696个模块名称与stock相同，仍不能据此认定所有模块功能等价。
- SYSVIPC已作为第23个补丁提供；最终版本的完整Image和运行验收仍待完成。

## 产物边界

本仓库不发布官方签名 boot，也不保证任意 Android 版本、任意 slot 或任意新基线可以直接刷写。编译出的 Image、boot、vmlinux、raw BTF、运行日志和设备备份应保存在本地证据目录，不应提交到本仓库。
