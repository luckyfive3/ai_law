"""AI法律助手 v1.0 — 前端测试用 mock API
提供 cases 相关的 mock 数据，用于前端独立测试
"""

from fastapi import APIRouter, Request

router = APIRouter()

CASE_DATA = {
    "mock_case_001": {"id": "mock_case_001", "title": "王家村房屋拆迁补偿纠纷案", "case_type": "民事", "status": "已分析", "win_rate": 80, "evidence_uploaded": True, "court_level": "一审", "parties": [{"name": "张委托", "role": "原告"}], "created_at": "2025-10-15T08:30:00Z", "updated_at": "2025-10-28T09:00:00Z", "tags": ["拆迁", "补偿纠纷"], "description": "原告张委托与被告之间关于房屋拆迁补偿的纠纷", "analyses": [], "qa_history": []},
    "mock_case_002": {"id": "mock_case_002", "title": "某科技公司合同违约案", "case_type": "商事", "status": "分析中", "win_rate": 55, "evidence_uploaded": True, "court_level": "二审", "parties": [{"name": "上海某娱乐公司", "role": "原告"}], "created_at": "2025-11-01T10:00:00Z", "updated_at": "2025-11-15T14:00:00Z", "tags": ["合同", "违约"], "description": "技术服务合同纠纷", "analyses": [], "qa_history": []},
    "mock_case_003": {"id": "mock_case_003", "title": "李某交通事故纠纷案", "case_type": "民事", "status": "待分析", "win_rate": 0, "evidence_uploaded": False, "court_level": "一审", "parties": [{"name": "李某", "role": "原告"}], "created_at": "2025-12-01T12:00:00Z", "updated_at": "2025-12-01T12:00:00Z", "tags": ["交通事故"], "description": "交通事故损害赔偿纠纷", "analyses": [], "qa_history": []},
}


# ── 案件列表 ──
@router.get("/api/v1/proxy/cases")
async def list_cases(request: Request):
    return {"code": 0, "message": "success", "data": {"list": list(CASE_DATA.values()), "total": 3, "page": 1, "page_size": 20, "has_more": False}}


# ── 案件简要列表 ──
@router.get("/api/v1/proxy/cases/list/simple")
async def list_simple(request: Request):
    return {"code": 0, "message": "success", "data": [{"id": k, "title": v["title"]} for k, v in CASE_DATA.items()]}


# ── 创建案件 ──
@router.post("/api/v1/proxy/cases")
async def create_case(request: Request):
    body = await request.json()
    return {"code": 0, "message": "案件创建成功", "data": {"id": "mock_case_new", "title": body.get("title", "新案件"), "case_type": body.get("case_type", "民事"), "status": "待分析", "win_rate": 0, "evidence_uploaded": False, "court_level": body.get("court_level", ""), "parties": body.get("parties", []), "created_at": "2025-12-15T10:00:00Z", "updated_at": "2025-12-15T10:00:00Z", "tags": body.get("tags", [])}}


# ── 案件详情 ──
@router.get("/api/v1/proxy/cases/{case_id}")
async def get_case(request: Request, case_id: str):
    c = CASE_DATA.get(case_id, CASE_DATA["mock_case_001"])
    return {"code": 0, "message": "success", "data": {
        **c,
        "analyses": [{"id": "a1", "analysis_type": "case_overview", "content": {"案情时间轴": [{"date": "2023-06-15", "title": "拆迁公告", "description": "发布拆迁公告"}, {"date": "2023-09-01", "title": "提起诉讼", "description": "向法院提起诉讼"}], "案情摘要": "本案为一起房屋拆迁补偿纠纷。\n\n案件涉及补偿标准的认定和安置方案的合理性。", "事实分析": "一、拆迁合法性问题\n拆迁公告手续完备。\n\n二、补偿标准争议\n原告认为补偿标准与实际价值不符。", "法律分析": "根据《中华人民共和国民法典》相关规定，当事人应当全面履行义务。", "定争分析": "争议焦点一：补偿标准是否合理\n焦点二：安置方案是否妥当", "司法推理": "综合各方因素，法院可能支持原告部分诉求。", "参考判例": "参考(2022)京01民终12345号判决。"}, "created_at": "2025-10-28T09:00:00Z"}],
        "qa_history": [{"id": "q1", "question": "被告是否应承担侵权责任？", "answer": "根据案情分析，被告行为构成侵权。根据《民法典》第1165条，行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。", "created_at": "2025-10-20T10:00:00Z"}],
    }}


