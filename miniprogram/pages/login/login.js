/**
 * AI法律助手 - 登录页
 * 对接后端: POST /api/v1/auth/login
 */
const authService = require('../../services/auth');

Page({
  data: {
    statusBarHeight: 0,
    username: '',
    password: '',
    agreeTerms: true,
    submitting: false
  },

  onLoad() {
    this.setData({ statusBarHeight: wx.getSystemInfoSync().statusBarHeight });
  },

  onUsernameInput(e) { this.setData({ username: e.detail.value }); },
  onPasswordInput(e) { this.setData({ password: e.detail.value }); },
  toggleAgree() { this.setData({ agreeTerms: !this.data.agreeTerms }); },

  /** 执行登录 — 按钮始终可点击，点击时校验 */
  onLogin() {
    const { username, password, agreeTerms, submitting } = this.data;
    if (submitting) return;

    const u = username.trim();
    if (!u || u.length < 2) {
      wx.showToast({ title: '用户名需至少2个字符', icon: 'none' });
      return;
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码需至少6个字符', icon: 'none' });
      return;
    }
    if (!agreeTerms) {
      wx.showToast({ title: '请先勾选同意用户协议', icon: 'none' });
      return;
    }

    console.log('[Login] 开始登录…', { username: u });
    this.setData({ submitting: true });

    authService.login(u, password, true)
      .then(result => {
        console.log('[Login] 登录成功:', result.user);
        getApp().setLoginState(result.access_token, result.refresh_token, result.user);
        wx.showToast({ title: '登录成功', icon: 'success', duration: 1200 });
        setTimeout(() => { wx.reLaunch({ url: '/pages/chat/chat' }); }, 1000);
      })
      .catch(e => {
        console.error('[Login] 登录失败:', e);
        this.setData({ submitting: false });
      });
  },

  goRegister() {
    wx.redirectTo({ url: '/pages/register/register' });
  }
});
