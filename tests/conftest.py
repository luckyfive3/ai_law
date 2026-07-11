"""
pytest 公共 fixtures
"""
import sys
import os
import pytest

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def sample_user():
    """示例用户数据"""
    return {
        "user_id": "507f1f77bcf86cd799439011",
        "username": "testuser",
        "password": "test123456",
        "nickname": "测试用户",
    }


@pytest.fixture
def sample_session():
    """示例会话数据"""
    return {
        "session_id": "507f1f77bcf86cd799439022",
        "title": "法律咨询",
        "category": "civil",
    }


@pytest.fixture
def sample_search_results():
    """示例 RAGFlow 检索结果"""
    return [
        {
            "law_name": "中华人民共和国民法典",
            "article_num": "第一千零七十九条",
            "law_text": "夫妻一方要求离婚的，可以由有关组织进行调解或者直接向人民法院提起离婚诉讼。",
            "source": "中华人民共和国民法典 第五编 第四章",
            "chunk_id": "abc123",
            "relevance": 0.92,
        },
        {
            "law_name": "中华人民共和国劳动法",
            "article_num": "第三十六条",
            "law_text": "国家实行劳动者每日工作时间不超过八小时、平均每周工作时间不超过四十四小时的工时制度。",
            "source": "中华人民共和国劳动法 第四章",
            "chunk_id": "def456",
            "relevance": 0.75,
        },
    ]


@pytest.fixture
def sample_history():
    """示例历史对话消息"""
    return [
        {"role": "user", "content": "什么是劳动合同？"},
        {"role": "assistant", "content": "劳动合同是劳动者与用人单位确立劳动关系、明确双方权利和义务的协议。"},
        {"role": "user", "content": "试用期最长多久？"},
        {"role": "assistant", "content": "根据《劳动合同法》第十九条，试用期最长不超过六个月。"},
    ]
