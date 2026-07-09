import i18n from "@/i18n";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Database, KeyRound, Loader2, MessageSquare, MessageSquareMore, RefreshCw, RotateCcw, Save, Server, SlidersHorizontal, Trash2, Power, QrCode, Activity } from "lucide-react";
import { toast } from "sonner";
import { api, isAuthRequiredError, type DataSourceSettings, type LLMProviderOption, type LLMSettings, type FeishuChannel, type WechatChannel, type ChannelRuntimeStatus, type DingtalkChannel, type QqChannel, type EmailChannel, type MsteamsChannel, type WebsocketChannel } from "@/lib/api";
import { setApiAuthKey } from "@/lib/apiAuth";
import { createPortal } from "react-dom";
import { AuthBarrier } from "@/components/layout/AuthBarrier";

interface LLMFormState {
  provider: string;
  model_name: string;
  base_url: string;
  temperature: number;
  timeout_seconds: number;
  max_retries: number;
  reasoning_effort: string;
}

const fieldClass =
  "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60";
const labelClass = "text-sm font-medium";
const hintClass = "text-xs text-muted-foreground";

function toForm(settings: LLMSettings): LLMFormState {
  return {
    provider: settings.provider,
    model_name: settings.model_name,
    base_url: settings.base_url,
    temperature: settings.temperature,
    timeout_seconds: settings.timeout_seconds,
    max_retries: settings.max_retries,
    reasoning_effort: settings.reasoning_effort || "",
  };
}

