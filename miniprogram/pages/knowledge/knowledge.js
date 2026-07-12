/**
 * AI法律助手 - 法律知识库页面
 */
const knowledgeService = require('../../services/knowledge');
const config = require('../../utils/config');

Page({
  data: {
    keyword: '',
    activeCategory: '',
    categories: [],
    items: [],
    page: 1, pageSize: 10,
    hasMore: false, loading: false
  },

  onLoad() {
    this._loadCategories();
    this._loadDocs();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, items: [] });
    this._loadDocs().finally(() => wx.stopPullDownRefresh());
  },

  async _loadCategories() {
    try {
      const data = await knowledgeService.getCategories();
      let cats;
      if (Array.isArray(data)) cats = data;
      else if (data && data.categories) cats = data.categories;
      else cats = [];
      // 过滤掉"全部"，避免与 WXML 中硬编码的"全部"标签重复
      cats = cats.filter(c => {
        const name = (c.name || '').toString().trim();
        const id = (c.id || c.category_id || '').toString().trim();
        return name !== '全部' && id !== 'all' && name !== '';
      });
      this.setData({ categories: cats });
    } catch (e) { this.setData({ categories: [] }); }
  },

  async _loadDocs() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const { keyword, activeCategory, page, pageSize } = this.data;
      let result;
      if (keyword) {
        result = await knowledgeService.search(keyword, activeCategory || '', page, pageSize);
      } else {
        result = await knowledgeService.getDocuments(activeCategory || '', page, pageSize);
      }
      let items = (result.items || []).map(item => ({
        id: item.id || item.chunk_id || '',
        name: item.name || item.law_name || item.title || '未知',
        category: item.category || '',
        publish_date: item.year || item.publish_date || '',
        chunk_count: item.chunk_count || 0
      }));
      this.setData({
        items: page === 1 ? items : [...this.data.items, ...items],
        hasMore: items.length >= pageSize,
        loading: false
      });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  onCategoryTap(e) {
    this.setData({ activeCategory: e.currentTarget.dataset.cat, page: 1, items: [], keyword: '' });
    this._loadDocs();
  },

  onSearchInput(e) { this.setData({ keyword: e.detail.value }); },
  onSearch() {
    this.setData({ page: 1, items: [], activeCategory: '' });
    this._loadDocs();
  },
  onLoadMore() {
    if (!this.data.hasMore || this.data.loading) return;
    this.setData({ page: this.data.page + 1 });
    this._loadDocs();
  },
  onTapDoc(e) {
    if (e.currentTarget.dataset.id) {
      wx.navigateTo({ url: `/pages/knowledge/detail?id=${e.currentTarget.dataset.id}` });
    }
  }
});
