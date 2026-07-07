<p align="center">
  <a href="README.md">English</a> | <b>中文</b> | <a href="README_ja.md">日本語</a> | <a href="README_ko.md">한국어</a> | <a href="README_ar.md">العربية</a>
</p>

<p align="center">
  <img src="assets/icon.png" width="120" alt="TideTrading Logo"/>
</p>

<h1 align="center">TideTrading：你的个人交易智能体</h1>

<p align="center">
  <b>一条命令，让你的智能体具备完整交易研究能力</b>
</p>

<p align="center">
  <a href="https://trendshift.io/repositories/25527" target="_blank"><img src="https://trendshift.io/api/badge/repositories/25527" alt="HKUDS%2FTideTrading | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat" alt="FastAPI">
  <img src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=flat&logo=react&logoColor=white" alt="React">
  <a href="https://pypi.org/project/tide-trading-ai/"><img src="https://img.shields.io/pypi/v/tide-trading-ai?style=flat&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat" alt="License"></a>
  <a href="https://github.com/skloxo/TideTrading/actions/workflows/test.yml"><img src="https://github.com/skloxo/TideTrading/actions/workflows/test.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/skloxo/TideTrading/actions/workflows/docker-publish.yml"><img src="https://github.com/skloxo/TideTrading/actions/workflows/docker-publish.yml/badge.svg" alt="Docker Build Status"></a>
  <br>
  <a href="https://github.com/HKUDS/.github/blob/main/profile/README.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat-square&logo=feishu&logoColor=white" alt="Feishu"></a>
  <a href="https://github.com/HKUDS/.github/blob/main/profile/README.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat-square&logo=wechat&logoColor=white" alt="WeChat"></a>
  <a href="https://discord.gg/6TdQnT5xcF"><img src="https://img.shields.io/badge/Discord-Join-7289DA?style=flat-square&logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="https://codespaces.new/skloxo/TideTrading"><img src="https://github.com/codespaces/badge.svg" alt="Open in GitHub Codespaces" style="max-width: 100%;"></a>
</p>

<p align="center">
  <a href="https://vibetrading.wiki/">官网</a> &nbsp;&middot;&nbsp;
  <a href="https://vibetrading.wiki/docs/">文档</a> &nbsp;&middot;&nbsp;
  <a href="#-news">News</a> &nbsp;&middot;&nbsp;
  <a href="#-key-features">Features</a> &nbsp;&middot;&nbsp;
  <a href="#-shadow-account">Shadow Account</a> &nbsp;&middot;&nbsp;
  <a href="#-demo">Demo</a> &nbsp;&middot;&nbsp;
  <a href="#-quick-start">Quick Start</a> &nbsp;&middot;&nbsp;
  <a href="#-examples">Examples</a> &nbsp;&middot;&nbsp;
  <a href="#-api-server">API / MCP</a> &nbsp;&middot;&nbsp;
  <a href="#-roadmap">Roadmap</a> &nbsp;&middot;&nbsp;
  <a href="#-contributing">Contributing</a>
</p>

<p align="center">
  <a href="#-quick-start"><img src="assets/pip-install.svg" height="45" alt="pip install tide-trading-ai"></a>
</p>

---

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

## ✨ Key Features

<div align="center">
<table align="center" width="94%" style="width:94%; margin-left:auto; margin-right:auto;">
  <tr>
    <td align="center" width="50%" valign="top">
      <img src="assets/feature-self-improving-trading-agent.png" height="130" alt="Self-improving trading agent"/><br>
      <h3>🔍 自我改进的交易智能体</h3>
      <div align="left">
        • 自然语言市场研究<br>
        • 策略草稿与文件/网页分析<br>
        • 由记忆驱动的研究工作流
      </div>
    </td>
    <td align="center" width="50%" valign="top">
      <img src="assets/feature-multi-agent-trading-teams.png" height="130" alt="Multi-agent trading teams"/><br>
      <h3>🐝 多智能体交易团队</h3>
      <div align="left">
        • 投资、量化、加密与风控团队<br>
        • 流式进度与持久化报告<br>
        • Worker 基于已获取的市场数据展开分析
      </div>
    </td>
  </tr>
  <tr>
    <td align="center" width="50%" valign="top">
      <img src="assets/feature-cross-market-data-backtesting.png" height="130" alt="Cross-market data and backtesting"/><br>
      <h3>📊 全球市场数据与回测</h3>
      <div align="left">
        • <b>全球覆盖</b>：A 股、港股、美股、加密货币、期货与外汇<br>
        • <b>券商完整</b>：10 个券商连接器（OKX, Binance, Alpaca, IBKR 等）全部可用并加固<br>
        • 多层数据 fallback 与跨市场组合回测<br>
        • PIT 数据、验证 artifacts 与 run cards
      </div>
    </td>
    <td align="center" width="50%" valign="top">
      <img src="assets/feature-shadow-account.png" height="130" alt="Shadow Account"/><br>
      <h3>👥 Shadow Account</h3>
      <div align="left">
        • 券商交易日志行为诊断<br>
        • 基于规则的 Shadow Account 对比<br>
        • 可导出的审计报告与策略代码
      </div>
    </td>
  </tr>
