/**
 * 新闻服务 API（v2 - 对应 /api/v2/*）
 */
const api = require('./api.js');

const IMG_PROXY = `${api.API_BASE}/proxy/image`;

module.exports = {
  /**
   * 首页（按来源分组，每源 Top3）
   */
  getHome() {
    return api.get('/home');
  },

  /**
   * 全部新闻（分页）
   * @param {number} page - 页码
   * @param {number} pageSize - 每页数量
   * @param {number|null} sourceId - 按来源筛选
   */
  getRawNews(page = 1, pageSize = 20, sourceId = null) {
    const params = { page, page_size: pageSize };
    if (sourceId) params.source_id = sourceId;
    return api.get('/news', params);
  },

  /**
   * 新闻详情（含按需正文）
   * @param {string|number} id - 新闻 ID
   */
  getNewsDetail(id) {
    return api.get(`/news/${id}`);
  },

  /**
   * 新闻源列表
   */
  getSources() {
    return api.get('/sources');
  },

  /**
   * 添加自定义新闻源
   * @param {object} opts - { name?, source_type, url }
   */
  addSource({ name, source_type, url }) {
    const data = { source_type, url };
    if (name) data.name = name;
    return api.post('/sources/custom', data);
  },

  /**
   * 删除自定义新闻源
   * @param {number} id - 源 ID
   */
  deleteSource(id) {
    return api.delete(`/sources/${id}`);
  },

  /**
   * 切换新闻源启用状态
   * @param {number} id - 源 ID
   */
  toggleSource(id) {
    return api.patch(`/sources/${id}/toggle`);
  },

  /**
   * 检测新闻源连通性
   * @param {number} id - 源 ID
   */
  checkSource(id) {
    return api.post(`/sources/check/${id}`);
  },

  /**
   * 手动触发抓取（全源）
   */
  triggerFetch() {
    return api.post('/trigger/fetch', {});
  },

  /**
   * 手动触发抓取（单源）
   * @param {number} id - 源 ID
   */
  triggerFetchSource(id) {
    return api.post(`/trigger/fetch/source/${id}`, {});
  },

  /**
   * 获取代理图片 URL
   * @param {string} url - 原始图片 URL
   */
  getProxyImageUrl(url) {
    if (!url) return '';
    return `${IMG_PROXY}?url=${encodeURIComponent(url)}`;
  },

  IMG_PROXY,
};
