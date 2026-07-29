# Bei News Digest v2 - 设计文档

本目录是 v2 重构版的设计文档，与 v1 完全分离。

---

## 文件清单

| 文件 | 内容 | 行数级别 |
|------|------|---------|
| [`后端技术方案-v2.md`](./后端技术方案-v2.md) | `version2/backend/` 的 FastAPI 后端设计 | 长文档 |
| [`小程序端技术方案-v2.md`](./小程序端技术方案-v2.md) | `wemini/` 的小程序端改造说明 | 长文档 |

---

## 快速对照（v1 vs v2 关键差异）

| 维度 | v1 | v2 |
|------|----|----|
| 抓取方式 | 9 个 RSS，其中 Reuters 404、CNN 抓不到 | 5 个稳定源：4 自研爬虫（BBC/CNN/AP/Al Jazeera）+ 1 RSS 降级（Reuters） |
| 数据模型 | 6 张表（含 AI 摘要链路） | 3 张表（news_sources / news_articles / news_contents） |
| AI 摘要 | OpenAI + Ollama 双方案，生成 text/quote/wiki atoms | **完全移除** |
| 首页 | 单一 Digest 8 条 | 按来源分组，每源 Top3 |
| 详情页 | 列表摘要 + AI 分析按钮 | 首页摘要 + 按需爬详情页（D + C 兜底） |
| 调度 | 单一 cron（每天 6:00/6:30/7:00） | 分时段调度（早高峰 30 分、日间 1 小时、晚高峰 30 分、凌晨 3 小时） |
| API 前缀 | `/api/*` | `/api/v2/*`（域名复用，路径加版本号） |
| 部署 | 阿里云 + 代理 | 复用阿里云 + 代理，监听 8001 端口（v1 仍跑 8000） |

---

## 实施路线图

### Phase 0：准备（1 天）
- [ ] 离线抓取 4 个爬虫源的首页 HTML 样本（BBC/CNN/Al Jazeera/AP）
- [ ] 在笔记本上分析 HTML 结构，确定 CSS 选择器
- [ ] 在 `tests/fixtures/` 保存样本 HTML

### Phase 1：后端骨架（2-3 天）
- [ ] 创建 `version2/backend/` 目录结构
- [ ] 写 `config.yaml`（完整配置）
- [ ] 写 `app/config.py`、`app/database.py`
- [ ] 写 `app/models/{news_source,news_article,news_content}.py`
- [ ] 写 `init_db.py`，自动 seed 5 个预设源
- [ ] `GET /api/v2/health` 跑通

### Phase 2：爬虫层（3-5 天）
- [ ] 实现 `BaseCrawler` 抽象类
- [ ] 实现 4 个专用 Crawler（BBC/CNN/Al Jazeera/AP）
- [ ] 实现 `reuters_rss.py`（Google News RSS）
- [ ] 实现 `generic_html.py`
- [ ] 实现 `rss_adapter.py`
- [ ] 实现 `source_dispatcher.py`
- [ ] `POST /api/v2/sources/{id}/check` 跑通（连通性检测）

### Phase 3：抓取任务（1-2 天）
- [ ] 实现 `fetch_task.py`
- [ ] 实现分时段 `TimeBasedScheduler`
- [ ] 实现 `cleanup_task.py`
- [ ] `POST /api/v2/trigger/fetch` 跑通

### Phase 4：API 路由（1-2 天）
- [ ] `/api/v2/sources` 全套（list/add/delete/toggle/check）
- [ ] `/api/v2/home`
- [ ] `/api/v2/news` + `/api/v2/news/{id}`（含按需爬详情页）
- [ ] `/api/v2/proxy/image`
- [ ] `/api/v2/stats`

### Phase 5：本地验证（1 天）
- [ ] 几个小时的连续运行
- [ ] 验证 5 个源都有数据
- [ ] 验证首页按源分组正确
- [ ] 验证摘要太短的新闻能按需爬到详情

### Phase 6：小程序改造（2-3 天）
- [ ] `services/api.js` 切换 API_BASE
- [ ] `services/news.js` 重写方法集
- [ ] `pages/home/` 按来源分组
- [ ] `pages/detail/` 改为 D + C 兜底
- [ ] `pages/sources/` 新增类型选择
- [ ] `pages/settings/` 删除新闻数量
- [ ] 删除 `pages/ai/`

### Phase 7：阿里云部署（1 天）
- [ ] 上传 `version2/backend/` 到服务器
- [ ] 安装依赖（`pip install -r requirements.txt`）
- [ ] 初始化数据库
- [ ] 启动 systemd 服务（8001 端口）
- [ ] nginx 转发 `/api/v2/`
- [ ] 小程序发布体验版

---

## 关键决策记录

