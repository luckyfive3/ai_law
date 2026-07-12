/**
 * AI法律助手 微信小程序 — 全局配置
 * 对接 ai_law 后端三大基础设施：
 *   1. MongoDB (阿里云 ECS, ai_law 库)
 *   2. DeepSeek Chat API (deepseek-chat 模型)
 *   3. RAGFlow 法律知识库 (阿里云 123.57.85.126, 7 个数据集)
 */
const config = {

  // ═══ 后端 API 地址 ═══
  // 通过 Nginx 代理访问（443端口 /api/ → backend:8080）
  // 参照 frontend/routes/api.py: BACKEND_URL = os.getenv("BACKEND_URL", "https://123.57.85.126")
  API_BASE_URL: 'https://123.57.85.126',
  API_PREFIX: '/api/v1',

  // ═══ DeepSeek 配置 (透传给后端) ═══
  // 模型: deepseek-chat, temperature: 0.2, max_tokens: 2048
  LLM_PROVIDER: 'deepseek',
  LLM_MODEL: 'deepseek-chat',

  // ═══ RAGFlow 法律知识库 ═══
  // 地址: http://123.57.85.126:8081  |  API Key: ragflow-OmEz***
  // 7 个数据集 ID 与模块映射（双通道：小程序直连 + 后端代理）
  RAGFLOW: {
    BASE_URL: 'http://123.57.85.126:8081',
    API_KEY: 'ragflow-REDACTED',
    ALL_DATASET_ID: 'e2d5546a7c5011f19855b7acec531fcb',
    DATASETS: {
      all:       { id: 'e2d5546a7c5011f19855b7acec531fcb', name: '综合' },
      marriage:  { id: '350004b87cdf11f199b8b7e53ff0faa6', name: '婚姻家庭' },
      labor:     { id: '53fdb5127ce011f199b8b7e53ff0faa6', name: '劳动纠纷' },
      contract:  { id: '7e7270a87ce011f199b8b7e53ff0faa6', name: '合同纠纷' },
      traffic:   { id: '9734a8187ce011f199b8b7e53ff0faa6', name: '交通事故' },
      housing:   { id: 'be93c2947ce111f199b8b7e53ff0faa6', name: '房产纠纷' },
      consumer:  { id: 'fc5695a27ce111f199b8b7e53ff0faa6', name: '消费维权' }
    },
    MODULES: {
      marriage:  { id: '350004b87cdf11f199b8b7e53ff0faa6', name: '婚姻家庭' },
      labor:     { id: '53fdb5127ce011f199b8b7e53ff0faa6', name: '劳动纠纷' },
      contract:  { id: '7e7270a87ce011f199b8b7e53ff0faa6', name: '合同纠纷' },
      traffic:   { id: '9734a8187ce011f199b8b7e53ff0faa6', name: '交通事故' },
      housing:   { id: 'be93c2947ce111f199b8b7e53ff0faa6', name: '房产纠纷' },
      consumer:  { id: 'fc5695a27ce111f199b8b7e53ff0faa6', name: '消费维权' }
    }
  },

  // ═══ 请求超时 ═══
  REQUEST_TIMEOUT: 30000,
  SSE_TIMEOUT: 120000,

  // ═══ 存储 Key ═══
  TOKEN_KEY: 'access_token',
  REFRESH_TOKEN_KEY: 'refresh_token',
  USER_INFO_KEY: 'user_info',

  // ═══ 常量 ═══
  MAX_MESSAGE_LENGTH: 2000,
  DEFAULT_PAGE_SIZE: 20,

  // ═══ 法律分类映射 (与后端 knowledge_service.py 一致) ═══
  LAW_CATEGORIES: {
    all: '全部',
    constitution: '宪法',
    civil: '民法',
    criminal: '刑法',
    administrative: '行政法',
    economic: '经济法',
    labor: '劳动法',
    marriage: '婚姻家庭',
    contract: '合同法',
    traffic: '交通法',
    property: '物权房产',
    company: '公司法',
    intellectual_property: '知识产权',
    consumer: '消费者权益',
    procedural: '诉讼程序',
    other: '其他'
  },

  // ═══ 咨询分类 (对应后端 6 个专业模块) ═══
  CONSULT_MODULES: [
    { value: '', name: '综合咨询', desc: '不限领域' },
    { value: 'marriage', name: '婚姻家庭', desc: '离婚、继承、抚养' },
    { value: 'labor', name: '劳动纠纷', desc: '辞退、工资、工伤' },
    { value: 'contract', name: '合同纠纷', desc: '违约、解除、效力' },
    { value: 'traffic', name: '交通事故', desc: '责任认定、赔偿' },
    { value: 'housing', name: '房产纠纷', desc: '买卖、租赁、物业' },
    { value: 'consumer', name: '消费维权', desc: '假货、欺诈、退赔' }
  ],

  // ═══ 欢迎引导问题 ═══
  WELCOME_QUESTIONS: [
    '被公司无故辞退，能要求多少赔偿？',
    '离婚时房产怎么分割？',
    '交通事故责任认定有哪些规定？',
    '合同违约怎么维权？',
    '买到假货商家不给退怎么办？',
    '租房押金不退怎么办？'
  ],

  // ═══ 错误码映射 (与后端 errcode.py 一致) ═══
  ERROR_CODES: {
    0: '操作成功',
    40003: '请求参数无效',
    40004: '请先同意用户协议',
    40005: '内容过长',
    40100: '请先登录',
    40101: '登录已过期，请重新登录',
    40102: '登录凭证无效',
    40104: '用户名或密码错误',
    40200: '请求过于频繁，请稍后再试',
    40202: '服务繁忙，请稍后再试',
    40300: '内容包含敏感信息，请修改后重试',
    40301: 'AI 无法回答该问题',
    40400: '会话不存在',
    40402: '用户不存在',
    40403: '法律条文不存在',
    50000: '服务器内部错误，请稍后再试',
    50001: 'AI 服务暂时不可用',
    50002: '搜索服务暂时不可用',
    50003: '数据库操作失败'
  }
};

module.exports = config;
