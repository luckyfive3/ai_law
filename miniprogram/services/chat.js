/**
 * AI法律助手 - 聊天服务
 */
const api = require('../utils/api');

module.exports = {
  sendMessage(sessionId, content, category = '', callbacks = {}) {
    return api.streamChat(sessionId, content, category, callbacks);
  },
  getMessages(sessionId, page = 1, pageSize = 50) {
    return api.get(`/chat/${sessionId}/messages`, { page, page_size: pageSize });
  },
  exportMessages(sessionId) {
    return api.get(`/chat/${sessionId}/export`);
  }
};
