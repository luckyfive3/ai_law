"""
案件管理模块 — Pydantic 数据模型
定义案件、证据、文档、分析、问答相关的请求体和响应体
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from utils.errcode import CodeSuccess, get_message


# ==================== 通用辅助模型 ====================

class PartyInfo(BaseModel):
    """案件当事人信息"""
    name: str = Field(..., description="当事人姓名/名称")
    role: str = Field(..., description="当事人角色（原告/被告/第三人等）")


# ==================== 请求模型 ====================

class CaseCreateRequest(BaseModel):
    """
    创建案件请求

    Fields:
        title: 案件标题
        case_type: 案件类型（民事案件/刑事案件/行政案件）
        description: 案件描述
        court_level: 审理级别（一审/二审/再审）
        parties: 当事人列表
        tags: 标签列表
    """
    title: str = Field(..., min_length=1, max_length=200, description="案件标题")
    case_type: str = Field(..., description="案件类型（民事案件/刑事案件/行政案件）")
    description: str = Field(default="", description="案件描述")
    court_level: str = Field(default="", description="审理级别（一审/二审/再审）")
    parties: List[PartyInfo] = Field(default_factory=list, description="当事人列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class CaseUpdateRequest(BaseModel):
    """
    更新案件请求

    Fields:
        title: 案件标题（可选）
        description: 案件描述（可选）
        status: 案件状态（可选）
        court_level: 审理级别（可选）
        tags: 标签列表（可选）
        parties: 当事人列表（可选）
    """
    title: Optional[str] = Field(default=None, max_length=200, description="案件标题")
    description: Optional[str] = Field(default=None, description="案件描述")
    status: Optional[str] = Field(default=None, description="案件状态")
    court_level: Optional[str] = Field(default=None, description="审理级别")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    parties: Optional[List[PartyInfo]] = Field(default=None, description="当事人列表")


class CaseQARequest(BaseModel):
    """
    案件问答请求

    Fields:
        question: 用户提问内容
    """
    question: str = Field(..., min_length=1, max_length=2000, description="提问内容")


class EvidenceCreateRequest(BaseModel):
    """
    创建证据请求

    Fields:
        name: 证据名称
        evidence_type: 证据类型（书面文件/电子文档/照片和视频/音频记录/物证）
        description: 证据描述
        purpose: 证明目的
        source: 证据来源
        collection_method: 收集方式
        collection_note: 收集备注
    """
    name: str = Field(..., min_length=1, max_length=200, description="证据名称")
    evidence_type: str = Field(..., description="证据类型（书面文件/电子文档/照片和视频/音频记录/物证）")
    description: str = Field(default="", description="证据描述")
    purpose: str = Field(default="", description="证明目的")
    source: str = Field(default="", description="证据来源")
    collection_method: str = Field(default="", description="收集方式")
    collection_note: str = Field(default="", description="收集备注")


class EvidenceUpdateRequest(BaseModel):
    """
    更新证据请求

    Fields:
        name: 证据名称（可选）
        evidence_type: 证据类型（可选）
        description: 证据描述（可选）
        purpose: 证明目的（可选）
        status: 证据状态（可选）
    """
    name: Optional[str] = Field(default=None, max_length=200, description="证据名称")
    evidence_type: Optional[str] = Field(default=None, description="证据类型")
    description: Optional[str] = Field(default=None, description="证据描述")
    purpose: Optional[str] = Field(default=None, description="证明目的")
    status: Optional[str] = Field(default=None, description="证据状态")


class DocumentCreateRequest(BaseModel):
    """
    创建文档请求

    Fields:
        name: 文档名称
        file_url: 文件URL
        doc_type: 文档类型
        description: 文档描述
    """
    name: str = Field(..., min_length=1, max_length=200, description="文档名称")
    file_url: str = Field(..., description="文件URL")
    doc_type: str = Field(..., description="文档类型")
    doc_category: str = Field(default="", description="文件类别（起诉书/判决书/通知书/证据/辩护词/其他）")
    description: str = Field(default="", description="文档描述")


class CaseAnalysisRequest(BaseModel):
    """触发案件分析请求（空请求体）"""
    pass


# ==================== 响应模型 ====================

class CaseInfo(BaseModel):
    """
    案件摘要信息

    Fields:
        id: 案件ID
        title: 案件标题
        case_type: 案件类型
        status: 案件状态（待分析/分析中/已分析）
        win_rate: 胜诉率（0-100）
        evidence_uploaded: 是否已上传证据
        court_level: 审理级别
        parties: 当事人列表
        created_at: 创建时间
        updated_at: 更新时间
        tags: 标签列表
    """
    id: str = Field(..., description="案件ID")
    title: str = Field(..., description="案件标题")
    case_type: str = Field(..., description="案件类型")
    status: str = Field(default="待分析", description="案件状态")
    win_rate: int = Field(default=0, ge=0, le=100, description="胜诉率")
    evidence_uploaded: bool = Field(default=False, description="是否已上传证据")
    court_level: str = Field(default="", description="审理级别")
    parties: List[PartyInfo] = Field(default_factory=list, description="当事人列表")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class QAInfo(BaseModel):
    """
    问答信息

    Fields:
        id: 问答ID
        question: 提问内容
        answer: 回答内容
        created_at: 创建时间
    """
    id: str = Field(..., description="问答ID")
    question: str = Field(..., description="提问内容")
    answer: str = Field(..., description="回答内容")
    created_at: str = Field(default="", description="创建时间")


class EvidenceInfo(BaseModel):
    """
    证据基础信息

    Fields:
        id: 证据ID
        name: 证据名称
        evidence_type: 证据类型
        description: 证据描述
        purpose: 证明目的
        status: 证据状态（待审核/AI分析中/AI分析通过/AI审核失败/律师待审核）
        audit_result: 审核结果
        audit_reason: 审核原因
        created_at: 创建时间
    """
    id: str = Field(..., description="证据ID")
    name: str = Field(..., description="证据名称")
    evidence_type: str = Field(..., description="证据类型")
    description: str = Field(default="", description="证据描述")
    purpose: str = Field(default="", description="证明目的")
    status: str = Field(default="待审核", description="证据状态")
    audit_result: Optional[str] = Field(default=None, description="审核结果")
    audit_reason: Optional[str] = Field(default=None, description="审核原因")
    created_at: str = Field(default="", description="创建时间")


class EvidenceDetailInfo(EvidenceInfo):
    """
    证据详细信息（扩展）

    Fields (extends EvidenceInfo):
        source: 证据来源
        collection_method: 收集方式
        collection_note: 收集备注
        uploader_name: 上传者名称
    """
    source: str = Field(default="", description="证据来源")
    collection_method: str = Field(default="", description="收集方式")
    collection_note: str = Field(default="", description="收集备注")
    uploader_name: str = Field(default="", description="上传者名称")


class DocumentInfo(BaseModel):
    """
    文档信息

    Fields:
        id: 文档ID
        name: 文档名称
        file_url: 文件URL
        doc_type: 文档类型
        uploader: 上传者用户名
        created_at: 创建时间
    """
    id: str = Field(..., description="文档ID")
    name: str = Field(..., description="文档名称")
    file_url: str = Field(..., description="文件URL")
    doc_type: str = Field(..., description="文档类型")
    uploader: str = Field(default="", description="上传者")
    created_at: str = Field(default="", description="创建时间")


class AnalysisInfo(BaseModel):
    """
    分析信息

    Fields:
        id: 分析ID
        analysis_type: 分析类型
        content: 分析内容（字典格式）
        created_at: 创建时间
    """
    id: str = Field(..., description="分析ID")
    analysis_type: str = Field(..., description="分析类型")
    content: Dict[str, Any] = Field(default_factory=dict, description="分析内容")
    created_at: str = Field(default="", description="创建时间")


class CaseDetailInfo(CaseInfo):
    """
    案件详情信息（扩展 CaseInfo）

    Fields (extends CaseInfo):
        description: 案件描述
        analyses: 分析记录列表
        qa_history: 问答历史列表
    """
    description: str = Field(default="", description="案件描述")
    analyses: List[AnalysisInfo] = Field(default_factory=list, description="分析记录列表")
    qa_history: List[QAInfo] = Field(default_factory=list, description="问答历史列表")


# ==================== 辅助函数（委托到 errcode 模块） ====================

def success_response(data: Any = None, message: str = None) -> dict:
    """
    构建成功响应

    Args:
        data: 响应数据
        message: 自定义成功消息

    Returns:
        成功状态的字典响应
    """
    return {
        "code": CodeSuccess,
        "message": message or get_message(CodeSuccess),
        "data": data,
    }


def error_response(code: int, data: Any = None) -> dict:
    """
    构建错误响应

    Args:
        code: 错误码
        data: 附加数据（可选）

    Returns:
        错误状态的字典响应
    """
    return {
        "code": code,
        "message": get_message(code),
        "data": data,
    }
