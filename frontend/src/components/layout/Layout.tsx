import { useTranslation } from "react-i18next";
import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Activity, BarChart3, Bot, ChevronDown, ChevronRight, FileText, Languages, Moon, Sun, Plus, Trash2, Pencil, MessageSquare, ChevronsLeft, ChevronsRight, Settings, Layers, Loader2, Menu, X, Terminal, Compass, Cpu, KeyRound, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDarkMode } from "@/hooks/useDarkMode";
import { api, isAuthRequiredError, type SessionItem, type UserProfile } from "@/lib/api";
import { useAgentStore } from "@/stores/agent";
import { ConnectionBanner } from "@/components/layout/ConnectionBanner";
import { ICPFooter } from "@/components/layout/ICPFooter";
import { clearApiAuthKey, getApiAuthKey } from "@/lib/apiAuth";

export function Layout() {
  const { t, i18n: i18nHook } = useTranslation();
  const isZhLayout = i18nHook.language === "zh-CN";
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { dark, toggle } = useDarkMode();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const sseStatus = useAgentStore(s => s.sseStatus);
  const sseRetryAttempt = useAgentStore(s => s.sseRetryAttempt);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("qa-sidebar") === "collapsed");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const isCollapsed = collapsed && !isMobile;

  const activeSessionId = searchParams.get("session");
  const streamingSessionId = useAgentStore(s => s.streamingSessionId);

  const [profileLoading, setProfileLoading] = useState(true);
  const [authFailed, setAuthFailed] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [devopsExpanded, setDevopsExpanded] = useState(false);

  useEffect(() => {
    const isDevopsPath =
      pathname === "/monitor" ||
      pathname === "/logs" ||
      (pathname === "/settings" && searchParams.get("tab") === "project");
    if (isDevopsPath) {
      setDevopsExpanded(true);
    }
  }, [pathname, searchParams]);

  const NAV = [
    { to: "/", icon: BarChart3, label: t('layout.home') },
    { to: "/dashboard", icon: Compass, label: i18nHook.language === "zh-CN" ? "数据大屏" : "Live Dashboard" },
    { to: "/agent", icon: Bot, label: t('layout.agent') },
    { to: "/runtime", icon: Activity, label: t('layout.runtime') },
    { to: "/reports", icon: FileText, label: t('layout.reports') },
    { to: "/xueqiu", icon: Activity, label: i18nHook.language === "zh-CN" ? "雪球监控" : "Xueqiu Watcher" },
    { to: "/alpha-zoo", icon: Layers, label: t('layout.alphaZoo') },
    { to: "/correlation", icon: BarChart3, label: t('layout.correlation') },
    { to: "/settings", icon: Settings, label: t('layout.settings') },
  ];

  useEffect(() => {
    let alive = true;
    api.getSettingsProfile()
      .then((p) => {
        if (!alive) return;
        setProfile(p);
        setAuthFailed(false);
        setProfileLoading(false);
      })
      .catch((err) => {
        if (!alive) return;
        if (isAuthRequiredError(err)) {
          setAuthFailed(true);
        }
        setProfileLoading(false);
      });
    return () => { alive = false; };
  }, []);

  // Redirect to /login if auth fails (no tenant key stored)
  useEffect(() => {
    const key = getApiAuthKey();
    if (!key) {
      navigate("/login", { replace: true });
      return;
    }
    if (!profileLoading && authFailed) {
      navigate("/login", { replace: true });
    }
  }, [profileLoading, authFailed, navigate]);

  useEffect(() => {
    localStorage.setItem("qa-sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  const loadSessions = () => {
    api.listSessions()
      .then((list) => setSessions(Array.isArray(list) ? list : []))
      .catch(() => {})
      .finally(() => setSessionsLoading(false));
  };

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Load sessions on mount. Also refresh when navigating TO /agent or when
  // the active session changes (covers new session creation from Agent).
  const isAgentPage = pathname.startsWith("/agent");
  useEffect(() => {
    if (!authFailed && !profileLoading) {
      loadSessions();
    }
  }, [isAgentPage, activeSessionId, authFailed, profileLoading]);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const deleteSession = async (sid: string) => {
    try {
      await api.deleteSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    } catch { /* ignore */ }
    setDeleteTarget(null);
  };

  const renameSession = async (sid: string) => {
    if (!renameValue.trim()) { setRenameTarget(null); return; }
    try {
      await api.renameSession(sid, renameValue.trim());
      setSessions((prev) => prev.map((s) => s.session_id === sid ? { ...s, title: renameValue.trim() } : s));
    } catch { /* ignore */ }
    setRenameTarget(null);
  };

  if (profileLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (authFailed) {
    // Redirect handled in useEffect above — show spinner while redirecting
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background relative overflow-hidden rtl:flex-row-reverse">
      {/* Mobile Drawer Overlay Backdrop */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar - responsive absolute drawer on mobile */}
      <aside className={cn(
        "border-e bg-card flex flex-col shrink-0 transition-all duration-200 z-50 overflow-visible",
        "max-md:fixed max-md:top-0 max-md:bottom-0 max-md:left-0 max-md:w-64 max-md:shadow-2xl",
        mobileOpen ? "max-md:translate-x-0" : "max-md:-translate-x-full",
        isCollapsed ? "md:w-12" : "md:w-64"
      )}>

        {/* Brand */}
        <div className={cn("border-b", isCollapsed ? "p-2 flex justify-center" : "p-4")}>
          <Link to="/" className={cn("flex items-center font-bold text-base tracking-tight", isCollapsed ? "justify-center" : "gap-2")}>
            <img src="/logo.png" className="h-5 w-5 rounded-md object-contain shrink-0" alt="Logo" />
            {!isCollapsed && (
              <span className="text-foreground">
                {i18nHook.language === "zh-CN" ? "潮汐投研" : "TideTrading"}
              </span>
            )}
          </Link>
        </div>

        {/* Nav */}
        <nav className={cn("space-y-0.5", isCollapsed ? "p-1" : "p-2")}>
          {NAV.map(({ to, icon: Icon, label }) => {
            const text = label;
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center rounded-md text-sm transition-colors",
                  isCollapsed ? "justify-center p-2" : "gap-3 px-3 py-2",
                  (to === "/" ? pathname === "/" : pathname.startsWith(to))
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={isCollapsed ? text : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {!isCollapsed && text}
              </Link>
            );
          })}

          {/* Collapsible Project DevOps Menu for Admin */}
          <div className="mt-2 space-y-0.5 border-t pt-2 border-border/40">
            {/* DevOps Main Entry */}
            <button
              onClick={() => setDevopsExpanded(!devopsExpanded)}
              className={cn(
                "w-full flex items-center rounded-md text-sm transition-colors text-left",
                isCollapsed ? "justify-center p-2" : "justify-between px-3 py-2",
                (pathname === "/monitor" || pathname === "/logs" || (pathname === "/settings" && searchParams.get("tab") === "project"))
                  ? "bg-primary/5 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title={isCollapsed ? (i18nHook.language === "zh-CN" ? "项目运维" : "DevOps") : undefined}
            >
              <div className="flex items-center gap-3">
                <Cpu className="h-4 w-4 shrink-0 text-amber-500/80" aria-hidden="true" />
                {!isCollapsed && (
                  <span>
                    {i18nHook.language === "zh-CN" ? "项目运维" : "DevOps"}
                  </span>
                )}
              </div>
              {!isCollapsed && (
                devopsExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5 opacity-60" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 opacity-60" />
                )
              )}
            </button>

            {/* DevOps Sub-Menus */}
            {devopsExpanded && (
              <div className={cn("space-y-0.5", !isCollapsed && "pl-4")}>
                <Link
                  to="/monitor"
                  className={cn(
                    "flex items-center rounded-md text-xs transition-colors",
                    isCollapsed ? "justify-center p-2" : "gap-2.5 px-3 py-1.5",
                    pathname === "/monitor"
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground/80 hover:bg-muted hover:text-foreground"
                  )}
                  title={isCollapsed ? (i18nHook.language === "zh-CN" ? "服务看板" : "Monitor") : undefined}
                >
                  <Activity className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {!isCollapsed && (i18nHook.language === "zh-CN" ? "服务看板" : "Monitor")}
                </Link>

                <Link
                  to="/project-settings"
                  className={cn(
                    "flex items-center rounded-md text-xs transition-colors",
                    isCollapsed ? "justify-center p-2" : "gap-2.5 px-3 py-1.5",
                    pathname === "/project-settings"
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground/80 hover:bg-muted hover:text-foreground"
                  )}
                  title={isCollapsed ? (i18nHook.language === "zh-CN" ? "项目设置" : "Project Settings") : undefined}
                >
                  <Settings className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {!isCollapsed && (i18nHook.language === "zh-CN" ? "项目设置" : "Project Settings")}
                </Link>

                <Link
                  to="/logs"
                  className={cn(
                    "flex items-center rounded-md text-xs transition-colors",
                    isCollapsed ? "justify-center p-2" : "gap-2.5 px-3 py-1.5",
                    pathname === "/logs"
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground/80 hover:bg-muted hover:text-foreground"
                  )}
                  title={isCollapsed ? (i18nHook.language === "zh-CN" ? "运行日志" : "Runtime Logs") : undefined}
                >
                  <Terminal className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {!isCollapsed && (i18nHook.language === "zh-CN" ? "运行日志" : "Runtime Logs")}
                </Link>

                <Link
                  to="/tenants"
                  className={cn(
                    "flex items-center rounded-md text-xs transition-colors",
                    isCollapsed ? "justify-center p-2" : "gap-2.5 px-3 py-1.5",
                    pathname === "/tenants"
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground/80 hover:bg-muted hover:text-foreground"
                  )}
                  title={isCollapsed ? (i18nHook.language === "zh-CN" ? "租户管理" : "Tenants") : undefined}
                >
                  <KeyRound className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {!isCollapsed && (i18nHook.language === "zh-CN" ? "租户管理" : "Tenants")}
                </Link>
              </div>
            )}
          </div>
        </nav>

        {/* Sessions — hidden when collapsed */}
        {!isCollapsed && (
          <div className="flex-1 overflow-auto border-t mt-2 flex flex-col">
            <div className="flex items-center justify-between px-4 py-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <MessageSquare className="h-3.5 w-3.5" />
                {t('layout.sessions')}
              </span>
              <Link
                to="/agent"
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                title={t('layout.newChat')}
              >
                <Plus className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="px-2 pb-2 space-y-0.5 overflow-auto flex-1">
              {sessionsLoading ? (
                <div className="space-y-1.5 px-2 py-1">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-7 rounded-md bg-muted/50 animate-pulse" />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted-foreground/60">{t('layout.noSessions')}</p>
              ) : null}
              {sessions.map((s) => {
                const isActive = s.session_id === activeSessionId;
                const isDeleting = deleteTarget === s.session_id;
                const isRenaming = renameTarget === s.session_id;
                return (
                  <div key={s.session_id} className="group relative flex items-center">
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") renameSession(s.session_id); if (e.key === "Escape") setRenameTarget(null); }}
                        onBlur={() => renameSession(s.session_id)}
                        className="flex-1 min-w-0 ps-3 pe-2 py-1 rounded-md text-xs border border-primary bg-background outline-none"
                      />
                    ) : (
                      <Link
                        to={`/agent?session=${s.session_id}`}
                        className={cn(
                          "flex-1 min-w-0 ps-3 pe-14 py-1.5 rounded-md text-xs transition-colors truncate block border-s-2",
                          isActive
                            ? "border-s-primary bg-primary/10 text-primary font-medium"
                            : "border-s-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                        title={s.title || s.session_id}
                      >
                        <span className="flex items-center gap-1.5">
                          {streamingSessionId === s.session_id ? (
                            <Loader2 className="h-3 w-3 shrink-0 animate-spin text-primary" />
                          ) : (
                            <span className={cn(
                              "h-1.5 w-1.5 rounded-full shrink-0",
                              isActive ? "bg-primary/70" : "bg-muted-foreground/40"
                            )} />
                          )}
                          {s.title || s.session_id.slice(0, 16)}
                        </span>
                      </Link>
                    )}
                    {!isRenaming && isDeleting ? (
                      <div className="absolute right-0.5 flex items-center gap-0.5">
                        <button onClick={() => deleteSession(s.session_id)} className="p-1 text-danger hover:bg-danger/10 rounded text-[10px] font-medium">{t('layout.confirm')}</button>
                        <button onClick={() => setDeleteTarget(null)} className="p-1 text-muted-foreground hover:bg-muted rounded text-[10px]">{t('layout.cancel')}</button>
                      </div>
                    ) : !isRenaming ? (
                      <div className="absolute right-1 opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setRenameTarget(s.session_id); setRenameValue(s.title || ""); }}
                          className="p-1 text-muted-foreground hover:text-foreground rounded"
                          title={t('layout.rename')}
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteTarget(s.session_id); }}
                          className="p-1 text-muted-foreground hover:text-danger rounded"
                          title={t('layout.delete')}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Spacer when collapsed */}
        {isCollapsed && <div className="flex-1" />}

        {/* Footer */}
        <div className={cn("border-t", isCollapsed ? "p-1 flex flex-col items-center gap-1" : "p-3 space-y-2")}>
          {isCollapsed ? (
            <>
              {/* 1. Expand sidebar */}
              <button
                onClick={() => setCollapsed(false)}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={t('layout.expand')}
              >
                <ChevronsRight className="h-3.5 w-3.5" />
              </button>
              {/* 2. Toggle dark/light */}
              <button
                onClick={toggle}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={dark ? t('layout.light') : t('layout.dark')}
              >
                {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </button>
              {/* 3. Toggle language */}
              <button
                onClick={() => {
                  const nextLang = i18nHook.language === "zh-CN" ? "en" : "zh-CN";
                  i18nHook.changeLanguage(nextLang).catch(console.error);
                }}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={i18nHook.language === "zh-CN" ? "Switch to English" : "切换为中文"}
              >
                <Languages className="h-3.5 w-3.5" />
              </button>
              {/* 4. Exit tenant */}
              {profile?.is_tenant && (
                <button
                  onClick={() => {
                    clearApiAuthKey();
                    navigate("/login", { replace: true });
                  }}
                  className="p-1.5 text-muted-foreground hover:text-destructive rounded transition-colors"
                  title={isZhLayout ? "退出租户" : "Log out"}
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              )}
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <button
                  onClick={toggle}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                  {dark ? t('layout.light') : t('layout.dark')}
                </button>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setCollapsed(true)}
                    className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors md:block hidden"
                    title={t('layout.collapse')}
                  >
                    <ChevronsLeft className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <LanguageSwitcher />
              </div>
              {/* Identity footer */}
              {profile && (
                <div className="text-[10px] text-muted-foreground/50 border-t pt-1.5 border-border/30 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate" title={profile.name}>User: {profile.name}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="uppercase">{profile.role}</span>
                      {profile.is_tenant && (
                        <button
                          onClick={() => {
                            clearApiAuthKey();
                            navigate("/login", { replace: true });
                          }}
                          className="p-0.5 text-muted-foreground/60 hover:text-destructive transition-colors animate-pulse"
                          title={isZhLayout ? "退出租户" : "Log out"}
                        >
                          <LogOut className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
              <ICPFooter className="border-t border-border/30 mt-2 pt-2 !pb-0" />
            </>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header Bar */}
        <header className="flex h-14 items-center justify-between border-b bg-card px-4 md:hidden shrink-0">
          <Link to="/" className="flex items-center font-bold text-base tracking-tight gap-2">
            <BarChart3 className="h-5 w-5 text-primary shrink-0" />
            <span className="text-foreground">
              {i18nHook.language === "zh-CN" ? "潮汐投研" : "TideTrading"}
            </span>
          </Link>
          <button 
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-2 text-muted-foreground hover:text-foreground rounded transition-colors"
            title="Menu"
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </header>

        <ConnectionBanner status={sseStatus} retryAttempt={sseRetryAttempt} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Language switcher — toggles instantly between English and Chinese.
// ---------------------------------------------------------------------------
function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";

  const toggleLang = () => {
    const nextLang = isZh ? "en" : "zh-CN";
    i18n.changeLanguage(nextLang).catch(console.error);
  };

  return (
    <button
      type="button"
      onClick={toggleLang}
      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
    >
      <Languages className="h-3.5 w-3.5 shrink-0" />
      <span className="whitespace-nowrap">{isZh ? "English" : "中文"}</span>
    </button>
  );
}
