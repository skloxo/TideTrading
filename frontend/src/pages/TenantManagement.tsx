import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { api, type TenantKey, type UserProfile } from "@/lib/api";
import { setAdminToken } from "@/lib/apiAuth";
import { Power, Trash2, Loader2, Copy, Check, Save, Plus, ShieldAlert, Lock } from "lucide-react";

export function TenantManagement() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  // Tenant API Keys states
  const [tenantKeys, setTenantKeys] = useState<TenantKey[]>([]);
  const [tenantKeysLoading, setTenantKeysLoading] = useState(false);
  const [isTenantModalOpen, setIsTenantModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [tenantSaving, setTenantSaving] = useState(false);
  const [generatedKey, setGeneratedKey] = useState("");
  const [isCopied, setIsCopied] = useState(false);

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

  const fetchTenantKeys = async () => {
    try {
      setTenantKeysLoading(true);
      const keys = await api.getTenantKeys();
      setTenantKeys(keys);
    } catch (err) {
      console.error("Failed to load tenant keys:", err);
    } finally {
      setTenantKeysLoading(false);
    }
  };

  useEffect(() => {
    if (profile?.is_admin) {
      fetchTenantKeys();
    }
  }, [profile]);

  const handleCreateTenantKey = async (e: FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setTenantSaving(true);
    try {
      const result = await api.createTenantKey({ name: newKeyName.trim() });
      setGeneratedKey(result.key);
      setTenantKeys([...tenantKeys, result]);
      setNewKeyName("");
      toast.success("密钥生成成功");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "生成密钥失败");
    } finally {
      setTenantSaving(false);
    }
  };

  const handleToggleTenantKey = async (tid: string, currentActive: boolean) => {
    try {
      const updated = await api.updateTenantKey(tid, { is_active: !currentActive });
      setTenantKeys(tenantKeys.map(k => k.tenant_id === tid ? updated : k));
      toast.success("密钥状态已更新");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "修改密钥状态失败");
    }
  };

  const handleDeleteTenantKey = async (tid: string) => {
    if (!window.confirm("确认删除此密钥？删除后该租户的 API 访问权限与隔离工作区将被立即彻底清除，无法撤销！")) {
      return;
    }
    try {
      await api.deleteTenantKey(tid);
      setTenantKeys(tenantKeys.filter(k => k.tenant_id !== tid));
      toast.success("密钥已成功删除");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除密钥失败");
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


  if (profileLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center text-muted-foreground animate-pulse">
        {isZh ? "正在验证访问权限..." : "Verifying access permissions..."}
      </div>
    );
  }

  if (!profile?.is_admin) {
    const fieldClass = "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";
    return (
      <div className="mx-auto max-w-7xl space-y-4 p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              {isZh ? "租户管理" : "Tenant Management"}
            </h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              {isZh ? "管理租户 API 接入密钥及隔离工作区沙箱。" : "Manage tenant API access credentials and sandbox workspaces."}
            </p>
          </div>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm space-y-4 max-w-xl">
          <div className="flex items-center gap-2 border-b pb-3">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <h2 className="text-base font-semibold">{isZh ? "管理员提权 (租户管理)" : "Admin Elevation (Tenant Management)"}</h2>
          </div>
          <p className="text-xs text-muted-foreground">
            {isZh 
              ? "此页面属于系统租户管理功能，仅限系统管理员访问。请输入管理员账号密码进行提权。" 
              : "This page is for tenant keys management and is restricted to admin. Please enter admin credentials to elevate."}
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



  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      {/* Title */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b pb-4 border-border/60">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            {isZh ? "租户与隔离工作区管理" : "Tenant & Workspace Management"}
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {isZh
              ? "生成新密钥时系统会自动创建其对应的物理隔离沙箱工作空间。"
              : "Workspaces are physically isolated under each tenant ID automatically."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setGeneratedKey("");
            setNewKeyName("");
            setIsTenantModalOpen(true);
          }}
          className="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 px-3.5 py-2 text-xs font-semibold transition cursor-pointer shadow-sm"
        >
          <Plus className="h-4 w-4" />
          {isZh ? "生成新租户密钥" : "Generate Tenant Key"}
        </button>
      </div>

      <div className="rounded-lg border bg-card p-4 shadow-sm">
        <div className="w-full overflow-x-auto">
          <table className="w-full min-w-[700px] border-collapse text-left text-xs text-muted-foreground">
            <thead>
              <tr className="border-b border-border text-[10px] font-semibold uppercase tracking-wider text-muted-foreground bg-muted/30">
                <th className="px-4 py-3">{isZh ? "租户备注名称" : "Tenant Nickname"}</th>
                <th className="px-4 py-3">Tenant ID</th>
                <th className="px-4 py-3">{isZh ? "系统密钥" : "API Key"}</th>
                <th className="px-4 py-3">{isZh ? "状态" : "Status"}</th>
                <th className="px-4 py-3 text-right">{isZh ? "操作" : "Actions"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tenantKeysLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center">
                    <div className="flex items-center justify-center gap-2 text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      {isZh ? "正在加载租户密钥列表..." : "Loading tenant keys..."}
                    </div>
                  </td>
                </tr>
              ) : tenantKeys.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    {isZh
                      ? "暂无已注册租户。点击右上角“生成新租户密钥”开始接入。"
                      : "No active tenants registered. Generate key above to start."}
                  </td>
                </tr>
              ) : (
                tenantKeys.map((key) => (
                  <tr key={key.tenant_id} className="hover:bg-muted/10 transition-colors">
                    <td className="px-4 py-3.5 font-medium text-foreground">{key.name}</td>
                    <td className="px-4 py-3.5 font-mono text-[10px]">{key.tenant_id}</td>
                    <td className="px-4 py-3.5">
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(key.key);
                          toast.success(isZh ? "密钥已成功复制到剪贴板" : "API key copied to clipboard");
                        }}
                        className="inline-flex items-center gap-1 rounded bg-muted/60 hover:bg-muted text-foreground px-2 py-1 text-[10px] font-medium transition cursor-pointer"
                      >
                        <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                        {isZh ? "复制密钥" : "Copy Key"}
                      </button>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${
                        key.is_active !== false
                          ? "bg-green-500/10 text-green-500 border-green-500/20"
                          : "bg-red-500/10 text-red-500 border-red-500/20"
                      }`}>
                        {key.is_active !== false ? (isZh ? "启用" : "Active") : (isZh ? "禁用" : "Disabled")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleToggleTenantKey(key.tenant_id, key.is_active !== false)}
                          className={`rounded p-1 transition ${
                            key.is_active !== false
                              ? "text-yellow-500 hover:bg-yellow-500/10"
                              : "text-green-500 hover:bg-green-500/10"
                          }`}
                          title={key.is_active !== false ? (isZh ? "禁用该密钥" : "Disable") : (isZh ? "启用该密钥" : "Enable")}
                        >
                          <Power className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteTenantKey(key.tenant_id)}
                          className="text-red-400 hover:text-red-500 hover:bg-red-500/10 rounded p-1 transition"
                          title={isZh ? "删除租户" : "Delete"}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tenant Key Generation Modal */}
      {isTenantModalOpen && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-md border bg-card p-4 shadow-xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              {generatedKey ? "密钥生成成功" : "生成新租户密钥"}
            </h3>
            
            {generatedKey ? (
              <div className="space-y-4">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  新租户的 API 密钥已生成。该密钥<strong>仅在此展示一次</strong>，请立即复制并妥善保存您的密钥：
                </p>
                <div className="flex gap-2 items-center rounded-md border bg-muted/40 p-3 font-mono text-sm break-all select-all text-emerald-500">
                  <span className="flex-1">{generatedKey}</span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(generatedKey);
                      setIsCopied(true);
                      setTimeout(() => setIsCopied(false), 2000);
                    }}
                    className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition shrink-0"
                    title="复制到剪贴板"
                  >
                    {isCopied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
                <div className="flex items-center justify-end pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => {
                      setIsTenantModalOpen(false);
                      setGeneratedKey("");
                    }}
                    className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground hover:opacity-90 px-4 py-2 text-sm font-medium transition cursor-pointer"
                  >
                    已复制并关闭
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateTenantKey} className="space-y-4">
                <label className="grid gap-1.5">
                  <span className="text-sm font-medium">租户备注名称 (例如：量化团队A)</span>
                  <input
                    type="text"
                    required
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                    placeholder="请输入方便识别的租户名称"
                  />
                </label>

                <div className="flex items-center justify-end gap-3 border-t pt-4 mt-6">
                  <button
                    type="button"
                    onClick={() => setIsTenantModalOpen(false)}
                    className="inline-flex items-center justify-center rounded-md border border-input bg-background hover:bg-accent px-4 py-2 text-sm font-medium transition cursor-pointer"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={tenantSaving}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-70 transition cursor-pointer"
                  >
                    {tenantSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {tenantSaving ? "生成中..." : "生成密钥"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
