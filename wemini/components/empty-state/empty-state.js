/**
 * 空状态组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 类型：no-data, error, network, search
    type: {
      type: String,
      value: 'no-data'
    },
    // 标题
    title: {
      type: String,
      value: '暂无数据'
    },
    // 描述
    description: {
      type: String,
      value: '请稍后再试'
    },
    // 是否显示操作按钮
    showAction: {
      type: Boolean,
      value: false
    },
    // 操作按钮文字
    actionText: {
      type: String,
      value: '刷新'
    }
  },

  data: {
    iconMap: {
      'no-data': '📭',
      'error': '⚠️',
      'network': '📡',
      'search': '🔍',
      'empty': '📰'
    }
  },

  methods: {
    onAction() {
      this.triggerEvent('action');
    }
  }
});
