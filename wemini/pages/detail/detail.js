/**
 * 新闻详情页逻辑
 */
const newsService = require('../../services/news.js');
const { formatTime } = require('../../utils/date.js');

// 清洗 HTML，只保留正文中的 <p>, <h2>, <h3>, <ul>, <ol>, <li>, <a>, <br>, <strong>, <em>, <blockquote> 等基本标签
function cleanContentHtml(html) {
  if (!html) return '';

  // 1. 提取 <bsp-story-page> 内的正文，如果没有则用原始 HTML
  let mainContent = html;
  const storyMatch = html.match(/<bsp-story-page[^>]*>([\s\S]*?)<\/bsp-story-page>/i);
  if (storyMatch) {
    mainContent = storyMatch[1];
  }

  // 2. 移除所有不需要的大块标签及其内容
  const blockRemove = [
    'script', 'style', 'iframe', 'svg', 'picture', 'source', 'form',
    'button', 'nav', 'header', 'footer', 'aside', 'template',
    'bsp-carousel', 'bsp-list-loadmore', 'bsp-page-actions', 'bsp-header-leaderboard',
    'bsp-jw-data-store', 'bsp-jw-player', 'bsp-copy-link', 'bsp-print-link',
    'bsp-story-page', 'bsp-timestamp', 'bsp-custom-headline', 'bsp-carousel-read-more',
    'vf-conversations', 'vf-trending-articles', 'vf-conversations-count',
  ];
  let cleaned = mainContent;
  for (const tag of blockRemove) {
    const regex = new RegExp(`<${tag}[^>]*>[\\s\\S]*?<\\/${tag}>`, 'gi');
    cleaned = cleaned.replace(regex, '');
    // 自闭合标签
    const selfClose = new RegExp(`<${tag}[^>]*\\/>`, 'gi');
    cleaned = cleaned.replace(selfClose, '');
  }

  // 3. 移除剩余的无效标签（只保留白名单）
  const allowedTags = ['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a', 'br', 'strong', 'em', 'b', 'i', 'u', 'blockquote', 'span', 'div', 'img', 'hr'];
  const tagPattern = new RegExp(`<\\/?(?!\\/?(?:${allowedTags.join('|')})(?:\\s[^>]*)?>)[a-zA-Z][^>]*>`, 'gi');
  cleaned = cleaned.replace(tagPattern, '');

  // 4. 移除 data-* 属性和 class, id, style 属性
  cleaned = cleaned.replace(/\s(data-[\w-]+|class|id|style)="[^"]*"/gi, '');

  // 5. 清理多余的空白行
  cleaned = cleaned.replace(/\n\s*\n/g, '\n');

  return cleaned.trim();
}

Page({
  data: {
    newsId: '',
    detail: null,
    formattedTime: '',
    loading: true,
    error: '',
    coverError: false,
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ newsId: options.id });
      this.loadNewsDetail();
    } else {
      this.setData({ loading: false, error: '缺少新闻 ID' });
    }
  },

  async loadNewsDetail() {
    this.setData({ loading: true, error: '', coverError: false });
    try {
      const res = await newsService.getNewsDetail(this.data.newsId);
      const d = res?.data || res;

      if (!d) {
        throw new Error('未找到新闻');
      }

      const cover = d.cover_image || d.coverImage || '';
      this.setData({
        loading: false,
        detail: {
          id: d.id,
          title: d.title,
          source: d.source_name || d.source,
          sourceCode: d.source_code,
          coverImage: cover,
          publishedAt: d.published_at,
          url: d.url || d.content_url || '',
          summary: d.summary || '',
          hasFullContent: !!d.has_full_content,
          contentHtml: cleanContentHtml(d.content_html || ''),
          contentSource: d.content_source || 'homepage',
          fetchedAt: d.fetched_at || null,
        },
        formattedTime: formatTime(d.published_at || d.publish_time),
        coverError: !cover,
      });
    } catch (err) {
      console.error('加载新闻详情失败:', err);
      this.setData({ loading: false, error: '加载失败，请重试' });
    }
  },

  onPreviewCover() {
    const img = this.data.detail?.coverImage;
    if (img && !this.data.coverError) {
      wx.previewImage({ urls: [img], current: img });
    }
  },

  onCoverError() {
    this.setData({ coverError: true });
  },

  onOpenOriginal() {
    const url = this.data.detail?.url;
    if (!url) {
      wx.showToast({ title: '原文链接不可用', icon: 'none', duration: 1500 });
      return;
    }
    // 优先尝试直接打开（企业微信 / PC 微信 / 工具唤起场景可用）
    if (wx.canIUse('openUrl')) {
      wx.openUrl({
        url,
        fail: () => {
          // fallback：复制链接
          wx.setClipboardData({
            data: url,
            success: () => {
              wx.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none', duration: 2000 });
            },
          });
        },
      });
    } else {
      wx.setClipboardData({
        data: url,
        success: () => {
          wx.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none', duration: 2000 });
        },
      });
    }
  },
});
