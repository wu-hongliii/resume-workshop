from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import renderers


PACKAGE_FILENAME = "简历工坊-完整演示资料包.zip"
ROOT = "简历工坊-完整演示资料包"
DEMO_NOTICE = "【演示专用】以下人物、公司、联系方式与经历均为虚构，仅用于功能演示。"


def _resume_payload(profile: dict, title: str, template: str = "ats") -> dict:
    return {
        "profile": profile,
        "resume": {
            "title": title,
            "language": "zh",
            "template": template,
            "page_mode": "one",
            "section_order": [
                "summary", "experience", "projects", "education", "skills", "certificates", "languages"
            ],
            "jd": "",
            "analysis": None,
            "suggestions": [],
            "questions": [],
        },
    }


def _same_industry_profile() -> dict:
    return {
        "basics": {
            "name": "林知远（演示专用）",
            "target_role": "AI 应用工程师",
            "phone": "138-0000-1001",
            "email": "demo.same@example.com",
            "city": "上海",
            "links": "github.com/demo-lin",
            "summary": f"{DEMO_NOTICE} 具备企业 AI 应用开发与客户交付经验，能够把业务问题拆解为可验证的技术方案。",
            "photo": "",
        },
        "experience": [
            {
                "company": "星河软件（演示公司）",
                "role": "AI 应用工程师",
                "start": "2023.07",
                "end": "至今",
                "location": "上海",
                "bullets": [
                    "参与企业知识助手的需求访谈、原型开发、评测与上线交付",
                    "将文档检索、权限过滤和答案溯源整理为可复用实施清单",
                    "与业务人员共同建立测试问题集，记录错误类型并推动迭代",
                ],
            },
            {
                "company": "云帆科技（演示公司）",
                "role": "后端开发工程师",
                "start": "2021.07",
                "end": "2023.06",
                "location": "杭州",
                "bullets": [
                    "使用 Python 与 SQL 开发内部数据服务和自动化任务",
                    "负责接口联调、异常排查和交付文档维护",
                ],
            },
        ],
        "projects": [
            {
                "name": "企业知识库问答助手（演示项目）",
                "role": "方案与交付",
                "start": "2024.03",
                "end": "2024.09",
                "technologies": "Python、RAG、FastAPI、PostgreSQL",
                "bullets": [
                    "梳理用户场景并将需求拆为数据接入、检索、回答和反馈闭环",
                    "建立包含正确性、引用完整性和拒答边界的离线评测表",
                ],
            }
        ],
        "education": [
            {"school": "东海大学（演示学校）", "degree": "本科", "major": "软件工程", "start": "2017.09", "end": "2021.06"}
        ],
        "skills": [
            {"category": "AI 应用", "items": ["RAG", "提示词设计", "评测集设计", "API 调用"]},
            {"category": "工程能力", "items": ["Python", "FastAPI", "SQL", "Git", "Docker"]},
        ],
        "certificates": [],
        "languages": ["中文：母语", "英文：可阅读技术文档"],
    }


def _career_switch_profile() -> dict:
    return {
        "basics": {
            "name": "周桥（演示专用）",
            "target_role": "桥涵设计工程师",
            "phone": "138-0000-2002",
            "email": "demo.switch@example.com",
            "city": "广州",
            "links": "github.com/demo-zhou",
            "summary": f"{DEMO_NOTICE} 具备工程设计、预算协调和技术资料整理经验，正在通过个人项目补充 AI 应用开发能力。",
            "photo": "",
        },
        "experience": [
            {
                "company": "远川工程咨询（演示公司）",
                "role": "桥涵设计工程师",
                "start": "2021.07",
                "end": "至今",
                "location": "广州",
                "bullets": [
                    "参与市政桥涵方案设计、工程量核对和技术文件编制",
                    "与道路、排水和造价专业协同处理设计接口与变更记录",
                    "整理规范条文和常见问题清单，减少重复资料查找",
                ],
            }
        ],
        "projects": [
            {
                "name": "工程规范问答助手（个人演示项目）",
                "role": "独立实践",
                "start": "2025.04",
                "end": "至今",
                "technologies": "Python、LLM API、RAG、SQLite",
                "bullets": [
                    "将公开规范样例整理为带来源标记的可检索知识片段",
                    "设计问题、答案、引用和人工复核字段，记录错误案例",
                ],
            }
        ],
        "education": [
            {"school": "南岭大学（演示学校）", "degree": "本科", "major": "土木工程", "start": "2017.09", "end": "2021.06"}
        ],
        "skills": [
            {"category": "工程设计", "items": ["桥涵设计", "工程量核对", "技术文档", "跨专业协同"]},
            {"category": "数字化实践", "items": ["Python 基础", "Excel", "LLM API", "Git 基础"]},
        ],
        "certificates": [],
        "languages": ["中文：母语", "英文：可阅读基础技术资料"],
    }


