/**
 * AI法律助手 - 历史记录
 */
const sessionService = require('../../services/session');

Page({
  data: {
    sessions: [], keyword: '', page: 1, hasMore: false, loading: false,
    listTop: 0, listHeight: 500
  },

  onLoad() {
    const sys = wx.getSystemInfoSync();
    // 搜索栏高度约 56px（padding上下各约16rpx+输入框内部高度）
    const barH = 56;
    this.setData({
      listTop: barH,
      listHeight: sys.windowHeight - barH
    });
  },

  onShow() {
    const app = getApp();
    if (!app.globalData.isLoggedIn) { wx.navigateTo({ url: '/pages/login/login' }); return; }
    this.setData({ page: 1, sessions: [] });
    this._loadSessions();
  },

  onPullDownRefresh() { this.setData({ page: 1, sessions: [] }); this._loadSessions().then(() => wx.stopPullDownRefresh()); },

  async _loadSessions() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const data = await sessionService.getSessions(this.data.page, 20, this.data.keyword);
      const list = (data.list || []).map(s => ({ ...s, updated_at_text: this._fmtTime(s.updated_at) }));
      this.setData({ sessions: this.data.page === 1 ? list : [...this.data.sessions, ...list], hasMore: data.has_more || false, loading: false });
    } catch (e) { this.setData({ loading: false }); }
  },

  onLoadMore() { if (!this.data.hasMore || this.data.loading) return; this.setData({ page: this.data.page + 1 }); this._loadSessions(); },

  onSearchInput(e) { this.setData({ keyword: e.detail.value }); },
  onSearch() { this.setData({ page: 1, sessions: [] }); this._loadSessions(); },

  onTapSession(e) {
    getApp().globalData.currentSessionId = e.currentTarget.dataset.id;
    wx.switchTab({ url: '/pages/chat/chat' });
  },

  async onDelete(e) {
    const id = e.currentTarget.dataset.id;
    const res = await new Promise(r => wx.showModal({ title: '确认删除', content: '删除后不可恢复', success: r }));
    if (!res.confirm) return;
    try { await sessionService.deleteSession(id); this.setData({ sessions: this.data.sessions.filter(s => s.id !== id) }); wx.showToast({ title: '已删除', icon: 'success' }); } catch (e) {}
  },

  _fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso), n = new Date(), diff = n - d;
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    return `${d.getMonth() + 1}/${d.getDate()}`;
  }
});
