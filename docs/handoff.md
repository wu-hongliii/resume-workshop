# 简历工坊项目 Handoff

> 更新日期：2026-08-16
> 当前阶段：`v0.3.0-beta` 公开发布候选版正在收尾；多模型、本地隐私确认、非商业许可、贡献文件、双架构 macOS 与 Windows 发布流程已加入，等待完整 CI、安全审查和公开仓库发布。

## 1. 项目定位

这是一个 Windows / macOS 本地 AI 简历工作台。用户先建立一份共用的基础人才档案，再为不同 JD 生成互相独立的岗位简历。项目当前供单人自用和熟人试用，不包含注册、登录、支付或公网部署。

核心产品原则：

- 基础人才档案与岗位定制正文分离。
- 本地数据默认不离开电脑；只有用户主动调用 AI 时发送必要文本。
- 同方向跳槽优先重组真实经历；跨行业转行可生成个人/模拟项目，但不得虚构公司任职。
- 导出稳定和一页可读性优先于纯视觉效果。
- 用户可以直接编辑和手动增删模块，AI 是辅助编辑器，不是唯一入口。

## 2. 启动方式

```powershell
cd D:\Code\resume
python -m app.main
```

默认地址：`http://127.0.0.1:8877`。

也可以双击 `start.bat`。依赖见根目录 `requirements.txt`。

## 3. 技术栈与模块

- Python 3.12、FastAPI、Uvicorn。
- 原生 HTML、CSS、JavaScript，无前端构建步骤。
- SQLite 保存状态、历史版本、岗位库和设置。
- `python-docx` 解析和导出 Word。
- PyMuPDF 解析 PDF。
- RapidOCR 为主要本地 OCR，EasyOCR 为兜底。
- `app/providers.py` 适配 DeepSeek、OpenAI、Claude、MiniMax、GLM、Kimi、MiMo、Ollama、LM Studio 和自定义 OpenAI 兼容服务。
- Playwright/Chromium 将 A4 HTML 渲染为 PDF。

关键文件：

- `app/main.py`：API、请求模型、本地 Host/Origin/大小边界。
- `app/demo_package.py`：在内存中生成两条虚构演示路线、JD 截图、项目证据和可导入 Word 模板，不写本地状态。
- `app/storage.py`：SQLite、历史版本、编辑撤销/恢复、备份。
- `app/parsers.py`：DOCX、PDF、图片、XLSX、文本解析，OCR 和模板风格提取。
- `app/providers.py`：服务商目录、配置校验、OpenAI 兼容与 Anthropic Messages 适配、连接测试。
- `app/ai.py`：统一模型请求、隐私过滤、岗位生成和编辑操作。
- `app/renderers.py`：HTML、PDF、DOCX 渲染和一页可读性限制。
- `web/index.html`：五步页面结构及对话框。
- `web/app.js`：前端状态、编辑器、AI 调用、岗位库、预览和导出。
- `web/app.css`：应用和简历模板样式。
- `app/runtime.py`：源码/打包资源路径、各平台用户数据目录和内置 Chromium 路径。
- `packaging/`：PyInstaller 规格、朋友安装包依赖和 Windows Inno Setup 配置。
- `.github/workflows/package.yml`：标签触发 Windows x64 安装版/便携版与 Intel/Apple Silicon macOS DMG，并发布 SHA-256 和构建证明；手动触发只生成测试产物。
- `tests/test_core.py`：后端、存储、解析、导出和安全核心测试。
- `tests/e2e_tailored_resume.py`：岗位正文、编辑、撤销恢复、岗位库和追问流程。
- `tests/e2e_jd_clipboard.py`：JD 截图粘贴与本地 OCR 流程。
- `tests/e2e_next_optimizations.py`：折叠工具卡、文件夹选择、学习路径和模板入口。
- `tests/e2e_visual_layout.py`：五步页面、设置与岗位库的桌面/平板/手机布局回归，不连接真实用户状态。
- `tests/e2e_onboarding.py`：七步首次引导、完整演示资料包下载、无状态写入、功能跳转、完成记忆、帮助入口和手机布局回归。
- `tests/e2e_smoke.py`：会真实导入和导出，只允许显式指向使用隔离数据库的测试服务，不得连接默认真实服务。

## 4. 数据模型与安全边界

真实数据位于 `data/resume.db`。`data/` 和 `exports/` 都不应进入版本控制，也不得在调试、测试或重构时清空。

状态的关键层级：

