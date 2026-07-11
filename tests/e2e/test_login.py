"""
E2E — 登录/注册流程
"""
import pytest
import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")


class TestLoginPage:
    """登录页面渲染和交互"""

    def test_login_page_loads(self, page):
        """登录页加载成功，包含必要元素"""
        page.goto(f"{BASE_URL}/login")

        # 页面标题或关键文案
        page.wait_for_timeout(1000)
        content = page.content()
        assert "登录" in content or "login" in content.lower()

    def test_register_page_accessible(self, page):
        """注册表单可以在登录页中切换"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)

        # 查找注册按钮/链接
        register_btn = page.locator("text=注册").first
        if register_btn.is_visible():
            register_btn.click()
            page.wait_for_timeout(500)

    def test_login_form_exists(self, page):
        """登录表单包含用户名和密码输入框"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)

        # 查找输入框
        inputs = page.locator("input").all()
        assert len(inputs) >= 2, "登录页至少应有2个输入框"


class TestRegisterFlow:
    """注册流程"""

    def test_register_valid_input(self, page):
        """E2E-01: 输入有效注册信息并提交"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)

        # 切换到注册面板
        register_tab = page.get_by_role("button", name="注册")
        register_tab.click()
        page.wait_for_timeout(500)

        # 填写表单
        page.get_by_placeholder("请输入用户名").fill("testuser")
        page.get_by_placeholder("请输入密码（至少6位）").fill("test123456")
        page.get_by_placeholder("请再次输入密码").fill("test123456")

        # 勾选同意协议
        agree_checkbox = page.locator('input[type="checkbox"]').first
        if agree_checkbox.is_visible():
            agree_checkbox.check()

        # 提交
        submit_btn = page.get_by_role("button", name="注册").last
        if submit_btn.is_visible():
            submit_btn.click()
            page.wait_for_timeout(2000)


class TestLoginFlow:
    """登录流程"""

    def test_login_valid_credentials(self, page):
        """E2E-01: 使用有效凭据登录"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_timeout(1000)

        # 填写登录表单
        username_input = page.locator('input[name="username"], input[placeholder*="用户"]').first
        password_input = page.locator('input[type="password"]').first

        if username_input.is_visible():
            username_input.fill("testuser")
        if password_input.is_visible():
            password_input.fill("test123456")

        # 勾选协议
        agree_checkbox = page.locator('input[type="checkbox"]').first
        if agree_checkbox.is_visible():
            agree_checkbox.check()

        # 登录
        login_btn = page.locator('button:has-text("登录")').last
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(2000)
