import os
import re
from copy import deepcopy

from playwright.sync_api import expect, sync_playwright


BASE_URL = os.environ.get("RESUME_TEST_URL", "http://127.0.0.1:8877")

BASE_STATE = {
    "profile": {
        "basics": {"name": "Base Candidate", "target_role": "Engineer", "phone": "13800000000", "email": "base@example.com", "city": "Shanghai", "links": "github.com/base", "summary": "Base summary", "photo": ""},
        "experience": [{"company": "Base Co", "role": "Engineer", "start": "2024", "end": "Present", "location": "Shanghai", "bullets": ["Built applications"]}],
        "projects": [], "education": [], "skills": [{"category": "Tech", "items": ["Python"]}], "certificates": [], "languages": [],
    },
    "resume": {
        "title": "Target Test", "language": "zh", "template": "ats", "page_mode": "one",
        "section_order": ["summary", "experience", "projects", "education", "skills", "certificates", "languages"],
        "jd": "", "analysis": None, "tailored_profile": None, "tailored_jd": "", "generation_mode": "same_direction", "proficiency_level": "beginner", "candidate_drafts": [], "suggestions": [], "questions": [],
    },
    "resume_library": [],
    "active_resume_id": None,
}


def main() -> None:
    saved_payloads = []
    generate_requests = []
    refine_requests = []
    selection_edit_requests = []
    smart_add_requests = []
    generated = deepcopy(BASE_STATE["profile"])
    generated["basics"] = {**generated["basics"], "name": "Model Changed Name", "phone": "000", "target_role": "FDE", "summary": "Targeted FDE delivery summary"}
    generated["experience"][0]["bullets"] = ["Delivered applications for enterprise clients"]
    generated["projects"] = [{"name": "FDE Solution Lab", "role": "个人项目", "start": "", "end": "", "technologies": "Python", "bullets": ["Built a customer delivery simulation"]}]
    question_calls = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("localStorage.setItem('resume-workshop:onboarding:v2', 'done'); localStorage.setItem('resume-workshop:terms:v1', 'accepted'); localStorage.setItem('resume-workshop:ai-consent:deepseek:https://api.deepseek.com:v1', 'accepted')")

        def state_route(route):
            if route.request.method == "GET":
                route.fulfill(json=BASE_STATE)
            else:
                saved_payloads.append(route.request.post_data_json["payload"])
                route.fulfill(json={"ok": True})

        page.route("**/api/state", state_route)
        page.route("**/api/settings", lambda route: route.fulfill(json={"configured": False, "masked": "", "ai_provider": "deepseek", "ai_provider_name": "DeepSeek", "ai_base_url": "https://api.deepseek.com", "ai_model": "deepseek-v4-flash", "ai_ready": False, "ai_providers": [{"id": "deepseek", "name": "DeepSeek", "default_base_url": "https://api.deepseek.com", "default_model": "deepseek-v4-flash", "key_required": True, "live_tested": True}], "search_configured": False, "search_provider": "", "search_masked": ""}))
        page.route("**/api/edit-history", lambda route: route.fulfill(json={"undo": None, "redo": None}))
        page.route("**/api/preview", lambda route: route.fulfill(content_type="text/html", body="<html><body></body></html>"))
        def generate_route(route):
            generate_requests.append(route.request.post_data_json)
            route.fulfill(json={"profile": generated})

        def question_route(route):
            nonlocal question_calls
            question_calls += 1
            questions = [
                {"done": False, "question": "What did you validate?", "why": "Adds concrete evidence"},
                {"done": False, "question": "How did you iterate?", "why": "Shows the working method"},
            ]
            route.fulfill(json=questions[question_calls - 1] if question_calls <= len(questions) else {"done": True, "question": "", "why": ""})

        refined = deepcopy(generated)
        refined["projects"][0]["bullets"].append("Validated the workflow with representative cases")

        def refine_route(route):
            refine_requests.append(route.request.post_data_json)
            changes = [] if len(refine_requests) == 3 else [{"path": "projects.0.bullets", "label": "项目经历第 1 项"}]
            route.fulfill(json={"profile": refined, "changes": changes})

        page.route("**/api/ai/generate", generate_route)
        page.route("**/api/ai/question", question_route)
        page.route("**/api/ai/refine", refine_route)
        def selection_edit_route(route):
            selection_edit_requests.append(route.request.post_data_json)
            route.fulfill(json={"replacement_text": "enterprise AI delivery"})

        page.route("**/api/ai/edit-selection", selection_edit_route)
        smart_added = deepcopy(generated)
        smart_added["projects"][0]["bullets"].append("Built TongdaXin stock and sector RPS indicators for review and selection")
        smart_added["skills"].append({"category": "Trading tools", "items": ["TongdaXin", "RPS indicators"]})

        def smart_add_route(route):
            smart_add_requests.append(route.request.post_data_json)
            route.fulfill(json={"profile": smart_added, "changes": [
                {"path": "projects.0.bullets", "label": "项目经历第 1 项"},
                {"path": "skills", "label": "专业技能"},
            ]})

        page.route("**/api/ai/add-content", smart_add_route)
        page.goto(BASE_URL, wait_until="networkidle")
        page.locator('[data-step="match"]').click()
        page.locator("#jdText").fill("Forward Deployed Engineer JD")
        page.locator("#relatedExperience").fill("Built a real customer-facing Python prototype")
        page.locator('[data-generation-mode="career_switch"]').click()
        page.locator('[data-proficiency-level="proficient"]').click()
        page.locator("#generateTailoredBtn").click()
        page.wait_for_selector("#panel-polish.active")
        assert "岗位定制模式" in page.locator("#tailoredBanner").text_content()
        summary_editor = page.locator('[data-tailored-path="basics.summary"]')
        assert summary_editor.input_value() == "Targeted FDE delivery summary"
        assert "Delivered applications for enterprise clients" in page.locator("#tailoredContentEditor").text_content()
        assert page.locator('[data-tailored-path="projects.0.name"]').input_value() == "FDE Solution Lab"
        project_bullets = page.locator('[data-tailored-path="projects.0.bullets"]')
        project_bullets.fill("Built stock、sector and monthly indicators in one result")
        page.locator('[data-tailored-add="projects"]').click()
        page.wait_for_selector('[data-tailored-path="projects.1.name"]')
        assert page.locator('[data-tailored-path="projects.0.bullets"]').input_value() == "Built stock、sector and monthly indicators in one result"
        page.locator('[data-tailored-path="projects.1.name"]').fill("Manual project")
        page.locator('[data-tailored-remove="projects.1"]').click()
        page.wait_for_selector('[data-tailored-path="projects.1.name"]', state="detached")
        page.locator("#undoAiEditBtn").click()
        expect(page.locator('[data-tailored-path="projects.1.name"]')).to_have_value("Manual project")
        page.locator("#redoAiEditBtn").click()
        page.wait_for_selector('[data-tailored-path="projects.1.name"]', state="detached")
        page.locator("#undoAiEditBtn").click()
        expect(page.locator('[data-tailored-path="projects.1.name"]')).to_have_value("Manual project")
        page.locator('[data-tailored-remove="projects.1"]').click()
        page.wait_for_selector('[data-tailored-path="projects.1.name"]', state="detached")
        summary_editor.focus()
        summary_editor.evaluate("el => { el.setSelectionRange(13, 25); el.dispatchEvent(new Event('select', { bubbles: true })); }")
        assert "已选中：个人概述" in page.locator("#aiEditTarget").text_content()
        page.locator("#aiEditInstruction").fill("Make this sound more enterprise-oriented")
        page.locator("#applyAiEditBtn").click()
        expect(page.locator('[data-tailored-path="basics.summary"]')).to_have_value(re.compile("enterprise AI delivery"))
        assert selection_edit_requests[-1]["path"] == "basics.summary"
        assert selection_edit_requests[-1]["selected_text"] == "delivery sum"
        assert selection_edit_requests[-1]["selection_start"] == 13
        assert selection_edit_requests[-1]["selection_end"] == 25
        page.locator("#undoAiEditBtn").click()
        expect(page.locator('[data-tailored-path="basics.summary"]')).to_have_value("Targeted FDE delivery summary")
        page.locator("#redoAiEditBtn").click()
        expect(page.locator('[data-tailored-path="basics.summary"]')).to_have_value(re.compile("enterprise AI delivery"))
        page.locator("#undoAiEditBtn").click()
        expect(page.locator('[data-tailored-path="basics.summary"]')).to_have_value("Targeted FDE delivery summary")
        page.locator("#clearAiTargetBtn").click()
        assert "整份简历调整模式" in page.locator("#aiEditTarget").text_content()
        assert page.locator("#applyAiAddBtn").is_enabled()
        assert page.locator("#applyAiEditBtn").is_enabled()
        page.locator("#aiEditInstruction").fill("I also built TongdaXin RPS indicators for stock selection review")
        page.locator("#applyAiAddBtn").click()
        expect(page.locator("#tailoredContentEditor")).to_contain_text("Built TongdaXin stock and sector RPS indicators")
        assert smart_add_requests[-1]["instruction"].startswith("I also built TongdaXin")
        assert smart_add_requests[-1]["mode"] == "add"
        assert "本轮实际修改 2 处" in page.locator("#refineChangeNotice").text_content()
        page.locator("#undoAiEditBtn").click()
        expect(page.locator("#tailoredContentEditor")).not_to_contain_text("Built TongdaXin stock and sector RPS indicators")
        page.locator("#redoAiEditBtn").click()
        expect(page.locator("#tailoredContentEditor")).to_contain_text("Built TongdaXin stock and sector RPS indicators")
        page.locator("#undoAiEditBtn").click()
        expect(page.locator("#tailoredContentEditor")).not_to_contain_text("Built TongdaXin stock and sector RPS indicators")
        summary_editor.fill("Reviewed targeted summary")
        page.wait_for_timeout(700)
        page.locator(".legacy-question-panel > summary").click()
        page.locator("#questionBtn").click()
        page.wait_for_selector("#questionCard:not(.hidden)")
        page.locator("#answerText").fill("Validated representative delivery cases")
        page.locator("#answerBtn").click()
        expect(page.locator("#questionText")).to_have_text("How did you iterate?")
        page.locator("#answerText").fill("Compared outputs and adjusted the workflow")
        page.locator("#answerBtn").click()
        expect(page.locator("#questionPosition")).to_contain_text("第 2 问")
        assert "本轮实际修改 1 处" in page.locator("#refineChangeNotice").text_content()
        page.locator("#previousQuestionBtn").click()
        assert page.locator("#answerText").input_value() == "Validated representative delivery cases"
        page.locator("#answerText").fill("Validated representative delivery and failure cases")
        page.locator("#answerBtn").click()
        page.wait_for_timeout(300)
        assert refine_requests[-1]["previous_answer"] == "Validated representative delivery cases"
        assert "本轮未修改正文" in page.locator("#refineChangeNotice").text_content()
        page.locator("#nextQuestionBtn").click()
        assert page.locator("#answerText").input_value() == "Compared outputs and adjusted the workflow"
        assert "Validated the workflow with representative cases" in page.locator("#tailoredContentEditor").text_content()
        assert saved_payloads
        saved = saved_payloads[-1]
        assert saved["profile"]["basics"]["name"] == "Base Candidate"
        assert saved["profile"]["basics"]["summary"] == "Base summary"
        assert saved["resume"]["related_experience"] == "Built a real customer-facing Python prototype"
        assert generate_requests[-1]["related_experience"] == "Built a real customer-facing Python prototype"
        assert generate_requests[-1]["generation_mode"] == "career_switch"
        assert generate_requests[-1]["proficiency_level"] == "proficient"
        assert saved["resume"]["tailored_profile"]["basics"]["name"] == "Base Candidate"
        assert saved["resume"]["tailored_profile"]["basics"]["phone"] == "13800000000"
        assert "Validated the workflow with representative cases" in saved["resume"]["tailored_profile"]["projects"][0]["bullets"]

        def accept_library_dialog(dialog):
            if dialog.type == "prompt":
                dialog.accept("FDE 岗位简历")
            else:
                dialog.accept()

        page.on("dialog", accept_library_dialog)
        page.locator("#saveResumeVariantBtn").click()
        expect(page.locator("#resumeLibraryBtn")).to_contain_text("1")
        saved_variant_state = saved_payloads[-1]
        assert saved_variant_state["profile"]["basics"]["name"] == "Base Candidate"
        assert len(saved_variant_state["resume_library"]) == 1
        assert saved_variant_state["resume_library"][0]["name"] == "FDE 岗位简历"
        assert saved_variant_state["resume_library"][0]["resume"]["jd"] == "Forward Deployed Engineer JD"
        assert saved_variant_state["resume_library"][0]["resume"]["tailored_profile"]["basics"]["summary"]

        page.locator("#newResumeVariantBtn").click()
        page.wait_for_selector("#panel-match.active")
        assert page.locator("#jdText").input_value() == ""
        new_resume_state = saved_payloads[-1]
        assert new_resume_state["profile"]["basics"]["name"] == "Base Candidate"
        assert new_resume_state["resume"]["tailored_profile"] is None
        assert new_resume_state["resume"]["jd"] == ""
        assert len(new_resume_state["resume_library"]) == 1

        page.locator("#resumeLibraryBtn").click()
        page.wait_for_selector("#resumeLibraryDialog[open]")
        page.locator("[data-load-resume-variant='0']").click()
        page.wait_for_selector("#panel-polish.active")
        assert page.locator("#jdText").input_value() == "Forward Deployed Engineer JD"
        assert page.locator('[data-tailored-path="basics.summary"]').input_value()
        reopened_state = saved_payloads[-1]
        assert reopened_state["profile"]["basics"]["name"] == "Base Candidate"
        assert reopened_state["active_resume_id"] == reopened_state["resume_library"][0]["id"]
        browser.close()
    print("tailored_resume=OK; resume_library=OK; base_profile_unchanged=OK; user_data_writes=0")


if __name__ == "__main__":
    main()
