/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 历史记录管理
   ═══════════════════════════════════════ */

const History = {
  page: 1,
  pageSize: 20,
  hasMore: true,
  isLoading: false,
  keyword: '',
  _debounceTimer: null,

  init() {
    this._bindEvents();
    this._loadList();
  },

  async _loadList(reset = false) {
    if (this.isLoading) return;
    if (!Auth.requireLogin()) return;

    if (reset) {
      this.page = 1;
      this.hasMore = true;
      const list = document.getElementById('historyList');
      if (list) list.innerHTML = '';
    }

    if (!this.hasMore) return;

    this.isLoading = true;
    this._showLoading(true);

    try {
      let url = `sessions?page=${this.page}&page_size=${this.pageSize}`;
      if (this.keyword) {
        url += `&keyword=${encodeURIComponent(this.keyword)}`;
      }
      const resp = await Api.get(url);
      const data = resp.data;

      if (data && data.list) {
        this._renderList(data.list);
        this.hasMore = data.has_more;
        this.page++;
      }

      if (!data || !data.list || data.list.length === 0) {
        const listEl = document.getElementById('historyList');
        if (listEl && listEl.children.length === 0) {
          this._showEmpty();
        }
      }
    } catch (e) {
      Toast.error('加载历史记录失败: ' + e.message);
    } finally {
      this.isLoading = false;
      this._showLoading(false);
    }
  },

  _renderList(items) {
    const container = document.getElementById('historyList');
    if (!container) return;

    // 隐藏空状态
    const empty = document.getElementById('historyEmpty');
    if (empty) empty.style.display = 'none';

    // 按日期分组
    let lastGroup = null;

    items.forEach(session => {
      const dateGroup = formatDate(session.updated_at);
      if (dateGroup !== lastGroup) {
        const groupEl = document.createElement('div');
        groupEl.className = 'history-date-group';
        groupEl.textContent = dateGroup;
        container.appendChild(groupEl);
        lastGroup = dateGroup;
      }

      const item = document.createElement('div');
      item.className = 'history-item';
      item.innerHTML = `
        <div class="history-item-main">
          <div class="history-item-title">${escapeHtml(session.title || '法律咨询')}</div>
          <div class="history-item-meta">
            ${session.msg_count || 0} 条消息 · ${formatTime(session.updated_at)}
          </div>
        </div>
        <button class="history-item-delete" data-id="${session.id}" title="删除">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
        </button>
      `;

      // 点击进入详情
      item.querySelector('.history-item-main').addEventListener('click', () => {
        window.location.href = `/history/${session.id}`;
      });

      // 删除按钮
      item.querySelector('.history-item-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        this._deleteSession(session.id, item);
      });

      container.appendChild(item);
    });
  },

  async _deleteSession(sessionId, itemEl) {
    showModal({
      title: '删除会话',
      message: '确定要删除这个会话吗？删除后无法恢复。',
      confirmText: '删除',
      danger: true,
      onConfirm: async () => {
        try {
          await Api.delete(`sessions/${sessionId}`);
          itemEl.style.opacity = '0';
          itemEl.style.transition = 'opacity 0.3s';
          setTimeout(() => {
            itemEl.remove();
            // 检查是否空列表
            const list = document.getElementById('historyList');
            if (list && list.children.length === 0) {
              this._showEmpty();
            }
          }, 300);
          Toast.success('已删除');
        } catch (e) {
          Toast.error('删除失败: ' + e.message);
        }
      },
    });
  },

  _showLoading(show) {
    const el = document.getElementById('historyLoading');
    if (el) el.style.display = show ? 'flex' : 'none';
  },

  _showEmpty() {
    const container = document.getElementById('historyList');
    if (!container) return;

    const empty = document.createElement('div');
    empty.id = 'historyEmpty';
    empty.className = 'empty-state';
    if (this.keyword) {
      empty.innerHTML = `
        <div class="icon">🔍</div>
        <div class="title">未找到相关记录</div>
        <div class="desc">没有包含"${escapeHtml(this.keyword)}"的会话</div>
      `;
    } else {
      empty.innerHTML = `
        <div class="icon">📋</div>
        <div class="title">暂无咨询记录</div>
        <div class="desc">去咨询一个问题吧</div>
        <a href="/chat" class="btn btn-primary">开始咨询</a>
      `;
    }
    container.appendChild(empty);
  },

  _bindEvents() {
    // 搜索输入（防抖 400ms）
    const searchInput = document.getElementById('historySearch');
    searchInput?.addEventListener('input', () => {
      const val = searchInput.value.trim();
      const clearBtn = document.getElementById('clearSearchBtn');
      clearTimeout(this._debounceTimer);
      this._debounceTimer = setTimeout(() => {
        this.keyword = val;
        if (clearBtn) clearBtn.style.display = val ? '' : 'none';
        this._loadList(true);
      }, 400);
    });

    // 清除搜索按钮
    document.getElementById('clearSearchBtn')?.addEventListener('click', () => {
      const input = document.getElementById('historySearch');
      if (input) input.value = '';
      this.keyword = '';
      document.getElementById('clearSearchBtn').style.display = 'none';
      this._loadList(true);
    });

    // 下拉刷新
    let touchStartY = 0;
    document.addEventListener('touchstart', (e) => { touchStartY = e.touches[0].clientY; });
    document.addEventListener('touchend', (e) => {
      const diff = e.changedTouches[0].clientY - touchStartY;
      if (diff > 80 && window.scrollY === 0) {
        this._loadList(true);
      }
    });
  },
};

