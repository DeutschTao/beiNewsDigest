/**
 * Digest 卡片组件
 */

const { formatTime, formatDateTime } = require('../../utils/date.js');

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 新闻数据
    news: {
      type: Object,
      value: {}
    }
  },

  data: {
    formattedTime: '',
    imageError: false
  },

  lifetimes: {
    attached() {
      this._updateFormattedTime();
      // 初始化时判断图片是否为空
      const cover = this.data.news?.coverImage || this.data.news?.cover_image;
      if (!cover) {
        this.setData({ imageError: true });
      }
    }
  },

  observers: {
    'news.id,news.coverImage,news.cover_image'() {
      this._updateFormattedTime();
      // 图片为空时直接显示占位图
      const cover = this.data.news?.coverImage || this.data.news?.cover_image;
      this.setData({ imageError: !cover });
    }
  },

  methods: {
    _updateFormattedTime() {
      const news = this.data.news;
      if (!news) {
        this.setData({ formattedTime: '' });
        return;
      }

      const publishTime = news.publishTime || news.publish_time;
      if (publishTime) {
        this.setData({
          formattedTime: formatDateTime(publishTime)
        });
      } else {
        this.setData({ formattedTime: '' });
      }
    },

    onCardTap() {
      this.triggerEvent('tap', this.data.news);
    },

    onImageError() {
      this.setData({ imageError: true });
    }
  }
});
