<p align="center">
  <img src="assets/icon.png" width="120" alt="TideTrading Logo"/>
</p>

<h1 align="center">TideTrading：聚焦 A股与港股的智能交易与多维分析工作站</h1>

<p align="center">
  <b>融合多维特征分析（情绪舆情、资金大单、技术回测、基本面分析）与多通道协同推送的个人投研工作站</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat" alt="FastAPI">
  <img src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=flat&logo=react&logoColor=white" alt="React">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/skloxo/TideTrading/actions/workflows/test.yml"><img src="https://github.com/skloxo/TideTrading/actions/workflows/test.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/skloxo/TideTrading/actions/workflows/docker-publish.yml"><img src="https://github.com/skloxo/TideTrading/actions/workflows/docker-publish.yml/badge.svg" alt="Docker Build Status"></a>
</p>

<p align="center">
  <a href="https://codespaces.new/skloxo/TideTrading"><img src="https://github.com/codespaces/badge.svg" alt="Open in GitHub Codespaces" style="max-width: 100%;"></a>
</p>

> [!NOTE]
> **TideTrading** 是专注 **A股与港股** 市场的开源独立智能投研工作站，于 2026-07 正式从上游社区独立。在整合技术指标与量化回测的同时，重点强化了**多维度市场特征提取**（如雪球网与主流社交媒体监控、舆情情绪面量化、大单资金流向监测、行业基本面复盘）与**多通道即插即用推送**（微信 iLink / 飞书），并实现了多租户安全沙箱隔离机制与本地 API 可信授权。向开源社区 [TideTrading](https://github.com/HKUDS/TideTrading) 致谢。

## 📰 最新动态

- **2026-07-07** 🚀 **v1.7.5 — 雪球监控多租户联合查询与 Cookie 轮询 & 持久化共享缓存池 (性能与反爬专项)**：
  - **持久化共享缓存池 (Persistent Shared Cache Pool)**：底层引入了 `shared_xueqiu_cache.json` 磁盘缓存。针对所有租户监控的组合及自选股，每一轮 Tick 仅在缓存失效时向雪球服务器发送一次请求，拉取的数据自动在磁盘上进行持久化。这极大地降低了重复请求与封禁风险，并且支持服务重启后免线上请求直接加载数据。
  - **协同 Cookie 负载均衡轮询 (Cooperative Cookie Rotation)**：当监控标的必须向线上请求时，系统收集所有监控此标的的租户所配置的 `xq_tokens`（雪球 Cookie）凭证，维护全局轮询指针轮流使用，热门组合由多租户协同分摊查询请求压力。
  - **租户安全隔离分发**：调仓日志与自选股变动独立记录在各租户自己的专属目录下，推送也只指向租户各自独立的飞书机器人，实现租户间的信息安全隔离。
  - **系统升级与版本比对重构**：后端重构了系统升级校验逻辑，使用数字元组大小比对机制替代原本的不等值判断，彻底消除了低版本误报与降级警告问题；同时升级了宿主机后台升级脚本，支持开发容器与生产容器的多卷一键升级监听触发。

- **2026-07-06** 🚀 **v1.7.4 — 项目设置独立页面 · 租户敏感凭证物理隔离（隐私防漏泄版本）**：
  - **项目设置独立化**：将项目全局 LLM 及数据源默认设置从普通设置中彻底剥离，提取为专属的 [ProjectSettings.tsx](file://wsl.localhost/Ubuntu-24.04/home/skloxo/aho/openclaw/project/Vibe-Trading/frontend/src/pages/ProjectSettings.tsx) 单页（路由 `/project-settings`），支持管理员就地提权访问。
  - **租户敏感凭证物理隔离**：重构了后端 API 的租户与全局配置合并逻辑。只要当前会话是普通租户（`tenant != "default"`），即使在本地 localhost 下访问，其“自定义大模型”表单输入框中也绝对不会回显或暴露任何属于全局管理员的敏感 API 密钥、模型名称（如 `mimo-v2.5-pro-ultraspeed`）或 Base URL，实现物理级的隐私安全防泄露。
  - **Tabless 清爽租户设置页**：重构后的 `/settings` 主页面去除了所有多余的页签切换，成为纯粹的租户个人通道（飞书机器人、微信）及覆盖配置管理页。

- **2026-07-03** 🚀 **v1.7.3 — 管理员就地提权卡片 · 独立租户管理页面上线（操作流失防范版本）**：
  - **就地管理员提权**：重构了所有受限管理界面的鉴权拦截逻辑。未提权用户访问 `/monitor`（服务看板）、`/settings` (项目设置选项卡)、`/logs`（运行日志）和 `/tenants`（租户管理）时，不再触发 `AdminGuard` 路由级重定向，而是在页面中就地展示 `管理员提权` 凭证输入框，大幅优化交互路径并防范重定向割裂。
  - **独立租户管理页面**：将原服务看板的租户密钥管理解耦，升级为独立的 [TenantManagement.tsx](file://wsl.localhost/Ubuntu-24.04/home/skloxo/aho/openclaw/project/Vibe-Trading/frontend/src/pages/TenantManagement.tsx)（路由 `/tenants`），并于侧边栏“项目运维”中集成“租户管理”二级导航。
  - **提权身份控制中枢**：将管理员密码修改与退出提权卡片统一移至服务看板底部，集中进行提权生命周期管理。

- **2026-07-02** 🚀 **v1.7.2 — i18n 品牌双语统一 · 首页视觉全面升级（蓝图视觉规范落地）**：
  - **i18n 品牌命名分层统一**：全平台严格落实「常用名 / 英文名」双语分层规范。中文模式（`zh-CN`）下，侧边栏、首页英雄区、大屏 Header、仿真终端、Footer 版权等所有用户可见位置统一展示**潮汐投研**；切换英文模式后自动切换为 **TideTrading**，彻底消除混合展示状态。
  - **首页视觉全面升级（蓝图视觉规范落地）**：依据 `docs/tide_trading_grand_roadmap.md` 中 §2 界面视觉设计规范，对首页进行全量视觉重构：英雄区新增渐变标题与发光光环，实装实时 A股 核心股票走势 Ticker 大屏，重构核心卡片为带有 Hover 交互发光阴影效果的玻璃态容器。

- **2026-07-02** 🚀 **v1.7.1 — 共享数据底座、大屏全卡片玻璃态重构与数据清洗自愈版本发布**：
  - **大屏卡片玻璃态去重重构**：全面清理了面板组件自身的冗余双重边框与白背景，悬浮发光与玻璃态统一收拢至 ReactGridLayout 外层父容器，消除浅色模式下的双重框线问题。
  - **共享/私有数据分离路由**：全市场历史 K 线归入共享库 `stocks_market.db`，用户自选数据与回测私有目录严格隔离在租户库 `stocks_<tenant_id>.db`。
  - **通达信二进制行情高速导入**：WAL 模式实现每秒 2.8 万条高速写入，累计导入 510 万+ 条历史行情；编写 SQLite 库个股简称占位符清洗脚本，打通腾讯 API 分批抓取机制。

- **2026-07-01** 🚀 **v1.6.0 — 行情网关自愈预检、多参考仓库对账看板与 GitHub CLI SOP 版本发布**：
  - **行情自愈预检**：新增 `_check_mootdx_and_heal` 行情网关预检，自愈 BESTIP 损坏异常并自动重新测速。
  - **参考仓库追踪**：新增 `update_repositories_status.py` 追踪上游及分叉状态，按天输出 [REPOSITORIES_STATUS.md](file://wsl.localhost/Ubuntu-24.04/home/skloxo/aho/openclaw/project/TideTrading/REPOSITORIES_STATUS.md) 对账大屏。

- **2026-07-01** 🚀 **v1.5.0 — 同花顺自选双向同步、秒级自选盯盘与收盘对账自愈系统版本发布**：
  - **自选股双向同步**：实现多租户自选股差分对账双向同步，交易盘中（5分钟）与非交易时段（30分钟）自适应频次轮询。
  - **秒级自选盯盘监控**：秒级自选行情扫描，指标触达时自动通过飞书/微信警报推送并防刷。
  - **收盘自愈与对账回填**：每日 15:35 自动校准基础数据与板块成分，支持开机启动对账自愈（Gap Healing）。

- **2026-06-30** 🚀 **v1.4.0 — 平台级公用数据共享缓存层 (SharedMemoryHub) 版本发布**：
  - **共享缓存服务**：线程安全单例 SharedMemoryHub 行情缓存（TTL=3秒），盘中批量高频刷新、盘后自动降频，防范多租户并发请求通达信 TCP 封禁 IP 风险。

- **2026-06-30** 🚀 **v1.3.0 — 平台指引优化、大屏与移动端 H5 响应式适配、服务看板合并与运行报告鉴权加固版本发布**：
  - **大屏幕合并与体验打磨**：合并密钥与升级看板，移动端 H5 自适应与双模主题配色优化，运行报告页面权限隔离校验。

- **2026-06-29** 🚀 **v1.1.0 — 服务看板与公网隔离优化版本发布**：
  - 引入高频行情 TCP 测速保活连接池，首次上线服务看板（展示内存、租户会话与控制台日志）并增加公网访问对全局密钥的沙箱隐私屏蔽。

---

## ✨ 核心功能

🎯 **聚焦 A股与港股**，深度定制，而非泛化全球市场的通用工具

| 功能模块 | 描述 |
|----------|------|
| 🧠 **自然语言驱动研究** | 用中文对话驱动投研工作流：分析个股、回测策略、解读财报、挖掘题材，无需写代码 |
| 📡 **多维市场特征提取** | 同步抓取**情绪面**（雪球大V舆情）、**资金面**（大单龙虎榜）、**技术面**（指标形态）、**基本面**（财报题材）四维立体信号 |
| 🔄 **同花顺自选股同步** | 支持多租户 Cookie 隔离配置，盘中 5 分钟/其余 30 分钟自适应双向差分对账，并提供前台一键手动同步 |
| 🚨 **自选盯盘与收盘自愈** | 交易时间秒级自选股高频盯着异动并推送飞书/微信；每日 15:35 自动触发收盘对账维护，支持 Gap Healing 数据自愈 |
| 🤖 **多智能体分析团队** | 29 个预置 Swarm 团队（投资委员会、量化台、技术分析团、风控审计等），多 Agent 协同辩论出研究共识 |
| 📲 **多通道即时推送** | 微信个人号（iLink）/ 飞书机器人即插即用，策略信号与研究简报实时直达手机 |
| 🔬 **策略回测与 Alpha 横评** | 支持 A股/港股策略回测、452 个预置 Alpha 因子（国君191、Qlib158、Alpha101）一键横评 |
| 👥 **Shadow Account 交易复盘** | 上传同花顺/东方财富/富途账单，AI 提取你的交易规律，与 Shadow 策略做对比，找出错失机会 |
| 🔌 **MCP 工具化** | 通过 MCP 协议接入 Claude Desktop / OpenClaw / Cursor 等任意 AI 工具，作为智能体工具箱使用 |
| 🏗 **本地私有部署** | Docker 一键部署，数据留本地，多租户安全隔离，API 可信授权，支持异地局域网访问 |

## 💡 什么是 TideTrading？

TideTrading 是面向 **A股与港股** 的开源独立智能投研工作站，深度聚焦中国市场的量化与 AI 投研能力。

它将自然语言提示连接到多维度市场特征分析（**情绪面 / 资金面 / 技术面 / 基本面**）、策略回测引擎、报告生成和持久投研记忆，并通过微信（iLink）/ 飞书等通道将研究简报即时推送到你的手机。

它面向研究、模拟和回测——面向理解市场、复盘自己的交易行为、挖掘 A股与港股的投资机会。

---

## ✨ 你能做什么

| 任务 | 输出与多维特征支持 |
|------|------|
| **多维特征提取与监控** | 结合**情绪面**（雪球大V及舆情监控）、**资金面**（大单与龙虎榜）、**技术面**（形态/指标回测）与**基本面**（题材/板块）对 A股与港股标的进行深度分析。 |
| **自选股同步与监控** | 实现同花顺云端自选股与本地 Watchlist 的真双向对账同步，开盘期间支持高频盯盘并推送异动警报。 |
| **回测策略想法** | 策略代码、指标、A股/港股 benchmark 对比、验证 artifacts 和 run cards。 |
| **复盘自己的交易** | 国内主流券商（同花顺、东方财富、富途等）日志解析、行为诊断、规则提取和 Shadow Account 对比。 |
| **多通道异常预警** | 即插即用绑定微信个人号（iLink）或飞书（Lark）机器人，将策略信号与运行简报实时推送至手机端。 |
| **运行分析师团队** | 面向投资、量化、宏观题材和风控工作流的多智能体研究评审。 |
| **交付可用成果** | 报告、TradingView Pine Script、通达信 (TDX)、MetaTrader 5、MCP tools，以及可延续的研究 sessions。 |
| **跑预置 alpha zoo 横评** | 452 个 alpha 因子（含国君 191、Qlib 158、Alpha 101），一键在沪深300/中证500上算 IC + IR + alive/reversed/dead 分类。 |

---

## 🗺 CNX 路线图与未来蓝图

TideTrading 定位为更贴合中国投资者交易习惯的 A股与港股智能投研终端。我们的未来演进蓝图聚焦于高频行情获取、自选双向同步、做T网格模拟盘及智能体交互体验的深度打磨，采用五阶段螺旋上升演进：

| 阶段 | 核心目标 / 特性 | 状态与进展 |
|------|------|------|
| **阶段一：高频行情基建、同花顺同步、移动端优化与指引升级** | 对接通达信 L1 TCP 高频秒级行情，实现同花顺自选股双向同步；完成移动端 H5 响应式排版加固；重构首页新手地图与智能体典型 Prompts；支持正式环境一键更新与平滑重启。 | **已完成** |
| **阶段二：默认选股脚本可视化、多用户并发与隔离安全** | 将租户已有的选股与复盘日报 Python 脚本搬上前端可视化，一键点击执行与图文渲染；强化多用户并发 Key池管理与数据库隔离。 | **进行中 (当前阶段)** |
| **阶段三：做T网格建议与 VirtualBroker 模拟盘** | 研发模拟柜台交易闭环，支持委托/成交状态机追踪，并在每日盘前自动生成股票做T网格策略建议。 | **规划中** |
| **阶段四：前端交互深度优化与研报排版美化** | 大幅升级人机交互体验，重构并设计更精美的大模型研报与日报图表排版；前端 K 线图上实现 TradeMarker 交易成交气泡。 | **规划中** |
| **阶段五：在线策略编辑与 VS Code 桌面工作台** | 为专业交易员提供在线 Monaco 策略/因子编译器与沙箱编译；支持 VLM 视觉研报与 K线形态分析；打造多窗口、拖拽式布局的桌面客户端。 | **规划中** |

---



```bash
pip install tide-ai

# A股个股回测与多通道简报推送示例
tide run -p "回测贵州茅台 (600519) 2024年的 20/50 日均线交叉策略，总结收益率与最大回撤，并通过微信推送研究简报"

# 一行 CLI 跑预置国君 191 因子横评
tide alpha bench --zoo gtja191 --universe csi300 --period 2020-2025 --top 20
```

```bash
tide --upload trades_export.csv
tide run -p "分析我的 A股/港股交易行为，提取我的 Shadow 策略，并与真实交易做对比"
```

---

## 👥 Shadow Account

Shadow Account 从你自己的交易记录出发，而不是从通用策略模板出发。

上传券商导出，让智能体总结你的交易行为，然后将真实交易路径与基于规则的 shadow strategy 进行对比。

| 步骤 | 智能体输出 |
|------|------------|
| **1. 读取交易日志** | 解析来自同花顺、东方财富、富途和 generic CSV 格式的券商导出。 |
| **2. 生成行为画像** | 持仓天数、胜率、盈亏比、回撤、处置效应、过度交易、追涨和锚定检查。 |
| **3. 提取你的规则** | 将反复出现的入场/出场行为转化为明确策略画像，而不是空泛总结。 |
| **4. 运行 shadow** | 回测提取出的规则，并高亮规则违背、过早离场、错过信号和替代交易路径。 |
| **5. 交付报告** | 生成可检查、可归档或在后续 session 中继续精修的 HTML/PDF 报告。 |

```bash
tide --upload trades_export.csv
tide run -p "分析我的 A股/港股交易行为，提取我的 Shadow 策略，并与真实交易做对比"
```

---

## 🧪 研究工作流

多数运行都会遵循同一条证据路径：路由请求、加载正确的市场上下文、执行工具、验证输出，并保持 artifacts 可检查。

| 层 | 发生什么 |
|----|----------|
| **Plan** | 选择相关金融 skills、tools、数据源，以及在有帮助时选择 swarm preset。 |
| **Ground** | 通过可用 loader 拉取 A 股、港股/美股、加密、期货、外汇、文档或网页上下文。 |
| **Execute** | 生成可测试的策略代码，运行工具，并使用匹配的回测引擎或分析工作流。 |
| **Validate** | 在适用时加入指标、benchmark comparison、Monte Carlo、Bootstrap、Walk-Forward、run cards 和 warnings。 |
| **Deliver** | 返回报告、artifacts、tool traces，以及面向 TradingView、TDX、MetaTrader 5、MCP clients 或后续 sessions 的导出。 |

---

## 🔩 详细能力清单

为保持主 README 易读，详细清单折叠在下方。需要检查可用构件时可展开查看。

<details>
<summary><b>金融能力库 (Finance Skill Library)</b> <sub>8 个类别中的 77 个 skills</sub></summary>

- 📊 77 个专业金融 skills，分布在 8 个类别中
- 🌐 覆盖传统市场、加密与 DeFi
- 🔬 从数据源到量化研究的完整能力链路

| 类别 | Skills | 示例 |
|------|--------|------|
| 数据源 (Data Source) | 7 | `data-routing`, `tushare`, `yfinance`, `okx-market`, `akshare`, `mootdx`, `ccxt` |
| 交易策略 (Strategy) | 17 | `strategy-generate`, `cross-market-strategy`, `technical-basic`, `candlestick`, `ichimoku`, `elliott-wave`, `smc`, `multi-factor`, `ml-strategy` |
| 投研分析 (Analysis) | 17 | `factor-research`, `macro-analysis`, `global-macro`, `valuation-model`, `earnings-forecast`, `credit-analysis`, `dividend-analysis` |
| 资产类别 (Asset Class) | 9 | `options-strategy`, `options-advanced`, `convertible-bond`, `etf-analysis`, `asset-allocation`, `sector-rotation` |
| 加密货币 (Crypto) | 7 | `perp-funding-basis`, `liquidation-heatmap`, `stablecoin-flow`, `defi-yield`, `onchain-analysis` |
| 资金流向 (Flow) | 7 | `hk-connect-flow`, `us-etf-flow`, `edgar-sec-filings`, `financial-statement`, `adr-hshare` |
| 核心工具 (Tool) | 11 | `backtest-diagnose`, `report-generate`, `pine-script`, `doc-reader`, `web-reader`, `vnpy-export`, `alpha-zoo` |
| 风险分析 (Risk Analysis) | 1 | `ashare-pre-st-filter` |

</details>

<details>
<summary><b>自定义数据源</b> <sub>注册你自己的历史 OHLCV loader</sub></summary>

需要一个我们没有内置 loader 的市场或数据商？自己加一个历史 K 线 loader，用
`source="<name>"` 选用即可。以下步骤会改动包源码，请从 clone 运行（`pip install -e .`）。

1. **编写 loader** —— 新建 `agent/backtest/loaders/<name>_loader.py`，写一个满足
   `DataLoaderProtocol` 的类（duck-typed，无需基类），并打上 `@register`：

   ```python
   import pandas as pd
   from backtest.loaders.registry import register

   @register
   class DataLoader:
       name = "mysource"            # the value you pass as source=
       markets = {"us_equity"}      # a_share/us_equity/hk_equity/crypto/futures/fund/macro/forex
       requires_auth = False

       def is_available(self) -> bool:
           return True              # token present? network reachable?

       def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
           # return {symbol: DataFrame indexed by trade_date,
           #         columns: open, high, low, close, volume}
           ...
   ```

2. **注册模块** 让 `@register` 生效 —— 把 `"backtest.loaders.<name>_loader"` 加进
   `agent/backtest/loaders/registry.py` 的 `_loader_modules`。
3. **放行名称** 通过配置校验 —— 把 `"mysource"` 加进 `agent/backtest/runner.py`
   的 `_VALID_SOURCES`。
4. *（可选）* 把它放进 `registry.py` 中某个市场的 `FALLBACK_CHAINS`，让
   `source="auto"` 也能命中它。
5. **使用** —— 在回测配置里写 `source="mysource"`，或经 CLI / agent 调用。

> **实时 ticks / 盘口深度不在 loader 范围内** —— loader 层只负责 point-in-time
> 历史 K 线。实时行情走 broker connector：加密用 `okx` / `binance` / `ccxt`，
> 股票用 `futu` / `tiger`。

</details>

<details>
<summary><b>预设交易团队 (Preset Trading Teams)</b> <sub>29 个 swarm presets</sub></summary>

- 🏢 29 个开箱即用的智能体团队
- ⚡ 预配置金融工作流
- 🎯 投资、交易与风险管理 presets

| Preset | 工作流 |
|--------|--------|
| `investment_committee` | 多空辩论 → 风险审查 → PM 最终决策 |
| `global_equities_desk` | A 股 + 港/美股 + 加密研究员 → 全球策略师 |
| `crypto_trading_desk` | Funding/basis + liquidation + flow → 风险经理 |
| `earnings_research_desk` | 基本面 + 预期修正 + options → 财报策略师 |
| `macro_rates_fx_desk` | 利率 + 外汇 + 商品 → 宏观 PM |
| `quant_strategy_desk` | 筛选 + 因子研究 → 回测 → 风险审计 |
| `technical_analysis_panel` | 经典 TA + Ichimoku + harmonic + Elliott + SMC → 共识 |
| `risk_committee` | 回撤 + 尾部风险 + regime review → 审批 |
| `global_allocation_committee` | A 股 + 加密 + 港/美股 → 跨市场配置 |

<sub>另有 20+ 专业 presets，可运行 tide --swarm-presets 查看全部。

</sub>

</details>

<details>
<summary><b>Alpha 因子库 (Alpha Zoo)</b> <sub>452 个预置 alpha，覆盖 4 个 zoo</sub></summary>

- 🧬 452 个横截面 alpha，算子层即禁用 lookahead
- 📈 一条 CLI 命令完成 IC + IR + alive/reversed/dead 分类
- 🔬 AST 纯函数门禁 + 300 行 lookahead 哨兵测试 + `pytest-socket` 网络阻断
- 📦 Qlib 部分附 Apache-2 出处声明；每个 zoo 一份 `LICENSE.md`，声明公式属于数学内容
- 🤝 社区 PR 走 Developer Certificate of Origin (DCO) 签名流程

| Zoo | 数量 | 来源 | 许可 |
|-----|------|------|------|
| **qlib158** | 154 | Microsoft Qlib `Alpha158`（Apache-2.0，锁定 commit） | Apache-2.0 |
| **alpha101** | 101 | Kakushadze (2015), "101 Formulaic Alphas", arXiv:1601.00991 | 公式属于数学内容 |
| **gtja191** | 191 | 国君证券 (2014)《191 个短周期交易型 alpha 因子》研报 | 公式属于数学内容 |
| **academic** | 6 | Fama-French 5 因子 + Carhart 动量（基于价格的代理实现） | 公开学术文献 |

运行 `tide alpha list` 浏览全部因子，`tide alpha show <id>` 查看公式与源码，`tide alpha bench --zoo X --universe Y --period Z` 给一整个 zoo 打分。

</details>

## 🎬 功能演示

<div align="center">
<table>
<tr>
<td width="50%">

https://github.com/user-attachments/assets/4e4dcb80-7358-4b9a-92f0-1e29612e6e86

</td>
<td width="50%">

https://github.com/user-attachments/assets/3754a414-c3ee-464f-b1e8-78e1a74fbd30

</td>
</tr>
<tr>
<td colspan="2" align="center"><sub>☝️ 自然语言回测与多智能体 swarm 辩论 — Web UI + CLI（TideTrading v1.7 功能演示）</sub></td>
</tr>
</table>
</div>

---

## 🚀 快速开始

### 一行安装（PyPI）

```bash
pip install tide-ai
```

然后运行第一个 A股 研究任务：

```bash
tide init
tide run -p "回测贵州茅台 (600519) 2024年的 20/50 日均线交叉策略，并微信推送研究简报"
```

> **包名与命令：** PyPI 包名是 `tide-ai`。安装后会获得三个命令：
>
> | 命令 | 用途 |
> |------|------|
> | `tide` | 交互式 CLI / TUI |
> | `tide serve` | 启动 FastAPI web server (默认端口 9988，测试/开发环境使用 9888) |
> | `tide-mcp` | 启动 MCP server（用于 Claude Desktop、OpenClaw、Cursor 等） |

```bash
tide init              # interactive .env setup
tide                   # launch CLI
tide serve --port 9988 # launch web UI
tide-mcp               # start MCP server (stdio)
```

### 或选择一种路径

| 路径 | 最适合 | 时间 |
|------|--------|------|
| **A. Docker** | 立即试用，零本地配置 | 2 min |
| **B. 本地安装** | 开发，完整 CLI 访问 | 5 min |
| **C. MCP plugin** | 接入你现有的智能体 | 3 min |
| **D. ClawHub** | 一条命令，无需 clone | 1 min |

### 前置条件

- 任意受支持 provider 的 **LLM API key**，或使用 **Ollama** 本地运行（无需 key）
- 路径 B 需要 **Python 3.11+**
- 路径 A 需要 **Docker**

> **支持的 LLM providers：** OpenRouter、OpenAI、DeepSeek、Gemini、Groq、DashScope/Qwen、Zhipu、Moonshot/Kimi、MiniMax、Xiaomi MIMO、Ollama（本地）。配置见 `.env.example`。

> **提示：** 由于自动 fallback，数据可以在没有任何 API key 的情况下工作。yfinance（港股）、mootdx（A 股，TCP 直连不封 IP）和 AKShare（A 股、港股、期货、外汇）都是免费的。Tushare token 是可选项 —— mootdx 是首选的免 token A 股 fallback，AKShare 作为覆盖更广的兜底。而情绪面支持则可通过设置页面一键绑定您的雪球网凭证进行深度监控。

<details>
<summary><b>🐳 Path A: Docker 部署（零配置，点击展开）</b></summary>

### Path A: Docker（零配置）

```bash
git clone https://github.com/skloxo/TideTrading.git
cd TideTrading
cp agent/.env.example agent/.env
# Edit agent/.env — uncomment your LLM provider and set API key
docker compose up --build
```

打开 `http://localhost:9988`（测试开发环境为 `http://localhost:9888`）。后端 + 前端在同一个容器中运行。

Docker 默认将后端发布在 `127.0.0.1:9988`，并以非 root 容器用户运行应用。如果你有意将 API 暴露到本机之外，请设置强 `API_AUTH_KEY`，并让客户端发送 `Authorization: Bearer <key>`。

</details>

<details>
<summary><b>💻 Path B: 本地源码安装与开发（点击展开）</b></summary>

### Path B: 本地安装

```bash
git clone https://github.com/skloxo/TideTrading.git
cd TideTrading
python -m venv .venv

# Activate
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -e .
cp agent/.env.example agent/.env   # Edit — set your LLM provider API key
tide                   # Launch interactive TUI
```

<details>
<summary><b>启动 Web UI（可选）</b></summary>

```bash
# Terminal 1: API server
tide serve --port 9988

# Terminal 2: Frontend dev server
cd frontend && npm install && npm run dev
```

打开 `http://localhost:5173` 或控制台打印的前端开发服务地址。前端会将 API 调用代理到 `localhost:9988`（测试/开发环境对应 `localhost:9888`）。

**生产模式（单 server）：**

```bash
cd frontend && npm run build && cd ..
tide serve --port 9988     # FastAPI serves dist/ as static files
```

> [!NOTE]
> `tide serve` 绑定 `0.0.0.0`，但默认只信任 loopback。若你从**另一台机器、虚拟机宿主机或局域网内的手机**访问，敏感接口会返回 `403` 且阻止写入，报错 `Cross-site request denied`。请配置 `agent/.env` 中的 `API_ALLOWED_HOSTS` 来信任您的公网/局域网域名或 IP 地址，这允许您在安全的局域网内免 key 异地使用和配置 settings；若要公开使用，请同时开启 `API_AUTH_KEY` 以确保网络传输安全。

</details>

</details>

<details>
<summary><b>🔌 Path C: MCP 插件接入（点击展开）</b></summary>

见下方 [MCP 插件](#-api-与-mcp-服务) 章节。
</details>

<details>
<summary><b>📦 Path D: ClawHub 一键安装（点击展开）</b></summary>

### Path D: ClawHub 一键安装

```bash
npx clawhub@latest install tide --force
```

skill + MCP config 会下载到你的智能体 skills 目录。详情见 [MCP 插件](#-api-与-mcp-服务)。
</details>

---

<details>
<summary><b>🧠 环境变量配置（.env 属性详解，点击展开）</b></summary>


将 `agent/.env.example` 复制为 `agent/.env`，并取消注释你想使用的 provider block。每个 provider 需要 3-4 个变量：

| 变量 | 必需 | 说明 |
|------|:----:|------|
| `LANGCHAIN_PROVIDER` | Yes | Provider 名称（`openrouter`, `deepseek`, `groq`, `ollama` 等） |
| `<PROVIDER>_API_KEY` | Yes* | API key（`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY` 等） |
| `<PROVIDER>_BASE_URL` | Yes | API endpoint URL |
| `LANGCHAIN_MODEL_NAME` | Yes | 模型名称（例如 `deepseek-v4-pro`） |
| `TUSHARE_TOKEN` | No | A 股数据的 Tushare Pro token（会 fallback 到 AKShare） |
| `TIMEOUT_SECONDS` | No | LLM 调用超时，默认 120s |
| `API_AUTH_KEY` | 网络部署推荐 | API 可被非本地客户端访问时要求的 Bearer token |
| `VIBE_TRADING_ENABLE_SHELL_TOOLS` | No | 在远程 API/MCP-SSE 风格部署中显式启用 shell-capable tools |
| `VIBE_TRADING_ALLOWED_FILE_ROOTS` | No | 文档和券商日志导入额外允许的逗号分隔 roots |
| `VIBE_TRADING_ALLOWED_RUN_ROOTS` | No | 生成代码 run directories 额外允许的逗号分隔 roots |

<sub>* Ollama 不需要 API key。OpenAI Codex 使用 ChatGPT OAuth，并通过 `oauth-cli-kit` 存储 token，不写入 `agent/.env`。</sub>

**免费数据（无需 key）：** A 股通过 AKShare，港/美股通过 yfinance，加密通过 OKX，100+ 加密交易所通过 CCXT。系统会为每个市场自动选择最佳可用数据源。

</details>

<details>
<summary><b>🎯 推荐的大语言模型（LLM）配置建议（点击展开）</b></summary>

### 🎯 推荐模型

TideTrading 是高度依赖工具的智能体：skills、backtests、memory 和 swarms 都会通过工具调用流转。模型选择会直接决定智能体是实际使用工具，还是从训练数据中编造答案。

| 档位 | 示例 | 使用场景 |
|------|------|----------|
| **Best** | `anthropic/claude-opus-4.7`, `anthropic/claude-sonnet-4.6`, `openai/gpt-5.5-pro`, `google/gemini-3.5-flash` | 复杂 swarms（3+ agents）、长研究 sessions、论文级分析 |
| **Sweet spot**（默认） | `deepseek-v4-pro`, `deepseek/deepseek-v4-pro`, `x-ai/grok-4.20`, `z-ai/glm-5.1`, `moonshotai/kimi-k2.6`, `qwen/qwen3-max-thinking` | 日常主力，约 1/10 成本下具备可靠工具调用 |
| **避免用于 agent** | `*-nano`, `*-flash-lite`, `*-coder-next`, 小型 / 蒸馏变体 | 工具调用不可靠，智能体会看起来像是在“凭记忆回答”，而不是加载 skills 或运行回测 |

默认 `agent/.env.example` 使用 DeepSeek 官方 API + `deepseek-v4-pro`；OpenRouter 用户可以使用 `deepseek/deepseek-v4-pro`。

</details>

---

<details>
<summary><b>🖥 CLI 命令行与交互式 TUI 指南（点击展开）</b></summary>


```bash
tide               # interactive TUI
tide run -p "..."  # single run
tide serve         # API server
tide alpha list    # 浏览 452 个预置 alpha；支持 show / bench / compare / export-manifest 子命令
```

<details>
<summary><b>TUI 终端快捷指令 (Slash Commands)</b></summary>

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有命令 |
| `/skills` | 列出全部 77 个 finance skills |
| `/swarm` | 列出 29 个 swarm team presets |
| `/swarm run <preset> [vars_json]` | 运行一个 swarm team，并实时流式展示 |
| `/swarm list` | Swarm 运行历史 |
| `/swarm show <run_id>` | Swarm 运行详情 |
| `/swarm cancel <run_id>` | 取消运行中的 swarm |
| `/list` | 最近 runs |
| `/show <run_id>` | Run 详情 + 指标 |
| `/code <run_id>` | 生成的策略代码 |
| `/pine <run_id>` | 导出指标（TradingView + TDX + MT5） |
| `/trace <run_id>` | 完整执行回放 |
| `/continue <run_id> <prompt>` | 用新指令继续一个 run |
| `/sessions` | 列出 chat sessions |
| `/settings` | 显示运行时配置 |
| `/clear` | 清屏 |
| `/quit` | 退出 |

</details>

<details>
<summary><b>单次运行命令与参数 (Single run & flags)</b></summary>

```bash
tide run -p "回测宁德时代 (300750) 2024年的日线突破策略"
tide run -p "分析腾讯控股 (00700.HK) 的动量因子" --json
tide run -f strategy.txt
echo "回测平安银行 (000001.SZ) RSI" | tide run
```

```bash
tide -p "your prompt"
tide --skills
tide --swarm-presets
tide --swarm-run investment_committee '{"topic":"A股与港股主力资金流向研判"}'
tide --list
tide --show <run_id>
tide --code <run_id>
tide --pine <run_id>           # Export indicators (TradingView + TDX + MT5)
tide --trace <run_id>
tide --continue <run_id> "精细化止盈止损策略"
tide --upload report.pdf
tide alpha list --zoo gtja191 --limit 10
tide alpha show gtja191_171
tide alpha bench --zoo gtja191 --universe csi300 --period 2020-2025 --top 20
```

</details>

</details>

---



## 💡 典型示例

<details>
<summary><b>策略回测示例（点击展开）</b></summary>


```bash
# 均线交叉策略回测 (A股/港股)
tide run -p "回测贵州茅台 (600519) 过去一年的 20/50 日均线交叉策略，展示夏普比率与最大回撤"

# 超买超卖均值回归策略测试
tide run -p "测试招商银行 (600036) RSI(14) 均值回归策略：低于30买入，高于70卖出，过去6个月"

# 多因子策略回测
tide run -p "回测沪深300成分股过去2年的动量+价值+质量多因子策略"

# 回测完成后，一键导出至通达信 (TDX) / TradingView / MetaTrader 5
tide --pine <run_id>
```

**一行命令横评预置 alpha zoo**：
```bash
tide alpha bench --zoo gtja191 --universe csi300 --period 2020-2025 --top 20
```

**浏览目录** + 查看单个 alpha：
```bash
tide alpha list --zoo gtja191 --theme reversal --limit 10
tide alpha show gtja191_171
```

**用 zoo 因子组合多因子信号**（Python）：
```python
from src.skills.multi_factor.zoo_signal_engine import ZooSignalEngine
engine = ZooSignalEngine.from_zoo(["gtja191_171", "gtja191_111", "gtja191_163"])
panel = ...  # your wide OHLCV panel
signal = engine.compute_signal(panel)
```

</details>

<details>
<summary><b>市场研究示例（点击展开）</b></summary>


```bash
# 个股深度投研
tide run -p "研究比亚迪 (002594)：财报趋势、分析师一致预期、大单资金流向及下季度核心风险"

# 宏观题材分析
tide run -p "分析当前中国降准降息政策预期、人民币汇率走势及对 A股 与港股的影响"

# 情绪面舆情特征深度监控
tide run -p "深度挖掘雪球热门股情绪指标：监控大V多空动向、股吧热门评论与高管增减持"
```

</details>

<details>
<summary><b>多智能体 Swarm 工作流示例（点击展开）</b></summary>


```bash
# 针对特定标的多空观点辩论
tide --swarm-run investment_committee '{"topic": "当前位置的腾讯控股 (00700.HK) 是否值得买入？"}'

# 因子筛选到回测审计的量化工作流
tide --swarm-run quant_strategy_desk '{"universe": "csi300", "horizon": "3 months"}'

# 经典技术形态多智能体共识研判
tide --swarm-run technical_analysis_panel '{"asset": "600519.SH", "timeframe": "1d"}'

# 宏观配置委员会进行资产配比建议
tide --swarm-run macro_rates_fx_desk '{"focus": "央行降息流动性释放对国债与权益资产的再配置建议"}'
```

</details>

<details>
<summary><b>跨 Session 记忆示例（点击展开）</b></summary>


```bash
# 设定您的个人交易风格偏好 (一次记录，全站有效)
tide run -p "记住：我偏好 RSI 策略，最大回撤限制为 10%，持仓期 5-20 天"

# 智能体将在未来对话会话中自动读取该偏好约束
tide run -p "为我设计一个适合我风险画像的 A股 策略"
```

</details>

<details>
<summary><b>上传与文档分析示例（点击展开）</b></summary>


```bash
# 上传个人交割单或券商账单进行交易复盘画像
tide --upload trades_export.csv
tide run -p "分析我的 A股/港股交易行为，提取我的 Shadow 策略，并与真实交易做对比"

# 上传财报/研报 PDF 并提炼核心风险与业绩超预期情况
tide --upload BYD_earnings.pdf
tide run -p "总结该比亚迪季度财报中的核心风险及与业绩预期偏差"
```
</details>


---

## 🔌 API 与 MCP 服务

为保持主 README 易读，API 服务与 MCP 插件的详细配置及接口说明折叠在下方。

<details>
<summary><b>🌐 API 服务接口与安全策略（点击展开）</b></summary>


```bash
tide serve --port 9988
```

| Method | Endpoint | 说明 |
|--------|----------|------|
| `GET` | `/runs` | 列出 runs |
| `GET` | `/runs/{run_id}` | Run 详情 |
| `GET` | `/runs/{run_id}/pine` | 多平台指标导出 |
| `POST` | `/sessions` | 创建 session |
| `POST` | `/sessions/{id}/messages` | 发送消息 |
| `GET` | `/sessions/{id}/events` | SSE event stream |
| `POST` | `/upload` | 上传 PDF/file |
| `GET` | `/swarm/presets` | 列出 swarm presets |
| `POST` | `/swarm/runs` | 启动 swarm run |
| `GET` | `/swarm/runs/{id}/events` | Swarm SSE stream |
| `GET` | `/alpha/list` | 按 zoo/theme/universe 过滤列出 alpha |
| `GET` | `/alpha/{alpha_id}` | Alpha 元数据 + 源代码 |
| `POST` | `/alpha/bench` | 启动一个 bench job（返回 `job_id`） |
| `GET` | `/alpha/bench/{job_id}/stream` | SSE 进度流 |
| `GET` | `/settings/llm` | 读取 Web UI LLM settings |
| `PUT` | `/settings/llm` | 更新本地 LLM settings |
| `GET` | `/settings/data-sources` | 读取本地数据源 settings |
| `PUT` | `/settings/data-sources` | 更新本地数据源 settings |

交互式文档：`http://localhost:9988/docs`

### 安全默认策略

对于 localhost 开发，`tide serve` 会保持浏览器工作流简单。对任何非本地客户端，敏感 API endpoints 都要求 `API_AUTH_KEY`；JSON/upload 请求请使用 `Authorization: Bearer <key>`。浏览器 EventSource streams 会在你于 Settings 中输入同一个 key 后由 Web UI 处理。

Shell-capable tools 可用于本地 CLI 与可信 localhost 工作流，但不会暴露给远程 API sessions，除非你显式设置 `VIBE_TRADING_ENABLE_SHELL_TOOLS=1`。文档和日志读取器默认限制在 upload/import roots 内；请将文件放在 `agent/uploads`、`agent/runs`、`./uploads`、`./data`、`~/.tide/uploads` 或 `~/.tide/imports` 下，或通过 `VIBE_TRADING_ALLOWED_FILE_ROOTS` 添加专用目录。

### Web UI 设置

Web UI Settings 页面允许本地用户更新 LLM provider/model、base URL、generation parameters、reasoning effort，以及 Tushare token 等可选市场数据凭据。Settings 会持久化到 `agent/.env`；provider defaults 从 `agent/src/providers/llm_providers.json` 加载。

Settings 读取无副作用：`GET /settings/llm` 和 `GET /settings/data-sources` 永远不会创建 `agent/.env`，并且只返回项目相对路径。Settings 读写可能暴露凭据状态或更新凭据/运行时环境，因此在配置了 `API_AUTH_KEY` 时会要求认证。如果 dev mode 下未设置 `API_AUTH_KEY`，settings 访问只接受 loopback clients。

---

</details>

<details>
<summary><b>🔌 MCP 插件与客户端集成配置（点击展开）</b></summary>


TideTrading 为任何 MCP-compatible client 暴露 36 个 MCP tools。它作为 stdio subprocess 运行，无需 server setup。核心 research tools 对 A股/港股 零 API key 可用；trading connector tools 使用当前选择的 connector profile；只有 `run_swarm` 需要 LLM key。

<details>
<summary><b>Claude Desktop 客户端配置</b></summary>

添加到 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "tide": {
      "command": "tide-mcp"
    }
  }
}
```

</details>

<details>
<summary><b>OpenClaw 配置</b></summary>

添加到 `~/.openclaw/config.yaml`：

```yaml
skills:
  - name: tide
    command: tide-mcp
```

</details>

<details>
<summary><b>Cursor / Windsurf 及其他 MCP 客户端配置</b></summary>

```bash
tide-mcp                  # stdio (default)
tide-mcp --transport sse  # SSE for web clients
```

</details>

**暴露的 MCP tools（36）：** `list_skills`, `load_skill`, `start_research_goal`, `get_research_goal`, `add_goal_evidence`, `update_research_goal_status`, `backtest`, `factor_analysis`, `analyze_options`, `pattern_recognition`, `read_url`, `read_document`, `web_search`, `write_file`, `read_file`, `list_swarm_presets`, `run_swarm`, `get_market_data`, `get_swarm_status`, `get_run_result`, `list_runs`, `reap_stale_runs`, `retry_run`, `analyze_trade_journal`, `extract_shadow_strategy`, `run_shadow_backtest`, `render_shadow_report`, `scan_shadow_signals`, `trading_connections`, `trading_select_connection`, `trading_check`, `trading_account`, `trading_positions`, `trading_orders`, `trading_quote`, `trading_history`.

<details>
<summary><b>从 ClawHub 安装（一条命令）</b></summary>

```bash
npx clawhub@latest install tide --force
```

> 由于该 skill 引用了外部 API，会触发 VirusTotal 自动扫描，因此需要 `--force`。代码完全开源，可自行检查。

这会将 skill + MCP config 下载到你的智能体 skills 目录。无需 clone。

在 ClawHub 浏览：[clawhub.ai/skills/tide](https://clawhub.ai/skills/tide)

</details>

<details>
<summary><b>OpenSpace — 自进化金融能力集成</b></summary>

全部 77 个 finance skills 都发布在 [open-space.cloud](https://open-space.cloud)，并通过 OpenSpace 的自进化引擎自主演进。

要配合 OpenSpace 使用，请将两个 MCP servers 都加入你的 agent config：

```json
{
  "mcpServers": {
    "openspace": {
      "command": "openspace-mcp",
      "toolTimeout": 600,
      "env": {
        "OPENSPACE_HOST_SKILL_DIRS": "/path/to/tide/agent/src/skills",
        "OPENSPACE_WORKSPACE": "/path/to/OpenSpace"
      }
    },
    "tide": {
      "command": "tide-mcp"
    }
  }
}
```

OpenSpace 会自动发现全部 77 个 skills，启用 auto-fix、auto-improve 和社区分享。在任意已连接 OpenSpace 的智能体中，可通过 `search_skills("finance backtest")` 搜索 TideTrading skills。

</details>

---

</details>

## 📁 项目结构

为保持主 README 易读，详细的项目源码与目录结构折叠在下方。

<details>
<summary><b>📁 项目源码与目录结构（点击展开）</b></summary>

```
TideTrading/
├── agent/                          # 后端（Python）
│   ├── cli/                        # CLI 包 —— 交互式 TUI + 子命令
│   ├── api_server.py               # FastAPI server —— runs、sessions、upload、swarm、SSE
│   ├── mcp_server.py               # MCP server —— 36 个工具，面向 OpenClaw / Claude Desktop
│   │
│   ├── src/
│   │   ├── agent/                  # ReAct agent 内核
│   │   │   ├── loop.py             #   5 层上下文压缩 + 读/写工具批处理
│   │   │   ├── context.py          #   system prompt + 持久记忆自动召回
│   │   │   ├── skills.py           #   skill loader（77 个内置 + 通过 CRUD 创建的用户 skill）
│   │   │   ├── tools.py            #   tool 基类 + 注册表
│   │   │   ├── memory.py           #   每个 run 的轻量 workspace 状态
│   │   │   ├── frontmatter.py      #   共享 safety YAML frontmatter
│   │   │   └── trace.py            #   执行 trace 写入器
│   │   │
│   │   ├── memory/                 # 跨 session 持久记忆
│   │   │   └── persistent.py       #   基于文件的记忆（~/.tide/memory/）
│   │   │
│   │   ├── tools/                  # 31 个自动发现的 agent 工具
│   │   │   ├── backtest_tool.py    #   运行回测
│   │   │   ├── remember_tool.py    #   跨 session 记忆（save/recall/forget）
│   │   │   ├── skill_writer_tool.py #  skill CRUD（save/patch/delete/file）
│   │   │   ├── session_search_tool.py # FTS5 跨 session 搜索
│   │   │   ├── swarm_tool.py       #   启动 swarm team
│   │   │   ├── web_search_tool.py  #   DuckDuckGo 网络搜索
│   │   │   └── ...                 #   bash、文件 I/O、因子分析、期权、alpha 浏览 + 横评等
│   │   │
│   │   ├── factors/                # Alpha Zoo —— 4 个 zoo 共 452 个 alpha
│   │   │   ├── base.py             #   19 个算子（rank/scale/ts_*/delta/decay_linear/safe_div/vwap）
│   │   │   ├── registry.py         #   纯 AST 元数据加载 + 惰性计算 + sanity 校验
│   │   │   ├── bench_runner.py     #   IC + alive/reversed/dead 分类
│   │   │   └── zoo/                #   qlib158 (154) + alpha101 (101) + gtja191 (191) + academic (6)
│   │   │
│   │   ├── api/                    # FastAPI 路由模块
│   │   │   └── alpha_routes.py     #   /alpha/list、/alpha/{id}、/alpha/bench、SSE 流
│   │   │
│   │   ├── skills/                 # 8 个类别共 77 个 finance skills（每个一份 SKILL.md）
│   │   ├── swarm/                  # Swarm DAG 执行引擎
│   │   │   └── presets/            #   29 个 swarm preset YAML 定义
│   │   ├── session/                # 多轮对话 + FTS5 session 搜索
│   │   └── providers/              # LLM provider 抽象层
│   │
│   └── backtest/                   # 回测引擎
│       ├── engines/                #   7 个引擎 + 跨市场 composite 引擎 + options_portfolio
│       ├── loaders/                #   7 个数据源：tushare、okx、yfinance、akshare、mootdx、ccxt、futu
│       │   ├── base.py             #   DataLoader Protocol
│       │   └── registry.py         #   Registry + 自动 fallback 链路
│       └── optimizers/             #   MVO、equal vol、max div、risk parity
│
├── frontend/                       # Web UI（React 19 + Vite + TypeScript）
│   └── src/
│       ├── pages/                  #   Home、Agent、AlphaZoo、RunDetail、Compare、Correlation、Settings
│       ├── components/             #   chat、charts、layout
│       └── stores/                 #   Zustand 状态管理
│
├── Dockerfile                      # 多阶段构建
├── docker-compose.yml              # 一条命令部署
├── pyproject.toml                  # 包配置 + CLI entrypoint
├── tools/                          # 仓库级 CI 辅助脚本
│   └── ci_grep_gates.sh            # 拦截 yaml.load / 商标 / 个股数据泄露
└── LICENSE                         # MIT
```

</details>

---




## 参与贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

**Good first issues** 使用 [`good first issue`](https://github.com/skloxo/TideTrading/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 标记，可选择一个开始。

想贡献更大的内容？请查看上方 [Roadmap](#-roadmap)，并在开始前先开 issue 讨论。

---

## 贡献者致谢

感谢所有为 TideTrading 做出贡献的人！

近期 v0.1.9 周期贡献者与致谢：

- @toanalien — session JSONL 崩溃加固 (#147)、迭代预算用尽时优雅退出 (#148)、LLM 生成 signal engine 的预检校验 (#149)、跨浏览器 Full Report 链接 (#150)
- @ai7eam-dev — 跨市场相关性时间戳对齐 (#158),以及会话运行状态指示器 + swarm 重试 (#159 → #160)
- @shadowinlife — 通过 SSE/HTTP 的远程 MCP server (#125),以及 swarm worker 中 operator 配置的外部 MCP 工具 (#142)
- @DoubleSky123 — 可配置 SSE idle timeout (#157)
- @ArthurXi — Web composer 的 IME 回车提交处理 (#146)
- @omcdecor-cyber — 上游任务失败时阻断下游的 swarm DAG (#145)
- @Soli22de — 带强制随机对照的严格 alpha-bench (#143)
- @ruok808 — CCXT loader 的 proxy 环境变量支持 (#126)
- @faizack — 远程 Ollama base URL 规范化 (#129)
- @fightZy — agent 会话历史加载修复 (#136)
- @lcwSeven — alpha list 接口接受短 universe 名 (#137)
- @Teerapat-Vatpitak — 解析后的 .env 来源日志 (#124)
- @warren618 / Haozhe Wu — connector-first 券商 profile、Robinhood Agentic Trading 通道、Research Goal 运行时、swarm reconcile + retry_run、agent/cli 重构、mootdx loader、发布集成



---

## 免责声明

TideTrading 是研究与交易辅助软件，不构成投资建议，不托管任何资金，也不运营执行场所。历史表现不代表未来结果，投资存在风险，请自行判断。

## 开源协议

MIT License — see [LICENSE](LICENSE)

---

<p align="center">
  感谢访问 <b>TideTrading</b> ✨
</p>