export function Settings() {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [dataSettings, setDataSettings] = useState<DataSourceSettings | null>(null);
  const [channelStatus, setChannelStatus] = useState<ChannelRuntimeStatus | null>(null);
  const [form, setForm] = useState<LLMFormState | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [tushareToken, setTushareToken] = useState("");
  const [clearTushareToken, setClearTushareToken] = useState(false);
  const [iwencaiKey, setIwencaiKey] = useState("");
  const [clearIwencaiKey, setClearIwencaiKey] = useState(false);
  const [fredApiKey, setFredApiKey] = useState("");
  const [clearFredApiKey, setClearFredApiKey] = useState(false);
  const [thsCookie, setThsCookie] = useState("");
  const [clearThsCookie, setClearThsCookie] = useState(false);
  const [thsTesting, setThsTesting] = useState(false);
  const [thsTestResult, setThsTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [thsSaving, setThsSaving] = useState(false);
  const [thsSavedOk, setThsSavedOk] = useState(false);
  const [thsSyncing, setThsSyncing] = useState(false);
  const [thsSyncResult, setThsSyncResult] = useState<{ success: boolean; message: string } | null>(null);
  
  // Feishu platforms settings states
  const [feishuChannels, setFeishuChannels] = useState<FeishuChannel[]>([]);
  const [wechatChannels, setWechatChannels] = useState<WechatChannel[]>([]);
  const [transientQrCode, setTransientQrCode] = useState<string | null>(null);
  const [transientQrStatus, setTransientQrStatus] = useState<string>("idle");
  const [showTransientScanner, setShowTransientScanner] = useState<boolean>(false);
  
  // Generic Modal States for 7 channels
  const [activeModalChannel, setActiveModalChannel] = useState<{
    type: 'feishu' | 'wechat' | 'dingtalk' | 'qq' | 'email' | 'msteams' | 'websocket';
    id?: string;
  } | null>(null);
  
  const [modalName, setModalName] = useState("");
  const [modalEnabled, setModalEnabled] = useState(true);
  const [modalField1, setModalField1] = useState("");
  const [modalField2, setModalField2] = useState("");
  const [modalField3, setModalField3] = useState("");
  const [modalField4, setModalField4] = useState("");
  const [modalField5, setModalField5] = useState("");
  const [modalBool1, setModalBool1] = useState(false);
  const [modalSaving, setModalSaving] = useState(false);

  // DingTalk, QQ, Email, MS Teams, WebSocket channels list states
  const [dingtalkChannels, setDingtalkChannels] = useState<DingtalkChannel[]>([]);
  const [qqChannels, setQqChannels] = useState<QqChannel[]>([]);
  const [emailChannels, setEmailChannels] = useState<EmailChannel[]>([]);
  const [msteamsChannels, setMsteamsChannels] = useState<MsteamsChannel[]>([]);
  const [websocketChannels, setWebsocketChannels] = useState<WebsocketChannel[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dataSaving, setDataSaving] = useState(false);
  const [channelRefreshing, setChannelRefreshing] = useState(false);
  const [settingsLoadError, setSettingsLoadError] = useState<string | null>(null);

  const [authFailed, setAuthFailed] = useState(false);
  const [llmMode, setLlmMode] = useState<"default" | "custom">("default");
  const [dataMode, setDataMode] = useState<"default" | "custom">("default");


  useEffect(() => {
    let alive = true;
    Promise.allSettled([
      api.getLLMSettings(),
      api.getDataSourceSettings(),
      api.getFeishuChannels(),
      api.getWechatChannels(),
      api.getDingtalkChannels(),
      api.getQqChannels(),
      api.getEmailChannels(),
      api.getMsteamsChannels(),
      api.getWebsocketChannels(),
      api.getChannelStatus(),
    ])
      .then(([llmResult, dataSourceResult, feishuResult, wechatResult, dingResult, qqResult, emailResult, teamsResult, wsResult, channelResult]) => {
        if (!alive) return;

        if (llmResult.status === "fulfilled") {
          setSettings(llmResult.value);
          setForm(toForm(llmResult.value));
        } else {
          const message = llmResult.reason instanceof Error ? llmResult.reason.message : "Unknown error";
          setSettingsLoadError(message);
          if (isAuthRequiredError(llmResult.reason)) {
            setAuthFailed(true);
            toast.error(message);
          } else {
            toast.error(`Failed to load LLM settings: ${message}`);
          }
        }

        if (dataSourceResult.status === "fulfilled") {
          setDataSettings(dataSourceResult.value);
        } else {
          const message = dataSourceResult.reason instanceof Error ? dataSourceResult.reason.message : "Unknown error";
          setSettingsLoadError(message);
          if (isAuthRequiredError(dataSourceResult.reason)) {
            setAuthFailed(true);
            toast.error(message);
          } else {
            toast.error(`Failed to load data source settings: ${message}`);
          }
        }

        if (feishuResult.status === "fulfilled") setFeishuChannels(feishuResult.value);
        if (wechatResult.status === "fulfilled") setWechatChannels(wechatResult.value);
        if (dingResult.status === "fulfilled") setDingtalkChannels(dingResult.value);
        if (qqResult.status === "fulfilled") setQqChannels(qqResult.value);
        if (emailResult.status === "fulfilled") setEmailChannels(emailResult.value);
        if (teamsResult.status === "fulfilled") setMsteamsChannels(teamsResult.value);
        if (wsResult.status === "fulfilled") setWebsocketChannels(wsResult.value);

        if (channelResult.status === "fulfilled") {
          setChannelStatus(channelResult.value);
        } else {
          const message = channelResult.reason instanceof Error ? channelResult.reason.message : "Unknown error";
          toast.error(`Failed to load channel status: ${message}`);
          setChannelStatus(null);
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const refreshChannelStatus = async () => {
    setChannelRefreshing(true);
    try {
      setChannelStatus(await api.getChannelStatus());
    } catch (error) {
      toast.error(`Failed to refresh channels: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setChannelRefreshing(false);
    }
  };






  const providers = settings?.providers ?? [];
  const selectedProvider = useMemo<LLMProviderOption | undefined>(
    () => providers.find((provider) => provider.name === form?.provider),
    [form?.provider, providers],
  );

  const applyProviderDefaults = (provider = selectedProvider) => {
    if (!provider || !form) return;
    setForm({
      ...form,
      model_name: provider.default_model,
      base_url: provider.default_base_url,
    });
  };

  const onProviderChange = (name: string) => {
    const provider = providers.find((item) => item.name === name);
    if (!provider || !form) return;
    setForm({
      ...form,
      provider: provider.name,
      model_name: provider.default_model,
      base_url: provider.default_base_url,
    });
    setApiKey("");
    setClearApiKey(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    try {
      const isDefault = llmMode === "default";
      const updated = await api.updateLLMSettings({
        provider: isDefault ? "openai" : form.provider,
        model_name: isDefault ? "placeholder" : form.model_name,
        base_url: isDefault ? "" : form.base_url,
        api_key: isDefault ? "" : apiKey.trim() || undefined,
        clear_api_key: isDefault ? true : clearApiKey,
        temperature: isDefault ? 0.0 : form.temperature,
        timeout_seconds: isDefault ? 120 : form.timeout_seconds,
        max_retries: isDefault ? 2 : form.max_retries,
        reasoning_effort: isDefault ? "" : form.reasoning_effort || undefined,
        use_default: isDefault,
      });
      setSettings(updated);
      setForm(toForm(updated));
      setApiKey("");
      setClearApiKey(false);
      toast.success(i18n.t("settings.llmSettingsSaved"));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(i18n.t("settings.saveLlmSettingsFailed", { message }));
    } finally {
      setSaving(false);
    }
  };

  const submitDataSources = async (event: FormEvent) => {
    event.preventDefault();
    setDataSaving(true);
    try {
      const isDefault = dataMode === "default";
      const updated = await api.updateDataSourceSettings({
        tushare_token: isDefault ? "" : tushareToken.trim() || undefined,
        clear_tushare_token: isDefault ? true : clearTushareToken,
        iwencai_key: isDefault ? "" : iwencaiKey.trim() || undefined,
        clear_iwencai_key: isDefault ? true : clearIwencaiKey,
        fred_api_key: isDefault ? "" : fredApiKey.trim() || undefined,
        clear_fred_api_key: isDefault ? true : clearFredApiKey,
        use_default: isDefault,
      });
      setDataSettings(updated);
      setTushareToken("");
      setClearTushareToken(false);
      setIwencaiKey("");
      setClearIwencaiKey(false);
      setFredApiKey("");
      setClearFredApiKey(false);
      toast.success(i18n.t("settings.dataSourceSettingsSaved"));
    } catch (error) {
      toast.error(i18n.t("settings.saveDataSourceSettingsFailed", { message: error instanceof Error ? error.message : "Unknown error" }));
    } finally {
      setDataSaving(false);
    }
  };

  const submitThsSync = async (event: FormEvent, clearMode?: boolean) => {
    event.preventDefault();
    setThsSaving(true);
    setThsSavedOk(false);
    try {
      const isDefault = dataMode === "default";
      const doClear = clearMode ?? clearThsCookie;
      const updated = await api.updateDataSourceSettings({
        ths_cookie: isDefault || doClear ? "" : thsCookie.trim() || undefined,
        clear_ths_cookie: isDefault ? true : doClear,
      });
      setDataSettings(updated);
      setThsCookie("");
      setClearThsCookie(false);
      setThsTestResult(null);
      setThsSavedOk(true);
      setTimeout(() => setThsSavedOk(false), 3000);
      toast.success(doClear ? "同花顺 Cookie 已清除" : "同花顺自选股同步设置保存成功");
    } catch (error) {
      toast.error("保存同花顺同步设置失败: " + (error instanceof Error ? error.message : "未知错误"));
    } finally {
      setThsSaving(false);
    }
  };

  const handleClearThsCookie = async (event: React.MouseEvent) => {
    event.preventDefault();
    if (!confirm("确定要清除已保存的同花顺 Cookie 吗？")) return;
    // Create a synthetic form event for submitThsSync
    const fakeEvent = { preventDefault: () => {} } as FormEvent;
    await submitThsSync(fakeEvent, true);
  };

  const handleTestThsConnection = async () => {
    const cookieToTest = thsCookie.trim();
    if (!cookieToTest) {
      toast.error("请输入同花顺 Cookie 后再测试连接");
      return;
    }
    setThsTesting(true);
    setThsTestResult(null);
    try {
      const res = await api.testThsCookie(cookieToTest);
      setThsTestResult(res);
      if (res.success) {
        toast.success("同花顺 Cookie 测试连接成功！");
      } else {
        toast.error("同花顺 Cookie 测试连接失败！");
      }
    } catch (error) {
      setThsTestResult({
        success: false,
        message: error instanceof Error ? error.message : "测试请求失败",
      });
      toast.error("测试请求出错");
    } finally {
      setThsTesting(false);
    }
  };

  const handleManualThsSync = async () => {
    setThsSyncing(true);
    setThsSyncResult(null);
    try {
      const res = await api.triggerThsSync();
      setThsSyncResult(res);
      if (res.success) {
        toast.success("同花顺自选股手动同步成功");
      } else {
        toast.error("手动同步失败: " + res.message);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "未知错误";
      setThsSyncResult({ success: false, message: msg });
      toast.error("手动同步失败: " + msg);
    } finally {
      setThsSyncing(false);
    }
  };

  const openChannelConfigModal = (type: 'feishu' | 'wechat' | 'dingtalk' | 'qq' | 'email' | 'msteams' | 'websocket', channel?: any) => {
    setActiveModalChannel({ type, id: channel?.id });
    if (channel) {
      setModalName(channel.name || "");
      setModalEnabled(channel.enabled !== false);
      if (type === 'feishu') {
        setModalField1(channel.app_id || "");
        setModalField2("");
        setModalField3(channel.allowed_users || "");
        setModalBool1(channel.allow_all_users || false);
      } else if (type === 'wechat') {
        setModalField1(channel.ilink_bot_token || "");
        setModalField2(channel.ilink_base_url || "");
        setModalField3(channel.ilink_bot_id || "");
        setModalField4(channel.ilink_user_id || "");
        setShowTransientScanner(false);
      } else if (type === 'dingtalk') {
        setModalField1(channel.client_id || "");
        setModalField2("");
      } else if (type === 'qq') {
        setModalField1(channel.app_id || "");
        setModalField2("");
      } else if (type === 'email') {
        setModalField1(channel.smtp_host || "");
        setModalField2(String(channel.smtp_port || 587));
        setModalField3(channel.smtp_username || "");
        setModalField4("");
        setModalField5(channel.from_address || "");
      } else if (type === 'msteams') {
        setModalField1(channel.app_id || "");
        setModalField2("");
      } else if (type === 'websocket') {
        setModalField1(channel.host || "127.0.0.1");
        setModalField2(String(channel.port || 8765));
        setModalField3("");
        setModalBool1(channel.websocket_requires_token !== false);
      }
    } else {
      setModalName("");
      setModalEnabled(true);
      setModalField1("");
      setModalField2("");
      setModalField3("");
      setModalField4("");
      setModalField5("");
      setModalBool1(type === 'websocket');
      
      if (type === 'wechat') {
        setTransientQrCode(null);
        setTransientQrStatus("idle");
        setShowTransientScanner(true);
      }
    }
  };

  const submitChannelConfig = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeModalChannel) return;
    
    setModalSaving(true);
    const { type, id } = activeModalChannel;
    
    try {
      if (type === 'feishu') {
        if (id) {
          const updated = await api.updateFeishuChannel(id, {
            name: modalName,
            app_id: modalField1,
            app_secret: modalField2 ? modalField2 : undefined,
            allowed_users: modalField3,
            allow_all_users: modalBool1,
            enabled: modalEnabled,
          });
          setFeishuChannels(feishuChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createFeishuChannel({
            name: modalName,
            app_id: modalField1,
            app_secret: modalField2,
            allowed_users: modalField3,
            allow_all_users: modalBool1,
            enabled: modalEnabled,
          });
          setFeishuChannels([...feishuChannels, created]);
        }
      } else if (type === 'wechat') {
        if (id) {
          const updated = await api.updateWechatChannel(id, {
            name: modalName,
            mode: 'ilink',
            enabled: modalEnabled,
            ilink_bot_token: modalField1,
            ilink_base_url: modalField2,
            ilink_bot_id: modalField3,
            ilink_user_id: modalField4,
          });
          setWechatChannels(wechatChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createWechatChannel({
            name: modalName,
            mode: 'ilink',
            enabled: modalEnabled,
            ilink_bot_token: modalField1,
            ilink_base_url: modalField2,
            ilink_bot_id: modalField3,
            ilink_user_id: modalField4,
          });
          setWechatChannels([...wechatChannels, created]);
        }
      } else if (type === 'dingtalk') {
        if (id) {
          const updated = await api.updateDingtalkChannel(id, {
            name: modalName,
            client_id: modalField1,
            client_secret: modalField2 ? modalField2 : undefined,
            enabled: modalEnabled,
          });
          setDingtalkChannels(dingtalkChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createDingtalkChannel({
            name: modalName,
            client_id: modalField1,
            client_secret: modalField2,
            enabled: modalEnabled,
          });
          setDingtalkChannels([...dingtalkChannels, created]);
        }
      } else if (type === 'qq') {
        if (id) {
          const updated = await api.updateQqChannel(id, {
            name: modalName,
            app_id: modalField1,
            secret: modalField2 ? modalField2 : undefined,
            enabled: modalEnabled,
          });
          setQqChannels(qqChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createQqChannel({
            name: modalName,
            app_id: modalField1,
            secret: modalField2,
            enabled: modalEnabled,
          });
          setQqChannels([...qqChannels, created]);
        }
      } else if (type === 'email') {
        if (id) {
          const updated = await api.updateEmailChannel(id, {
            name: modalName,
            smtp_host: modalField1,
            smtp_port: parseInt(modalField2, 10) || 587,
            smtp_username: modalField3,
            smtp_password: modalField4 ? modalField4 : undefined,
            from_address: modalField5,
            enabled: modalEnabled,
          });
          setEmailChannels(emailChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createEmailChannel({
            name: modalName,
            smtp_host: modalField1,
            smtp_port: parseInt(modalField2, 10) || 587,
            smtp_username: modalField3,
            smtp_password: modalField4,
            from_address: modalField5,
            enabled: modalEnabled,
          });
          setEmailChannels([...emailChannels, created]);
        }
      } else if (type === 'msteams') {
        if (id) {
          const updated = await api.updateMsteamsChannel(id, {
            name: modalName,
            app_id: modalField1,
            app_password: modalField2 ? modalField2 : undefined,
            enabled: modalEnabled,
          });
          setMsteamsChannels(msteamsChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createMsteamsChannel({
            name: modalName,
            app_id: modalField1,
            app_password: modalField2,
            enabled: modalEnabled,
          });
          setMsteamsChannels([...msteamsChannels, created]);
        }
      } else if (type === 'websocket') {
        if (id) {
          const updated = await api.updateWebsocketChannel(id, {
            name: modalName,
            host: modalField1,
            port: parseInt(modalField2, 10) || 8765,
            token: modalField3 ? modalField3 : undefined,
            websocket_requires_token: modalBool1,
            enabled: modalEnabled,
          });
          setWebsocketChannels(websocketChannels.map(c => c.id === id ? updated : c));
        } else {
          const created = await api.createWebsocketChannel({
            name: modalName,
            host: modalField1,
            port: parseInt(modalField2, 10) || 8765,
            token: modalField3,
            websocket_requires_token: modalBool1,
            enabled: modalEnabled,
          });
          setWebsocketChannels([...websocketChannels, created]);
        }
      }
      
      toast.success(i18n.t("settings.channelSaved") || "Channel configuration saved successfully");
      setActiveModalChannel(null);
    } catch (error: any) {
      toast.error((i18n.t("settings.channelSaveFailed") || "Save failed: ") + (error?.message || "Unknown error"));
    } finally {
      setModalSaving(false);
    }
  };

  const toggleGenericChannel = async (type: 'feishu' | 'wechat' | 'dingtalk' | 'qq' | 'email' | 'msteams' | 'websocket', channel: any) => {
    try {
      if (type === 'feishu') {
        const updated = await api.updateFeishuChannel(channel.id, {
          name: channel.name,
          app_id: channel.app_id,
          app_secret: undefined,
          allowed_users: channel.allowed_users,
          allow_all_users: channel.allow_all_users,
          enabled: !channel.enabled,
        });
        setFeishuChannels(feishuChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'wechat') {
        const updated = await api.updateWechatChannel(channel.id, {
          name: channel.name,
          mode: 'ilink',
          enabled: !channel.enabled,
          ilink_bot_token: channel.ilink_bot_token,
          ilink_base_url: channel.ilink_base_url,
          ilink_bot_id: channel.ilink_bot_id,
          ilink_user_id: channel.ilink_user_id,
        });
        setWechatChannels(wechatChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'dingtalk') {
        const updated = await api.updateDingtalkChannel(channel.id, {
          name: channel.name,
          client_id: channel.client_id,
          client_secret: undefined,
          enabled: !channel.enabled,
        });
        setDingtalkChannels(dingtalkChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'qq') {
        const updated = await api.updateQqChannel(channel.id, {
          name: channel.name,
          app_id: channel.app_id,
          secret: undefined,
          enabled: !channel.enabled,
        });
        setQqChannels(qqChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'email') {
        const updated = await api.updateEmailChannel(channel.id, {
          name: channel.name,
          smtp_host: channel.smtp_host,
          smtp_port: channel.smtp_port,
          smtp_username: channel.smtp_username,
          smtp_password: undefined,
          from_address: channel.from_address,
          enabled: !channel.enabled,
        });
        setEmailChannels(emailChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'msteams') {
        const updated = await api.updateMsteamsChannel(channel.id, {
          name: channel.name,
          app_id: channel.app_id,
          app_password: undefined,
          enabled: !channel.enabled,
        });
        setMsteamsChannels(msteamsChannels.map(c => c.id === channel.id ? updated : c));
      } else if (type === 'websocket') {
        const updated = await api.updateWebsocketChannel(channel.id, {
          name: channel.name,
          host: channel.host,
          port: channel.port,
          token: undefined,
          websocket_requires_token: channel.websocket_requires_token,
          enabled: !channel.enabled,
        });
        setWebsocketChannels(websocketChannels.map(c => c.id === channel.id ? updated : c));
      }
      toast.success(i18n.t("settings.channelSaved") || "Status toggled successfully");
    } catch (error: any) {
      toast.error((i18n.t("settings.channelSaveFailed") || "Toggle failed: ") + (error?.message || "Unknown error"));
    }
  };

  const deleteGenericChannel = async (type: 'feishu' | 'wechat' | 'dingtalk' | 'qq' | 'email' | 'msteams' | 'websocket', id: string) => {
    if (!window.confirm(i18n.t("settings.deleteConfirm") || "Are you sure you want to delete this channel?")) {
      return;
    }
    try {
      if (type === 'feishu') {
        await api.deleteFeishuChannel(id);
        setFeishuChannels(feishuChannels.filter(c => c.id !== id));
      } else if (type === 'wechat') {
        await api.deleteWechatChannel(id);
        setWechatChannels(wechatChannels.filter(c => c.id !== id));
      } else if (type === 'dingtalk') {
        await api.deleteDingtalkChannel(id);
        setDingtalkChannels(dingtalkChannels.filter(c => c.id !== id));
      } else if (type === 'qq') {
        await api.deleteQqChannel(id);
        setQqChannels(qqChannels.filter(c => c.id !== id));
      } else if (type === 'email') {
        await api.deleteEmailChannel(id);
        setEmailChannels(emailChannels.filter(c => c.id !== id));
      } else if (type === 'msteams') {
        await api.deleteMsteamsChannel(id);
        setMsteamsChannels(msteamsChannels.filter(c => c.id !== id));
      } else if (type === 'websocket') {
        await api.deleteWebsocketChannel(id);
        setWebsocketChannels(websocketChannels.filter(c => c.id !== id));
      }
      toast.success(i18n.t("settings.channelDeleted") || "Channel deleted successfully");
    } catch (error: any) {
      toast.error((i18n.t("settings.channelDeleteFailed") || "Delete failed: ") + (error?.message || "Unknown error"));
    }
  };

  // Poll WeChat Transient QR code and login status
  useEffect(() => {
    if (activeModalChannel?.type !== "wechat" || !showTransientScanner) {
      setTransientQrCode(null);
      setTransientQrStatus("idle");
      return;
    }

    let timeoutId: any = null;
    let isMounted = true;

    const fetchTransientQrAndPoll = async () => {
      try {
        setTransientQrStatus("waiting");
        const data = await api.getWechatTransientQrcode("ilink");
        if (!isMounted) return;

        if (data.qrcode) {
          setTransientQrCode(data.qrcode);
        }

        const pollStatus = async () => {
          if (!isMounted || !data.temp_id) return;
          try {
            const statusData = await api.getWechatTransientStatus(data.temp_id);
            if (!isMounted) return;

            if (statusData.status) {
              const status = statusData.status;
              if (status === "success" || status === "login" || status === "logged_in") {
                setTransientQrStatus("success");
                if (statusData.bot_token) {
                  setModalField1(statusData.bot_token);
                }
                if (statusData.baseurl) {
                  setModalField2(statusData.baseurl);
                }
                if (statusData.ilink_bot_id) {
                  setModalField3(statusData.ilink_bot_id);
                }
                if (statusData.ilink_user_id) {
                  setModalField4(statusData.ilink_user_id);
                }
                toast.success("扫码绑定成功！");
                setShowTransientScanner(false);
                return;
              } else if (status === "scanned") {
                setTransientQrStatus("scanned");
              } else if (status === "expired") {
                setTransientQrStatus("expired");
                return;
              } else {
                setTransientQrStatus("waiting");
              }
            }
          } catch (err) {
            console.error("Error polling transient WeChat status:", err);
          }
          timeoutId = setTimeout(pollStatus, 2000);
        };

        timeoutId = setTimeout(pollStatus, 2000);
      } catch (err: any) {
        console.error("Error initiating transient WeChat QR login:", err);
        const errMsg = err.response?.data?.detail || "无法获取扫码登录二维码，请确保通道配置正确且网关正常启动";
        toast.error(errMsg);
        setTransientQrStatus("idle");
      }
    };

    fetchTransientQrAndPoll();

    return () => {
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [activeModalChannel, showTransientScanner]);

  if (authFailed) {
    return (
      <div className="mx-auto max-w-md w-full p-4 space-y-4">
        <AuthBarrier
          onLogin={(key) => {
            setApiAuthKey(key);
            window.location.reload();
          }}
        />
      </div>
    );
  }

  if (loading || !form || !settings || !dataSettings) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{i18n.t("settings.title")}</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">{i18n.t("settings.subtitle")}</p>
        </div>
        <div className="flex min-h-32 items-center justify-center rounded-lg border bg-card p-3.5 text-sm text-muted-foreground">
          {settingsLoadError ? (
            <div className="text-center">
              <div className="font-medium text-foreground">{i18n.t("settings.unavailable")}</div>
              <div className="mt-1">{settingsLoadError}</div>
            </div>
          ) : (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {i18n.t("settings.loading")}
            </>
          )}
        </div>
      </div>
    );
  }

  const keyStatus = settings.api_key_configured
    ? i18n.t("settings.configured")
    : settings.api_key_required
      ? i18n.t("settings.keepCurrentKey")
      : selectedProvider?.auth_type === "oauth" && selectedProvider.login_command
        ? i18n.t("settings.providerUsesOauth", { command: selectedProvider.login_command })
        : i18n.t("settings.noApiKeyRequired");
  const apiKeyDisabled = !selectedProvider?.api_key_required || clearApiKey;
  const tushareStatus = dataSettings.tushare_token_configured
    ? i18n.t("settings.configured")
    : i18n.t("settings.keepCurrentToken");


  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{i18n.t("settings.title")}</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">{i18n.t("settings.subtitle")}</p>
        </div>
      </div>

      <div className="space-y-4">

      {/* Consolidated Notification Channels Management Card */}
      <section className="rounded-lg border bg-card p-5 shadow-sm space-y-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between border-b pb-4 border-border/40">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-primary">
              <MessageSquare className="h-5 w-5" />
              <h2 className="text-base font-semibold text-foreground">通知通道管理</h2>
            </div>
            <p className="max-w-3xl text-xs text-muted-foreground">在此配置与维护通知通道参数，双向绑定不同网关完成推送隔离。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={refreshChannelStatus}
              disabled={channelRefreshing}
              className="inline-flex items-center justify-center gap-1.5 rounded-md border px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer bg-background"
            >
              {channelRefreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              刷新状态
            </button>
          </div>
        </div>

        {/* Global Stats Summary bar */}
        {(() => {
          const supportedChannelKeys = ["weixin", "feishu", "dingtalk", "qq", "email", "msteams", "websocket"];
          const channelRows = channelStatus
            ? Object.entries(channelStatus.channels ?? {}).filter(([key]) => supportedChannelKeys.includes(key))
            : [];
          const channelEnabledCount = channelRows.filter(([, item]) => item.enabled).length;
          const channelLoadedCount = channelRows.filter(([, item]) => item.loaded).length;
          const channelUnavailableCount = channelRows.filter(([, item]) => item.available === false).length;
          const runningState = channelStatus?.running ? "运行中 (Running)" : "已停止 (Stopped)";
          return (
            <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
              <div className="rounded-md border bg-muted/10 px-3.5 py-3.5 space-y-1">
                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">服务状态</div>
                <div className="text-sm font-semibold text-foreground">{runningState}</div>
              </div>
              <div className="rounded-md border bg-muted/10 px-3.5 py-3.5 space-y-1">
                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">已启用通道</div>
                <div className="text-sm font-semibold text-foreground">{channelEnabledCount}</div>
              </div>
              <div className="rounded-md border bg-muted/10 px-3.5 py-3.5 space-y-1">
                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">已加载通道</div>
                <div className="text-sm font-semibold text-foreground">{channelLoadedCount}</div>
              </div>
              <div className="rounded-md border bg-muted/10 px-3.5 py-3.5 space-y-1">
                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">不可用通道</div>
                <div className="text-sm font-semibold text-foreground">{channelUnavailableCount}</div>
              </div>
            </div>
          );
        })()}

        {/* Single Integrated Horizontal Configuration & Diagnostics Table */}
        <div className="overflow-x-auto rounded-md border border-border/60">
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-muted-foreground select-none">
              <tr className="border-b border-border/40">
                <th className="px-3 py-3 text-left font-semibold">通道类型</th>
                <th className="px-3 py-3 text-left font-semibold">诊断与恢复提示</th>
                <th className="px-3 py-3 text-left font-semibold">当前配置</th>
                <th className="px-3 py-3 text-left font-semibold">状态</th>
                <th className="px-3 py-3 text-right font-semibold">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {/* Helper variables inside tbody to get diagnostic logic */}
              {(() => {
                const getDiag = (key: string) => {
                  const item = channelStatus?.channels?.[key];
                  if (!item) return "未加载";
                  return item.error || item.install_hint || "运行状态正常";
                };

                const renderActions = (type: 'feishu' | 'wechat' | 'dingtalk' | 'qq' | 'email' | 'msteams' | 'websocket', chan: any) => (
                  <div className="flex items-center justify-end gap-2.5">
                    {chan && (
                      <button
                        type="button"
                        onClick={() => toggleGenericChannel(type, chan)}
                        className={`rounded p-1 border hover:bg-muted transition cursor-pointer ${chan.enabled ? "text-green-500 border-green-500/20" : "text-muted-foreground border-border"}`}
                        title="启用/禁用"
                      >
                        <Power className="h-3.5 w-3.5" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => openChannelConfigModal(type, chan)}
                      className="rounded px-2.5 py-1 border border-primary/20 text-primary hover:bg-primary/5 transition text-[11px] font-medium cursor-pointer"
                    >
                      {chan ? "编辑" : "配置"}
                    </button>
                    {chan && (
                      <button
                        type="button"
                        onClick={() => deleteGenericChannel(type, chan.id)}
                        className="rounded p-1 border border-red-500/20 text-red-400 hover:text-red-500 hover:bg-red-500/5 transition cursor-pointer"
                        title="删除"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                );

                const wechatChan = wechatChannels[0];
                const feishuChan = feishuChannels[0];
                const dingtalkChan = dingtalkChannels[0];
                const qqChan = qqChannels[0];
                const emailChan = emailChannels[0];
                const msteamsChan = msteamsChannels[0];
                const websocketChan = websocketChannels[0];

                return (
                  <>
                    {/* 1. WeChat Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <Activity className="h-4 w-4 text-green-500" />
                          <div className="font-semibold text-foreground">个人微信 (WeChat)</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          对接微信官方 iLink 服务，支持微信消息交互。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("weixin")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {wechatChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {wechatChan.name}</div>
                            {wechatChan.ilink_bot_id && <div>Bot ID: {wechatChan.ilink_bot_id}</div>}
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          wechatChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {wechatChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("wechat", wechatChan)}
                      </td>
                    </tr>

                    {/* 2. Feishu Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-blue-500" />
                          <div className="font-semibold text-foreground">飞书机器人 (Feishu)</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          对接飞书应用机器人，支持长连接与事件订阅。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("feishu")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {feishuChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {feishuChan.name}</div>
                            <div>App ID: {feishuChan.app_id}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          feishuChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {feishuChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("feishu", feishuChan)}
                      </td>
                    </tr>

                    {/* 3. DingTalk Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <MessageSquareMore className="h-4 w-4 text-sky-500" />
                          <div className="font-semibold text-foreground">钉钉机器人 (DingTalk)</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          对接钉钉 Stream Gateway 实现长连接双向推送。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("dingtalk")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {dingtalkChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {dingtalkChan.name}</div>
                            <div>Client ID: {dingtalkChan.client_id}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          dingtalkChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {dingtalkChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("dingtalk", dingtalkChan)}
                      </td>
                    </tr>

                    {/* 4. QQ Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-amber-500" />
                          <div className="font-semibold text-foreground">QQ机器人 (QQ Bot)</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          对接 NapCat / QQ 官方开放平台通知机器人。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("qq")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {qqChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {qqChan.name}</div>
                            <div>App ID: {qqChan.app_id}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          qqChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {qqChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("qq", qqChan)}
                      </td>
                    </tr>

                    {/* 5. Email Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <Database className="h-4 w-4 text-purple-500" />
                          <div className="font-semibold text-foreground">邮箱通知 (SMTP Email)</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          使用 SMTP 服务发送行情警报与核心调仓邮件。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("email")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {emailChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {emailChan.name}</div>
                            <div>发件箱: {emailChan.smtp_username}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          emailChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {emailChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("email", emailChan)}
                      </td>
                    </tr>

                    {/* 6. MS Teams Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <Server className="h-4 w-4 text-indigo-500" />
                          <div className="font-semibold text-foreground">MS Teams 机器人</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          对接 Microsoft Teams Webhook，发送量化提醒。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("msteams")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {msteamsChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {msteamsChan.name}</div>
                            <div>App ID: {msteamsChan.app_id}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          msteamsChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {msteamsChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("msteams", msteamsChan)}
                      </td>
                    </tr>

                    {/* 7. WebSocket Row */}
                    <tr className="hover:bg-muted/10 transition">
                      <td className="px-3 py-3.5 align-top">
                        <div className="flex items-center gap-2">
                          <SlidersHorizontal className="h-4 w-4 text-cyan-500" />
                          <div className="font-semibold text-foreground">WebSocket 接口</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[220px]">
                          开启本地 WebSocket 监听，支持外部指令直接收发。
                        </div>
                      </td>
                      <td className="px-3 py-3.5 align-top text-muted-foreground leading-relaxed max-w-[280px] break-words">
                        {getDiag("websocket")}
                      </td>
                      <td className="px-3 py-3.5 align-top font-mono text-[10.5px] text-muted-foreground">
                        {websocketChan ? (
                          <div className="space-y-0.5">
                            <div>别名: {websocketChan.name}</div>
                            <div>监听: {websocketChan.host}:{websocketChan.port}</div>
                          </div>
                        ) : (
                          <span className="italic text-muted-foreground/60">尚未配置</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 align-top">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                          websocketChan?.enabled 
                            ? "bg-green-500/10 text-green-400 border-green-500/20" 
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          {websocketChan?.enabled ? "已启用" : "未启用"}
                        </span>
                      </td>
                      <td className="px-3 py-3.5 align-top text-right">
                        {renderActions("websocket", websocketChan)}
                      </td>
                    </tr>
                  </>
                );
              })()}
            </tbody>
          </table>
        </div>
      </section>

          {/* Tenant LLM Settings */}
          {/* Tenant LLM settings has a connection and generation settings form which is toggled by Custom vs Default */}
          <form onSubmit={submit} className="grid gap-3.5 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)] border bg-card/30 rounded-md p-3.5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 col-span-full border-b pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  <h2 className="text-base font-semibold">{i18n.t("settings.llmSettings")}</h2>
                </div>
                <p className="text-xs text-muted-foreground">{i18n.t("settings.llmSettingsDesc")}</p>
              </div>
              <div className="flex items-center gap-2 bg-muted/65 p-1 rounded-lg border border-border/80">
                <button
                  type="button"
                  onClick={() => setLlmMode("default")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                    llmMode === "default"
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  默认 (项目配置)
                </button>
                <button
                  type="button"
                  onClick={() => setLlmMode("custom")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                    llmMode === "custom"
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  自定义 (覆盖配置)
                </button>
              </div>
            </div>

            {llmMode === "default" ? (
              <div className="rounded-lg border bg-muted/20 p-4.5 text-center space-y-4 col-span-full">
                <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-full w-fit mx-auto">
                  <Server className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-semibold text-foreground">已启用“默认项目配置”</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto">
                    当前大模型配置已设置为继承系统管理员配置的全局默认参数。如果您想要独立自定义，请点击上方“自定义 (覆盖配置)”按钮。
                  </p>
                </div>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  确认保存，使用项目默认 LLM
                </button>
              </div>
            ) : (
              <>
                <section className="rounded-lg border bg-card p-3.5 shadow-sm">
                  <div className="mb-5 flex items-center gap-2">
                    <Server className="h-4 w-4 text-primary" />
                    <h2 className="text-base font-semibold">{i18n.t("settings.connection")}</h2>
                  </div>

                  <div className="grid gap-4">
                    <label className="grid gap-2">
                      <span className={labelClass}>{i18n.t("settings.provider")}</span>
                      <select
                        value={form.provider}
                        onChange={(event) => onProviderChange(event.target.value)}
                        className={fieldClass}
                      >
                        {providers.map((provider) => (
                          <option key={provider.name} value={provider.name}>{provider.label}</option>
                        ))}
                      </select>
                      <span className={hintClass}>{"Changing providers updates the recommended model and endpoint."}</span>
                    </label>

                    <label className="grid gap-2">
                      <span className={labelClass}>{i18n.t("settings.model")}</span>
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
                          title={i18n.t("settings.useProviderDefaults")}
                        >
                          <RotateCcw className="h-4 w-4" />
                          <span className="hidden sm:inline">{i18n.t("settings.useProviderDefaults")}</span>
                        </button>
                      </div>
                      <span className={hintClass}>{i18n.t("settings.modelIdHint")}</span>
                    </label>

                    <label className="grid gap-2">
                      <span className={labelClass}>{i18n.t("settings.baseUrl")}</span>
                      <input
                        value={form.base_url}
                        onChange={(event) => setForm({ ...form, base_url: event.target.value })}
                        className={fieldClass}
                        placeholder={selectedProvider?.default_base_url}
                        disabled={selectedProvider?.auth_type === "oauth"}
                      />
                    </label>

                    <label className="grid gap-2">
                      <span className={labelClass}>
                        {selectedProvider?.auth_type === "oauth" ? "OAuth" : "API key"}
                      </span>
                      <div className="relative">
                        <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        <input
                          type="password"
                          value={apiKey}
                          onChange={(event) => setApiKey(event.target.value)}
                          className={`${fieldClass} pl-9`}
                          placeholder={settings.api_key_hint || keyStatus}
                          autoComplete="current-password"
                          disabled={apiKeyDisabled}
                        />
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className={hintClass}>{settings.api_key_hint || keyStatus}</span>
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
                            {i18n.t("settings.clearApiKey")}
                          </label>
                        ) : null}
                      </div>
                      {selectedProvider?.api_key_required && (
                        <div className="text-xs text-muted-foreground/80 mt-1">
                          支持配置多个 Key（以英文逗号分隔），系统会自动进行并发轮换与 429 冷却重试自愈。
                        </div>
                      )}
                    </label>
                  </div>
                </section>

                <section className="rounded-lg border bg-card p-3.5 shadow-sm flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="mb-5 flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4 text-primary" />
                      <h2 className="text-base font-semibold">{i18n.t("settings.generation")}</h2>
                    </div>

                    <div className="grid gap-4">
                      <label className="grid gap-2">
                        <span className={labelClass}>{i18n.t("settings.temperature")}</span>
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
                        <span className={labelClass}>{i18n.t("settings.timeoutSeconds")}</span>
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
                        <span className={labelClass}>{i18n.t("settings.maxRetries")}</span>
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
                        <span className={labelClass}>{i18n.t("settings.reasoningEffort")}</span>
                        <select
                          value={form.reasoning_effort}
                          onChange={(event) => setForm({ ...form, reasoning_effort: event.target.value })}
                          className={fieldClass}
                        >
                          <option value="">{i18n.t("settings.off")}</option>
                          <option value="low">{i18n.t("settings.reasoningEffortLow")}</option>
                          <option value="medium">{i18n.t("settings.reasoningEffortMedium")}</option>
                          <option value="high">{i18n.t("settings.reasoningEffortHigh")}</option>
                          <option value="max">{i18n.t("settings.reasoningEffortMax")}</option>
                        </select>
                        <span className={hintClass}>{i18n.t("settings.reasoningEffortDesc")}</span>
                      </label>

                      <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">{i18n.t("settings.saved")}: </span>
                        <span className="break-all font-mono">{settings.env_path}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={saving}
                    className="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
                  >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {saving ? i18n.t("settings.saving") : i18n.t("settings.save")}
                  </button>
                </section>
              </>
            )}
          </form>

          {/* Tenant Data Source Settings */}
          <form onSubmit={submitDataSources} className="rounded-lg border bg-card p-3.5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary" />
                  <h2 className="text-base font-semibold">{i18n.t("settings.dataSourceSettings")}</h2>
                </div>
                <p className="text-sm text-muted-foreground">{i18n.t("settings.dataSourceSettingsDesc")}</p>
              </div>
              <div className="flex items-center gap-2 bg-muted/65 p-1 rounded-lg border border-border/80">
                <button
                  type="button"
                  onClick={() => setDataMode("default")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                    dataMode === "default"
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  默认 (项目配置)
                </button>
                <button
                  type="button"
                  onClick={() => setDataMode("custom")}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                    dataMode === "custom"
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  自定义 (覆盖配置)
                </button>
              </div>
            </div>

            {dataMode === "default" ? (
              <div className="rounded-lg border bg-muted/20 p-4.5 text-center space-y-4">
                <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-full w-fit mx-auto">
                  <Database className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-semibold text-foreground">已启用“默认项目数据源配置”</h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto">
                    当前数据源配置已设置为继承系统管理员配置的全局默认参数（包括 Tushare, iWencai, FRED 等）。如果您想要独立自定义，请点击上方“自定义 (覆盖配置)”按钮。
                  </p>
                </div>
                <button
                  type="submit"
                  disabled={dataSaving}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
                >
                  {dataSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  确认保存，使用项目默认数据源
                </button>
              </div>
            ) : (
              <div className="grid gap-3.5 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
                <div className="grid gap-4">
                  <label className="grid gap-2">
                    <span className={labelClass}>{i18n.t("settings.tushareToken")}</span>
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
                      <span className={hintClass}>{i18n.t("settings.tushareDesc")}</span>
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
                        {i18n.t("settings.clearTushareToken")}
                      </label>
                    </div>
                  </label>

                  <label className="grid gap-2">
                    <span className={labelClass}>{i18n.t("settings.iwencaiApiKey")}</span>
                    <div className="relative">
                      <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <input
                        type="password"
                        value={iwencaiKey}
                        onChange={(event) => setIwencaiKey(event.target.value)}
                        className={`${fieldClass} pl-9`}
                        placeholder={dataSettings.iwencai_key_configured ? i18n.t("settings.configured") : i18n.t("settings.keepCurrentKey")}
                        autoComplete="current-password"
                        disabled={clearIwencaiKey}
                      />
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className={hintClass}>{i18n.t("settings.iwencaiDesc")}</span>
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
                        {i18n.t("settings.clearSavedKey")}
                      </label>
                    </div>
                  </label>

                  <label className="grid gap-2">
                    <span className={labelClass}>{i18n.t("settings.fredApiKey")}</span>
                    <div className="relative">
                      <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <input
                        type="password"
                        value={fredApiKey}
                        onChange={(event) => setFredApiKey(event.target.value)}
                        className={`${fieldClass} pl-9`}
                        placeholder={dataSettings.fred_api_key_configured ? i18n.t("settings.configured") : i18n.t("settings.keepCurrentKey")}
                        autoComplete="current-password"
                        disabled={clearFredApiKey}
                      />
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className={hintClass}>{i18n.t("settings.fredDesc")}</span>
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
                        {i18n.t("settings.clearSavedKey")}
                      </label>
                    </div>
                  </label>

                  <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{i18n.t("settings.saved")}: </span>
                    <span className="break-all font-mono">{dataSettings.env_path}</span>
                  </div>

                  <button
                    type="submit"
                    disabled={dataSaving}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
                  >
                    {dataSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {dataSaving ? i18n.t("settings.saving") : i18n.t("settings.saveDataSourceSettings")}
                  </button>
                </div>

                <div className="rounded-md border bg-muted/20 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{i18n.t("settings.baostock")}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${dataSettings.baostock_supported ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
                      {dataSettings.baostock_supported ? i18n.t("settings.loaderAvailable") : i18n.t("settings.noProjectLoader")}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm text-muted-foreground font-sans">
                    <p>{dataSettings.baostock_message}</p>
                    <p>
                      {dataSettings.baostock_installed
                        ? i18n.t("settings.pythonPackageInstalled")
                        : i18n.t("settings.pythonPackageNotInstalled")}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </form>

          {/* 同花顺自选同步设置 (用户独立配置卡片) */}
          <form onSubmit={submitThsSync} className="rounded-lg border bg-card p-3.5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  <h2 className="text-base font-semibold">同花顺自选股同步设置</h2>
                </div>
                <p className="text-sm text-muted-foreground">配置您的同花顺个人网页端 Cookie，用于同步云端自选股与本地 Watchlist 数据库。</p>
              </div>
            </div>

            <div className="grid gap-3.5 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
              <div className="grid gap-4">
                <label className="grid gap-2">
                  <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    同花顺 Cookie
                    {dataSettings.ths_cookie_configured && (
                      <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-500 ring-1 ring-inset ring-emerald-500/20">
                        ✓ 已配置
                      </span>
                    )}
                    {thsSavedOk && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-500 ring-1 ring-inset ring-emerald-500/30 animate-in fade-in duration-300">
                        ✓ 已保存
                      </span>
                    )}
                  </span>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <input
                      type="password"
                      value={thsCookie}
                      onChange={(event) => setThsCookie(event.target.value)}
                      className={`${fieldClass} pl-9`}
                      placeholder={dataSettings.ths_cookie_configured ? "已配置，输入以替换旧 Cookie" : "请输入同花顺个人 Cookie"}
                      autoComplete="current-password"
                    />
                  </div>
                  <span className={hintClass}>用于同花顺云端自选股与本地 Watchlist 的双向同步</span>
                </label>

                <div className="flex flex-col gap-2 rounded-md bg-muted/20 p-3 border border-border/40">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">测试同花顺 Cookie 是否有效：</span>
                    <button
                      type="button"
                      onClick={handleTestThsConnection}
                      disabled={thsTesting}
                      className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md border border-border bg-background hover:bg-muted text-foreground transition disabled:opacity-50 cursor-pointer"
                    >
                      {thsTesting ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          测试中...
                        </>
                      ) : (
                        "测试连接"
                      )}
                    </button>
                  </div>

                  {thsTestResult && (
                    <div className={`text-xs rounded p-2 ${thsTestResult.success ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" : "bg-destructive/10 text-destructive border border-destructive/20"}`}>
                      {thsTestResult.success ? "✅ " : "❌ "}
                      {thsTestResult.message}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={thsSaving}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-70 cursor-pointer shadow-sm"
                  >
                    {thsSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {thsSaving ? "保存中..." : "保存同花顺设置"}
                  </button>

                  {dataSettings.ths_cookie_configured && (
                    <button
                      type="button"
                      onClick={handleClearThsCookie}
                      disabled={thsSaving}
                      className="inline-flex items-center justify-center gap-1.5 rounded-md border border-destructive/40 px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 transition disabled:opacity-50 cursor-pointer"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      清除 Cookie
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                {/* 手动同步区域 */}
                {dataSettings.ths_cookie_configured && (
                  <div className="rounded-md border border-border/40 bg-muted/10 p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-foreground">手动同步</span>
                      <button
                        type="button"
                        onClick={handleManualThsSync}
                        disabled={thsSyncing}
                        className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md border border-border bg-background hover:bg-muted text-foreground transition disabled:opacity-50 cursor-pointer"
                      >
                        {thsSyncing ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            同步中...
                          </>
                        ) : (
                          <>
                            <RotateCcw className="h-3 w-3" />
                            立即同步自选股
                          </>
                        )}
                      </button>
                    </div>
                    {thsSyncResult && (
                      <div className={`text-xs rounded p-2 ${thsSyncResult.success ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" : "bg-destructive/10 text-destructive border border-destructive/20"}`}>
                        {thsSyncResult.success ? "✅ " : "❌ "}{thsSyncResult.message}
                      </div>
                    )}
                  </div>
                )}

                {/* 自动同步机制说明 */}
                <details className="group rounded-md border border-border/40 bg-muted/10">
                  <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-medium text-muted-foreground hover:text-foreground">
                    <span>⏱️ 自动同步机制</span>
                    <span className="transition group-open:rotate-180">▼</span>
                  </summary>
                  <div className="p-3 pt-0 text-xs text-muted-foreground space-y-2 border-t border-border/30">
                    <p className="font-medium text-foreground">双向同步：同花顺 ⇄ TideTrading</p>
                    <ul className="space-y-1 pl-2">
                      <li>• 在 TideTrading 新增/删除自选股 → 自动推送到同花顺云端</li>
                      <li>• 在同花顺 App/网页修改自选股 → 自动同步到本地</li>
                    </ul>
                    <p className="font-medium text-foreground pt-1">轮询频率</p>
                    <ul className="space-y-1 pl-2">
                      <li>• 📈 <span className="text-foreground font-medium">交易日盘中</span>（周一–五 09:30–15:00）—— 每 <span className="text-foreground font-medium">5 分钟</span></li>
                      <li>• 🌙 <span className="text-foreground font-medium">盘前/盘后及周末</span> —— 每 <span className="text-foreground font-medium">30 分钟</span></li>
                    </ul>
                    <p className="text-[10px] text-muted-foreground/60 pt-1">🔒 写接口仅在检测到本地变化时才调用，不主动超频请求</p>
                  </div>
                </details>

                {/* 如何获取 Cookie */}
                <details open className="group rounded-md border border-border/40 bg-muted/10">
                  <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-medium text-muted-foreground hover:text-foreground">
                    <span>💡 如何获取同花顺 Cookie？（仅需3步）</span>
                    <span className="transition group-open:rotate-180">▼</span>
                  </summary>
                  <div className="p-3 pt-0 text-xs text-muted-foreground space-y-2 border-t border-border/30">
                    <p>1. 在电脑浏览器上访问并登录 <a href="http://stock.10jqka.com.cn/" target="_blank" rel="noreferrer" className="text-primary hover:underline font-medium">同花顺个人中心</a>。</p>
                    <p>2. 登录成功后，按键盘的 <strong>F12</strong> 键（或右击网页任意空白处选择"检查"），切换到 <strong>"网络 (Network)"</strong> 面板。</p>
                    <p>3. 刷新一下页面，在网络请求列表中点击任意以 <code>10jqka.com.cn</code> 结尾的请求，在右侧 <strong>"请求标头 (Request Headers)"</strong> 中找到 <code>Cookie</code>，完整复制其对应的一长串值，粘贴到上方输入框保存即可。</p>
                  </div>
                </details>
              </div>
            </div>
          </form>

        </div>
       



      {/* Generic Channel Configuration Modal */}
      {activeModalChannel && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-md border bg-card p-5 shadow-xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              {activeModalChannel.id ? "编辑" : "配置"} 
              {activeModalChannel.type === 'feishu' && "飞书机器人"}
              {activeModalChannel.type === 'wechat' && "个人微信 (iLink)"}
              {activeModalChannel.type === 'dingtalk' && "钉钉机器人"}
              {activeModalChannel.type === 'qq' && "QQ机器人"}
              {activeModalChannel.type === 'email' && "邮箱通知 (SMTP)"}
              {activeModalChannel.type === 'msteams' && "MSTeams机器人"}
              {activeModalChannel.type === 'websocket' && "WebSocket 接口"}
            </h3>

            <form onSubmit={submitChannelConfig} className="space-y-4">
              {/* Common Name Field */}
              <label className="grid gap-1.5">
                <span className={labelClass}>通道名称</span>
                <input
                  type="text"
                  required
                  value={modalName}
                  onChange={(e) => setModalName(e.target.value)}
                  className={fieldClass}
                  placeholder="请输入通道别名，例如：量化交易助理"
                />
              </label>

              {/* 1. Feishu Specific Fields */}
              {activeModalChannel.type === 'feishu' && (
                <>
                  <label className="grid gap-1.5">
                    <span className={labelClass}>App ID</span>
                    <input
                      type="text"
                      required
                      value={modalField1}
                      onChange={(e) => setModalField1(e.target.value)}
                      className={fieldClass}
                      placeholder="cli_xxxxxxxx"
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>App Secret</span>
                    <div className="relative">
                      <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                      <input
                        type="password"
                        required={!activeModalChannel.id}
                        value={modalField2}
                        onChange={(e) => setModalField2(e.target.value)}
                        className={`${fieldClass} pl-9`}
                        placeholder={activeModalChannel.id ? "•••••••• (无需修改请留空)" : "App Secret"}
                        autoComplete="new-password"
                      />
                    </div>
                  </label>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="feishuAllowAll"
                      checked={modalBool1}
                      onChange={(e) => setModalBool1(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
                    />
                    <label htmlFor="feishuAllowAll" className="text-xs text-muted-foreground cursor-pointer select-none">
                      允许任何人调试或互动聊天
                    </label>
                  </div>

                  {!modalBool1 ? (
                    <label className="grid gap-1.5">
                      <span className={labelClass}>限制允许成员 (以逗号分隔的 OpenID)</span>
                      <input
                        type="text"
                        value={modalField3}
                        onChange={(e) => setModalField3(e.target.value)}
                        className={fieldClass}
                        placeholder="ou_xxxxxxxx,ou_yyyyyyyy"
                      />
                      <span className={hintClass}>仅允许列表中的飞书用户与此机器人对话。</span>
                    </label>
                  ) : (
                    <div className="rounded-md bg-amber-500/10 p-3.5 text-xs text-amber-500 border border-amber-500/20 leading-relaxed">
                      ⚠️ <strong>公测调试模式已启用</strong>：任何飞书群组或私聊中添加此机器人的用户均可向其发送交易指令。
                    </div>
                  )}
                </>
              )}

              {/* 2. WeChat Specific Fields */}
              {activeModalChannel.type === 'wechat' && (
                <div className="space-y-4">
                  {showTransientScanner ? (
                    <div className="flex flex-col items-center justify-center p-4 border border-dashed rounded-lg bg-black/20 gap-3 max-w-sm mx-auto w-full animate-in fade-in duration-200">
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        {transientQrStatus === "waiting" && "请使用手机微信扫描二维码登录"}
                        {transientQrStatus === "scanned" && "已扫码，请在手机端确认登录"}
                        {transientQrStatus === "success" && "🎉 扫码登录成功！"}
                        {transientQrStatus === "expired" && "二维码已过期，请重新获取"}
                      </div>

                      {transientQrCode ? (
                        <div className="relative border p-2 bg-white rounded-lg">
                          <img
                            src={transientQrCode}
                            alt="WeChat Login QR Code"
                            className="h-40 w-40 object-contain animate-fade-in"
                          />
                          {transientQrStatus === "expired" && (
                            <div className="absolute inset-0 bg-black/75 flex items-center justify-center rounded-lg flex-col gap-2">
                              <span className="text-xs text-white">二维码已过期</span>
                              <button
                                type="button"
                                onClick={() => {
                                  setTransientQrCode(null);
                                  setTransientQrStatus("idle");
                                  setShowTransientScanner(false);
                                  setTimeout(() => setShowTransientScanner(true), 50);
                                }}
                                className="rounded bg-primary px-2.5 py-1 text-[11px] font-medium text-white hover:opacity-90 cursor-pointer"
                              >
                                点击刷新
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="h-40 w-40 flex items-center justify-center border rounded-lg bg-muted/30">
                          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                      )}

                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-1">
                        <span className={`h-2 w-2 rounded-full ${
                          transientQrStatus === "success" ? "bg-green-500" :
                          transientQrStatus === "scanned" ? "bg-blue-500 animate-pulse" :
                          "bg-yellow-500 animate-pulse"
                        }`} />
                        <span>
                          {transientQrStatus === "success" ? "已连接" :
                           transientQrStatus === "scanned" ? "已扫码，待手机确认" :
                           "等待手机扫码..."}
                        </span>
                      </div>

                      {activeModalChannel.id && (
                        <button
                          type="button"
                          onClick={() => setShowTransientScanner(false)}
                          className="text-xs text-primary hover:underline mt-1 cursor-pointer"
                        >
                          取消并返回
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="text-xs text-muted-foreground bg-black/10 border border-border/60 rounded-md p-3">
                        <p className="font-semibold text-foreground mb-1 text-center">官方微信机器人 (iLink) 绑定详情</p>
                        <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border/40">
                          <div>
                            <span className="block text-[10px] text-muted-foreground">Bot ID</span>
                            <span className="font-mono text-xs text-foreground block truncate">{modalField3 || "未绑定"}</span>
                          </div>
                          <div>
                            <span className="block text-[10px] text-muted-foreground">管理员微信 ID</span>
                            <span className="font-mono text-xs text-foreground block truncate select-all break-all">{modalField4 || "未绑定"}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-center">
                        <button
                          type="button"
                          onClick={() => {
                            setModalField1("");
                            setModalField2("");
                            setModalField3("");
                            setModalField4("");
                            setShowTransientScanner(true);
                          }}
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold border bg-background hover:bg-accent hover:text-accent-foreground transition cursor-pointer"
                        >
                          <QrCode className="h-3.5 w-3.5" />
                          重新扫码绑定
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 3. DingTalk Specific Fields */}
              {activeModalChannel.type === 'dingtalk' && (
                <>
                  <label className="grid gap-1.5">
                    <span className={labelClass}>Client ID (钉钉应用 Key)</span>
                    <input
                      type="text"
                      required
                      value={modalField1}
                      onChange={(e) => setModalField1(e.target.value)}
                      className={fieldClass}
                      placeholder="e.g. dingxxxxxxxxxxxx"
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>Client Secret (钉钉应用 AppSecret)</span>
                    <input
                      type="password"
                      required={!activeModalChannel.id}
                      value={modalField2}
                      onChange={(e) => setModalField2(e.target.value)}
                      className={fieldClass}
                      placeholder={activeModalChannel.id ? "•••••••• (无需修改请留空)" : "Client Secret"}
                    />
                  </label>
                </>
              )}

              {/* 4. QQ Specific Fields */}
              {activeModalChannel.type === 'qq' && (
                <>
                  <label className="grid gap-1.5">
                    <span className={labelClass}>App ID (机器人应用 ID)</span>
                    <input
                      type="text"
                      required
                      value={modalField1}
                      onChange={(e) => setModalField1(e.target.value)}
                      className={fieldClass}
                      placeholder="e.g. 102030405"
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>Bot Token (机器人令牌)</span>
                    <input
                      type="password"
                      required={!activeModalChannel.id}
                      value={modalField2}
                      onChange={(e) => setModalField2(e.target.value)}
                      className={fieldClass}
                      placeholder={activeModalChannel.id ? "•••••••• (无需修改请留空)" : "Token"}
                    />
                  </label>
                </>
              )}

              {/* 5. Email Specific Fields */}
              {activeModalChannel.type === 'email' && (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="grid gap-1.5">
                        <span className={labelClass}>SMTP 服务器地址</span>
                        <input
                          type="text"
                          required
                          value={modalField1}
                          onChange={(e) => setModalField1(e.target.value)}
                          className={fieldClass}
                          placeholder="e.g. smtp.qq.com"
                        />
                      </label>
                    </div>
                    <div>
                      <label className="grid gap-1.5">
                        <span className={labelClass}>SMTP 端口</span>
                        <input
                          type="number"
                          required
                          value={modalField2}
                          onChange={(e) => setModalField2(e.target.value)}
                          className={fieldClass}
                          placeholder="465"
                        />
                      </label>
                    </div>
                  </div>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>发件人邮箱账号</span>
                    <input
                      type="email"
                      required
                      value={modalField3}
                      onChange={(e) => setModalField3(e.target.value)}
                      className={fieldClass}
                      placeholder="e.g. your_email@qq.com"
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>客户端授权码 (或邮箱密码)</span>
                    <input
                      type="password"
                      required={!activeModalChannel.id}
                      value={modalField4}
                      onChange={(e) => setModalField4(e.target.value)}
                      className={fieldClass}
                      placeholder={activeModalChannel.id ? "•••••••• (无需修改请留空)" : "授权码密码"}
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>发件人显示邮箱 (From)</span>
                    <input
                      type="email"
                      required
                      value={modalField5}
                      onChange={(e) => setModalField5(e.target.value)}
                      className={fieldClass}
                      placeholder="e.g. your_email@qq.com"
                    />
                  </label>
                </>
              )}

              {/* 6. MS Teams Specific Fields */}
              {activeModalChannel.type === 'msteams' && (
                <>
                  <label className="grid gap-1.5">
                    <span className={labelClass}>Teams App ID</span>
                    <input
                      type="text"
                      required
                      value={modalField1}
                      onChange={(e) => setModalField1(e.target.value)}
                      className={fieldClass}
                      placeholder="e.g. 3ea7xxxx-xxxx-xxxx"
                    />
                  </label>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>App Password (应用密码)</span>
                    <input
                      type="password"
                      required={!activeModalChannel.id}
                      value={modalField2}
                      onChange={(e) => setModalField2(e.target.value)}
                      className={fieldClass}
                      placeholder={activeModalChannel.id ? "•••••••• (无需修改请留空)" : "App Password"}
                    />
                  </label>
                </>
              )}

              {/* 7. WebSocket Specific Fields */}
              {activeModalChannel.type === 'websocket' && (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="grid gap-1.5">
                        <span className={labelClass}>本地监听地址</span>
                        <input
                          type="text"
                          required
                          value={modalField1}
                          onChange={(e) => setModalField1(e.target.value)}
                          className={fieldClass}
                          placeholder="e.g. 127.0.0.1"
                        />
                      </label>
                    </div>
                    <div>
                      <label className="grid gap-1.5">
                        <span className={labelClass}>端口</span>
                        <input
                          type="number"
                          required
                          value={modalField2}
                          onChange={(e) => setModalField2(e.target.value)}
                          className={fieldClass}
                          placeholder="8765"
                        />
                      </label>
                    </div>
                  </div>

                  <label className="grid gap-1.5">
                    <span className={labelClass}>连接密钥 / Token (留空表示不进行验证)</span>
                    <input
                      type="password"
                      value={modalField3}
                      onChange={(e) => setModalField3(e.target.value)}
                      className={fieldClass}
                      placeholder="Token"
                    />
                  </label>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="wsRequireToken"
                      checked={modalBool1}
                      onChange={(e) => setModalBool1(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
                    />
                    <label htmlFor="wsRequireToken" className="text-xs text-muted-foreground cursor-pointer select-none">
                      强制进行密钥验证
                    </label>
                  </div>
                </>
              )}

              {/* Status Switch */}
              <div className="flex items-center gap-2 pt-2 border-t mt-4 border-border/40">
                <input
                  type="checkbox"
                  id="modalEnabled"
                  checked={modalEnabled}
                  onChange={(e) => setModalEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
                />
                <label htmlFor="modalEnabled" className="text-xs text-muted-foreground cursor-pointer select-none font-semibold">
                  启用此通信通道 (Enable Channel)
                </label>
              </div>

              {/* Footer Buttons */}
              <div className="flex items-center justify-end gap-3 border-t pt-4 mt-6 border-border/40">
                <button
                  type="button"
                  onClick={() => setActiveModalChannel(null)}
                  className="inline-flex items-center justify-center rounded-md border border-input bg-background hover:bg-accent px-4 py-2 text-sm font-medium transition cursor-pointer"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={modalSaving || (activeModalChannel.type === 'wechat' && showTransientScanner && transientQrStatus !== "success")}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 transition cursor-pointer"
                >
                  {modalSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {modalSaving ? "保存中..." : "保存设置"}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

    </div>
  );
}
