/**
 * 百科词条 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 词条标题
    title: {
      type: String,
      value: ''
    },
    // 词条摘要
    summary: {
      type: String,
      value: ''
    },
    // 词条链接
    url: {
      type: String,
      value: ''
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 400
    }
  },

  data: {
    expanded: false
  },

  methods: {
    onToggle() {
      this.setData({
        expanded: !this.data.expanded
      });
    },

    onOpenWiki() {
      const url = this.data.url;
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
      } else {
        // 如果没有 URL，使用 Wikipedia 搜索
        const searchUrl = `https://en.wikipedia.org/wiki/${encodeURIComponent(this.data.title)}`;
        wx.setClipboardData({
          data: searchUrl,
          success: () => {
            wx.showToast({
              title: '链接已复制，请在浏览器打开',
              icon: 'none',
              duration: 2000
            });
          }
        });
      }
    }
  }
});
