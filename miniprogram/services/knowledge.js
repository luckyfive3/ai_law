/**
 * AI法律助手 - 法律知识库服务
 *
 * 双通道访问 RAGFlow：
 *   通道 A（优先）：通过后端 /api/v1/knowledge/* 代理
 *   通道 B（降级）：直连 RAGFlow http://123.57.85.126:8081/api/v1/
 *
 * RAGFlow 7 个数据集 ID 与领域映射：
 *   综合: e2d5546a...  婚姻: 350004b8...  劳动: 53fdb512...
 *   合同: 7e7270a8...  交通: 9734a818...  房产: be93c294...
 *   消费: fc5695a2...
 */
const config = require('../utils/config');
const api = require('../utils/api');
const RAGFLOW = config.RAGFLOW;

// ════════════════════════════════
// RAGFlow 直连客户端
// ════════════════════════════════
function ragflowGet(path, params) {
  const qs = params ? Object.keys(params)
    .filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
    .map(k => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
    .join('&') : '';
  const url = RAGFLOW.BASE_URL + '/api/v1' + path + (qs ? '?' + qs : '');
  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method: 'GET',
      header: { 'Authorization': 'Bearer ' + RAGFLOW.API_KEY },
      timeout: 15000,
      success: (res) => {
        if (res.statusCode === 200) {
          const d = res.data;
          resolve((d && d.code === 0) ? d.data : (d.data || d));
        } else reject({ code: res.statusCode });
      },
      fail: (err) => reject(err)
    });
  });
}

/** 根据分类 key 获取数据集列表 */
function datasetsFor(key) {
  if (!key || key === 'all' || key === '') return Object.values(RAGFLOW.DATASETS || {});
  const m = RAGFLOW.MODULES && RAGFLOW.MODULES[key];
  const d = RAGFLOW.DATASETS && RAGFLOW.DATASETS[key];
  return d ? [d] : (m ? [m] : Object.values(RAGFLOW.DATASETS || {}));
}

function cleanName(n) {
  if (!n) return '';
  let s = n;
  const i = s.lastIndexOf('/');
  if (i >= 0) s = s.substring(i + 1);
  if (s.toLowerCase().endsWith('.docx')) s = s.substring(0, s.length - 5);
  return s.replace(/_\d{8}$/, '');
}

// ════════════════════════════════
// 导出
// ════════════════════════════════
module.exports = {

  getCategories() {
    return api.get('/knowledge/categories', {}, { auth: false });
  },

  async getDocuments(categoryKey, page, pageSize) {
    try {
      return await api.get('/knowledge/documents', {
        filter_type: 'category',
        filter_value: categoryKey || 'all',
        page: page || 1,
        page_size: pageSize || 20
      }, { auth: false });
    } catch (e) {
      return await this._docsFromRAGFlow(categoryKey, page, pageSize);
    }
  },

  async _docsFromRAGFlow(categoryKey, page, pageSize) {
    page = page || 1; pageSize = pageSize || 20;
    const datasets = datasetsFor(categoryKey);
    const all = [];
    for (const ds of datasets) {
      try {
        const data = await ragflowGet('/datasets/' + ds.id + '/documents', { page: 1, page_size: 500 });
        const docs = (data && data.docs) ? data.docs : (Array.isArray(data) ? data : []);
        for (const d of docs) {
          all.push({
            id: String(d.id || ''),
            name: cleanName(d.name) || ds.name,
            category: ds.name,
            chunk_count: d.chunk_count || 0
          });
        }
      } catch (e) {}
    }
    const start = (page - 1) * pageSize;
    return { items: all.slice(start, start + pageSize), total: all.length };
  },

  async search(keyword, categoryKey, page, pageSize) {
    try {
      return await api.get('/knowledge/search', {
        keyword: keyword || '',
        page: page || 1,
        page_size: pageSize || 10
      }, { auth: false });
    } catch (e) {
      return await this._searchFromRAGFlow(keyword, categoryKey, page, pageSize);
    }
  },

  async _searchFromRAGFlow(keyword, categoryKey, page, pageSize) {
    page = page || 1; pageSize = pageSize || 10;
    const datasets = datasetsFor(categoryKey);
    const map = new Map();
    for (const ds of datasets) {
      try {
        const data = await ragflowGet('/retrieval', { dataset_ids: [ds.id], question: keyword, top_k: pageSize * 3 });
        let chunks = [];
        if (data && data.chunks) chunks = data.chunks;
        else if (Array.isArray(data)) chunks = data;
        for (const c of chunks) {
          const cid = c.id || c.chunk_id || '';
          if (!map.has(cid)) {
            map.set(cid, {
              id: cid,
              name: cleanName(c.document_name || c.doc_name || ''),
              content: c.content || '',
              similarity: c.similarity || 0,
              dataset_name: ds.name
            });
          }
        }
      } catch (e) {}
    }
    const sorted = Array.from(map.values()).sort((a, b) => (b.similarity || 0) - (a.similarity || 0));
    const start = (page - 1) * pageSize;
    return { items: sorted.slice(start, start + pageSize), count: sorted.length };
  },

  async getLawDetail(docId) {
    try {
      return await api.get('/knowledge/laws/' + docId, {}, { auth: false });
    } catch (e) {
      return await this._detailFromRAGFlow(docId);
    }
  },

  async _detailFromRAGFlow(docId) {
    const datasets = Object.values(RAGFLOW.DATASETS || {});
    for (const ds of datasets) {
      try {
        const data = await ragflowGet('/datasets/' + ds.id + '/documents/' + docId + '/chunks', { page: 1, page_size: 500 });
        let chunks = [];
        if (data && data.chunks) chunks = data.chunks;
        else if (Array.isArray(data)) chunks = data;
        if (chunks.length > 0) {
          let name = '';
          try {
            const docsData = await ragflowGet('/datasets/' + ds.id + '/documents', { page: 1, page_size: 500 });
            const docs = (docsData && docsData.docs) ? docsData.docs : (Array.isArray(docsData) ? docsData : []);
            const found = docs.find(d => String(d.id) === String(docId));
            if (found) name = cleanName(found.name);
          } catch (e) {}
          return {
            id: docId, name: name || '法律条文', year: '',
            chunks: chunks.map(c => ({ id: String(c.id || ''), content: c.content || '' }))
          };
        }
      } catch (e) {}
    }
    throw new Error('文档不存在或未解析');
  }
};
