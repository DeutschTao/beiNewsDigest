/**
 * 进度指示器组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 当前索引
    current: {
      type: Number,
      value: 0,
      observer: '_updateActiveWidth'
    },
    // 总数
    total: {
      type: Number,
      value: 0
    }
  },

  data: {
    activeWidth: '48rpx'
  },

  lifetimes: {
    attached() {
      this._updateActiveWidth();
    }
  },

  methods: {
    _updateActiveWidth() {
      // 根据当前索引更新活动状态的宽度
      this.setData({
        activeWidth: '48rpx'
      });
    }
  }
});
