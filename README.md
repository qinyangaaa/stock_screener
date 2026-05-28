# 股票筛选推荐小工具 (Stock Screener)

基于"尾盘选股策略"的 A 股智能筛选工具。每个交易日 14:30 自动对全 A 股进行两级过滤 + 综合评分，输出 Top N 推荐。

## 功能特性

- **两级过滤**：批量初筛（涨幅/量比/换手率/市值） + 逐个技术面深查（成交量台阶/K线多头/分时强度/尾盘信号）
- **综合评分**：6 因子加权打分（量比 25% / 涨幅 20% / 换手率 15% / 均线强度 15% / 分时强度 15% / 尾盘信号 10%）
- **动态配置**：可视化面板实时调整所有策略阈值，无需重启
- **筛选明细**：完整的漏斗分析，可追踪每只股票在哪个规则被淘汰
- **定时 + 手动**：交易日 14:30 自动触发，支持随时手动运行
- **历史回溯**：按日期查看历史推荐记录

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3 / Flask / APScheduler |
| 前端 | React 18 / TypeScript / Vite / Ant Design 5 |
| 数据库 | SQLite |
| 数据源 | Sina API（行情+K线） + 腾讯 API（量比/换手率/市值补充） |

## 项目结构

```
stock_screener/
├── backend/
│   ├── app.py                  # Flask 入口
│   ├── config.py               # 策略参数 + 动态配置系统
│   ├── scheduler.py            # APScheduler 定时任务
│   ├── trading_calendar.py     # A 股交易日历
│   ├── fetcher/
│   │   ├── base.py             # 抽象基类 + 数据结构
│   │   ├── sina_fetcher.py     # Sina + 腾讯混合数据源（主）
│   │   ├── dfcf_fetcher.py     # 东方财富 API（备）
│   │   └── akshare_fetcher.py  # Akshare 封装（备）
│   ├── strategy/
│   │   ├── engine.py           # 两级过滤引擎
│   │   ├── rules.py            # 8 条规则独立实现
│   │   └── scorer.py           # 6 因子加权评分
│   ├── models/
│   │   └── database.py         # SQLite 数据模型
│   └── api/
│       └── routes.py           # REST API
├── frontend/
│   └── src/
│       ├── App.tsx             # 主布局
│       ├── components/
│       │   ├── Dashboard.tsx       # 今日推荐面板
│       │   ├── StockCard.tsx       # 推荐卡片
│       │   ├── StockDetail.tsx     # 规则详情抽屉
│       │   ├── TriggerPanel.tsx    # 触发 + 进度
│       │   ├── HistoryPanel.tsx    # 历史记录
│       │   ├── BreakdownPanel.tsx  # 筛选漏斗明细
│       │   ├── ConfigPanel.tsx     # 策略参数配置
│       │   └── StatusBadge.tsx     # 信号标签
│       ├── services/api.ts     # API 封装
│       └── types/stock.ts      # TypeScript 类型
├── start.py                   # 一键启动脚本
└── README.md
```

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- pip 依赖：`flask flask-cors apscheduler akshare requests numpy`

### 安装与运行

```bash
# 1. 安装后端依赖
pip install flask flask-cors apscheduler akshare requests numpy

# 2. 启动后端
cd backend
python app.py
# 后端运行在 http://localhost:8038

# 3. 安装前端依赖
cd frontend
npm install

# 4. 启动前端
npm run dev
# 前端运行在 http://localhost:5174
```

也可使用根目录的一键启动脚本：

```bash
python start.py
```

### 首次使用

1. 打开 `http://localhost:5174`
2. 点击顶部触发面板的"开始筛选"按钮，或等待 14:30 自动触发
3. 筛选完成后在"今日推荐"标签查看结果
4. 在"筛选明细"标签查看完整漏斗分析
5. 在"策略配置"标签调整参数阈值

## 策略规则

### 第一级过滤（批量，约 5% 通过率）

| 规则 | 条件 | 默认阈值 |
|------|------|----------|
| 涨幅 | 涨幅在合理区间 | 3% - 5%（极端行情放宽至 2%-7%） |
| 量比 | 量比不低于下限 | ≥ 1.0 |
| 换手率 | 换手率适中 | 5% - 20% |
| 流通市值 | 中小盘股优先 | 100 - 500 亿 |

### 第二级过滤（逐个深查）

| 规则 | 说明 | 默认阈值 |
|------|------|----------|
| 台阶式放量 | 最后 6 根 5 分钟 K 线量价齐升，后 3 根至少 2 根高于前一半均值 | — |
| 多头排列 + 套牢盘 | MA5>MA10>MA20>MA60 至少满足 3 组，上方套牢盘 ≤ 60% | — |
| 分时强度 | 站上分时黄线的 K 线占比 ≥ 70%，且强于大盘 | — |
| 尾盘信号 | 14:30 后创新高且回踩黄线不破（距黄线 ≤ 0.5%） | — |

所有阈值均可在"策略配置"页面动态调整。

## 动态配置

- 在"策略配置"标签页可视化编辑所有参数
- 修改即时生效，无需重启服务
- 配置持久化到 SQLite，重启后保留
- 支持按分组批量保存，也可逐个确认
- "重置默认值"可一键恢复出厂设置

## API 参考

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/screen/run` | 手动触发筛选 |
| GET | `/api/screen/status/<task_id>` | 查询筛选进度 |
| POST | `/api/screen/cancel` | 取消正在进行的筛选 |
| GET | `/api/screen/details` | 最近一次筛选明细 |
| GET | `/api/screen/details/<task_id>` | 指定任务的筛选明细 |
| GET | `/api/recommendations/latest` | 最新推荐结果 |
| GET | `/api/recommendations/history?date=YYYY-MM-DD` | 历史推荐 |
| GET | `/api/recommendations/history/dates` | 有推荐的日期列表 |
| GET | `/api/stock/<code>/detail` | 某只股票的历史推荐 |
| GET | `/api/config` | 获取所有策略参数（含元数据） |
| PUT | `/api/config` | 更新参数（单个/批量/重置） |

## 配置说明

修改 `backend/config.py` 中的 `AppConfig` 可调整：

- `port`: 后端端口（默认 8038）
- `data_source`: 数据源 `"sina"` | `"akshare"` | `"dfcf"`
- `debug`: Flask debug 模式

策略参数通过 Web 界面管理，详见"动态配置"一节。

## 网络说明

工具绕过系统代理直接访问数据源。如遇网络问题：
- 确认 Sina Finance (`hq.sinajs.cn`, `money.finance.sina.com.cn`) 可访问
- 确认腾讯行情 (`qt.gtimg.cn`) 可访问
- 后端所有请求使用 `proxies={None, None}` 绕过代理

## License

MIT
