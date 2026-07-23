/**
 * 文本 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 要点列表
    points: {
      type: Array,
      value: []
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 0
    }
  }
});