// ── 历史详情页 ──
const HistoryDetail = {
  sessionId: null,

  init(sessionId) {
    this.sessionId = sessionId;
    this._loadDetail();
    this._bindEvents();
  },

  async _loadDetail() {
    if (!Auth.requireLogin()) return;

    try {
      const resp = await Api.get(`sessions/${this.sessionId}`);
      const data = resp.data;

      if (!data) {
        this._showEmpty();
        return;
      }

      // 渲染会话信息
      const infoEl = document.getElementById('detailInfo');
      if (infoEl) {
        infoEl.innerHTML = `
          <span>${escapeHtml(data.title || '法律咨询')}</span>
          <span style="margin-left:var(--space-4);font-size:var(--text-xs);color:var(--color-gray-500);">
            ${data.msg_count || 0} 条消息 · ${formatTime(data.updated_at)}
          </span>
        `;
      }

      // 渲染消息列表
      const listEl = document.getElementById('messageList');
      if (!listEl || !data.messages) return;

      data.messages.forEach(msg => {
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
            ${msg.role === 'assistant' ? '<div class="message-actions"><button class="copy-btn">复制全文</button></div>' : ''}
            ${lawCardsHTML}
          </div>
        `;

        // 复制按钮
        const copyBtn = el.querySelector('.copy-btn');
        copyBtn?.addEventListener('click', () => {
          navigator.clipboard.writeText(msg.content).then(() => {
            Toast.success('已复制');
          }).catch(() => Toast.error('复制失败'));
        });

        // 法条折叠
        el.querySelectorAll('.law-card-header').forEach(header => {
          header.addEventListener('click', () => {
            header.parentElement.classList.toggle('open');
          });
        });

        listEl.appendChild(el);
      });
    } catch (e) {
      Toast.error('加载历史详情失败: ' + e.message);
    }
  },

  _showEmpty() {
    const el = document.getElementById('messageList');
    if (!el) return;
    el.innerHTML = `
      <div class="empty-state">
        <div class="icon">📄</div>
        <div class="title">会话不存在</div>
        <div class="desc">该会话可能已被删除</div>
        <a href="/history" class="btn btn-outline">返回历史记录</a>
      </div>
    `;
  },

  _bindEvents() {
    // 删除当前对话
    document.getElementById('deleteSessionBtn')?.addEventListener('click', () => {
      showModal({
        title: '删除会话',
        message: '确定要删除这个会话吗？删除后无法恢复。',
        danger: true,
        confirmText: '删除',
        onConfirm: async () => {
          try {
            await Api.delete(`sessions/${this.sessionId}`);
            Toast.success('已删除');
            window.location.href = '/history';
          } catch (e) {
            Toast.error('删除失败: ' + e.message);
          }
        },
      });
    });

    // 继续咨询
    document.getElementById('continueChatBtn')?.addEventListener('click', () => {
      window.location.href = `/chat?session_id=${this.sessionId}`;
    });

    // 导出对话
    document.getElementById('exportBtn')?.addEventListener('click', async () => {
      try {
        // 通过后端导出接口获取数据
        const resp = await fetch(`/api/v1/proxy/chat/${this.sessionId}/export`, {
          headers: { 'Authorization': `Bearer ${Auth.getToken()}` },
        });
        if (!resp.ok) throw new Error('导出失败');

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `法律咨询记录_${this.sessionId}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        Toast.success('导出成功');
      } catch (e) {
        // 降级方案：复制页面上已有内容
        const messages = document.querySelectorAll('.message-bubble');
        let text = '';
        messages.forEach(m => {
          text += m.textContent + '\n\n---\n\n';
        });
        navigator.clipboard.writeText(text).then(() => {
          Toast.success('对话内容已复制到剪贴板');
        }).catch(() => Toast.error('导出失败'));
      }
    });
  },
};