</table>
</div>

## 💡 What Is TideTrading?

TideTrading 是一个开源研究工作台，用于把金融问题转化为可运行的分析。它将自然语言提示连接到市场数据加载器、策略生成、回测引擎、报告、导出和持久研究记忆。

它面向研究、模拟和回测——并且在你选择时，可通过你自己授权的券商（如 Robinhood Agentic Trading）进行自主交易。它不托管任何资金，绝不超出你设定的限额交易，且你可随时一键停止。

---

## ✨ What You Can Do

| 任务 | 输出 |
|------|------|
| **提出交易问题** | 结合工具、数据、文档和可复用 session 上下文的市场研究。 |
| **回测策略想法** | 策略代码、指标、benchmark 上下文、验证 artifacts 和 run cards。 |
| **复盘自己的交易** | 券商日志解析、行为诊断、规则提取和 Shadow Account 对比。 |
| **改进重复研究** | 持久记忆和可编辑 skills 将有用流程变成可复用工作流。 |
| **运行分析师团队** | 面向投资、量化、加密、宏观和风控工作流的多智能体研究评审。 |
| **交付可用成果** | 报告、TradingView Pine Script、TDX、MetaTrader 5、MCP tools，以及可延续的研究 sessions。 |
| **跑预置 alpha zoo 横评** | 456 个 alpha 因子（Qlib 158 + Kakushadze 101 + GTJA 191 + FF5 + Carhart），一行 CLI 在你选的 universe 上算 IC + IR + alive/reversed/dead 分类 |

---

## ⚡ Quick Example

```bash
pip install tide-trading-ai

# 自然语言研究
tide run -p "Backtest a BTC-USDT 20/50 moving-average strategy for 2024, summarize return and drawdown, then export the report"

# 一行 CLI 跑预置 alpha zoo 横评
tide alpha bench --zoo gtja191 --universe csi300 --period 2018-2025 --top 20
```

```bash
tide --upload trades_export.csv
tide run -p "Analyze my trading behavior, extract my shadow strategy, and compare it with my actual trades"
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
tide run -p "Analyze my trading behavior, extract my shadow strategy, and compare it with my actual trades"
```

---

## 🧪 Research Workflow

多数运行都会遵循同一条证据路径：路由请求、加载正确的市场上下文、执行工具、验证输出，并保持 artifacts 可检查。

| 层 | 发生什么 |
|----|----------|
| **Plan** | 选择相关金融 skills、tools、数据源，以及在有帮助时选择 swarm preset。 |
| **Ground** | 通过可用 loader 拉取 A 股、港股/美股、加密、期货、外汇、文档或网页上下文。 |
| **Execute** | 生成可测试的策略代码，运行工具，并使用匹配的回测引擎或分析工作流。 |
| **Validate** | 在适用时加入指标、benchmark comparison、Monte Carlo、Bootstrap、Walk-Forward、run cards 和 warnings。 |
| **Deliver** | 返回报告、artifacts、tool traces，以及面向 TradingView、TDX、MetaTrader 5、MCP clients 或后续 sessions 的导出。 |

---

## 📡 数据源与智能 Fallback

一次 `get_market_data` 调用，**18 个行情数据源**。设 `source: "auto"`——loader 按符号自动选源，再沿按 **被封 IP 风险** 排序的同市场链向下走（永不封的公开源在前，限速 / 需 key 的在后）。零配置，无单点故障。

| Source | Markets | Auth | Role |
|--------|---------|------|------|
| `tencent` · `mootdx` | A-share | none | never IP-banned (`mootdx` = 通达信 TCP) |
| `eastmoney` | A / US / HK | none | OHLCV + deep fundamentals & flow tools (throttled) |
| `baostock` · `akshare` | A (+ US/HK/futures/macro/fx) | none | free fallbacks |
| `tushare` | A / futures / fund / macro | token | richest A-share |
| `yahoo` · `sina` · `stooq` | US (/HK) | none | direct chart/quotes/options · K-line to 1984 · EOD CSV |
| `yfinance` | US / HK | none | wrapper |
| `finnhub` · `alphavantage` · `tiingo` · `fmp` | US | key | optional providers |
| `okx` · `ccxt` | crypto | none | OKX + 100+ exchanges |
| `futu` | HK / A | OpenD | optional local FutuOpenD |
| `local` | any | none | your own CSV / Parquet / DuckDB via `local:` prefix |

**Fallback 链（按被封 IP 风险排序）：**

- **A股** → `tencent` · `mootdx` · `eastmoney` · `baostock` · `akshare` · `tushare` · `local`
- **美股** → `yahoo` · `stooq` · `sina` · `eastmoney` · `yfinance` · `tiingo` · `fmp` · `finnhub` · `alphavantage` · `akshare` · `local`
- **港股** → `eastmoney` · `yahoo` · `futu` · `yfinance` · `akshare` · `local`
- **加密** → `okx` · `ccxt` · `yfinance` · `local` &nbsp;·&nbsp; *(期货 / 基金 / 宏观 / 外汇 → `tushare`/`akshare` → `local`)*

