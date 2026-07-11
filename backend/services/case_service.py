"""
AI法律助手 v1.0 — 案件管理服务
管理案件、证据、文档的全生命周期，提供 AI 分析、问答、证据审核等 Mock 功能
"""

import logging
import random
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from schemas.case_schemas import (
    CaseCreateRequest,
    CaseUpdateRequest,
    CaseQARequest,
    EvidenceCreateRequest,
    EvidenceUpdateRequest,
    DocumentCreateRequest,
)

logger = logging.getLogger(__name__)


# ==================== Mock AI 分析文本生成器 ====================

_MOCK_LAW_ARTICLES = {
    "中华人民共和国民法典": [
        {"article": "第五百零九条", "text": "当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。"},
        {"article": "第五百七十七条", "text": "当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。"},
        {"article": "第一千一百六十五条", "text": "行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。依照法律规定推定行为人有过错，其不能证明自己没有过错的，应当承担侵权责任。"},
        {"article": "第一千一百六十七条", "text": "侵权行为危及他人人身、财产安全的，被侵权人有权请求侵权人承担停止侵害、排除妨碍、消除危险等侵权责任。"},
        {"article": "第一千一百七十九条", "text": "侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费、营养费、住院伙食补助费等为治疗和康复支出的合理费用，以及因误工减少的收入。"},
    ],
    "中华人民共和国民事诉讼法": [
        {"article": "第六十三条", "text": "当事人对自己提出的主张，有责任提供证据。当事人及其诉讼代理人因客观原因不能自行收集的证据，或者人民法院认为审理案件需要的证据，人民法院应当调查收集。"},
        {"article": "第六十四条", "text": "人民法院应当按照法定程序，全面地、客观地审查核实证据。"},
    ],
}


