/**
 * AI法律助手 - 法条详情页
 */
const knowledgeService = require('../../services/knowledge');

Page({
  data: { lawId: '', detail: { name: '', year: '' }, chunks: [], loading: true },

  onLoad(options) {
    if (options.id) { this.setData({ lawId: options.id }); this._loadDetail(options.id); }
  },

  async _loadDetail(id) {
    try {
      const detail = await knowledgeService.getLawDetail(id);
      const chunks = (detail.chunks || []).map((c, i) => ({
        num: '第 ' + (i + 1) + ' 段',
        content: c.content || ''
      }));
      this.setData({
        detail: { name: detail.name || '未知法律', year: detail.year || '' },
        chunks, loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  }
});