SAME_INDUSTRY_JD = f"""{DEMO_NOTICE}
目标岗位：Forward Deployed Engineer（企业 AI 应用方向）

岗位职责：
1. 深入客户业务现场，识别高价值场景并形成可交付的 AI 应用方案。
2. 使用 Python、API、RAG 等技术快速搭建原型并推动上线。
3. 建立评测、监控和反馈机制，持续改进答案质量与用户体验。
4. 与产品、算法、工程和客户团队协作，沉淀实施方法和交付文档。

任职要求：
1. 具备 Python 开发、接口联调和问题排查能力。
2. 理解大模型应用、检索增强生成和提示词设计的基本方法。
3. 能够把模糊业务问题拆解成清晰的技术任务和验收标准。
4. 具备良好的沟通、演示和文档能力，有客户交付经验者优先。
"""


CAREER_SWITCH_JD = f"""{DEMO_NOTICE}
目标岗位：初级 Forward Deployed Engineer（AI 解决方案方向）

岗位职责：
1. 协助完成业务访谈、需求梳理、方案演示和项目实施。
2. 使用 Python 和大模型 API 开发数据处理、知识问答或流程自动化原型。
3. 整理测试问题、失败案例和用户反馈，支持产品持续迭代。
4. 编写清晰的操作说明、项目文档和交付材料。

任职要求：
1. 本科及以上学历，专业不限，有工程、制造或咨询背景者欢迎申请。
2. 掌握 Python 基础，能够调用 API 并处理常见结构化数据。
3. 对 AI 应用开发有持续实践，能够展示个人项目和学习过程。
4. 逻辑清晰，愿意进入业务现场解决具体问题。
"""


def _font(size: int) -> tuple[ImageFont.ImageFont, bool]:
    candidates = (
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size), True
    return ImageFont.load_default(), False


def _jd_screenshot() -> bytes:
    font, cjk = _font(30)
    small_font, _ = _font(22)
    image = Image.new("RGB", (1500, 1120), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 42, 1452, 1076), fill="white", outline="#d7d1c4", width=3)
    draw.rectangle((48, 42, 1452, 128), fill="#173b32")
    if cjk:
        title = "演示专用｜初级 Forward Deployed Engineer"
        lines = [
            "岗位职责",
            "1. 协助业务访谈、需求梳理、方案演示和项目实施。",
            "2. 使用 Python 和大模型 API 开发知识问答或自动化原型。",
            "3. 整理测试问题、失败案例和用户反馈，支持持续迭代。",
            "4. 编写操作说明、项目文档和交付材料。",
            "任职要求",
            "1. 专业不限，有工程、制造或咨询背景者欢迎申请。",
            "2. 掌握 Python 基础，能够调用 API 并处理结构化数据。",
            "3. 能展示个人项目、学习过程和解决问题的方法。",
            "所有公司、人物与岗位信息均为虚构，仅用于 OCR 演示。",
        ]
    else:
        title = "DEMO ONLY | Junior Forward Deployed Engineer"
        lines = [
            "RESPONSIBILITIES",
            "1. Support discovery, solution demos and project delivery.",
            "2. Build prototypes with Python, LLM APIs and RAG.",
            "3. Document test questions, failures and user feedback.",
            "REQUIREMENTS",
            "1. Basic Python and API integration skills.",
            "2. Demonstrable personal projects and learning evidence.",
            "All people, companies and roles are fictional demo data.",
        ]
    draw.text((82, 67), title, font=font, fill="white")
    y = 174
    for line in lines:
        is_heading = line in {"岗位职责", "任职要求", "RESPONSIBILITIES", "REQUIREMENTS"}
        draw.text((94, y), line, font=font if is_heading else small_font, fill="#173b32" if is_heading else "#2c302d")
        y += 78 if is_heading else 70
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _template_payload() -> dict:
    profile = {
        "basics": {
            "name": "姓名（演示模板）",
            "target_role": "目标职位",
            "phone": "手机号",
            "email": "邮箱",
            "city": "城市",
            "links": "作品链接",
            "summary": "这里展示个人概述的排版位置。导入模板时，系统只提取版式倾向，不导入这些示例文字。",
            "photo": "",
        },
        "experience": [{"company": "公司名称", "role": "职位", "start": "开始时间", "end": "结束时间", "location": "地点", "bullets": ["职责与成果示例"]}],
        "projects": [{"name": "项目名称", "role": "项目角色", "start": "开始时间", "end": "结束时间", "technologies": "技术与工具", "bullets": ["项目成果示例"]}],
        "education": [{"school": "学校名称", "degree": "学历", "major": "专业", "start": "开始时间", "end": "结束时间"}],
        "skills": [{"category": "专业技能", "items": ["技能一", "技能二", "技能三"]}],
        "certificates": [],
        "languages": [],
    }
    return _resume_payload(profile, "编辑部单栏-演示模板", template="editorial")


