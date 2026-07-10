import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Loader2, Copy, Check, Plus } from "lucide-react";
import { setApiAuthKey } from "@/lib/apiAuth";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ICPFooter } from "@/components/layout/ICPFooter";

export function TenantRegister() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";
  const navigate = useNavigate();

  // Registration states
  const [nickname, setNickname] = useState("");
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [registeredResult, setRegisteredResult] = useState<{ key: string; name: string } | null>(null);
  const [isCopied, setIsCopied] = useState(false);

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
            {isZh
              ? "注册新身份并生成您的独占访问密钥"
              : "Register a new tenant identity and generate access key"}
          </p>
        </div>

        {/* Content Box */}
        <div className="rounded-xl border bg-card shadow-lg overflow-hidden p-6">
          {registeredResult ? (
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

      <ICPFooter className="py-6" />
    </div>
  );
}
