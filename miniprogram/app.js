/**
 * AI法律助手 微信小程序
 * 入口文件 — 全局生命周期、登录状态管理
 */
const authService = require('./services/auth');

App({
  globalData: {
    userInfo: null,
    isLoggedIn: false,
    currentSessionId: null,
    env: ''
  },

  onLaunch() {
    // 初始化云开发（保留兼容）
    if (wx.cloud) {
      wx.cloud.init({ env: this.globalData.env, traceUser: true });
    }

    this._checkLoginStatus();

    const systemInfo = wx.getSystemInfoSync();
    this.globalData.systemInfo = systemInfo;
    this.globalData.statusBarHeight = systemInfo.statusBarHeight;
    this.globalData.isIOS = systemInfo.system.indexOf('iOS') !== -1;
  },

  onShow() {
    this._checkLoginStatus();
  },

  _checkLoginStatus() {
    const isLoggedIn = authService.isLoggedIn();
    this.globalData.isLoggedIn = isLoggedIn;
    this.globalData.userInfo = isLoggedIn ? authService.getUserInfo() : null;
  },

  setLoginState(accessToken, refreshToken, userInfo) {
    authService.saveAuth(accessToken, refreshToken, userInfo);
    this.globalData.isLoggedIn = true;
    this.globalData.userInfo = userInfo;
  },

  clearLoginState() {
    authService.clearAuth();
    this.globalData.isLoggedIn = false;
    this.globalData.userInfo = null;
    this.globalData.currentSessionId = null;
  },

  getUserInfo() {
    return this.globalData.userInfo;
  },

  requireLogin(callback) {
    if (this.globalData.isLoggedIn) {
      callback && callback();
    } else {
      wx.navigateTo({ url: '/pages/login/login' });
    }
  }
});
