/**
 * 新闻详情页逻辑
 */

const newsService = require('../../services/news.js');
const { addToReadHistory } = require('../../utils/storage.js');
const { formatTime } = require('../../utils/date.js');

Page({
  data: {
    // 新闻 ID
    newsId: '',
    // 新闻详情
    detail: null,
    // 格式化时间
    formattedTime: '',
    // 加载状态
    loading: true,
    // 处理中状态
    processing: false,
    // 错误信息
    error: '',
    // 封面图加载失败
    coverError: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ newsId: options.id });
      this.loadNewsDetail();
    } else {
      this.setData({
        loading: false,
        error: '缺少新闻 ID'
      });
    }
  },

  // 加载新闻详情
  async loadNewsDetail() {
    this.setData({ loading: true, error: '', coverError: false });

    try {
      const res = await newsService.getNewsDetail(this.data.newsId);
      const detail = res?.data || res;

      if (!detail) {
        throw new Error('未找到新闻');
      }

      // 图片为空时直接显示占位图
      const cover = detail.coverImage || detail.cover_image;
      if (!cover) {
        this.setData({ coverError: true });
      }

      // 检查是否需要 AI 处理
      if (detail.is_processed === false) {
        this.setData({
          loading: false,
          processing: true,
          detail: this._adaptDetail(detail)
        });
        // 触发 AI 处理
        await this.processNews();
      } else {
        this.setData({
          loading: false,
          detail: this._adaptDetail(detail),
          formattedTime: formatTime(detail.publish_time || detail.publishTime)
        });
        // 添加到阅读历史
        addToReadHistory(this.data.newsId);
      }
    } catch (err) {
      console.error('加载新闻详情失败:', err);
      this.setData({
        loading: false,
        error: '加载失败，请重试'
      });
    }
  },

  // 触发 AI 处理
  async processNews() {
    try {
      const res = await newsService.processNews(this.data.newsId);
      const processed = res?.data || res;

      if (processed) {
        const cover = processed.coverImage || processed.cover_image;
        this.setData({
          processing: false,
          detail: this._adaptDetail(processed),
          formattedTime: formatTime(processed.publish_time || processed.publishTime),
          coverError: !cover
        });
        // 添加到阅读历史
        addToReadHistory(this.data.newsId);
      }
    } catch (err) {
      console.error('AI 处理失败:', err);
      this.setData({
        processing: false,
        error: 'AI 处理失败，请重试'
      });
    }
  },

  // 适配详情数据
  _adaptDetail(d) {
    if (!d) return null;
    return {
      id: d.id,
      title: d.title,
      source: d.source_name || d.source,
      sourceLogo: d.source_logo || '',
      coverImage: d.cover_image || d.coverImage || '',
      publishTime: d.publish_time || d.publishTime || '',
      contentUrl: d.content_url || d.contentUrl || '',
      atoms: (d.atoms || []).map((a) => ({
        type: a.atom_type || a.type,
        order: a.atom_order || a.order,
        ...(a.content && typeof a.content === 'object' ? a.content : {}),
        // 兼容不同字段名
        ...(a.points ? { points: a.points } : {}),
        ...(a.images ? { images: a.images } : {}),
        ...(a.quote ? { quote: a.quote } : {}),
        ...(a.author ? { author: a.author } : {}),
        ...(a.role ? { role: a.role } : {}),
        ...(a.location ? { location: a.location } : {}),
        ...(a.latitude ? { latitude: a.latitude } : {}),
        ...(a.longitude ? { longitude: a.longitude } : {}),
        ...(a.description ? { description: a.description } : {}),
        ...(a.title ? { title: a.title } : {}),
        ...(a.summary ? { summary: a.summary } : {}),
        ...(a.url ? { url: a.url } : {}),
        ...(a.events ? { events: a.events } : {})
      }))
    };
  },

  // 返回
  onBack() {
    wx.navigateBack();
  },

  // 分享
  onShare() {
    const detail = this.data.detail;
    if (!detail) return;

    const url = detail.contentUrl || detail.content_url;
    if (url) {
      wx.setClipboardData({
        data: url,
        success: () => {
          wx.showToast({
            title: '链接已复制',
            icon: 'success',
            duration: 1500
          });
        }
      });
    }
  },

  // 预览封面图
  onPreviewCover() {
    const coverImage = this.data.detail?.coverImage;
    if (coverImage && !this.data.coverError) {
      wx.previewImage({
        urls: [coverImage],
        current: coverImage
      });
    }
  },

  // 封面图加载失败
  onCoverError() {
    this.setData({ coverError: true });
  },

  // 打开原文
  onOpenOriginal() {
    const url = this.data.detail?.contentUrl || this.data.detail?.content_url;
    if (url) {
      wx.setClipboardData({
        data: url,
        success: () => {
          wx.showToast({
            title: '链接已复制，请在浏览器打开',
            icon: 'none',
            duration: 2000
          });
        }
      });
    } else {
      wx.showToast({
        title: '原文链接不可用',
        icon: 'none',
        duration: 1500
      });
    }
  }
});
