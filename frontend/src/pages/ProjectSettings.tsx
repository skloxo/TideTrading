import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { api, type DataSourceSettings, type FeatureFlagsResponse, type LLMProviderOption, type LLMSettings, type UserProfile } from "@/lib/api";
import { setAdminToken } from "@/lib/apiAuth";
import { Database, KeyRound, Loader2, RotateCcw, Save, Server, SlidersHorizontal, ShieldAlert, Lock } from "lucide-react";

interface LLMFormState {
  provider: string;
  model_name: string;
  base_url: string;
  temperature: number;
  timeout_seconds: number;
  max_retries: number;
  reasoning_effort: string;
}

function toForm(settings: LLMSettings): LLMFormState {
  return {
    provider: settings.provider,
    model_name: settings.model_name,
    base_url: settings.base_url || "",
    temperature: settings.temperature,
    timeout_seconds: settings.timeout_seconds,
    max_retries: settings.max_retries,
    reasoning_effort: settings.reasoning_effort || "",
  };
}

export function ProjectSettings() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  // Global Config States
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [form, setForm] = useState<LLMFormState | null>(null);
  const [dataSettings, setDataSettings] = useState<DataSourceSettings | null>(null);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlagsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dataSaving, setDataSaving] = useState(false);
  const [settingsLoadError, setSettingsLoadError] = useState<string | null>(null);
  // LLM inputs
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);

  // Data Sources inputs
  const [tushareToken, setTushareToken] = useState("");
  const [clearTushareToken, setClearTushareToken] = useState(false);
  const [iwencaiKey, setIwencaiKey] = useState("");
  const [clearIwencaiKey, setClearIwencaiKey] = useState(false);
  const [fredApiKey, setFredApiKey] = useState("");
  const [clearFredApiKey, setClearFredApiKey] = useState(false);

  // Admin elevation states
  const [adminUsername, setAdminUsername] = useState("admin");
  const [adminPassword, setAdminPassword] = useState("");
  const [elevating, setElevating] = useState(false);

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

  const loadGlobalSettings = async () => {
    try {
      setLoading(true);
      const [llmData, dataData, flagsData] = await Promise.all([
        api.getLLMSettings({ headers: { "X-Vibe-Scope": "global" } }),
        api.getDataSourceSettings({ headers: { "X-Vibe-Scope": "global" } }),
        api.getFeatureFlags({ headers: { "X-Vibe-Scope": "global" } })
      ]);
      setSettings(llmData);
      setForm(toForm(llmData));
      setDataSettings(dataData);
      setFeatureFlags(flagsData);
      setSettingsLoadError(null);
    } catch (err: any) {
      setSettingsLoadError(err?.message || "Failed to load project settings");
      toast.error(isZh ? "获取全局设置失败" : "Failed to load project settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile?.role === "admin") {
      loadGlobalSettings();
    }
  }, [profile]);

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

  const providers = settings?.providers ?? [];
  const selectedProvider = useMemo<LLMProviderOption | undefined>(
    () => providers.find((p) => p.name === form?.provider),
    [form?.provider, providers]
  );

  const applyProviderDefaults = () => {
    if (!form || !selectedProvider) return;
    setForm({
      ...form,
      model_name: selectedProvider.default_model,
      base_url: selectedProvider.default_base_url || "",
    });
    setApiKey("");
    setClearApiKey(false);
  };

  const onProviderChange = (providerName: string) => {
    if (!form) return;
    const target = providers.find((p) => p.name === providerName);
    if (!target) return;
    setForm({
      ...form,
      provider: providerName,
      model_name: target.default_model,
      base_url: target.default_base_url || "",
    });
    setApiKey("");
    setClearApiKey(false);
  };

  const submitLLM = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    try {
      const updated = await api.updateLLMSettings({
        provider: form.provider,
        model_name: form.model_name,
        base_url: form.base_url,
        api_key: apiKey.trim() || undefined,
        clear_api_key: clearApiKey,
        temperature: form.temperature,
        timeout_seconds: form.timeout_seconds,
        max_retries: form.max_retries,
        reasoning_effort: form.reasoning_effort || undefined,
        use_default: false,
      }, { headers: { "X-Vibe-Scope": "global" } });
      setSettings(updated);
      setForm(toForm(updated));
      setApiKey("");
      setClearApiKey(false);
      toast.success(isZh ? "全局 LLM 连接设置已保存" : "Global LLM settings saved successfully");
    } catch (err: any) {
      toast.error(err?.message || "Failed to save LLM settings");
    } finally {
      setSaving(false);
    }
  };

  const submitDataSources = async (e: FormEvent) => {
    e.preventDefault();
    if (!dataSettings) return;
    setDataSaving(true);
    try {
      const updated = await api.updateDataSourceSettings({
        tushare_token: tushareToken.trim() || undefined,
        clear_tushare_token: clearTushareToken,
        iwencai_key: iwencaiKey.trim() || undefined,
        clear_iwencai_key: clearIwencaiKey,
        fred_api_key: fredApiKey.trim() || undefined,
        clear_fred_api_key: clearFredApiKey,
        use_default: false,
      }, { headers: { "X-Vibe-Scope": "global" } });
      setDataSettings(updated);
      setTushareToken("");
      setClearTushareToken(false);
      setIwencaiKey("");
      setClearIwencaiKey(false);
      setFredApiKey("");
      setClearFredApiKey(false);
      toast.success(isZh ? "全局数据源设置已保存" : "Global data source settings saved");
    } catch (err: any) {
      toast.error(err?.message || "Failed to save data source settings");
    } finally {
      setDataSaving(false);
    }
  };

  const keyStatus = settings?.api_key_configured
    ? isZh ? "已配置" : "Configured"
    : isZh ? "未配置" : "Not Configured";

  const apiKeyDisabled = !selectedProvider?.api_key_required || clearApiKey;
  
  const tushareStatus = dataSettings?.tushare_token_configured
    ? isZh ? "已配置" : "Configured"
    : isZh ? "未配置" : "Not Configured";

  const labelClass = "text-xs font-semibold text-muted-foreground uppercase tracking-wider block";
  const fieldClass = "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";
  const hintClass = "text-[10px] text-muted-foreground block mt-1";

  if (profileLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center text-muted-foreground animate-pulse">
        {isZh ? "正在验证访问权限..." : "Verifying access permissions..."}
      </div>
    );
  }

  if (profile?.role !== "admin") {
    return (
      <div className="mx-auto max-w-7xl space-y-4 p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {isZh ? "项目全局设置" : "Project Settings"}
            </h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              {isZh ? "配置项目全局的默认大模型凭证及公共金融数据源接入 Token。" : "Configure project-global default LLM endpoints and financial data feeds."}
            </p>
          </div>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm space-y-4 max-w-xl">
          <div className="flex items-center gap-2 border-b pb-3">
            <ShieldAlert className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">管理员提权 (项目设置)</h2>
          </div>
          <p className="text-xs text-muted-foreground">此页面属于项目全局设置，仅限系统管理员修改。请输入管理员账号密码进行提权。</p>
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

  if (loading || !form || !dataSettings) {
    return (
      <div className="flex h-[40vh] items-center justify-center text-muted-foreground gap-2">
        {settingsLoadError ? (
          <div className="text-center space-y-2">
            <div className="font-semibold text-foreground">{isZh ? "加载全局配置项失败" : "Failed to load configuration"}</div>
            <div className="text-xs text-muted-foreground max-w-md">{settingsLoadError}</div>
            <button type="button" onClick={() => loadGlobalSettings()} className="text-xs text-primary hover:underline font-medium cursor-pointer">重试</button>
          </div>
        ) : (
          <div className="flex items-center gap-2 animate-pulse">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span>{isZh ? "正在加载全局配置项..." : "Loading configuration..."}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{isZh ? "项目全局设置 (系统管理员)" : "Project Settings (Admin)"}</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">{isZh ? "配置项目全局的默认大模型凭证及公共金融数据源接入 Token。" : "Configure default LLM settings and data source API tokens globally."}</p>
        </div>
      </div>

      <form onSubmit={submitLLM} className="grid gap-3.5 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)]">
        <section className="rounded-lg border bg-card p-3.5 shadow-sm">
          <div className="mb-5 flex items-center gap-2">
            <Server className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">项目全局 LLM 连接设置</h2>
          </div>

          <div className="grid gap-4">
            <label className="grid gap-2">
              <span className={labelClass}>{isZh ? "大模型厂商" : "Provider"}</span>
              <select
                value={form.provider}
                onChange={(event) => onProviderChange(event.target.value)}
                className={fieldClass}
              >
                {providers.map((provider) => (
                  <option key={provider.name} value={provider.name}>{provider.label}</option>
                ))}
              </select>
            </label>

            <label className="grid gap-2">
              <span className={labelClass}>{isZh ? "模型名称 (Model ID)" : "Model ID"}</span>
              <div className="flex gap-2">
                <input
                  value={form.model_name}
                  onChange={(event) => setForm({ ...form, model_name: event.target.value })}
                  className={fieldClass}
                  required
                />
                <button
                  type="button"
                  onClick={() => applyProviderDefaults()}
                  className="inline-flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground cursor-pointer"
                  title={isZh ? "使用厂商默认配置" : "Use defaults"}
                >
                  <RotateCcw className="h-4 w-4" />
                  <span className="hidden sm:inline">{isZh ? "默认模型" : "Default"}</span>
                </button>
              </div>
            </label>

            <label className="grid gap-2">
              <span className={labelClass}>{isZh ? "自定义 API 代理基址 (Base URL)" : "Base URL"}</span>
              <input
                value={form.base_url}
                onChange={(event) => setForm({ ...form, base_url: event.target.value })}
                className={fieldClass}
                placeholder={selectedProvider?.default_base_url}
              />
            </label>

            <label className="grid gap-2">
              <span className={labelClass}>API Key</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="password"
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  className={`${fieldClass} pl-9`}
                  placeholder={settings?.api_key_hint || keyStatus}
                  autoComplete="current-password"
                  disabled={apiKeyDisabled}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className={hintClass}>{settings?.api_key_hint || keyStatus}</span>
                {selectedProvider?.api_key_required ? (
                  <label className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      checked={clearApiKey}
                      onChange={(event) => {
                        setClearApiKey(event.target.checked);
                        if (event.target.checked) setApiKey("");
                      }}
                      className="h-3.5 w-3.5 accent-primary"
                    />
                    {isZh ? "清除已存 Key" : "Clear Key"}
                  </label>
                ) : null}
              </div>
            </label>
          </div>
        </section>

        <section className="rounded-lg border bg-card p-3.5 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="mb-5 flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-primary" />
              <h2 className="text-base font-semibold">全局大模型参数生成设置</h2>
            </div>

            <div className="grid gap-4">
              <label className="grid gap-2">
                <span className={labelClass}>{isZh ? "采样温度 (Temperature)" : "Temperature"}</span>
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={form.temperature}
                  onChange={(event) => setForm({ ...form, temperature: Number(event.target.value) })}
                  className={fieldClass}
                />
              </label>

              <label className="grid gap-2">
                <span className={labelClass}>{isZh ? "请求超时秒数 (Timeout)" : "Timeout (s)"}</span>
                <input
                  type="number"
                  min={1}
                  max={3600}
                  step={1}
                  value={form.timeout_seconds}
                  onChange={(event) => setForm({ ...form, timeout_seconds: Number(event.target.value) })}
                  className={fieldClass}
                />
              </label>

              <label className="grid gap-2">
                <span className={labelClass}>{isZh ? "异常自动重试次数" : "Max Retries"}</span>
                <input
                  type="number"
                  min={0}
                  max={20}
                  step={1}
                  value={form.max_retries}
                  onChange={(event) => setForm({ ...form, max_retries: Number(event.target.value) })}
                  className={fieldClass}
                />
              </label>

              <label className="grid gap-2">
                <span className={labelClass}>{isZh ? "推理深度 (Reasoning Effort)" : "Reasoning Effort"}</span>
                <select
                  value={form.reasoning_effort}
                  onChange={(event) => setForm({ ...form, reasoning_effort: event.target.value })}
                  className={fieldClass}
                >
                  <option value="">{isZh ? "关闭" : "Off"}</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="max">Max</option>
                </select>
              </label>

              <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{isZh ? "保存路径" : "Env Path"}: </span>
                <span className="break-all font-mono">{settings?.env_path}</span>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saving ? (isZh ? "保存中..." : "Saving...") : (isZh ? "保存全局连接" : "Save Settings")}
          </button>
        </section>
      </form>

      <form onSubmit={submitDataSources} className="rounded-lg border bg-card p-3.5 shadow-sm space-y-4">
        <div className="mb-2 space-y-1">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">项目全局数据源默认设置</h2>
          </div>
          <p className="text-sm text-muted-foreground">{isZh ? "为主站行情源、回测 and 选股因子数据库接入系统级认证凭证。" : "Configure fallback credentials for technical data feeds and stock screeners."}</p>
        </div>

        <div className="grid gap-3.5 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
          <div className="grid gap-4">
            <label className="grid gap-2">
              <span className={labelClass}>Tushare Token</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="password"
                  value={tushareToken}
                  onChange={(event) => setTushareToken(event.target.value)}
                  className={`${fieldClass} pl-9`}
                  placeholder={tushareStatus}
                  autoComplete="current-password"
                  disabled={clearTushareToken}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className={hintClass}>{isZh ? "国内股票基本面、财务比率及指数宏观的核心来源。" : "Primary source for A-share fundamental facts and macroeconomic indices."}</span>
                <label className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clearTushareToken}
                    onChange={(event) => {
                      setClearTushareToken(event.target.checked);
                      if (event.target.checked) setTushareToken("");
                    }}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  {isZh ? "清除 Token" : "Clear Token"}
                </label>
              </div>
            </label>

            <label className="grid gap-2">
              <span className={labelClass}>iWencai API Key</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="password"
                  value={iwencaiKey}
                  onChange={(event) => setIwencaiKey(event.target.value)}
                  className={`${fieldClass} pl-9`}
                  placeholder={dataSettings.iwencai_key_configured ? (isZh ? "已配置" : "Configured") : (isZh ? "未配置" : "Not Configured")}
                  autoComplete="current-password"
                  disabled={clearIwencaiKey}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className={hintClass}>{isZh ? "同花顺问财自然语言选股 API Token。" : "Access token for iWencai semantic screening API."}</span>
                <label className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clearIwencaiKey}
                    onChange={(event) => {
                      setClearIwencaiKey(event.target.checked);
                      if (event.target.checked) setIwencaiKey("");
                    }}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  {isZh ? "清除 Key" : "Clear Key"}
                </label>
              </div>
            </label>

            <label className="grid gap-2">
              <span className={labelClass}>FRED API Key</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="password"
                  value={fredApiKey}
                  onChange={(event) => setFredApiKey(event.target.value)}
                  className={`${fieldClass} pl-9`}
                  placeholder={dataSettings.fred_api_key_configured ? (isZh ? "已配置" : "Configured") : (isZh ? "未配置" : "Not Configured")}
                  autoComplete="current-password"
                  disabled={clearFredApiKey}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className={hintClass}>{isZh ? "美联储经济数据源（FRED）Token，用于宏观指标分析。" : "Federal Reserve Economic Data (FRED) API key for macro data parsing."}</span>
                <label className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clearFredApiKey}
                    onChange={(event) => {
                      setClearFredApiKey(event.target.checked);
                      if (event.target.checked) setFredApiKey("");
                    }}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  {isZh ? "清除 Key" : "Clear Key"}
                </label>
              </div>
            </label>
          </div>

          <div className="flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-md border bg-muted/20 px-4 py-3 opacity-90">
                <span className="text-sm font-medium">{isZh ? "命令行执行工具" : "CLI Exec Tools"}</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  featureFlags?.shell_tools_enabled
                    ? "bg-green-500/10 text-green-500"
                    : "bg-gray-500/10 text-gray-500"
                }`}>
                  {featureFlags?.shell_tools_enabled ? (isZh ? "已启用" : "Enabled") : (isZh ? "未启用" : "Disabled")}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border bg-muted/20 px-4 py-3 opacity-90">
                <span className="text-sm font-medium">{isZh ? "计划任务调度器" : "Cron Scheduler"}</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  featureFlags?.scheduler_enabled
                    ? "bg-green-500/10 text-green-500"
                    : "bg-gray-500/10 text-gray-500"
                }`}>
                  {featureFlags?.scheduler_enabled ? (isZh ? "已启用" : "Enabled") : (isZh ? "未启用" : "Disabled")}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-md border bg-muted/20 px-4 py-3 opacity-90">
                <span className="text-sm font-medium">{isZh ? "独立会话运行态" : "Session Runtimes"}</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  featureFlags?.session_runtime_enabled
                    ? "bg-green-500/10 text-green-500"
                    : "bg-gray-500/10 text-gray-500"
                }`}>
                  {featureFlags?.session_runtime_enabled ? (isZh ? "已启用" : "Enabled") : (isZh ? "未启用" : "Disabled")}
                </span>
              </div>
            </div>

            <div className="mt-4">
              <button
                type="submit"
                disabled={dataSaving}
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
              >
                {dataSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {dataSaving ? (isZh ? "保存中..." : "Saving...") : (isZh ? "保存全局数据源" : "Save Data Sources")}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
