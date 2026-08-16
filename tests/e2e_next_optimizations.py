import json
import os
import re

from playwright.sync_api import expect, sync_playwright


BASE_URL = os.environ.get("RESUME_TEST_URL", "http://127.0.0.1:8877")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.add_init_script("localStorage.setItem('resume-workshop:onboarding:v2', 'done'); localStorage.setItem('resume-workshop:terms:v1', 'accepted'); localStorage.setItem('resume-workshop:ai-consent:deepseek:https://api.deepseek.com:v1', 'accepted')")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    state = {
        "profile": {"basics": {"name": "测试", "target_role": "AI工程师", "phone": "", "email": "", "city": "", "links": "", "summary": "", "photo": ""}, "experience": [], "projects": [], "education": [], "skills": [], "certificates": [], "languages": []},
        "resume": {"title": "测试简历", "language": "zh", "template": "ats", "page_mode": "one", "section_order": ["summary", "projects", "skills"], "jd": "需要 Python", "analysis": {"summary": "存在技能缺口", "score": 20, "gaps": ["Python"], "requirements": []}, "tailored_profile": None, "tailored_jd": "", "related_experience": "", "generation_mode": "career_switch", "proficiency_level": "beginner", "questions": []},
        "resume_library": [], "active_resume_id": None,
    }
    saved_resume = json.loads(json.dumps(state["resume"]))
    saved_resume["title"] = "已保存的 FDE 简历"
    state["resume_library"] = [{"id": "fde-saved", "name": "FDE", "saved_at": "2026-07-28T10:00:00", "resume": saved_resume}]
    project_requests = []

    def project_case_route(route):
        body = route.request.post_data_json
        project_requests.append(body)
        material_type = body.get("material_type") or "engineering"
        labels = {
            "engineering": {"methods": "规范与工具", "structure": "设计范围与方法", "highlights": "技术要点"},
            "content": {"methods": "资料与方法", "structure": "内容结构", "highlights": "核心观点"},
        }.get(material_type, {"methods": "方法与工具", "structure": "工作框架", "highlights": "关键要点"})
        payload = {"name": "朝拾", "role": "独立开发者", "summary": "Windows 与 Android 双端的本地优先时间管理应用", "material_type": material_type, "material_type_label": "工程设计或施工项目" if material_type == "engineering" else "内容创作、文章或报告", "classification_confidence": 0.91, "labels": labels, "methods": "Flutter、Drift、Supabase", "structure": "Riverpod + go_router + Drift Outbox", "highlights": ["离线优先", "跨端同步"], "bullets": ["设计待办同步冲突策略"], "evidence_items": [{"statement": "采用本地优先架构", "filename": "README.md", "quote": "朝拾是一款本地优先的跨平台时间管理工具", "confidence": 0.95}], "uncertainties": []}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    page.route("**/api/state", lambda route: route.fulfill(status=200, content_type="application/json", body='{"ok":true}') if route.request.method == "PUT" else route.fulfill(status=200, content_type="application/json", body=json.dumps(state)))
    page.route("**/api/import**", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps({"filename": "README.md", "text": "朝拾是一款本地优先的跨平台时间管理工具", "used_ocr": False})))
    page.route("**/api/ai/project-case", project_case_route)
    learning_resources = [
        {"title": "Python 零基础教程", "platform": "哔哩哔哩", "kind": "直达课程", "url": "https://www.bilibili.com/video/BV1R7411F7JV/"},
        {"title": "Python 语言程序设计", "platform": "中国大学 MOOC", "kind": "具体课程", "url": "https://www.icourse163.org/course/detail.htm?cid=268001"},
        {"title": "用 Python 学人工智能", "platform": "国家高等教育智慧教育平台", "kind": "具体课程", "url": "https://higher.smartedu.cn/course/68c0987da9f4619f8f00c004"},
        {"title": "Python 入门", "platform": "慕课网", "kind": "具体课程", "url": "https://www.imooc.com/learn/177"},
        {"title": "机器学习及其 Python 实践", "platform": "学堂在线", "kind": "具体课程", "url": "https://www.xuetangx.com/course/THU08091000367/"},
    ]
    learning_payload = {"summary": "先学基础", "resource_note": "链接直达具体课程", "stages": [{"title": "Python", "duration": "2周", "goal": "掌握语法", "deliverable": "练习项目", "resource_pool": learning_resources, "resources": learning_resources[:3]}]}
    page.route("**/api/ai/learning-path", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(learning_payload)))
    page.route("**/api/learning-feedback", lambda route: route.fulfill(status=200, content_type="application/json", body='{"ok":true}'))
    page.goto(BASE_URL, wait_until="networkidle")
    assert "v=20260816.1" in page.locator('link[rel="stylesheet"]').get_attribute("href")
    page.evaluate("document.querySelector('#settingsDialog').showModal()")
    download_box = page.locator("#backupBtn").bounding_box()
    restore_box = page.locator(".backup-actions .button-like").bounding_box()
    assert download_box and restore_box
    assert abs(download_box["y"] - restore_box["y"]) <= 1
    assert abs(download_box["height"] - restore_box["height"]) <= 1
    page.evaluate("document.querySelector('#settingsDialog').close()")

    page.locator('[data-step="match"]').click()
    page.locator('[data-generation-mode="career_switch"]').click()
    assert page.locator("#learningPathCard").is_visible()
    page.locator(".project-folder-card > summary").click()
    assert page.locator("#projectFolderInput").count() == 1
    assert page.locator("#analyzeProjectFolderBtn").is_disabled()
    page.evaluate("""() => {
        const fileHandle = {kind: 'file', getFile: async () => new File(['# FDE 项目'], 'README.md', {type: 'text/markdown'})};
        const generatedHandle = {name: '.dart_tool', kind: 'directory', async *entries() { yield ['build.json', fileHandle]; }};
        const directoryHandle = {name: 'FDE-project', kind: 'directory', async *entries() { yield ['.dart_tool', generatedHandle]; yield ['README.md', fileHandle]; }};
        Object.defineProperty(window, 'showDirectoryPicker', {configurable: true, value: async () => directoryHandle});
    }""")
    page.locator("#chooseProjectFolderBtn").click()
    expect(page.locator("#projectFolderSummary")).to_contain_text("FDE-project")
    assert "优先选择 1 个" in page.locator("#projectFolderSummary").inner_text()
    assert not page.locator("#analyzeProjectFolderBtn").is_disabled()
    page.locator("#analyzeProjectFolderBtn").click()
    page.locator("#projectCaseText").wait_for(state="visible")
    assert "设计范围与方法：Riverpod + go_router + Drift Outbox" in page.locator("#projectCaseText").input_value()
    assert "置信度 91%" in page.locator("#projectMaterialTypeStatus").inner_text()
    assert "README.md" in page.locator("#projectCaseEvidenceList").text_content()
    page.locator("#projectMaterialType").select_option("content")
    page.locator("#reanalyzeProjectCaseBtn").click()
    expect(page.locator("#projectCaseText")).to_have_value(re.compile("内容结构："))
    assert project_requests[-1]["material_type"] == "content"
    page.locator("#learningPathCard > summary").click()
    with page.expect_response("**/api/ai/learning-path"):
        page.locator("#generateLearningPathBtn").click()
    page.locator("#learningPathResult").get_by_text("先学基础").wait_for(state="visible")
    direct_link = page.locator("#learningPathResult a").first
    assert "/video/" in direct_link.get_attribute("href")
    assert "search" not in direct_link.get_attribute("href")
    assert page.locator("[data-refresh-learning-stage]").is_visible()
    with page.expect_response("**/api/learning-feedback"):
        page.locator('[data-learning-feedback="useful"]').first.click()
    assert "active" in (page.locator('[data-learning-feedback="useful"]').first.get_attribute("class") or "")
    first_resource = page.locator("#learningPathResult .learning-resource a").first.get_attribute("href")
    page.locator(".learning-custom-feedback input").first.fill("希望增加更多动手练习")
    page.locator("[data-save-learning-note]").first.click()
    assert page.evaluate("url => state.resume.learning_resource_notes?.[url]", first_resource) == "希望增加更多动手练习"
    page.locator("[data-refresh-learning-stage]").click()
    refreshed_resource = page.locator("#learningPathResult .learning-resource a").first.get_attribute("href")
    assert refreshed_resource != first_resource
    assert "bilibili.com" not in refreshed_resource

    page.evaluate("""() => {
        document.querySelector('.project-folder-card').open = true;
        document.querySelector('#projectCaseDraft').classList.remove('hidden');
        document.querySelector('#projectCaseText').value = '上一个岗位的临时草稿';
        document.querySelector('#learningPathCard').open = true;
    }""")
    page.locator("#resumeLibraryBtn").click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator('[data-load-resume-variant="0"]').click()
    expect(page.locator("#resumeTitle")).to_have_value("已保存的 FDE 简历")
    assert not page.locator(".project-folder-card").get_attribute("open")
    assert "hidden" in (page.locator("#projectCaseDraft").get_attribute("class") or "")
    assert page.locator("#projectCaseText").input_value() == ""
    assert not page.locator("#learningPathCard").get_attribute("open")

    page.locator('[data-step="design"]').click()
    assert page.locator("#templateFileInput").count() == 1
    assert page.locator(".template-sites a").count() == 3
    first_batch = page.locator(".template-sites a").evaluate_all("links => links.map(link => link.href)")
    page.locator("#refreshTemplateSitesBtn").click()
    second_batch = page.locator(".template-sites a").evaluate_all("links => links.map(link => link.href)")
    assert len(second_batch) == 3
    assert first_batch != second_batch
    assert all(link.get_attribute("target") == "_blank" for link in page.locator(".template-sites a").all())
    assert page.locator(".template-site-toolbar").evaluate("node => node.scrollWidth <= node.clientWidth")
    assert page.locator("#resumePreview").is_visible()
    assert not errors, errors
    browser.close()
