/**
 * FAB 悬浮菜单组件
 */

Component({
  options: {
    multipleSlots: true,
    addGlobalClass: true
  },

  properties: {
    // 菜单项配置
    actions: {
      type: Array,
      value: [
        { id: 'refresh', text: '刷新', icon: '🔄' },
        { id: 'allNews', text: '全部新闻', icon: '📋' },
        { id: 'settings', text: '设置', icon: '⚙️' }
      ]
    },
    // 是否禁用
    disabled: {
      type: Boolean,
      value: false
    }
  },

  data: {
    isExpanded: false,
    isTouching: false
  },

  lifetimes: {
    attached() {
      // 绑定触摸事件监听
    }
  },

  pageLifetimes: {
    show() {
      // 页面显示时检查是否需要关闭菜单
    }
  },

  methods: {
    // 切换菜单状态
    toggleMenu() {
      if (this.data.disabled) return;
      this.setData({
        isExpanded: !this.data.isExpanded
      });
    },

    // 关闭菜单
    closeMenu() {
      if (this.data.isExpanded) {
        this.setData({
          isExpanded: false
        });
      }
    },

    // 菜单项点击
    onAction(e) {
      const { action } = e.currentTarget.dataset;
      this.closeMenu();

      // 触发事件
      this.triggerEvent('action', { action });
    },

    // 触摸开始
    onTouchStart(e) {
      this.setData({
        isTouching: true
      });
    },

    // 触摸结束
    onTouchEnd(e) {
      this.setData({
        isTouching: false
      });
    },

    // 阻止触摸穿透
    preventTouch(e) {
      // 防止遮罩层触摸事件穿透
    }
  }
});