除 OHLCV 外，**18 个只读数据工具**深入基本面与资金面——资金流、龙虎榜、北向、两融、大宗交易、股东户数、解禁、板块、研报、新闻、SEC 文件、财务报表、期权链、机构持仓、全市场筛选、代码搜索、宏观——全部经 MCP 暴露。显式 `local:` 源永不静默 fallback 到网络源。

---

## 🔩 Detailed Capabilities

为保持主 README 易读，详细清单折叠在下方。需要检查可用构件时可展开查看。

<details>
<summary><b>Finance Skill Library</b> <sub>8 个类别中的 79 个 skills</sub></summary>

- 📊 79 个专业金融 skills，分布在 8 个类别中
- 🌐 覆盖传统市场、加密与 DeFi
- 🔬 从数据源到量化研究的完整能力链路

| 类别 | Skills | 示例 |
|------|--------|------|
| Data Source | 9 | `data-routing`, `tushare`, `yfinance`, `okx-market`, `akshare`, `mootdx`, `ccxt`, `eastmoney`, `sec-edgar` |
| Strategy | 17 | `strategy-generate`, `cross-market-strategy`, `technical-basic`, `candlestick`, `ichimoku`, `elliott-wave`, `smc`, `multi-factor`, `ml-strategy` |
| Analysis | 17 | `factor-research`, `macro-analysis`, `global-macro`, `valuation-model`, `earnings-forecast`, `credit-analysis`, `dividend-analysis` |
| Asset Class | 9 | `options-strategy`, `options-advanced`, `convertible-bond`, `etf-analysis`, `asset-allocation`, `sector-rotation` |
| Crypto | 7 | `perp-funding-basis`, `liquidation-heatmap`, `stablecoin-flow`, `defi-yield`, `onchain-analysis` |
| Flow | 7 | `hk-connect-flow`, `us-etf-flow`, `edgar-sec-filings`, `financial-statement`, `adr-hshare` |
| Tool | 11 | `backtest-diagnose`, `report-generate`, `pine-script`, `doc-reader`, `web-reader`, `vnpy-export`, `alpha-zoo` |
| Risk Analysis | 1 | `ashare-pre-st-filter` |

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
<summary><b>Preset Trading Teams</b> <sub>29 个 swarm presets</sub></summary>

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
<summary><b>Alpha Zoo</b> <sub>456 个预置 alpha，覆盖 4 个 zoo</sub></summary>

- 🧬 456 个横截面 alpha，算子层即禁用 lookahead
- 📈 一条 CLI 命令完成 IC + IR + alive/reversed/dead 分类
- 🔬 AST 纯函数门禁 + 300 行 lookahead 哨兵测试 + `pytest-socket` 网络阻断
- 📦 Qlib 部分附 Apache-2 出处声明；每个 zoo 一份 `LICENSE.md`，声明公式属于数学内容
- 🤝 社区 PR 走 Developer Certificate of Origin (DCO) 签名流程

| Zoo | 数量 | 来源 | 许可 |
|-----|------|------|------|
| **qlib158** | 154 | Microsoft Qlib `Alpha158`（Apache-2.0，锁定 commit） | Apache-2.0 |
| **alpha101** | 101 | Kakushadze (2015), "101 Formulaic Alphas", arXiv:1601.00991 | 公式属于数学内容 |
| **gtja191** | 191 | 国君证券 (2014)《191 个短周期交易型 alpha 因子》研报 | 公式属于数学内容 |
| **academic** | 10 | Fama-French 5 因子 + Carhart 动量（基于价格的代理实现） + Jegadeesh reversal + George-Hwang 52-week-high + Amihud illiquidity + Harvey-Siddique skew | 公开学术文献 |

运行 `tide alpha list` 浏览全部因子，`tide alpha show <id>` 查看公式与源码，`tide alpha bench --zoo X --universe Y --period Z` 给一整个 zoo 打分。

</details>

## 🎬 Demo

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
<td colspan="2" align="center"><sub>☝️ 自然语言回测与多智能体 swarm 辩论 — Web UI + CLI</sub></td>
</tr>
</table>
</div>

---

## 🚀 Quick Start

### 一行安装（PyPI）

```bash
pip install tide-trading-ai
```

然后运行第一个研究任务：

```bash
tide init
tide run -p "Backtest a BTC-USDT 20/50 moving-average strategy for 2024 and summarize return and drawdown"
```

> **从旧版本升级？** 0.1.10 升级到了 LangChain 1.x。若在 0.1.10 之前的安装上执行 `pip install -U tide-trading-ai` 后导入报错（例如 langgraph 无法导入），请重建 venv 或运行 `pip install --force-reinstall tide-trading-ai`。全新安装不受影响。

> **包名与命令：** PyPI 包名是 `tide-trading-ai`。安装后会获得三个命令：
>
> | 命令 | 用途 |
> |------|------|
> | `tide` | 交互式 CLI / TUI |
> | `tide serve` | 启动 FastAPI web server |
> | `tide-mcp` | 启动 MCP server（用于 Claude Desktop、OpenClaw、Cursor 等） |

