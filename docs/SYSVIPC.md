# SYSVIPC 增量

第23个补丁在已恢复stock的f348基线上开启System V IPC，包括共享内存、信号量和
消息队列。只有`arch/arm64/configs/gki_defconfig`和`include/linux/sched.h`改变。

采用cctv的reserve6/7/8方案：原task_struct中间位置的sysvsem/sysvshm移到预留空间，
sysvsem占reserve6，sysvshm占reserve7/8。不添加额外KABI条件，避免开启SYSVIPC
时移动fs/files等既有成员。这些位置保存管理字段，不限制应用共享内存的容量。

实际配置相对stock只增加：

```text
CONFIG_SYSVIPC=y
CONFIG_SYSVIPC_COMPAT=y
CONFIG_SYSVIPC_SYSCTL=y
```

后两项由已有compat/sysctl配置自动启用。IPC_NS、PID_NS、POSIX_MQUEUE、DEVTMPFS
保持关闭；不包含NTSYNC、EVDI或其它DroidSpaces扩展。

clang-r510928的21个指定ARM64对象目标检查通过。SYSVIPC=n/y的task_struct均为
4800字节，原218个字段保持；fs/files/io_uring/nsproxy/signal/sighand偏移分别为
2136/2144/2152/2160/2168/2176。其它七个选定结构n/y相同；所检1945个导出CRC
相同，module_layout为0x4e276f37。savedefconfig与提交配置逐字节一致。

来源提交83e4d6950，补丁SHA256为
`08eceeebac0bf31863a0acfbde4cce689ced4856da72b3ec82be8e953d987e92`。
全部23个补丁从e1b346b6逐步重放，最终tree为
`f50f02f8976716270ecae9c58560deabd021587a`，与当前源码完全相同。

当前最终版本尚未完整编译或上机。此前PostgreSQL运行成功来自包含额外容器配置的
实验版本，不能直接记成本提交的运行验收。旧实验镜像不随本仓库发布。
