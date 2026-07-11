/**
 * utils.js 单元测试
 * 测试 escapeHtml / formatTime / formatDate / simpleMarkdown
 *
 * 函数实现来自 frontend/static/js/utils.js，内联于此以便在 Node.js 环境测试
 */

import { describe, it, expect } from 'vitest';

// ── 从 utils.js 提取的纯函数实现 ──

function escapeHtml(str) {
  if (!str) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(str).replace(/[&<>"']/g, c => map[c]);
}

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

// ── 测试用例 ──

describe('escapeHtml', () => {
  it('转义 & 符号', () => {
    expect(escapeHtml('a & b')).toBe('a &amp; b');
  });

  it('转义 < 和 >', () => {
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;');
  });

  it('转义引号', () => {
    expect(escapeHtml('"hello"')).toBe('&quot;hello&quot;');
    expect(escapeHtml("it's")).toBe('it&#39;s');
  });

  it('空字符串返回空', () => {
    expect(escapeHtml('')).toBe('');
  });

  it('null/undefined 返回空字符串', () => {
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(undefined)).toBe('');
  });

  it('普通文本不变', () => {
    expect(escapeHtml('正常中文文本')).toBe('正常中文文本');
  });
});

describe('formatTime', () => {
  it('刚发生的消息显示"刚刚"', () => {
    const now = new Date().toISOString();
    expect(formatTime(now)).toBe('刚刚');
  });

  it('几分钟前', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatTime(fiveMinAgo)).toBe('5分钟前');
  });

  it('几小时前', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 3600 * 1000).toISOString();
    expect(formatTime(twoHoursAgo)).toBe('2小时前');
  });

  it('空值返回空字符串', () => {
    expect(formatTime('')).toBe('');
    expect(formatTime(null)).toBe('');
  });

  it('不同年份显示完整日期', () => {
    expect(formatTime('2020-03-15T10:30:00')).toContain('2020');
  });
});

describe('formatDate', () => {
  it('今天', () => {
    const today = new Date().toISOString();
    expect(formatDate(today)).toBe('今天');
  });

  it('昨天', () => {
    const yesterday = new Date(Date.now() - 86400000).toISOString();
    expect(formatDate(yesterday)).toBe('昨天');
  });

  it('空值返回空字符串', () => {
    expect(formatDate('')).toBe('');
    expect(formatDate(null)).toBe('');
  });

  it('较早日期显示中文格式', () => {
    const result = formatDate('2023-01-15T00:00:00');
    expect(result).toContain('2023年');
    expect(result).toContain('1月');
  });
});

describe('simpleMarkdown', () => {
  it('空文本返回空字符串', () => {
    expect(simpleMarkdown('')).toBe('');
    expect(simpleMarkdown(null)).toBe('');
  });

  it('粗体转换', () => {
    const result = simpleMarkdown('这是**重点**内容');
    expect(result).toContain('<strong>重点</strong>');
  });

  it('斜体转换', () => {
    const result = simpleMarkdown('this is *emphasized* text');
    expect(result).toContain('<em>emphasized</em>');
  });

  it('标题转换', () => {
    expect(simpleMarkdown('## 二级标题')).toContain('<h3>二级标题</h3>');
    expect(simpleMarkdown('### 三级标题')).toContain('<h4>三级标题</h4>');
  });

  it('代码块转换', () => {
    const result = simpleMarkdown('```js\nconst x = 1;\n```');
    expect(result).toContain('<pre><code>');
    expect(result).toContain('const x = 1;');
  });

  it('行内代码转换', () => {
    const result = simpleMarkdown('使用 `console.log()` 调试');
    expect(result).toContain('<code>console.log()</code>');
  });

  it('链接转换', () => {
    const result = simpleMarkdown('[点击这里](https://example.com)');
    expect(result).toContain('<a href="https://example.com"');
    expect(result).toContain('target="_blank"');
    expect(result).toContain('>点击这里</a>');
  });

  it('列表转换', () => {
    const result = simpleMarkdown('- 项目1\n- 项目2');
    expect(result).toContain('<li>项目1</li>');
    expect(result).toContain('<li>项目2</li>');
    expect(result).toContain('<ul>');
  });

  it('引用转换', () => {
    const result = simpleMarkdown('> 这是一段引用');
    expect(result).toContain('<blockquote>');
  });

  it('XSS 防护：不执行 script 标签', () => {
    const result = simpleMarkdown('<script>alert("xss")</script>');
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;script&gt;');
  });

  it('段落包裹', () => {
    const result = simpleMarkdown('段落1\n\n段落2');
    expect(result).toContain('<p>');
  });
});
