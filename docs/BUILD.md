# 应用与编译说明

补丁应用命令见[README](../README.md)。所有22个补丁都应用在 common Git 仓库中，不应用在外层 platform 仓库。

应用后核对 `git rev-parse 'HEAD^{tree}'`，预期为 `7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`。当前候选来源提交为 `f34864787733a55f7fba20ca65eda7c674e1d43e`，提交ID不作为重放结果的相等条件。

编译使用对应官方源码、工具链和构建环境。此仓库只交付内核源码补丁，不附带构建入口修改或自动构建脚本。编译产物仍须核对配置、导出CRC、结构布局和模块信任，再做设备验证。

原研究使用 Linux 6.6.118、clang-r510928，保持 built-in HMBIRD 和 stock 配置方向。单对象检查或构建成功不等于运行行为完全相同。
