/**
 * 本地存储工具
 */

const PREFIX = 'bei_news_';

/**
 * 设置存储
 * @param {string} key - 键名
 * @param {any} value - 值
 */
function setStorage(key, value) {
  try {
    wx.setStorageSync(PREFIX + key, value);
    return true;
  } catch (e) {
    console.error('Storage set error:', e);
    return false;
  }
}

/**
 * 获取存储
 * @param {string} key - 键名
 * @param {any} defaultValue - 默认值
 * @returns {any}
 */
function getStorage(key, defaultValue = null) {
  try {
    const value = wx.getStorageSync(PREFIX + key);
    return value !== '' ? value : defaultValue;
  } catch (e) {
    console.error('Storage get error:', e);
    return defaultValue;
  }
}

/**
 * 移除存储
 * @param {string} key - 键名
 */
function removeStorage(key) {
  try {
    wx.removeStorageSync(PREFIX + key);
    return true;
  } catch (e) {
    console.error('Storage remove error:', e);
    return false;
  }
}

/**
 * 清除所有存储
 */
function clearStorage() {
  try {
    wx.clearStorageSync();
    return true;
  } catch (e) {
    console.error('Storage clear error:', e);
    return false;
  }
}

/**
 * 获取存储信息
 * @returns {object}
 */
function getStorageInfo() {
  try {
    return wx.getStorageInfoSync();
  } catch (e) {
    console.error('Storage info error:', e);
    return null;
  }
}

// 用户设置相关
const SETTINGS_KEY = 'settings';

function getSettings() {
  return getStorage(SETTINGS_KEY, {
    pushEnabled: true,
    morningPush: { enabled: true, time: '06:00' },
    eveningPush: { enabled: true, time: '21:00' },
  });
}

function setSettings(settings) {
  return setStorage(SETTINGS_KEY, settings);
}

function updateSettings(updates) {
  const current = getSettings();
  const updated = { ...current, ...updates };
  return setSettings(updated);
}

// 阅读历史相关
const READ_HISTORY_KEY = 'readHistory';

function getReadHistory() {
  return getStorage(READ_HISTORY_KEY, []);
}

function addToReadHistory(newsId) {
  const history = getReadHistory();
  if (!history.includes(newsId)) {
    history.unshift(newsId);
    // 最多保存 100 条
    if (history.length > 100) {
      history.pop();
    }
    setStorage(READ_HISTORY_KEY, history);
  }
  return history;
}

function isRead(newsId) {
  const history = getReadHistory();
  return history.includes(newsId);
}

// Digest 缓存
const DIGEST_CACHE_KEY = 'digest_cache';

function getCachedDigest() {
  const cache = getStorage(DIGEST_CACHE_KEY, null);
  if (!cache) return null;

  // 检查缓存是否过期（30分钟）
  const cacheTime = cache.timestamp || 0;
  const now = Date.now();
  if (now - cacheTime > 30 * 60 * 1000) {
    return null;
  }
  return cache.data;
}

function setCachedDigest(data) {
  return setStorage(DIGEST_CACHE_KEY, {
    data,
    timestamp: Date.now()
  });
}

module.exports = {
  setStorage,
  getStorage,
  removeStorage,
  clearStorage,
  getStorageInfo,
  getSettings,
  setSettings,
  updateSettings,
  getReadHistory,
  addToReadHistory,
  isRead,
  getCachedDigest,
  setCachedDigest
};
