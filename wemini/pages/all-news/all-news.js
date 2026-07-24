/**
 * 全部新闻列表页（v2 - 按源Tab分类展示，支持左右滑动切换）
 */

const newsService = require('../../services/news.js');
const { formatDateTime } = require('../../utils/date.js');

Page({
  data: {
    sources: [],
    activeIndex: 0,
    scrollLeft: 0,

    // 初始 loading（Tab 数据加载中）
    loading: true,

    // swiper 高度
    swiperHeight: 0,

    // 各 Tab 的新闻列表（数组，下标对应 Tab 位置）
    newsLists: [],
    // 各 Tab 的分页信息
    newsPages: [],
    newsTotals: [],
    // 各 Tab 的加载状态
    newsLoading: [],
    newsLoadingMore: [],
    newsHasMore: [],
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const tabBarHeight = 88;
    const bottomBarHeight = 120 + (sysInfo.safeAreaInsets?.bottom || 0);
    const swiperHeight = sysInfo.windowHeight - tabBarHeight - bottomBarHeight;
    this.setData({ swiperHeight });

    this.loadSourcesAndNews();
  },

  // 加载新闻源列表 + 默认选中第一个
  async loadSourcesAndNews() {
    this.setData({ loading: true });
    try {
      const res = await newsService.getSources();
      const data = res?.data || res;
      if (data) {
        const allSources = [
          ...(data.preset_sources || []),
          ...(data.custom_sources || []),
        ];
        const enabledSources = allSources.filter(s => s.is_enabled);
        this.setData({ sources: enabledSources });

        if (enabledSources.length > 0) {
          const n = enabledSources.length;
          this.setData({
            newsLists: Array.from({ length: n }, () => []),
            newsPages: Array.from({ length: n }, () => 1),
            newsTotals: Array.from({ length: n }, () => 0),
            newsLoading: Array.from({ length: n }, () => true),
            newsLoadingMore: Array.from({ length: n }, () => false),
            newsHasMore: Array.from({ length: n }, () => true),
            loading: false,
          });
          await this.loadNews(0, enabledSources[0].id);
        } else {
          this.setData({ loading: false });
        }
      } else {
        this.setData({ loading: false });
      }
    } catch (err) {
      console.error('[all-news] loadSources failed:', err);
      this.setData({ loading: false });
    }
  },

  // 按 Tab 索引加载新闻
  async loadNews(index, sourceId, append = false) {
    const lists = [...this.data.newsLists];
    const pages = [...this.data.newsPages];

    this._setDataAt(lists, index, append ? lists[index] : []);
    this._setLoading(index, false);
    this._setLoadingMore(index, append);

    const page = append ? pages[index] : 1;

    try {
      const res = await newsService.getRawNews(page, 20, sourceId);
      const data = res?.data || res;

      if (data) {
        const items = data.items || [];
        const total = data.total || 0;

        items.forEach(item => {
          item.formattedTime = formatDateTime(item.published_at || item.publish_time);
        });

        const newLists = [...this.data.newsLists];
        newLists[index] = append ? [...newLists[index], ...items] : items;

        const newPages = [...this.data.newsPages];
        newPages[index] = page + 1;

        this.setData({
          newsLists: newLists,
          newsPages: newPages,
          newsTotals: this._setAt([...this.data.newsTotals], index, total),
          newsLoading: this._setAt([...this.data.newsLoading], index, false),
          newsLoadingMore: this._setAt([...this.data.newsLoadingMore], index, false),
          newsHasMore: this._setAt([...this.data.newsHasMore], index, newLists[index].length < total),
        });
      } else {
        this._setLoading(index, false);
        this._setLoadingMore(index, false);
      }
    } catch (err) {
      console.error('[all-news] loadNews failed:', err);
      this._setLoading(index, false);
      this._setLoadingMore(index, false);
    }
  },

  // ---- Tab 点击切换 ----
  onTabChange(e) {
    const index = parseInt(e.currentTarget.dataset.index, 10);
    if (index === this.data.activeIndex) return;

    this.setData({ activeIndex: index });
    this._loadIfEmpty(index);
  },

  // ---- Swiper 滑动切换，同步 Tab ----
  onSwiperChange(e) {
    const index = e.detail.current;
    if (index === this.data.activeIndex) return;

    this.setData({ activeIndex: index });
    this._loadIfEmpty(index);
  },

  // 如果当前 Tab 列表为空则加载
  _loadIfEmpty(index) {
    const sourceId = this.data.sources[index]?.id;
    if (!sourceId) return;
    if (this.data.newsLists[index].length === 0) {
      this.loadNews(index, sourceId);
    }
  },

  // 加载更多
  onLoadMore() {
    const idx = this.data.activeIndex;
    const sourceId = this.data.sources[idx]?.id;
    if (!sourceId) return;
    if (this.data.newsLoadingMore[idx] || !this.data.newsHasMore[idx]) return;

    this.loadNews(idx, sourceId, true);
  },

  // 刷新
  onRefresh() {
    const idx = this.data.activeIndex;
    const sourceId = this.data.sources[idx]?.id;
    if (!sourceId) return;

    const newLists = [...this.data.newsLists];
    newLists[idx] = [];
    const newPages = [...this.data.newsPages];
    newPages[idx] = 1;
    const newHasMore = [...this.data.newsHasMore];
    newHasMore[idx] = true;

    this.setData({
      newsLists: newLists,
      newsPages: newPages,
      newsHasMore: newHasMore,
    });
    this.loadNews(idx, sourceId);
  },

  // 图片加载失败
  onItemImageError(e) {
    const { id } = e.currentTarget.dataset;
    const idx = this.data.activeIndex;
    const newLists = [...this.data.newsLists];
    newLists[idx] = newLists[idx].map(item => {
      if (item.id === id) return { ...item, _imgError: true };
      return item;
    });
    this.setData({ newsLists: newLists });
  },

  // 点击新闻项
  onItemTap(e) {
    const { item } = e.currentTarget.dataset;
    if (item && item.id) {
      wx.navigateTo({ url: `/pages/detail/detail?id=${item.id}` });
    }
  },

  // ---- 工具方法 ----
  _setDataAt(arr, index, value) {
    const newArr = [...arr];
    newArr[index] = value;
    this.setData({ [this._getArrayKey(arr)]: newArr });
  },

  _setAt(arr, index, value) {
    const newArr = [...arr];
    newArr[index] = value;
    return newArr;
  },

  _setLoading(index, val) {
    const newArr = [...this.data.newsLoading];
    newArr[index] = val;
    this.setData({ newsLoading: newArr });
  },

  _setLoadingMore(index, val) {
    const newArr = [...this.data.newsLoadingMore];
    newArr[index] = val;
    this.setData({ newsLoadingMore: newArr });
  },

  _getArrayKey(arr) {
    if (arr === this.data.newsLists) return 'newsLists';
    return '';
  },
});
