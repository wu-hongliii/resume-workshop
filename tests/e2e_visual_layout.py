import json
import os
from copy import deepcopy
from pathlib import Path

from playwright.sync_api import sync_playwright

from e2e_tailored_resume import BASE_STATE


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "exports" / "e2e" / "visual-layout"
BASE_URL = os.environ.get("RESUME_TEST_URL", "http://127.0.0.1:8877")


def representative_state() -> dict:
    state = deepcopy(BASE_STATE)
    state["profile"]["basics"].update({
        "name": "吴某某",
        "target_role": "Forward Deployed Engineer（AI Agent 方向）",
        "summary": "具备工程项目交付与跨团队沟通经验，正在将 Python、AI Agent 和业务流程自动化能力用于客户现场问题解决。",
    })
    state["profile"]["experience"] = [
        {
            "company": "某工程技术公司",
            "role": "项目工程师",
            "start": "2022.07",
            "end": "2025.02",
            "location": "广州",
            "bullets": ["协调设计、施工与业主需求，推进问题闭环", "整理项目数据并形成可复用的交付文档"],
        }
    ]
    state["profile"]["projects"] = [
        {
            "name": "本地 AI 简历工作台",
            "role": "个人项目",
            "start": "2026.06",
            "end": "至今",
            "technologies": "Python、FastAPI、DeepSeek API、Playwright",
            "bullets": ["设计从资料解析、JD 匹配到 Word/PDF 导出的完整流程", "通过真实用户反馈迭代 OCR 校验、岗位版本与 AI 协同编辑"],
        },
        {
            "name": "工程资料问答 Agent",
            "role": "个人项目",
            "start": "2026.05",
            "end": "2026.06",
            "technologies": "Python、RAG、SQLite",
            "bullets": ["将项目文档整理为可检索知识库", "为常见业务问题提供带出处的答案草稿"],
        },
    ]
    state["profile"]["skills"] = [
        {"category": "AI 与开发", "items": ["Python", "FastAPI", "大模型 API", "RAG", "Playwright"]},
        {"category": "交付能力", "items": ["需求澄清", "方案表达", "跨团队协作", "问题闭环"]},
    ]
    state["resume"].update({
        "title": "FDE 岗位定制简历",
        "jd": "负责客户现场 AI 方案落地，要求 Python、LLM 应用开发、需求分析和跨团队沟通能力。",
        "analysis": {
            "score": 72,
            "summary": "工程交付和沟通经验可迁移，需补强 AI 应用开发的项目证据。",
            "strengths": ["工程项目交付经验", "跨团队沟通与问题闭环"],
            "gaps": ["企业级 LLM 应用经验", "系统化 Python 工程能力"],
            "keywords": ["Python", "LLM", "客户交付"],
            "suggestions": ["补充可演示的 AI Agent 项目", "量化项目交付过程"],
            "requirements": [],
        },
        "tailored_profile": deepcopy(state["profile"]),
        "tailored_jd": "负责客户现场 AI 方案落地",
        "generation_mode": "career_switch",
        "proficiency_level": "beginner",
        "related_experience": "已搭建本地 AI 工具，并持续根据实际使用反馈迭代。",
    })
    return state


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    state = representative_state()
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.add_init_script("localStorage.removeItem('resume-workshop:terms:v1'); localStorage.setItem('resume-workshop:onboarding:v2', 'done'); localStorage.setItem('resume-workshop:ai-consent:deepseek:https://api.deepseek.com:v1', 'accepted')")
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: console_errors.append(str(error)))

        page.route("**/api/state", lambda route: route.fulfill(json=state if route.request.method == "GET" else {"ok": True}))
        page.route("**/api/settings", lambda route: route.fulfill(json={"configured": False, "masked": "", "ai_provider": "deepseek", "ai_provider_name": "DeepSeek", "ai_base_url": "https://api.deepseek.com", "ai_model": "deepseek-v4-flash", "ai_ready": False, "ai_providers": [{"id": "deepseek", "name": "DeepSeek", "default_base_url": "https://api.deepseek.com", "default_model": "deepseek-v4-flash", "key_required": True, "live_tested": True}], "search_configured": False, "search_provider": "", "search_masked": ""}))
        page.route("**/api/edit-history", lambda route: route.fulfill(json={"undo": None, "redo": None}))
        page.route("**/api/preview", lambda route: route.fulfill(content_type="text/html", body="<html><body style='margin:0;background:white'></body></html>"))
        page.route("**/api/versions**", lambda route: route.fulfill(status=200, content_type="application/json", body="[]"))

        page.goto(BASE_URL, wait_until="networkidle")
        page.locator("#termsDialog").wait_for(state="visible")
        page.screenshot(path=OUTPUT / "1440-terms.png", full_page=True)
        page.locator("#acceptTermsBtn").click()
        page.locator("#rawText").fill("用于检查输入框、说明文字和按钮的对齐关系。")

        for step in ("import", "profile", "match", "polish", "design"):
            page.locator(f'[data-step="{step}"]').click()
            page.wait_for_timeout(250)
            if step == "match":
                page.locator(".project-folder-card > summary").click()
                page.locator("#learningPathCard").evaluate("element => element.classList.remove('hidden')")
                page.locator("#learningPathCard > summary").click()
            page.screenshot(path=OUTPUT / f"1440-{step}.png", full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"), step

        page.locator("#settingsBtn").click()
        page.screenshot(path=OUTPUT / "1440-settings.png", full_page=True)
        page.locator("#settingsDialog .icon-button").click()
        page.locator("#aboutBtn").click()
        page.locator(".support-qr-grid img").first.wait_for(state="visible")
        assert page.locator(".support-qr-grid img").evaluate_all("images => images.every(image => image.complete && image.naturalWidth > 0)")
        page.screenshot(path=OUTPUT / "1440-about.png", full_page=True)
        page.locator("#closeAboutBtn").click()
        page.locator("#resumeLibraryBtn").click()
        page.screenshot(path=OUTPUT / "1440-library.png", full_page=True)
        page.locator("#resumeLibraryDialog .icon-button").click()

        for width in (1180, 980, 800, 768, 760, 375):
            page.set_viewport_size({"width": width, "height": 900})
            for step in ("import", "profile", "match", "polish", "design"):
                page.locator(f'[data-step="{step}"]').click()
                page.wait_for_timeout(150)
                if step in ("polish", "design"):
                    page.screenshot(path=OUTPUT / f"{width}-{step}.png", full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"), f"{width}-{step}"

        page.locator("#aboutBtn").click()
        page.screenshot(path=OUTPUT / "375-about.png", full_page=True)
        about_box = page.locator(".about-card").bounding_box()
        assert about_box and about_box["width"] <= 375
        page.locator("#closeAboutBtn").click()

        browser.close()

    if console_errors:
        raise AssertionError("Browser errors: " + " | ".join(console_errors))
    print(json.dumps({"screenshots": 21, "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
