/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 工具函数
   ═══════════════════════════════════════ */

// ── Toast 消息 ──
const Toast = {
  container: null,

  _ensure() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 3000) {
    this._ensure();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    this.container.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, duration);
  },

  success(msg) { this.show(msg, 'success'); },
  error(msg)   { this.show(msg, 'error', 5000); },
  info(msg)    { this.show(msg, 'info'); },
  warning(msg) { this.show(msg, 'warning', 4000); },
};

// ── Modal 弹窗 ──
function showModal({ title, message, confirmText = '确认', cancelText = '取消', onConfirm, danger = false }) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';

  overlay.innerHTML = `
    <div class="modal">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(message)}</p>
      <div class="modal-actions">
        <button class="btn btn-outline cancel-btn">${escapeHtml(cancelText)}</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'} confirm-btn">${escapeHtml(confirmText)}</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  const close = () => overlay.remove();

  overlay.querySelector('.cancel-btn').addEventListener('click', close);
  overlay.querySelector('.confirm-btn').addEventListener('click', () => {
    if (onConfirm) onConfirm();
    close();
  });
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

  return { close };
}

// ── HTML 转义 ──
function escapeHtml(str) {
  if (!str) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(str).replace(/[&<>"']/g, c => map[c]);
}

// ── 日期/时间格式化 ──
function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const now = new Date();
  const diff = now - d;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;

  const pad = n => String(n).padStart(2, '0');
  if (d.getFullYear() === now.getFullYear()) {
    return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yday = new Date(today - 86400000);
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());

  if (target.getTime() === today.getTime()) return '今天';
  if (target.getTime() === yday.getTime()) return '昨天';
  const weekStart = new Date(today - today.getDay() * 86400000);
  if (target >= weekStart) return '本周';

  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

// ── API 请求封装 ──
const API_BASE = '/api/v1/proxy';

async function api(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = Auth.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body && method !== 'GET') {
    opts.body = JSON.stringify(body);
  }

  const resp = await fetch(`${API_BASE}/${path}`, opts);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || `HTTP ${resp.status}`);
  }
  return resp.json();
}

const Api = {
  get:    (path)          => api('GET', path),
  post:   (path, body)    => api('POST', path, body),
  put:    (path, body)    => api('PUT', path, body),
  delete: (path)          => api('DELETE', path),
};

// 用于初始化 SSE 连接的 URL（直接连 Go 后端,绕过 Python 代理）
function sseUrl(path) {
  return `/api/v1/proxy/${path}`;
}

// ── 简单的客户端 Markdown 渲染 ──
// 用于即时预览，正式渲染建议用后端 marked 库或 showdown.js
function simpleMarkdown(text) {
  if (!text) return '';

  let html = escapeHtml(text);

  // 标题
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  // 粗体和斜体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 引用
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // 列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  // 代码块
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // 段落
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';

  // 清理空段落
  html = html.replace(/<p>\s*<\/p>/g, '');

  return html;
}
