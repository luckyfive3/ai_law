/**
 * AI法律助手 - 认证服务
 * 对接 ai_law 后端: POST /api/v1/auth/{register,login,refresh,logout}
 * 后端要求: agree_terms 必须为 true（Pydantic validator 强制校验）
 */
const api = require('../utils/api');

const authService = {

  /** 注册 */
  register(username, password, confirmPassword, agreeTerms = true) {
    console.log('[Auth] 注册:', { username, agreeTerms });
    return api.post('/auth/register', {
      username,
      password,
      confirm_password: confirmPassword,
      agree_terms: agreeTerms
    }, { auth: false, showLoading: true, loadingText: '注册中…' });
  },

  /** 登录 */
  login(username, password, agreeTerms = true) {
    console.log('[Auth] 登录:', { username });
    return api.post('/auth/login', {
      username,
      password,
      agree_terms: agreeTerms
    }, { auth: false, showLoading: true, loadingText: '登录中…' });
  },

  /** 刷新 Token */
  refreshToken(refreshToken) {
    return api.post('/auth/refresh', {
      refresh_token: refreshToken
    }, { auth: false });
  },

  /** 退出登录 */
  logout() {
    return api.post('/auth/logout', {}, { silent: true });
  },

  /** 保存登录凭证到本地存储 */
  saveAuth(accessToken, refreshToken, userInfo) {
    wx.setStorageSync('access_token', accessToken);
    wx.setStorageSync('refresh_token', refreshToken);
    wx.setStorageSync('user_info', userInfo);
    console.log('[Auth] Token 已保存');
  },

  /** 检查是否已登录 */
  isLoggedIn() {
    const token = wx.getStorageSync('access_token');
    return !!token && token.length > 10;
  },

  /** 获取缓存的用户信息 */
  getUserInfo() {
    return wx.getStorageSync('user_info') || null;
  },

  /** 清除所有登录凭证 */
  clearAuth() {
    wx.removeStorageSync('access_token');
    wx.removeStorageSync('refresh_token');
    wx.removeStorageSync('user_info');
    console.log('[Auth] 登录态已清除');
  }
};

module.exports = authService;
