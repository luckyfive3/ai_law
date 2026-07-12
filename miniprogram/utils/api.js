/**
 * AI法律助手 微信小程序 — 请求封装
 * 对接 ai_law FastAPI 后端 (123.57.85.126:8080)
 * JWT 认证 + SSE 流式 + 自动 Token 刷新 + 详细错误日志
 */
const config = require('./config');

const api = {

  /**
   * 通用请求
   * @param {string} method - GET/POST/PUT/DELETE
   * @param {string} path   - API 路径（不含 /api/v1 前缀）
   * @param {object|null} data - 请求体
   * @param {object} options - auth, showLoading, loadingText, silent
   */
  request(method, path, data = null, options = {}) {
    const { auth = true, showLoading = false, loadingText = '加载中…', silent = false } = options;

    if (showLoading) wx.showLoading({ title: loadingText, mask: true });

    const header = { 'Content-Type': 'application/json' };
    if (auth) {
      const token = wx.getStorageSync(config.TOKEN_KEY);
      if (token) header['Authorization'] = `Bearer ${token}`;
    }

    const url = config.API_BASE_URL + config.API_PREFIX + path;
    // 优先尝试直接访问 8080 后端（本地开发/ECS 直连）
    // 如失败，微信开发者工具勾选「不校验合法域名」
    console.log(`[API] ${method} ${url}`, data || '');

    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method,
        data,
        header,
        timeout: config.REQUEST_TIMEOUT,
        success: (res) => {
          if (showLoading) wx.hideLoading();
          const statusCode = res.statusCode;
          const body = res.data || {};
          const { code, message, data: resData } = body;

          // 成功：code===0 或 HTTP 2xx
          if (code === 0) {
            console.log(`[API] ✅ ${method} ${path}`, resData);
            resolve(resData);
            return;
          }

          if (statusCode === 200 && code === undefined) {
            console.log(`[API] ✅ ${method} ${path} (no code field)`, body);
            resolve(body);
            return;
          }

          // HTTP 422 → Pydantic 校验失败
          if (statusCode === 422) {
            const detail = body.detail || [];
            const errors = Array.isArray(detail) ? detail.map(d => d.msg || '').join('; ') : String(detail);
            console.error(`[API] ❌ 422 Validation Error: ${method} ${path}`, errors, body);
            if (!silent) wx.showToast({ title: '请求格式错误: ' + errors, icon: 'none', duration: 3000 });
            reject({ code: 422, message: errors, data: body });
            return;
          }

          // HTTP 401 → 密码错误或未授权
          if (statusCode === 401) {
            // detail 可能是 { code, message } 对象
            const detailMsg = (body.detail && body.detail.message) || message || '用户名或密码错误';
            if (code === 40101 && auth) {
              this._refreshAndRetry(method, path, data, options).then(resolve).catch(reject);
              return;
            }
            // 40102: 登录凭证无效（Token 被篡改/secret 变化/后端重启等），无法刷新，直接清除登录态
            if (code === 40102 && auth) {
              console.error(`[API] ❌ 401 Invalid Credentials: ${method} ${path}`, detailMsg);
              this._clearAuthAndRedirect();
              if (!silent) wx.showToast({ title: '登录凭证无效，请重新登录', icon: 'none', duration: 2000 });
              reject({ code: code || 401, message: detailMsg });
              return;
            }
            console.error(`[API] ❌ 401 Unauthorized: ${method} ${path}`, detailMsg);
            if (!silent) wx.showToast({ title: detailMsg, icon: 'none', duration: 2500 });
            reject({ code: code || 401, message: detailMsg });
            return;
          }

          // HTTP 400 → 参数错误
          if (statusCode === 400) {
            const detailMsg = (body.detail && body.detail.message) || message || '请求参数无效';
            console.error(`[API] ❌ 400 Bad Request: ${method} ${path}`, detailMsg);
            if (!silent) wx.showToast({ title: detailMsg, icon: 'none', duration: 2500 });
            reject({ code: code || 400, message: detailMsg });
            return;
          }

          // 其他错误
          const errMsg = config.ERROR_CODES[code] || message || '请求失败';
          console.error(`[API] ❌ ${method} ${path} status=${statusCode} code=${code}`, errMsg, body);
          if (!silent) wx.showToast({ title: errMsg, icon: 'none', duration: 2500 });
          reject({ code, message: errMsg, data: resData });
        },
        fail: (err) => {
          if (showLoading) wx.hideLoading();
          const errStr = err.errMsg || '';
          const msg = errStr.includes('timeout') ? '请求超时，请检查网络'
            : errStr.includes('fail') ? '网络连接失败，请检查后端服务是否启动'
            : '网络异常，请稍后再试';
          console.error(`[API] ❌ Network Error: ${method} ${path}`, errStr);
          if (!silent) wx.showToast({ title: msg, icon: 'none', duration: 3000 });
          reject({ code: -1, message: msg, raw: err });
        }
      });
    });
  },

  get(path, params = {}, options = {}) {
    const query = Object.keys(params)
      .filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
      .map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join('&');
    return this.request('GET', query ? `${path}?${query}` : path, null, options);
  },

  post(path, data = {}, options = {}) {
    return this.request('POST', path, data, options);
  },

  put(path, data = {}, options = {}) {
    return this.request('PUT', path, data, options);
  },

  delete(path, options = {}) {
    return this.request('DELETE', path, null, options);
  },

  /** SSE 流式聊天 */
  streamChat(sessionId, content, category = '', callbacks = {}) {
    const { onSearching, onChunk, onDone, onError } = callbacks;
    const token = wx.getStorageSync(config.TOKEN_KEY);
    const url = config.API_BASE_URL + config.API_PREFIX + '/chat/stream';

    console.log('[SSE] POST /chat/stream', { session_id: sessionId, content: content.substring(0, 30), category });

    const reqTask = wx.request({
      url,
      method: 'POST',
      data: { session_id: sessionId, content, category: category || '' },
      header: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      enableChunked: true,
      timeout: config.SSE_TIMEOUT || 120000,
      success: () => {},
      fail: (err) => {
        console.error('[SSE] ❌ Request failed:', err.errMsg);
        onError && onError(err.errMsg || '连接失败');
      }
    });

    let buffer = '';
    reqTask.onChunkReceived((chunk) => {
      try {
        let text;
        if (typeof chunk.data === 'string') {
          text = chunk.data;
        } else if (chunk.data instanceof ArrayBuffer) {
          const arr = new Uint8Array(chunk.data);
          text = '';
          for (let i = 0; i < arr.length; i++) text += String.fromCharCode(arr[i]);
          text = decodeURIComponent(escape(text));
        } else {
          text = String(chunk.data || '');
        }
        buffer += text;
        const lines = buffer.split('\n');
        buffer = '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (!trimmed.startsWith('data: ')) { buffer = trimmed; continue; }

          try {
            const jsonStr = trimmed.substring(6);
            const data = JSON.parse(jsonStr);

            if (data.status === 'searching') { onSearching && onSearching(); }
            else if (data.done === true) { onDone && onDone({ messageId: data.message_id, laws: data.laws || [], tokens: data.tokens || {} }); }
            else if (data.status === 'error') { onError && onError(data.error || '生成失败'); }
            else if (data.content !== undefined) { onChunk && onChunk(data.content); }
          } catch (e) { buffer = trimmed; }
        }
      } catch (e) {
        console.warn('[SSE] chunk parse error:', e);
      }
    });

    return reqTask;
  },

  /** 刷新 Token 并重试原请求 */
  async _refreshAndRetry(method, path, data, options) {
    try {
      const refreshToken = wx.getStorageSync(config.REFRESH_TOKEN_KEY);
      if (!refreshToken) throw new Error('no_refresh_token');

      console.log('[API] 🔄 Token 过期，尝试刷新...');
      const result = await this.request('POST', '/auth/refresh', { refresh_token: refreshToken }, { auth: false, silent: true });

      wx.setStorageSync(config.TOKEN_KEY, result.access_token);
      wx.setStorageSync(config.REFRESH_TOKEN_KEY, result.refresh_token);
      console.log('[API] ✅ Token 刷新成功，重试原请求');
      return await this.request(method, path, data, options);

    } catch (e) {
      console.error('[API] ❌ Token 刷新失败，清除登录态');
      wx.removeStorageSync(config.TOKEN_KEY);
      wx.removeStorageSync(config.REFRESH_TOKEN_KEY);
      wx.removeStorageSync(config.USER_INFO_KEY);

      const pages = getCurrentPages();
      const current = pages[pages.length - 1];
      // 只对非登录/注册页跳转
      if (current && current.route !== 'pages/login/login' && current.route !== 'pages/register/register') {
        wx.redirectTo({ url: '/pages/login/login' });
      }
      throw e;
    }
  },

  /** 清除登录态并跳转登录页 */
  _clearAuthAndRedirect() {
    wx.removeStorageSync(config.TOKEN_KEY);
    wx.removeStorageSync(config.REFRESH_TOKEN_KEY);
    wx.removeStorageSync(config.USER_INFO_KEY);

    const app = getApp();
    if (app && app.clearLoginState) app.clearLoginState();

    const pages = getCurrentPages();
    const current = pages[pages.length - 1];
    if (current && current.route !== 'pages/login/login' && current.route !== 'pages/register/register') {
      wx.redirectTo({ url: '/pages/login/login' });
    }
  }
};

module.exports = api;
