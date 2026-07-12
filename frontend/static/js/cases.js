/* ═══════════════════════════════════════
   AI法律助手 v1.0 — 案件管理（精简版）
   保留：案情梳理 + 案件文档
   删除：QA问答 / 证据链 / 证据清单 / 材料证据
   ═══════════════════════════════════════ */

const DOC_CATEGORIES = [
  { value: 'indictment', label: '起诉书' },
  { value: 'judgment', label: '判决书' },
  { value: 'notice', label: '通知书' },
  { value: 'evidence', label: '证据材料' },
  { value: 'defense', label: '辩护词' },
  { value: 'other', label: '其他文件' },
];

function _getWinBar(rate) {
  if (rate === null || rate === undefined) return '';
  var pct = Number(rate) || 0;
  var color = pct >= 70 ? 'var(--color-accent-green)' : pct >= 45 ? 'var(--color-warning)' : 'var(--color-accent-red)';
  return '<span class="win-rate-badge" style="background:'+color+'15;color:'+color+';border:1px solid '+color+'40;padding:2px 8px;border-radius:12px;font-size:var(--text-xs);">胜诉率评估: '+Math.round(pct)+'%</span>';
}

const CaseApp = {
  page: 1, search: '', status: '', tags: [],

  async init() {
    if (!Auth.requireLogin()) return;
    this._bindEvents();
    await this.loadCases();
  },

  _bindEvents() {
    document.getElementById('newCaseBtn')?.addEventListener('click', () => this._showCreateModal());
    document.getElementById('closeCreateModal')?.addEventListener('click', () => { document.getElementById('createCaseModal').style.display = 'none'; });
    document.getElementById('createCaseForm')?.addEventListener('submit', (e) => { e.preventDefault(); this._createCase(); });

    var self = this;
    document.getElementById('caseSearch')?.addEventListener('input', function() { self.search = this.value; self.page = 1; self.loadCases(); });
    document.getElementById('statusFilter')?.addEventListener('change', function() { self.status = this.value; self.page = 1; self.loadCases(); });

    var tagsInput = document.getElementById('tagsInput');
    var tagsWrapper = document.getElementById('tagsInputWrapper');
    tagsInput?.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { e.preventDefault(); var v = this.value.trim(); if (v && self.tags.indexOf(v) < 0) { self.tags.push(v); self._renderTags(tagsWrapper); this.value = ''; } }
    });
  },

  _renderTags(wrapper) {
    var existing = wrapper.querySelectorAll('.tag-chip'); existing.forEach(function(c) { c.remove(); });
    var input = document.getElementById('tagsInput');
    this.tags.forEach(function(t, i) {
      var chip = document.createElement('span'); chip.className = 'tag-chip';
      chip.style.cssText = 'display:inline-flex;align-items:center;gap:4px;background:var(--color-primary-50);color:var(--color-primary-700);padding:2px 8px;border-radius:12px;font-size:var(--text-xs);margin:2px;';
      chip.innerHTML = t + '<span style="cursor:pointer;margin-left:4px;" data-idx="'+i+'">×</span>';
      wrapper.insertBefore(chip, input);
    });
    var self = this;
    wrapper.addEventListener('click', function(e) {
      if (e.target.dataset.idx !== undefined) { self.tags.splice(Number(e.target.dataset.idx), 1); self._renderTags(wrapper); }
    });
  },

  _showCreateModal() {
    this.tags = [];
    this._renderTags(document.getElementById('tagsInputWrapper'));
    document.getElementById('createCaseModal').style.display = 'flex';
    document.getElementById('newCaseTitle').focus();
  },

  async _createCase() {
    var title = document.getElementById('newCaseTitle').value.trim();
    var type = document.getElementById('newCaseType').value;
    var desc = document.getElementById('newCaseDescription').value.trim();
    var court = document.getElementById('newCaseCourt').value;
    if (!title) { Toast.warning('请输入案件名称'); return; }
    try {
      var resp = await Api.post('cases', { title: title, case_type: type, description: desc, court_level: court, tags: this.tags });
      Toast.success('案件已创建');
      document.getElementById('createCaseModal').style.display = 'none';
      window.location.href = '/cases/' + resp.data.id;
    } catch(e) { Toast.error('创建失败: ' + e.message); }
  },

  async loadCases() {
    var grid = document.getElementById('casesGrid'); if (!grid) return;
    grid.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div></div></div>';
    try {
      var qs = '?page='+this.page+'&page_size=12';
      if (this.search) qs += '&search='+encodeURIComponent(this.search);
      if (this.status) qs += '&status='+encodeURIComponent(this.status);
      var resp = await Api.get('cases'+qs);
      var data = resp.data; var items = data.list || [];
      if (items.length===0) {
        grid.innerHTML = '<div class="cases-empty-state"><div class="empty-icon">📂</div><div class="empty-title">暂无案件</div><div class="empty-desc">点击「新建案件」开始</div></div>';
      } else {
        grid.innerHTML = items.map(function(c) {
          var wr = c.win_rate; var tags = c.tags || [];
          return '<a href="/cases/'+encodeURIComponent(c.id)+'" class="case-card-link" style="text-decoration:none;color:inherit;">'
            + '<div class="case-card"><div class="case-card-header"><h3>'+escapeHtml(c.title)+'</h3>'
            + '<span class="badge '+(c.status==='已分析'?'badge-analyzed':c.status==='分析中'?'badge-pending':'badge-pending')+'">'+escapeHtml(c.status||'待分析')+'</span></div>'
            + '<div class="case-card-body"><div class="case-meta"><span>'+escapeHtml(c.case_type||'')+'</span>'
            + (c.court_level?'<span>'+escapeHtml(c.court_level)+'</span>':'')
            + '<span>'+escapeHtml(formatTime(c.created_at))+'</span></div></div>'
            + '<div class="case-card-footer"><div class="case-tags">'+tags.slice(0,3).map(function(t){return '<span class="case-tag">'+escapeHtml(t)+'</span>';}).join('')+(tags.length>3?'<span class="case-tag">+'+String(tags.length-3)+'</span>':'')+'</div>'+_getWinBar(wr)+'</div></div></a>';
        }).join('');
      }
      this._renderPagination(data.total, data.page, data.page_size);
    } catch(e) { grid.innerHTML = '<div class="cases-empty-state"><div class="empty-title">加载失败: '+escapeHtml(e.message)+'</div></div>'; }
  },

  _renderPagination(total, page, pageSize) {
    var el = document.getElementById('casesPagination'); if (!el) return;
    var totalPages = Math.ceil(total / pageSize); if (totalPages <= 1) { el.innerHTML = ''; return; }
    var html = '';
    for (var i = 1; i <= totalPages; i++) {
      html += '<button class="page-btn'+(i===page?' active':'')+'" onclick="CaseApp.goPage('+i+')">'+i+'</button>';
    }
    el.innerHTML = html;
  },

  goPage(p) { this.page = p; this.loadCases(); window.scrollTo(0,0); }
};

