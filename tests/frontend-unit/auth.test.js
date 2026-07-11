/**
 * Auth 鉴权状态管理 + 防抖搜索 单元测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// ── Auth 状态机实现（摘自 auth.js） ──

class AuthState {
  constructor() {
    this._token = null;
    this._user = null;
  }

  getToken() { return this._token; }
  isLoggedIn() { return !!this._token; }
  getUser() { return this._user; }

  login(token, refreshToken, user) {
    this._token = token;
    this._user = user;
    localStorage.setItem('access_token', token);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));
  }

  logout() {
    this._token = null;
    this._user = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('last_chat_session_id');
  }

  requireLogin(currentPath = '/chat') {
    if (!this.isLoggedIn()) {
      const redirect = encodeURIComponent(currentPath);
      return { ok: false, redirect: `/login?redirect=${redirect}` };
    }
    return { ok: true };
  }

  init() {
    this._token = localStorage.getItem('access_token');
    const raw = localStorage.getItem('user');
    this._user = raw ? JSON.parse(raw) : null;
  }
}

// ── 防抖搜索（摘自 history.js） ──

class DebouncedSearch {
  constructor(delay = 400) {
    this.delay = delay;
    this.keyword = '';
    this._timer = null;
  }

  input(value, callback) {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => {
      this.keyword = value.trim();
      if (callback) callback(this.keyword);
    }, this.delay);
  }
}

// ── 测试 ──

describe('Auth 鉴权状态管理', () => {
  let auth;

  beforeEach(() => {
    globalThis._resetStorage();
    auth = new AuthState();
  });

  it('初始状态：未登录', () => {
    expect(auth.isLoggedIn()).toBe(false);
    expect(auth.getToken()).toBeNull();
    expect(auth.getUser()).toBeNull();
  });

  it('login 设置 token 和用户信息并持久化到 localStorage', () => {
    auth.login('access-123', 'refresh-456', {
      id: 'uid1', username: 'test', nickname: '测试',
    });
    expect(auth.isLoggedIn()).toBe(true);
    expect(auth.getToken()).toBe('access-123');
    expect(auth.getUser().nickname).toBe('测试');
    expect(localStorage.getItem('access_token')).toBe('access-123');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-456');
  });

  it('logout 清除所有状态', () => {
    auth.login('t', 'r', { id: 'u' });
    sessionStorage.setItem('last_chat_session_id', 's123');

    auth.logout();

    expect(auth.isLoggedIn()).toBe(false);
    expect(auth.getToken()).toBeNull();
    expect(auth.getUser()).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(sessionStorage.getItem('last_chat_session_id')).toBeNull();
  });

  it('requireLogin 已登录返回 { ok: true }', () => {
    auth.login('t', 'r', { id: 'u' });
    expect(auth.requireLogin()).toEqual({ ok: true });
  });

  it('requireLogin 未登录返回跳转 URL', () => {
    const result = auth.requireLogin('/chat');
    expect(result.ok).toBe(false);
    expect(result.redirect).toContain('/login?redirect=');
  });

  it('getUser 返回完整用户信息', () => {
    auth.login('t', 'r', { id: 'u1', username: 'user1', nickname: '小红' });
    expect(auth.getUser().username).toBe('user1');
  });

  it('init 从 localStorage 恢复登录态', () => {
    localStorage.setItem('access_token', 'saved-token');
    localStorage.setItem('user', JSON.stringify({ id: 'u1', nickname: '老用户' }));
    auth.init();
    expect(auth.isLoggedIn()).toBe(true);
    expect(auth.getToken()).toBe('saved-token');
    expect(auth.getUser().nickname).toBe('老用户');
  });

  it('init 无 token 时保持未登录', () => {
    auth.init();
    expect(auth.isLoggedIn()).toBe(false);
  });
});

describe('History 防抖搜索', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('延迟后触发搜索回调', () => {
    const search = new DebouncedSearch(300);
    let result = null;

    search.input('劳动法', (kw) => { result = kw; });

    expect(result).toBeNull(); // 尚未触发

    vi.advanceTimersByTime(300);
    expect(result).toBe('劳动法');
  });

  it('快速连续输入只触发最后一次', () => {
    const search = new DebouncedSearch(300);
    const calls = [];

    search.input('a', (kw) => calls.push(kw));
    search.input('ab', (kw) => calls.push(kw));
    search.input('abc', (kw) => calls.push(kw));

    vi.advanceTimersByTime(300);
    expect(calls).toEqual(['abc']);
  });

  it('空字符串搜索', () => {
    const search = new DebouncedSearch(300);
    let result = 'not-called';

    search.input('  ', (kw) => { result = kw; });
    vi.advanceTimersByTime(300);
    expect(result).toBe('');
  });
});
