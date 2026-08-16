# 简历工坊 · Local Resume Studio

> 本地优先的 AI 岗位简历工作台：从旧简历建立基础档案，再根据目标 JD 生成、编辑、排版并导出岗位版本。

[English README](README.en.md) · [用户指南](docs/user-guide.md) · [隐私说明](PRIVACY.md) · [安全政策](SECURITY.md)

## 它能做什么

- 导入 DOCX、PDF、扫描件或多张图片，先展示解析结果再确认基础人才档案；
- 粘贴文字或截图识别 JD，保留 OCR 原文、自动校对结果和修改记录；
- 支持同方向跳槽与跨行业转行两种生成方式；
- 根据 JD 与个人材料生成独立的岗位简历正文，不覆盖基础档案；
- 手动增删模块、局部 AI 修改、全文调整、动态追问、撤销与恢复；
- 从本地项目文件夹整理可追溯的项目案例草稿；
- 生成转行学习路径并按需搜索具体免费课程；
- 导入 Word、PDF 或图片模板，实时预览并导出 Word / PDF；
- 保存多个岗位版本、历史快照和不含 API Key 的本地备份。

## AI 服务

设置中可选择 DeepSeek、OpenAI、Anthropic Claude、MiniMax、GLM、Kimi、MiMo、Ollama、LM Studio 或自定义 OpenAI 兼容接口。DeepSeek 为默认云端服务；Ollama 与 LM Studio 可用于本机模型。

各服务商的 API Key 由用户自行申请，并按服务商分别保存在当前电脑，不进入备份、仓库或简历内容。由于维护者没有所有服务的真实 Key，非 DeepSeek 云端适配主要通过协议测试验证；请使用设置中的“测试连接”确认自己的账号、模型和区域端点。

## 快速开始

### 下载成品

从 [GitHub Releases](https://github.com/wu-hongliii/resume-workshop/releases) 下载 Windows x64 安装版/便携版，或 macOS 对应架构版本。当前安装包未进行付费代码签名，系统可能显示未知开发者提示；请只从本仓库下载并核对 SHA-256。

### 从源码运行

需要 Python 3.12：

```powershell
python -m pip install -r requirements.txt
python -m app.main
```

浏览器会自动打开 `http://127.0.0.1:8877`。Windows 也可双击 `start.bat`。

如需运行浏览器测试：

```powershell
python -m playwright install chromium
```

## 隐私与内容边界

档案、岗位版本和历史默认保存在本机。只有用户主动使用云端 AI、OCR 文字校对或课程搜索时，才会发送完成当前操作所需的内容；本项目不采集遥测或崩溃报告。详见 [PRIVACY.md](PRIVACY.md)。

AI 与 OCR 可能出错。请在投递前核对全部内容，不要虚构可核验的公司任职、学历、证书或精确业绩。个人与模拟项目应确保自己能够解释。

## 许可

本项目是**源码公开（source-available）**，不是 OSI 认可的开源软件。个人、学习、求职和公司内部免费使用；禁止未经授权的商业销售、收费打包、收费简历/培训/招聘服务以及付费托管服务。修改版免费分发时必须更名、标注非官方、保留署名，并按相同条款公开完整源代码。

完整约束以中文 [LICENSE](LICENSE) 为准。商业授权：`2725275630@qq.com`。

## 贡献与反馈

- 功能建议和普通问题：提交 GitHub Issue；
- 代码贡献：阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CLA.md](CLA.md) 后提交 Pull Request；
- 安全漏洞：不要公开披露，请按 [SECURITY.md](SECURITY.md) 发送邮件；
- 作者支持：软件“关于”页提供完全自愿的微信/支付宝入口，支持与否不影响任何功能。

## 开发验证

```powershell
python -m compileall -q app
node --check web/app.js
python -m unittest discover -s tests -p "test_core.py"
python tests/e2e_onboarding.py
python tests/e2e_visual_layout.py
```

架构与接手说明见 [docs/architecture.md](docs/architecture.md) 和 [docs/handoff.md](docs/handoff.md)。
