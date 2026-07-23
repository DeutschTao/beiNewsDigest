# Bei News Digest 微信小程序

复刻 Yahoo News Digest 的每日新闻摘要聚合工具，微信小程序版本。

## 功能特性

- **Digest 首页**：全屏滑动卡片展示新闻，毛玻璃头部，进度指示器
- **新闻详情**：Atoms 组件展示（文本摘要、引述、百科词条、图片集、地图、时间线）
- **全部新闻**：分页加载列表
- **新闻源管理**：预设源 + 自定义 RSS 源，支持连通性检测
- **设置中心**：推送开关、早晚报时间、内容设置

## 技术栈

- 微信小程序原生开发
- vant-weapp UI 组件库
- 自定义组件（FAB 菜单、进度指示器、Atoms 组件等）

## 项目结构

```
wemini/
├── app.js                 # 应用入口
├── app.json              # 全局配置
├── app.wxss              # 全局样式
├── project.config.json   # 项目配置
│
├── pages/                # 页面
│   ├── home/            # Digest 首页
│   ├── detail/          # 新闻详情
│   ├── all-news/        # 全部新闻
│   ├── sources/         # 新闻源管理
│   └── settings/        # 设置中心
│
├── components/          # 组件
│   ├── fab-menu/        # FAB 悬浮菜单
│   ├── progress-indicator/
│   ├── digest-header/
│   ├── digest-card/
│   ├── digest-footer/
│   ├── empty-state/
│   ├── skeleton-card/
│   └── atoms/           # Atoms 组件集
│       ├── text-atom/
│       ├── quote-atom/
│       ├── wiki-atom/
│       ├── image-atom/
│       ├── map-atom/
│       └── timeline-atom/
│
├── services/            # API 服务层
├── utils/              # 工具函数
└── styles/             # 公共样式
```

## 使用说明

### 1. 安装依赖

本项目为微信小程序原生项目，无需额外安装依赖。

### 2. 导入项目

1. 下载代码到本地
2. 打开微信开发者工具
3. 选择「导入项目」
4. 选择 `wemini` 文件夹
5. AppID 填写：`wxfdcf02523d46cc9b`

### 3. 配置后端地址

在 `services/api.js` 中配置后端 API 地址：

```javascript
const API_BASE = 'http://localhost:8000/api'; // 开发环境
// 生产环境需要配置为公网地址
```

### 4. 启用下拉刷新

确保在微信开发者工具中开启了「允许下拉刷新」。

## 与 H5 版本的差异

| 功能 | H5 版本 | 小程序版本 |
|------|---------|-----------|
| 右上角操作按钮 | 显示在顶部右侧 | 右下角 FAB 菜单 |
| 路由 | Vue Router | wx.navigateTo |
| 状态管理 | Pinia | Page data |
| 存储 | localStorage | wx.setStorageSync |
| 组件库 | Vant 4 | 自定义组件 |

## 设计风格

保持与 H5 版本一致的设计风格：

- **深色毛玻璃**：头部背景 `linear-gradient(135deg, #1a1a1a 0%, #333333 100%)`
- **主题色**：#333333
- **卡片设计**：全屏大图背景 + 毛玻璃标题叠加
- **进度指示**：底部弹性圆点

## API 接口

小程序调用后端 API 接口与 H5 版本相同：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/digest` | GET | 获取今日 Digest |
| `/api/news` | GET | 获取新闻列表（分页） |
| `/api/news/{id}` | GET | 获取新闻详情 |
| `/api/sources` | GET | 获取新闻源 |
| `/api/sources/custom` | POST | 添加自定义源 |
| `/api/sources/{id}/toggle` | PATCH | 切换源状态 |
| `/api/sources/check/{id}` | POST | 检测源连通性 |
| `/api/news/{id}/process` | POST | 触发 AI 处理 |
| `/api/trigger/refresh` | POST | 触发刷新 |

## 注意事项

1. 微信小程序要求 HTTPS 接口，请确保后端配置了 SSL 证书
2. 域名需要在微信公众平台后台配置白名单
3. 部分功能（如订阅消息）需要用户授权
4. 图片代理需要后端支持

## License

MIT
