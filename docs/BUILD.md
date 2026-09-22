# 应用与编译说明

补丁应用命令见[README](../README.md)。从包含 `kernel_platform/` 的工程根目录执行，通过 `git -C kernel_platform/common` 将全部23个补丁应用到 common Git 仓库：前22个恢复stock，第23个增加SYSVIPC。

应用后核对 `git -C kernel_platform/common rev-parse 'HEAD^{tree}'`，预期为 `f50f02f8976716270ecae9c58560deabd021587a`。当前来源提交为 `83e4d6950a2d2fb62482e6391466d66fc8906370`，提交ID不作为重放结果的相等条件。前22个补丁完成时的tree仍为 `7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`。

编译使用对应官方源码、工具链和构建环境。此仓库只交付内核源码补丁，不附带构建入口修改或自动构建脚本。编译产物仍须核对配置、导出CRC、结构布局和模块信任，再做设备验证。

原研究使用 Linux 6.6.118、clang-r510928，保持 built-in HMBIRD 和 stock 配置方向。单对象检查或构建成功不等于运行行为完全相同。

包含第23个补丁的最终配置仅增加SYSVIPC及自动compat/sysctl；不要额外开启IPC_NS/PID_NS/POSIX_MQUEUE/DEVTMPFS。当前只完成配置、选定对象和布局/CRC检查，尚无这个最终版本的完整Image或boot。
