/**
 * 基础 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 类型
    type: {
      type: String,
      value: ''
    },
    // 动画延迟（毫秒）
    delay: {
      type: Number,
      value: 0
    }
  }
});
