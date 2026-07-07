import { useTranslation } from "react-i18next";
import { useEffect, useRef, useState } from "react";
import { Link, Outlet, useLocation, useSearchParams } from "react-router-dom";
import { Activity, BarChart3, Bot, Check, ChevronDown, ChevronRight, FileText, Languages, Moon, Sun, Plus, Trash2, Pencil, MessageSquare, ChevronsLeft, ChevronsRight, Settings, Layers, Loader2, Menu, X, Terminal, Compass, Cpu, KeyRound } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDarkMode } from "@/hooks/useDarkMode";
import { api, isAuthRequiredError, type SessionItem, type UserProfile } from "@/lib/api";
import { useAgentStore } from "@/stores/agent";
import { ConnectionBanner } from "@/components/layout/ConnectionBanner";
import { AuthBarrier } from "@/components/layout/AuthBarrier";
import { setApiAuthKey } from "@/lib/apiAuth";
import { SUPPORTED_LANGUAGES } from "@/i18n";

// Bump on each release; one place keeps the footer in sync with package.json.
const APP_VERSION = "v1.7.5.5";

export function Layout() {
  const { t } = useTranslation();

  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
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
    { to: "/alpha-zoo", icon: Layers, label: t('layout.alphaZoo') },
    { to: "/xueqiu", icon: Activity, label: i18nHook.language === "zh-CN" ? "雪球监控" : "Xueqiu Watcher" },
    { to: "/settings", icon: Settings, label: t('layout.settings') },
    { to: "/correlation", icon: BarChart3, label: t('layout.correlation') },
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
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="mx-auto max-w-md w-full p-4 space-y-4">
          <AuthBarrier
            onLogin={(key) => {
              setApiAuthKey(key);
              window.location.reload();
            }}
          />
        </div>
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
              <button onClick={toggle} className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors" title={dark ? t('layout.light') : t('layout.dark')}>
                {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </button>
              <button onClick={() => setCollapsed(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors" title={t('layout.expand')}>
                <ChevronsRight className="h-3.5 w-3.5" />
              </button>
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
                <p className="text-[10px] text-muted-foreground/60">{t('app.version') || APP_VERSION}</p>
              </div>
              {profile && (
                <div className="text-[10px] text-muted-foreground/50 border-t pt-1.5 border-border/30 truncate flex justify-between gap-2">
                  <span className="truncate" title={profile.name}>User: {profile.name}</span>
                  <span className="shrink-0 uppercase">{profile.role}</span>
                </div>
              )}
              </div>
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
// Language switcher — dropdown listing every language registered in
// src/i18n/index.ts. Persists the choice via i18next's localStorage detector
// and emits the `languageChanged` event handled in the i18n module to flip
// <html dir/lang> for RTL languages.
//
// Positioning: the menu uses `position: fixed` and is placed at
// `(triggerLeft, triggerTop - gap)`. This bypasses every ancestor's
// `overflow: hidden/auto/scroll`, stacking contexts, and CSS direction
// rules, so the dropdown is *always* fully visible regardless of where
// the trigger sits in the layout or which language is active. We measure
// the trigger with getBoundingClientRect() and update on resize/scroll.
// ---------------------------------------------------------------------------
function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [menuStyle, setMenuStyle] = useState<{ left: number; bottom: number; minWidth: number } | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent | TouchEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest?.("[data-lang-menu]")
      ) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("touchstart", onClick, { passive: true });
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("touchstart", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Recompute the menu's fixed coordinates whenever it opens, or whenever
  // the viewport changes (resize / scroll / language switch). The menu is
  // anchored to the trigger's *left edge* and sits *above* the trigger.
  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const place = () => {
      const r = triggerRef.current?.getBoundingClientRect();
      if (!r) return;
      // Anchor: align the menu's right edge with the trigger's right edge,
      // then clamp to the viewport so the menu never overflows the screen.
      const menuWidth = 160; // px — approx longest label "العربية" + padding
      const gap = 4; // mb-1
      const desiredLeft = r.right - menuWidth;
      const maxLeft = window.innerWidth - menuWidth - 8;
      const minLeft = 8;
      const left = Math.max(minLeft, Math.min(maxLeft, desiredLeft));
      setMenuStyle({
        left,
        // distance from viewport bottom: viewport height − trigger top + gap
        bottom: window.innerHeight - r.top + gap,
        minWidth: menuWidth,
      });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  // i18n.language (singular) is the primary active language. We try an exact
  // match first against SUPPORTED_LANGUAGES. If that fails (e.g. a regional
  // variant like "ja-JP"), we fall back to i18n.languages (plural) which
  // includes both the detected and resolved codes. NOTE: i18n.languages
  // always contains the fallback language ("en"), so it must NOT be the
  // primary match — otherwise "en" being first in SUPPORTED_LANGUAGES
  // would always win and the switcher would never show any other language.
  const current =
    SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language) ??
    SUPPORTED_LANGUAGES.find((l) => i18n.languages?.includes(l.code)) ??
    SUPPORTED_LANGUAGES[0];

  return (
    <div>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("layout.language")}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Languages className="h-3.5 w-3.5 shrink-0" />
        <span className="whitespace-nowrap">{current.label}</span>
        <ChevronDown className={cn("h-3 w-3 shrink-0 transition-transform", open && "rotate-180")} />
      </button>
      {open && menuStyle && (
        <ul
          data-lang-menu
          aria-label="Select language"
          style={{
            position: "fixed",
            left: menuStyle.left,
            bottom: menuStyle.bottom,
            minWidth: menuStyle.minWidth,
            zIndex: 60,
          }}
          className="rounded-md border border-border bg-popover shadow-lg ring-1 ring-black/5"
        >
          {SUPPORTED_LANGUAGES.map((lang) => {
            const active = lang.code === current.code;
            return (
              <li key={lang.code}>
                <button
                  type="button"
                  onClick={() => {
                    i18n.changeLanguage(lang.code).catch(console.error);
                    setOpen(false);
                  }}
                  aria-current={active || undefined}
                  className={cn(
                    "w-full flex items-center gap-2 px-2.5 py-1.5 text-xs hover:bg-muted hover:text-foreground transition-colors",
                    active && "text-foreground",
                  )}
                >
                  <span className="flex-1 text-start whitespace-nowrap">{lang.label}</span>
                  {active && <Check className="h-3 w-3 shrink-0" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
>>>>>>> ref-upstream/main
