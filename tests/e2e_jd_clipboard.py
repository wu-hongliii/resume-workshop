import os
import re

from playwright.sync_api import Route, expect, sync_playwright


BASE_URL = os.environ.get("RESUME_TEST_URL", "http://127.0.0.1:8877")

EMPTY_STATE = {
    "profile": {
        "basics": {"name": "", "target_role": "", "phone": "", "email": "", "city": "", "links": "", "summary": "", "photo": ""},
        "experience": [], "projects": [], "education": [], "skills": [], "certificates": [], "languages": [],
    },
    "resume": {
        "title": "Clipboard Test", "language": "zh", "template": "ats", "page_mode": "one",
        "section_order": ["summary", "experience", "projects", "education", "skills", "certificates", "languages"],
        "jd": "", "analysis": None, "suggestions": [], "questions": [],
    },
}


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("localStorage.setItem('resume-workshop:onboarding:v2', 'done'); localStorage.setItem('resume-workshop:terms:v1', 'accepted'); localStorage.setItem('resume-workshop:ai-consent:deepseek:https://api.deepseek.com:v1', 'accepted')")

        page.route("**/api/state", lambda route: route.fulfill(json=EMPTY_STATE if route.request.method == "GET" else {"ok": True}))
        page.route("**/api/settings", lambda route: route.fulfill(json={"configured": False, "masked": "", "ai_provider": "deepseek", "ai_provider_name": "DeepSeek", "ai_base_url": "https://api.deepseek.com", "ai_model": "deepseek-v4-flash", "ai_ready": False, "ai_providers": [{"id": "deepseek", "name": "DeepSeek", "default_base_url": "https://api.deepseek.com", "default_model": "deepseek-v4-flash", "key_required": True, "live_tested": True}], "search_configured": False, "search_provider": "", "search_masked": ""}))
        page.route("**/api/preview", lambda route: route.fulfill(content_type="text/html", body="<html><body></body></html>"))

        def import_handler(route: Route) -> None:
            route.fulfill(json={"filename": "clipboard-jd.png", "text": "AI Engineer JD Python RAG", "used_ocr": True})

        page.route("**/api/import**", import_handler)
        page.route("**/api/ai/correct-ocr", lambda route: route.fulfill(json={
            "corrected_text": "【截图 1】\nAI Engineer JD Python RAG（已校对）",
            "corrections": [{"index": 1, "original": "AI Engineer", "corrected": "AI Engineer", "reason": "专有名词保留"}],
        }))
        page.goto(BASE_URL, wait_until="networkidle")
        page.locator('[data-step="match"]').click()
        page.evaluate(
            """() => {
                const data = new DataTransfer();
                data.items.add(new File([new Uint8Array([137, 80, 78, 71])], 'jd.png', {type: 'image/png'}));
                const event = new ClipboardEvent('paste', {clipboardData: data, bubbles: true, cancelable: true});
                document.querySelector('#jdText').dispatchEvent(event);
            }"""
        )
        expect(page.locator("#jdText")).to_have_value(re.compile("已校对"))
        assert "自动校对 1 张截图" in page.locator("#jdPasteStatus").text_content()
        assert page.locator("#jdOcrAudit").is_visible()
        page.locator("#undoJdCorrectionBtn").click()
        assert "已校对" not in page.locator("#jdText").input_value()
        assert "AI Engineer JD Python RAG" in page.locator("#jdText").input_value()
        browser.close()
    print("clipboard_image_to_jd=OK; user_data_writes=0")


if __name__ == "__main__":
    main()
