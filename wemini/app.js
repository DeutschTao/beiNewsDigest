App({
  onLaunch() {
    // 初始化存储
    this.initStorage();
  },

  initStorage() {
    // 检查是否首次启动
    const isFirstLaunch = wx.getStorageSync('isFirstLaunch');
    if (isFirstLaunch === '') {
      // 首次启动，初始化默认设置
      wx.setStorageSync('isFirstLaunch', 'false');
      wx.setStorageSync('settings', {
        pushEnabled: true,
        morningPush: { enabled: true, time: '06:00' },
        eveningPush: { enabled: true, time: '21:00' },
        newsCount: 8
      });
      wx.setStorageSync('readHistory', []);
    }
  },

  globalData: {
    // API 基础地址，开发环境使用 localhost，生产环境需要配置
    API_BASE: 'http://localhost:8001/api/v2',
    // 当前 Digest 数据
    currentDigest: null,
    // 用户设置
    settings: null
  }
});
