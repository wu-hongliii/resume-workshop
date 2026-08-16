import os
import zipfile

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("RESUME_TEST_URL", "http://127.0.0.1:8877")
STORAGE_KEY = "resume-workshop:onboarding:v2"


def run() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(BASE_URL, wait_until="networkidle")

        terms = page.locator("#termsDialog")
        terms.wait_for(state="visible")
        assert page.locator("#termsDialog .terms-points p").count() == 4
        page.locator("#acceptTermsBtn").click()
        assert page.evaluate("localStorage.getItem('resume-workshop:terms:v1')") == "accepted"

        dialog = page.locator("#onboardingDialog")
        dialog.wait_for(state="visible")
        assert page.locator("#onboardingStepList button").count() == 7
        assert page.locator("#onboardingStepList button.active").get_attribute("data-onboarding-step") == "0"
        assert page.locator("#previousOnboardingBtn").is_disabled()
        state_before = page.request.get(f"{BASE_URL}/api/state").json()

        with page.expect_download() as download_info:
            page.locator("#demoPackageBtn").click()
        download = download_info.value
        assert download.suggested_filename == "简历工坊-完整演示资料包.zip"
        with zipfile.ZipFile(download.path()) as archive:
            names = archive.namelist()
            assert any(name.endswith("旧简历-林知远-AI应用工程师-演示专用.docx") for name in names)
            assert any(name.endswith("旧简历-周桥-桥涵设计工程师-演示专用.docx") for name in names)
            assert any(name.endswith("编辑部单栏-演示模板.docx") for name in names)
        assert page.request.get(f"{BASE_URL}/api/state").json() == state_before

        page.locator("#nextOnboardingBtn").click()
        assert page.locator("#onboardingStepList button.active").get_attribute("data-onboarding-step") == "1"
        page.locator('[data-onboarding-step="6"]').click()
        assert page.locator("#nextOnboardingBtn").inner_text() == "开始制作"
        page.locator("#nextOnboardingBtn").click()
        assert not dialog.is_visible()
        assert page.evaluate("key => localStorage.getItem(key)", STORAGE_KEY) == "done"

        page.locator("#helpBtn").click()
        assert dialog.is_visible()
        page.locator("#closeOnboardingBtn").click()

        page.locator("#openDemoGuideBtn").click()
        assert dialog.is_visible()
        page.locator('[data-onboarding-step="2"]').click()
        page.locator("#goOnboardingBtn").click()
        assert page.locator("#panel-profile").is_visible()
        page.locator('[data-step="import"]').click()

        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#helpBtn").click()
        assert dialog.is_visible()
        assert page.locator("#onboardingStepList").evaluate("node => getComputedStyle(node).gridAutoFlow") == "column"
        assert page.locator("#onboardingStepList").evaluate("node => node.scrollWidth > node.clientWidth")
        page.locator("#skipOnboardingBtn").click()
        browser.close()


if __name__ == "__main__":
    run()