def build_demo_package() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(
            f"{ROOT}/00-开始前请读.txt",
            f"""{DEMO_NOTICE}

这套资料用于走完简历工坊的真实操作流程，不会自动写入你的档案。

推荐顺序：
1. 先选择“同行业跳槽”或“跨行业转行”文件夹。
2. 在“导入资料”上传该文件夹中的旧简历。
3. 在“确认档案”核对姓名、经历和技能。
4. 在“岗位匹配”粘贴 JD 文本，或粘贴 JD 截图体验 OCR。
5. 选择对应求职模式，按需加入补充经历和项目证据文件夹。
6. 生成岗位简历后，在“内容编辑”修改，再到“排版导出”导入演示模板并导出 Word/PDF。

演示结束后，可使用岗位库保留版本，或使用“开始新岗位”清空当前岗位内容。所有演示信息均为虚构。
""",
        )

        same = f"{ROOT}/01-同行业跳槽-FDE"
        archive.writestr(
            f"{same}/01-旧简历-林知远-AI应用工程师-演示专用.docx",
            renderers.render_docx(_resume_payload(_same_industry_profile(), "林知远-旧简历-演示专用")),
        )
        archive.writestr(f"{same}/02-目标岗位JD-FDE-演示专用.txt", SAME_INDUSTRY_JD)
        archive.writestr(
            f"{same}/03-岗位补充经历-演示专用.txt",
            f"""{DEMO_NOTICE}
曾独立为售前同事制作一套客户演示环境，能够用非技术语言解释检索、引用和拒答边界。
在一次知识助手试点中负责收集业务问题、组织验收并整理上线后的反馈清单。
希望突出客户沟通、快速原型、问题排查和交付闭环，而不是只强调模型概念。
""",
        )
        archive.writestr(
            f"{same}/04-项目证据-企业知识助手/README.md",
            f"""# 企业知识助手（演示专用）

{DEMO_NOTICE}

目标：让售后团队能够从产品手册和常见问题中找到带出处的答案。
个人职责：需求访谈、原型搭建、测试问题整理、演示和交付文档。
技术：Python、FastAPI、向量检索、PostgreSQL。
""",
        )
        archive.writestr(
            f"{same}/04-项目证据-企业知识助手/项目复盘.md",
            "问题：早期答案缺少出处且容易混用不同产品版本。\n改进：增加产品版本过滤、引用检查和无法确认时的拒答规则。\n验收：业务人员复核固定问题集并记录失败类型。\n",
        )
        archive.writestr(
            f"{same}/04-项目证据-企业知识助手/评测记录.csv",
            "问题类型,样例数量,通过数量,主要问题\n事实问答,20,17,旧版本文档混入\n操作步骤,15,13,引用段落不完整\n越权问题,10,10,无\n",
        )

        switch = f"{ROOT}/02-跨行业转行-FDE"
        archive.writestr(
            f"{switch}/01-旧简历-周桥-桥涵设计工程师-演示专用.docx",
            renderers.render_docx(_resume_payload(_career_switch_profile(), "周桥-旧简历-演示专用")),
        )
        archive.writestr(f"{switch}/02-目标岗位JD-FDE-演示专用.txt", CAREER_SWITCH_JD)
        archive.writestr(f"{switch}/03-目标岗位JD截图-OCR演示专用.png", _jd_screenshot())
        archive.writestr(
            f"{switch}/04-岗位补充经历-演示专用.txt",
            f"""{DEMO_NOTICE}
利用周末学习 Python，并把日常规范查询整理成一个个人问答助手原型。
能够解释数据整理、问题设计、错误记录和人工复核过程，但没有正式 AI 公司任职经历。
希望保留工程行业的需求理解、严谨性和跨专业沟通优势，同时诚实呈现当前技术水平。
""",
        )
        archive.writestr(
            f"{switch}/05-项目证据-工程规范问答助手/README.md",
            f"""# 工程规范问答助手（个人演示项目）

{DEMO_NOTICE}

场景：工程人员查找桥涵规范条文时，需要快速定位来源并保留人工复核。
范围：公开样例文档、问题清单、答案引用和错误记录；不用于真实设计决策。
个人职责：需求整理、文档切分、提示词、测试表和演示页面。
""",
        )
        archive.writestr(
            f"{switch}/05-项目证据-工程规范问答助手/需求说明.md",
            "用户需要按问题定位相关条文，答案必须展示来源；无法确认时提示人工复核。\n首版只支持本地样例文档，不接入公司资料，不替代注册工程师判断。\n",
        )
        archive.writestr(
            f"{switch}/05-项目证据-工程规范问答助手/测试记录.csv",
            "编号,问题,预期,结果\n01,查询条文适用范围,回答并给出来源,通过\n02,询问样例外材料,提示资料不足,通过\n03,要求直接给出设计结论,提示人工复核,通过\n",
        )

        archive.writestr(
            f"{ROOT}/03-自定义简历模板/编辑部单栏-演示模板.docx",
            renderers.render_docx(_template_payload()),
        )
        archive.writestr(
            f"{ROOT}/04-建议录屏顺序.txt",
            "导入旧简历 → 确认档案 → 粘贴 JD 截图 → OCR 校对 → 选择跳槽/转行模式 → 选择项目证据文件夹 → 生成岗位简历 → 右侧 AI 修改 → 导入模板 → 导出 Word/PDF。\n录屏前请确认页面中没有真实姓名、手机号和 API Key。\n",
        )
    return buffer.getvalue()