def _generate_case_overview_analysis(
    title: str, case_type: str, court_level: str, parties: List[Dict], description: str
) -> Dict[str, Any]:
    """生成 Mock 案件综合分析的完整内容"""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    party_names = [p.get("name", "某当事人") for p in parties[:3]]
    plaintiff = party_names[0] if len(party_names) >= 1 else "原告"
    defendant = party_names[1] if len(party_names) >= 2 else "被告"

    return {
        "案情摘要": f"""本案为一起{case_type}案件，由{plaintiff}与{defendant}之间的纠纷引发。{description or "案件基本情况如下：双方当事人因合同履行问题产生争议，原告主张被告存在违约行为，要求被告承担相应的违约责任并赔偿经济损失。被告则认为自身已尽到合理义务，不应承担赔偿责任。"}

经初步审查，本案涉及的核心事实包括：合同的签订与履行过程、违约行为的认定、损失范围及金额的确定等。案件属于{court_level}审理阶段，需要就该阶段的争议焦点进行全面分析。""",

        "案情时间轴": [
            {"date": "2023-06-15", "title": "合同签订", "description": "双方签订《合作协议》，约定被告向原告提供技术服务，合同总金额50万元"},
            {"date": "2023-06-20", "title": "首期款项支付", "description": "原告按约定支付首期款项15万元"},
            {"date": "2023-07-15", "title": "履约争议产生", "description": "原告发现被告提供的技术服务存在严重质量问题，多项功能无法正常使用"},
            {"date": "2023-07-25", "title": "首次协商", "description": "双方就质量问题进行了第一次协商，被告承认存在部分瑕疵并承诺整改"},
            {"date": "2023-08-15", "title": "整改截止", "description": "约定的整改期限届满，被告未能完成全部整改工作"},
            {"date": "2023-08-20", "title": "最终催告", "description": "原告向被告发出书面催告函，要求其在7日内完成整改"},
            {"date": "2023-09-01", "title": "提起诉讼", "description": "原告向有管辖权的人民法院提起诉讼，请求判令被告承担违约责任"},
        ],

        "事实分析": f"""一、合同关系的成立与有效性

根据《中华人民共和国民法典》第五百零九条的规定，当事人应当按照约定全面履行自己的义务。经审查，原被告双方签订的《合作协议》系双方真实意思表示，内容不违反法律、行政法规的强制性规定，合同依法成立并有效，双方当事人均应按合同约定履行各自义务。

二、违约行为的认定

原告主张被告提供的技术服务存在严重质量问题，具体表现为：（1）系统频繁崩溃，月均宕机时间超过48小时；（2）关键功能模块无法正常使用；（3）数据安全存在重大隐患。根据合同约定的服务标准，上述问题已构成根本性违约。

三、损失的范围与计算

原告因被告的违约行为遭受了以下损失：（1）直接经济损失约20万元，包括首期款项及为补救问题而支出的额外费用；（2）间接损失（可得利益损失）约30万元，因系统不可用导致业务中断造成的损失。

四、因果关系的证明

原告提供的系统运行日志、第三方检测报告等证据能够证明，被告的技术服务质量问题与原告遭受的经济损失之间存在直接的因果关系。""",

        "法律分析": f"""本部分依据《中华人民共和国民法典》及相关法律法规，对本案涉及的法律问题进行深入分析：

一、合同违约责任

根据《民法典》第五百七十七条的规定："当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。"本案中，被告提供的技术服务不符合合同约定的质量标准，构成不完全履行，应当承担违约责任。

二、损害赔偿的范围

根据《民法典》第五百八十四条，当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额应当相当于因违约所造成的损失，包括合同履行后可以获得的利益。但不得超过违约方订立合同时预见到或者应当预见到的因违约可能造成的损失。

三、举证责任分配

根据《民事诉讼法》第六十三条，当事人对自己提出的主张，有责任提供证据。原告需就违约行为的存在、损失的范围及因果关系承担举证责任。被告如需主张免责事由，则需就该事由的存在承担举证责任。

四、{court_level}程序的特殊考量

鉴于本案处于{court_level}阶段，需要重点关注：（1）一审/二审中事实认定的准确性；（2）证据的充分性与合法性；（3）法律适用的正确性。""",

        "定争分析": f"""本案的争议焦点可以归纳为以下几个方面：

一、核心争议焦点

1. 被告提供的技术服务是否构成违约？
   - 原告方立场：服务质量严重不达标，多项核心功能无法正常使用
   - 被告方立场：已尽到合理努力，部分问题属于正常的技术调试范围

2. 原告主张的损失金额是否合理？
   - 直接损失15万元的认定与计算依据
   - 间接损失（可期待利益）30万元的合理性
   - 原告是否履行了减损义务

3. 被告是否享有免责或减责事由？
   - 合同中的责任限制条款是否有效
   - 是否存在不可抗力或其他免责情形

二、次要争议焦点

1. 合同约定的服务标准是否明确可执行
2. 原告是否给予了合理的整改期限
3. 第三方因素对服务质量的影响程度""",

        "司法推理": f"""基于上述事实分析和法律分析，本所对本案进行如下司法推理：

一、违约责任的构成要件分析

本案中，被告未能在合同约定的期限内提供符合质量标准的服务，其行为已满足违约责任的构成要件：（1）存在合法有效的合同关系；（2）被告存在不履行或不完全履行合同义务的事实；（3）原告因此遭受了实际损失；（4）违约行为与损失之间存在因果关系。

二、赔偿金额的确定

原告主张的直接损失15万元，有合同付款凭证及第三方检测报告等证据支持，应予认定。关于间接损失30万元的主张，原告需要进一步提供证据证明可期待利益的合理性及可预见性。根据《民法典》第五百八十四条的可预见规则，赔偿金额应以被告在订立合同时能够预见的范围为限。

三、责任比例的分担

综合考虑以下因素：（1）被告的违约程度属于根本性违约；（2）原告已给予合理的整改期限；（3）原告在发现质量问题后及时采取了止损措施。本所认为，被告应承担主要责任，责任比例建议为80%，即被告应赔偿原告实际损失的80%。

四、法律适用的最终结论

综上所述，本所提出以下裁判意见：
- 确认原被告之间的《合作协议》合法有效
- 认定被告存在根本性违约行为
- 判令被告赔偿原告经济损失合计人民币36万元（按45万元的80%计算）
- 判令被告承担本案全部诉讼费用
- 驳回原告的其他诉讼请求""",

        "参考判例": f"""以下为本所检索到的与本案件具有较高相似度的参考判例：

**案例一：（2022）京01民终12345号 — 信息技术服务合同纠纷案**

基本案情：原告委托被告开发企业管理系统，被告交付的系统存在持续性的功能缺陷，原告请求解除合同并要求被告返还已支付款项并赔偿损失。

裁判要点：法院认定被告提供的技术服务不满足合同约定的验收标准，构成根本性违约，判决解除合同，被告返还已收款80万元并赔偿原告损失30万元。本案对技术服务合同中"验收标准"的认定具有参考意义。

**案例二：（2021）沪73民初567号 — 软件技术服务合同纠纷案**

基本案情：类似的技术服务质量争议案件。

裁判要点：法院支持了原告关于被告提供的技术服务不符合合同约定标准的主张，判决被告赔偿原告经济损失及合理维权费用共计25万元。法院特别强调了技术服务合同中质量标准条款的重要性。

**案例三：（2023）粤民终890号 — 技术服务合同违约赔偿案**

基本案情：因技术服务提供方履约不当导致用户方业务损失。

裁判要点：二审法院维持了一审判决，认定违约方应当赔偿因违约造成的直接损失和可期待利益损失，但可期待利益的计算需有充分证据支持。本案确认了可预见规则在技术合同纠纷中的适用标准。

---

以上分析由 AI 法律助手自动生成，仅供参考。建议在做出最终法律决策前，咨询具有执业资格的专业律师。

分析时间：{now_str}""",
    }