```bash
tide init              # interactive .env setup
tide                   # launch CLI
tide serve --port 8899 # launch web UI
tide-mcp               # start MCP server (stdio)
```

### 或选择一种路径

| 路径 | 最适合 | 时间 |
|------|--------|------|
| **A. Docker** | 立即试用，零本地配置 | 2 min |
| **B. Local install** | 开发，完整 CLI 访问 | 5 min |
| **C. MCP plugin** | 接入你现有的智能体 | 3 min |
| **D. ClawHub** | 一条命令，无需 clone | 1 min |

### 前置条件

- 任意受支持 provider 的 **LLM API key**，或使用 **Ollama** 本地运行（无需 key）
- 路径 B 需要 **Python 3.11+**
- 路径 A 需要 **Docker**
- OpenAI Codex 也可通过 ChatGPT OAuth 使用：设置 `LANGCHAIN_PROVIDER=openai-codex`，然后运行 `tide provider login openai-codex`。它不使用 `OPENAI_API_KEY`。

> **支持的 LLM providers：** OpenRouter、OpenAI、DeepSeek、Gemini、Groq、DashScope/Qwen、Zhipu、Moonshot/Kimi、MiniMax、Xiaomi MIMO、Z.ai、Ollama（本地）。配置见 `.env.example`。

> **提示：** 由于自动 fallback，所有市场都可以在没有任何 API key 的情况下工作。yfinance（港/美股）、OKX（加密）、mootdx（A 股，TCP 直连不封 IP）和 AKShare（A 股、美股、港股、期货、外汇）都是免费的。Tushare token 是可选项 —— mootdx 是首选的免 token A 股 fallback，AKShare 作为覆盖更广的兜底。

### Path A: Docker（零配置）

```bash
git clone https://github.com/HKUDS/TideTrading.git
cd TideTrading
cp agent/.env.example agent/.env
# Edit agent/.env — uncomment your LLM provider and set API key
docker compose up --build
```

打开 `http://localhost:8899`。后端 + 前端在同一个容器中运行。

Docker 默认将后端发布在 `127.0.0.1:8899`，并以非 root 容器用户运行应用。如果你有意将 API 暴露到本机之外，请设置强 `API_AUTH_KEY`，并让客户端发送 `Authorization: Bearer <key>`。

### Path B: Local install

```bash
git clone https://github.com/HKUDS/TideTrading.git
cd TideTrading
python -m venv .venv

# Activate
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -e .
cp agent/.env.example agent/.env   # Edit — set your LLM provider API key
tide                       # Launch interactive TUI
```

<details>
<summary><b>启动 Web UI（可选）</b></summary>

```bash
# Terminal 1: API server
tide serve --port 8899

# Terminal 2: Frontend dev server
cd frontend && npm install && npm run dev
```

打开 `http://localhost:5899`。前端会将 API 调用代理到 `localhost:8899`。

**生产模式（单 server）：**

```bash
cd frontend && npm run build && cd ..
tide serve --port 8899     # FastAPI serves dist/ as static files
```

> [!NOTE]
> `tide serve` 绑定 `0.0.0.0`，但默认只信任 loopback：在**同一台机器**上打开 UI（`http://localhost:8899`）零配置即可用。若你从**另一台机器、虚拟机宿主机或局域网内的手机**访问，敏感接口会返回 `403`，聊天会提示 “Remote API access requires an API key”——请在 `agent/.env` 里设置一个强 `API_AUTH_KEY`，重启，并在 **Settings** 中输入同一个 key。（Docker Desktop 宿主网关场景：设 `VIBE_TRADING_TRUST_DOCKER_LOOPBACK=1` 并保持默认的 `127.0.0.1` 端口绑定。）

</details>

### Path C: MCP plugin

