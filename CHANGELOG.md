# Changelog

All notable changes to Vibe-Trading are documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

## [1.7.5.4] — 2026-07-07

### Added
- **多租户沙箱安全隔离**：彻底重构并隔离了非 default 租户的 Swarm 运行时、图谱可视化、详情日志、投研目标与 Autopilot 会话及 Trace 追踪工作区，并在 `path_utils.py` 中动态注入 uploads/runs 路径白名单解决权限报错。
- **全局持仓与收益共享缓存**：在组合详情拉取 API 中实装跨租户共享缓存，防止多用户监控同一标的时的重复接口调用。
- **Token 契约状态与推送联动**：过期或空订阅租户自动转入“监控停用状态”，剔除共享 token 并阻断通知推送。


## [0.1.10-s4] — 2026-07-02

### Added
- **共享与私有双层数据库分层架构**：彻底隔离了多租户的私有记录（自选股、策略回测日志与持仓）和系统全局的共享行情数据库（历史 K 线、基本面元数据与财务报表），保障高并发回测只读隔离安全。
- **550 万行通达信/同花顺本地二进制冷启动大灌注**：成功逆向解密 Windows 客户端历史 `.day` 价格行情文件，在容器内以 SQLite WAL 模式实现平均每秒 2.8 万条的高速增量填充，提供对沪深交易所、北交所 (BJ) 以及板块概念指数 (DS) 数据的完美解析支持。
- **并发写锁自愈保护**：导入大盘底座期间，自动越过短暂的 SQLite `database is locked` 锁碰撞，确保前台看板与回测引擎的正常读访问不中断。
- **首屏 i18n 强制中文预设**：为首次打开的访客自动注入 `zh-CN` 拦截，确保首屏以完全中文面板加载，并完美保存用户后续的手动语言偏好。


## [0.1.10-s2] — 2026-06-24

### Added
- **多通道飞书机器人设置与交互引导**：在设置页提供多飞书通道配置（CRUD）和可视化表单交互。
- **免权限 OpenID 反射命令**：允许用户在未配置白名单时，通过向飞书 Bot 发送 `/myid` 反射获取自己的 OpenID。
- **小白友好型调试模式**：根据公开调试模式自动展开或折叠 Allowed Users 录入框，并在启用公开调试时展示琥珀色安全警告横幅。

### Fixed
- **Lark-OAPI 多线程事件循环冲突**：通过 `LoopProxy` 代理 Lark SDK 事件循环全局属性，将各飞书 WebSocket 连接隔离到独立的线程与事件循环中，解决因共用主线程 Uvicorn 事件循环引发的 `RuntimeError`，恢复多通道 Bot 交互稳定性。

## [0.1.10-s1] — 2026-06-24

### Added
- **深度中文本地化**：精细化翻译了所有核心页面，包括欢迎页示例与模板提示词、Alpha 因子库分类与主题、相关性矩阵热力图及设置页面。
- **双子代理（开发/测试）协同测试与交付验收 SOP**：定义并落地了一套多智能体分工编写测试与异机交叉验证的标准作业程序。
- **安全性防护机制**：确立了本地敏感 credentials 凭证的隔离机制，加入 `.gitignore` 保护私有数据安全。

## [0.1.9] — 2026-06-01

### Added
- **Connector-first broker profiles (IBKR + Robinhood).** Trading access now
  starts from a selectable connector profile rather than separate broker/live
  entry points; `vibe-trading connector list/use/check/account/positions/orders/quote/history`
  and the MCP `trading_*` tools share the selected profile, with paper/live as
  a property under the connector. IBKR is usable immediately as a local
  read-only TWS / IB Gateway profile; the official IBKR remote MCP path is
  seeded as an OAuth `mcp.read` probe until stable read tool names ship.
  Robinhood Agentic Trading is a bounded connector behind OAuth, a committed
  mandate, an order guard, an audit ledger, and an instant halt switch.
- **Research Goal runtime.** Long-running, research-only goals with auditable
  checklist criteria, budgets, and a `/goal` CLI command, plus REST + MCP
  endpoints (`start_research_goal`, `get_research_goal`, `add_goal_evidence`,
  `update_research_goal_status`) and a Web `GoalDrawer`.
- **Swarm `retry_run`.** Re-launch a failed/stale/cancelled run with the
  original preset + variables; exposed as both `POST /swarm/runs/{id}/retry`
  and an MCP `retry_run` tool (the `list_runs → retry` loop). 36 MCP tools now.