- `profile`：共用基础人才档案。
- `resume`：当前岗位工作区，包括 JD、分析、定制正文、语言、模板、页数、问答等。
- `resume.tailored_profile`：当前岗位真正用于编辑、预览和导出的正文。
- `resume_library`：保存的岗位版本，每项保存独立 `resume` 快照。
- `active_resume_id`：当前打开的岗位库条目。

必须保持的安全不变量：

1. 岗位 AI 生成、编辑、翻译和追问不得回写 `profile`。
2. 切换或新建岗位后，旧的异步 AI 响应不得写入新岗位。
3. 状态保存必须串行，避免较早请求覆盖较新内容。
4. 修改真实数据库或迁移 schema 前先建立可恢复备份，并在操作前后比较数据摘要。
5. 发给 AI 的档案应过滤姓名、电话、邮箱、城市、链接、照片和经历地点。
6. 服务保持只监听 `127.0.0.1`，并保留 Host、Origin 和请求体大小校验。
7. 每个服务商的 API Key 使用独立的系统当前账户安全存储：Windows 为 DPAPI，macOS 为“钥匙串”；备份中不包含 Key。
8. 源码运行继续使用项目内 `data/`；打包后的 Windows 数据位于 `%LOCALAPPDATA%\ResumeWorkshop`，macOS 数据位于 `~/Library/Application Support/ResumeWorkshop`，程序升级/卸载不主动删除用户资料。

## 5. 当前实现的用户流程

1. 多选、拖拽或粘贴方式导入 DOCX、PDF、扫描件和图片。
2. 展示解析原文与结构化基础档案，用户人工确认。
3. 粘贴 JD 文本，或在 JD 文本框粘贴多张截图；逐张本地 OCR 后由 AI 校对，保留原文、校对版、修改记录和撤销入口。
4. 生成匹配分析；分数由 JD 要求和档案证据确定性计算，模型只负责拆解要求和解释。
5. 选择同方向/跨行业模式及小白、入门、熟练、精通层级。
6. 生成完整岗位正文；跨行业模式可生成个人项目、模拟项目和技能。
7. 用户直接编辑、手动增删模块，或使用右侧 AI 修改字段、选中文字、智能新增或调整整份简历。
8. AI 修改支持撤销和恢复；动态追问支持跳过、结束、上一问和下一问。
9. 可从代码、工程资料、研究报告、金融复盘、文章等文件夹分批提取事实，自动识别九类材料并显示原文依据；用户可改类型重整，确认后再加入补充信息。
10. 跨行业模式可基于匹配差距拆解学习任务；默认使用本地课程目录，也可配置 Brave/Tavily 实时发现任意职业的具体课程页，再进行语义复核、30天本地缓存和本地用户反馈。
11. 中文、英文、中英混排，三套内置模板或导入式自定义模板，模块排序，一页或多页。
12. PDF、Word 和 Ctrl+P 备用导出。
13. 当前岗位可保存到岗位库；新建岗位只清空岗位工作区，不清空基础档案。
14. 历史版本最多 100 个，备份恢复去重并在恢复前保存真实当前状态。

## 6. 关键设计决定

### 为什么不是 Canva 式自由拖拽

第一版采用模块化编辑，降低复杂度并保持 PDF、Word 和 ATS 解析稳定。当前自由度来自文字编辑、模块顺序、模板、页数以及模块增删。

### 为什么保留基础档案和岗位正文两层

基础档案是长期事实源；岗位正文允许筛选、重写和生成模拟项目。混为一层会导致为某个岗位生成的内容污染以后所有岗位。

### 为什么跨行业模式允许生成项目

用户希望转行时可以根据 JD 快速获得可修改的个人/模拟项目草稿，但明确不生成虚构公司任职。生成项目的 role 必须标注“个人项目”“模拟项目”或“案例研究”。

### 为什么限制一页缩放

自动缩放低于 75% 会造成字号过小。后端 PDF 渲染会拒绝这种导出，前端也会提示用户精简或切换多页。

## 7. 验证命令

在项目根目录运行：

```powershell
node --check web/app.js
python -m compileall -q app
python -m unittest discover -s tests -p "test_core.py"
python tests/e2e_tailored_resume.py
python tests/e2e_jd_clipboard.py
python tests/e2e_next_optimizations.py
python tests/e2e_visual_layout.py
python tests/e2e_onboarding.py
python -m pip check
```

截至 2026-08-16：

