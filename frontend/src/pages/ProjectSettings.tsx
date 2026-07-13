import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { api, type DataSourceSettings, type FeatureFlagsResponse, type LLMProviderOption, type LLMSettings, type UserProfile } from "@/lib/api";
import { setAdminToken } from "@/lib/apiAuth";
import { Database, KeyRound, Loader2, RotateCcw, Save, Server, SlidersHorizontal, ShieldAlert, Lock, Plus, Trash2, Edit, MessageSquareMore } from "lucide-react";


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

  const [agentConfigJson, setAgentConfigJson] = useState<any>(null);
  
  // agent.yaml channels config states
  const [sendProgress, setSendProgress] = useState(true);
  const [sendToolHints, setSendToolHints] = useState(false);
  const [sendMaxRetries, setSendMaxRetries] = useState(2);
  const [replyTimeoutS, setReplyTimeoutS] = useState(600);
  const [channelConfigSaving, setChannelConfigSaving] = useState(false);
  
  // MCP Modal States
  const [isMcpModalOpen, setIsMcpModalOpen] = useState(false);
  const [editingMcpName, setEditingMcpName] = useState<string | null>(null);
  const [mcpName, setMcpName] = useState("");
  const [mcpType, setMcpType] = useState("stdio");
  const [mcpCommand, setMcpCommand] = useState("");
  const [mcpArgs, setMcpArgs] = useState("");
  const [mcpEnv, setMcpEnv] = useState("");
  const [mcpSaving, setMcpSaving] = useState(false);

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
  const [thsCookie, setThsCookie] = useState("");
  const [clearThsCookie, setClearThsCookie] = useState(false);

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
      const [llmData, dataData, flagsData, configJsonData] = await Promise.all([
        api.getLLMSettings({ headers: { "X-Vibe-Scope": "global" } }),
        api.getDataSourceSettings({ headers: { "X-Vibe-Scope": "global" } }),
        api.getFeatureFlags({ headers: { "X-Vibe-Scope": "global" } }),
        api.getAgentConfigJson({ headers: { "X-Vibe-Scope": "global" } }),
      ]);
      setSettings(llmData);
      setForm(toForm(llmData));
      setDataSettings(dataData);
      setFeatureFlags(flagsData);
      setAgentConfigJson(configJsonData || {});
      if (configJsonData && configJsonData.channels) {
        setSendProgress(configJsonData.channels.send_progress !== false);
        setSendToolHints(!!configJsonData.channels.send_tool_hints);
        setSendMaxRetries(configJsonData.channels.send_max_retries ?? 2);
        setReplyTimeoutS(configJsonData.channels.reply_timeout_s ?? 600);
      } else {
        setSendProgress(true);
        setSendToolHints(false);
        setSendMaxRetries(2);
        setReplyTimeoutS(600);
      }
      setSettingsLoadError(null);
    } catch (err: any) {
      setSettingsLoadError(err?.message || "Failed to load project settings");
      toast.error(isZh ? "获取全局设置失败" : "Failed to load project settings");
    } finally {
      setLoading(false);
    }
  };



  useEffect(() => {
    if (profile?.is_admin) {
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
        ths_cookie: thsCookie.trim() || undefined,
        clear_ths_cookie: clearThsCookie,
        use_default: false,
      }, { headers: { "X-Vibe-Scope": "global" } });
      setDataSettings(updated);
      setTushareToken("");
      setClearTushareToken(false);
      setIwencaiKey("");
      setClearIwencaiKey(false);
      setFredApiKey("");
      setClearFredApiKey(false);
      setThsCookie("");
      setClearThsCookie(false);
      toast.success(isZh ? "全局数据源设置已保存" : "Global data source settings saved");
    } catch (err: any) {
      toast.error(err?.message || "Failed to save data source settings");
    } finally {
      setDataSaving(false);
    }
  };


  const submitVisualChannelConfig = async (e: FormEvent) => {
    e.preventDefault();
    setChannelConfigSaving(true);
    try {
      const updated = {
        ...agentConfigJson,
        channels: {
          ...agentConfigJson?.channels,
          send_progress: sendProgress,
          send_tool_hints: sendToolHints,
          send_max_retries: sendMaxRetries,
          reply_timeout_s: replyTimeoutS,
        }
      };
      const response = await api.updateAgentConfigJson(updated, { headers: { "X-Vibe-Scope": "global" } });
      setAgentConfigJson(response);
      
      toast.success(isZh ? "高级推送与交互配置已成功保存" : "Notification settings saved successfully");
    } catch (err: any) {
      toast.error((isZh ? "保存失败: " : "Save failed: ") + (err?.message || "Unknown error"));
    } finally {
      setChannelConfigSaving(false);
    }
  };

  const openAddMcpModal = () => {
    setEditingMcpName(null);
    setMcpName("");
    setMcpType("stdio");
    setMcpCommand("");
    setMcpArgs("");
    setMcpEnv("");
    setIsMcpModalOpen(true);
  };

  const openEditMcpModal = (name: string, config: any) => {
    setEditingMcpName(name);
    setMcpName(name);
    setMcpType(config.type || "stdio");
    setMcpCommand(config.command || "");
    setMcpArgs(config.args ? config.args.join("\n") : "");
    setMcpEnv(config.env ? Object.entries(config.env).map(([k, v]) => `${k}=${v}`).join("\n") : "");
    setIsMcpModalOpen(true);
  };

  const submitMcpServer = async (e: FormEvent) => {
    e.preventDefault();
    if (!mcpName.trim()) {
      toast.error(isZh ? "请输入 MCP 服务名称" : "Please enter MCP server name");
      return;
    }
    setMcpSaving(true);
    try {
      const argsArray = mcpArgs
        .split("\n")
        .map((arg) => arg.trim())
        .filter((arg) => arg !== "");
        
      const envObj: Record<string, string> = {};
      mcpEnv.split("\n").forEach((line) => {
        const parts = line.split("=");
        if (parts[0] && parts[0].trim()) {
          envObj[parts[0].trim()] = parts.slice(1).join("=").trim();
        }
      });

      const newServerConfig: any = {
        type: mcpType,
        command: mcpCommand.trim(),
        args: argsArray,
        env: envObj,
      };

      const updatedConfig = { ...agentConfigJson };
      if (!updatedConfig.mcp_servers) {
        updatedConfig.mcp_servers = {};
      }

      if (editingMcpName && editingMcpName !== mcpName.trim()) {
        delete updatedConfig.mcp_servers[editingMcpName];
      }

      updatedConfig.mcp_servers[mcpName.trim()] = newServerConfig;

      await api.updateAgentConfigJson(updatedConfig, { headers: { "X-Vibe-Scope": "global" } });
      setAgentConfigJson(updatedConfig);
      toast.success(isZh ? "保存 MCP 服务成功" : "Saved MCP server successfully");
      setIsMcpModalOpen(false);
    } catch (err: any) {
      toast.error((isZh ? "保存失败: " : "Save failed: ") + (err?.message || "Unknown error"));
    } finally {
      setMcpSaving(false);
    }
  };

  const deleteMcpServer = async (name: string) => {
    if (!window.confirm(isZh ? `确定要删除 MCP 服务 "${name}" 吗？` : `Are you sure you want to delete MCP server "${name}"?`)) {
      return;
    }
    try {
      const updatedConfig = { ...agentConfigJson };
      if (updatedConfig.mcp_servers) {
        delete updatedConfig.mcp_servers[name];
      }
      await api.updateAgentConfigJson(updatedConfig, { headers: { "X-Vibe-Scope": "global" } });
      setAgentConfigJson(updatedConfig);

      toast.success(isZh ? "删除 MCP 服务成功" : "Deleted MCP server successfully");
    } catch (err: any) {
      toast.error((isZh ? "删除失败: " : "Delete failed: ") + (err?.message || "Unknown error"));
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

  if (!profile?.is_admin) {
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
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <h2 className="text-base font-semibold">{isZh ? "管理员提权 (项目设置)" : "Admin Elevation (Project Settings)"}</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            {isZh 
              ? "此页面属于项目全局设置，仅限系统管理员修改。请输入管理员账号密码进行提权。" 
              : "This page is for global settings and is restricted to admin. Please enter admin credentials to elevate."}
          </p>
          <form onSubmit={handleAdminElevate} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">{isZh ? "管理员账号" : "Admin Username"}</span>
                <input type="text" value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} className={fieldClass} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">{isZh ? "管理员密码" : "Admin Password"}</span>
                <input type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} className={fieldClass} placeholder={isZh ? "请输入管理员密码" : "Password"} required />
              </label>
            </div>
            <button type="submit" disabled={elevating} className="inline-flex items-center justify-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm">
              {elevating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
              {isZh ? "进行管理员提权" : "Elevate as Admin"}
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
          <h1 className="text-2xl font-semibold tracking-tight">{isZh ? "\u9879\u76ee\u5168\u5c40\u8bbe\u7f6e (\u7cfb\u7edf\u7ba1\u7406\u5458)" : "Project Settings (Admin)"}</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">{isZh ? "\u914d\u7f6e\u9879\u76ee\u5168\u5c40\u7684\u9ed8\u8ba4\u5927\u6a21\u578b\u51ed\u8bc1\u53ca\u516c\u5171\u91d1\u878d\u6570\u636e\u6e90\u63a5\u5165 Token\u3002" : "Configure default LLM settings and data source API tokens globally."}</p>
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

            <label className="grid gap-2">
              <span className={labelClass}>同花顺 (Tonghuashun) Cookie</span>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <textarea
                  rows={2}
                  value={thsCookie}
                  onChange={(event) => setThsCookie(event.target.value)}
                  className={`${fieldClass} pl-9 py-2 min-h-[60px] resize-y`}
                  placeholder={dataSettings.ths_cookie_configured ? (isZh ? "已配置" : "Configured") : (isZh ? "未配置" : "Not Configured")}
                  disabled={clearThsCookie}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className={hintClass}>{isZh ? "用于同花顺自选股同步服务的数据接入验证。" : "Access cookie required for Tonghuashun watchlist synchronization."}</span>
                <label className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clearThsCookie}
                    onChange={(event) => {
                      setClearThsCookie(event.target.checked);
                      if (event.target.checked) setThsCookie("");
                    }}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  {isZh ? "清除 Cookie" : "Clear Cookie"}
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

      {/* MCP Services Visual List Card */}
      <div className="rounded-lg border bg-card p-4.5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <MessageSquareMore className="h-5 w-5 text-primary" />
              <h2 className="text-base font-semibold">{isZh ? "MCP 外部上下文组件服务" : "MCP Context Component Services"}</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              {isZh 
                ? "配置外部 Model Context Protocol 服务以提供额外的工具与数据（例如天气、网页搜索等）。" 
                : "Configure external Model Context Protocol services to extend agent tool sets (e.g. weather, web search)."}
            </p>
          </div>
          <button
            type="button"
            onClick={openAddMcpModal}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 text-xs font-semibold transition cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            {isZh ? "添加 MCP 服务" : "Add MCP Service"}
          </button>
        </div>

        {(!agentConfigJson?.mcp_servers || Object.keys(agentConfigJson.mcp_servers).length === 0) ? (
          <div className="text-center py-8 text-sm text-muted-foreground border border-dashed rounded-lg">
            {isZh ? "暂无配置的 MCP 服务" : "No configured MCP services"}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm text-muted-foreground font-sans">
              <thead>
                <tr className="border-b border-border/80">
                  <th className="py-2.5 font-semibold text-foreground">{isZh ? "服务名称" : "Server Name"}</th>
                  <th className="py-2.5 font-semibold text-foreground">{isZh ? "类型" : "Type"}</th>
                  <th className="py-2.5 font-semibold text-foreground">{isZh ? "可执行命令" : "Command"}</th>
                  <th className="py-2.5 font-semibold text-foreground">{isZh ? "参数数量" : "Args"}</th>
                  <th className="py-2.5 font-semibold text-foreground text-right">{isZh ? "操作" : "Actions"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {Object.entries(agentConfigJson.mcp_servers).map(([name, srv]: [string, any]) => (
                  <tr key={name} className="hover:bg-muted/10">
                    <td className="py-3 font-medium text-foreground font-mono">{name}</td>
                    <td className="py-3">
                      <span className="inline-flex items-center rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs font-medium font-mono">
                        {srv.type || "stdio"}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-xs max-w-xs truncate">{srv.command}</td>
                    <td className="py-3 font-mono text-xs">{srv.args ? srv.args.length : 0}</td>
                    <td className="py-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => openEditMcpModal(name, srv)}
                          className="text-muted-foreground hover:text-foreground hover:bg-muted rounded-md p-1.5 transition cursor-pointer"
                          title={isZh ? "编辑" : "Edit"}
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteMcpServer(name)}
                          className="text-red-400 hover:text-red-500 hover:bg-red-500/10 rounded-md p-1.5 transition cursor-pointer"
                          title={isZh ? "删除" : "Delete"}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Visual Agent Advanced Channels Config Card */}
      <div className="rounded-lg border bg-card p-4.5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b pb-3">
          <SlidersHorizontal className="h-5 w-5 text-primary" />
          <div className="space-y-0.5">
            <h2 className="text-base font-semibold">{isZh ? "智能体推送与交互设置 (agent.yaml)" : "Agent Push & Interaction Settings"}</h2>
            <p className="text-xs text-muted-foreground">
              {isZh ? "配置智能体在消息通道中的高级交互行为与重试机制。" : "Configure intermediate push states and retry mechanisms for the agent."}
            </p>
          </div>
        </div>

        <form onSubmit={submitVisualChannelConfig} className="space-y-4.5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={sendProgress}
                  onChange={(e) => setSendProgress(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
                />
                <span className="text-sm font-semibold">{isZh ? "发送中间状态与研究进度" : "Send Intermediate Progress"}</span>
              </label>
              <p className="text-xs text-muted-foreground pl-6">
                {isZh ? "启用后，智能体在思考和执行工具的过程中会发送中间状态消息。" : "Agent sends messages showing tool calls and reasoning before replying."}
              </p>
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={sendToolHints}
                  onChange={(e) => setSendToolHints(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
                />
                <span className="text-sm font-semibold">{isZh ? "显示工具调用技术提示" : "Show Tool Call Hints"}</span>
              </label>
              <p className="text-xs text-muted-foreground pl-6">
                {isZh ? "启用后，将在消息中附带具体的底层工具调用参数与技术诊断提示。" : "Append raw tools diagnostics and parameters to messages."}
              </p>
            </div>

            <div className="grid gap-1.5">
              <span className={labelClass}>{isZh ? "通信最大重试次数" : "Max Send Retries"}</span>
              <input
                type="number"
                min="1"
                max="10"
                required
                value={sendMaxRetries}
                onChange={(e) => setSendMaxRetries(parseInt(e.target.value) || 2)}
                className={fieldClass}
                placeholder="e.g. 2"
              />
              <p className={hintClass}>
                {isZh ? "设置当发送失败时的最大自动尝试次数（范围 1-10 次，默认 2）。" : "Set maximum auto retries when notification sending fails (range 1-10, default 2)."}
              </p>
            </div>

            <div className="grid gap-1.5">
              <span className={labelClass}>{isZh ? "客户端回复超时时间 (秒)" : "Reply Timeout (Seconds)"}</span>
              <input
                type="number"
                min="1"
                max="86400"
                required
                value={replyTimeoutS}
                onChange={(e) => setReplyTimeoutS(parseInt(e.target.value) || 600)}
                className={fieldClass}
                placeholder="e.g. 600"
              />
              <p className={hintClass}>
                {isZh ? "AI 等待人类交互或接口应答的最大超时时间（默认 600 秒）。" : "Max timeout for waiting user prompt inputs during workflows (default 600)."}
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-border/40">
            <button
              type="submit"
              disabled={channelConfigSaving}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm animate-in fade-in"
            >
              {channelConfigSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {channelConfigSaving ? (isZh ? "保存中..." : "Saving...") : (isZh ? "保存推送配置" : "Save Push Configuration")}
            </button>
          </div>
        </form>
      </div>



      {/* MCP Modal */}
      {isMcpModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-md border bg-card p-5 shadow-xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              {editingMcpName ? (isZh ? "编辑 MCP 服务" : "Edit MCP Service") : (isZh ? "添加 MCP 服务" : "Add MCP Service")}
            </h3>
            <form onSubmit={submitMcpServer} className="space-y-4">
              <label className="grid gap-1.5">
                <span className={labelClass}>{isZh ? "服务名称 (ID)" : "Service Name (ID)"}</span>
                <input
                  type="text"
                  required
                  disabled={editingMcpName !== null}
                  value={mcpName}
                  onChange={(e) => setMcpName(e.target.value)}
                  className={fieldClass}
                  placeholder="e.g. weather"
                />
              </label>

              <label className="grid gap-1.5">
                <span className={labelClass}>{isZh ? "传输类型" : "Transport Type"}</span>
                <select
                  value={mcpType}
                  onChange={(e) => setMcpType(e.target.value)}
                  className={fieldClass}
                >
                  <option value="stdio">stdio (本地命令进程)</option>
                  <option value="sse">sse (HTTP Server Sent Events)</option>
                  <option value="streamableHttp">streamableHttp (流式 HTTP)</option>
                </select>
              </label>

              <label className="grid gap-1.5">
                <span className={labelClass}>{isZh ? "执行命令" : "Command"}</span>
                <input
                  type="text"
                  required
                  value={mcpCommand}
                  onChange={(e) => setMcpCommand(e.target.value)}
                  className={fieldClass}
                  placeholder="e.g. node"
                />
              </label>

              <label className="grid gap-1.5">
                <span className={labelClass}>{isZh ? "启动参数 (每行一个参数)" : "Arguments (one per line)"}</span>
                <textarea
                  value={mcpArgs}
                  onChange={(e) => setMcpArgs(e.target.value)}
                  className={`${fieldClass} font-mono h-24 resize-y`}
                  placeholder="e.g.&#10;/path/to/server.js&#10;--flag"
                />
              </label>

              <label className="grid gap-1.5">
                <span className={labelClass}>{isZh ? "环境变量 (格式: KEY=VALUE，每行一个)" : "Environment Variables (KEY=VALUE, one per line)"}</span>
                <textarea
                  value={mcpEnv}
                  onChange={(e) => setMcpEnv(e.target.value)}
                  className={`${fieldClass} font-mono h-24 resize-y`}
                  placeholder="e.g.&#10;API_KEY=my_secret_value"
                />
              </label>

              <div className="flex items-center justify-end gap-3 border-t pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setIsMcpModalOpen(false)}
                  className="inline-flex items-center justify-center rounded-md border border-input bg-background hover:bg-accent px-4 py-2 text-sm font-medium transition cursor-pointer"
                >
                  {isZh ? "取消" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={mcpSaving}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-70 transition cursor-pointer"
                >
                  {mcpSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {mcpSaving ? (isZh ? "保存中..." : "Saving...") : (isZh ? "保存" : "Save")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
