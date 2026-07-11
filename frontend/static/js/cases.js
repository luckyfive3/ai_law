/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 案件管理模块
   ═══════════════════════════════════════ */

const STATUS_MAP = {
  '待分析':   { label: '待分析', cls: 'badge-pending' },
  '分析中':   { label: '分析中', cls: 'badge-analyzing' },
  '已分析':   { label: '已分析', cls: 'badge-analyzed' },
  pending:    { label: '待分析', cls: 'badge-pending' },
  analyzing:  { label: '分析中', cls: 'badge-analyzing' },
  analyzed:   { label: '已分析', cls: 'badge-analyzed' },
};

const CASE_TYPE_MAP = {
  civil: '民事', criminal: '刑事', administrative: '行政',
  commercial: '商事', labor: '劳动', other: '其他',
};

const COURT_LEVEL_MAP = {
  basic: '基层法院', intermediate: '中级法院', high: '高级法院', supreme: '最高法院',
};

function _getStatusBadge(status) {
  const m = STATUS_MAP[status] || STATUS_MAP.pending;
  const dotColor = m.label === '已分析' ? 'green' : m.label === '分析中' ? 'blue' : 'gray';
  return `<span class="badge ${m.cls}"><span class="status-dot ${dotColor}"></span>${m.label}</span>`;
}

function _getWinBar(rate) {
  if (rate == null) return '';
  const r = Number(rate);
  let cls = 'red'; if (r > 60) cls = 'green'; else if (r >= 30) cls = 'orange';
  return `<div class="win-rate"><span class="win-rate-value win-rate-${cls}">${r}%</span>
    <div class="win-rate-bar"><div class="win-rate-bar-fill ${cls}" style="width:${r}%"></div></div></div>`;
}