见下方 [MCP Plugin](#-mcp-plugin) 章节。

### Path D: ClawHub（一条命令）

```bash
npx clawhub@latest install tide --force
```

skill + MCP config 会下载到你的智能体 skills 目录。详情见 [ClawHub install](#-mcp-plugin)。

---

## 🧠 Environment Variables

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

### 🎯 Recommended Models

TideTrading 是高度依赖工具的智能体：skills、backtests、memory 和 swarms 都会通过工具调用流转。模型选择会直接决定智能体是实际使用工具，还是从训练数据中编造答案。

| 档位 | 示例 | 使用场景 |
|------|------|----------|
| **Best** | `anthropic/claude-opus-4.7`, `anthropic/claude-sonnet-4.6`, `openai/gpt-5.5-pro`, `google/gemini-3.5-flash` | 复杂 swarms（3+ agents）、长研究 sessions、论文级分析 |
| **Sweet spot**（默认） | `deepseek-v4-pro`, `deepseek/deepseek-v4-pro`, `x-ai/grok-4.20`, `z-ai/glm-5.1`, `moonshotai/kimi-k2.6`, `qwen/qwen3-max-thinking` | 日常主力，约 1/10 成本下具备可靠工具调用 |
| **避免用于 agent** | `*-nano`, `*-flash-lite`, `*-coder-next`, 小型 / 蒸馏变体 | 工具调用不可靠，智能体会看起来像是在“凭记忆回答”，而不是加载 skills 或运行回测 |

默认 `agent/.env.example` 使用 DeepSeek 官方 API + `deepseek-v4-pro`；OpenRouter 用户可以使用 `deepseek/deepseek-v4-pro`。

---

## 🖥 CLI Reference

```bash
tide               # interactive TUI
tide run -p "..."  # single run
tide serve         # API server
tide alpha list    # 浏览 456 个预置 alpha；支持 show / bench / compare / export-manifest 子命令
```

<details>
<summary><b>TUI 内 slash commands</b></summary>

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有命令 |
| `/skills` | 列出全部 79 个 finance skills |
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
<summary><b>Single run 与 flags</b></summary>

```bash
tide run -p "Backtest BTC-USDT MACD strategy, last 30 days"
tide run -p "Analyze AAPL momentum" --json
tide run -f strategy.txt
echo "Backtest 000001.SZ RSI" | tide run
```

```bash
tide -p "your prompt"
tide --skills
tide --swarm-presets
tide --swarm-run investment_committee '{"topic":"BTC outlook"}'
tide --list
tide --show <run_id>
tide --code <run_id>
tide --pine <run_id>           # Export indicators (TradingView + TDX + MT5)
tide --trace <run_id>
tide --continue <run_id> "refine the strategy"
tide --upload report.pdf
tide alpha list --zoo gtja191 --limit 10
tide alpha show gtja191_171
tide alpha bench --zoo gtja191 --universe csi300 --period 2018-2025 --top 20
```

</details>

---

## 💡 Examples

### Strategy & Backtesting

```bash
# Moving average crossover on US equities
tide run -p "Backtest a 20/50-day moving average crossover on AAPL for the past year, show Sharpe ratio and max drawdown"

# RSI mean-reversion on crypto
tide run -p "Test RSI(14) mean-reversion on BTC-USDT: buy below 30, sell above 70, last 6 months"

# Multi-factor strategy on A-shares
tide run -p "Backtest a momentum + value + quality multi-factor strategy on CSI 300 constituents over 2 years"

# After backtesting, export to TradingView / TDX / MetaTrader 5
tide --pine <run_id>
```

**一行命令横评预置 alpha zoo**：
```bash
tide alpha bench --zoo gtja191 --universe csi300 --period 2018-2025 --top 20
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

### Market Research

```bash
# Equity deep-dive
tide run -p "Research NVDA: earnings trend, analyst consensus, option flow, and key risks for next quarter"

# Macro analysis
tide run -p "Analyze the current Fed rate path, USD strength, and impact on EM equities and gold"

# Crypto on-chain
tide run -p "Deep dive BTC on-chain: whale flows, exchange balances, miner activity, and funding rates"
```

### Swarm Workflows

```bash
# Bull/bear debate on a stock
tide --swarm-run investment_committee '{"topic": "Is TSLA a buy at current levels?"}'

# Quant strategy from screening to backtest
tide --swarm-run quant_strategy_desk '{"universe": "S&P 500", "horizon": "3 months"}'

# Crypto desk: funding + liquidation + flow → risk manager
tide --swarm-run crypto_trading_desk '{"asset": "ETH-USDT", "timeframe": "1w"}'

# Global macro portfolio allocation
tide --swarm-run macro_rates_fx_desk '{"focus": "Fed pivot impact on EM bonds"}'
```

### Cross-Session Memory

```bash
# Save your preferences once
tide run -p "Remember: I prefer RSI-based strategies, max 10% drawdown, hold period 5–20 days"

# The agent recalls them in future sessions automatically
tide run -p "Build a crypto strategy that fits my risk profile"
```

### Upload & Analyze Documents

```bash
# Analyze a broker export or earnings report
tide --upload trades_export.csv
tide run -p "Profile my trading behavior and identify any biases"

tide --upload NVDA_Q1_earnings.pdf
tide run -p "Summarize the key risks and beats/misses from this earnings report"
```

---

## 🌐 API Server

```bash
tide serve --port 8899
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
| `POST` | `/scheduled-runs` | 创建定时研究任务（间隔毫秒或 cron） |
| `GET` | `/scheduled-runs` | 列出定时任务 |
| `DELETE` | `/scheduled-runs/{job_id}` | 取消定时任务 |

交互式文档：`http://localhost:8899/docs`

### Security defaults

对于 localhost 开发，`tide serve` 会保持浏览器工作流简单。对任何非本地客户端，敏感 API endpoints 都要求 `API_AUTH_KEY`；JSON/upload 请求请使用 `Authorization: Bearer <key>`。浏览器 EventSource streams 会在你于 Settings 中输入同一个 key 后由 Web UI 处理。

Shell-capable tools 可用于本地 CLI 与可信 localhost 工作流，但不会暴露给远程 API sessions，除非你显式设置 `VIBE_TRADING_ENABLE_SHELL_TOOLS=1`。文档和日志读取器默认限制在 upload/import roots 内；请将文件放在 `agent/uploads`、`agent/runs`、`./uploads`、`./data`、`~/.tide/uploads` 或 `~/.tide/imports` 下，或通过 `VIBE_TRADING_ALLOWED_FILE_ROOTS` 添加专用目录。

### Web UI Settings

Web UI Settings 页面允许本地用户更新 LLM provider/model、base URL、generation parameters、reasoning effort，以及 Tushare token 等可选市场数据凭据。Settings 会持久化到 `agent/.env`；provider defaults 从 `agent/src/providers/llm_providers.json` 加载。

Settings 读取无副作用：`GET /settings/llm` 和 `GET /settings/data-sources` 永远不会创建 `agent/.env`，并且只返回项目相对路径。Settings 读写可能暴露凭据状态或更新凭据/运行时环境，因此在配置了 `API_AUTH_KEY` 时会要求认证。如果 dev mode 下未设置 `API_AUTH_KEY`，settings 访问只接受 loopback clients。

### 定时研究（Scheduled research）

让研究 prompt 或回测按固定周期重复运行。后台执行器**默认关闭**——启动服务时设置 `VIBE_TRADING_ENABLE_SCHEDULER=1` 才会开启：

```bash
VIBE_TRADING_ENABLE_SCHEDULER=1 tide serve --port 8899
```

然后通过 REST 创建任务。`schedule` 可以是纯整数（间隔**毫秒**）或 5 段 cron 表达式（`分 时 日 月 周`）：

```bash
# 每 6 小时（cron）
curl -X POST http://localhost:8899/scheduled-runs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Scan CSI300 for momentum breakouts and backtest the top 5","schedule":"0 */6 * * *"}'

# 列出 / 取消
curl http://localhost:8899/scheduled-runs
curl -X DELETE http://localhost:8899/scheduled-runs/<job_id>
```

每次触发都会在一个全新的 agent session 中运行该 `prompt`（可选回测参数放在 `config` 里），任务持久化到 `~/.tide/`，重启后依然保留。不设这个开关时，`/scheduled-runs` 端点仍会记录任务，但不会真正触发。配置了 `API_AUTH_KEY` 时，每次请求需加 `-H "Authorization: Bearer <key>"`。

---

## 🔌 MCP Plugin

TideTrading 为任何 MCP-compatible client 暴露 54 个 MCP tools。它作为 stdio subprocess 运行，无需 server setup。核心 research tools 对港股/美股/加密零 API key 可用；trading connector tools 使用当前选择的 connector profile；只有 `run_swarm` 需要 LLM key。

<details>
<summary><b>Claude Desktop</b></summary>

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
<summary><b>OpenClaw</b></summary>

添加到 `~/.openclaw/config.yaml`：

```yaml
skills:
  - name: tide
    command: tide-mcp
```

</details>

<details>
<summary><b>Cursor / Windsurf / other MCP clients</b></summary>

```bash
tide-mcp                  # stdio (default)
tide-mcp --transport sse  # SSE for web clients
```

</details>

**暴露的 MCP tools（54）：** `list_skills`, `load_skill`, `start_research_goal`, `get_research_goal`, `add_goal_evidence`, `update_research_goal_status`, `backtest`, `factor_analysis`, `analyze_options`, `pattern_recognition`, `read_url`, `read_document`, `web_search`, `write_file`, `read_file`, `list_swarm_presets`, `run_swarm`, `get_market_data`, `get_fund_flow`, `get_dragon_tiger`, `get_northbound_flow`, `get_margin_trading`, `get_block_trades`, `get_shareholder_count`, `get_lockup_expiry`, `get_sector_info`, `get_research_reports`, `get_stock_news`, `get_sec_filings`, `get_financial_statements`, `get_options_chain`, `get_stock_profile`, `screen_market`, `search_symbol`, `get_macro_series`, `iwencai_search`, `get_swarm_status`, `get_run_result`, `list_runs`, `reap_stale_runs`, `retry_run`, `analyze_trade_journal`, `extract_shadow_strategy`, `run_shadow_backtest`, `render_shadow_report`, `scan_shadow_signals`, `trading_connections`, `trading_select_connection`, `trading_check`, `trading_account`, `trading_positions`, `trading_orders`, `trading_quote`, `trading_history`.

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
<summary><b>OpenSpace — 自进化 skills</b></summary>

全部 79 个 finance skills 都发布在 [open-space.cloud](https://open-space.cloud)，并通过 OpenSpace 的自进化引擎自主演进。

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

OpenSpace 会自动发现全部 79 个 skills，启用 auto-fix、auto-improve 和社区分享。在任意已连接 OpenSpace 的智能体中，可通过 `search_skills("finance backtest")` 搜索 TideTrading skills。

</details>

---

## 📁 Project Structure

<details>
<summary><b>点击展开</b></summary>

```
TideTrading/
├── agent/                          # 后端（Python）
│   ├── cli/                        # CLI 包 —— 交互式 TUI + 子命令
│   ├── api_server.py               # FastAPI server —— runs、sessions、upload、swarm、SSE
│   ├── mcp_server.py               # MCP server —— 54 个工具，面向 OpenClaw / Claude Desktop
│   │
│   ├── src/
│   │   ├── agent/                  # ReAct agent 内核
│   │   │   ├── loop.py             #   5 层上下文压缩 + 读/写工具批处理
│   │   │   ├── context.py          #   system prompt + 持久记忆自动召回
│   │   │   ├── skills.py           #   skill loader（79 个内置 + 通过 CRUD 创建的用户 skill）
│   │   │   ├── tools.py            #   tool 基类 + 注册表
│   │   │   ├── memory.py           #   每个 run 的轻量 workspace 状态
│   │   │   ├── frontmatter.py      #   共享的 YAML frontmatter 解析器
│   │   │   └── trace.py            #   执行 trace 写入器
│   │   │
│   │   ├── memory/                 # 跨 session 持久记忆
│   │   │   └── persistent.py       #   基于文件的记忆（~/.tide/memory/）
│   │   │
│   │   ├── tools/                  # 68 个自动发现的 agent 工具
│   │   │   ├── backtest_tool.py    #   运行回测
│   │   │   ├── remember_tool.py    #   跨 session 记忆（save/recall/forget）
│   │   │   ├── skill_writer_tool.py #  skill CRUD（save/patch/delete/file）
│   │   │   ├── session_search_tool.py # FTS5 跨 session 搜索
│   │   │   ├── swarm_tool.py       #   启动 swarm team
│   │   │   ├── web_search_tool.py  #   DuckDuckGo 网络搜索
│   │   │   └── ...                 #   bash、文件 I/O、因子分析、期权、alpha 浏览 + 横评等
│   │   │
│   │   ├── factors/                # Alpha Zoo —— 4 个 zoo 共 456 个 alpha
│   │   │   ├── base.py             #   19 个算子（rank/scale/ts_*/delta/decay_linear/safe_div/vwap）
│   │   │   ├── registry.py         #   纯 AST 元数据加载 + 惰性计算 + sanity 校验
│   │   │   ├── bench_runner.py     #   IC + alive/reversed/dead 分类
│   │   │   └── zoo/                #   qlib158 (154) + alpha101 (101) + gtja191 (191) + academic (10)
│   │   │
│   │   ├── api/                    # FastAPI 路由模块
│   │   │   └── alpha_routes.py     #   /alpha/list、/alpha/{id}、/alpha/bench、SSE 流
│   │   │
│   │   ├── skills/                 # 8 个类别共 79 个 finance skills（每个一份 SKILL.md）
│   │   ├── swarm/                  # Swarm DAG 执行引擎
│   │   │   └── presets/            #   29 个 swarm preset YAML 定义
│   │   ├── session/                # 多轮对话 + FTS5 session 搜索
│   │   └── providers/              # LLM provider 抽象层
│   │
│   └── backtest/                   # 回测引擎
│       ├── engines/                #   7 个引擎 + 跨市场 composite 引擎 + options_portfolio
│       ├── loaders/                #   18 个数据源：tushare、okx、yfinance、akshare、baostock、tencent、mootdx、ccxt、futu、local、eastmoney、sina、stooq、yahoo、finnhub、alphavantage、tiingo、fmp
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

## 🏛 Ecosystem

TideTrading 是 **[HKUDS](https://github.com/HKUDS)** 智能体生态的一部分：

<table>
  <tr>
    <td align="center" width="20%">
      <a href="https://github.com/HKUDS/nanobot"><b>NanoBot</b></a><br>
      <sub>Ultra-Lightweight Personal AI Assistant</sub>
    </td>
    <td align="center" width="20%">
      <a href="https://github.com/HKUDS/AI-Trader"><b>AI-Trader</b></a><br>
      <sub>Agent-Native Signal &amp; Copy Trading Platform</sub>
    </td>
    <td align="center" width="20%">
      <a href="https://github.com/HKUDS/CLI-Anything"><b>CLI-Anything</b></a><br>
      <sub>Making All Software Agent-Native</sub>
    </td>
    <td align="center" width="20%">
      <a href="https://github.com/HKUDS/OpenSpace"><b>OpenSpace</b></a><br>
      <sub>Self-Evolving AI Agent Skills</sub>
    </td>
    <td align="center" width="20%">
      <a href="https://github.com/HKUDS/ClawTeam"><b>ClawTeam</b></a><br>
      <sub>Agent Swarm Intelligence</sub>
    </td>
  </tr>
</table>

---

## 🗺 Roadmap

> 我们按阶段交付。工作开始时，条目会移动到 [Issues](https://github.com/HKUDS/TideTrading/issues)。

| 阶段 | 功能 | 状态 |
|------|------|------|
| **Trust Layer** | 可复现 run cards 已输出并展示在 Run Detail；v1 会补充 tool traces 与 citations | v0 已发布 |
| **Hypothesis Registry** | 持久化研究假设：lifecycle status、data sources、skills、run-card links 与 invalidation notes | Backend MVP 已发布 |
| **Research Autopilot** | 手动触发优先的研究循环：hypothesis → deterministic backtest → evidence report | 第 1–3 阶段已发布 |
| **Data Bridge** | 自带数据：本地 CSV/Parquet/SQL connectors 与 schema mapping | 本地加载器已发布 |
| **Options Lab** | Vol surface、Greeks dashboard、payoff/scenario explorer | Planned |
| **Portfolio Studio** | Risk x-ray、constraints、turnover-aware optimizer、rebalance notes | Planned |
| **Alpha Zoo** | 452 个预置 alpha 因子（Qlib 158 + Kakushadze 101 + GTJA 191 + FF5 + Carhart），一行 CLI 跑横评，agent 集成，Web UI 浏览 | **已发布 0.1.8** |
| **Research Delivery** | 定时 briefs 到 Slack / Telegram / email-style channels | 调度器已发布 |
| **Community** | 可分享的 skills、presets 和 strategy cards | Exploring |

---

## Contributing

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

**Good first issues** 使用 [`good first issue`](https://github.com/HKUDS/TideTrading/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 标记，可选择一个开始。

想贡献更大的内容？请查看上方 [Roadmap](#-roadmap)，并在开始前先开 issue 讨论。

---

## Contributors

感谢所有为 TideTrading 做出贡献的人！

近期 v0.1.10 周期贡献者与致谢：

- @Hinotoi-agent — 一波安全加固：本地关停鉴权 (#241)、回环主机重绑定拒绝 (#242)、agent shell 工具显式开启 (#243)、设置写入鉴权 (#245)、mandate proposal-id 收敛 (#256)、持久记忆类型校验 (#257)、MCP swarm run-id 收敛 (#258)
- @mvanhorn — 可选本地数据缓存 (#177)、Gemini thoughtSignature 经 OpenAI-compat 工具调用往返 (#176)、自定义数据源指南 (#194)、glm/zhipu provider 别名 + 模型名推断 (#247)
- @gyx09212214-prog — loader 容忍畸形 crypto/RSSHub 超时环境变量 (#227、#240)、yfinance 包含请求的结束日期 (#226)、run-card 非有限指标的严格 JSON (#238)、ddgs 重试 fallback 覆盖 (#239)
- @BillDin — 聊天界面显示 swarm agent 状态 (#188)、显式 preset 名处理 (#189)、swarm worker 的 loader 行情工具 (#199)、preset 上下文延续 (#200)
- @Robin1987China — Research Autopilot 假设-目标桥 (#260)、本地 CSV/Parquet/DuckDB 数据加载器 (#252)、assistant-prefill 修复 + 可配置 Kimi User-Agent (#248)
- @LemonCANDY42 — 只读运行时状态面板 (#210)、持久化 AgentLoop 用量产物 (#223)、可选 Run Detail 图表负载 (#225)
- @zwrong — trace.jsonl 零截断 + offload 改造 (#206)、退出时显示 session-id + `resume <session-id>` (#218)
- @forge-builder — AI 贡献者指南 (#173)、OpenClaw MCP 只读冒烟测试文档 (#165)
- @skloxo — 中文 (zh-CN) 前端本地化（采纳自 #217）
- @LeeCQiang — 全部 452 个 Alpha Zoo 因子的中文 docstring (#180)
- @KaiLuettmann — 发布时发布 GHCR 预构建镜像 (#187)
- @ngoanpv — 经 AgentLoop dict 路径保留 Gemini thought_signature (#184)
- @ShahNewazKhan — 经 host.docker.internal 触达宿主 Ollama (#196)
- @sambazhu — 前端同步已完成的聊天 attempts (#236)
- @bhlt — baostock 原生代码格式支持 (#230)
- @octo-patch — MiniMax M3 默认模型升级 (#162)
- @warren618 / Haozhe Wu — 全球数据层（8 源 + 18 只读数据工具）、10 个券商 SDK 连接器、alpha compare 全栈、provider 可靠性大修、多引擎 web_search fallback、响应式 Stop + SSE 重连、发布集成

<a href="https://github.com/HKUDS/TideTrading/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/TideTrading" />
</a>

---

## Disclaimer

TideTrading 是研究与交易软件。它不是投资建议，不托管任何资金，也不运营执行场所。仅通过你自己明确授权的券商通道（如 Robinhood Agentic Trading）进行交易，且只在你设定的限额内、你可随时停止。该券商交易能力为实验性，未经我们对接真实券商账户验证——风险自负。历史表现不代表未来结果。

## License

MIT License — see [LICENSE](LICENSE)

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=HKUDS/TideTrading&type=Date)](https://star-history.com/#HKUDS/TideTrading&Date)

<p align="center">
  ⭐ 如果 <b>TideTrading</b> 对你的研究有帮助，点个 Star 让更多人看到它。
</p>

---

<p align="center">
  感谢访问 <b>TideTrading</b> ✨
</p>
<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.TideTrading&style=flat" alt="visitors"/>
</p>