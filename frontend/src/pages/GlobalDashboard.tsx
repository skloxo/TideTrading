import { useState, useEffect, useRef } from "react";
import { 
  Cpu, Terminal, Play, Pause, Settings, Check 
} from "lucide-react";

// Import modular widgets
import { Watchlist } from "@/components/dashboard/Watchlist";
import { LimitUpBoard } from "@/components/dashboard/LimitUpBoard";
import { FundFlows } from "@/components/dashboard/FundFlows";
import { MarketSentiment } from "@/components/dashboard/MarketSentiment";
import { YuziMovement } from "@/components/dashboard/YuziMovement";
import { ConceptRotation } from "@/components/dashboard/ConceptRotation";
import { PopularStocks } from "@/components/dashboard/PopularStocks";
import { LonghuBang } from "@/components/dashboard/LonghuBang";
import { MobileAlerts } from "@/components/dashboard/MobileAlerts";
import { Portfolio } from "@/components/dashboard/Portfolio";
import { KolOpinions } from "@/components/dashboard/KolOpinions";

interface TerminalLog {
  time: string;
  sender: string;
  type: "info" | "action" | "warning" | "success";
  message: string;
}

export function GlobalDashboard() {
  const [isPlaying, setIsPlaying] = useState(true);
  const [simProgress, setSimProgress] = useState(78);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState("");
  const [logs, setLogs] = useState<TerminalLog[]>([]);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // View Mode: Global vs Personal
  const [viewMode, setViewMode] = useState<"global" | "personal">("global");

  // Tenant-based layout customization
  const [currentTenant, setCurrentTenant] = useState<string>("tenant_c");
  const [showConfig, setShowConfig] = useState(false);

  // Map of tenant roles to allowed widgets
  const TENANT_WIDGETS: Record<string, string[]> = {
    tenant_a: ["watchlist", "sentiment", "concepts", "popular", "kol", "logsTerminal", "reactTimeline"],
    tenant_b: ["watchlist", "limitUp", "fundFlows", "sentiment", "d3Graph", "lattice", "alerts", "portfolio", "logsTerminal", "reactTimeline"],
    tenant_c: [
      "watchlist", "limitUp", "fundFlows", "sentiment", "d3Graph", "lattice",
      "yuzi", "concepts", "popular", "longhu", "alerts", "portfolio", "kol",
      "logsTerminal", "reactTimeline"
    ],
  };

  const isWidgetAllowed = (id: string) => {
    const allowed = TENANT_WIDGETS[currentTenant] || [];
    return allowed.includes(id);
  };

  const [enabledWidgets, setEnabledWidgets] = useState<Record<string, boolean>>({
    watchlist: true,
    limitUp: true,
    fundFlows: true,
    sentiment: true,
    d3Graph: true,
    lattice: true,
    yuzi: true,
    concepts: true,
    popular: true,
    longhu: true,
    alerts: false,
    portfolio: false,
    kol: true,
    logsTerminal: true,
    reactTimeline: false,
  });

  // Switch between Global and Personal views (preconfigures layout focus)
  const handleViewModeChange = (mode: "global" | "personal") => {
    setViewMode(mode);
    if (mode === "global") {
      setEnabledWidgets({
        watchlist: true,
        limitUp: true,
        fundFlows: true,
        sentiment: true,
        d3Graph: true,
        lattice: true,
        yuzi: true,
        concepts: true,
        popular: true,
        longhu: true,
        alerts: false,
        portfolio: false,
        kol: true,
        logsTerminal: true,
        reactTimeline: false,
      });
    } else {
      setEnabledWidgets({
        watchlist: true,
        limitUp: false,
        fundFlows: false,
        sentiment: true,
        d3Graph: false,
        lattice: false,
        yuzi: false,
        concepts: false,
        popular: true,
        longhu: false,
        alerts: true,
        portfolio: true,
        kol: true,
        logsTerminal: true,
        reactTimeline: true,
      });
    }
  };

  // Simulated live clock aligned to trading hours (e.g. 14:24:57)
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const timeStr = now.toTimeString().split(" ")[0];
      setCurrentTime(`2026-07-01 ${timeStr}`);
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Initial terminal logs
  useEffect(() => {
    const initialLogs: TerminalLog[] = [
      { time: "14:20:05", sender: "SYS_ENGINE", type: "info", message: "OASIS Multi-Agent Simulator initialized. Loading A-share seed profiles..." },
      { time: "14:20:12", sender: "PORTFOLIO", type: "info", message: "Scanning user watchlists: Active stocks = 8, Total capital = 10,000,000" },
      { time: "14:21:00", sender: "SOCIAL_MON", type: "action", message: "Sentiment Spike: #低空经济# keyword frequency +340% in Weibo/Xueqiu" },
      { time: "14:22:15", sender: "AGENT_YUZI", type: "action", message: "游资·宁波解放路: Triggered BUY order block on 万丰奥威 (301550) - Volume: 45,000 lots" },
      { time: "14:23:02", sender: "AGENT_BEIXIANG", type: "success", message: "北向资金: Added 1,200,000 shares in 宁德时代 (300750) - Sector inflows confirmed" },
      { time: "14:23:45", sender: "SYS_ENGINE", type: "warning", message: "Market volatility high. High-frequency price feed latency: 12ms. Retrying bridge..." },
      { time: "14:24:10", sender: "AGENT_SANHU", type: "action", message: "散户群体: Fear-driven panic selling detected on 601398 (工商银行)" },
      { time: "14:24:32", sender: "DECISION_REACTOR", type: "success", message: "ReACT Analyzer: Generated bullish trade candidate report for Concept [低空航空]" },
    ];
    setLogs(initialLogs);
  }, []);

  // Scroll to bottom of logs container directly to prevent scrolling the whole page
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Append dynamic logs if playing
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const messages = [
        { sender: "AGENT_YUZI", type: "action", message: "游资·小鳄鱼: Accumulating positions in 工业富联 (601138) near support level" },
        { sender: "AGENT_JIGOU", type: "action", message: "机构席位: Reallocating portfolio weights, trimming positions in high-beta tech" },
        { sender: "SOCIAL_MON", type: "info", message: "Xueqiu Social Pulse: User discussion index on 比亚迪 (002594) rises to 8.9/10" },
        { sender: "AGENT_SANHU", type: "warning", message: "散户群体: FOMO sentiment driving breakout buying on 万丰奥威 (301550)" },
        { sender: "AGENT_BEIXIANG", type: "success", message: "北向资金: Net block purchases on 贵州茅台 (600519) +34,000 shares" },
        { sender: "DECISION_REACTOR", type: "success", message: "ReACT Analyzer: Decision loop 412 completed. Portfolio recommended tilt to Energy." },
      ];

      const chosen = messages[Math.floor(Math.random() * messages.length)];
      const now = new Date();
      const timeStr = now.toTimeString().split(" ")[0];

      setLogs((prev) => [
        ...prev.slice(-20),
        {
          time: timeStr,
          sender: chosen.sender,
          type: chosen.type as any,
          message: chosen.message,
        },
      ]);

      setSimProgress((prev) => (prev >= 100 ? 5 : prev + 1));
    }, 4000);

    return () => clearInterval(interval);
  }, [isPlaying]);

  // Helper function to render a widget based on tenant configuration
  const renderWidget = (
    id: string, 
    name: string, 
    isVipOnly: boolean, 
    Component: React.ComponentType
  ) => {
    if (!isWidgetAllowed(id) || !name || isVipOnly === undefined) return null;
    if (!enabledWidgets[id]) return null;
    return <div key={id} className="h-full"><Component /></div>;
  };

  const widgetDefinitions = [
    { id: "watchlist", name: "⭐ 自选股监控", isVipOnly: false, column: "left" },
    { id: "limitUp", name: "🔥 涨停板追踪", isVipOnly: false, column: "left" },
    { id: "fundFlows", name: "📊 板块资金流", isVipOnly: false, column: "left" },
    { id: "sentiment", name: "📈 大盘情绪温度", isVipOnly: false, column: "left" },
    
    { id: "yuzi", name: "🕵️ 游资盘中大单", isVipOnly: true, column: "right" },
    { id: "concepts", name: "📡 题材热度轮动", isVipOnly: false, column: "right" },
    { id: "popular", name: "🔥 热门人气个股", isVipOnly: false, column: "right" },
    { id: "longhu", name: "📋 龙虎榜单明细", isVipOnly: true, column: "right" },
    { id: "alerts", name: "🚨 盘中高频预警", isVipOnly: false, column: "right" },
    { id: "portfolio", name: "💼 我的持仓股票", isVipOnly: true, column: "right" },
    { id: "kol", name: "👥 大V盘中情绪", isVipOnly: false, column: "right" },
  ];

  return (
    <div 
      className="w-full min-h-screen text-slate-800 dark:text-slate-100 flex flex-col font-mono relative overflow-hidden bg-slate-50 dark:bg-[#0a0a0f] bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] dark:bg-[radial-gradient(#141424_1px,transparent_1px)]"
      style={{ backgroundSize: "24px 24px" }}
    >
      {/* HEADER SECTION */}
      <header className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center px-4 py-3 border-b border-slate-200 dark:border-[#222233] bg-white/90 dark:bg-[#0a0a0f]/90 sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-rose-600 dark:bg-[#ff3366] animate-pulse" />
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-widest text-rose-600 dark:text-[#ff3366]">VIBE-TRADING-CNX // QUANT TERMINAL</span>
            <span className="text-[10px] text-slate-500 dark:text-slate-450">SYS_STATUS: ACTIVE // EMULATING: {simProgress}% // NETWORK: ONLINE</span>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-3 mt-2 sm:mt-0 text-xs">
          {/* View Mode Switcher */}
          <div className="flex items-center gap-1 border border-slate-200 dark:border-[#222233] p-0.5 bg-slate-150 dark:bg-[#12121e] rounded">
            <button 
              onClick={() => handleViewModeChange("global")}
              className={`px-3 py-1 text-xs font-bold transition-all rounded-sm ${
                viewMode === "global" 
                  ? "bg-rose-600 dark:bg-[#ff3366] text-white" 
                  : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              全局看板
            </button>
            <button 
              onClick={() => handleViewModeChange("personal")}
              className={`px-3 py-1 text-xs font-bold transition-all rounded-sm ${
                viewMode === "personal" 
                  ? "bg-rose-600 dark:bg-[#ff3366] text-white" 
                  : "text-slate-500 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              个人看板
            </button>
          </div>

          {/* Tenant Selector */}
          <div className="flex items-center gap-1.5 border border-slate-200 dark:border-[#222233] px-2.5 py-1 bg-slate-50 dark:bg-[#12121e] text-slate-700 dark:text-slate-300 rounded">
            <span className="text-slate-500 dark:text-slate-400">当前租户:</span>
            <select 
              value={currentTenant} 
              onChange={(e) => setCurrentTenant(e.target.value)}
              className="bg-transparent text-slate-800 dark:text-white font-bold outline-none cursor-pointer"
            >
              <option value="tenant_a" className="bg-white dark:bg-[#12121e] text-slate-800 dark:text-white">租户 A (零售版)</option>
              <option value="tenant_b" className="bg-white dark:bg-[#12121e] text-slate-800 dark:text-white">租户 B (专业版)</option>
              <option value="tenant_c" className="bg-white dark:bg-[#12121e] text-rose-600 dark:text-[#ff3366] font-bold">租户 C (旗舰版)</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 border border-slate-200 dark:border-[#222233] px-2.5 py-1 bg-slate-50 dark:bg-[#12121e] text-slate-700 dark:text-slate-300 rounded">
            <span className="text-slate-500 dark:text-slate-400">时间:</span>
            <span className="text-slate-800 dark:text-white font-bold">{currentTime || "2026-07-01 14:24:57"}</span>
          </div>

          <div className="flex items-center gap-1">
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex items-center justify-center p-1.5 border border-slate-200 dark:border-[#222233] bg-slate-50 hover:bg-slate-100 dark:bg-[#12121e] dark:hover:bg-[#1a1a2e] text-rose-600 dark:text-[#ff3366] hover:text-rose-700 dark:hover:text-[#ff5588] transition-colors rounded"
              title={isPlaying ? "Pause Simulation" : "Start Simulation"}
            >
              {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            </button>
            <button 
              onClick={() => setShowConfig(!showConfig)}
              className={`flex items-center justify-center p-1.5 border border-slate-200 dark:border-[#222233] transition-colors rounded ${
                showConfig 
                  ? "bg-rose-600 dark:bg-[#ff3366] text-white" 
                  : "bg-slate-50 hover:bg-slate-100 dark:bg-[#12121e] dark:hover:bg-[#1a1a2e] text-rose-600 dark:text-[#ff3366] hover:text-rose-700"
              }`}
              title="Layout Settings"
            >
              <Settings className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* CONFIGURATION DRAWER PANEL */}
      {showConfig && (
        <div className="absolute top-14 right-4 w-72 bg-white/98 dark:bg-[#0c0c14]/98 border border-slate-200 dark:border-[#333344] z-40 p-4 max-h-[85vh] overflow-y-auto shadow-2xl animate-in slide-in-from-right-5 duration-200 rounded-lg text-slate-800 dark:text-slate-100">
          <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-2 mb-3">
            <span className="text-xs font-extrabold text-rose-600 dark:text-[#ff3366] tracking-wider">🔧 仪表盘布局配置</span>
            <button onClick={() => setShowConfig(false)} className="text-slate-500 hover:text-slate-900 dark:hover:text-white text-xs">✕</button>
          </div>

          <div className="space-y-4">
            {/* Tenant switcher rules explanation */}
            <div className="bg-slate-50 dark:bg-[#12121e] p-2.5 border border-slate-200 dark:border-[#222233] rounded text-[10px] leading-relaxed text-slate-500 dark:text-slate-400">
              <span className="text-slate-850 dark:text-white font-bold block mb-1">租户权限规则 (Tenant Access):</span>
              <ul className="list-disc pl-3.5 space-y-1">
                <li><strong className="text-slate-700 dark:text-slate-200">租户 A (零售版)</strong>: 自选/情绪/题材/大V观点</li>
                <li><strong className="text-slate-700 dark:text-slate-200">租户 B (专业版)</strong>: 专业打板/资金流/持仓/预警</li>
                <li><strong className="text-slate-700 dark:text-slate-200">租户 C (旗舰版)</strong>: 独占游资大单/完整研报图谱</li>
              </ul>
            </div>

            {/* Widget checkboxes */}
            <div className="space-y-1.5">
              <span className="text-[10px] text-slate-500 block mb-1 font-bold">大屏组件显隐控制 (切换看板类型可重置)</span>
              
              {/* Left Column widgets */}
              {widgetDefinitions.filter(w => w.column === "left" && isWidgetAllowed(w.id)).length > 0 && (
                <div className="border-b border-slate-100 dark:border-[#222233]/40 pb-2">
                  <span className="text-[8px] text-slate-400 dark:text-slate-600 font-bold block mb-1">左栏组件 (LEFT COL)</span>
                  {widgetDefinitions.filter(w => w.column === "left" && isWidgetAllowed(w.id)).map(widget => (
                    <label key={widget.id} className="flex items-center justify-between text-xs py-1 cursor-pointer group">
                      <span className="text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">{widget.name}</span>
                      <button 
                        onClick={() => setEnabledWidgets(prev => ({ ...prev, [widget.id]: !prev[widget.id] }))}
                        className={`h-4 w-4 border flex items-center justify-center transition-colors ${
                          enabledWidgets[widget.id] ? "bg-rose-600 dark:bg-[#ff3366] border-rose-600 dark:border-[#ff3366]" : "border-slate-350 dark:border-[#333344] bg-white dark:bg-[#0c0c14]"
                        }`}
                      >
                        {enabledWidgets[widget.id] && <Check className="h-3 w-3 text-white" />}
                      </button>
                    </label>
                  ))}
                </div>
              )}

              {/* Middle Column widgets */}
              {(isWidgetAllowed("d3Graph") || isWidgetAllowed("lattice")) && (
                <div className="border-b border-slate-100 dark:border-[#222233]/40 py-2">
                  <span className="text-[8px] text-slate-400 dark:text-slate-600 font-bold block mb-1">中栏视图 (MIDDLE COL)</span>
                  {isWidgetAllowed("d3Graph") && (
                    <label className="flex items-center justify-between text-xs py-1 cursor-pointer group">
                      <span className="text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">🕸️ D3力导向拓扑关系</span>
                      <button 
                        onClick={() => setEnabledWidgets(prev => ({ ...prev, d3Graph: !prev.d3Graph }))}
                        className={`h-4 w-4 border flex items-center justify-center transition-colors ${
                          enabledWidgets.d3Graph ? "bg-rose-600 dark:bg-[#ff3366] border-rose-600 dark:border-[#ff3366]" : "border-slate-350 dark:border-[#333344] bg-white dark:bg-[#0c0c14]"
                        }`}
                      >
                        {enabledWidgets.d3Graph && <Check className="h-3 w-3 text-white" />}
                      </button>
                    </label>
                  )}
                  {isWidgetAllowed("lattice") && (
                    <label className="flex items-center justify-between text-xs py-1 cursor-pointer group">
                      <span className="text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">📈 打板概率分布格子</span>
                      <button 
                        onClick={() => setEnabledWidgets(prev => ({ ...prev, lattice: !prev.lattice }))}
                        className={`h-4 w-4 border flex items-center justify-center transition-colors ${
                          enabledWidgets.lattice ? "bg-rose-600 dark:bg-[#ff3366] border-rose-600 dark:border-[#ff3366]" : "border-slate-350 dark:border-[#333344] bg-white dark:bg-[#0c0c14]"
                        }`}
                      >
                        {enabledWidgets.lattice && <Check className="h-3 w-3 text-white" />}
                      </button>
                    </label>
                  )}
                </div>
              )}

              {/* Right Column widgets */}
              {widgetDefinitions.filter(w => w.column === "right" && isWidgetAllowed(w.id)).length > 0 && (
                <div className="pt-2">
                  <span className="text-[8px] text-slate-400 dark:text-slate-600 font-bold block mb-1">右栏组件 (RIGHT COL)</span>
                  {widgetDefinitions.filter(w => w.column === "right" && isWidgetAllowed(w.id)).map(widget => (
                    <label key={widget.id} className="flex items-center justify-between text-xs py-1 cursor-pointer group">
                      <span className="text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors flex items-center gap-1">
                        {widget.name}
                      </span>
                      <button 
                        onClick={() => setEnabledWidgets(prev => ({ ...prev, [widget.id]: !prev[widget.id] }))}
                        className={`h-4 w-4 border flex items-center justify-center transition-colors ${
                          enabledWidgets[widget.id] ? "bg-rose-600 dark:bg-[#ff3366] border-rose-600 dark:border-[#ff3366]" : "border-slate-350 dark:border-[#333344] bg-white dark:bg-[#0c0c14]"
                        }`}
                      >
                        {enabledWidgets[widget.id] && <Check className="h-3 w-3 text-white" />}
                      </button>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* DASHBOARD GRID - 3 COLUMNS */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 p-4 overflow-hidden">
        
        {/* LEFT COLUMN: WATCHLIST & SECTORS (~25% width) */}
        <section className="lg:col-span-1 flex flex-col gap-4 overflow-y-auto">
          {renderWidget("sentiment", "大盘情绪指数", false, MarketSentiment)}
          {renderWidget("watchlist", "自选股监控", false, Watchlist)}
          {renderWidget("limitUp", "涨停板追踪", false, LimitUpBoard)}
          {renderWidget("fundFlows", "板块资金流", false, FundFlows)}
        </section>

        {/* MIDDLE COLUMN: NETWORK GRAPH & GALTON BOARD (~50% width) */}
        <section className="lg:col-span-2 flex flex-col gap-4 overflow-y-auto">
          
          {/* D3.js Network Graph Mockup */}
          {enabledWidgets.d3Graph && (
            <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 flex flex-col relative overflow-hidden min-h-[350px] rounded shadow-sm dark:shadow-none">
              <div className="border-b border-slate-200 dark:border-[#222233] px-3 py-2 flex justify-between items-center bg-slate-50 dark:bg-[#12121e]">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300">🕸️ D3.js 力导向个股题材关系宇宙 (D3 RELATIONSHIP GRAPH)</span>
                <div className="flex gap-2 text-[10px] text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-rose-600 dark:bg-[#ff3366]" />个股</span>
                  <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#e5a93c]" />题材</span>
                  <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#00abc0] dark:bg-[#00e5ff]" />智能体</span>
                </div>
              </div>

              {/* Static SVG Force-Directed Graph Mockup */}
              <div className="flex-1 relative cursor-grab active:cursor-grabbing bg-slate-50 dark:bg-[#09090f]">
                <svg className="w-full h-full" style={{ minHeight: "350px" }}>
                  {/* Defs for glowing effects */}
                  <defs>
                    <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="5" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                    <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="5" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                    <filter id="glow-yellow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="5" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                  </defs>

                  {/* Connection lines */}
                  <g className="stroke-slate-200 dark:stroke-[#26263a]" strokeWidth="1.5">
                    <line x1="250" y1="200" x2="130" y2="100" />
                    <line x1="250" y1="200" x2="250" y2="70" />
                    <line x1="250" y1="70" x2="130" y2="100" />
                    <line x1="250" y1="70" x2="380" y2="100" />
                    <line x1="120" y1="310" x2="250" y2="200" />
                    <line x1="120" y1="310" x2="250" y2="330" />
                    <line x1="250" y1="330" x2="360" y2="280" />
                    <line x1="380" y1="100" x2="360" y2="280" />
                    <line x1="380" y1="200" x2="380" y2="100" />
                  </g>

                  {/* Relationship labels */}
                  <g fontSize="8" textAnchor="middle" fontFamily="monospace">
                    <rect x="175" y="140" width="36" height="10" className="fill-white dark:fill-[#09090f] stroke-slate-200 dark:stroke-[#26263a]" rx="3" />
                    <text x="193" y="148" className="fill-slate-500 dark:fill-[#4e4e6a]">买入</text>

                    <rect x="235" y="125" width="30" height="10" className="fill-white dark:fill-[#09090f] stroke-slate-200 dark:stroke-[#26263a]" rx="3" />
                    <text x="250" y="133" className="fill-slate-500 dark:fill-[#4e4e6a]">主导</text>

                    <rect x="295" y="75" width="40" height="10" className="fill-white dark:fill-[#09090f] stroke-slate-200 dark:stroke-[#26263a]" rx="3" />
                    <text x="315" y="83" className="fill-slate-500 dark:fill-[#4e4e6a]">板块龙头</text>

                    <rect x="170" y="245" width="36" height="10" className="fill-white dark:fill-[#09090f] stroke-slate-200 dark:stroke-[#26263a]" rx="3" />
                    <text x="188" y="253" className="fill-slate-500 dark:fill-[#4e4e6a]">重仓</text>
                  </g>

                  {/* Nodes */}
                  <g className="cursor-pointer group" onClick={() => setActiveNode("low-alt")} transform="translate(250, 70)">
                    <circle r="22" className="fill-amber-50/80 dark:fill-[#241e15] stroke-amber-500 dark:stroke-[#e5a93c]" strokeWidth="2.5" filter="url(#glow-yellow)" />
                    <text dy=".3em" textAnchor="middle" className="fill-amber-750 dark:fill-[#e5a93c] font-sans" fontSize="10" fontWeight="bold">低空经济</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("ai-count")} transform="translate(380, 200)">
                    <circle r="18" className="fill-amber-50/80 dark:fill-[#241e15] stroke-amber-500 dark:stroke-[#e5a93c]" strokeWidth="2" />
                    <text dy=".3em" textAnchor="middle" className="fill-amber-750 dark:fill-[#e5a93c] font-sans" fontSize="9" fontWeight="bold">AI算力</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("wanfeng")} transform="translate(130, 100)">
                    <circle r="20" className="fill-rose-50/80 dark:fill-[#2a1017] stroke-rose-600 dark:stroke-[#ff3366]" strokeWidth="2.5" filter="url(#glow-red)" />
                    <text dy=".3em" textAnchor="middle" className="fill-rose-600 dark:fill-[#ff3366] font-sans" fontSize="9" fontWeight="bold">万丰奥威</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("ningde")} transform="translate(250, 330)">
                    <circle r="20" className="fill-rose-50/80 dark:fill-[#2a1017] stroke-rose-600 dark:stroke-[#ff3366]" strokeWidth="2.5" filter="url(#glow-red)" />
                    <text dy=".3em" textAnchor="middle" className="fill-rose-600 dark:fill-[#ff3366] font-sans" fontSize="9" fontWeight="bold">宁德时代</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("byd")} transform="translate(360, 280)">
                    <circle r="18" className="fill-rose-50/80 dark:fill-[#2a1017] stroke-rose-600 dark:stroke-[#ff3366]" strokeWidth="2" />
                    <text dy=".3em" textAnchor="middle" className="fill-rose-600 dark:fill-[#ff3366] font-sans" fontSize="9" fontWeight="bold">比亚迪</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("fulan")} transform="translate(380, 100)">
                    <circle r="18" className="fill-rose-50/80 dark:fill-[#2a1017] stroke-rose-600 dark:stroke-[#ff3366]" strokeWidth="2" />
                    <text dy=".3em" textAnchor="middle" className="fill-rose-600 dark:fill-[#ff3366] font-sans" fontSize="9" fontWeight="bold">工业富联</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("yuzi")} transform="translate(250, 200)">
                    <circle r="24" className="fill-cyan-50/80 dark:fill-[#122530] stroke-[#00abc0] dark:stroke-[#00e5ff]" strokeWidth="2.5" filter="url(#glow-cyan)" />
                    <text dy="-.1em" textAnchor="middle" className="fill-[#009baf] dark:fill-[#00e5ff] font-sans" fontSize="9" fontWeight="bold">游资·游侠</text>
                    <text dy="1em" textAnchor="middle" className="fill-[#007b8b] dark:fill-[#0099aa]" fontSize="7" fontFamily="monospace">[AGENT]</text>
                  </g>

                  <g className="cursor-pointer group" onClick={() => setActiveNode("beixiang")} transform="translate(120, 310)">
                    <circle r="20" className="fill-cyan-50/80 dark:fill-[#122530] stroke-[#00abc0] dark:stroke-[#00e5ff]" strokeWidth="2" />
                    <text dy="-.1em" textAnchor="middle" className="fill-[#009baf] dark:fill-[#00e5ff] font-sans" fontSize="9" fontWeight="bold">北向资金</text>
                    <text dy="1.1em" textAnchor="middle" className="fill-[#007b8b] dark:fill-[#0099aa]" fontSize="6" fontFamily="monospace">[AGENT]</text>
                  </g>
                </svg>

                {activeNode && (
                  <div className="absolute bottom-3 left-3 right-3 bg-white/95 dark:bg-[#0d0d15]/95 border border-slate-250 dark:border-[#333344] p-3 text-xs flex flex-col gap-1.5 animate-in fade-in slide-in-from-bottom-2 duration-200 text-slate-800 dark:text-slate-350 shadow-lg rounded">
                    <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1">
                      <span className="font-bold text-rose-600 dark:text-[#ff3366] text-sm">
                        {activeNode === "low-alt" ? "题材: 低空经济" :
                         activeNode === "ai-count" ? "题材: AI算力" :
                         activeNode === "wanfeng" ? "个股: 万丰奥威 (301550)" :
                         activeNode === "ningde" ? "个股: 宁德时代 (300750)" :
                         activeNode === "byd" ? "个股: 比亚迪 (002594)" :
                         activeNode === "fulan" ? "个股: 工业富联 (601138)" :
                         activeNode === "yuzi" ? "智能体: 游资·游侠" : "智能体: 北向资金"}
                      </span>
                      <button onClick={() => setActiveNode(null)} className="text-slate-400 hover:text-slate-800 dark:hover:text-white">✕</button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-600 dark:text-slate-300">
                      <div>关联强度: <span className="text-slate-900 dark:text-white font-bold">HIGH (0.89)</span></div>
                      <div>大单追踪: <span className="text-rose-600 dark:text-[#ff3366] font-bold">主买流入+1.2亿</span></div>
                      <div>热点强度: <span className="text-amber-600 dark:text-[#e5a93c] font-bold">98 (极强)</span></div>
                      <div>博弈倾向: <span className="text-[#00abc0] dark:text-[#00e5ff] font-bold">持续做多</span></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Probability Lattice Card (Bell curve distribution plinko) */}
          {enabledWidgets.lattice && (
            <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 rounded shadow-sm dark:shadow-none">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300">📈 概率格子 · 涨停突破概率分布 (PROBABILITY LATTICE)</span>
              <div className="flex flex-col gap-2 bg-slate-50 dark:bg-[#09090f] p-4 rounded relative border border-slate-100 dark:border-[#1f1f2e]">
                <div className="absolute top-2 right-2 flex items-center gap-1.5 text-[8px] text-slate-550 dark:text-slate-500 font-bold">
                  <span className="inline-block w-2 h-2 bg-rose-600 dark:bg-[#ff3366] rounded-full" /> 涨停成功
                  <span className="inline-block w-2 h-2 bg-emerald-600 dark:bg-[#00ff88] rounded-full" /> 炸板回落
                </div>

                <div className="flex flex-col items-center gap-2 py-2 border-b border-slate-200 dark:border-[#222233]/40">
                  <div className="flex gap-6 text-slate-500 dark:text-slate-600 text-[10px]">
                    <span>1 阶</span><span>2 阶</span><span>3 阶</span><span>4 阶</span><span>5 阶</span>
                  </div>
                  <div className="flex gap-4">
                    {[...Array(9)].map((_, i) => (
                      <span key={i} className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
                    ))}
                  </div>
                  <div className="flex gap-4 px-2">
                    {[...Array(8)].map((_, i) => (
                      <span key={i} className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
                    ))}
                  </div>
                  <div className="flex gap-4">
                    {[...Array(9)].map((_, i) => (
                      <span key={i} className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
                    ))}
                  </div>
                </div>

                <div className="h-20 flex items-end gap-1.5 pt-2">
                  {[12, 18, 35, 65, 88, 75, 50, 30, 15, 8].map((h, i) => {
                    const isHigh = h > 40;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <div 
                          className={`w-full transition-all duration-500 ${isHigh ? "bg-rose-600 dark:bg-[#ff3366]" : "bg-emerald-600 dark:bg-[#00ff88]"}`}
                          style={{ height: `${h}%`, minHeight: "2px" }}
                        />
                        <span className="text-[7px] text-slate-500 dark:text-slate-600 font-bold">{i * 10}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

        </section>

        {/* RIGHT COLUMN: SIMULATION MONITOR & ReACT TIMELINE (~25% width) */}
        <section className="lg:col-span-1 flex flex-col gap-4 overflow-y-auto">
          
          {/* Decoupled widgets with roles permission lock */}
          {renderWidget("yuzi", "🕵️ 游资盘中大单", true, YuziMovement)}
          {renderWidget("concepts", "📡 题材热度轮动", false, ConceptRotation)}
          {renderWidget("popular", "🔥 热门人气个股", false, PopularStocks)}
          {renderWidget("longhu", "📋 龙虎榜单明细", true, LonghuBang)}
          {renderWidget("alerts", "🚨 盘中高频预警", false, MobileAlerts)}
          {renderWidget("portfolio", "💼 我的持仓股票", true, Portfolio)}
          {renderWidget("kol", "👥 大V盘中情绪", false, KolOpinions)}

          {/* OASIS Simulation Monitor Terminal (Always keeps Hacker dark theme for visuals) */}
          {enabledWidgets.logsTerminal && (
            <div className="border border-slate-200 dark:border-[#222233] bg-[#06060c] flex flex-col h-[280px] overflow-hidden rounded shrink-0 shadow-sm dark:shadow-none">
              <div className="border-b border-[#222233] px-3 py-2 flex justify-between items-center bg-[#12121e]">
                <span className="text-xs font-bold text-slate-350 dark:text-slate-300 flex items-center gap-1.5 font-mono">
                  <Terminal className="h-3.5 w-3.5 text-rose-600 dark:text-[#ff3366]" />
                  OASIS 实时仿真终端 (MONITOR)
                </span>
                <span className="text-[8px] bg-rose-50 dark:bg-[#ff3366]/20 border border-rose-250 dark:border-[#ff3366]/30 text-rose-650 dark:text-[#ff3366] px-1 py-0.2 font-bold animate-pulse">
                  SIMULATING
                </span>
              </div>
              
              <div 
                ref={logsContainerRef}
                className="flex-1 bg-[#06060c] p-2.5 overflow-y-auto text-[10px] font-mono leading-relaxed space-y-2 border-b border-[#222233]"
              >
                {logs.map((log, idx) => {
                  let color = "text-slate-400";
                  if (log.type === "action") color = "text-[#00e5ff]";
                  if (log.type === "success") color = "text-[#ff3366]";
                  if (log.type === "warning") color = "text-amber-500";
                  return (
                    <div key={idx} className="border-l-2 border-[#1f1f2e] pl-1.5">
                      <div className="flex justify-between text-[8px] text-slate-600 mb-0.5">
                        <span>[{log.time}] {log.sender}</span>
                      </div>
                      <p className={`${color} break-all font-mono`}>{log.message}</p>
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-3 text-[9px] text-slate-400 bg-[#12121e] p-2 text-center border-t border-[#1a1a2e]">
                <div>节点: <span className="text-white font-bold">341</span></div>
                <div>关系链: <span className="text-white font-bold">1,766</span></div>
                <div>智能体: <span className="text-[#00e5ff] font-bold">55</span></div>
              </div>
            </div>
          )}

          {/* ReACT Thinking Timeline Panel */}
          {enabledWidgets.reactTimeline && (
            <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 rounded shrink-0 shadow-sm dark:shadow-none">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-[#222233] pb-1.5 flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-rose-600 dark:text-[#ff3366]" />
                AI 研报 ReACT 思考时间轴 (DECISIONS)
              </span>
              
              <div className="text-[10px] space-y-3.5 relative pl-4 border-l border-slate-200 dark:border-[#222233]/80 py-1.5">
                <div className="relative">
                  <span className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-rose-600 dark:bg-[#ff3366] border-2 border-white dark:border-[#10101a] flex items-center justify-center text-[7px] text-white dark:text-[#10101a] font-extrabold">1</span>
                  <span className="text-rose-650 dark:text-[#ff3366] font-bold">THOUGHT (思考行为)</span>
                  <p className="text-slate-650 dark:text-slate-400 font-mono mt-0.5">"目前板块资金集中度异常升高，低空航空龙头万丰奥威连板突破。需校验锂电池上游碳酸锂期货价格走势对其采购成本的边际改善情况。"</p>
                </div>

                <div className="relative">
                  <span className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-[#00abc0] dark:bg-[#00e5ff] border-2 border-white dark:border-[#10101a] flex items-center justify-center text-[7px] text-white dark:text-[#10101a] font-extrabold">2</span>
                  <span className="text-[#00abc0] dark:text-[#00e5ff] font-bold">ACTION (工具调用)</span>
                  <p className="text-slate-650 dark:text-slate-400 font-mono mt-0.5">调用 API 网关检索 Zep 图谱检索工具: `InsightForge.query_graph("lithium carbonate futures")` 进行关联映射。</p>
                </div>

                <div className="relative">
                  <span className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-emerald-650 dark:bg-[#00ff88] border-2 border-white dark:border-[#10101a] flex items-center justify-center text-[7px] text-white dark:text-[#10101a] font-extrabold">3</span>
                  <span className="text-emerald-650 dark:text-[#00ff88] font-bold">OBSERVATION (环境返回)</span>
                  <p className="text-slate-650 dark:text-slate-400 font-mono mt-0.5">返回关联强度 -0.85 (强负相关)。碳酸锂主力合约下跌4.5%，证实万丰奥威等电池产业链下游企业成本红利空间增大。</p>
                </div>

                <div className="relative">
                  <span className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-slate-400 dark:bg-slate-500 border-2 border-white dark:border-[#10101a] flex items-center justify-center text-[7px] text-white dark:text-white font-extrabold">4</span>
                  <span className="text-slate-800 dark:text-white font-bold">DECISION (策略终判)</span>
                  <p className="text-rose-600 dark:text-[#ff3366] font-bold font-mono mt-0.5">"成本压力减轻 + 资金高频流入 $\rightarrow$ 调高万丰奥威与宁德时代今日突破概率至 85%，发布看多选股评级。"</p>
                </div>
              </div>
            </div>
          )}

        </section>

      </div>
    </div>
  );
}
