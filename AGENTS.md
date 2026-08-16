# 简历工坊项目规则

## 项目定位

Windows / macOS 本机运行的浏览器式 AI 简历工作台；基础人才档案、岗位版本和历史数据默认只保存在本机。

## 启动与验证

- 启动：`python -m app.main`，访问 `http://127.0.0.1:8877`。
- 核心测试：`python tests/test_core.py`。
- 浏览器回归：`python tests/e2e_tailored_resume.py`、`python tests/e2e_jd_clipboard.py`、`python tests/e2e_next_optimizations.py`、`python tests/e2e_visual_layout.py` 和 `python tests/e2e_onboarding.py`。
- 前端语法：`node --check web/app.js`；后端语法：`python -m compileall -q app`。

## 技术栈与目录

- `app/`：FastAPI、SQLite、OCR、多服务商 AI 调用和 PDF/Word 渲染。
- `web/`：原生 HTML/CSS/JavaScript 界面。
- `tests/`：核心与 Playwright 端到端测试。
- `docs/`：需求和架构现役说明。
- `data/`：真实本地资料；`exports/`：导出与安全备份，两者都不是源码。

## 修改约定

- 不删除、重置或覆盖 `data/`、`exports/` 及用户已填写的状态；涉及迁移前先做可恢复备份并核对状态摘要。
- 不得把会写状态的 `tests/e2e_smoke.py` 指向真实服务；它只允许在显式授权写入的隔离测试服务上运行。
- 基础人才档案与岗位定制正文必须分离；岗位 AI 操作不得回写基础档案。
- 生成个人/模拟项目只用于跨行业模式，不得虚构公司任职、学历、证书或精确业绩。
- 保持本地服务只监听 `127.0.0.1`，并保留 Host、Origin、请求大小和 AI 隐私过滤边界。
- 改动应保持小而可验证；只更新与当前任务直接相关的代码和文档。

## 当前状态

本地闭环、模板导入、JD OCR 校对、文件夹案例草稿、转行学习路径、七步新手引导、完整演示资料包和朋友试用安装包已可运行。`v0.3.0-beta` 公开发布候选版支持多服务商 AI；Windows x64、Intel macOS 与 Apple Silicon macOS 包由标签触发的 GitHub Actions 构建。后续优先使用真实或脱敏材料验收 OCR 误改率、模板相似度、案例证据、AI 内容质量和 Word/PDF 跨环境稳定性。