def _generate_mock_qa_answer(question: str, case_title: str) -> str:
    """生成 Mock 法律问答回答"""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return f"""根据您提出的问题，结合案件"{case_title}"的具体情况，现答复如下：

{question}

**一、法律依据**

根据《中华人民共和国民法典》第五百七十七条的规定："当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。"同时，根据《民法典》第五百零九条，当事人应当按照约定全面履行自己的义务，并遵循诚信原则。

**二、问题分析**

针对您的问题，我们从以下几个方面进行分析：

1. **合同约定的效力**：根据案件材料，双方当事人签订的合同系双方真实意思表示，合同合法有效。依据《民法典》第一百四十三条关于民事法律行为有效要件的规定，该合同对双方均具有法律约束力。

2. **违约行为认定标准**：根据《民法典》第五百七十七条，违约行为的认定需要同时满足：（1）存在合法有效的合同义务；（2）当事人未按约定履行或履行不符合约定；（3）不存在法定或约定的免责事由。

3. **举证要点**：根据《中华人民共和国民事诉讼法》第六十三条的规定，当事人对自己提出的主张有责任提供证据。建议您重点收集和保存以下证据材料：合同原件及补充协议、付款凭证、沟通记录（微信/邮件/书面函件）、违约行为的客观证据（如检测报告、验收记录）、损失证明文件等。

**三、实务建议**

1. 建议尽快发起正式的书面催告程序，明确告知对方违约事实并要求限期整改；
2. 妥善保存所有证据材料，必要时可以进行公证取证；
3. 如有条件，建议委托专业的第三方机构出具技术鉴定报告；
4. 在选择诉讼策略时，需要综合考虑诉讼周期、诉讼成本和预期收益。

**四、风险提示**

本案存在以下主要风险点：
- 证据保全的及时性和完整性问题
- 合同中可能存在的免责条款或责任限制条款
- 损失金额的计算可能面临对方和法院的质疑
- 诉讼时效问题需特别关注（普通诉讼时效为三年）

---

以上分析由 AI 法律助手自动生成，仅供参考。建议在做出最终法律决策前，咨询具有执业资格的专业律师。

答复时间：{now_str}"""


def _generate_mock_evidence_chain(evidence_list: List[Dict]) -> Dict[str, Any]:
    """生成 Mock 证据链分析"""
    items = []
    for i, ev in enumerate(evidence_list[:5]):
        items.append({
            "name": ev.get("name", f"证据{i+1}"),
            "type": ev.get("evidence_type", "书面文件"),
            "relation": f"该证据与其他证据之间存在{'关联关系' if i > 0 else '基础证明关系'}，共同指向案件核心事实",
        })

    return {
        "证据链概述": "通过对案件全部证据的系统梳理，可以构建出一条完整的证据链，证明当事人之间的合同关系、违约行为的发生以及损失的存在。证据之间相互印证、环环相扣，形成了有效的证明体系。",
        "证据链结构": {
            "一级证据（直接证据）": "合同原件、付款凭证等直接证明案件基本事实的证据",
            "二级证据（间接证据）": "沟通记录、检测报告等间接证明违约行为存在的证据",
            "三级证据（辅助证据）": "行业标准、市场数据等辅助证明损失合理性的证据",
        },
        "证据节点": items,
        "证据链完整性评估": "该案件证据链完整度约为85%，主要证据均已收集到位，部分辅助证据有待补充。核心事实的证明已达到高度盖然性标准。",
        "薄弱环节": "证据链中存在以下可加强之处：（1）违约行为与损失之间的因果关系尚需进一步证明；（2）可期待利益损失的计算依据需要补充；（3）部分电子证据的真实性需要通过公证或鉴定加以确认。",
    }


