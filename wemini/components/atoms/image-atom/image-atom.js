/**
 * 图片 Atom 组件
 */

Component({
  options: {
    addGlobalClass: true
  },

  properties: {
    // 图片列表
    images: {
      type: Array,
      value: []
    },
    // 动画延迟
    delay: {
      type: Number,
      value: 300
    }
  },

  data: {
    imageErrors: []
  },

  observers: {
    images(newVal) {
      if (newVal) {
        this.setData({ imageErrors: new Array(newVal.length).fill(false) });
      }
    }
  },

  methods: {
    onPreviewImage(e) {
      const { index } = e.currentTarget.dataset;
      wx.previewImage({
        urls: this.data.images,
        current: this.data.images[index]
      });
    },

    onImageError(e) {
      const { index } = e.currentTarget.dataset;
      const imageErrors = [...this.data.imageErrors];
      imageErrors[index] = true;
      this.setData({ imageErrors });
    }
  }
});
