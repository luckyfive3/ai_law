/**
 * AI法律助手 - Markdown → rich-text HTML 渲染
 */
function mdToHtml(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
    '<pre style="background:#f5f5f5;border-radius:8rpx;padding:20rpx;overflow-x:auto;font-size:24rpx;line-height:1.6;margin:16rpx 0;"><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g,
    '<code style="background:#f0f0f0;padding:2rpx 8rpx;border-radius:4rpx;font-size:24rpx;">$1</code>');

  html = html.replace(/^#### (.+)$/gm, '<h4 style="font-size:28rpx;font-weight:600;margin:16rpx 0 8rpx;">$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:30rpx;font-weight:700;margin:20rpx 0 10rpx;">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:32rpx;font-weight:700;margin:24rpx 0 12rpx;border-bottom:2rpx solid #eee;padding-bottom:8rpx;">$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1 style="font-size:36rpx;font-weight:700;margin:28rpx 0 16rpx;">$1</h1>');

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
  html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li style="margin:6rpx 0;padding-left:8rpx;">$1</li>');
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li style="margin:6rpx 0;padding-left:8rpx;">$1</li>');
  html = html.replace(/^[\-\*]{3,}$/gm, '<hr style="border:none;border-top:2rpx solid #e8e8e8;margin:20rpx 0;"/>');
  html = html.replace(/^&gt;\s?(.+)$/gm,
    '<blockquote style="border-left:6rpx solid #d4a574;padding:8rpx 20rpx;margin:16rpx 0;background:rgba(212,165,116,0.06);color:#666;font-size:28rpx;">$1</blockquote>');

  html = html.replace(/\n\n/g, '<div style="height:16rpx;"></div>');
  html = html.replace(/\n/g, '<br/>');
  return html;
}

function textToHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br/>');
}

module.exports = { mdToHtml, textToHtml };