def _generate_mock_evidence_list(evidence_list: List[Dict], parties: List[Dict]) -> Dict[str, Any]:
    """生成 Mock 证据清单分析"""
    plaintiff_name = "原告"
    defendant_name = "被告"
    for p in parties:
        if p.get("role") == "原告":
            plaintiff_name = p.get("name", "原告")
        if p.get("role") == "被告":
            defendant_name = p.get("name", "被告")

    plaintiff_evidence = []
    defendant_evidence = []
    for i, ev in enumerate(evidence_list[:6]):
        if i % 2 == 0:
            plaintiff_evidence.append({
                "name": ev.get("name", f"证据{i+1}"),
                "type": ev.get("evidence_type", "书面文件"),
                "purpose": ev.get("purpose", "证明案件基本事实"),
                "admissibility": "高度可采" if i < 2 else "中",
            })
        else:
            defendant_evidence.append({
                "name": ev.get("name", f"证据{i+1}"),
                "type": ev.get("evidence_type", "电子文档"),
                "purpose": ev.get("purpose", "反驳原告主张"),
                "admissibility": "中",
            })

    return {
        f"{plaintiff_name}方证据": plaintiff_evidence if plaintiff_evidence else [
            {"name": "合同原件", "type": "书面文件", "purpose": "证明合同关系成立及具体约定内容", "admissibility": "高"},
            {"name": "付款凭证", "type": "书面文件", "purpose": "证明原告已按约定支付款项", "admissibility": "高"},
            {"name": "系统运行日志", "type": "电子文档", "purpose": "证明被告服务存在严重质量问题", "admissibility": "中"},
        ],
        f"{defendant_name}方证据": defendant_evidence if defendant_evidence else [
            {"name": "服务响应记录", "type": "电子文档", "purpose": "证明被告已提供相关技术支持", "admissibility": "中"},
            {"name": "项目验收报告", "type": "书面文件", "purpose": "证明部分功能已通过验收测试", "admissibility": "高"},
        ],
        "薄弱点": [
            "部分电子证据的原始载体保存不规范，可能影响证据的真实性认定",
            "间接损失的计算缺乏独立的第三方审计或鉴定报告支持",
        ],
        "矛盾点": [
            "双方对服务质量标准的理解存在重大分歧，合同约定较为模糊",
            "关于整改是否完成的判断标准不统一",
        ],
        "法官采信分析": "结合本案证据的整体情况，法院大概率会采信以下核心证据：（1）合同原件——证明基本法律关系；（2）付款凭证——证明履行情况；（3）第三方检测报告——证明服务质量问题。对于电子证据，法院可能要求进行公证或技术鉴定后方可采信。",
        "补充建议": [
            "建议申请对涉案技术系统进行司法鉴定，以客观评估服务质量",
            "建议对关键电子证据进行公证保全，确保证据的合法性和证明力",
            "建议收集同类技术服务的市场价格信息，为损失计算提供参照依据",
            "建议补充提供双方就质量问题进行沟通的全部记录材料",
        ],
    }


def _generate_mock_evidence_audit(evidence_name: str, evidence_type: str) -> Dict[str, Any]:
    """生成 Mock 证据审核结果（随机通过/不通过）"""
    is_pass = random.choice([True, True, True, False])

    if is_pass:
        return {
            "result": "pass",
            "status": "AI分析通过",
            "reason": f'证据【{evidence_name}】（类型：{evidence_type}）已通过AI审核。该证据来源清晰、形式合法、内容真实、与案件事实具有关联性，符合《中华人民共和国民事诉讼法》第六十三条关于证据资格的规定。建议将本证据作为核心证据在庭审中使用。',
        }
    else:
        reasons = [
            f'证据【{evidence_name}】存在形式瑕疵：{evidence_type}类证据需要提供原始存储载体或经过公证的副本，当前提交的材料缺少必要的认证信息，无法确保证据的真实性和完整性。建议补充提供原始文件或办理公证手续后重新提交。',
            f'证据【{evidence_name}】的关联性不足：经AI分析，本证据所证明的事实与案件争议焦点的关联程度较低，单独使用难以形成有效的证明力。建议结合其他证据构建完整的证据链后再提交。',
            f'证据【{evidence_name}】的合法性存疑：{evidence_type}类证据的收集方式可能存在程序性问题。根据《最高人民法院关于民事诉讼证据的若干规定》，以侵害他人合法权益或者违反法律禁止性规定的方法取得的证据，不能作为认定案件事实的依据。建议核实证据的来源合法性后再提交。',
        ]
        return {
            "result": "fail",
            "status": "AI审核失败",
            "reason": random.choice(reasons),
        }


# ==================== CaseService ====================

