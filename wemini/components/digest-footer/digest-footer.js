/**
 * Digest 底部组件
 */

const { formatRelativeTime } = require('../../utils/date.js');

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 当前索引
    currentIndex: {
      type: Number,
      value: 0
    },
    // 总数
    total: {
      type: Number,
      value: 0
    },
    // 是否显示进度
    showProgress: {
      type: Boolean,
      value: true
    },
    // 上次刷新时间
    lastRefresh: {
      type: String,
      value: ''
    }
  },

  data: {
    lastRefreshText: ''
  },

  lifetimes: {
    attached() {
      this._updateLastRefreshText();
    }
  },

  observers: {
    lastRefresh() {
      this._updateLastRefreshText();
    }
  },

  methods: {
    _updateLastRefreshText() {
      if (!this.data.lastRefresh) {
        this.setData({ lastRefreshText: '' });
        return;
      }
      console.log('_updateLastRefreshText', this.data.lastRefresh)
      const text = formatRelativeTime(this.data.lastRefresh);
      this.setData({ lastRefreshText: text });
    }
  }
});
