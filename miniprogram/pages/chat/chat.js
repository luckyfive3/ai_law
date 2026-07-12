/**
 * AI法律助手 - 智能咨询（核心页面）
 * 后端链路：DeepSeek Chat + RAGFlow 法律知识库 + MongoDB (阿里云)
 */
const chatService = require('../../services/chat');
const sessionService = require('../../services/session');
const config = require('../../utils/config');
const { mdToHtml, textToHtml } = require('../../utils/markdown');

Page({
  data: {
    statusBarHeight: 0,
    currentSessionId: null, currentTitle: 'AI法律助手', sessionList: [],
    messages: [], loading: false, loadingHistory: false, canLoadMore: false, historyPage: 1,
    inputValue: '', streaming: false, isSearching: false, streamingContent: '', streamingBuffer: '', scrollToId: '',
    showSidebar: false, currentReqTask: null,
    welcomeQuestions: config.WELCOME_QUESTIONS,
    modules: config.CONSULT_MODULES, activeModule: '',
    msgListTop: 0,       // 消息列表顶部偏移
    scrollHeight: 500    // 消息列表像素高度
  },

  onLoad() {
    const app = getApp();
    const sys = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sys.statusBarHeight });
    this._calcLayout(sys);
    if (!app.globalData.isLoggedIn) return;
    this._loadSessionList();
  },

  _calcLayout(sys) {
    sys = sys || wx.getSystemInfoSync();
    // 模块栏高度 ≈ 48px（16rpx上+12rpx下+内部内容约20px）
    const barH = 48;
    // 输入区高度 ≈ 56px（padding上下各约16rpx+内容约24px）
    const inputH = 56;
    const scrollHeight = sys.windowHeight - barH - inputH;
    this.setData({
      msgListTop: barH,
      scrollHeight: scrollHeight
    });
  },

  onShow() {
    const app = getApp();
    if (app.globalData.isLoggedIn) {
      if (!this.data.currentSessionId && this.data.messages.length === 0) this._loadSessionList();
    }
    if (app.globalData.currentSessionId && app.globalData.currentSessionId !== this.data.currentSessionId) {
      const sid = app.globalData.currentSessionId; app.globalData.currentSessionId = null;
      this._abortStream();
      this.setData({ loading: true, currentSessionId: sid });
      chatService.getMessages(sid, 1, 50).then(data => {
        const msgs = (data.list || []).map(m => ({
          ...m,
          richContent: m.role === 'assistant' ? mdToHtml(m.content || '') : textToHtml(m.content || '')
        }));
        this.setData({ messages: msgs, loading: false, canLoadMore: data.has_more || false, historyPage: 1, scrollToId: 'msg-bottom' });
      }).catch(() => this.setData({ loading: false }));
    }
  },

  onHide() { this._abortStream(); },
  onUnload() { this._abortStream(); },

  async _loadSessionList() {
    try {
      const data = await sessionService.getSessions(1, 30);
      this.setData({ sessionList: (data.list || []).map(s => ({
        ...s,
        updated_at_text: this._formatTime(s.updated_at)
      })) });
    } catch (e) {}
  },

  onModuleSelect(e) { this.setData({ activeModule: e.currentTarget.dataset.value }); },

  onSend() {
    const app = getApp();
    if (!app.globalData.isLoggedIn) { wx.navigateTo({ url: '/pages/login/login' }); return; }
    if (!this.data.streaming) {
      const c = this.data.inputValue.trim();
      if (c) this._sendMessage(c);
    }
  },

  async _sendMessage(content) {
    if (!this.data.currentSessionId) {
      try {
        const title = content.length > 20 ? content.substring(0, 20) + '...' : content;
        const s = await sessionService.createSession(title, '');
        this.setData({ currentSessionId: s.id, currentTitle: title });
      } catch (e) { return; }
    }
    const userMsg = { id: 'user-' + Date.now(), role: 'user', content, richContent: textToHtml(content) };
    this.setData({
      messages: [...this.data.messages, userMsg],
      inputValue: '', streaming: true, isSearching: true,
      streamingContent: '', streamingBuffer: '',
      scrollToId: 'msg-bottom'
    });

    const reqTask = chatService.sendMessage(this.data.currentSessionId, content, this.data.activeModule, {
      onSearching: () => this.setData({ isSearching: false }),
      onChunk: (text) => {
        const buf = this.data.streamingBuffer + text;
        this.setData({ streamingContent: mdToHtml(buf), streamingBuffer: buf, isSearching: false });
      },
      onDone: (result) => {
        const aiMsg = {
          id: result.messageId || 'ai-' + Date.now(),
          role: 'assistant',
          content: this.data.streamingBuffer,
          richContent: mdToHtml(this.data.streamingBuffer),
          laws: result.laws || [],
          tokens: result.tokens || {}
        };
        this.setData({
          messages: [...this.data.messages, aiMsg],
          streaming: false, streamingContent: '', streamingBuffer: '',
          isSearching: false, scrollToId: 'msg-bottom'
        });
        if (this.data.messages.length >= 2) {
          this.setData({ currentTitle: content.substring(0, 15) + (content.length > 15 ? '…' : '') });
        }
        this._loadSessionList();
      },
      onError: (err) => {
        wx.showToast({ title: err || '生成失败', icon: 'none' });
        this.setData({ streaming: false, isSearching: false, streamingContent: '', streamingBuffer: '' });
      }
    });
    this.setData({ currentReqTask: reqTask });
  },

  onInput(e) { this.setData({ inputValue: e.detail.value }); },
  onInputFocus() {
    this.setData({ scrollToId: 'msg-bottom' });
  },

  onQuickQuestion(e) {
    const app = getApp();
    if (!app.globalData.isLoggedIn) { wx.navigateTo({ url: '/pages/login/login' }); return; }
    const q = e.currentTarget.dataset.question;
    this.setData({ inputValue: q });
    this._sendMessage(q);
  },

  toggleSidebar() {
    this.setData({ showSidebar: !this.data.showSidebar });
    if (!this.data.showSidebar) this._loadSessionList();
  },
  closeSidebar() { this.setData({ showSidebar: false }); },

  async onSwitchSession(e) {
    const { id, title } = e.currentTarget.dataset;
    if (id === this.data.currentSessionId) { this.closeSidebar(); return; }
    this._abortStream(); this.closeSidebar();
    try {
      this.setData({ loading: true, currentSessionId: id, currentTitle: title || 'AI法律助手' });
      const data = await chatService.getMessages(id, 1, 50);
      const msgs = (data.list || []).map(m => ({
        ...m,
        richContent: m.role === 'assistant' ? mdToHtml(m.content || '') : textToHtml(m.content || '')
      }));
      this.setData({ messages: msgs, loading: false, canLoadMore: data.has_more || false, historyPage: 1, scrollToId: 'msg-bottom' });
    } catch (e) { this.setData({ loading: false }); }
  },

  onNewChat() {
    this._abortStream();
    this.setData({
      currentSessionId: null, currentTitle: 'AI法律助手', messages: [],
      streaming: false, streamingContent: '', streamingBuffer: '',
      isSearching: false, showSidebar: false
    });
  },

  async onDeleteSession(e) {
    const { id } = e.currentTarget.dataset;
    const res = await new Promise(r => wx.showModal({ title: '删除会话', content: '确定删除该会话？', success: r }));
    if (!res.confirm) return;
    try {
      await sessionService.deleteSession(id);
      if (id === this.data.currentSessionId) this.onNewChat();
      this._loadSessionList();
      wx.showToast({ title: '已删除', icon: 'success' });
    } catch (e) {}
  },

  async onLoadMore() {
    if (!this.data.currentSessionId || !this.data.canLoadMore || this.data.loadingHistory) return;
    this.setData({ loadingHistory: true });
    const np = this.data.historyPage + 1;
    try {
      const data = await chatService.getMessages(this.data.currentSessionId, np, 50);
      const older = (data.list || []).map(m => ({
        ...m,
        richContent: m.role === 'assistant' ? mdToHtml(m.content || '') : textToHtml(m.content || '')
      }));
      this.setData({
        messages: [...older, ...this.data.messages],
        loadingHistory: false, canLoadMore: data.has_more || false, historyPage: np
      });
    } catch (e) { this.setData({ loadingHistory: false }); }
  },

  onScrollToUpper() {
    if (this.data.currentSessionId && this.data.canLoadMore && !this.data.loadingHistory) {
      this.onLoadMore();
    }
  },

  _abortStream() {
    if (this.data.currentReqTask) {
      try { this.data.currentReqTask.abort(); } catch (e) {}
      this.setData({ currentReqTask: null });
    }
  },

  _formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso), n = new Date(), diff = n - d;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  }
});
