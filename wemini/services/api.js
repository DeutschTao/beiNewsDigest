/**
 * API 请求封装
 */

const app = getApp();

// API 基础地址（v2）
const API_BASE = 'http://localhost:8001/api/v2';
// const API_BASE = 'https://static.youngtao.wang/api/v2';

/**
 * 请求封装
 * @param {object} options - 请求配置
 */
function request(options) {
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
      ...options.header
    };

    // 添加 token（如果需要）
    const token = wx.getStorageSync('token');
    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }

    wx.request({
      url: API_BASE + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header,
      timeout: options.timeout || 30000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          // 如果返回的是 {code, data, message} 格式
          if (res.data && res.data.code !== undefined) {
            if (res.data.code === 0 || res.data.code === 200) {
              resolve(res.data);
            } else {
              // 处理业务错误
              wx.showToast({
                title: res.data.message || '请求失败',
                icon: 'none',
                duration: 2000
              });
              reject(res.data);
            }
          } else {
            resolve(res.data);
          }
        } else if (res.statusCode === 401) {
          // 未授权，跳转登录
          wx.showToast({
            title: '请先登录',
            icon: 'none',
            duration: 2000
          });
          reject({ code: 401, message: '未授权' });
        } else if (res.statusCode === 500) {
          wx.showToast({
            title: '服务器错误',
            icon: 'none',
            duration: 2000
          });
          reject({ code: 500, message: '服务器错误' });
        } else {
          reject(res.data || { code: res.statusCode, message: '请求失败' });
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '网络请求失败',
          icon: 'none',
          duration: 2000
        });
        reject({ code: -1, message: '网络请求失败', error: err });
      }
    });
  });
}

/**
 * GET 请求
 */
function get(url, data = {}, options = {}) {
  return request({
    url,
    method: 'GET',
    data,
    ...options
  });
}

/**
 * POST 请求
 */
function post(url, data = {}, options = {}) {
  return request({
    url,
    method: 'POST',
    data,
    ...options
  });
}

/**
 * PUT 请求
 */
function put(url, data = {}, options = {}) {
  return request({
    url,
    method: 'PUT',
    data,
    ...options
  });
}

/**
 * DELETE 请求
 */
function del(url, data = {}, options = {}) {
  return request({
    url,
    method: 'DELETE',
    data,
    ...options
  });
}

/**
 * PATCH 请求
 */
function patch(url, data = {}, options = {}) {
  return request({
    url,
    method: 'PATCH',
    data,
    ...options
  });
}

module.exports = {
  request,
  get,
  post,
  put,
  del,
  patch,
  API_BASE
};