// ── 案件详情页 ──
const CaseDetailApp = {
  caseId: null,

  async init(caseId) {
    if (!Auth.requireLogin()) return;
    this.caseId = caseId;
    await this._loadCaseData();
    this._bindTabs();
    this.switchTab('analysis');
  },

  async _loadCaseData() {
    try {
      var resp = await Api.get('cases/'+this.caseId);
      var d = resp.data;
      if (!d) { Toast.error('案件不存在'); return; }
      var wr = d.win_rate;

      // 更新标题
      var header = document.getElementById('caseDetailHeader');
      if (header) {
        var h1 = header.querySelector('h1');
        if (h1) h1.textContent = d.title || '未命名案件';
      }

      // 更新信息栏
      var infoEl = document.getElementById('caseInfoBar');
      if (infoEl) {
        var parts = [];
        parts.push('<div class="info-item"><span class="info-label">案件类型</span><span>'+escapeHtml(d.case_type||'')+'</span></div>');
        if (d.court_level) parts.push('<div class="info-item"><span class="info-label">审理级别</span><span>'+escapeHtml(d.court_level)+'</span></div>');
        parts.push('<div class="info-item"><span class="info-label">案件状态</span><span class="badge '+(d.status==='已分析'?'badge-analyzed':'badge-pending')+'">'+escapeHtml(d.status||'待分析')+'</span></div>');
        if (wr!==null) parts.push('<div class="info-item">'+_getWinBar(wr)+'</div>');
        if (d.tags&&d.tags.length) parts.push('<div class="info-item"><span class="info-label">标签</span><span>'+d.tags.map(function(t){return '<span class="case-tag">'+escapeHtml(t)+'</span>';}).join(' ')+'</span></div>');
        if (d.description) parts.push('<div class="info-item"><span class="info-label">案件描述</span><span>'+escapeHtml(d.description)+'</span></div>');
        // 添加上传按钮
        parts.push('<div class="info-item" style="margin-top:var(--space-2);"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp._showUploadModal()">📤 上传文件</button></div>');
        infoEl.innerHTML = parts.join('');
      }
    } catch(e) { Toast.error('加载案件失败: '+e.message); }
  },

  _bindTabs() {
    var self = this;
    document.querySelectorAll('#caseTabs .tab-item').forEach(function(tab) {
      tab.addEventListener('click', function() { self.switchTab(this.dataset.tab); });
    });
  },

  switchTab(tabName) {
    document.querySelectorAll('#caseTabs .tab-item').forEach(function(t) { t.classList.toggle('active', t.dataset.tab===tabName); });
    document.querySelectorAll('#caseTabContent .tab-content').forEach(function(el) { el.classList.toggle('active', el.id==='tab-'+tabName); });
    if (tabName==='analysis') this.loadAnalysis();
    else if (tabName==='documents') this.loadDocuments();
  },

  // ── 案情分析 ──
  async loadAnalysis() {
    var container = document.getElementById('tab-analysis'); if (!container||container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div><div class="skeleton-line w100 h8"></div></div></div>';
    try {
      var resp = await Api.get('cases/'+this.caseId+'/analysis');
      var d = resp.data;
      if (!d||(!d['案情摘要']&&!d['案情时间轴']&&!d['事实分析'])) {
        container.innerHTML = '<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无案情分析</div><div class="empty-desc">上传案件文件后点击"AI分析"生成智能案情梳理</div><button class="btn btn-primary" onclick="CaseDetailApp.triggerAnalysis()">开始AI分析</button></div>';
      } else {
        container.innerHTML = this._renderAnalysisContent(d);
      }
      container.dataset.loaded = 'true';
    } catch(e) {
      container.innerHTML = '<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无案情分析</div><div class="empty-desc">上传案件文件后点击"AI分析"生成智能案情梳理</div><button class="btn btn-primary" onclick="CaseDetailApp.triggerAnalysis()">开始AI分析</button></div>';
    }
  },

  _renderAnalysisContent(d) {
    var html = '<div class="analysis-actions"><button class="btn btn-outline btn-sm" onclick="CaseDetailApp.triggerAnalysis()">🔄 重新AI分析</button></div>';
    var timeline = d['案情时间轴'];
    if (timeline&&Array.isArray(timeline)&&timeline.length>0) {
      html += '<div class="analysis-section"><h3><span class="section-icon">⏱️</span>案情时间轴</h3><div class="timeline">'
        + timeline.map(function(item){return '<div class="timeline-item"><div class="timeline-date">'+escapeHtml(item.date||'')+'</div><div class="timeline-title">'+escapeHtml(item.title||'')+'</div>'+(item.description?'<div class="timeline-desc">'+escapeHtml(item.description)+'</div>':'')+'</div>';}).join('')
        + '</div></div>';
    }
    var sections = [
      {key:'案情摘要',title:'案情摘要',icon:'📋'},
      {key:'事实分析',title:'事实分析',icon:'🔍'},
      {key:'法律分析',title:'法律分析',icon:'⚖️'},
      {key:'定争分析',title:'定争分析',icon:'🎯'},
      {key:'司法推理',title:'司法推理',icon:'📝'},
      {key:'参考判例',title:'AI推荐判例',icon:'💡'},
    ];
    sections.forEach(function(sec) {
      var content = d[sec.key];
      if (content&&typeof content==='string') {
        html += '<div class="analysis-section"><h3><span class="section-icon">'+sec.icon+'</span>'+sec.title+'</h3>'
          + '<div class="section-content">'+simpleMarkdown(content)+'</div></div>';
      }
    });
    return html||'<div class="cases-empty-state"><div class="empty-icon">📋</div><div class="empty-title">暂无分析内容</div></div>';
  },

  async triggerAnalysis() {
    try {
      Toast.info('正在进行AI分析...');
      await Api.post('cases/'+this.caseId+'/analysis', {});
      Toast.success('AI分析完成');
      await this._loadCaseData();
      var c = document.getElementById('tab-analysis'); if(c)c.dataset.loaded='false';
      this.switchTab('analysis');
    } catch(e) { Toast.error('分析失败: '+e.message); }
  },

  // ── 案件文档 ──
  async loadDocuments() {
    var container = document.getElementById('tab-documents'); if (!container||container.dataset.loaded==='true') return;
    container.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"><div class="skeleton-line w60 h24"></div></div></div>';
    try {
      var resp = await Api.get('cases/'+this.caseId+'/documents');
      var data = resp.data; var items = data.list||data||[];
      var html = '<div class="document-list"><div class="document-list-header"><span>共 '+items.length+' 个文档</span><button class="btn btn-primary btn-sm" onclick="CaseDetailApp._showUploadModal()">上传文档</button></div>';
      if (items.length===0) { html += '<div style="padding:var(--space-10);text-align:center;color:var(--color-gray-500);">暂无文档，请点击"上传文档"按钮上传案件文件</div>'; }
      else {
        items.forEach(function(doc) {
          var ext = (doc.name||'').split('.').pop()?.toLowerCase()||'';
          var icons = {pdf:'📕',doc:'📘',docx:'📘',xls:'📗',xlsx:'📗',png:'🖼️',jpg:'🖼️',jpeg:'🖼️'};
          var cat = doc.doc_category||'';
          var catLabel = DOC_CATEGORIES.find(function(c){return c.value===cat;});
          html += '<div class="document-item"><div class="doc-icon">'+(icons[ext]||'📄')+'</div><div class="doc-info">'
            + '<div class="doc-name">'+escapeHtml(doc.name||'未命名文档')+'</div>'
            + (catLabel?'<div class="doc-meta">'+escapeHtml(catLabel.label)+' · '+escapeHtml(formatTime(doc.created_at)||'')+'</div>':'<div class="doc-meta">'+escapeHtml(formatTime(doc.created_at)||'')+'</div>')
            + '</div>'
            + '<div class="doc-actions"><button data-doc-url="'+escapeHtml(doc.file_url||'')+'" onclick="CaseDetailApp._downloadByData(this)">下载</button><button onclick="CaseDetailApp._deleteDoc(\''+escapeHtml(doc.id)+'\')">删除</button></div></div>';
        });
      }
      html += '</div>'; container.innerHTML = html; container.dataset.loaded = 'true';
    } catch(e) { container.innerHTML = '<div class="cases-empty-state"><div class="empty-title">加载失败: '+escapeHtml(e.message)+'</div></div>'; }
  },

  _showUploadModal() {
    var self = this;
    var overlay = document.createElement('div'); overlay.className = 'modal-overlay';
    var catOptions = DOC_CATEGORIES.map(function(c){return '<option value="'+c.value+'">'+c.label+'</option>';}).join('');
    overlay.innerHTML = '<div class="modal" style="max-width:480px;"><h3>上传案件文件</h3>'
      + '<div class="form-group"><label>文件类别</label><select id="docCategory" class="input">'+catOptions+'</select></div>'
      + '<div class="form-group"><label>选择文件</label><input type="file" id="docFile" class="input" accept=".pdf,.doc,.docx,.txt" style="padding:var(--space-2) 0;"></div>'
      + '<p style="font-size:var(--text-xs);color:var(--color-gray-500);">支持 PDF、Word、TXT 格式，最大10MB</p>'
      + '<div class="modal-actions"><button class="btn btn-outline cancelUp">取消</button><button class="btn btn-primary confirmUp">上传并AI分析</button></div></div>';
    document.body.appendChild(overlay);
    var close = function() { overlay.remove(); };
    overlay.querySelector('.cancelUp').addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if(e.target===overlay)close(); });
    overlay.querySelector('.confirmUp').addEventListener('click', async function() {
      var file = document.getElementById('docFile')?.files?.[0];
      if (!file) { Toast.warning('请选择文件'); return; }
      if (file.size > 10*1024*1024) { Toast.warning('文件大小不能超过10MB'); return; }
      var category = document.getElementById('docCategory')?.value||'other';
      try {
        Toast.info('正在上传...');
        var formData = new FormData(); formData.append('file', file); formData.append('doc_category', category);
        var headers = {}; var token = Auth.getToken(); if(token)headers['Authorization']='Bearer '+token;
        var resp = await fetch(API_BASE+'/cases/'+self.caseId+'/upload', {method:'POST',headers:headers,body:formData});
        if (!resp.ok) { var err=await resp.json().catch(function(){return{message:'HTTP '+resp.status};}); throw new Error(err.message||'上传失败'); }
        var result = await resp.json();
        Toast.success('上传成功，启动AI分析...');
        close();
        // 刷新文档列表和案件数据
        var cDocs = document.getElementById('tab-documents'); if(cDocs)cDocs.dataset.loaded='false';
        self.loadDocuments();
        await Api.post('cases/'+self.caseId+'/analysis', {});
        Toast.success('AI分析完成');
        await self._loadCaseData();
        var cAna = document.getElementById('tab-analysis'); if(cAna)cAna.dataset.loaded='false';
        self.switchTab('analysis');
      } catch(e) { Toast.error('操作失败: '+e.message); }
    });
  },

  _downloadDoc(url) { if(url)window.open(url,'_blank'); },
  _downloadByData(el) { var url = el?.getAttribute('data-doc-url'); if(url)window.open(url,'_blank'); },

  async _deleteDoc(docId) {
    var self = this;
    showModal({title:'删除文档',message:'确定删除该文档吗？',confirmText:'删除',danger:true,onConfirm:async function(){
      try { await Api.delete('cases/'+self.caseId+'/documents/'+docId); Toast.success('已删除'); var c=document.getElementById('tab-documents'); if(c)c.dataset.loaded='false'; self.loadDocuments(); } catch(e) { Toast.error('删除失败: '+e.message); }
    }});
  },
};
