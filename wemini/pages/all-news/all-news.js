/**
 * 全部新闻列表页（v2 - 按源Tab分类展示）
 */

const newsService = require('../../services/news.js');
const { formatDateTime } = require('../../utils/date.js');

Page({
  data: {
    sources: [],           // 启用的新闻源列表（作为 Tab）
    activeSourceId: null,  // 当前选中的 source_id
    list: [],
    page: 1,
    pageSize: 20,
    total: 0,
    loading: true,
    loadingMore: false,
    hasMore: true,
  },

  onLoad() {
    this.loadSourcesAndNews();
  },

  // 加载新闻源列表 + 默认选中第一个
  async loadSourcesAndNews() {
    this.setData({ loading: true });
    try {
      const res = await newsService.getSources();
      const data = res?.data || res;
      if (data) {
        // 合并预设源和自定义源，只保留启用的
        const allSources = [
          ...(data.preset_sources || []),
          ...(data.custom_sources || []),
        ];
        const enabledSources = allSources.filter(s => s.is_enabled);
        this.setData({ sources: enabledSources });

        if (enabledSources.length > 0) {
          const firstId = enabledSources[0].id;
          this.setData({ activeSourceId: firstId, page: 1, list: [], hasMore: true });
          await this.loadNews(firstId);
        } else {
          this.setData({ loading: false });
        }
      } else {
        this.setData({ loading: false });
      }
    } catch (err) {
      console.error('loadSources failed:', err);
      this.setData({ loading: false });
    }
  },

  // 按 source_id 加载新闻
  async loadNews(sourceId, append = false) {
    const page = append ? this.data.page : 1;
    const list = append ? this.data.list : [];
    this.setData({ loading: !append, loadingMore: append });

    try {
      const res = await newsService.getRawNews(page, this.data.pageSize, sourceId);
      const data = res?.data || res;

      if (data) {
        const items = data.items || [];
        const total = data.total || 0;

        items.forEach(item => {
          item.formattedTime = formatDateTime(item.published_at || item.publish_time);
        });

        this.setData({
          list: append ? [...list, ...items] : items,
          total,
          loading: false,
          loadingMore: false,
          hasMore: (append ? list.length + items.length : items.length) < total,
        });
      } else {
        this.setData({ loading: false, loadingMore: false });
      }
    } catch (err) {
      console.error('loadNews failed:', err);
      this.setData({ loading: false, loadingMore: false });
    }
  },

  // 切换 Tab
  onTabChange(e) {
    const sourceId = parseInt(e.currentTarget.dataset.id, 10);
    if (sourceId === this.data.activeSourceId) return;

    this.setData({
      activeSourceId: sourceId,
      page: 1,
      list: [],
      hasMore: true,
    });
    this.loadNews(sourceId);
  },

  // 加载更多
  async onLoadMore() {
    if (this.data.loadingMore || !this.data.hasMore || !this.data.activeSourceId) return;

    this.setData({ page: this.data.page + 1 });
    await this.loadNews(this.data.activeSourceId, true);
  },

  // 刷新
  onRefresh() {
    this.setData({ page: 1, list: [], hasMore: true });
    if (this.data.activeSourceId) {
      this.loadNews(this.data.activeSourceId);
    }
  },

  // 返回
  onBack() {
    wx.navigateBack();
  },

  // 图片加载失败
  onItemImageError(e) {
    const { id } = e.currentTarget.dataset;
    const list = this.data.list.map(item => {
      if (item.id === id) {
        return { ...item, _imgError: true };
      }
      return item;
    });
    this.setData({ list });
  },

  // 点击新闻项
  onItemTap(e) {
    const { item } = e.currentTarget.dataset;
    if (item && item.id) {
      wx.navigateTo({
        url: `/pages/detail/detail?id=${item.id}`
      });
    }
  },
});
