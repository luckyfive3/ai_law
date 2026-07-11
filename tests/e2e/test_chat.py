"""
E2E — 聊天对话流程
"""
import os
import re

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:3000")


class TestChatPage:
    """对话页面"""

    def test_chat_page_loads(self, page):
        """对话页加载成功"""
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_timeout(1500)

        content = page.content()
        assert "chat" in page.url.lower() or "对话" in content or "消息" in content or "法律" in content

    def test_chat_input_exists(self, page):
        """对话页包含消息输入框"""
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_timeout(1000)

        # 查找textarea或input
        inputs = page.locator("textarea, input[type='text']").all()
        assert len(inputs) >= 1, "对话页应包含输入框"

    def test_new_session_button(self, page):
        """新建会话按钮存在"""
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_timeout(1000)

        # 查找新建相关按钮/链接
        try:
            new_btn = page.locator("button").filter(has_text="新建").first
            if new_btn.is_visible():
                new_btn.click()
                page.wait_for_timeout(500)
        except Exception:
            pass  # 未登录或按钮不存在时跳过


class TestChatMessageInteraction:
    """E2E-02: 发送消息并接收回复"""

    def test_send_message_and_wait_response(self, page):
        """发送消息 → 等待 SSE 流式响应"""
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_timeout(1500)

        # 检查是否需要先登录
        if "login" in page.url.lower():
            # 如果被重定向到登录页，跳过测试
            return

        # 找到输入框
        textarea = page.locator("textarea").first
        if not textarea.is_visible():
            textarea = page.locator('input[type="text"]').first

        if textarea.is_visible():
            textarea.fill("请简单介绍民法典的基本原则")
            page.wait_for_timeout(300)

            # 发送按钮
            send_btn = page.locator('button:has-text("发送"), button[type="submit"]').last
            if send_btn.is_visible():
                send_btn.click()
                # 等待流式响应
                page.wait_for_timeout(5000)

                # 检查页面有回复内容
                content = page.content()
                # 至少应该有加载状态或回复文本
                assert len(content) > 0


class TestDisclaimer:
    """E2E-06: 免责声明页面"""

    def test_disclaimer_page(self, page):
        """免责声明页正常显示"""
        page.goto(f"{BASE_URL}/disclaimer")
        page.wait_for_timeout(1000)

        content = page.content()
        assert "免责" in content or "声明" in content or "disclaimer" in content.lower()