- 49 项核心测试通过，覆盖演示资料包、服务商配置隔离、Anthropic 协议适配、更新检查、解析、渲染和安全边界。
- 五项不写真实状态的 Playwright 端到端测试通过。
- JavaScript/Python 语法检查通过。
- `.github/workflows/ci.yml` 已配置远端 CI：PR 到 `main`、推送 `main` 或手动触发时，运行语法检查、依赖检查、核心测试和五项不写真实状态的 Playwright 回归；会显式排除 `e2e_smoke.py`。
- `.github/workflows/package.yml` 在 `v*` 标签和手动操作时运行：使用 Windows x64、`macos-15-intel` 与 `macos-15`（arm64）runner 做成品健康检查；标签构建会创建 GitHub Release、SHA-256 和 artifact attestation。
- 端到端测试报告 `user_data_writes=0`。

测试真实数据安全时，必须比较 `data/resume.db` 操作前后的 SHA-256；不要把测试指向真实数据库。
`tests/e2e_smoke.py` 会导入测试文件并修改隔离档案，必须同时设置隔离服务地址和 `RESUME_E2E_ALLOW_STATE_WRITES=1` 才能运行。

## 8. 已知限制与风险

- 还没有用足够多的真实扫描简历做 OCR 质量基准，复杂表格、多栏和低清图片仍可能识别错误。
- AI JSON 输出已做容错，但模型连续截断或返回非结构化内容时仍可能失败。
- 服务商默认模型和端点会变化；更新 `app/providers.py` 时必须同时更新连接测试、用户指南和协议级测试。非 DeepSeek 云端适配尚未使用维护者真实 Key 全量验证，界面必须保留诚实提示。
- Word 是独立稳定渲染，不可能与浏览器/PDF 像素级一致；不同字体环境可能重新分页。
- 一页预览依赖前端测量，最终 PDF 还有后端 75% 可读性门禁作为兜底。
- 当前没有用户账户、应用解锁密码、多人隔离、配额、审计日志或公网安全设计，不能直接当作 SaaS 发布。
- 自定义模板是受约束的风格重建，不是任意元素级复刻；图片模板的结构识别仍需更多样本验证。
- 文件夹分析会从最多 300 个候选文件中优先选择说明、设计、核心内容和测试，最终最多读取 40 个白名单文件、约12万字、单文件 5 MB；旧版 `.doc`、`.xls` 和复杂二进制项目文件不在支持范围。证据定位目前到文件与原文摘录，尚未保留 Word 页码。
- 学习资源默认使用本地目录；任意职业覆盖依赖用户自行配置 Brave Search 或 Tavily API Key。课程检索可能受配额、索引和平台下架影响，系统会拒绝搜索页并在无可靠结果时明确提示。
- 网页静态资源响应使用 `Cache-Control: no-store`，避免更新后 HTML 与旧 JS/CSS 混用。

## 9. 推荐的下一步

优先级从高到低：

1. 使用一份真实或脱敏旧简历和真实 JD 完成完整人工验收。
2. 建立多截图 JD OCR 样本集，记录自动校对前后的字段级错误率与误改率。
3. 用 10 个 Word/PDF/图片模板评估主色、单双栏和导出相似度。
4. 用代码项目和普通工作资料各做案例草稿验收，重点检查证据与不确定项。
5. 对 AI 生成做案例评测：同方向相关性、转行项目可解释性、去 AI 味和重复率。
6. 使用不同长度简历验证内置/自定义模板的一页、多页和 Word/PDF 稳定性。
7. 根据公开测试反馈再决定是否增加英文界面、更多模板、Apple Developer ID 签名/公证和多模态 OCR 兜底；Apple Silicon 安装包已进入标签发布矩阵。
8. 如果准备对外发布，先使用 `security-threat-model` 做完整威胁建模，再设计认证、多用户隔离、密钥管理、速率限制和隐私协议。

## 10. 接手注意事项

- 先阅读根目录 `AGENTS.md`、`README.md`、本文件和 `docs/architecture.md`。
- 开始修改前确认本地服务和真实数据库状态，不要用示例状态覆盖现有资料。
- 修 bug 时先补能复现问题的测试，再做最小修改。
- 修改 AI schema 时同步检查 `assemble_targeted_profile`、前端编辑器、渲染器和备份兼容性。
- 修改状态结构时考虑旧 SQLite 状态和旧备份包，避免只支持新建空数据。
- 交付前复跑全部门禁，并通过 `neat-freak` 对齐代码、README、架构、用户指南和 handoff。
