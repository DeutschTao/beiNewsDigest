/**
 * 首页逻辑（v2 - 单轮播图15条）
 */
const newsService = require('../../services/news.js');

const MAX_DIGEST = 15;

Page({
  data: {
    digest: [],
    loading: true,
    refreshing: false,
    currentIndex: 0,
    lastRefresh: '',
    readHistory: {},
  },

  onLoad() {
    this.fetchHome();
  },

  onShow() {
    // 不做静默刷新
  },

  async fetchHome() {
    this.setData({ loading: true });
    try {
      const res = await newsService.getHome();
      const data = res?.data || res;

      if (data && Array.isArray(data.groups)) {
        const allItems = [];
          data.groups.forEach(g => {
            g.items.forEach(item => {
              item.source_name = item.source_name || g.source_name;
              // 兼容 digest-card 取 publishTime 字段
              item.publishTime = item.publishTime || item.publish_time || item.published_at;
              allItems.push(item);
            });
          });

        const digest = allItems.slice(0, MAX_DIGEST);

        this.setData({
          digest,
          loading: false,
          lastRefresh: Date.now(),
        });
        console.log(this.data.lastRefresh, '---');
      } else {
        this.setData({ digest: [], loading: false });
      }
    } catch (err) {
      console.error('fetchHome failed:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none', duration: 1500 });
    }
  },

  onPullDownRefresh() {
    this.fetchHome().then(() => wx.stopPullDownRefresh());
  },

  async onRefresh() {
    if (this.data.refreshing) return;
    this.setData({ refreshing: true });
    try {
      await newsService.triggerFetch();
      setTimeout(async () => {
        await this.fetchHome();
        this.setData({ refreshing: false });
        wx.showToast({ title: '刷新成功', icon: 'success', duration: 1500 });
      }, 1500);
    } catch (err) {
      console.error('refresh failed:', err);
      this.setData({ refreshing: false });
      wx.showToast({ title: '刷新失败', icon: 'none', duration: 1500 });
    }
  },

  onSwiperChange(e) {
    this.setData({ currentIndex: e.detail.current });
  },

  onCardTap(e) {
    const news = e.detail || e.currentTarget?.dataset?.item;
    if (news && news.id) {
      wx.navigateTo({ url: `/pages/detail/detail?id=${news.id}` });
    }
  },

  onMarkRead(e) {
    const news = e.detail || e.currentTarget?.dataset?.item;
    if (news && news.id) {
      const readHistory = { ...this.data.readHistory, [news.id]: true };
      this.setData({ readHistory });
    }
  },

  onToggle() {
    // 预留 toggle 功能
  },

  onFabAction(e) {
    const { action } = e.detail;
    if (action === 'refresh') this.onRefresh();
    else if (action === 'allNews') wx.navigateTo({ url: '/pages/all-news/all-news' });
    else if (action === 'settings') wx.navigateTo({ url: '/pages/settings/settings' });
  },
});
