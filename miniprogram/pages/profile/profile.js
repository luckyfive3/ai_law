/**
 * AI法律助手 - 个人中心
 */
const userService = require('../../services/user');
const sessionService = require('../../services/session');

Page({
  data: { statusBarHeight: 0, isLoggedIn: false, userInfo: null, saveHistory: true },

  onLoad() { this.setData({ statusBarHeight: wx.getSystemInfoSync().statusBarHeight }); },
  onShow() {
    const app = getApp();
    this.setData({ isLoggedIn: app.globalData.isLoggedIn, userInfo: app.globalData.userInfo });
    if (app.globalData.isLoggedIn) this._loadProfile();
  },

  async _loadProfile() {
    try { const p = await userService.getProfile(); this.setData({ userInfo: p, saveHistory: p.privacy_save_history !== false }); } catch (e) {}
  },

  goLogin() { wx.navigateTo({ url: '/pages/login/login' }); },

  onEditProfile() {
    if (!this.data.isLoggedIn) { wx.navigateTo({ url: '/pages/login/login' }); return; }
    wx.showToast({ title: '功能开发中', icon: 'none' });
  },

  onPrivacyChange(e) { const val = e.detail.value; this.setData({ saveHistory: val }); userService.updatePrivacy(val).catch(() => {}); },

  async onClearHistory() {
    if (!this.data.isLoggedIn) return;
    const res = await new Promise(r => wx.showModal({ title: '确认清空', content: '将清空所有历史会话，此操作不可恢复', success: r }));
    if (!res.confirm) return;
    try { const result = await sessionService.clearAllSessions(); wx.showToast({ title: result.message || '已清空', icon: 'success' }); } catch (e) {}
  },

  onAbout() {
    wx.showModal({ title: 'AI法律助手', content: '基于法律法规知识库为您提供专业法律信息参考。\n\n本产品仅供参考，不构成法律建议。如有实际法律问题，请咨询专业律师。\n\n版本：v1.0', showCancel: false, confirmText: '知道了' });
  },

  async onLogout() {
    const res = await new Promise(r => wx.showModal({ title: '退出登录', content: '确定要退出登录吗？', success: r }));
    if (!res.confirm) return;
    getApp().clearLoginState();
    this.setData({ isLoggedIn: false, userInfo: null });
    wx.switchTab({ url: '/pages/chat/chat' });
  }
});
