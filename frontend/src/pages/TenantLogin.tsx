import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Loader2 } from "lucide-react";
import { setApiAuthKey } from "@/lib/apiAuth";
import { useTranslation } from "react-i18next";
import { ICPFooter } from "@/components/layout/ICPFooter";

export function TenantLogin() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";
  const navigate = useNavigate();

  // Login states
  const [key, setKey] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

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

  return (
    <div className="min-h-screen flex flex-col items-center justify-between bg-gradient-to-br from-background to-muted/40 p-4">
      <div />

      <div className="w-full max-w-md my-auto">
        {/* Logo + Title */}
        <div className="text-center mb-8 space-y-2">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20 mx-auto mb-4">
            <img src="/logo.png" alt="Logo" className="h-10 w-10 object-contain" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            {isZh ? "潮汐投研" : "TideTrading"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isZh ? "请输入密钥登录系统" : "Enter access key to log in"}
          </p>
        </div>

        {/* Content Box */}
        <div className="rounded-xl border bg-card shadow-lg overflow-hidden p-6">
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
        </div>
      </div>

      <ICPFooter />
    </div>
  );
}
