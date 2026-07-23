/**
 * 时间线 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 事件列表
    events: {
      type: Array,
      value: []
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 600
    }
  }
});
