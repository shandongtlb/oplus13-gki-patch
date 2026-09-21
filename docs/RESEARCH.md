# 研究过程与证据边界

本项目以恢复 OnePlus 13 stock common 行为、ABI 和 built-in HMBIRD 为目标。补丁应用在[官方 common 源码](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750)的 `e1b346b6` 基线上；HMBIRD 主体取自官方回退提交 `c7bef25f` 的 parent `f2223b9`。先恢复被回退的源码和接入，再按 stock 二进制核对差异，保留当前基线的独立更新。旧官方实现只是起点，不能直接视为当前 stock 的完整实现。

第一步固定输入身份，分别记录源码、stock Image、配置、raw BTF 和候选产物。raw BTF 能说明类型、字段偏移及函数原型，却不包含函数机器码；布局相同不能证明函数体相同，也不能将 raw BTF 当作完整 vmlinux。符号名和相邻地址用于定位，函数边界还需结合实际对象、ELF 和 Image 核验。

随后逐函数比较 ARM64 指令。对链接造成的地址变化，解析重定位并核对实际调用或数据目标；同时检查 alternatives 替换代码和 jump labels 的站点、目标与元数据。明确的链接转换和条件性语义差异单列，不以笼统忽略地址的方式判定通过。改动关键指令或清链写入的负对照用于检查验收器是否能拒绝错误输入；新构建产物也需重新绑定证据。部分 HMBIRD 项仍依赖合法取值、稳定输入及生命周期前提，涉及写入宽度或空指针读取顺序；模拟案例不能证明所有并发、访存事件和异常路径相同。这些前提随结论保留，不计作严格指令匹配。

F2FS 的范围来自实际编译的 23 个对象，包含局部函数和 trace 生成函数，共 1223 个函数实例、127080 个指令词。最终完成该固定范围的函数体、边界、静态数据及相关元数据核对，其中明确的链接转换保留说明。没有发现需要另加补丁的确定 F2FS 差距；这不覆盖整个 Linux 外部调用链，也不证明断电持久化、并发或长期写回等价。

确定的源码恢复整理成 22 封补丁，涵盖 HMBIRD 接入、生命周期、CPU 选择、超时、uclamp、shadow tick，以及 block、EROFS、swap hook、xHCI 和 stock 公钥信任等差异。完整构建后核对了 9003 个导出符号的 CRC 与属性、12258 个类型布局组、83 个 HMBIRD 原型和证书。上述检查限定兼容性与静态范围，运行结果另见[当前状态](STATUS.md)。

候选有限实测出现两类调度警告。`!migration_pending` 涉及任务在普通允许 CPU 集合外运行、恢复迁移时缺少 pending，此前的亲和性与迁移历史仍不完整。`rq->balance_callback` 的候选诊断捕获到 RT pull 回调，离线分析找到 HMBIRD 迭代器解锁与下一次取锁之间的可达窗口；正常调度出口仍会清链，现场排队者和消费顺序尚未证明。

2026-09-21 的 stock 对照已实采核实 release、notes、BTF 和配置；首轮王者两次启用、两次关闭均记录到 finished，用户确认重进大厅正常，最终息屏。首轮没有使用 probe，自然新增 1 条相同 `rq_pin_lock` callback 不变量警告。stock 报点为 `__schedule`，不同于候选的 `task_rq_lock` / HMBIRD 关闭 worker；第二轮在 probe 结束后的关闭附近另观察到两个 owner 的同条件告警，详见[当前状态](STATUS.md)。这证明该类不变量告警在 stock 也会发生，但 callback 身份及完整因果仍未知。

随后切回候选，notes、BTF 和配置实采匹配，`!migration_pending` 再次出现在文件访问检查、FUSE lookup / BPF、`migrate_enable` 路径。辅助日志仅确认一次启用和一次关闭 finished，用户反馈重进正常；这些正常操作不能消除告警。两段120秒候选 probe 均为0 hit、0 miss并已清理，但告警与 probe 的精确时间关系尚未证明，不能直接判定发生在探针间隙。stock 的有限对照及120秒 probe 尚未命中此迁移异常，第二次重进也未被 stock probe 完整覆盖。此前 class、亲和性、pending 历史和根因仍待证，既不能据此认定候选独有，也不能一并关闭两类问题；没有新增修复或隐藏警告。

22 封补丁已逐步重放并核对每一步完整源码 tree。提交 ID 包含作者、提交者及时间等信息，重新应用后可能变化；文件内容和模式按 [README](../README.md) 给出的目标 tree 核对。tree 一致仍不能代替构建身份或运行验证，有限对照也不证明全内核等价；个人原始日志和设备备份不随本说明发布。

迁移 pending 的后续专项审计补查了 stopper、迁移/setter、FUSE lookup、网络 BPF 与 RCU 包围函数，11个完整函数共1124词，1091词直接对应，31词同名调用映射，2词相同字符串地址映射。相关 metadata 另核对，pending store→load 和 migrate_disable→migrate_enable 负对照均拒绝。正常抢占可发生在 migrate_disable 自身返回之前，FUSE 后续 backing I/O 不在该次 BPF pin 区间内。新增异 rq stopper 根据临时 cpus_ptr 提前完成请求的条件链，独立阅读未发现锁序能必然排除，但尚无现场轨迹；stock 对应路径同在，不以源码可达性代替真实复现，也不据此修改官方策略。采集站点/once 顺序已经排除错选解释，下一次须补设备侧实际 arm 与时间边界，并在异常清 pending 前捕获普通 mask、临时 mask 和任务身份。此轮只有离线研究，22个补丁保持不变。
