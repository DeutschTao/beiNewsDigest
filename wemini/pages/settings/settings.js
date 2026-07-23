/**
 * 设置中心页逻辑
 */

const newsService = require('../../services/news.js');
const { getSettings, setSettings, updateSettings, clearStorage } = require('../../utils/storage.js');

// 生成小时数组
const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
// 生成分钟数组
const minutes = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

Page({
  data: {
    // 推送总开关
    pushEnabled: true,
    // 早报开关
    morningEnabled: true,
    // 晚报开关
    eveningEnabled: true,
    // 早报时间
    morningTime: '06:00',
    // 晚报时间
    eveningTime: '21:00',
    // 新闻源计数
    enabledCount: 0,
    totalCount: 0,
    // 是否显示时间选择器
    showTimePicker: false,
    // 时间选择器类型
    timePickerType: 'morning',
    // 时间选择器的值 [hourIndex, minuteIndex]
    pickerValue: [6, 0],
    // 小时选项
    hours: hours,
    // 分钟选项
    minutes: minutes
  },

  onLoad() {
    this.loadSettings();
    this.loadSourceCounts();
  },

  // 加载设置
  loadSettings() {
    const settings = getSettings();

    this.setData({
      pushEnabled: settings.pushEnabled,
      morningEnabled: settings.morningPush?.enabled,
      eveningEnabled: settings.eveningPush?.enabled,
      morningTime: settings.morningPush?.time || '06:00',
      eveningTime: settings.eveningPush?.time || '21:00',
    });
  },

  // 加载新闻源计数
  async loadSourceCounts() {
    try {
      const res = await newsService.getSources();
      const data = res?.data || res;

      if (data) {
        const all = [...(data.preset_sources || []), ...(data.custom_sources || [])];
        const enabled = all.filter(s => s.is_enabled).length;

        this.setData({
          enabledCount: enabled,
          totalCount: all.length
        });
      }
    } catch (err) {
      console.error('加载新闻源计数失败:', err);
    }
  },

  // 切换推送总开关
  onTogglePush() {
    const newValue = !this.data.pushEnabled;
    this.setData({ pushEnabled: newValue });
    updateSettings({ pushEnabled: newValue });

    wx.showToast({
      title: newValue ? '推送已开启' : '推送已关闭',
      icon: 'success',
      duration: 1500
    });
  },

  // 切换早报开关
  onToggleMorning() {
    const newValue = !this.data.morningEnabled;
    this.setData({ morningEnabled: newValue });
    updateSettings({
      morningPush: {
        enabled: newValue,
        time: this.data.morningTime
      }
    });

    wx.showToast({
      title: newValue ? '早报已开启' : '早报已关闭',
      icon: 'success',
      duration: 1500
    });
  },

  // 切换晚报开关
  onToggleEvening() {
    const newValue = !this.data.eveningEnabled;
    this.setData({ eveningEnabled: newValue });
    updateSettings({
      eveningPush: {
        enabled: newValue,
        time: this.data.eveningTime
      }
    });

    wx.showToast({
      title: newValue ? '晚报已开启' : '晚报已关闭',
      icon: 'success',
      duration: 1500
    });
  },

  // 首页推荐新闻数量
  onSelectNewsCount() {
    const options = [
      { name: '4 条', value: 4 },
      { name: '6 条', value: 6 },
      { name: '8 条', value: 8 },
      { name: '10 条', value: 10 },
      { name: '12 条', value: 12 }
    ];

    wx.showActionSheet({
      itemList: options.map(o => o.name),
      success: (res) => {
        const selected = options[res.tapIndex];
        this.setData({ newsCount: selected.value });
        updateSettings({ newsCount: selected.value });

        wx.showToast({
          title: `已设置为 ${selected.value} 条`,
          icon: 'success',
          duration: 1500
        });
      }
    });
  },

  // 选择早报时间
  onSelectMorningTime() {
    this._showTimePicker('morning');
  },

  // 选择晚报时间
  onSelectEveningTime() {
    this._showTimePicker('evening');
  },

  // 显示时间选择器
  _showTimePicker(type) {
    const currentTime = type === 'morning' ? this.data.morningTime : this.data.eveningTime;
    const parts = currentTime.split(':');
    const hour = parseInt(parts[0], 10);
    const minute = parseInt(parts[1], 10);

    this.setData({
      showTimePicker: true,
      timePickerType: type,
      pickerValue: [hour, minute]
    });
  },

  // 时间选择器值变化
  onTimeChange(e) {
    const value = e.detail.value;
    const hour = value[0];
    const minute = value[1];

    this.setData({
      pickerValue: [hour, minute]
    });
  },

  // 时间选择器确认
  onTimeConfirm() {
    const { timePickerType, pickerValue, hours, minutes } = this.data;
    const hour = hours[pickerValue[0]];
    const minute = minutes[pickerValue[1]];
    const timeStr = `${hour}:${minute}`;

    if (timePickerType === 'morning') {
      this.setData({ morningTime: timeStr });
      updateSettings({
        morningPush: {
          enabled: this.data.morningEnabled,
          time: timeStr
        }
      });
    } else {
      this.setData({ eveningTime: timeStr });
      updateSettings({
        eveningPush: {
          enabled: this.data.eveningEnabled,
          time: timeStr
        }
      });
    }

    this.setData({ showTimePicker: false });

    wx.showToast({
      title: `时间已设置为 ${timeStr}`,
      icon: 'success',
      duration: 1500
    });
  },

  // 时间选择器取消
  onTimeCancel() {
    this.setData({ showTimePicker: false });
  },

  // 阻止冒泡
  noop() {},

  // 跳转到新闻源管理
  onGoSources() {
    wx.navigateTo({
      url: '/pages/sources/sources'
    });
  },

  // 清除缓存
  onClearCache() {
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有缓存数据吗？',
      success: (res) => {
        if (res.confirm) {
          clearStorage();
          wx.showToast({
            title: '缓存已清除',
            icon: 'success',
            duration: 1500
          });
        }
      }
    });
  },

  // 重置设置
  onResetSettings() {
    wx.showModal({
      title: '确认重置',
      content: '确定要重置所有设置为默认值吗？',
      success: (res) => {
        if (res.confirm) {
          const defaultSettings = {
            pushEnabled: true,
            morningPush: { enabled: true, time: '06:00' },
            eveningPush: { enabled: true, time: '21:00' },
          };

          setSettings(defaultSettings);

          this.setData({
            pushEnabled: true,
            morningEnabled: true,
            eveningEnabled: true,
            morningTime: '06:00',
            eveningTime: '21:00',
            newsCount: 8
          });

          wx.showToast({
            title: '设置已重置',
            icon: 'success',
            duration: 1500
          });
        }
      }
    });
  },

  // 返回
  onBack() {
    wx.navigateBack();
  }
});