### 已敲定
- ✅ 重构范围：全部推倒重来（前端 UI 复用，逻辑全改）
- ✅ Schema：自定义满足 4 个目标源 + 1 个降级 + 自定义扩展
- ✅ version2/ 完全独立运行，监听 8001
- ✅ 本地开发 + 阿里云部署
- ✅ 前端 UI 复用
- ✅ Python + SQLite + config.yaml
- ✅ 5 个预设源：BBC、CNN（爬虫）/ Al Jazeera、AP（爬虫）/ Reuters（Google News RSS）
- ✅ 详情页：列表摘要（首页拿到的）作为主内容，太短时按需爬详情页（缓存 24h）
- ✅ 自定义源：前端按钮选类型（RSS / 网页爬虫）
- ✅ 首页：按来源分组，每源 Top 3
- ✅ 数据保留：默认 7 天，可配置
- ✅ API 前缀：`/api/v2/`
- ✅ 推送：UI 占位保留，后端不实现
- ✅ 爬虫频率：分时段（早/晚高峰 30 分、日间 1 小时、凌晨 3 小时）
- ✅ 每次抓取：每源最多 50 条
- ✅ Top 3 排序：按源页面原始 position（即首页编辑排序）
- ✅ 通用 HTML 爬虫规则认可
- ✅ 去重：`SHA1(source_code + url)` 作主键
- ✅ 自定义 HTML 源：通用爬虫模式（用户自负质量）

### 待实施时确定
- ⚠️ 4 个爬虫源的 CSS 选择器（Phase 0 阶段产出）
- ⚠️ 默认 `digest_window_hours` 与首页 24 小时的权衡
- ⚠️ 摘要 < 100 字触发按需抓取的阈值（可调）
- ⚠️ rich-text 中图片是否强制走代理

### 显式不做
- ❌ AI 摘要 / atoms
- ❌ Web Push 通知（后端）
- ❌ 用户登录
- ❌ 阅读历史
- ❌ 个性化推荐
- ❌ 跨源事件去重
- ❌ 推送通知后端实现
- ❌ 设置中的"每期新闻数量"

---

## 文件组织

```
beiNewsDigest/
├── PRD.md                            # v1 产品需求文档（保留）
├── 后端技术方案.md                    # v1 后端技术方案（保留）
├── 前端技术方案.md                    # v1 前端技术方案（保留）
│
├── backend/                          # v1 后端代码（保留运行）
├── frontend/                         # v1 Vue 前端（保留不动）
├── wemini/                           # 小程序代码（**会被修改**）
│
└── version2/                         # v2 设计文档 + 未来代码
    ├── README.md                     # 本文件（索引）
    ├── 后端技术方案-v2.md             # 后端设计
    ├── 小程序端技术方案-v2.md          # 小程序端改造
    └── backend/                      # ← 待开发
        ├── config.yaml
        ├── requirements.txt
        ├── main.py
        ├── init_db.py
        ├── app/
        │   ├── config.py
        │   ├── database.py
        │   ├── models/
        │   ├── schemas/
        │   ├── routers/
        │   ├── services/
        │   ├── tasks/
        │   └── utils/
        └── tests/
```

---

## 联调与验收

参见两个设计文档末尾的"验收清单"小节。所有勾选完毕，方可发布。

---

## 联系与变更

如对设计有调整，请直接编辑两份技术方案 + 本 README 的"待定项"段落。


## 服务器部署清库重启

可以整个 backend/ 目录都传上去，但以下几个不需要传：

文件/目录	说明
venv/	虚拟环境，服务器有自己的 Python 环境
__pycache__/	Python 缓存，自动生成
.DS_Store	macOS 系统文件

# 0. 装包
/root/miniconda3/envs/beinews/bin/pip install -r /root/beinews/version2/backend/requirements.txt
# 1. 删除旧的数据库文件
rm /root/beinews/version2/backend/data/bei_news_v2.db*

# 2. 重启服务（会自动重新创建数据库并 seed）
supervisorctl restart beinews-v2

# 3. 查看启动日志确认正常
supervisorctl status beinews-v2

## 切换代理节点的配置
不需要重启
# 切到英国
curl -X PUT http://127.0.0.1:9090/proxies/Ghelper \
  -H "Content-Type: application/json" \
  -d '{"name": "🇬🇧 英国"}'

# 切到新加坡
curl -X PUT http://127.0.0.1:9090/proxies/Ghelper \
  -H "Content-Type: application/json" \
  -d '{"name": "🇸🇬 新加坡"}'

# 切到香港
curl -X PUT http://127.0.0.1:9090/proxies/Ghelper \
  -H "Content-Type: application/json" \
  -d '{"name": "🇭🇰 香港智能"}'

# 切到日本
curl -X PUT http://127.0.0.1:9090/proxies/Ghelper \
  -H "Content-Type: application/json" \
  -d '{"name": "🇯🇵 日本"}'

# 全部线路
"all":["🌐 全球智能","美国西雅图","美国西雅图2","美国洛杉矶[CM]","美国硅谷","美国硅谷2","美国硅谷3","美国圣何塞","美国洛杉矶","美国洛杉矶2","美国ISP","🇭🇰 香港智能","🇭🇰香港中转[CM]","🇭🇰香港精品4","🇭🇰香港精品3","🇭🇰香港精品2","🇬🇧 英国","🇫🇷 法国","🇩🇪 德国","🇲🇾 马来西亚","🇹🇭 泰国[CM]","🇰🇷韩國","🇨🇳 台湾","🇯🇵 日本","🇮🇩 印尼","🇯🇵 日本4","🇸🇬 新加坡[CM]","🇸🇬 新加坡","🇸🇬 新加坡3","AI专用","线路少请更换软件看公告"]