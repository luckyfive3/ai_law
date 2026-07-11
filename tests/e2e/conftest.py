"""
E2E 测试公共 fixtures
需要前端(3000)和后端(8080)都已启动
"""
import pytest
import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def browser_context(playwright):
    """创建浏览器上下文"""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    yield context
    context.close()
    browser.close()


@pytest.fixture
def page(browser_context):
    """每个测试用例一个独立页面"""
    p = browser_context.new_page()
    yield p
    p.close()