// ── 案件列表页 ──
const CaseApp = {
  currentPage: 1,
  currentFilter: '',
  currentKeyword: '',
  pageSize: 10,
  totalCount: 0,
  _searchTimer: null,

  async init() {
    if (!Auth.isLoggedIn()) { window.location.href = '/login?redirect=' + encodeURIComponent('/cases'); return; }
    this._bindEvents();
    await this.loadCases(1);
  },

  _bindEvents() {
    document.getElementById('newCaseBtn')?.addEventListener('click', () => this._showCreateModal());
    document.getElementById('caseSearch')?.addEventListener('input', (e) => {
      clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => { this.currentKeyword = e.target.value.trim(); this.loadCases(1); }, 400);
    });
    document.getElementById('statusFilter')?.addEventListener('change', (e) => { this.currentFilter = e.target.value; this.loadCases(1); });
    document.getElementById('createCaseForm')?.addEventListener('submit', (e) => { e.preventDefault(); this._handleCreateCase(); });
    document.getElementById('closeCreateModal')?.addEventListener('click', () => this._hideCreateModal());
    document.getElementById('createCaseModal')?.addEventListener('click', (e) => { if (e.target.id === 'createCaseModal') this._hideCreateModal(); });
    this._initTagsInput();

    // 添加文件上传按钮事件
    document.getElementById('uploadCaseFileBtn')?.addEventListener('click', () => this._handleUploadAndAnalyze());
  },

  _initTagsInput() {
    const wrapper = document.getElementById('tagsInputWrapper');
    const input = document.getElementById('tagsInput');
    if (!wrapper || !input) return;
    const tags = [];
    const render = () => {
      wrapper.querySelectorAll('.tag-item').forEach(el => el.remove());
      tags.forEach((tag, i) => {
        const s = document.createElement('span');
        s.className = 'tag-item';
        s.innerHTML = escapeHtml(tag) + '<span class="tag-remove">&times;</span>';
        wrapper.insertBefore(s, input);
        s.querySelector('.tag-remove').onclick = () => { tags.splice(i, 1); render(); };
      });
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); const v = input.value.replace(/,/g, '').trim(); if (v && tags.indexOf(v) === -1) { tags.push(v); render(); input.value = ''; } }
      if (e.key === 'Backspace' && input.value === '' && tags.length > 0) { tags.pop(); render(); }
    });
    wrapper._getTags = () => tags;
  },

  async loadCases(page) {
    if (!Auth.isLoggedIn()) return;
    this.currentPage = page || this.currentPage;
    const grid = document.getElementById('casesGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="loading-skeleton">' + [1,2,3,4].map(() => '<div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w40 h12"></div><div class="skeleton-line w80 h8"></div><div class="skeleton-line w100 h8"></div></div>').join('') + '</div>';
    try {
      const params = new URLSearchParams({ page: String(this.currentPage), page_size: String(this.pageSize) });
      if (this.currentKeyword) params.set('keyword', this.currentKeyword);
      if (this.currentFilter) params.set('status', this.currentFilter);
      const resp = await Api.get('cases?' + params.toString());
      const data = resp.data;
      this.totalCount = data.total || 0;
      if (!data.list || data.list.length === 0) {
        grid.innerHTML = '<div class="cases-empty-state" style="grid-column:1/-1;"><div class="empty-icon">📂</div><div class="empty-title">暂无数据</div><div class="empty-desc">还没有创建任何案件，点击上方按钮创建第一个案件</div><button class="btn btn-primary" onclick="CaseApp._showCreateModal()">新建案件</button></div>';
      } else {
        grid.innerHTML = data.list.map(c => this.renderCaseCard(c)).join('');
      }
      this._renderPagination();
    } catch (e) {
      grid.innerHTML = '<div class="cases-empty-state" style="grid-column:1/-1;"><div class="empty-icon">⚠️</div><div class="empty-title">加载失败</div><div class="empty-desc">'+escapeHtml(e.message)+'</div><button class="btn btn-outline" onclick="CaseApp.loadCases()">重试</button></div>';
    }
  },

  renderCaseCard(c) {
    const st = STATUS_MAP[c.status] || STATUS_MAP.pending;
    const ctype = CASE_TYPE_MAP[c.case_type] || c.case_type || '未分类';
    const court = COURT_LEVEL_MAP[c.court_level] || c.court_level || '';
    const wr = c.win_rate != null ? Number(c.win_rate) : null;
    const tags = c.tags || [];
    return '<div class="case-card" onclick="CaseApp.openCaseDetail(\''+escapeHtml(c.id)+'\')" data-case-id="'+escapeHtml(c.id)+'">'
      + '<div class="case-card-header"><span class="case-title">'+escapeHtml(c.title||'未命名案件')+'</span>'+_getStatusBadge(c.status)+'</div>'
      + '<div class="case-card-meta"><span>🏛️ '+escapeHtml(court||'—')+'</span><span>📋 '+escapeHtml(ctype)+'</span><span>🕐 '+formatTime(c.created_at)+'</span></div>'
      + '<div class="case-card-footer"><div class="case-tags">'+tags.slice(0,3).map(t=>'<span class="case-tag">'+escapeHtml(t)+'</span>').join('')+(tags.length>3?'<span class="case-tag">+'+String(tags.length-3)+'</span>':'')+'</div><div class="case-card-stats">'+_getWinBar(wr)+'</div></div>'
      + '</div>';
  },

  _renderPagination() {
    const container = document.getElementById('casesPagination');
    if (!container || this.totalCount <= this.pageSize) { if (container) container.innerHTML = ''; return; }
    const totalPages = Math.ceil(this.totalCount / this.pageSize);
    let html = '<button class="page-btn" '+(this.currentPage===1?'disabled':'')+' onclick="CaseApp.loadCases('+(this.currentPage-1)+')">上一页</button>';
    for (let i=1; i<=totalPages; i++) {
      if (i===1 || i===totalPages || (i>=this.currentPage-2 && i<=this.currentPage+2)) {
        html += '<button class="page-btn'+(i===this.currentPage?' active':'')+'" onclick="CaseApp.loadCases('+i+')">'+i+'</button>';
      } else if (i===this.currentPage-3 || i===this.currentPage+3) {
        html += '<span style="color:var(--color-gray-400);padding:0 4px;">...</span>';
      }
    }
    html += '<button class="page-btn" '+(this.currentPage===totalPages?'disabled':'')+' onclick="CaseApp.loadCases('+(this.currentPage+1)+')">下一页</button>';
    container.innerHTML = html;
  },

  openCaseDetail(caseId) { if (caseId) window.location.href = '/cases/'+caseId; },

  _showCreateModal() { const m = document.getElementById('createCaseModal'); if (m) m.style.display = 'flex'; },
  _hideCreateModal() { const m = document.getElementById('createCaseModal'); if (m) m.style.display = 'none'; document.getElementById('createCaseForm')?.reset(); },

  async _handleCreateCase() {
    const fileInput = document.getElementById('caseFileInput');
    const file = fileInput?.files?.[0];

    // 如果选择了文件，走"上传并分析"流程
    if (file) {
      return this._handleUploadAndAnalyze();
    }

    // 否则走普通创建流程
    const title = document.getElementById('newCaseTitle')?.value?.trim();
    if (!title) { Toast.warning('请输入案件名称'); return; }
    const body = {
      title: title,
      case_type: document.getElementById('newCaseType')?.value || 'civil',
      description: document.getElementById('newCaseDescription')?.value?.trim() || '',
      court_level: document.getElementById('newCaseCourt')?.value || '',
      tags: document.getElementById('tagsInputWrapper')?._getTags ? document.getElementById('tagsInputWrapper')._getTags() : [],
    };
    try {
      const resp = await Api.post('cases', body);
      Toast.success('案件创建成功');
      this._hideCreateModal();
      await this.loadCases(1);
      if (resp.data && resp.data.id) {
        setTimeout(() => { window.location.href = '/cases/' + resp.data.id; }, 500);
      }
    } catch (e) {
      Toast.error('创建失败: ' + e.message);
    }
  },

  async _handleUploadAndAnalyze() {
    const fileInput = document.getElementById('caseFileInput');
    const file = fileInput?.files?.[0];
    if (!file) { Toast.warning('请先选择文件'); return; }

    // 先创建案件
    const title = document.getElementById('newCaseTitle')?.value?.trim() || file.name.replace(/\.[^.]+$/, '');
    const body = {
      title: title,
      case_type: document.getElementById('newCaseType')?.value || 'civil',
      description: document.getElementById('newCaseDescription')?.value?.trim() || '从文件上传: ' + file.name,
      court_level: document.getElementById('newCaseCourt')?.value || '',
      tags: document.getElementById('tagsInputWrapper')?._getTags ? document.getElementById('tagsInputWrapper')._getTags() : [],
    };
    try {
      Toast.info('正在创建案件...');
      const resp = await Api.post('cases', body);
      const caseId = resp.data?.id;
      if (!caseId) { Toast.error('案件创建失败'); return; }

      // 上传文件作为文档
      Toast.info('正在上传文件...');
      const formData = new FormData();
      formData.append('file', file);
      const headers = {};
      const token = Auth.getToken();
      if (token) headers['Authorization'] = 'Bearer ' + token;
      const upResp = await fetch(API_BASE + '/cases/' + caseId + '/upload', { method: 'POST', headers: headers, body: formData });
      if (!upResp.ok) throw new Error('文件上传失败');

      this._hideCreateModal();

      // 触发分析
      Toast.info('正在启动AI分析...');
      await Api.post('cases/' + caseId + '/analysis', {});
      Toast.success('案件创建成功，AI分析已启动！');
      setTimeout(() => { window.location.href = '/cases/' + caseId; }, 800);
    } catch (e) {
      Toast.error('操作失败: ' + e.message);
    }
  },

  deleteCase(caseId) {
    showModal({
      title: '删除案件', message: '确定要删除该案件吗？数据将无法恢复。',
      confirmText: '删除', danger: true,
      onConfirm: async () => { try { await Api.delete('cases/'+caseId); Toast.success('已删除'); this.loadCases(this.currentPage); } catch(e) { Toast.error('删除失败: '+e.message); } },
    });
  },
};

