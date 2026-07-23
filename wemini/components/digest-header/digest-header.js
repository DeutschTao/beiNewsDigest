/**
 * Digest 头部组件
 */

const { safeNewDate } = require('../../utils/date.js');

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    date: {
      type: String,
      value: ''
    }
  },

  data: {
    formattedDate: ''
  },

  lifetimes: {
    attached() {
      this._updateFormattedDate();
    }
  },

  observers: {
    date() {
      this._updateFormattedDate();
    }
  },

  methods: {
    _updateFormattedDate() {
      const d = this.data.date ? safeNewDate(this.data.date) : new Date();
      if (isNaN(d.getTime())) {
        this.setData({ formattedDate: '今日' });
        return;
      }
      const year = d.getFullYear();
      const month = d.getMonth() + 1;
      const day = d.getDate();
      const weekDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()];
      this.setData({
        formattedDate: `今日 · ${year}年${month}月${day}日 ${weekDay}`
      });
    }
  }
});
