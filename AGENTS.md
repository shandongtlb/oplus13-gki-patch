# 仓库约定

- 本仓库保存 Markdown 说明、`source/patches/` 的22个stock common恢复补丁和选定的离线分析脚本。
- 先读 README.md 和 docs/STATUS.md。基线为 e1b346b6，目标源码tree为7a1b84dc67bb56ccb8a39cadca40e01a44d8abbd。
- 保持 stock 行为、ABI 和 built-in HMBIRD；不加入性能优化、SYSVIPC或构建入口补丁。
- 新版本需要单独核对，不强行套用。有限静态与真机结果不等于全内核等价。
- 不删除本地文件。被忽略的实验、脚本、证据和产物留在本地。
- 不自动编译、刷写或重启。修改及验证结果写入文档。
- 脚本输入和输出放在被忽略的 `local/` 中；按明确文件名放行脚本，不提交原始手机日志或镜像。
