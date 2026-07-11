/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 流式聊天核心
   ═══════════════════════════════════════ */

const Chat = {
  currentSessionId: null,
  isStreaming: false,
  abortController: null,
  currentCategory: 'all',
  CATEGORY_CONFIG: {
    'all': { label: '综合', icon: '⚖️' },
    'marriage': { label: '婚姻家庭', icon: '💒' },
    'labor': { label: '劳动纠纷', icon: '💼' },
    'contract': { label: '合同纠纷', icon: '📝' },
    'traffic': { label: '交通事故', icon: '🚗' },
    'housing': { label: '房产纠纷', icon: '🏠' },
    'consumer': { label: '消费维权', icon: '🛒' },
  },
  // 会话缓存: { [sessionId]: { title, updatedAt, msgCount, html } }
  conversationsCache: {},
  // 侧边栏会话元信息列表
  conversationMetas: [],
  // sessionStorage key
  STORAGE_KEY: 'last_chat_session_id',

  init(sessionId) {
    this.currentSessionId = sessionId || null;

    const params = new URLSearchParams(window.location.search);
    const urlCategory = params.get('category');
    if (urlCategory && this.CATEGORY_CONFIG[urlCategory]) {
      this.currentCategory = urlCategory;
    }

    // 未登录 → 跳转登录页
    if (!Auth.isLoggedIn()) {
      window.location.href = '/login?redirect=' + encodeURIComponent('/chat' + (sessionId ? '?session_id=' + sessionId : ''));
      return;
    }

    // 没有 URL 参数但 sessionStorage 有记录且已登录 → 恢复上次会话
    if (!this.currentSessionId && Auth.isLoggedIn()) {
      const lastId = sessionStorage.getItem(this.STORAGE_KEY);
      if (lastId) {
        let redirectUrl = `/chat?session_id=${lastId}`;
        if (urlCategory) redirectUrl += `&category=${urlCategory}`;
        window.location.replace(redirectUrl);
        return;
      }
    }

    this._bindEvents();
    this._setupInputAutoResize();
    this._bindCategoryEvents();
    this._loadConversationList();
    this._bindMobileSidebar();

    // 如果带有 session_id，加载该会话的消息
    if (this.currentSessionId) {
      this._persistSessionId(this.currentSessionId);
      this._loadInitialSession(this.currentSessionId);
    }
  },

  // ── 持久化当前 session_id 到 sessionStorage ──
  _persistSessionId(id) {
    if (id) {
      sessionStorage.setItem(this.STORAGE_KEY, id);
    } else {
      sessionStorage.removeItem(this.STORAGE_KEY);
    }
  },

  // ── 初次加载指定会话的消息 ──
  async _loadInitialSession(sessionId) {
    if (!Auth.isLoggedIn()) return;

    const list = document.getElementById('messageList');
    const welcome = document.getElementById('welcomeGuide');
    if (welcome) welcome.style.display = 'none';

    try {
      const resp = await Api.get(`sessions/${sessionId}`);
      const data = resp.data;
      if (!data || !data.messages) return;

      if (list) list.innerHTML = '';
      data.messages.forEach(msg => {
        this._renderHistoryMessage(msg);
      });
      this._saveCurrentToCache();
      this._scrollToBottom();
    } catch (e) {
      // 会话可能已被删除，静默回退
      console.warn('加载初始会话失败:', e.message);
    }
  },

  // ── 加载侧边栏会话列表 ──
  async _loadConversationList() {
    const listEl = document.getElementById('conversationList');
    if (!listEl) return;

    if (!Auth.isLoggedIn()) {
      listEl.innerHTML = `
        <div class="sidebar-empty">
          <div class="icon">🔒</div>
          <div class="text">登录后可查看历史对话</div>
        </div>`;
      return;
    }

    listEl.innerHTML = '<div class="sidebar-loading"><div class="spinner"></div></div>';

    try {
      const resp = await Api.get('sessions?page=1&page_size=10');
      const data = resp.data;
      this.conversationMetas = data?.list || [];
      this._renderConversationList();
    } catch (e) {
      listEl.innerHTML = `
        <div class="sidebar-empty">
          <div class="text">加载失败</div>
        </div>`;
    }
  },

  _renderConversationList() {
    const listEl = document.getElementById('conversationList');
    if (!listEl) return;

    if (this.conversationMetas.length === 0) {
      listEl.innerHTML = `
        <div class="sidebar-empty">
          <div class="icon">💬</div>
          <div class="text">暂无历史对话</div>
        </div>`;
      return;
    }

    let html = '';
    this.conversationMetas.forEach(session => {
      const isActive = session.id === this.currentSessionId;
      html += `
        <div class="conversation-item ${isActive ? 'active' : ''}" data-session-id="${escapeHtml(session.id)}">
          <div class="conversation-item-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <div class="conversation-item-body">
            <div class="conversation-item-title">${escapeHtml(session.title || '法律咨询')}</div>
            <div class="conversation-item-meta">${escapeHtml(formatTime(session.updated_at))}</div>
          </div>
          <button class="conversation-item-delete" data-delete-id="${escapeHtml(session.id)}" title="删除">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>`;
    });

    listEl.innerHTML = html;

    // 绑定点击事件
    listEl.querySelectorAll('.conversation-item').forEach(item => {
      item.addEventListener('click', (e) => {
        // 不拦截删除按钮的点击
        if (e.target.closest('.conversation-item-delete')) return;
        const sid = item.dataset.sessionId;
        if (sid && sid !== this.currentSessionId) {
          this.switchConversation(sid);
        }
      });
    });

    // 绑定删除按钮
    listEl.querySelectorAll('.conversation-item-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._deleteConversation(btn.dataset.deleteId);
      });
    });
  },

  // ── 切换会话 ──
  async switchConversation(sessionId) {
    if (this.isStreaming) {
      Toast.warning('请等待当前回复完成');
      return;
    }

    if (sessionId === this.currentSessionId) return;

    // 保存当前会话的 HTML 到缓存
    this._saveCurrentToCache();

    // 切换到目标会话
    this.currentSessionId = sessionId;
    this._persistSessionId(sessionId);
    window.history.replaceState(null, '', `/chat?session_id=${sessionId}`);

    // 更新侧边栏高亮
    this._updateSidebarActive();

    const list = document.getElementById('messageList');
    const welcome = document.getElementById('welcomeGuide');

    // 检查缓存
    const cached = this.conversationsCache[sessionId];
    if (cached && cached.html) {
      if (list) list.innerHTML = cached.html;
      this._scrollToBottom();
      // 重新绑定消息中的事件
      this._rebindMessageActions();
      // 关闭移动端侧边栏
      this._closeSidebar();
      return;
    }

    // 从 API 加载
    if (!Auth.isLoggedIn()) return;

    if (list) {
      list.innerHTML = '<div class="sidebar-loading" style="padding:var(--space-16);"><div class="spinner"></div></div>';
    }
    if (welcome) welcome.style.display = 'none';

    try {
      const resp = await Api.get(`sessions/${sessionId}`);
      const data = resp.data;
      if (!data || !data.messages) {
        if (list) list.innerHTML = '';
        this._showWelcomeGuide();
        this._closeSidebar();
        return;
      }

      // 渲染消息
      if (list) list.innerHTML = '';
      data.messages.forEach(msg => {
        this._renderHistoryMessage(msg);
      });

      // 缓存
      this._saveCurrentToCache();
    } catch (e) {
      Toast.error('加载会话失败: ' + e.message);
      if (list) list.innerHTML = '';
      this._showWelcomeGuide();
    }

    this._scrollToBottom();
    this._closeSidebar();
  },

  // ── 渲染历史消息 ──
  _renderHistoryMessage(msg) {
    const list = document.getElementById('messageList');
    if (!list) return;

    const el = document.createElement('div');
    el.className = `message message--${msg.role}`;

    const avatar = msg.role === 'user' ? '我' : 'AI';
    const avatarBg = msg.role === 'user'
      ? 'background:var(--color-primary-100);color:var(--color-primary-700);'
      : 'background:var(--color-gray-100);color:var(--color-primary-600);';

    let lawCardsHTML = '';
    if (msg.law_refs && msg.law_refs.length > 0) {
      lawCardsHTML = msg.law_refs.map(law => `
        <div class="law-card">
          <div class="law-card-header">
            <span>《${escapeHtml(law.name)}》${escapeHtml(law.article || '')}</span>
            <span class="arrow">▼</span>
          </div>
          <div class="law-card-body">
            <p>${escapeHtml(law.text || '')}</p>
          </div>
        </div>
      `).join('');
    }

    el.innerHTML = `
      <div class="message-avatar" style="${avatarBg}">${avatar}</div>
      <div class="message-body">
        <div class="message-bubble markdown-body">${simpleMarkdown(msg.content)}</div>
        <div class="message-time">${formatTime(msg.created_at)}</div>
        ${msg.role === 'assistant' ? '<div class="message-actions" style="display:flex;"><button class="copy-btn">复制全文</button></div>' : ''}
        ${lawCardsHTML}
      </div>
    `;

    this._bindMessageElementEvents(el);
    list.appendChild(el);
  },

  // ── 绑定单条消息的事件 ──
  _bindMessageElementEvents(el) {
    const copyBtn = el.querySelector('.copy-btn');
    copyBtn?.addEventListener('click', () => {
      const bubble = el.querySelector('.message-bubble');
      if (bubble) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = bubble.innerHTML;
        const text = tempDiv.textContent || tempDiv.innerText || '';
        navigator.clipboard.writeText(text).then(() => {
          Toast.success('已复制');
        }).catch(() => Toast.error('复制失败'));
      }
    });

    el.querySelectorAll('.law-card-header').forEach(header => {
      header.addEventListener('click', () => {
        header.parentElement.classList.toggle('open');
      });
    });
  },

  // ── 重新绑定消息列表中的交互事件 ──
  _rebindMessageActions() {
    document.querySelectorAll('.message--assistant').forEach(el => {
      this._bindMessageElementEvents(el);
    });
  },

  // ── 保存当前会话 HTML 到缓存 ──
  _saveCurrentToCache() {
    if (!this.currentSessionId) return;
    const list = document.getElementById('messageList');
    if (!list) return;

    const meta = this.conversationMetas.find(m => m.id === this.currentSessionId);
    this.conversationsCache[this.currentSessionId] = {
      title: meta?.title || '法律咨询',
      updatedAt: meta?.updated_at || new Date().toISOString(),
      html: list.innerHTML,
    };
  },

  // ── 刷新侧边栏并更新缓存信息 ──
  async _refreshConversationMeta() {
    if (!this.currentSessionId || !Auth.isLoggedIn()) return;
    try {
      const resp = await Api.get(`sessions/${this.currentSessionId}`);
      const data = resp.data;
      if (data) {
        // 更新或添加到 metas 列表
        const idx = this.conversationMetas.findIndex(m => m.id === this.currentSessionId);
        const meta = {
          id: this.currentSessionId,
          title: data.title || '法律咨询',
          updated_at: data.updated_at || new Date().toISOString(),
          msg_count: data.msg_count || 0,
        };
        if (idx >= 0) {
          this.conversationMetas[idx] = meta;
        } else {
          this.conversationMetas.unshift(meta);
        }
        // 重新排序：最近更新的在前
        this.conversationMetas.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        this._renderConversationList();
        // 同时更新缓存
        this._saveCurrentToCache();
      }
    } catch (e) {
      // 静默失败
    }
  },

  // ── 更新侧边栏高亮 ──
  _updateSidebarActive() {
    document.querySelectorAll('.conversation-item').forEach(item => {
      item.classList.toggle('active', item.dataset.sessionId === this.currentSessionId);
    });
  },

  // ── 删除侧边栏会话 ──
  async _deleteConversation(sessionId) {
    showModal({
      title: '删除会话',
      message: '确定要删除这个会话吗？删除后无法恢复。',
      confirmText: '删除',
      danger: true,
      onConfirm: async () => {
        try {
          await Api.delete(`sessions/${sessionId}`);
          // 从缓存中移除
          delete this.conversationsCache[sessionId];
          // 从列表中移除
          this.conversationMetas = this.conversationMetas.filter(m => m.id !== sessionId);

          // 如果删除的是当前会话
          if (sessionId === this.currentSessionId) {
            this.currentSessionId = null;
            this._persistSessionId(null);
            const list = document.getElementById('messageList');
            if (list) list.innerHTML = '';
            this._showWelcomeGuide();
            window.history.replaceState(null, '', '/chat');
          }

          this._renderConversationList();
          Toast.success('已删除');
        } catch (e) {
          Toast.error('删除失败: ' + e.message);
        }
      },
    });
  },

  // ── 移动端侧边栏控制 ──
  _bindMobileSidebar() {
    const menuBtn = document.getElementById('menuBtn');
    const sidebar = document.getElementById('chatSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    const open = () => {
      sidebar?.classList.add('open');
      overlay?.classList.add('visible');
      document.body.style.overflow = 'hidden';
    };

    const close = () => {
      sidebar?.classList.remove('open');
      overlay?.classList.remove('visible');
      document.body.style.overflow = '';
    };

    menuBtn?.addEventListener('click', open);
    overlay?.addEventListener('click', close);

    // 点击侧边栏中的会话项后关闭
    sidebar?.addEventListener('click', (e) => {
      if (e.target.closest('.conversation-item') && !e.target.closest('.conversation-item-delete')) {
        close();
      }
    });
  },

  _closeSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar?.classList.remove('open');
    overlay?.classList.remove('visible');
    document.body.style.overflow = '';
  },

  _bindCategoryEvents() {
    const bar = document.getElementById('categoryBar');
    if (!bar) return;
    this._updateCategoryDisplay();
    bar.querySelectorAll('.category-tag').forEach(tag => {
      tag.addEventListener('click', () => {
        if (this.isStreaming) { Toast.warning('请等待当前回复完成'); return; }
        const newCat = tag.dataset.category;
        if (newCat !== this.currentCategory) {
          this._saveCurrentToCache();
          this.currentCategory = newCat;
          this.currentSessionId = null;
          this._persistSessionId(null);
          const list = document.getElementById('messageList');
          if (list) list.innerHTML = '';
          this._showWelcomeGuide();
          window.history.replaceState(null, '', '/chat?category=' + newCat);
        }
        this._updateCategoryDisplay();
      });
    });
  },

  _updateCategoryDisplay() {
    document.querySelectorAll('.category-tag').forEach(tag => {
      tag.classList.toggle('active', tag.dataset.category === this.currentCategory);
    });
  },

  // ── 发送消息 ──
  async sendMessage(content, category = null) {
    if (this.isStreaming || !content.trim()) return;

    // 未登录拦截
    if (!Auth.isLoggedIn()) {
      showModal({
        title: '请先登录',
        message: '发送消息前需要登录账号，是否前往登录？',
        confirmText: '去登录',
        onConfirm: () => {
          window.location.href = `/login?redirect=${encodeURIComponent('/chat')}`;
        },
      });
      return;
    }

    this.isStreaming = true;
    this._setSendButtonState('streaming');

    // 如果没有 session，先创建
    if (!this.currentSessionId) {
      try {
        const resp = await Api.post('sessions', {
          title: content.substring(0, 50),
          category: this.currentCategory === 'all' ? 'general' : this.currentCategory,
        });
        this.currentSessionId = resp.data.id;
        this._persistSessionId(this.currentSessionId);
        // 更新 URL
        window.history.replaceState(null, '', `/chat?session_id=${this.currentSessionId}`);
        // 刷新侧边栏列表
        await this._refreshConversationMeta();
      } catch (e) {
        Toast.error('创建会话失败: ' + e.message);
        this.isStreaming = false;
        this._setSendButtonState('idle');
        return;
      }
    }

    // 渲染用户消息
    this._appendMessage('user', content);
    this._clearInput();
    this._scrollToBottom();

    // 渲染 AI 消息占位（思考中）
    const thinkingEl = this._appendThinking();

    // 拼接 SSE URL
    const fetchUrl = sseUrl(`chat/stream`);
    this.abortController = new AbortController();

    try {
      const resp = await fetch(fetchUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${Auth.getToken()}`,
        },
        body: JSON.stringify({
          session_id: this.currentSessionId,
          content: content,
          category: this.currentCategory === 'all' ? 'general' : this.currentCategory,
        }),
        signal: this.abortController.signal,
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.message || `请求失败 (${resp.status})`);
      }

      // 读取 SSE 流
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';
      let lawRefs = [];
      let messageEl = null;
      let contentEl = null;
      let streamError = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const jsonStr = line.substring(5).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.status === 'error') {
              if (thinkingEl) thinkingEl.remove();
              Toast.error(data.error || '服务异常');
              streamError = true;
              break;
            }

            if (data.status === 'searching') {
              if (thinkingEl) {
                thinkingEl.querySelector('.thinking-text').textContent = '正在检索相关法条…';
              }
            } else if (data.done === true) {
              // 流结束，统一在此完成消息最终化
              lawRefs = data.laws || [];

              if (messageEl && contentEl) {
                contentEl.innerHTML = simpleMarkdown(fullContent);

                if (lawRefs.length > 0) {
                  this._appendLawCards(messageEl, lawRefs);
                }

                const timeEl = messageEl.querySelector('.message-time');
                if (timeEl) timeEl.textContent = formatTime(new Date().toISOString());

                const actionsEl = messageEl.querySelector('.message-actions');
                if (actionsEl) actionsEl.style.display = 'flex';
              }

              if (!messageEl && thinkingEl) {
                // 空响应：移除 thinking，显示兜底消息
                thinkingEl.remove();
                const fallbackEl = this._createAssistantMessageContainer();
                const bubble = fallbackEl.querySelector('.message-bubble');
                if (bubble) bubble.innerHTML = simpleMarkdown(fullContent || '抱歉，未能生成回复。');
                const timeEl = fallbackEl.querySelector('.message-time');
                if (timeEl) timeEl.textContent = formatTime(new Date().toISOString());
                const actionsEl = fallbackEl.querySelector('.message-actions');
                if (actionsEl) actionsEl.style.display = 'flex';
              }

              this._refreshConversationMeta();
            } else if (data.content !== undefined) {
              // 首字到达时替换 thinking 为正式消息
              if (!messageEl) {
                if (thinkingEl) thinkingEl.remove();
                messageEl = this._createAssistantMessageContainer();
                contentEl = messageEl.querySelector('.message-bubble');
              }

              fullContent += data.content;
              contentEl.innerHTML = simpleMarkdown(fullContent) + '<span class="cursor-blink"></span>';
              this._scrollToBottom();
            }
          } catch (e) {
            console.warn('SSE parse error:', e, jsonStr);
          }
        }

        if (streamError) break;
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        if (thinkingEl) thinkingEl.remove();
        const msgEl = document.querySelector('.message--assistant:last-of-type');
        const bubble = msgEl?.querySelector('.message-bubble');
        if (bubble) {
          bubble.innerHTML = bubble.innerHTML.replace(/<span class="cursor-blink"><\/span>/g, '');
        }
        Toast.info('已停止生成');
      } else {
        if (thinkingEl) thinkingEl.remove();
        Toast.error('消息发送失败: ' + err.message);
      }
    } finally {
      this.isStreaming = false;
      this.abortController = null;
      this._setSendButtonState('idle');
    }
  },

  // ── 停止生成 ──
  stopGeneration() {
    if (this.abortController) {
      this.abortController.abort();
    }
  },

  // ── 新建对话 ──
  startNewChat() {
    if (this.isStreaming) {
      Toast.warning('请等待当前回复完成');
      return;
    }

    // 保存当前会话
    this._saveCurrentToCache();

    this.currentSessionId = null;
    this._persistSessionId(null);
    const list = document.getElementById('messageList');
    if (list) list.innerHTML = '';

    this._showWelcomeGuide();
    this._updateSidebarActive();

    window.history.replaceState(null, '', '/chat');
    document.getElementById('chatInput')?.focus();
    this._closeSidebar();
  },

  // ── 内部辅助方法 ──

  _bindEvents() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    if (input && sendBtn) {
      sendBtn.addEventListener('click', () => {
        if (this.isStreaming) {
          this.stopGeneration();
        } else {
          this.sendMessage(input.value);
        }
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (this.isStreaming) {
            this.stopGeneration();
          } else {
            this.sendMessage(input.value);
          }
        }
      });

      input.addEventListener('input', () => {
        this._setSendButtonState(this.isStreaming ? 'streaming' : 'idle');
      });
    }

    // 新建对话按钮
    document.getElementById('newChatBtn')?.addEventListener('click', () => this.startNewChat());

    // 快捷提问（支持动态生成的欢迎引导）
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.quick-question');
      if (btn) {
        const question = btn.dataset.question;
        if (question) {
          const input = document.getElementById('chatInput');
          if (input) input.value = question;
          this.sendMessage(question);
        }
      }
    });
  },

  _setupInputAutoResize() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
  },

  _setSendButtonState(state) {
    const btn = document.getElementById('sendBtn');
    const input = document.getElementById('chatInput');
    if (!btn) return;

    if (state === 'streaming') {
      btn.classList.add('stop-btn');
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>';
      btn.disabled = false;
    } else {
      btn.classList.remove('stop-btn');
      const hasContent = input && input.value.trim().length > 0;
      btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
      btn.disabled = !hasContent;
    }
  },

  _clearInput() {
    const input = document.getElementById('chatInput');
    if (input) {
      input.value = '';
      input.style.height = 'auto';
    }
  },

  _appendMessage(role, content) {
    const list = document.getElementById('messageList');
    if (!list) return;

    // 隐藏欢迎引导
    const welcome = document.getElementById('welcomeGuide');
    if (welcome) welcome.style.display = 'none';

    const time = new Date().toISOString();
    const el = document.createElement('div');
    el.className = `message message--${role}`;
    el.innerHTML = `
      <div class="message-avatar">${role === 'user' ? '我' : 'AI'}</div>
      <div class="message-body">
        <div class="message-bubble">${escapeHtml(content)}</div>
        <div class="message-time">${formatTime(time)}</div>
        ${role === 'assistant' ? '<div class="message-actions" style="display:none;"></div>' : ''}
      </div>
    `;
    list.appendChild(el);
    this._scrollToBottom();
    return el;
  },

  _appendThinking() {
    const list = document.getElementById('messageList');
    if (!list) return null;

    const el = document.createElement('div');
    el.className = 'message message--assistant';
    el.innerHTML = `
      <div class="message-avatar" style="background:var(--color-gray-100);color:var(--color-primary-600);">AI</div>
      <div class="message-body">
        <div class="message-bubble">
          <div class="thinking-dots">
            <span></span><span></span><span></span>
          </div>
          <div class="thinking-text" style="font-size:var(--text-xs);color:var(--color-gray-500);margin-top:4px;">正在思考…</div>
        </div>
      </div>
    `;
    list.appendChild(el);
    this._scrollToBottom();
    return el;
  },

  _createAssistantMessageContainer() {
    const list = document.getElementById('messageList');
    const el = document.createElement('div');
    el.className = 'message message--assistant';
    el.innerHTML = `
      <div class="message-avatar" style="background:var(--color-gray-100);color:var(--color-primary-600);">AI</div>
      <div class="message-body">
        <div class="message-bubble markdown-body"></div>
        <div class="message-time"></div>
        <div class="message-actions" style="display:none;">
          <button class="copy-btn" title="复制全文">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
            复制
          </button>
        </div>
      </div>
    `;

    const copyBtn = el.querySelector('.copy-btn');
    copyBtn?.addEventListener('click', () => {
      const bubble = el.querySelector('.message-bubble');
      if (bubble) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = bubble.innerHTML;
        const text = tempDiv.textContent || tempDiv.innerText || '';
        navigator.clipboard.writeText(text).then(() => {
          Toast.success('已复制');
        }).catch(() => Toast.error('复制失败'));
      }
    });

    list.appendChild(el);
    return el;
  },

  _appendLawCards(messageEl, laws) {
    if (!laws || laws.length === 0) return;
    const body = messageEl.querySelector('.message-body');
    if (!body) return;

    body.querySelectorAll('.law-card').forEach(c => c.remove());

    laws.forEach(law => {
      const card = document.createElement('div');
      card.className = 'law-card';
      card.innerHTML = `
        <div class="law-card-header">
          <span>《${escapeHtml(law.name)}》${escapeHtml(law.article || '')}</span>
          <span class="arrow">▼</span>
        </div>
        <div class="law-card-body">
          <p>${escapeHtml(law.text || '')}</p>
          ${law.source ? `<p style="margin-top:8px;font-size:var(--text-xs);color:var(--color-gray-500);">来源: ${escapeHtml(law.source)}</p>` : ''}
        </div>
      `;

      card.querySelector('.law-card-header').addEventListener('click', () => {
        card.classList.toggle('open');
      });

      body.appendChild(card);
    });
  },

  _showWelcomeGuide() {
    const list = document.getElementById('messageList');
    if (!list) return;
    const existing = document.getElementById('welcomeGuide');
    if (existing) {
      existing.style.display = '';
      return;
    }

    const el = document.createElement('div');
    el.id = 'welcomeGuide';
    el.className = 'empty-state';
    el.style.padding = 'var(--space-16) var(--space-6)';
    el.innerHTML = `
      <div class="icon">⚖️</div>
      <div class="title">您好，我是AI法律助手</div>
      <div class="desc">基于法律法规知识库为您提供法律信息参考<br>您可以随时向我咨询法律相关问题</div>
      <div style="margin-top: var(--space-6);">
        <p style="font-size: var(--text-sm); color: var(--color-gray-500); margin-bottom: var(--space-3);">试试这些问题：</p>
        <div style="display: flex; flex-wrap: wrap; gap: var(--space-2); justify-content: center;">
          <button class="btn btn-outline btn-sm quick-question" data-question="被公司无故辞退，能要求多少赔偿？">无故辞退如何赔偿？</button>
          <button class="btn btn-outline btn-sm quick-question" data-question="离婚时房产怎么分割？">离婚房产如何分割？</button>
          <button class="btn btn-outline btn-sm quick-question" data-question="交通事故责任认定有哪些规定？">交通事故责任认定</button>
          <button class="btn btn-outline btn-sm quick-question" data-question="合同违约怎么维权？">合同违约如何维权？</button>
        </div>
      </div>
    `;
    list.appendChild(el);
  },

  _scrollToBottom() {
    requestAnimationFrame(() => {
      const msgList = document.getElementById('messageList');
      if (msgList) {
        msgList.scrollTop = msgList.scrollHeight;
      }
    });
  },
};
