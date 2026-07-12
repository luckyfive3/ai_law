/**
 * AI法律助手 - 会话服务
 */
const api = require('../utils/api');

module.exports = {
  createSession(title = '', category = '') {
    return api.post('/sessions', { title, category });
  },
  getSessions(page = 1, pageSize = 20, keyword = '') {
    return api.get('/sessions', { page, page_size: pageSize, keyword });
  },
  getSessionDetail(sessionId, page = 1, pageSize = 50) {
    return api.get(`/sessions/${sessionId}`, { page, page_size: pageSize });
  },
  deleteSession(sessionId) {
    return api.delete(`/sessions/${sessionId}`);
  },
  clearAllSessions() {
    return api.delete('/sessions/clear-all');
  }
};
