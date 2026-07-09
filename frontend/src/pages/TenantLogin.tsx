import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Loader2, Copy, Check, Plus } from "lucide-react";
import { setApiAuthKey } from "@/lib/apiAuth";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function TenantLogin() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";
  const navigate = useNavigate();

  // Navigation tabs: "login" | "register"
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");

  // Login states
  const [key, setKey] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  // Registration states
  const [nickname, setNickname] = useState("");
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [registeredResult, setRegisteredResult] = useState<{ key: string; name: string } | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Login submit handler
  const handleLoginSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) return;
    setLoginLoading(true);
    setLoginError("");
    try {
      // Validate key by calling the profile endpoint directly
      const res = await fetch("/settings/profile", {
        headers: { Authorization: `Bearer ${trimmed}` },
      });
      if (!res.ok) {
        setLoginError(
          isZh
            ? "租户密钥无效或已失效，请重新输入"
            : "Invalid or expired tenant key. Please try again."
        );
        return;
      }
      const data = await res.json();
      if (!data.is_tenant) {
        setLoginError(
          isZh
            ? "该密钥不是有效的租户密钥，请确认后重试"
            : "This key is not a valid tenant key."
        );
        return;
      }
      setApiAuthKey(trimmed);
      navigate("/", { replace: true });
    } catch {
      setLoginError(isZh ? "网络错误，请稍后重试" : "Network error. Please try again.");
    } finally {
      setLoginLoading(false);
    }
  };

  // Register submit handler
  const handleRegisterSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!nickname.trim()) return;
    setRegistering(true);
    setRegisterError("");
    try {
      const res = await api.registerTenant({ name: nickname.trim() });
      setRegisteredResult(res);
      toast.success(
        isZh
          ? "租户注册成功！请复制并妥善保存您的访问密钥。"
          : "Tenant registered successfully! Please copy and save your access key."
      );
    } catch (err: any) {
      setRegisterError(err?.message || (isZh ? "注册失败，请更换名称后重试" : "Registration failed."));
    } finally {
      setRegistering(false);
    }
  };

  // Copy registration key
  const handleCopyKey = () => {
    if (!registeredResult) return;
    navigator.clipboard.writeText(registeredResult.key);
    setIsCopied(true);
    toast.success(isZh ? "密钥已复制到剪贴板" : "Key copied to clipboard");
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/40 p-4">
      <div className="w-full max-w-md">
        {/* Logo + Title */}
        <div className="text-center mb-8 space-y-2">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20 mx-auto mb-4">
            <img src="/logo.png" alt="Logo" className="h-10 w-10 object-contain" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            {isZh ? "潮汐投研" : "TideTrading"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isZh
              ? "请输入密钥访问，或注册成为新租户"
              : "Enter access key or register as a new tenant"}
          </p>
        </div>

        {/* Tab Selection */}
        <div className="rounded-xl border bg-card shadow-lg overflow-hidden">
          <div className="flex border-b">
            <button
              onClick={() => {
                setActiveTab("login");
                setRegisteredResult(null);
              }}
              className={`flex-1 py-3 text-center text-sm font-semibold transition ${
                activeTab === "login"
                  ? "bg-muted/30 text-foreground border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isZh ? "使用密钥登录" : "Login with Key"}
            </button>
            <button
              onClick={() => {
                setActiveTab("register");
                setRegisteredResult(null);
              }}
              className={`flex-1 py-3 text-center text-sm font-semibold transition ${
                activeTab === "register"
                  ? "bg-muted/30 text-foreground border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isZh ? "注册新身份 (租户)" : "Register Tenant"}
            </button>
          </div>

          <div className="p-6">
            {activeTab === "login" ? (
              /* LOGIN TAB */
              <form onSubmit={handleLoginSubmit} className="space-y-5">
                <label className="block space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                    {isZh ? "租户 API 密钥" : "Tenant API Key"}
                  </span>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
                    <input
                      id="tenant-key-input"
                      type="password"
                      value={key}
                      onChange={(e) => setKey(e.target.value)}
                      placeholder={isZh ? "请输入您的租户密钥..." : "tide_t_..."}
                      className="w-full rounded-md border bg-background pl-9 pr-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                      autoComplete="current-password"
                      autoFocus
                      required
                    />
                  </div>
                  <span className="text-[11px] text-muted-foreground block">
                    {isZh
                      ? "密钥由系统管理员提供，格式：tide_t_..."
                      : "Key provided by your system admin, format: tide_t_..."}
                  </span>
                </label>

                {loginError && (
                  <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-xs text-destructive">
                    {loginError}
                  </div>
                )}

                <button
                  id="tenant-login-submit"
                  type="submit"
                  disabled={loginLoading || !key.trim()}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-60 cursor-pointer shadow-sm"
                >
                  {loginLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <KeyRound className="h-4 w-4" />
                  )}
                  {loginLoading
                    ? isZh ? "验证中..." : "Verifying..."
                    : isZh ? "登录" : "Log In"}
                </button>
              </form>
            ) : registeredResult ? (
              /* REGISTRATION SUCCESS VIEW */
              <div className="space-y-5">
                <div className="rounded-md bg-amber-500/10 p-3.5 border border-amber-500/20 text-xs text-amber-500 leading-relaxed">
                  <strong>⚠️ {isZh ? "请务必妥善保管以下密钥：" : "Keep your key safe:"}</strong>
                  <p className="mt-1">
                    {isZh
                      ? "出于安全考虑，该密钥仅在此处展示一次，关闭窗口后将无法重新找回。若丢失您将无法访问之前的历史数据与会话记录。"
                      : "For security reasons, this key will only be shown once. If lost, you cannot recover your past workspaces or runs."}
                  </p>
                </div>

                <div className="rounded-md border bg-muted/50 p-3 flex items-center justify-between gap-3">
                  <span className="font-mono text-sm break-all select-all font-semibold block leading-tight">
                    {registeredResult.key}
                  </span>
                  <button
                    onClick={handleCopyKey}
                    className="p-2 rounded bg-background border hover:bg-accent transition shrink-0 cursor-pointer"
                    title={isZh ? "复制到剪贴板" : "Copy to clipboard"}
                  >
                    {isCopied ? (
                      <Check className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>

                <button
                  onClick={() => {
                    setApiAuthKey(registeredResult.key);
                    navigate("/", { replace: true });
                  }}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90 cursor-pointer shadow-sm"
                >
                  <KeyRound className="h-4 w-4" />
                  {isZh ? "保存并直接登录" : "Save & Login"}
                </button>
              </div>
            ) : (
              /* REGISTRATION FORM */
              <form onSubmit={handleRegisterSubmit} className="space-y-5">
                <label className="block space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                    {isZh ? "自定义租户昵称" : "Custom Tenant Nickname"}
                  </span>
                  <input
                    id="tenant-name-input"
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    placeholder={isZh ? "例如：策略开发一组" : "e.g., Development Team A"}
                    className="w-full rounded-md border bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                    autoFocus
                    required
                  />
                  <p className="text-[10px] text-muted-foreground leading-relaxed block">
                    {isZh
                      ? "* 2-20 个字符，包含中英文、数字、空格、下划线及中划线，且名称不能重复。"
                      : "* 2-20 chars. alphanumeric, space, hyphens or underscores. Must be unique."}
                  </p>
                </label>

                {registerError && (
                  <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-xs text-destructive">
                    {registerError}
                  </div>
                )}

                <button
                  id="tenant-register-submit"
                  type="submit"
                  disabled={registering || !nickname.trim()}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-60 cursor-pointer shadow-sm"
                >
                  {registering ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  {registering
                    ? isZh ? "生成中..." : "Generating..."
                    : isZh ? "生成身份密钥" : "Generate Access Key"}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
