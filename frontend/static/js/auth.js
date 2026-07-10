/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 鉴权状态管理
   ═══════════════════════════════════════ */

const Auth = {
  _token: null,
  _user: null,

  init() {
    this._token = localStorage.getItem('access_token');
    this._user = JSON.parse(localStorage.getItem('user') || 'null');
    this._updateUI();
  },

  getToken() {
    return this._token;
  },

  isLoggedIn() {
    return !!this._token;
  },

  getUser() {
    return this._user;
  },

  login(token, refreshToken, user) {
    this._token = token;
    this._user = user;
    localStorage.setItem('access_token', token);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));
    this._updateUI();
  },

  logout() {
    this._token = null;
    this._user = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    // 清除聊天会话记录，重新登录后开启新对话
    sessionStorage.removeItem('last_chat_session_id');
    this._updateUI();

    // 如果当前在需要登录的页面，跳转到首页
    const protectedPages = ['/profile', '/history'];
    const currentPath = window.location.pathname;
    if (protectedPages.includes(currentPath)) {
      window.location.href = '/';
    }
  },

  // 检查登录状态，未登录则跳转到登录页
  requireLogin() {
    if (!this.isLoggedIn()) {
      const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?redirect=${currentUrl}`;
      return false;
    }
    return true;
  },

  _updateUI() {
    // Header 用户区域
    const loggedInEls = document.querySelectorAll('.auth-logged-in');
    const loggedOutEls = document.querySelectorAll('.auth-logged-out');

    loggedInEls.forEach(el => {
      el.style.display = this.isLoggedIn() ? '' : 'none';
    });
    loggedOutEls.forEach(el => {
      el.style.display = this.isLoggedIn() ? 'none' : '';
    });

    // 用户头像
    const avatarEls = document.querySelectorAll('.header-avatar');
    if (avatarEls.length && this._user) {
      const initial = (this._user.nickname || '用')[0];
      avatarEls.forEach(el => { el.textContent = initial; });
    }
  },

  // 拦截需要登录的链接
  handleProtectedLink(event) {
    const link = event.currentTarget;
    if (!this.isLoggedIn()) {
      event.preventDefault();
      const redirect = encodeURIComponent(link.getAttribute('href'));
      window.location.href = `/login?redirect=${redirect}`;
    }
  },
};

// ── 初始化 ──
document.addEventListener('DOMContentLoaded', () => {
  Auth.init();

  // 拦截需要登录的链接
  document.querySelectorAll('[data-auth-required]').forEach(link => {
    link.addEventListener('click', (e) => {
      if (!Auth.isLoggedIn()) {
        e.preventDefault();
        const redirect = encodeURIComponent(link.getAttribute('href'));
        window.location.href = `/login?redirect=${redirect}`;
      }
    });
  });
});
