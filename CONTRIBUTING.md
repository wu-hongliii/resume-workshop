# 参与贡献

感谢你帮助改进简历工坊。提交代码前请先阅读 [LICENSE](LICENSE)、[CLA.md](CLA.md) 和 [SECURITY.md](SECURITY.md)。

## 推荐流程

1. 先搜索已有 Issue；较大的功能请先开 Issue 说明目标和交互效果。
2. 从 `main` 创建功能分支，保持改动单一、可验证。
3. 不要提交真实简历、API Key、收款信息副本、`data/`、`exports/` 或构建产物。
4. 运行本地检查：

```powershell
python -m compileall -q app
node --check web/app.js
python -m unittest discover -s tests -p "test_core.py"
```

5. 提交 Pull Request，完整填写测试结果、隐私影响和截图（如涉及 UI）。

提交 PR 即表示你同意 [CLA.md](CLA.md)。贡献者保留著作权，同时允许项目作者整合、发布和再许可贡献。

## 内容安全边界

- 基础人才档案与岗位定制正文必须保持分离。
- 不得新增虚构公司任职、学历、证书或精确业绩的默认行为。
- API Key 必须只保存在本机安全存储，不得进入日志、备份、截图或测试夹具。
- 本地服务继续只监听 `127.0.0.1`，不得削弱 Host、Origin、请求大小或 AI 隐私过滤边界。

安全问题不要公开提交 Issue，请按 [SECURITY.md](SECURITY.md) 私下报告。
