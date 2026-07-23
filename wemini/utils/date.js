/**
 * 日期格式化工具
 */

/**
 * 安全创建 Date 对象（兼容 iOS）
 * @param {Date|string|number} date - 日期
 * @returns {Date}
 */
function safeNewDate(date) {
  if (!date) return new Date();
  // 如果是数字时间戳，直接使用
  if (typeof date === 'number') {
    return new Date(date);
  }
  // 如果是字符串，尝试转换
  if (typeof date === 'string') {
    // 替换短横线为斜杠（iOS 兼容）
    const normalized = date.replace(/-/g, '/');
    const d = new Date(normalized);
    // 如果转换失败，尝试直接使用原字符串
    if (isNaN(d.getTime())) {
      return new Date(date);
    }
    return d;
  }
  return new Date(date);
}

/**
 * 格式化日期
 * @param {Date|string|number} date - 日期
 * @param {string} format - 格式类型：'full', 'short', 'monthDay'
 * @returns {string}
 */
function formatDate(date, format = 'full') {
  if (!date) return '';
  const d = safeNewDate(date);
  if (isNaN(d.getTime())) return '';

  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const weekDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()];

  switch (format) {
    case 'short':
      return `${month}月${day}日 ${weekDay}`;
    case 'monthDay':
      return `今日 · ${year}年${month}月${day}日`;
    case 'full':
    default:
      return `${year}年${month}月${day}日 ${weekDay}`;
  }
}

/**
 * 格式化时间（相对时间）
 * @param {Date|string|number} date - 日期
 * @returns {string}
 */
function formatTime(date) {
  if (!date) return '';
  const d = safeNewDate(date);
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);

  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;

  return formatDate(date, 'short');
}

/**
 * 格式化相对时间
 * @param {Date|string|number} date - 日期
 * @returns {string}
 */
function formatRelativeTime(date) {
  if (!date) return '';
  const d = safeNewDate(date);
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);

  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;

  return d.toLocaleDateString('zh-CN');
}

/**
 * 格式化时间为 HH:mm
 * @param {Date|string|number} date - 日期
 * @returns {string}
 */
function formatTimeOnly(date) {
  if (!date) return '';
  const d = safeNewDate(date);
  if (isNaN(d.getTime())) return '';
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
}

/**
 * 格式化日期为 MM-DD HH:mm
 * @param {Date|string|number} date - 日期
 * @returns {string}
 */
function formatDateTime(date) {
  if (!date) return '';
  const d = safeNewDate(date);
  if (isNaN(d.getTime())) return '';
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hour = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${month}-${day} ${hour}:${min}`;
}

/**
 * 判断是否是同一天
 * @param {Date} date1
 * @param {Date} date2
 * @returns {boolean}
 */
function isSameDay(date1, date2) {
  if (!date1 || !date2) return false;
  const d1 = safeNewDate(date1);
  const d2 = safeNewDate(date2);
  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return false;
  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
}

module.exports = {
  safeNewDate,
  formatDate,
  formatTime,
  formatRelativeTime,
  formatTimeOnly,
  formatDateTime,
  isSameDay
};
