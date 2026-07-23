/**
 * 工具函数汇总
 */

// 导入日期工具
const date = require('./date.js');
// 导入存储工具
const storage = require('./storage.js');

/**
 * 显示加载提示
 * @param {string} title - 提示文字
 * @param {boolean} mask - 是否显示透明蒙层
 */
function showLoading(title = '加载中...', mask = true) {
  if (wx.showLoading) {
    wx.showLoading({ title, mask });
  } else {
    wx.showToast({ title, icon: 'loading', duration: 30000, mask });
  }
}

/**
 * 隐藏加载提示
 */
function hideLoading() {
  if (wx.hideLoading) {
    wx.hideLoading();
  }
  wx.hideToast();
}

/**
 * 显示成功提示
 * @param {string} title - 提示文字
 */
function showSuccess(title = '成功') {
  wx.showToast({ title, icon: 'success', duration: 2000 });
}

/**
 * 显示失败提示
 * @param {string} title - 提示文字
 */
function showError(title = '操作失败') {
  wx.showToast({ title, icon: 'none', duration: 2000 });
}

/**
 * 显示确认对话框
 * @param {object} options - 配置项
 * @returns {Promise}
 */
function showConfirm(options) {
  return new Promise((resolve, reject) => {
    wx.showModal({
      title: options.title || '提示',
      content: options.content || '',
      confirmText: options.confirmText || '确定',
      cancelText: options.cancelText || '取消',
      success: (res) => {
        if (res.confirm) {
          resolve(true);
        } else {
          resolve(false);
        }
      },
      fail: () => reject(false)
    });
  });
}

/**
 * 节流函数
 * @param {function} fn - 要节流的函数
 * @param {number} delay - 延迟时间（毫秒）
 */
function throttle(fn, delay = 300) {
  let lastTime = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastTime >= delay) {
      lastTime = now;
      fn.apply(this, args);
    }
  };
}

/**
 * 防抖函数
 * @param {function} fn - 要防抖的函数
 * @param {number} delay - 延迟时间（毫秒）
 */
function debounce(fn, delay = 300) {
  let timer = null;
  return function(...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * 深拷贝
 * @param {any} obj - 要拷贝的对象
 */
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item));
  }
  const cloned = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
}

/**
 * 生成唯一 ID
 */
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
}

/**
 * 获取当前页面路径
 */
function getCurrentPage() {
  const pages = getCurrentPages();
  return pages[pages.length - 1];
}

/**
 * 复制到剪贴板
 * @param {string} text - 要复制的文本
 */
function copyToClipboard(text) {
  return new Promise((resolve, reject) => {
    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success', duration: 1500 });
        resolve(true);
      },
      fail: reject
    });
  });
}

/**
 * 获取系统信息
 */
function getSystemInfo() {
  try {
    return wx.getSystemInfoSync();
  } catch {
    return {};
  }
}

/**
 * 检查是否是 iPhone X 或更高版本（刘海屏）
 */
function isIphoneX() {
  const info = getSystemInfo();
  return info.model && info.model.indexOf('iPhone X') !== -1;
}

/**
 * 获取安全区域
 */
function getSafeArea() {
  const info = getSystemInfo();
  return info.safeArea || { top: 0, bottom: info.windowHeight };
}

module.exports = {
  ...date,
  ...storage,
  showLoading,
  hideLoading,
  showSuccess,
  showError,
  showConfirm,
  throttle,
  debounce,
  deepClone,
  generateId,
  getCurrentPage,
  copyToClipboard,
  getSystemInfo,
  isIphoneX,
  getSafeArea
};
