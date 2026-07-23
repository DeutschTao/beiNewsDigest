/**
 * 地图 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 地点名称
    location: {
      type: String,
      value: ''
    },
    // 描述
    description: {
      type: String,
      value: ''
    },
    // 纬度
    latitude: {
      type: String,
      value: ''
    },
    // 经度
    longitude: {
      type: String,
      value: ''
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 500
    }
  },

  methods: {
    onOpenLocation() {
      const { latitude, longitude, location } = this.data;

      if (latitude && longitude) {
        wx.openLocation({
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
          name: location,
          address: this.data.description || ''
        });
      } else {
        // 如果没有坐标，复制地点名称到剪贴板
        wx.setClipboardData({
          data: location,
          success: () => {
            wx.showToast({
              title: '地点已复制',
              icon: 'success',
              duration: 1500
            });
          }
        });
      }
    }
  }
});
