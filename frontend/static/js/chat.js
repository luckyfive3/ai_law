/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 流式聊天核心
   ═══════════════════════════════════════ */

const Chat = {
  currentSessionId: null,
  isStreaming: false,
  abortController: null,

  init(sessionId) {
    this.currentSessionId = sessionId || null;
    this._bindEvents();
    this._setupInputAutoResize();
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
          category: category || 'general',
        });
        this.currentSessionId = resp.data.id;
        // 更新 URL
        window.history.replaceState(null, '', `/chat?session_id=${this.currentSessionId}`);
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
          category: category || 'general',
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            // 处理事件类型
            const eventType = line.substring(6).trim();
            if (eventType === 'thinking' && thinkingEl) {
              // 更新思考状态
              const statusEl = thinkingEl.querySelector('.thinking-text');
              if (statusEl) statusEl.textContent = '正在检索相关法条…';
            }
            continue;
          }

          if (!line.startsWith('data:')) continue;
          const jsonStr = line.substring(5).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.status === 'searching') {
              if (thinkingEl) {
                thinkingEl.querySelector('.thinking-text').textContent = '正在检索相关法条…';
              }
            } else if (data.content !== undefined) {
              // 首字到达时替换 thinking 为正式消息
              if (!messageEl) {
                if (thinkingEl) {
                  thinkingEl.remove();
                }
                messageEl = this._createAssistantMessageContainer();
                contentEl = messageEl.querySelector('.message-bubble');
              }

              fullContent += data.content;
              contentEl.innerHTML = simpleMarkdown(fullContent) + '<span class="cursor-blink"></span>';
              this._scrollToBottom();
            } else if (data.laws) {
              lawRefs = data.laws;
              // 法条到达后追加法条卡片
              if (messageEl) {
                this._appendLawCards(messageEl, lawRefs);
              }
            } else if (data.message_id !== undefined) {
              // 流结束
              if (messageEl && contentEl) {
                // 去掉闪烁光标
                contentEl.innerHTML = simpleMarkdown(fullContent);

                // 追加风险提示
                this._appendDisclaimer(messageEl);

                // 追加法条卡片（如果还没加）
                if (lawRefs.length > 0) {
                  this._appendLawCards(messageEl, lawRefs);
                }

                // 设置时间
                const timeEl = messageEl.querySelector('.message-time');
                if (timeEl) timeEl.textContent = formatTime(new Date().toISOString());

                // 显示操作按钮
                const actionsEl = messageEl.querySelector('.message-actions');
                if (actionsEl) actionsEl.style.display = 'flex';
              }
            }
          } catch (e) {
            console.warn('SSE parse error:', e, jsonStr);
          }
        }
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        // 用户主动停止，已生成的内容保留
        if (thinkingEl) thinkingEl.remove();
        const msgEl = document.querySelector('.message--assistant:last-of-type');

        // 去掉闪烁光标
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
    this.currentSessionId = null;
    const list = document.getElementById('messageList');
    if (list) list.innerHTML = '';

    // 显示欢迎引导
    this._showWelcomeGuide();

    window.history.replaceState(null, '', '/chat');
    document.getElementById('chatInput')?.focus();
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

    // 常见问题快捷提问卡片
    document.querySelectorAll('.quick-question').forEach(card => {
      card.addEventListener('click', () => {
        const question = card.dataset.question;
        if (question) this.sendMessage(question);
      });
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

    // 绑定复制按钮
    const copyBtn = el.querySelector('.copy-btn');
    copyBtn?.addEventListener('click', () => {
      const bubble = el.querySelector('.message-bubble');
      if (bubble) {
        // 去除 HTML 标记，获取纯文本
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

    // 移除已有法条卡片
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

      // 点击折叠/展开
      card.querySelector('.law-card-header').addEventListener('click', () => {
        card.classList.toggle('open');
      });

      body.appendChild(card);
    });
  },

  _appendDisclaimer(messageEl) {
    const body = messageEl.querySelector('.message-body');
    if (!body) return;
    // 移除已有风险提示
    body.querySelectorAll('.disclaimer-bar').forEach(d => d.remove());

    const bar = document.createElement('div');
    bar.className = 'disclaimer-bar';
    bar.innerHTML = `
      <span class="icon">⚠️</span>
      <span>以上内容仅供参考，不构成法律意见。如遇重大法律问题，强烈建议您咨询具有执业资格的律师以获取专业法律建议。</span>
    `;
    body.appendChild(bar);
  },

  _showWelcomeGuide() {
    const list = document.getElementById('messageList');
    if (!list) return;
    const existing = document.getElementById('welcomeGuide');
    if (existing) existing.style.display = '';

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

    // 绑定快捷提问
    el.querySelectorAll('.quick-question').forEach(card => {
      card.addEventListener('click', () => {
        const question = card.dataset.question;
        if (question) this.sendMessage(question);
      });
    });
  },

  _scrollToBottom() {
    requestAnimationFrame(() => {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    });
  },
};
