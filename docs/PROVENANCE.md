# 来源与复现边界

- 官方源码：[OnePlusOSS/android_kernel_common_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750)。
- common基线：`e1b346b6b4f4096eb342ae3684838a942fd6f6c4`。
- 官方HMBIRD回退提交：`c7bef25f9416d6a0f87ce551be9c25729f7dae6c`。
- 旧版HMBIRD源码基线：其父提交 `f2223b938963c24e8ad9ac2e4491c8bb718e3eb5`。
- 22个恢复提交的最终来源：`f34864787733a55f7fba20ca65eda7c674e1d43e`。
- 前22个恢复补丁的tree：`7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd`。
- 第23个SYSVIPC提交：`83e4d6950a2d2fb62482e6391466d66fc8906370`。
- 全部23个补丁的重放目标tree：`f50f02f8976716270ecae9c58560deabd021587a`。
- SYSVIPC布局来源：[cctv reserve6/7/8补丁](https://github.com/cctv18/oppo_oplus_realme_sm8750/blob/4eec6347fa5d0b3495dbeca3e34eccbfbadf500b/droidspaces_patch/fix_sysvipc_kabi_6_7_8.patch)，仅调整上下文及空白以适配本基线；没有额外KABI条件。

从已有官方HMBIRD源码出发，以stock raw BTF、Image符号、ARM64机器码和候选编译结果交叉核对。版本迭代和开源回退必须分别分析，不能把所有差异直接称为私有修改。

补丁保留原有版权和SPDX声明，遵循对应上游文件的许可证。第18个补丁包含的是stock模块验证所需的公钥证书，不是私钥。部分提交说明引用本地研究归档；那些原始二进制证据及手机日志不随本仓库发布。

本仓库与厂商无官方隶属关系；公开的是当前复原源码，不是官方签名镜像，也不保证任意新版本或设备兼容。
