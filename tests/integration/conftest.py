"""
集成测试公共 fixtures — 使用 FastAPI TestClient + mongomock
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


@pytest.fixture
def test_app():
    """
    创建测试用的 FastAPI app，mock MongoDB 和所有外部服务。
    这样集成测试可以快速运行，不需要真实的外部依赖。
    """
    # 先 mock 数据库
    mock_db = MagicMock()
    for coll in ["users", "sessions", "messages", "law_refs", "audit_logs", "token_usage", "sms_codes", "user_profiles"]:
        setattr(mock_db, coll, MagicMock())

    mock_db.users.find_one = AsyncMock()
    mock_db.users.insert_one = AsyncMock()
    mock_db.users.update_one = AsyncMock()
    mock_db.users.count_documents = AsyncMock()
    mock_db.sessions.find = MagicMock()
    mock_db.sessions.find_one = AsyncMock()
    mock_db.sessions.insert_one = AsyncMock()
    mock_db.sessions.update_one = AsyncMock()
    mock_db.sessions.count_documents = AsyncMock()
    mock_db.sessions.update_many = AsyncMock()
    mock_db.sessions.aggregate = MagicMock()
    mock_db.messages.find = MagicMock()
    mock_db.messages.find_one = AsyncMock()
    mock_db.messages.insert_one = AsyncMock()
    mock_db.messages.count_documents = AsyncMock()
    mock_db.law_refs.find = MagicMock()
    mock_db.law_refs.insert_many = AsyncMock()
    mock_db.audit_logs.insert_one = AsyncMock()
    mock_db.token_usage.insert_one = AsyncMock()
    mock_db.token_usage.count_documents = AsyncMock()
    mock_db.user_profiles.find_one = AsyncMock()
    mock_db.user_profiles.update_one = AsyncMock()

    # mock motor cursor
    def make_cursor(items):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__aiter__.return_value = items.__iter__()
        return cursor

    mock_db.sessions.find.side_effect = lambda *a, **kw: make_cursor([])
    mock_db.messages.find.side_effect = lambda *a, **kw: make_cursor([])
    mock_db.law_refs.find.side_effect = lambda *a, **kw: make_cursor([])

    def make_insert_result(inserted_id_str="507f1f77bcf86cd799439011"):
        from bson import ObjectId
        result = MagicMock()
        result.inserted_id = ObjectId(inserted_id_str)
        return result

    mock_db.users.insert_one.side_effect = lambda *a, **kw: make_insert_result()
    mock_db.sessions.insert_one.side_effect = lambda *a, **kw: make_insert_result("507f1f77bcf86cd799439022")
    mock_db.messages.insert_one.side_effect = lambda *a, **kw: make_insert_result("507f1f77bcf86cd799439033")

    # mock session cursor for list
    def make_list_cursor(items):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__aiter__.return_value = iter(items).__aiter__()
        return cursor

    mock_db.sessions.find.side_effect = lambda *a, **kw: make_list_cursor([])

    with patch("database.init_database", new=AsyncMock(return_value=mock_db)):
        with patch("database.get_database", return_value=mock_db):
            with patch("services.llm_service_v2.ChatOpenAI") as mock_chat_openai:
                from main import app, load_config, Settings

                # ensure settings are available
                if not hasattr(app.state, "settings"):
                    app.state.settings = load_config()
                if not hasattr(app.state, "services"):
                    app.state.db = mock_db
                    from main import _init_services
                    _init_services(app)

            from fastapi.testclient import TestClient
            client = TestClient(app)
            yield client


@pytest.fixture
def auth_headers(test_app):
    """获取已认证用户的请求头"""
    # 注册一个测试用户
    test_app.app.state.db.users.find_one = AsyncMock(return_value=None)

    resp = test_app.post("/api/v1/auth/register", json={
        "username": "integrationuser",
        "password": "pass123456",
        "confirm_password": "pass123456",
        "agree_terms": True,
    })
    if resp.status_code == 200:
        data = resp.json()
        token = data["data"]["access_token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # fallback: mock the login
    from utils.jwt_utils import create_access_token
    token = create_access_token("507f1f77bcf86cd799439011", "integrationuser")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