- **Operator-configured external MCP tools in swarm workers** (#142) and
  **remote MCP transports** for the built-in agent.
- **`mootdx` A-share OHLCV loader** — native 通达信 TCP, no token, sits between
  tushare and akshare in the fallback chain. CCXT loader now reads proxy env
  for restricted networks (#126).
- **Hypothesis Registry CLI** — `list / show / invalidate`.
- **Strict alpha-bench mode** with a mandatory random control (#143).

### Changed
- **CLI split into the `agent/cli/` package** (from a 3216-LOC single file),
  with a refreshed interactive terminal UI (figlet banner + activity rail) and
  a single `cli/_version.py` version source.
- Swarm status reconciles from live task files on every read; `run_swarm`
  sends MCP progress heartbeats, and the stale-run reaper uses per-run
  thresholds (#132).
- Refreshed provider default model ids; bumped `langgraph` for CVE-2026-28277.

### Fixed
- **`--version` no longer drifts (#156).** The version derives from package
  metadata, falling back to reading `pyproject.toml` directly — no hardcoded
  constant left to forget on release.
- **Session running-status indicator** now survives reconnect / page reload /
  sidebar navigation; **swarm DAG** blocks downstream tasks when an upstream
  task fails (#145).
- **Robustness pass:** pre-flight validation for LLM-generated signal engines
  with clean JSON errors (#149), graceful agent-loop exit at the iteration
  budget instead of an output-less `failed` (#148), `flush + fsync` session
  message writes that skip corrupted JSONL lines on read (#147), and IME Enter
  handling in the Web composer (#146).
- **Full Report** link now always renders when a `runId` exists, even cross-browser
  (#150); SSE idle timeout is configurable via `VIBE_TRADING_SSE_TIMEOUT` (#157);
  cross-market correlation normalizes timestamps so crypto-vs-equity pairs align (#158).

## [0.1.8] — 2026-05-17

### Added — Alpha Zoo (450+ pre-built quant alphas)
- `agent/src/factors/` — base operators (`rank`, `scale`, `ts_*`, `delta`,
  `decay_linear`, `signed_power`, `safe_div`, market-aware `vwap`) and a
  registry that AST-extracts metadata from each alpha module without
  importing it. Lookahead is enforced at the operator level
  (`delta(d>=1)`), and registry sanity checks reject `+/-inf` and
  outputs that are more than 95 % NaN.
- 4 zoos shipping 452 alphas total:
  - **qlib158** (154 alphas) — port of Microsoft Qlib's `Alpha158`
    feature handler under Apache-2.0, with pinned commit SHA per file.
  - **alpha101** (101 alphas) — implementation of Kakushadze (2015)
    *"101 Formulaic Alphas"* (arXiv:1601.00991), written from the paper
    appendix; the relevant trademarked string is intentionally absent.
  - **gtja191** (191 alphas) — implementation of Guotai Junan's 2014
    *"191 Short-period Trading Alpha Factors"* research report.
  - **academic** (6 factors) — Fama-French 5 + Carhart momentum, shipped
    as honest price-based proxies (not the canonical FF series).
- `vibe-trading alpha {list,show,bench,compare,export-manifest}` CLI
  subcommand. `show` and `export-manifest` enforce path-traversal guards.
- New agent tools: `AlphaZooTool` (browse) and `AlphaBenchTool`
  (orchestrator with Jinja2 autoescape + strict CSP HTML report).
- `ZooSignalEngine.from_zoo(...)` — composite multi-factor signal engine
  with cross-sectional standardisation, weighting, and optional top-N /
  bottom-N long-short conversion.
- `wiki/scripts/build_alpha_library.py` — Alpha Library renderer.
  Reads `manifest.json` produced by `vibe-trading alpha export-manifest`
  and emits 452 per-alpha HTML pages plus 4 per-zoo overviews, each with
  `script-src 'none'` CSP. The landing page hydrates per-zoo counts
  from `content/index.json`.
- New blog post: *"Which of the 191 GTJA alphas still work in 2026?"*
  with aggregate IC statistics, theme breakdown, and the top alphas
  that survive eight years of out-of-sample data.

### Added — Web UI for Alpha Zoo
- New page at `/alpha-zoo` in the Vite + React frontend with three
  views: browse (4 zoo cards + filter bar + paginated table), detail
  (formula, metadata, collapsible source code), and bench-runner
  (form → SSE-streamed progress + Alive/Reversed/Dead stat cards +
  Top-5-by-IR table + by-theme breakdown chart). "Alpha Zoo" nav
  entry added to the layout.
- Four new REST routes in the FastAPI server:
  - `GET /alpha/list` — filterable alpha catalogue
  - `GET /alpha/{alpha_id}` — meta + source code
  - `POST /alpha/bench` — kicks off a background bench job and
    returns a `job_id`
  - `GET /alpha/bench/{job_id}/stream` — Server-Sent Events with
    `progress`, `result`, `done`, and `error` event types. In-memory
    job state with a 1-hour TTL; no Redis/Celery dependency.
- Bench math is refactored into `agent/src/factors/bench_runner.py`
  so the CLI driver (`agent/scripts/w4a_run_benches.py`) and the new
  API worker share a single implementation.

### Added — Safety floor
- `agent/tests/factors/test_alpha_purity.py` — AST allowlist scan over
  every `zoo/**/*.py` module (whitelist: pandas, numpy, scipy.\*,
  `src.factors.base`, `__future__`, `typing`, `math`, `dataclasses`;
  banned: `os`, `sys`, `subprocess`, `socket`, `urllib`, `requests`,
  `httpx`, `pathlib`, `Path`, `open`, `eval`, `exec`, `compile`,
  `__import__`, and `getattr(_, "__*")`).
- `agent/tests/factors/test_lookahead.py` — sentinel future-row
  injection on a 300-row synthetic panel; corrupting rows after the
  probe must leave the probe value unchanged within 1e-9.
- `tools/ci_grep_gates.sh` — CI gate that rejects `yaml.load(` without
  `safe_load`, any trademarked-name leak in shipped artifacts, and any
  per-stock-code data leak in `wiki/**/*.{json,csv,html}`.
- `agent/tests/factors/conftest.py` — opt-in `pytest-socket` integration
  that hard-fails any test attempting outbound network during the
  factors test suite.

### Added — Community governance
- `CONTRIBUTING.md` — Developer Certificate of Origin sign-off
  requirement and a contributor checklist for new alpha PRs (purity,
  lookahead, `__alpha_meta__` shape, LaTeX-matches-code, per-zoo
  LICENSE.md, DCO).
- `NOTICE` (repo root) — Apache-2.0 attribution for Qlib and a
  declaration that the bundled formulas from Kakushadze, GTJA, and the
  academic baselines are mathematical content (paper prose, tables, and
  figures are not reproduced here).
- Per-zoo `LICENSE.md` for each of `qlib158/`, `alpha101/`, `gtja191/`,
  and `academic/`, plus an upstream `NOTICE` for `qlib158/`.

### Changed
- `agent/src/tools/factor_analysis_tool.py` extracted its IC/IR and
  layered-backtest helpers to `agent/src/factors/factor_analysis_core.py`
  so the new `alpha_bench_tool` reuses the same maths. Public tool
  signature is unchanged; `_compute_ic_series` and `_compute_group_equity`
  remain importable as backward-compatible aliases.
- `agent/cli.py` grew by 7 lines to register the `alpha` subcommand;
  all handler logic lives in `agent/src/factors/cli_handlers.py`.
- Packaging: `pyproject.toml` now ships `zoo/**/*.yaml`, `zoo/**/*.md`,
  and `zoo/**/NOTICE` as package data; `MANIFEST.in` recursively
  includes `agent/src/factors`.

### Known limitations
- The `btc-usdt` universe is single-asset; cross-sectional IC requires
  ≥2 instruments, so the bundled `alpha101_btc` bench run returns
  alive/reversed/dead = 0/0/0 by construction. Use a multi-symbol crypto
  basket (e.g. BTC + ETH + SOL + the top-N perpetuals) for meaningful
  cross-sectional results; a curated `crypto-majors` universe is planned
  for 0.2.

### Internal
- `wiki/alpha-library/manifest.json` and `wiki/alpha-library/content/`
  are generated artifacts and gitignored. Run
  `vibe-trading alpha export-manifest --out wiki/alpha-library/manifest.json
  --force` followed by `python wiki/scripts/build_alpha_library.py` to
  regenerate the static site.
