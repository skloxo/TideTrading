import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { api, type MonitorStats, type QuoteGatewayStatus, type SystemVersionInfo, type LiveStatus, type UserProfile } from "@/lib/api";
import { setAdminToken } from "@/lib/apiAuth";
import { Activity, Server, Database, FolderHeart, RefreshCw, Wifi, Loader2, Save, ShieldAlert, Lock, LogOut, ArrowUpCircle } from "lucide-react";

export function Monitor() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api.getSettingsProfile()
      .then((p) => {
        if (!alive) return;
        setProfile(p);
        setProfileLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setProfileLoading(false);
      });
    return () => { alive = false; };
  }, []);

  const [stats, setStats] = useState<MonitorStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quote status states
  const [quoteStatus, setQuoteStatus] = useState<QuoteGatewayStatus | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);

  // System version & one-click upgrade states
  const [adminUsername, setAdminUsername] = useState("admin");
  const [adminPassword, setAdminPassword] = useState("");
  const [elevating, setElevating] = useState(false);
  const [adminOldPassword, setAdminOldPassword] = useState("");
  const [adminNewPassword, setAdminNewPassword] = useState("");
  const [adminConfirmPassword, setAdminConfirmPassword] = useState("");
  const [changingPwd, setChangingPwd] = useState(false);

  // System version & one-click upgrade states
  const [versionInfo, setVersionInfo] = useState<SystemVersionInfo | null>(null);
  const [versionLoading, setVersionLoading] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [upgradeCountdown, setUpgradeCountdown] = useState(0);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const [liveStatus, setLiveStatus] = useState<LiveStatus | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);

  const fetchQuoteStatus = async (showLoading = false, showToast = false) => {
    if (showLoading) setQuoteLoading(true);
    try {
      const data = await api.getQuoteGatewayStatus();
      setQuoteStatus(data);
      if (showToast) {
        toast.success(isZh ? "行情网关状态刷新成功" : "Quote gateway status refreshed successfully");
      }
    } catch (err) {
      console.error("Failed to fetch quote gateway status:", err);
      if (showToast) {
        toast.error(isZh ? "刷新行情网关状态失败" : "Failed to refresh quote gateway status");
      }
    } finally {
      if (showLoading) setQuoteLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await api.getMonitorStats();
      setStats(data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch monitor stats:", err);
      setError(err?.message || "Failed to fetch stats");
    } finally {
      setStatsLoading(false);
    }
  };


  const fetchVersionInfo = async (showToast = false) => {
    try {
      setVersionLoading(true);
      const info = await api.getSystemVersion();
      setVersionInfo(info);
      if (showToast) {
        if (info.has_update) {
          toast.info(isZh ? `发现新版本: ${info.latest_version}，请点击升级` : `New version available: ${info.latest_version}`);
        } else {
          toast.success(isZh ? "已是最新版本" : "System is already up to date");
        }
      }
    } catch (err) {
      console.error("Failed to load version info:", err);
      if (showToast) {
        toast.error(isZh ? "检查版本更新失败，请重试" : "Failed to check system version");
      }
    } finally {
      setVersionLoading(false);
    }
  };

  const fetchLiveStatus = async (showLoading = false, showToast = false) => {
    if (showLoading) setLiveLoading(true);
    try {
      const data = await api.getLiveStatus();
      setLiveStatus(data);
      if (showToast) {
        toast.success(isZh ? "实盘引擎状态刷新成功" : "Live trading status refreshed successfully");
      }
    } catch (err) {
      console.error("Failed to fetch live status:", err);
      if (showToast) {
        toast.error(isZh ? "刷新实盘引擎状态失败" : "Failed to refresh live trading status");
      }
    } finally {
      if (showLoading) setLiveLoading(false);
    }
  };

  // Initial load and periodic stats/quote refresh
  useEffect(() => {
    if (profile?.role !== "admin") return;

    fetchStats();
    fetchQuoteStatus(true, false);
    fetchVersionInfo(false);
    fetchLiveStatus(true, false);

    const interval = setInterval(() => {
      fetchStats();
      fetchQuoteStatus(false, false);
      fetchLiveStatus(false, false);
    }, 10000); // Stats and Quote Gateway refresh every 10s
    return () => clearInterval(interval);
  }, [profile]);

  // Countdown timer for upgrade modal
  useEffect(() => {
    if (!showUpgradeModal) return;
    setUpgradeCountdown(30);
    const interval = setInterval(() => {
      setUpgradeCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          window.location.reload();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [showUpgradeModal]);

  const handleTriggerUpgrade = async () => {
    if (upgrading) return;
    setUpgrading(true);
    try {
      await api.triggerSystemUpdate();
      setShowUpgradeModal(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "升级触发失败";
      toast.error(msg);
    } finally {
      setUpgrading(false);
    }
  };

  const handleAdminElevate = async (e: FormEvent) => {
    e.preventDefault();
    if (!adminPassword) return;
    setElevating(true);
    try {
      const res = await api.adminElevate({ username: adminUsername, password: adminPassword });
      setAdminToken(res.admin_token);
      toast.success("管理员提权成功！");
      setAdminPassword("");
      window.location.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "提权失败，请检查账号密码");
    } finally {
      setElevating(false);
    }
  };

  const handleAdminChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    if (adminNewPassword !== adminConfirmPassword) {
      toast.error("两次输入的新密码不一致");
      return;
    }
    setChangingPwd(true);
    try {
      await api.adminChangePassword({ old_password: adminOldPassword, new_password: adminNewPassword });
      toast.success("管理员密码修改成功！");
      setAdminOldPassword("");
      setAdminNewPassword("");
      setAdminConfirmPassword("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "密码修改失败");
    } finally {
      setChangingPwd(false);
    }
  };

  const handleAdminDeelevate = () => {
    setAdminToken("");
    toast.success("已退出管理员提权状态");
    window.location.reload();
  };

  if (profileLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center text-muted-foreground animate-pulse">
        {isZh ? "正在验证访问权限..." : "Verifying access permissions..."}
      </div>
    );
  }

  if (!profileLoading && profile?.role !== "admin") {
    const fieldClass = "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {isZh ? "服务配置与性能监控" : "Service Configuration & Monitor"}
            </h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              {isZh ? "实时监控进程资源占用及系统升级维护。" : "Monitor running processes and handle system updates in real-time."}
            </p>
          </div>
        </div>
        <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4 max-w-xl">
          <div className="flex items-center gap-2 border-b pb-3">
            <ShieldAlert className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">管理员提权 (系统运维)</h2>
          </div>
          <p className="text-xs text-muted-foreground">此页面属于系统运维管理功能，仅限系统管理员访问。请输入管理员账号密码进行提权。</p>
          <form onSubmit={handleAdminElevate} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">管理员账号</span>
                <input type="text" value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} className={fieldClass} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">管理员密码</span>
                <input type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} className={fieldClass} placeholder="请输入管理员密码" />
              </label>
            </div>
            <button type="submit" disabled={elevating} className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm">
              {elevating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
              进行管理员提权
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      {/* Title */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {isZh ? "服务配置与性能监控" : "Service Configuration & Monitor"}
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {isZh
              ? "实时监控进程资源占用、租户接入密钥管控及系统升级维护。"
              : "Monitor running processes, manage tenant access credentials, and handle system updates in real-time."}
          </p>
        </div>
        <button
          onClick={async () => {
            await Promise.all([
              fetchStats(),
              fetchQuoteStatus(true, false),
              fetchVersionInfo(false),
              fetchLiveStatus(true, false)
            ]);
            toast.success(isZh ? "监控看板数据已全部更新" : "All monitor dashboard stats updated");
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border border-border/80 bg-background hover:bg-muted transition text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {isZh ? "刷新全部" : "Refresh All"}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Grid of Stats */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {/* Memory Usage */}
        <div className="rounded-lg border bg-card p-5 shadow-sm space-y-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {isZh ? "内存占用" : "Memory Usage"}
            </span>
            <Server className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : `${stats?.memory_usage_mb.toFixed(1) || "0.0"} MB`}
            </div>
            <div className="w-full bg-muted rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-primary h-1.5 rounded-full transition-all duration-500"
                style={{ width: stats ? `${Math.min((stats.memory_usage_mb / 1024) * 100, 100)}%` : "0%" }}
              />
            </div>
          </div>
        </div>

        {/* Active Tenants */}
        <div className="rounded-lg border bg-card p-5 shadow-sm space-y-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {isZh ? "有效租户" : "Active Tenants"}
            </span>
            <Activity className="h-4 w-4 text-green-500" />
          </div>
          <div>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : stats?.active_tenants.length || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {isZh ? "已注册并分配密钥的租户" : "Registered tenants with API keys"}
            </p>
          </div>
        </div>

        {/* Total Sessions */}
        <div className="rounded-lg border bg-card p-5 shadow-sm space-y-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {isZh ? "总会话数" : "Total Sessions"}
            </span>
            <FolderHeart className="h-4 w-4 text-purple-500" />
          </div>
          <div>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : stats?.total_sessions || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {isZh ? "沙箱对话持久化目录数" : "Number of sandbox session directories"}
            </p>
          </div>
        </div>

        {/* Total Runs */}
        <div className="rounded-lg border bg-card p-5 shadow-sm space-y-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {isZh ? "执行记录" : "Strategy Runs"}
            </span>
            <Database className="h-4 w-4 text-orange-500" />
          </div>
          <div>
            <div className="text-2xl font-bold">
              {statsLoading ? "..." : stats?.total_runs || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {isZh ? "量化执行与回测历史记录" : "Quantitative strategy & backtest history"}
            </p>
          </div>
        </div>
      </div>

      {/* Background Services & Data Status Section */}
      <div className="space-y-3">
        <h2 className="text-base font-semibold tracking-tight text-foreground">
          {isZh ? "数据对账与后台服务监控" : "Data Reconciliation & Background Services"}
        </h2>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {/* Data Maintenance Card */}
          <div className="rounded-lg border bg-card p-5 shadow-sm space-y-3 flex flex-col justify-between relative overflow-hidden group">
            {/* Ambient decorative effect */}
            <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-xl pointer-events-none group-hover:bg-primary/10 transition-all duration-500" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4.5 w-4.5 text-primary" />
                <span className="text-sm font-semibold text-foreground">
                  {isZh ? "收盘数据维护与自愈" : "Data Sync & Self-Healing"}
                </span>
              </div>
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase transition ${
                stats?.services?.data_maintenance?.running 
                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}>
                {stats?.services?.data_maintenance?.running ? (isZh ? "运行中" : "RUNNING") : (isZh ? "已停止" : "STOPPED")}
              </span>
            </div>
            
            <div className="space-y-1.5 text-xs text-muted-foreground pt-1">
              <div className="flex justify-between">
                <span>{isZh ? "历史对账区间" : "Historical Range"}:</span>
                <span className="font-mono text-foreground font-medium">{stats?.services?.data_maintenance?.historical_range || "N/A"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>{isZh ? "今日同步状态" : "Today's Status"}:</span>
                <span className={`font-semibold ${
                  stats?.services?.data_maintenance?.today_status === "已完成"
                    ? "text-emerald-500"
                    : stats?.services?.data_maintenance?.today_status === "同步延迟/失败"
                    ? "text-destructive font-bold animate-pulse"
                    : "text-amber-500"
                }`}>
                  {stats?.services?.data_maintenance?.today_status || (isZh ? "等待中" : "Pending")}
                </span>
              </div>
              <div className="flex justify-between">
                <span>{isZh ? "已监控股票数" : "Monitored Stocks"}:</span>
                <span className="text-foreground font-medium">{stats?.services?.data_maintenance?.total_stocks || 0} {isZh ? "只" : "stocks"}</span>
              </div>
              <div className="flex justify-between">
                <span>{isZh ? "公共数据库大小" : "Market DB Size"}:</span>
                <span className="text-foreground font-medium">{stats?.services?.data_maintenance?.db_size_mb || 0} MB</span>
              </div>
            </div>
          </div>

          {/* THS Watchlist Sync Card */}
          <div className="rounded-lg border bg-card p-5 shadow-sm space-y-3 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/5 rounded-full blur-xl pointer-events-none group-hover:bg-green-500/10 transition-all duration-500" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wifi className="h-4.5 w-4.5 text-green-500" />
                <span className="text-sm font-semibold text-foreground">
                  {isZh ? "同花顺自选双向同步" : "THS Watchlist Sync"}
                </span>
              </div>
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase transition ${
                stats?.services?.ths_sync?.running 
                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}>
                {stats?.services?.ths_sync?.running ? (isZh ? "运行中" : "RUNNING") : (isZh ? "已停止" : "STOPPED")}
              </span>
            </div>
            
            <p className="text-xs text-muted-foreground leading-relaxed pt-1">
              {isZh 
                ? "基于 Web Cookie 自动检测并多租户同步同花顺自选股，若未配置凭据将自动降级为本地隔离数据库自选模式。" 
                : "Bi-directional background synchronization of portfolios with Tonghuashun over secure cookies."}
            </p>
          </div>

          {/* Watchlist Real-time Alert Card */}
          <div className="rounded-lg border bg-card p-5 shadow-sm space-y-3 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl pointer-events-none group-hover:bg-purple-500/10 transition-all duration-500" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4.5 w-4.5 text-purple-500" />
                <span className="text-sm font-semibold text-foreground">
                  {isZh ? "自选股秒级高频预警" : "Watchlist High-Freq Alert"}
                </span>
              </div>
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase transition ${
                stats?.services?.watchlist_monitor?.running 
                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}>
                {stats?.services?.watchlist_monitor?.running ? (isZh ? "运行中" : "RUNNING") : (isZh ? "已停止" : "STOPPED")}
              </span>
            </div>
            
            <p className="text-xs text-muted-foreground leading-relaxed pt-1">
              {isZh 
                ? "在交易时间段内以秒级频率高频轮询自选股的价格、涨跌幅、及异动状态，并在触发冷却规则后向通道推送通知。" 
                : "High-frequency real-time stock price and alerts dispatcher during official trading hours."}
            </p>
          </div>

          {/* Xueqiu Portfolio Watcher Card */}
          <div className="rounded-lg border bg-card p-5 shadow-sm space-y-3 flex flex-col justify-between relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/5 rounded-full blur-xl pointer-events-none group-hover:bg-orange-500/10 transition-all duration-500" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="h-4.5 w-4.5 text-orange-500" />
                <span className="text-sm font-semibold text-foreground">
                  {isZh ? "雪球大V组合盯哨" : "Xueqiu Portfolio Watcher"}
                </span>
              </div>
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase transition ${
                stats?.services?.xueqiu_watcher?.running 
                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                  : "bg-destructive/10 text-destructive border border-destructive/20"
              }`}>
                {stats?.services?.xueqiu_watcher?.running ? (isZh ? "运行中" : "RUNNING") : (isZh ? "已停止" : "STOPPED")}
              </span>
            </div>
            
            <p className="text-xs text-muted-foreground leading-relaxed pt-1">
              {isZh 
                ? "长连接或短周期高频监控配置中指定的雪球投资组合与大 V 自选股列表，在其发生调仓或调入调出时即时收集。" 
                : "Real-time crawler and notifier for combinations rebalancing and target portfolio actions."}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Realtime Quote Gateway, Live Engine & System Version Cards */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Quote Gateway */}
          {quoteStatus && (
            <div className="rounded-lg border bg-card p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                    <Wifi className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold">{isZh ? "实时行情网关状态" : "Realtime Quote Gateway"}</h2>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => fetchQuoteStatus(true, true)}
                  disabled={quoteLoading}
                  className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent transition cursor-pointer disabled:opacity-60"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${quoteLoading ? "animate-spin" : ""}`} />
                  {isZh ? "刷新" : "Refresh"}
                </button>
              </div>
              <div className="grid gap-4 grid-cols-2">
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "网关状态" : "Status"}</span>
                  <div className="text-xs font-semibold">{quoteStatus.status}</div>
                </div>
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "平均测速延迟" : "Avg Latency"}</span>
                  <div className="text-xs font-semibold font-mono">{quoteStatus.latency_ms} ms</div>
                </div>
              </div>
            </div>
          )}

          {/* Live Trading Engine */}
          {liveStatus && (
            <div className="rounded-lg border bg-card p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                    <Activity className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold">{isZh ? "实盘引擎监控" : "Live Trading Monitor"}</h2>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => fetchLiveStatus(true, true)}
                  disabled={liveLoading}
                  className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent transition cursor-pointer disabled:opacity-60"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${liveLoading ? "animate-spin" : ""}`} />
                  {isZh ? "刷新" : "Refresh"}
                </button>
              </div>
              <div className="grid gap-4 grid-cols-2">
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "全局熔断状态" : "Global Halt"}</span>
                  <div className="text-xs font-semibold">{liveStatus.global_halted ? "HALTED" : "NORMAL"}</div>
                </div>
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "活跃运行器" : "Active Runners"}</span>
                  <div className="text-xs font-semibold font-mono">{liveStatus.brokers.filter(b => b.runner?.alive).length}</div>
                </div>
              </div>
            </div>
          )}

          {/* System Version */}
          {versionInfo && (
            <div className="rounded-lg border bg-card p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                    <Server className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold">{isZh ? "系统版本管理" : "System Version"}</h2>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => fetchVersionInfo(true)}
                  disabled={versionLoading}
                  className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent transition cursor-pointer disabled:opacity-60"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${versionLoading ? "animate-spin" : ""}`} />
                  {isZh ? "检查" : "Check"}
                </button>
              </div>
              <div className="grid gap-4 grid-cols-2">
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "当前版本" : "Current"}</span>
                  <div className="text-xs font-bold font-mono">{versionInfo.current_version}</div>
                </div>
                <div className="rounded-md border bg-muted/10 p-3 flex flex-col justify-between">
                  <span className="text-[10px] text-muted-foreground">{isZh ? "最新版本" : "Latest"}</span>
                  <div className="text-xs font-bold font-mono">{versionInfo.latest_version}</div>
                </div>
              </div>
              {versionInfo.has_update && (
                <button
                  type="button"
                  onClick={handleTriggerUpgrade}
                  disabled={upgrading}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-amber-600 transition disabled:opacity-70 cursor-pointer mt-4"
                >
                  {upgrading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUpCircle className="h-4 w-4" />}
                  {upgrading ? (isZh ? "正在触发升级…" : "Upgrading...") : (isZh ? `立即升级到 ${versionInfo.latest_version}` : `Upgrade to ${versionInfo.latest_version}`)}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Admin Control Card */}
      {(() => {
        const fieldClass = "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";
        return (
          <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4 max-w-xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-primary" />
                <h2 className="text-base font-semibold">管理员身份管理</h2>
              </div>
              <button type="button" onClick={handleAdminDeelevate} className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted transition cursor-pointer">
                <LogOut className="h-3.5 w-3.5" />
                退出提权
              </button>
            </div>
            <p className="text-xs text-muted-foreground">您当前处于系统管理员身份，可以修改管理员账户密码。</p>
            <form onSubmit={handleAdminChangePassword} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <label className="block space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">原管理员密码</span>
                  <input type="password" value={adminOldPassword} onChange={(e) => setAdminOldPassword(e.target.value)} className={fieldClass} placeholder="旧密码" required />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">新管理员密码</span>
                  <input type="password" value={adminNewPassword} onChange={(e) => setAdminNewPassword(e.target.value)} className={fieldClass} placeholder="新密码" required />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">确认新密码</span>
                  <input type="password" value={adminConfirmPassword} onChange={(e) => setAdminConfirmPassword(e.target.value)} className={fieldClass} placeholder="确认新密码" required />
                </label>
              </div>
              <button type="submit" disabled={changingPwd} className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm">
                {changingPwd ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                保存管理员密码
              </button>
            </form>
          </div>
        );
      })()}

      {/* --- MODALS --- */}

      {/* Upgrade Countdown Modal */}

      {/* 2. Upgrade Countdown Modal */}
      {showUpgradeModal && createPortal(
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/70 backdrop-blur-lg">
          <div className="relative flex flex-col items-center gap-6 rounded-2xl border border-white/10 bg-white/5 p-10 shadow-2xl backdrop-blur-xl text-center max-w-sm w-full mx-4">
            <div className="relative flex items-center justify-center" style={{ height: "128px", width: "128px" }}>
              <svg className="absolute h-28 w-28 -rotate-90 animate-spin-slow" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
                <circle
                  cx="50" cy="50" r="44" fill="none" stroke="rgba(251,191,36,0.7)" strokeWidth="6" strokeLinecap="round"
                  strokeDasharray={`${(upgradeCountdown / 30) * 276.5} 276.5`}
                  style={{ transition: "stroke-dasharray 1s linear" }}
                />
              </svg>
              <span className="text-4xl font-bold text-white tabular-nums">{upgradeCountdown}</span>
            </div>

            <div style={{ marginTop: "16px" }}>
              <h3 className="text-xl font-semibold text-white mb-2">系统升级中…</h3>
              <p className="text-sm text-white/70 leading-relaxed">
                后台正在拉取最新代码并重启服务<br />
                页面将在 <span className="font-bold text-amber-400">{upgradeCountdown}</span> 秒后自动刷新
              </p>
            </div>

            <div className="flex items-center gap-2 text-white/50 text-xs">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              服务重启中，请稍候…
            </div>

            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm text-white hover:bg-white/20 transition cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              立即刷新页面
            </button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
