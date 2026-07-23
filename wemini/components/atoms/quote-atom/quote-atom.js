/**
 * 引述 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 引述内容
    quote: {
      type: String,
      value: ''
    },
    // 作者
    author: {
      type: String,
      value: ''
    },
    // 身份/角色
    role: {
      type: String,
      value: ''
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 200
    }
  }
});