# ── 获取分析 ──
@router.get("/api/v1/proxy/cases/{case_id}/analysis")
async def get_analysis(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": {"id": "a1", "分析类型": "case_overview", "案情时间轴": [{"date": "2023-06-15", "title": "拆迁公告", "description": "发布拆迁公告"}, {"date": "2023-07-20", "title": "协商不成功", "description": "双方协商未达成一致"}, {"date": "2023-09-01", "title": "提起诉讼", "description": "向法院提起诉讼"}], "案情摘要": "本案为一起房屋拆迁补偿纠纷。\n\n案件涉及补偿标准的认定和安置方案的合理性。经初步审查，拆迁公告手续完备，但补偿标准存在争议。", "事实分析": "一、拆迁合法性问题\n\n拆除手续完备，程序合法。\n\n二、补偿标准争议\n\n原告认为补偿标准与实际价值不符。\n\n三、安置方案合理性\n\n被告提供的安置方案需进一步评估其公平性和合理性。", "法律分析": "根据《中华人民共和国民法典》第五百零九条的规定，当事人应当按照约定全面履行自己的义务。\n\n同时根据相关行政法规，征收补偿应当公平合理，确保被征收人原有生活水平不降低。", "定争分析": "一、核心争议焦点\n1. 补偿标准是否合理——原告坚持市场评估价格，被告依据政府指导价\n2. 安置方案是否妥当\n\n二、次要争议焦点\n1. 评估机构的资质问题\n2. 临时安置补助费标准", "司法推理": "一、补偿标准的判定\n综合考虑市场价格、区位因素、房屋面积等，原告主张有一定合理性。\n\n二、胜诉率预估\n综合各方面因素，预估胜诉率为80%。", "参考判例": "参考以下相似判例：\n\n(2022)京01民终12345号\n基本案情：类似拆迁补偿纠纷\n裁判要点：法院支持原告部分诉求，判令按市场价补足差额", "created_at": "2025-10-28T09:00:00Z"}}


# ── 触发分析 ──
@router.post("/api/v1/proxy/cases/{case_id}/analysis")
async def trigger_analysis(request: Request, case_id: str):
    return {"code": 0, "message": "分析完成", "data": {"id": "analysis_new"}}


# ── QA ──
@router.get("/api/v1/proxy/cases/{case_id}/qa")
async def get_qa(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": [{"id": "q1", "question": "被告是否应承担侵权责任？", "answer": "根据案情分析，被告行为构成侵权。\n\n**一、法律依据**\n根据《民法典》第1165条。\n\n**二、分析**\n结合案情，被告存在过错行为。\n\n**三、建议**\n建议收集相关证据材料。", "created_at": "2025-10-20T10:00:00Z"}]}


@router.post("/api/v1/proxy/cases/{case_id}/qa")
async def ask_question(request: Request, case_id: str):
    body = await request.json()
    q = body.get("question", "")
    return {"code": 0, "message": "问答成功", "data": {"id": "qa_new", "question": q, "answer": f'关于【{q}】的问题，根据相关法律规定：\n\n**一、法律依据**\n根据《民法典》相关规定。\n\n**二、分析**\n结合本案案情...\n\n**三、建议**\n收集证据，咨询专业律师。', "created_at": "2025-12-15T10:30:00Z"}}


# ── 证据链 ──
@router.get("/api/v1/proxy/cases/{case_id}/evidence-chain")
async def get_chain(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": {"id": "chain_001", "证据链概述": "通过对案件全部证据的系统梳理，可以构建出一条完整的证据链。证据之间相互印证、环环相扣。", "证据节点": [{"name": "合同原件", "relation": "基础证明关系，证明双方权利义务"}, {"name": "付款凭证", "relation": "关联关系，证明款项支付事实"}, {"name": "鉴定报告", "relation": "核心证明关系，证明损害结果"}, {"name": "现场照片", "relation": "辅助证明关系，证明现场状况"}], "证据链完整性评估": "该案件证据链完整度约为85%。", "薄弱环节": "1. 因果关系需进一步证明\n2. 损失计算依据需补充", "created_at": "2025-10-28T09:00:00Z"}}


@router.post("/api/v1/proxy/cases/{case_id}/evidence-chain")
async def trigger_chain(request: Request, case_id: str):
    return {"code": 0, "message": "证据链生成完成", "data": {"id": "chain_new"}}


# ── 证据清单 ──
@router.get("/api/v1/proxy/cases/{case_id}/evidence-list")
async def get_elist(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": {"id": "elist_001", "原告方证据": [{"name": "合同原件", "admissibility": "高"}, {"name": "付款凭证", "admissibility": "高"}, {"name": "鉴定报告", "admissibility": "中"}], "被告方证据": [{"name": "服务记录", "admissibility": "中"}, {"name": "验收报告", "admissibility": "高"}], "薄弱点": ["电子证据保存不规范", "间接损失计算缺第三方报告"], "矛盾点": ["双方对质量标准理解存在分歧"], "法官采信分析": "法院大概率会采信合同原件、付款凭证等核心证据。", "补充建议": ["建议申请司法鉴定", "建议对关键电子证据公证保全"], "created_at": "2025-10-28T09:00:00Z"}}


@router.post("/api/v1/proxy/cases/{case_id}/evidence-list")
async def trigger_elist(request: Request, case_id: str):
    return {"code": 0, "message": "证据清单生成完成", "data": {"id": "elist_new"}}


# ── 证据管理 ──
@router.get("/api/v1/proxy/cases/{case_id}/evidence")
async def list_evidence(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": {"list": [{"id": "ev_001", "name": "房屋买卖合同原件", "evidence_type": "书面文件", "status": "AI分析通过", "description": "双方签订的房屋买卖合同", "purpose": "证明合同关系成立", "created_at": "2025-10-16T08:00:00Z"}, {"id": "ev_002", "name": "银行转账记录", "evidence_type": "电子文档", "status": "待审核", "description": "首期款项支付记录", "purpose": "证明已履行付款义务", "created_at": "2025-10-16T09:00:00Z"}, {"id": "ev_003", "name": "现场照片", "evidence_type": "照片和视频", "status": "AI审核失败", "description": "拆迁现场照片", "purpose": "证明房屋现状", "created_at": "2025-10-18T10:00:00Z"}], "total": 3, "page": 1, "page_size": 20, "has_more": False}}


@router.post("/api/v1/proxy/cases/{case_id}/evidence")
async def create_evidence(request: Request, case_id: str):
    body = await request.json()
    return {"code": 0, "message": "证据创建成功", "data": {"id": "ev_new", "name": body.get("name", "新证据"), "status": "待审核", "evidence_type": body.get("evidence_type", "书面文件")}}


@router.get("/api/v1/proxy/cases/{case_id}/evidence/{evidence_id}")
async def get_evidence(request: Request, case_id: str, evidence_id: str):
    return {"code": 0, "message": "success", "data": {"id": evidence_id, "name": "房屋买卖合同原件", "evidence_type": "书面文件", "status": "AI分析通过", "description": "双方签订的房屋买卖合同", "purpose": "证明合同关系成立", "audit_reason": "该证据来源清晰、形式合法，符合证据资格规定。", "created_at": "2025-10-16T08:00:00Z"}}


@router.post("/api/v1/proxy/cases/{case_id}/evidence/{evidence_id}/audit")
async def audit_evidence(request: Request, case_id: str, evidence_id: str):
    return {"code": 0, "message": "审核完成", "data": {"result": "pass", "reason": "证据通过审核"}}


# ── 文档管理 ──
@router.get("/api/v1/proxy/cases/{case_id}/documents")
async def list_documents(request: Request, case_id: str):
    return {"code": 0, "message": "success", "data": {"list": [{"id": "doc_001", "name": "民事答辩状.docx", "file_url": "/uploads/doc_001.docx", "created_at": "2025-10-20T10:00:00Z"}, {"id": "doc_002", "name": "证据材料.pdf", "file_url": "/uploads/doc_002.pdf", "created_at": "2025-10-22T14:00:00Z"}], "total": 2, "page": 1, "page_size": 20, "has_more": False}}


@router.post("/api/v1/proxy/cases/{case_id}/documents")
async def create_document(request: Request, case_id: str):
    return {"code": 0, "message": "文档创建成功", "data": {"id": "doc_new"}}


@router.delete("/api/v1/proxy/cases/{case_id}/documents/{doc_id}")
async def delete_document(request: Request, case_id: str, doc_id: str):
    return {"code": 0, "message": "文档删除成功", "data": None}


@router.delete("/api/v1/proxy/cases/{case_id}")
async def delete_case(request: Request, case_id: str):
    return {"code": 0, "message": "案件删除成功", "data": None}


@router.post("/api/v1/proxy/cases/{case_id}/upload")
async def upload_file(request: Request, case_id: str):
    return {"code": 0, "message": "文件上传成功", "data": {"filename": "test.docx", "file_url": "/uploads/test.docx"}}