class CaseService:
    """
    案件管理服务
    管理案件、证据、文档的全生命周期操作
    提供 Mock AI 分析、问答、证据审核等功能
    """

    def __init__(self, db: AsyncIOMotorDatabase, llm_service=None):
        """
        初始化案件管理服务

        Args:
            db: MongoDB 数据库实例
            llm_service: LLM 服务实例（可选，当前版本使用 Mock 数据）
        """
        self.db = db
        self.llm_service = llm_service

    # ═══════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════

    def _now(self) -> str:
        """获取当前 UTC 时间字符串"""
        return datetime.now(timezone.utc).isoformat()

    def _safe_oid(self, id_str: str) -> ObjectId:
        """安全地将字符串转换为 ObjectId"""
        try:
            return ObjectId(id_str)
        except Exception:
            return None

    def _doc_to_case_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 CaseInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "title": doc.get("title", ""),
            "case_type": doc.get("case_type", ""),
            "status": doc.get("status", "待分析"),
            "win_rate": doc.get("win_rate", 0),
            "evidence_uploaded": doc.get("evidence_uploaded", False),
            "court_level": doc.get("court_level", ""),
            "parties": doc.get("parties", []),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "tags": doc.get("tags", []),
        }

    def _doc_to_evidence_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 EvidenceInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "evidence_type": doc.get("evidence_type", ""),
            "description": doc.get("description", ""),
            "purpose": doc.get("purpose", ""),
            "status": doc.get("status", "待审核"),
            "audit_result": doc.get("audit_result"),
            "audit_reason": doc.get("audit_reason"),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_evidence_detail(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 EvidenceDetailInfo 格式"""
        info = self._doc_to_evidence_info(doc)
        info.update({
            "source": doc.get("source", ""),
            "collection_method": doc.get("collection_method", ""),
            "collection_note": doc.get("collection_note", ""),
            "uploader_name": doc.get("uploader_name", ""),
        })
        return info

    def _doc_to_document_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 DocumentInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "file_url": doc.get("file_url", ""),
            "doc_type": doc.get("doc_type", ""),
            "uploader": doc.get("uploader", ""),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_analysis_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 AnalysisInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "analysis_type": doc.get("analysis_type", ""),
            "content": doc.get("content", {}),
            "created_at": doc.get("created_at", ""),
        }

    def _doc_to_qa_info(self, doc: Dict) -> Dict:
        """将 MongoDB 文档转换为 QAInfo 格式"""
        return {
            "id": str(doc["_id"]),
            "question": doc.get("question", ""),
            "answer": doc.get("answer", ""),
            "created_at": doc.get("created_at", ""),
        }

    # ═══════════════════════════════════════
    # 案件 CRUD
    # ═══════════════════════════════════════

    async def list_cases(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: str = "",
        keyword: str = "",
    ) -> Tuple[List[Dict], int]:
        """
        获取用户案件列表（分页）

        Args:
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页条数
            status_filter: 状态筛选
            keyword: 关键词搜索

        Returns:
            (案件列表, 总数)
        """
        query: Dict[str, Any] = {
            "user_id": user_id,
            "is_deleted": {"$ne": True},
        }

        if status_filter:
            query["status"] = status_filter

        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("\"", "\\\"")
            query["$or"] = [
                {"title": {"$regex": escaped, "$options": "i"}},
                {"description": {"$regex": escaped, "$options": "i"}},
            ]

        total = await self.db.cases.count_documents(query)

        skip = (page - 1) * page_size
        cursor = (
            self.db.cases.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        cases = []
        async for doc in cursor:
            cases.append(self._doc_to_case_info(doc))

        return cases, total

    async def get_case(self, user_id: str, case_id: str) -> Optional[Dict]:
        """
        获取单个案件详情（含分析记录和问答历史）

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            案件详情字典，不存在返回 None
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return None

        case_doc = await self.db.cases.find_one({
            "_id": oid,
            "user_id": user_id,
            "is_deleted": {"$ne": True},
        })

        if not case_doc:
            return None

        case_info = self._doc_to_case_info(case_doc)
        case_info["description"] = case_doc.get("description", "")

        # 加载分析记录
        analyses = []
        analysis_cursor = self.db.case_analyses.find({"case_id": case_id}).sort("created_at", -1)
        async for a_doc in analysis_cursor:
            analyses.append(self._doc_to_analysis_info(a_doc))
        case_info["analyses"] = analyses

        # 加载问答历史
        qa_history = []
        qa_cursor = self.db.case_qa.find({"case_id": case_id}).sort("created_at", -1)
        async for q_doc in qa_cursor:
            qa_history.append(self._doc_to_qa_info(q_doc))
        case_info["qa_history"] = qa_history

        return case_info

    async def create_case(self, user_id: str, data: CaseCreateRequest) -> Dict:
        """
        创建新案件

        Args:
            user_id: 用户ID
            data: 创建请求数据

        Returns:
            创建的案件信息
        """
        now = self._now()
        case_doc = {
            "user_id": user_id,
            "title": data.title,
            "case_type": data.case_type,
            "description": data.description,
            "court_level": data.court_level,
            "parties": [p.model_dump() for p in data.parties],
            "tags": data.tags,
            "status": "待分析",
            "win_rate": 0,
            "evidence_uploaded": False,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.cases.insert_one(case_doc)
        case_id = str(result.inserted_id)

        logger.info(f"案件创建成功: id={case_id}, user_id={user_id}, title={data.title}")

        case_doc["_id"] = result.inserted_id
        return self._doc_to_case_info(case_doc)

    async def update_case(self, user_id: str, case_id: str, data: CaseUpdateRequest) -> Optional[Dict]:
        """
        更新案件信息

        Args:
            user_id: 用户ID
            case_id: 案件ID
            data: 更新请求数据

        Returns:
            更新后的案件信息，不存在返回 None
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return None

        update_fields = {"updated_at": self._now()}

        if data.title is not None:
            update_fields["title"] = data.title
        if data.description is not None:
            update_fields["description"] = data.description
        if data.status is not None:
            update_fields["status"] = data.status
        if data.court_level is not None:
            update_fields["court_level"] = data.court_level
        if data.tags is not None:
            update_fields["tags"] = data.tags
        if data.parties is not None:
            update_fields["parties"] = [p.model_dump() for p in data.parties]

        result = await self.db.cases.find_one_and_update(
            {"_id": oid, "user_id": user_id, "is_deleted": {"$ne": True}},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            logger.warning(f"案件更新失败: case_id={case_id}, user_id={user_id}")
            return None

        logger.info(f"案件更新成功: case_id={case_id}")
        return self._doc_to_case_info(result)

    async def delete_case(self, user_id: str, case_id: str) -> bool:
        """
        软删除案件

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            是否删除成功
        """
        oid = self._safe_oid(case_id)
        if oid is None:
            return False

        result = await self.db.cases.update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"is_deleted": True, "updated_at": self._now()}},
        )

        if result.modified_count > 0:
            logger.info(f"案件删除成功: id={case_id}, user_id={user_id}")
            return True

        return False

    # ═══════════════════════════════════════
    # AI 案件分析（Mock）
    # ═══════════════════════════════════════

    async def analyze_case(self, user_id: str, case_id: str) -> Optional[Dict]:
        """
        Mock AI 案件综合分析

        生成包含案情摘要、时间轴、事实分析、法律分析、
        定争分析、司法推理、参考判例的完整分析报告。

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            分析结果，案件不存在返回 None
        """
        case = await self.get_case(user_id, case_id)
        if case is None:
            return None

        # 更新状态为"分析中"
        await self.db.cases.update_one(
            {"_id": self._safe_oid(case_id)},
            {"$set": {"status": "分析中", "updated_at": self._now()}},
        )

        # 生成 Mock 分析内容
        content = _generate_case_overview_analysis(
            title=case["title"],
            case_type=case["case_type"],
            court_level=case["court_level"],
            parties=case.get("parties", []),
            description=case.get("description", ""),
        )

        # 模拟胜诉率
        win_rate = random.randint(45, 85)

        # 存储分析结果
        now = self._now()
        analysis_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "analysis_type": "case_overview",
            "content": content,
            "created_at": now,
        }
        analysis_result = await self.db.case_analyses.insert_one(analysis_doc)

        # 更新案件状态和胜诉率
        await self.db.cases.update_one(
            {"_id": self._safe_oid(case_id)},
            {"$set": {
                "status": "已分析",
                "win_rate": win_rate,
                "updated_at": now,
            }},
        )

        logger.info(f"案件分析完成: case_id={case_id}, win_rate={win_rate}")

        return {
            "id": str(analysis_result.inserted_id),
            "analysis_type": "case_overview",
            "content": content,
            "win_rate": win_rate,
            "created_at": now,
        }

    async def qa_case(self, user_id: str, case_id: str, question: str) -> Dict:
        """
        Mock AI 案件问答

        根据案件上下文生成法律问答回复。

        Args:
            user_id: 用户ID
            case_id: 案件ID
            question: 用户提问

        Returns:
            问答结果
        """
        case = await self.get_case(user_id, case_id)
        case_title = case["title"] if case else "未知案件"

        answer = _generate_mock_qa_answer(question, case_title)

        now = self._now()
        qa_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "created_at": now,
        }

        result = await self.db.case_qa.insert_one(qa_doc)

        logger.info(f"案件问答完成: case_id={case_id}")

        return self._doc_to_qa_info(qa_doc)

    # ═══════════════════════════════════════
    # 证据链分析（Mock）
    # ═══════════════════════════════════════

    async def analyze_evidence_chain(self, user_id: str, case_id: str) -> Optional[Dict]:
        """
        Mock 证据链分析

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            分析结果
        """
        case = await self.get_case(user_id, case_id)
        if case is None:
            return None

        # 加载证据列表
        evidence_list, _ = await self.list_evidence(user_id, case_id, page=1, page_size=100)

        content = _generate_mock_evidence_chain(evidence_list)

        now = self._now()
        analysis_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "analysis_type": "evidence_chain",
            "content": content,
            "created_at": now,
        }

        result = await self.db.case_analyses.insert_one(analysis_doc)

        logger.info(f"证据链分析完成: case_id={case_id}")

        return {
            "id": str(result.inserted_id),
            "analysis_type": "evidence_chain",
            "content": content,
            "created_at": now,
        }

    async def analyze_evidence_list(self, user_id: str, case_id: str) -> Optional[Dict]:
        """
        Mock 证据清单分析

        Args:
            user_id: 用户ID
            case_id: 案件ID

        Returns:
            分析结果
        """
        case = await self.get_case(user_id, case_id)
        if case is None:
            return None

        evidence_list, _ = await self.list_evidence(user_id, case_id, page=1, page_size=100)
        parties = case.get("parties", [])

        content = _generate_mock_evidence_list(evidence_list, parties)

        now = self._now()
        analysis_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "analysis_type": "evidence_list",
            "content": content,
            "created_at": now,
        }

        result = await self.db.case_analyses.insert_one(analysis_doc)

        logger.info(f"证据清单分析完成: case_id={case_id}")

        return {
            "id": str(result.inserted_id),
            "analysis_type": "evidence_list",
            "content": content,
            "created_at": now,
        }

    # ═══════════════════════════════════════
    # 证据管理
    # ═══════════════════════════════════════

    async def list_evidence(
        self,
        user_id: str,
        case_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int]:
        """
        获取案件证据列表（分页）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            page: 页码
            page_size: 每页条数

        Returns:
            (证据列表, 总数)
        """
        query = {"case_id": case_id, "is_deleted": {"$ne": True}}

        total = await self.db.case_evidence.count_documents(query)

        skip = (page - 1) * page_size
        cursor = (
            self.db.case_evidence.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        evidence_list = []
        async for doc in cursor:
            evidence_list.append(self._doc_to_evidence_info(doc))

        return evidence_list, total

    async def get_evidence(self, user_id: str, case_id: str, evidence_id: str) -> Optional[Dict]:
        """
        获取单个证据详情

        Args:
            user_id: 用户ID
            case_id: 案件ID
            evidence_id: 证据ID

        Returns:
            证据详情
        """
        oid = self._safe_oid(evidence_id)
        if oid is None:
            return None

        doc = await self.db.case_evidence.find_one({
            "_id": oid,
            "case_id": case_id,
            "is_deleted": {"$ne": True},
        })

        if not doc:
            return None

        return self._doc_to_evidence_detail(doc)

    async def create_evidence(
        self, user_id: str, case_id: str, data: EvidenceCreateRequest
    ) -> Dict:
        """
        创建证据

        Args:
            user_id: 用户ID
            case_id: 案件ID
            data: 创建请求数据

        Returns:
            创建的证据信息
        """
        now = self._now()
        evidence_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "name": data.name,
            "evidence_type": data.evidence_type,
            "description": data.description,
            "purpose": data.purpose,
            "source": data.source,
            "collection_method": data.collection_method,
            "collection_note": data.collection_note,
            "status": "待审核",
            "audit_result": None,
            "audit_reason": None,
            "uploader_name": "",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.case_evidence.insert_one(evidence_doc)

        # 更新案件证据标志
        await self.db.cases.update_one(
            {"_id": self._safe_oid(case_id)},
            {"$set": {"evidence_uploaded": True, "updated_at": now}},
        )

        logger.info(f"证据创建成功: id={str(result.inserted_id)}, case_id={case_id}")

        evidence_doc["_id"] = result.inserted_id
        return self._doc_to_evidence_info(evidence_doc)

    async def update_evidence(
        self, user_id: str, case_id: str, evidence_id: str, data: EvidenceUpdateRequest
    ) -> Optional[Dict]:
        """
        更新证据

        Args:
            user_id: 用户ID
            case_id: 案件ID
            evidence_id: 证据ID
            data: 更新请求数据

        Returns:
            更新后的证据信息
        """
        oid = self._safe_oid(evidence_id)
        if oid is None:
            return None

        update_fields = {"updated_at": self._now()}

        if data.name is not None:
            update_fields["name"] = data.name
        if data.evidence_type is not None:
            update_fields["evidence_type"] = data.evidence_type
        if data.description is not None:
            update_fields["description"] = data.description
        if data.purpose is not None:
            update_fields["purpose"] = data.purpose
        if data.status is not None:
            update_fields["status"] = data.status

        result = await self.db.case_evidence.find_one_and_update(
            {"_id": oid, "case_id": case_id, "is_deleted": {"$ne": True}},
            {"$set": update_fields},
            return_document=True,
        )

        if not result:
            return None

        logger.info(f"证据更新成功: evidence_id={evidence_id}")
        return self._doc_to_evidence_info(result)

    async def delete_evidence(self, user_id: str, case_id: str, evidence_id: str) -> bool:
        """
        删除证据（软删除）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            evidence_id: 证据ID

        Returns:
            是否删除成功
        """
        oid = self._safe_oid(evidence_id)
        if oid is None:
            return False

        result = await self.db.case_evidence.update_one(
            {"_id": oid, "case_id": case_id},
            {"$set": {"is_deleted": True, "updated_at": self._now()}},
        )

        if result.modified_count > 0:
            logger.info(f"证据删除成功: id={evidence_id}")
            return True

        return False

    # ═══════════════════════════════════════
    # 证据审核（Mock AI）
    # ═══════════════════════════════════════

    async def audit_evidence(self, user_id: str, case_id: str, evidence_id: str) -> Optional[Dict]:
        """
        Mock AI 证据审核

        随机判定通过或不通过，返回审核结果和原因。

        Args:
            user_id: 用户ID
            case_id: 案件ID
            evidence_id: 证据ID

        Returns:
            审核结果
        """
        evidence = await self.get_evidence(user_id, case_id, evidence_id)
        if evidence is None:
            return None

        audit_result = _generate_mock_evidence_audit(
            evidence_name=evidence["name"],
            evidence_type=evidence["evidence_type"],
        )

        now = self._now()

        # 更新证据状态
        await self.db.case_evidence.update_one(
            {"_id": self._safe_oid(evidence_id), "case_id": case_id},
            {"$set": {
                "status": audit_result["status"],
                "audit_result": audit_result["result"],
                "audit_reason": audit_result["reason"],
                "updated_at": now,
            }},
        )

        logger.info(f"证据审核完成: evidence_id={evidence_id}, result={audit_result['result']}")

        return {
            "evidence_id": evidence_id,
            **audit_result,
            "audited_at": now,
        }

    # ═══════════════════════════════════════
    # 文档管理
    # ═══════════════════════════════════════

    async def list_documents(
        self,
        user_id: str,
        case_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int]:
        """
        获取案件文档列表（分页）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            page: 页码
            page_size: 每页条数

        Returns:
            (文档列表, 总数)
        """
        query = {"case_id": case_id, "is_deleted": {"$ne": True}}

        total = await self.db.case_documents.count_documents(query)

        skip = (page - 1) * page_size
        cursor = (
            self.db.case_documents.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )

        documents = []
        async for doc in cursor:
            documents.append(self._doc_to_document_info(doc))

        return documents, total

    async def create_document(
        self, user_id: str, case_id: str, data: DocumentCreateRequest
    ) -> Dict:
        """
        创建文档记录

        Args:
            user_id: 用户ID
            case_id: 案件ID
            data: 创建请求数据

        Returns:
            创建的文档信息
        """
        now = self._now()
        doc_doc = {
            "case_id": case_id,
            "user_id": user_id,
            "name": data.name,
            "file_url": data.file_url,
            "doc_type": data.doc_type,
            "description": data.description,
            "uploader": "",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.case_documents.insert_one(doc_doc)

        logger.info(f"文档创建成功: id={str(result.inserted_id)}, case_id={case_id}")

        doc_doc["_id"] = result.inserted_id
        return self._doc_to_document_info(doc_doc)

    async def delete_document(self, user_id: str, case_id: str, document_id: str) -> bool:
        """
        删除文档（软删除）

        Args:
            user_id: 用户ID
            case_id: 案件ID
            document_id: 文档ID

        Returns:
            是否删除成功
        """
        oid = self._safe_oid(document_id)
        if oid is None:
            return False

        result = await self.db.case_documents.update_one(
            {"_id": oid, "case_id": case_id},
            {"$set": {"is_deleted": True, "updated_at": self._now()}},
        )

        if result.modified_count > 0:
            logger.info(f"文档删除成功: id={document_id}")
            return True

        return False