// ── 案件详情页 ──
const CaseDetailApp = {
  caseId: null, caseData: null,

  init(caseId) {
    if (!Auth.isLoggedIn()) { window.location.href = '/login?redirect=' + encodeURIComponent('/cases/'+caseId); return; }
    this.caseId = caseId;
    this._bindTabs();
    this._loadCaseData();
  },

  async _loadCaseData() {
    try {
      const resp = await Api.get('cases/'+this.caseId);
      this.caseData = resp.data;
      this._renderCaseHeader();
    } catch(e) { Toast.error('加载案件失败: '+e.message); }
  },

  _renderCaseHeader() {
    const c = this.caseData; if (!c) return;
    const container = document.getElementById('caseDetailHeader');
    if (!container) return;
    const st = STATUS_MAP[c.status] || STATUS_MAP.pending;
    container.innerHTML = '<div class="case-detail-header-left">'
      + '<a href="/cases" class="case-detail-back"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>返回案件列表</a>'
      + '<div class="case-detail-title-row"><h1>'+escapeHtml(c.title||'未命名案件')+'</h1>'+_getStatusBadge(c.status)+'</div></div>'
      + '<div class="case-detail-header-right">'
      + '<button class="btn btn-primary btn-sm" onclick="CaseDetailApp.triggerAnalysis()">🤖 AI分析</button>'
      + '<a class="btn btn-outline btn-sm" href="/chat?caseLink='+escapeHtml(this.caseId)+'">💬 智能咨询</a>'
      + '<button class="btn btn-outline btn-sm" onclick="CaseDetailApp._showUploadModal()">📤 上传文件</button>'
      + '<button class="btn btn-outline btn-sm" style="color:var(--color-accent-red);border-color:var(--color-accent-red);" onclick="CaseApp.deleteCase(\''+escapeHtml(this.caseId)+'\')">删除</button></div>';
    const infoBar = document.getElementById('caseInfoBar');
    if (infoBar) {
      const ctype = CASE_TYPE_MAP[c.case_type] || c.case_type || '';
      const court = COURT_LEVEL_MAP[c.court_level] || c.court_level || '';
      const wr = c.win_rate != null ? Number(c.win_rate) : null;
      infoBar.innerHTML = '<div class="info-item"><span class="info-label">类型：</span><span class="info-value">'+escapeHtml(ctype)+'</span></div>'
        + '<div class="info-item"><span class="info-label">法院：</span><span class="info-value">'+escapeHtml(court||'—')+'</span></div>'
        + '<div class="info-item"><span class="info-label">创建：</span><span class="info-value">'+formatTime(c.created_at)+'</span></div>'
        + (wr !== null ? '<div class="info-item">'+_getWinBar(wr)+'</div>' : '');
    }
  },

  _bindTabs() {
    document.querySelectorAll('#caseTabs .tab-item').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });
  },

  switchTab(tabName) {
    document.querySelectorAll('#caseTabs .tab-item').forEach(t => t.classList.toggle('active', t.dataset.tab===tabName));
    document.querySelectorAll('#caseTabContent .tab-content').forEach(el => el.classList.toggle('active', el.id==='tab-'+tabName));
    switch(tabName) {
      case 'analysis': this.loadAnalysis(); break;
      case 'qa': this._initQA(); break;
      case 'evidence': this.loadEvidence(); break;
      case 'evidence-chain': this.loadEvidenceChain(); break;
      case 'evidence-list': this.loadEvidenceList(); break;
      case 'documents': this.loadDocuments(); break;
    }
  },

  // ── 案情分析 ──
  async loadAnalysis() {
    const container = document.getElementById('tab-analysis');
    if (!container || container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      const resp = await Api.get('cases/'+this.caseId+'/analysis');
      const d = resp.data;
      if (!d || (!d['案情摘要'] && !d['案情时间轴'] && !d['事实分析'])) {
        container.innerHTML = '<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无案情分析</div><div class="empty-desc">点击右上角"分析"按钮生成AI案情分析</div><button class="btn btn-primary" onclick="CaseDetailApp.triggerAnalysis()">开始分析</button></div>';
      } else {
        container.innerHTML = this._renderAnalysisContent(d);
      }
      container.dataset.loaded = 'true';
    } catch(e) {
      container.innerHTML = '<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无案情分析</div><div class="empty-desc">点击右上角"分析"按钮生成AI案情分析</div><button class="btn btn-primary" onclick="CaseDetailApp.triggerAnalysis()">开始分析</button></div>';
    }
  },

  _renderAnalysisContent(d) {
    let html = '';
    // 时间轴
    const timeline = d['案情时间轴'];
    if (timeline && Array.isArray(timeline) && timeline.length > 0) {
      html += '<div class="analysis-section"><h3><span class="section-icon">⏱️</span>案情时间轴</h3><div class="timeline">'
        + timeline.map(item => '<div class="timeline-item"><div class="timeline-date">'+escapeHtml(item.date||'')+'</div><div class="timeline-title">'+escapeHtml(item.title||'')+'</div>'+(item.description?'<div class="timeline-desc">'+escapeHtml(item.description)+'</div>':'')+'</div>').join('')
        + '</div></div>';
    }
    // 各个分析模块
    const sections = [
      { key: '案情摘要', title: '案情摘要', icon: '📋' },
      { key: '事实分析', title: '事实分析', icon: '🔍' },
      { key: '法律分析', title: '法律分析', icon: '⚖️' },
      { key: '定争分析', title: '定争分析', icon: '🎯' },
      { key: '司法推理', title: '司法推理', icon: '📝' },
      { key: '参考判例', title: 'AI推荐判例', icon: '💡' },
    ];
    sections.forEach(sec => {
      const content = d[sec.key];
      if (content && typeof content === 'string') {
        html += '<div class="analysis-section"><h3><span class="section-icon">'+sec.icon+'</span>'+sec.title+'</h3>'
          + '<div class="section-content">'+simpleMarkdown(content)+'</div></div>';
      }
    });
    return html || '<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无分析内容</div></div>';
  },

  async triggerAnalysis() {
    try {
      Toast.info('正在启动分析...');
      await Api.post('cases/'+this.caseId+'/analysis', {});
      Toast.success('分析完成');
      await this._loadCaseData();
      const c = document.getElementById('tab-analysis');
      if (c) c.dataset.loaded = 'false';
      this.switchTab('analysis');
    } catch(e) { Toast.error('分析失败: '+e.message); }
  },

  // ── QA 问答 ──
  _initQA() {
    const container = document.getElementById('tab-qa');
    if (!container || container.dataset.inited==='true') return;
    container.dataset.inited = 'true';
    this._loadQAHistory();
    document.getElementById('qaSendBtn')?.addEventListener('click', () => { const q = document.getElementById('qaInput')?.value?.trim(); if (q) this.sendQuestion(q); });
    document.getElementById('qaInput')?.addEventListener('keydown', (e) => { if (e.key==='Enter'&&!e.shiftKey) { e.preventDefault(); const q = e.target.value.trim(); if (q) this.sendQuestion(q); } });
  },

  async _loadQAHistory() {
    const list = document.getElementById('qaList'); if (!list) return;
    try {
      const resp = await Api.get('cases/'+this.caseId+'/qa');
      const data = resp.data;
      const items = data.list || data || [];
      if (items.length === 0) {
        list.innerHTML = '<div class="cases-empty-state" style="padding:var(--space-8);"><div class="empty-icon">💬</div><div class="empty-title">暂无问答记录</div><div class="empty-desc">在下方输入框中提问</div></div>';
      } else {
        list.innerHTML = items.map(item => '<div class="qa-question"><div class="qa-question-bubble">'+escapeHtml(item.question)+'</div></div><div class="qa-answer"><div class="qa-answer-card"><div class="qa-answer-header">AI回答 · '+formatTime(item.created_at)+'</div><div class="qa-answer-body">'+simpleMarkdown(item.answer||'')+'</div></div></div>').join('');
      }
    } catch(e) { list.innerHTML = '<div class="cases-empty-state"><div class="empty-title">加载失败</div></div>'; }
  },

  async sendQuestion(question) {
    if (!question) return;
    const input = document.getElementById('qaInput'); if (input) input.value = '';
    const list = document.getElementById('qaList'); if (!list) return;
    const qEl = document.createElement('div'); qEl.className = 'qa-question'; qEl.innerHTML = '<div class="qa-question-bubble">'+escapeHtml(question)+'</div>'; list.appendChild(qEl);
    const aEl = document.createElement('div'); aEl.className = 'qa-answer'; aEl.innerHTML = '<div class="qa-answer-card"><div class="qa-answer-header">AI回答 · 思考中...</div><div class="qa-answer-body"><div class="spinner" style="margin:var(--space-4) auto;"></div></div></div>'; list.appendChild(aEl);
    list.scrollTop = list.scrollHeight;
    try {
      const resp = await Api.post('cases/'+this.caseId+'/qa', { question });
      aEl.querySelector('.qa-answer-body').innerHTML = simpleMarkdown(resp.data?.answer || '暂无回答');
      aEl.querySelector('.qa-answer-header').textContent = 'AI回答 · '+formatTime(new Date().toISOString());
    } catch(e) {
      aEl.querySelector('.qa-answer-body').innerHTML = '<p style="color:var(--color-accent-red);">错误: '+escapeHtml(e.message)+'</p>';
      aEl.querySelector('.qa-answer-header').textContent = 'AI回答 · 请求失败';
    }
    list.scrollTop = list.scrollHeight;
  },

  // ── 证据链 ──
  async loadEvidenceChain() {
    const container = document.getElementById('tab-evidence-chain'); if (!container || container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      const resp = await Api.get('cases/'+this.caseId+'/evidence-chain');
      const d = resp.data || {};
      const nodes = d['证据节点'] || d.chain || d['证据链结构'] || {};
      const nodeList = Array.isArray(nodes) ? nodes : Object.values(nodes);
      let html = '<div class="analysis-actions"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp.triggerEvidenceChain()">重新生成</button></div>';
      if (d['证据链概述']) html += '<div class="analysis-section"><h3>📊 证据链概述</h3><div class="section-content">'+simpleMarkdown(d['证据链概述'])+'</div></div>';
      html += '<div class="evidence-chain">' + nodeList.slice(0,10).map((item,i) => {
        const name = typeof item === 'string' ? item : (item.name||item.title||'证据节点 '+(i+1));
        const desc = typeof item === 'string' ? '' : (item.description||item.relation||'');
        return '<div class="evidence-chain-item"><div class="chain-title">'+(i+1)+'. '+escapeHtml(name)+'</div>'+(desc?'<div class="chain-desc">'+escapeHtml(desc)+'</div>':'')+'</div>';
      }).join('') + '</div>';
      if (d['证据链完整性评估']) html += '<div class="analysis-section"><h3>📈 完整性评估</h3><div class="section-content">'+simpleMarkdown(d['证据链完整性评估'])+'</div></div>';
      if (d['薄弱环节']) html += '<div class="analysis-section"><h3>⚠️ 薄弱环节</h3><div class="section-content">'+simpleMarkdown(d['薄弱环节'])+'</div></div>';
      container.innerHTML = html;
      container.dataset.loaded = 'true';
    } catch(e) {
      container.innerHTML = '<div class="analysis-actions"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp.triggerEvidenceChain()">生成证据链</button></div><div class="cases-empty-state"><div class="empty-icon">🔗</div><div class="empty-title">暂无证据链</div></div>';
    }
  },

  async triggerEvidenceChain() {
    try { Toast.info('正在生成证据链...'); await Api.post('cases/'+this.caseId+'/evidence-chain', {}); Toast.success('证据链生成完成'); const c=document.getElementById('tab-evidence-chain'); if(c)c.dataset.loaded='false'; this.loadEvidenceChain(); } catch(e) { Toast.error('生成失败: '+e.message); }
  },

  // ── 证据清单 ──
  async loadEvidenceList() {
    const container = document.getElementById('tab-evidence-list'); if (!container || container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      const resp = await Api.get('cases/'+this.caseId+'/evidence-list');
      const d = resp.data || {};
      let html = '<div class="analysis-actions"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp.triggerEvidenceList()">重新生成</button></div>';
      // 动态查找原被告证据键
      const keys = Object.keys(d).filter(k => k.includes('证据') || k.includes('方'));
      let foundAny = false;
      keys.forEach(k => {
        const items = d[k];
        if (!Array.isArray(items)) return;
        foundAny = true;
        html += '<div class="evidence-list-group"><div class="evidence-list-group-header">'+escapeHtml(k)+'</div>';
        if (items.length===0) html += '<div style="padding:var(--space-6);text-align:center;color:var(--color-gray-500);">暂无数据</div>';
        else items.forEach((item,i) => {
          html += '<div class="evidence-list-item"><span class="item-num">'+(i+1)+'</span><span class="item-name">'+escapeHtml(item.name||'证据项')+'</span><span class="item-status badge '+(item.admissibility==='高'?'badge-analyzed':'badge-pending')+'">采信度: '+escapeHtml(item.admissibility||'中')+'</span></div>';
        });
        html += '</div>';
      });
      if (!foundAny) html += '<div class="cases-empty-state"><div class="empty-icon">📊</div><div class="empty-title">暂无证据清单数据</div></div>';
      // 分析内容
      ['薄弱点','矛盾点','法官采信分析','补充建议'].forEach(sec => {
        const content = d[sec];
        if (content) {
          const display = Array.isArray(content) ? content.map(x=>'<li>'+escapeHtml(typeof x==='string'?x:JSON.stringify(x))+'</li>').join('') : simpleMarkdown(content);
          html += '<div class="analysis-section"><h3>📊 '+sec+'</h3><div class="section-content">'+(Array.isArray(content)?'<ul>'+display+'</ul>':display)+'</div></div>';
        }
      });
      container.innerHTML = html;
      container.dataset.loaded = 'true';
    } catch(e) {
      container.innerHTML = '<div class="analysis-actions"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp.triggerEvidenceList()">生成证据清单</button></div><div class="cases-empty-state"><div class="empty-icon">📊</div><div class="empty-title">暂无证据清单</div></div>';
    }
  },

  async triggerEvidenceList() {
    try { Toast.info('正在生成证据清单...'); await Api.post('cases/'+this.caseId+'/evidence-list', {}); Toast.success('生成完成'); const c=document.getElementById('tab-evidence-list'); if(c)c.dataset.loaded='false'; this.loadEvidenceList(); } catch(e) { Toast.error('生成失败: '+e.message); }
  },

  // ── 材料证据 ──
  async loadEvidence() {
    const container = document.getElementById('tab-evidence'); if (!container || container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      const resp = await Api.get('cases/'+this.caseId+'/evidence');
      const data = resp.data; const items = data.list || data || [];
      let html = '<div class="section-toolbar"><h3>共 '+items.length+' 项证据</h3><div class="toolbar-actions"><button class="btn btn-primary btn-sm" onclick="CaseDetailApp._showEvidenceForm()">新建证据</button></div></div>';
      if (items.length===0) { html += '<div class="cases-empty-state"><div class="empty-icon">📁</div><div class="empty-title">暂无证据材料</div></div>'; }
      else {
        html += '<div class="evidence-grid">';
        items.forEach(item => {
          const iconMap = { '书面文件':'📄','电子文档':'📘','照片和视频':'🖼️','音频记录':'🎵','物证':'📦' };
          const icon = iconMap[item.evidence_type] || '📁';
          const isApproved = item.status && (item.status.includes('通过') || item.status.includes('已审核'));
          html += '<div class="evidence-card" onclick="CaseDetailApp.loadEvidenceDetail(\''+escapeHtml(item.id)+'\')">'
            + '<div class="evidence-icon">'+icon+'</div>'
            + '<div class="evidence-info"><div class="evidence-name">'+escapeHtml(item.name||'未命名证据')+'</div>'
            + '<div class="evidence-meta"><span>'+escapeHtml(item.evidence_type||'其他')+'</span>'
            + '<span class="badge '+(isApproved?'badge-analyzed':'badge-pending')+'">'+(isApproved?'已审核':escapeHtml(item.status||'待审核'))+'</span></div></div></div>';
        });
        html += '</div>';
      }
      container.innerHTML = html; container.dataset.loaded = 'true';
    } catch(e) { container.innerHTML = '<div class="cases-empty-state"><div class="empty-title">加载失败: '+escapeHtml(e.message)+'</div></div>'; }
  },

  _showEvidenceForm() {
    const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal" style="max-width:480px;"><h3>新建证据</h3>'
      + '<div class="form-group"><label>证据名称</label><input type="text" class="input" id="evName" placeholder="请输入证据名称"></div>'
      + '<div class="form-group"><label>证据类型</label><select id="evType"><option value="书面文件">书面文件</option><option value="电子文档">电子文档</option><option value="照片和视频">照片和视频</option><option value="音频记录">音频记录</option><option value="物证">物证</option></select></div>'
      + '<div class="form-group"><label>描述</label><textarea id="evDesc" class="input" rows="3" placeholder="请输入证据描述"></textarea></div>'
      + '<div class="form-group"><label>证明目的</label><input type="text" class="input" id="evPurpose" placeholder="请输入证明目的"></div>'
      + '<div class="modal-actions"><button class="btn btn-outline" id="cancelEv">取消</button><button class="btn btn-primary" id="submitEv">确认</button></div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelector('#cancelEv').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target===overlay) close(); });
    overlay.querySelector('#submitEv').addEventListener('click', async () => {
      const name = document.getElementById('evName')?.value?.trim();
      if (!name) { Toast.warning('请输入证据名称'); return; }
      try {
        await Api.post('cases/'+this.caseId+'/evidence', {
          name, evidence_type: document.getElementById('evType')?.value||'书面文件',
          description: document.getElementById('evDesc')?.value?.trim()||'',
          purpose: document.getElementById('evPurpose')?.value?.trim()||'',
        });
        Toast.success('证据创建成功'); close();
        const c = document.getElementById('tab-evidence'); if (c) c.dataset.loaded = 'false'; this.loadEvidence();
      } catch(e) { Toast.error('创建失败: '+e.message); }
    });
  },

  async loadEvidenceDetail(evidenceId) {
    const overlay = document.createElement('div'); overlay.className = 'evidence-detail-overlay';
    overlay.innerHTML = '<div class="evidence-detail"><div class="evidence-detail-body"><div class="spinner" style="margin:40px auto;"></div></div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.addEventListener('click', e => { if (e.target===overlay) close(); });
    try {
      const resp = await Api.get('cases/'+this.caseId+'/evidence/'+evidenceId);
      const item = resp.data;
      const isApproved = item.status && (item.status.includes('通过') || item.status.includes('已审核'));
      overlay.innerHTML = '<div class="evidence-detail"><div class="evidence-detail-header"><h3>'+escapeHtml(item.name||'证据详情')+'</h3><button class="evidence-detail-close">&times;</button></div>'
        +'<div class="evidence-detail-body"><div class="detail-row"><span class="detail-label">类型</span><span class="detail-value">'+escapeHtml(item.evidence_type||'其他')+'</span></div>'
        +'<div class="detail-row"><span class="detail-label">状态</span><span class="detail-value"><span class="badge '+(isApproved?'badge-analyzed':'badge-pending')+'">'+escapeHtml(item.status||'待审核')+'</span></span></div>'
        +(item.description?'<div class="detail-row"><span class="detail-label">描述</span><span class="detail-value">'+escapeHtml(item.description)+'</span></div>':'')
        +(item.purpose?'<div class="detail-row"><span class="detail-label">证明目的</span><span class="detail-value">'+escapeHtml(item.purpose)+'</span></div>':'')
        +(item.audit_reason?'<div class="detail-row"><span class="detail-label">审核结果</span><span class="detail-value">'+simpleMarkdown(item.audit_reason)+'</span></div>':'')
        +'</div><div class="evidence-detail-footer">'
        +(!isApproved?'<button class="btn btn-primary btn-sm" id="auditBtn">🤖 AI审核</button>':'')
        +'<button class="btn btn-outline btn-sm evCloseBtn">关闭</button></div></div>';
      overlay.querySelector('.evidence-detail-close')?.addEventListener('click', close);
      overlay.querySelector('.evCloseBtn')?.addEventListener('click', close);
      overlay.querySelector('#auditBtn')?.addEventListener('click', async () => {
        try { Toast.info('正在审核...'); await Api.post('cases/'+this.caseId+'/evidence/'+evidenceId+'/audit',{}); Toast.success('审核完成'); close(); const c=document.getElementById('tab-evidence'); if(c)c.dataset.loaded='false'; this.loadEvidence(); } catch(e) { Toast.error('审核失败: '+e.message); }
      });
    } catch(e) {
      overlay.innerHTML = '<div class="evidence-detail"><div class="evidence-detail-body"><p style="color:var(--color-accent-red);text-align:center;padding:var(--space-8);">加载失败: '+escapeHtml(e.message)+'</p></div></div>';
      overlay.addEventListener('click', close);
    }
  },

  // ── 文档管理 ──
  async loadDocuments() {
    const container = document.getElementById('tab-documents'); if (!container || container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      const resp = await Api.get('cases/'+this.caseId+'/documents');
      const data = resp.data; const items = data.list || data || [];
      let html = '<div class="document-list"><div class="document-list-header"><span>共 '+items.length+' 个文档</span><button class="btn btn-primary btn-sm" onclick="CaseDetailApp._showUploadModal()">上传文档</button></div>';
      if (items.length===0) { html += '<div style="padding:var(--space-10);text-align:center;color:var(--color-gray-500);">暂无文档</div>'; }
      else {
        items.forEach(doc => {
          const ext = (doc.name||'').split('.').pop()?.toLowerCase()||'';
          const icons = { pdf:'📕',doc:'📘',docx:'📘',xls:'📗',xlsx:'📗',png:'🖼️',jpg:'🖼️',jpeg:'🖼️' };
          html += '<div class="document-item"><div class="doc-icon">'+(icons[ext]||'📄')+'</div><div class="doc-info"><div class="doc-name">'+escapeHtml(doc.name||'未命名文档')+'</div><div class="doc-meta">'+escapeHtml(formatTime(doc.created_at)||'')+'</div></div>'
            +'<div class="doc-actions"><button data-doc-url="' + escapeHtml(doc.file_url||'') + '" onclick="CaseDetailApp._downloadByData(this)">下载</button><button onclick="CaseDetailApp._deleteDoc(\''+escapeHtml(doc.id)+'\')">删除</button></div></div>';
        });
      }
      html += '</div>'; container.innerHTML = html; container.dataset.loaded = 'true';
    } catch(e) { container.innerHTML = '<div class="cases-empty-state"><div class="empty-title">加载失败: '+escapeHtml(e.message)+'</div></div>'; }
  },

  _showUploadModal() {
    const overlay = document.createElement('div'); overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal"><h3>上传文档</h3><div class="form-group"><label>选择文件</label><input type="file" id="docFile" class="input" accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt"></div><div class="modal-actions"><button class="btn btn-outline cancelUp">取消</button><button class="btn btn-primary confirmUp">上传并分析</button></div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelector('.cancelUp').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target===overlay) close(); });
    overlay.querySelector('.confirmUp').addEventListener('click', async () => {
      const file = document.getElementById('docFile')?.files?.[0];
      if (!file) { Toast.warning('请选择文件'); return; }
      try {
        Toast.info('正在上传文档...');
        const formData = new FormData(); formData.append('file', file);
        const headers = {}; const token = Auth.getToken(); if (token) headers['Authorization'] = 'Bearer '+token;
        const resp = await fetch(API_BASE+'/cases/'+this.caseId+'/upload', { method:'POST', headers, body:formData });
        if (!resp.ok) { const err = await resp.json().catch(()=>({message:'HTTP '+resp.status})); throw new Error(err.message||'上传失败'); }
        Toast.success('上传成功，启动AI分析...');
        close();
        const cDocs = document.getElementById('tab-documents'); if (cDocs) cDocs.dataset.loaded = 'false';
        this.loadDocuments();
        // 自动触发分析
        await Api.post('cases/'+this.caseId+'/analysis', {});
        Toast.success('AI分析已启动');
        await this._loadCaseData();
        const cAna = document.getElementById('tab-analysis'); if (cAna) cAna.dataset.loaded = 'false';
        this.switchTab('analysis');
      } catch(e) { Toast.error('操作失败: '+e.message); }
    });
  },

  _downloadDoc(url) { if (url) window.open(url, '_blank'); },
  _downloadByData(el) { const url = el?.getAttribute('data-doc-url'); if (url) window.open(url, '_blank'); },

  async _deleteDoc(docId) {
    showModal({ title:'删除文档', message:'确定删除该文档吗？', confirmText:'删除', danger:true, onConfirm: async () => {
      try { await Api.delete('cases/'+this.caseId+'/documents/'+docId); Toast.success('已删除'); const c=document.getElementById('tab-documents'); if(c)c.dataset.loaded='false'; this.loadDocuments(); } catch(e) { Toast.error('删除失败: '+e.message); }
    }});
  },
};
