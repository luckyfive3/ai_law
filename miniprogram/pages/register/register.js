/**
 * AI法律助手 - 注册页
 * 对接后端: POST /api/v1/auth/register
 */
const authService = require('../../services/auth');

Page({
  data: {
    statusBarHeight: 0,
    username: '',
    password: '',
    confirmPassword: '',
    agreeTerms: false,
    submitting: false
  },

  onLoad() {
    this.setData({ statusBarHeight: wx.getSystemInfoSync().statusBarHeight });
  },

  onUsernameInput(e) { this.setData({ username: e.detail.value }); },
  onPasswordInput(e) { this.setData({ password: e.detail.value }); },
  onConfirmPwdInput(e) { this.setData({ confirmPassword: e.detail.value }); },
  toggleAgree() { this.setData({ agreeTerms: !this.data.agreeTerms }); },

  /** 执行注册 — 按钮始终可点击，点击时做校验并提示 */
  onRegister() {
    const { username, password, confirmPassword, agreeTerms, submitting } = this.data;
    if (submitting) return;

    // 逐项校验 + 明确提示
    const u = username.trim();
    if (!u || u.length < 2) {
      wx.showToast({ title: '用户名需至少2个字符', icon: 'none' });
      return;
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码需至少6个字符', icon: 'none' });
      return;
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码输入不一致', icon: 'none' });
      return;
    }
    if (!agreeTerms) {
      wx.showToast({ title: '请先勾选同意用户协议', icon: 'none' });
      return;
    }

    console.log('[Register] 开始注册…', { username: u });
    this.setData({ submitting: true });

    authService.register(u, password, confirmPassword, true)
      .then(result => {
        console.log('[Register] 注册成功:', result.user);
        getApp().setLoginState(result.access_token, result.refresh_token, result.user);
        wx.showToast({ title: '注册成功', icon: 'success', duration: 1200 });
        setTimeout(() => { wx.reLaunch({ url: '/pages/chat/chat' }); }, 1000);
      })
      .catch(e => {
        console.error('[Register] 注册失败:', e);
        this.setData({ submitting: false });
      });
  },

  goLogin() {
    wx.redirectTo({ url: '/pages/login/login' });
  }
});
