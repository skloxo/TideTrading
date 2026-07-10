import {
  Bot,
  BarChart3,
  Zap,
  UserCircle2,
  Database,
  ShieldAlert,
  Cpu,
  HelpCircle,
  Activity,
  CheckCircle2,
  History,
  Compass,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useEffect, useState } from "react";
import { api, type ChangelogItem } from "@/lib/api";
import ReactMarkdown from "react-markdown";

export function Home() {
  const { i18n } = useTranslation();
  const isZh = i18n.language?.startsWith("zh");

  const [changelogList, setChangelogList] = useState<ChangelogItem[]>([]);
  const [loadingChangelog, setLoadingChangelog] = useState(true);

  const STATIC_CHANGELOG: ChangelogItem[] = [
    { v: "v1.7.8", date: "2026-07-10", title: isZh ? "修复通达信网关挂载卷下软链接失效与挂载点自愈" : "Fixed mootdx symlink broken path and mount directory self-healing", body: isZh ? "修复了在 Docker 容器挂载 vt-home 卷时，导致 mootdx 的 .mootdx 软链接目标丢失并报错 File exists 的问题，在服务初始化时引入自愈机制创建底层挂载点。" : "Patched the mootdx runtime path to auto-create the missing target .mootdx directory under the mounted host volume, preventing broken symlink and FileExistsError crash when reading gateway status." },
    { v: "v1.7.7", date: "2026-07-10", title: isZh ? "支持全局管理员根密钥直接登录与数据卷底层写权限修复" : "Allowed admin API_AUTH_KEY to login and fixed write permissions", body: isZh ? "修复了多租户沙箱升级后根密钥被前端登录拦截的逻辑漏洞，支持使用全局 root 密钥一键登录 default 默认租户空间；同时修复了底层 sqlite 数据库 file 所有权被 root 占用的问题，恢复了正式环境的密码修改及数据写入能力。" : "Patched the login filter to allow the global admin API_AUTH_KEY to claim and login to the default root workspace, restoring access to all original configurations. Corrected data volume file ownership from root back to the application user to fix write permission denied operational errors." },
    { v: "v1.7.6", date: "2026-07-10", title: isZh ? "恢复三位版本号规范、全量消息通道 SDK 打包与内存泄露/残留任务清理" : "Restored three-part versioning vX.Y.Z, bundled channels SDK, and cleaned task leaks", body: isZh ? "恢复标准三位制 vX.Y.Z 版本号格式以 Z 位做日常微小更新与自动化增量；在 Dockerfile 中安装钉钉、QQ 等全部第三方消息适配器依赖；实装删除租户内存重载与 WeChat iLink 残留协程强制销毁，杜绝无密钥租户后台报错。" : "Restored three-part versioning vX.Y.Z with daily bugfixes incremental on Z. Installed full Slack/Discord/DingTalk/QQ channels adapters. Added active memory reloading during tenant deletion to purge WeChat polling task leaks and background error loops." },
    { v: "v1.7.5.5", date: "2026-07-07", title: isZh ? "服务看板重构与系统视觉圆角及信息密度全局统一规范" : "Refactored service monitor and unified global card rounding & visual density", body: isZh ? "在服务看板（/monitor）新增 Swarm 智能体执行引擎与 MCP 外部组件网关状态监控卡片；基于 Robinhood 卡片对全局视觉规范进行收窄，统一圆角为 6px（rounded-md），并全面提升大屏与表单的信息排版密度。" : "Added status cards for Swarm Agent Execution Engine and MCP Component Gateway to the service monitor (/monitor). Unified global card border-radius to 6px (rounded-md) matching Robinhood cards, and optimized padding/gaps for much higher visual information density." },
    { v: "v1.7.5.4", date: "2026-07-07", title: isZh ? "多租户沙箱隔离、全局持仓收益共享缓存与 Token 契约自愈保护" : "Launched multi-tenant sandboxed workspace isolation and details cache", body: isZh ? "完成 Cards 1.1-1.5 重构，隔离了非 default 租户 of Swarm 运行时、图谱可视化、详情日志、投研目标与 Autopilot 会话及 Trace 追踪；实装跨租户详情共享缓存，合并重复网络请求；联动 Token 过期状态与监控停用契约自愈。" : "Completed Cards 1.1-1.5 storage isolation for Swarm runtime, simulation graphs, detail logs, research goals, autopilot sessions, and trace writers. Implemented cross-tenant shared cache for portfolio details to merge duplicate requests. Enforced token expiration contract to auto-exclude invalid credentials." },
    { v: "v1.7.5", date: "2026-07-07", title: isZh ? "雪球监控多租户联合查询与 Cookie 轮询 & 持久化共享缓存池 (性能与反爬专项)" : "Launched multi-tenant Xueqiu shared cache and cooperative cookie rotation", body: isZh ? "支持雪球监控的多租户共享缓存与 Cookie 轮询分摊查询，实现全自动反爬限流自愈，调仓日志与飞书通知完全租户级安全隔离；重构系统版本接口与四段式版本比对机制，修复低版本误报与开发环境一键升级拦截故障。" : "Launched multi-tenant Xueqiu shared cache and cooperative cookie rotation to balance query load and auto-heal anti-scraping blocks, with tenant-scoped private logging and webhooks. Refactored backend version endpoint and four-part versioning comparison rules to eliminate false version warnings and enable dev-container one-click upgrade monitoring." },
    { v: "v1.7.4", date: "2026-07-06", title: isZh ? "项目设置独立页面 · 租户敏感凭证物理隔离" : "Decoupled global project settings to a standalone page", body: isZh ? "将项目全局 LLM 及数据源默认设置从普通设置中彻底剥离，提取为独立单页`/project-settings`；同时重构后端配置合并逻辑，在租户没有配置自定义 LLM 时进行物理级隐私隔离，不再向普通租户端泄露全局模型名（如 mimo）及密钥凭证。" : "Decoupled global project settings to a standalone page under the `/project-settings` route. Refactored backend configuration merging to strictly isolate tenant spaces; if a tenant has not configured custom LLM/data settings, global admin secrets and model names (e.g. mimo-v2.5-pro-ultraspeed) are fully hidden from the tenant settings form." },
    { v: "v1.7.3", date: "2026-07-03", title: isZh ? "管理员就地提权卡片 · 独立租户管理页面上线" : "Refactored admin privilege verification to inline elevation cards", body: isZh ? "重构管理员权限提权逻辑为各功能页面的就地提权卡片交互，并从服务看板中剥离出独立的租户与物理隔离工作区管理页面（新路由 `/tenants`），极大简化了管理员与普通用户的操作路径并防范了路由重定向断流。" : "Refactored admin privilege verification to inline elevation cards across restricted pages (Monitor, Settings, Logs, Tenants). Decoupled and launched a dedicated Tenant & Workspace Management page under the `/tenants` route to avoid full-page route redirects." }
  ];

  useEffect(() => {
    let active = true;
    api.getSystemChangelog(isZh ? "zh" : "en")
      .then((res) => {
        if (active) {
          if (res && res.changelog && res.changelog.length > 0) {
            setChangelogList(res.changelog);
          } else {
            setChangelogList(STATIC_CHANGELOG);
          }
          setLoadingChangelog(false);
        }
      })
      .catch(() => {
        if (active) {
          setChangelogList(STATIC_CHANGELOG);
          setLoadingChangelog(false);
        }
      });
    return () => {
      active = false;
    };
  }, [isZh]);

  const FEATURES = [
    {
      icon: Bot,
      color: "cyan",
      title: isZh ? "AI 智能体联队" : "AI Agent Swarm",
      desc: isZh
        ? "基于双向 ReAct 推理，支持多角色（多头/空头/风控/PM）的投资委员会 debate 决策机制。"
        : "ReAct reasoning swarm with investment committee debate preset (bull vs bear, risk audit, PM decision).",
    },
    {
      icon: BarChart3,
      color: "orange",
      title: isZh ? "极速回测引擎" : "Built-in Backtest",
      desc: isZh
        ? "多数据源智能覆盖，提供日线与分钟级的 A 股及港股历史量化分析回测支持。"
        : "Built-in engine with multiple data sources covering minute-to-daily bars for A/H-shares.",
    },
    {
      icon: Zap,
      color: "pink",
      title: isZh ? "实时流式输出" : "Real-time Streaming",
      desc: isZh
        ? "秒级呈现智能体决策树，实时直观展示其意图解析、代码生成和原子工具的调用链。"
        : "Watch the agent's decision tree, tool execution logs, and live code generation in real time.",
    },
    {
      icon: UserCircle2,
      color: "amber",
      title: isZh ? "物理隔离沙箱" : "Isolated Sandbox",
      desc: isZh
        ? "使用租户 API Key 隔离运行环境。会话、执行记录、上传文件等均物理独立，确保资产隐私。"
        : "Physical isolation based on Tenant API Keys for sessions, policy runs, and file storage.",
    },
    {
      icon: Compass,
      color: "emerald",
      title: isZh ? "雪球协同监控" : "Cooperative Xueqiu Watcher",
      desc: isZh
        ? "支持多租户隔离监控，底层共享持久化缓存池，协同 Cookie 旋转轮询，大幅分摊并降低接口封禁风险。"
        : "Multi-tenant monitoring with persistent shared cache pool and cooperative cookie rotation to prevent bans.",
    },
  ];

  const colorMap: Record<string, { icon: string; bg: string; border: string; glow: string }> = {
    cyan:   { icon: "text-cyan-400",   bg: "bg-cyan-500/10",   border: "border-cyan-500/20",   glow: "group-hover:shadow-cyan-500/20" },
    orange: { icon: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", glow: "group-hover:shadow-orange-500/20" },
    pink:   { icon: "text-pink-400",   bg: "bg-pink-500/10",   border: "border-pink-500/20",   glow: "group-hover:shadow-pink-500/20" },
    amber:  { icon: "text-amber-400",  bg: "bg-amber-500/10",  border: "border-amber-500/20",  glow: "group-hover:shadow-amber-500/20" },
    emerald:{ icon: "text-emerald-400",bg: "bg-emerald-500/10",border: "border-emerald-500/20",glow: "group-hover:shadow-emerald-500/20" },
  };

  return (
    <div className="mx-auto max-w-6xl p-4 space-y-20 pb-28">

      {/* ══════════════════ 1. HERO SECTION ══════════════════ */}
      <section className="relative flex flex-col items-center justify-center text-center space-y-7 pt-14 overflow-hidden">

        {/* Background glow orbs */}
        <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-primary/8 rounded-full blur-[80px]" />
          <div className="absolute top-10 left-1/4 w-64 h-64 bg-cyan-500/6 rounded-full blur-[60px]" />
          <div className="absolute top-10 right-1/4 w-64 h-64 bg-pink-500/6 rounded-full blur-[60px]" />
        </div>

        {/* Version badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-primary/25 bg-primary/8 text-primary text-xs font-semibold backdrop-blur-sm shadow-sm shadow-primary/10">
          <Activity className="h-3 w-3 animate-pulse" />
          <span>v1.7.8 Stable</span>
          <span className="w-px h-3 bg-primary/30" />
          <span className="text-emerald-400 font-normal">{isZh ? "运行中" : "Live"}</span>
        </div>

        {/* Title */}
        <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-none text-foreground">
          {isZh ? "潮汐投研" : "TideTrading"}
        </h1>

        {/* Tagline */}
        <p className="max-w-2xl text-sm md:text-base text-muted-foreground leading-relaxed">
          {isZh
            ? "聚焦 A股与港股 的智能交易与多维分析工作站，深度融合舆情情绪面、资金流向、技术指标回测与基本面分析，支持多通道即插即用推送与多租户隔离沙箱。"
            : "A multi-dimensional trading & analysis workstation focused on A/H-shares, integrating sentiment parsing, capital flows, backtesting, and secure multi-tenant sandbox."}
        </p>



      </section>

      {/* ══════════════════ 2. FEATURE CARDS ══════════════════ */}
      <section className="space-y-4">
        <div className="text-center space-y-1.5">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            {isZh ? "核心产品能力与优势" : "Core Capabilities & Advantages"}
          </h2>
          <p className="text-xs text-muted-foreground">{isZh ? "专为 A/H 股市场打造的量化智能工作站" : "Quantitative intelligence for A/H-share markets"}</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {FEATURES.map(({ icon: Icon, color, title, desc }) => {
            const c = colorMap[color];
            return (
              <div
                key={title}
                className={`group relative border border-border/60 bg-card/50 backdrop-blur-sm rounded-md p-4 space-y-4 hover:border-border/90 hover:bg-card/80 transition-all duration-300 hover:shadow-xl ${c.glow} cursor-default overflow-hidden`}
              >
                {/* Corner glow */}
                <div className={`absolute top-0 right-0 w-20 h-20 ${c.bg} rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 -translate-x-4 -translate-y-4 pointer-events-none`} />
                <div className={`inline-flex p-2.5 rounded-md ${c.bg} ${c.icon} border ${c.border}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="space-y-1.5">
                  <h3 className="font-bold text-sm text-foreground">{title}</h3>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">{desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ══════════════════ 3. LLM ORCHESTRATION ══════════════════ */}
      <section className="relative rounded-md overflow-hidden border border-border/50 bg-gradient-to-br from-card/80 to-muted/20 backdrop-blur-sm p-4.5 md:p-10">
        {/* Bg accent */}
        <div className="absolute inset-0 pointer-events-none -z-10">
          <div className="absolute top-0 right-0 w-80 h-80 bg-primary/4 rounded-full blur-[80px]" />
        </div>

        <div className="grid gap-10 lg:grid-cols-12 items-start">
          {/* Left */}
          <div className="lg:col-span-5 space-y-3.5">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold border border-primary/25 bg-primary/8 text-primary">
              <Cpu className="h-3 w-3" />
              <span>{isZh ? "设计哲学" : "Orchestration Philosophy"}</span>
            </div>
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight leading-tight">
              {isZh ? "大模型语义编排机制与设计哲学" : "LLM Orchestration & Design Philosophy"}
            </h2>
            <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
              {isZh ? (
                <>
                  平台秉承<strong className="text-foreground">「确定性优先」</strong>原则，并深度贯彻<strong className="text-foreground">「第一性原理」</strong>与<strong className="text-foreground">「奥卡姆剃刀」</strong>。凡是可以通过确定性算法解决的部分，均执行流程化代码，绝不滥用大模型。
                  <br /><br />
                  我们主张将卡片设计极致简化，大模型仅精确定位为<strong className="text-foreground">「语义路由器与服务编排器」</strong>，将客观数据串联并流式呈递出决策思考链路。
                </>
              ) : (
                <>
                  TideTrading operates on a <strong className="text-foreground">"Deterministic First"</strong> approach, integrated with <strong className="text-foreground">"First Principles"</strong> and <strong className="text-foreground">"Occam's Razor"</strong>. We run deterministic scripts or queries directly.
                  <br /><br />
                  LLMs act strictly as <strong className="text-foreground">semantic routers & orchestrators</strong>: plan actions, invoke atomic tools, and format reports.
                </>
              )}
            </p>
          </div>

          {/* Right: Steps */}
          <div className="lg:col-span-7 flex flex-col space-y-3">
            {[
              {
                n: 1, color: "cyan",
                title: isZh ? "自然语言输入 (User Prompt)" : "Natural Language Input",
                body: isZh ? "用户使用日常语言描述策略意图：帮我调取行情网关，看看比亚迪现在的买卖盘" : "Users describe intentions naturally, e.g., 'Check my connector portfolio concentration'",
              },
              {
                n: 2, color: "primary",
                title: isZh ? "语义路由与代码生成" : "Semantic Routing & Code Generation",
                body: isZh ? "主智能体提取参数并生成调用原子工具的代码片段，实时向前端流式传输思考链路。" : "The Agent Router extracts parameters, plans actions, and writes tool execution scripts dynamically.",
              },
              {
                n: 3, color: "orange",
                title: isZh ? "确定性工具执行" : "Deterministic Tool Execution",
                body: isZh ? "后台在租户沙箱中安全运行该代码，直连 TCP 行情网关或因子库，返回纯粹客观数据。" : "Scripts execute securely within tenant sandboxes, fetching raw quotes or factors directly.",
              },
              {
                n: 4, color: "amber",
                title: isZh ? "结果融合与智能反馈" : "Result Fusion & Intelligent Feedback",
                body: isZh ? "智能体捕获执行数据，提炼并组织成排版美观、指标齐备的 HTML 或 PDF 回报报告。" : "The agent merges raw output into highly scannable, indicator-rich markdown / HTML reports.",
              },
            ].map((step) => (
              <div
                key={step.n}
                className="flex items-start gap-4 bg-card/60 backdrop-blur-sm p-4 rounded-md border border-border/50 hover:border-primary/30 transition-all group"
              >
                <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black border-2 transition-colors
                  ${step.color === "cyan"    ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-400 group-hover:bg-cyan-500/25" :
                    step.color === "orange"  ? "bg-orange-500/15 border-orange-500/40 text-orange-400 group-hover:bg-orange-500/25" :
                    step.color === "amber"   ? "bg-amber-500/15 border-amber-500/40 text-amber-400 group-hover:bg-amber-500/25" :
                                               "bg-primary/15 border-primary/40 text-primary group-hover:bg-primary/25"}`}
                >
                  {step.n}
                </div>
                <div className="space-y-0.5">
                  <h4 className="text-xs font-semibold">{step.title}</h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">{step.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════ 4. DATA CHAIN ══════════════════ */}
      <section className="space-y-7">
        <div className="text-center space-y-1.5">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            {isZh ? "AH股行情与交易数据链指引" : "A/H-Share Data Chain & Execution Flow"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-xl mx-auto">
            {isZh ? "平台打通了高频行情获取、本地历史归档与多券商实盘交易之间的核心管道。" : "Bridges high-frequency quotes, localized databases, and multi-broker live trading."}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* A-Share card — red neon theme */}
          <div className="relative border border-rose-500/20 bg-card/60 backdrop-blur-sm p-4 rounded-md space-y-3.5 overflow-hidden group hover:border-rose-500/40 transition-all hover:shadow-lg hover:shadow-rose-500/10">
            <div className="absolute top-0 right-0 w-40 h-40 bg-rose-500/5 rounded-full blur-2xl pointer-events-none" />
            <div className="flex items-center gap-2.5 font-bold text-sm text-rose-400">
              <div className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <Database className="h-4 w-4" />
              </div>
              {isZh ? "A股实时行情与持久化数据链" : "A-Share Quotation & DB Pipeline"}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {isZh ? "专为国内A股设计的行情获取架构，保障低延迟、高并发和数据的客观稳固。" : "Engineered for high-frequency domestic A-shares data, ensuring robustness and consistency."}
            </p>
            <ul className="space-y-3 text-[11px] text-muted-foreground">
              {[
                { title: isZh ? "通达信 TCP 行情网关" : "TDX TCP Gateway", body: isZh ? "直连通达信行情，建立多测速池自动心跳与断线重连；网络超时自动降级至腾讯 L1 HTTP。" : "Low-latency TCP connection pool with auto speed checks; fallbacks to Tencent HTTP." },
                { title: isZh ? "公共数据共享缓存" : "Shared Memory Cache", body: isZh ? "交易时间内单线程高频轮询指数和题材板块并存入内存公库，防止多租户并发触发封 IP。" : "Global cache wheels index/sector quotes every 5s to prevent IP bans." },
                { title: isZh ? "自动收盘维护" : "Daily Close Maintenance", body: isZh ? "每日 15:30 自动拉取基本面估值、题材板块映射、主力资金流向及两融杠杆，写入 local DB。" : "Scheduler polls valuation, funding flow, and margin data at 15:30 to rebuild stocks.db." },
              ].map((li) => (
                <li key={li.title} className="flex gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                  <span><strong className="text-foreground">{li.title}</strong>：{li.body}</span>
                </li>
              ))}
            </ul>
            <div className="p-3 bg-rose-950/20 dark:bg-rose-950/30 rounded-md border border-rose-500/10 text-[10px] font-mono text-rose-400/80">
              {isZh ? "A股数据链: TDX TCP → SharedMemory → sqlite:stocks.db" : "A-Share: TDX TCP → SharedMemory → sqlite:stocks.db"}
            </div>
          </div>

          {/* H-Share/Risk card — cyan neon theme */}
          <div className="relative border border-cyan-500/20 bg-card/60 backdrop-blur-sm p-4 rounded-md space-y-3.5 overflow-hidden group hover:border-cyan-500/40 transition-all hover:shadow-lg hover:shadow-cyan-500/10">
            <div className="absolute top-0 right-0 w-40 h-40 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" />
            <div className="flex items-center gap-2.5 font-bold text-sm text-cyan-400">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                <ShieldAlert className="h-4 w-4" />
              </div>
              {isZh ? "港股实盘/模拟交易风控链" : "H-Share Live & Risk Pipeline"}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {isZh ? "通过可信连接器接入港股实盘（长桥、富途等），并实施严格的防暴走风控。" : "Connects to HK broker APIs with strict multi-layered safeguards against trade runs."}
            </p>
            <ul className="space-y-3 text-[11px] text-muted-foreground">
              {[
                { title: isZh ? "OAuth 授权与只读默认" : "OAuth & Read-only Default", body: isZh ? "券商接口优先仅赋予账户资产及持仓只读权限，只有当发生明确交易委托签署时才唤醒交易通道。" : "OAuth defaults to read-only summaries unless explicit trading keys are injected." },
                { title: isZh ? "限额风控委托 (Mandates)" : "Trade Mandates", body: isZh ? "每个连接均绑定委托规则（包含标的 Universe、单笔额度上限、到期日），超限下单在前端即被驳回。" : "Every broker session must bind a mandate defining valid stock pool, size, and expiry." },
                { title: isZh ? "全局紧急熔断闸" : "Global Halt Switch", body: isZh ? "系统后台提供一键紧急挂起。启用后，所有活跃交易连接将瞬间失效，任何下单指令直接返回失败。" : "One-click halt instantly suspends all runners, declining order requests immediately." },
              ].map((li) => (
                <li key={li.title} className="flex gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                  <span><strong className="text-foreground">{li.title}</strong>：{li.body}</span>
                </li>
              ))}
            </ul>
            <div className="p-3 bg-cyan-950/20 dark:bg-cyan-950/30 rounded-md border border-cyan-500/10 text-[10px] font-mono text-cyan-400/80">
              {isZh ? "风控链: Broker API → OAuth Token → Mandate limits → Global Halt" : "Risk: Broker API → OAuth Token → Mandate limits → Global Halt"}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════ 5. ONBOARDING WIZARD ══════════════════ */}
      <section className="space-y-7">
        <div className="text-center space-y-1.5">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            {isZh ? "租户新手引导向导" : "Tenant Onboarding Wizard"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-xl mx-auto">
            {isZh ? "简单四步，配齐并校验您的私人量化智能体工作空间配置。" : "Follow these steps to set up your private quant workspace and start trading."}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3.5">
          {[
            { n: "01", icon: UserCircle2, color: "cyan",   title: isZh ? "步骤一：配置券商密钥" : "Step 1: Broker Auth",       body: isZh ? "前往「设置」，在个人配置中填写您的券商密钥（如 Longbridge API 密钥、Xueqiu Cookie 等）以激活交易连接。" : "Navigate to Settings and add your broker credentials (Longbridge API key, Xueqiu cookie)." },
            { n: "02", icon: Cpu,         color: "primary", title: isZh ? "步骤二：配置私有模型" : "Step 2: Private LLM",       body: isZh ? "配置您专属的 AI 大模型后端（OpenAI, OpenRouter 等），设定个性化决策参数。" : "Configure your private LLM provider, setting model name, base URL, and API key." },
            { n: "03", icon: Activity,    color: "orange",  title: isZh ? "步骤三：校验风控状态" : "Step 3: Verify Runtime",    body: isZh ? "前往「运行状态」监视面板，校验账户连接状况、当前的限额规则（Mandate）及风控到期时间。" : "Visit the Runtime Monitor to double check account status, mandate limits, and expiry." },
            { n: "04", icon: Bot,         color: "amber",   title: isZh ? "步骤四：开启量化对话" : "Step 4: Start Chatting",   body: isZh ? "进入「智能体工作区」或「回测报告」，向智能体下达指令，启动多智能体策略回测。" : "Open Quant Agent Workspace or Reports to initiate backtests and view details." },
          ].map((step) => {
            const Icon = step.icon;
            const c = colorMap[step.color] ?? colorMap["cyan"];
            return (
              <div key={step.n} className="relative border border-border/50 bg-card/50 backdrop-blur-sm p-4 rounded-md space-y-4 group hover:border-primary/30 hover:shadow-md transition-all overflow-hidden">
                <div className={`absolute top-4 right-4 text-3xl font-black ${c.icon} opacity-10 group-hover:opacity-20 transition-opacity font-mono select-none`}>{step.n}</div>
                <div className={`inline-flex p-2.5 rounded-md ${c.bg} ${c.icon} border ${c.border}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="font-semibold text-xs leading-snug">{step.title}</h3>
                <p className="text-[11px] text-muted-foreground leading-relaxed">{step.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ══════════════════ 6. ROADMAP & CHANGELOG ══════════════════ */}
      <section className="space-y-4">
        <div className="text-center space-y-1.5">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center justify-center gap-2.5">
            <Compass className="h-6 w-6 text-primary" />
            {isZh ? "线路蓝图与迭代展望" : "Roadmap & Release Changelog"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-xl mx-auto">
            {isZh ? "潮汐投研 产品线的最新演进动态与中长期功能规划蓝图。" : "Track our current milestones and mid-to-long term quantitative roadmap."}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* Changelog */}
          <div className="border border-border/50 bg-card/60 backdrop-blur-sm p-4 rounded-md space-y-3.5">
            <h3 className="text-sm font-bold flex items-center gap-2 text-primary pb-3 border-b border-border/50">
              <History className="h-4 w-4" />
              {isZh ? "迭代记录 (Milestones Completed)" : "Milestones Completed"}
            </h3>
            <div className="relative">
              {loadingChangelog ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
                  <span className="animate-spin h-3.5 w-3.5 border-2 border-primary border-t-transparent rounded-full" />
                  <span>{isZh ? "正在同步最新动态..." : "Syncing latest changelog..."}</span>
                </div>
              ) : (
                changelogList.map((item, index) => (
                  <div key={item.v} className="relative pl-5 pb-5 border-l-2 border-primary/20 last:pb-0">
                    <span className={`absolute -left-[7px] top-1.5 h-3 w-3 rounded-full border-2 border-background ${index === 0 ? "bg-primary animate-pulse" : "bg-primary/35"}`} />
                    <h4 className="text-xs font-semibold flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-primary font-bold">{item.v}</span>
                      {item.date && <span className="text-[9px] text-muted-foreground font-normal">({item.date})</span>}
                      <span className="text-foreground">— {item.title}</span>
                    </h4>
                    <ReactMarkdown
                      components={{
                        p: ({ node, ...props }) => <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc pl-4 space-y-1.5 my-1.5" {...props} />,
                        li: ({ node, ...props }) => <li className="text-[10px] text-muted-foreground leading-normal" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-foreground" {...props} />,
                        code: ({ node, ...props }) => <code className="bg-muted px-1.5 py-0.5 rounded text-[9px] font-mono text-cyan-400" {...props} />,
                        a: ({ node, ...props }) => <a className="text-primary hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                      }}
                    >
                      {item.body}
                    </ReactMarkdown>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Roadmap */}
          <div className="border border-border/50 bg-card/60 backdrop-blur-sm p-4 rounded-md space-y-3.5">
            <h3 className="text-sm font-bold flex items-center gap-2 text-orange-400 pb-3 border-b border-border/50">
              <Zap className="h-4 w-4" />
              {isZh ? "规划蓝图 (Future Blueprints)" : "Future Blueprints"}
            </h3>
            <div className="relative">
              {[
                { title: isZh ? "选股与复盘日报脚本可视化"          : "Selection Script Visualization",     status: isZh ? "进行中" : "In Progress", statusColor: "text-amber-500 bg-amber-500/10", dot: "bg-orange-400 animate-pulse", body: isZh ? "将租户已有的量化选股与复盘日报 Python 脚本整合至前端，提供一键执行与图文看板渲染。" : "Visualize historical screening and daily analysis scripts on Web UI with one-click run." },
                { title: isZh ? "多智能体深度投研协同管线 (Swarm)"   : "Multi-Agent Deep Research Swarm",     status: isZh ? "进行中" : "In Progress", statusColor: "text-amber-500 bg-amber-500/10", dot: "bg-orange-400 animate-pulse", body: isZh ? "多智能体辩论式深度投研 Swarm，牛熊双方 Agent 协同推演，产出含结构化数据的深度研报。" : "Multi-agent bull/bear debate pipeline producing deep research reports with structured data." },
                { title: isZh ? "多租户并发 Key 池管理与安全加固"    : "Multi-tenant Key Pool & Hardening",   status: isZh ? "计划中" : "Planned",     statusColor: "text-muted-foreground bg-muted", dot: "bg-muted", body: isZh ? "允许各租户共享或隔离定制 API 密钥池，进一步加固执行沙箱与隔离安全性。" : "Multi-tenant API keys pool sharing and sandbox verification isolation hardening." },
                { title: isZh ? "VirtualBroker 模拟盘与多空撮合"    : "VirtualBroker Sim Trading",           status: isZh ? "计划中" : "Planned",     statusColor: "text-muted-foreground bg-muted", dot: "bg-muted", body: isZh ? "研发轻量级模拟柜台（支持委托、撮合、成交、撤单状态机追踪），为策略提供实测环境。" : "Lightweight local broker counter engine for matching mock orders and order lifecycle tracking." },
                { title: isZh ? "盘前个股做T网格策略建议生成"        : "Pre-market Grid Recommendations",    status: isZh ? "计划中" : "Planned",     statusColor: "text-muted-foreground bg-muted", dot: "bg-muted", body: isZh ? "每日开盘前，根据历史波动特征自动生成个股网格做T压力支撑位及额度配置建议。" : "Automated pre-market support/resistance grid calculation and sizing guidelines." },
                { title: isZh ? "Monaco 在线代码编辑器与沙箱编译器"  : "Online Code Editor & Sandbox",        status: isZh ? "规划中" : "Proposed",    statusColor: "text-muted-foreground bg-muted", dot: "bg-muted", body: isZh ? "集成 Monaco 编辑器，支持专业交易员在 Web 界面直接编写、修改并编译运行策略。" : "Embed Monaco editor to write, tweak, compile, and backtest custom strategies on the fly." },
                { title: isZh ? "VLM 视觉研报与 K线技术形态识别"     : "VLM Visual Pattern Recognition",     status: isZh ? "规划中" : "Proposed",    statusColor: "text-muted-foreground bg-muted", dot: "bg-muted", body: isZh ? "利用视觉大模型（VLM）读取 K线走势图并自动识别技术形态（如双底、头肩底等）。" : "Leverage Multi-modal Vision LLMs to read charts and identify classic tech patterns." },
              ].map((item) => (
                <div key={item.title} className="relative pl-5 pb-5 border-l-2 border-orange-500/20 last:pb-0">
                  <span className={`absolute -left-[7px] top-1.5 h-3 w-3 rounded-full border-2 border-background ${item.dot}`} />
                  <h4 className="text-xs font-semibold flex items-center gap-1.5 flex-wrap">
                    {item.title}
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-normal ${item.statusColor}`}>{item.status}</span>
                  </h4>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════ 7. FOOTER ══════════════════ */}
      <footer className="pt-8 border-t border-border/50 flex flex-col md:flex-row items-center justify-between text-xs text-muted-foreground gap-4">
        <div className="flex items-center gap-1.5">
          <HelpCircle className="h-4 w-4" />
          <span>{isZh ? "有疑问？请阅读共享技能使用指引" : "Need help? Check local platform guide skill."}</span>
        </div>
        <div>
          <span>&copy; 2026 {isZh ? "潮汐投研" : "TideTrading"}. All rights reserved.</span>
        </div>
      </footer>

    </div>
  );
}
