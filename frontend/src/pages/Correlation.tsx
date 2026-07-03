import i18n from '@/i18n';
import { useState } from "react";
import { BarChart3, HelpCircle, X, BookOpen } from "lucide-react";
import { CorrelationMatrix } from "@/components/charts/CorrelationMatrix";
import ReactMarkdown from "react-markdown";

const WINDOWS = [30, 60, 90, 180, 365] as const;

const GUIDE_MD = `
### 📊 资产相关性矩阵使用指南 / Asset Correlation Matrix Guide

相关性矩阵用于衡量不同资产在特定窗口内的**日收益率两两联动紧密程度**，是现代资产配置与多元风险分散的核心量化工具。

#### 1. 核心概念与相关系数（$\\rho$）
相关系数的值域严格限定在 **[-1, 1]** 之间：
*   **1.0（完全正相关）**：资产走势完全同步（自身与自身永远为 1.0）。
*   **0.0（互不相关）**：资产走势完全独立，随机运动。
*   **-1.0（完全负相关）**：资产走势方向完全相反，是完美的避险对冲标的。
*   **强弱判定**：
    *   **0.7 ~ 1.0**：强正相关（如同属白酒板块的茅台与五粮液，通常呈强烈的板块共振）。
    *   **0.3 ~ 0.7**：中等正相关（如大盘蓝筹股，受指数系统性波动影响，但行业驱动不同）。
    *   **0.0 ~ 0.3**：弱相关（如黄金与科技股，拥有极佳的分散能力）。
    *   **小于 0.0**：负相关（能有效降低组合整体的夏普比率回撤风险）。

#### 2. 参数设置与数学算法
*   **资产代码 (Asset Codes)**：逗号分隔的标的代码（如 \`000001.SZ,600519.SH,000858.SZ,601318.SH\`）。
*   **回溯窗口 (Window)**：计算天数。30天用于观察短线题材共振，180天/365天用于分析长线周期联动。
*   **算法选择 (Method)**：
    *   **Pearson (皮尔逊)**：衡量线性相关，适合收益率呈平稳正态分布的传统股债资产。
    *   **Spearman (斯皮尔曼秩)**：基于变动的单调排名计算，对极端单日暴涨暴跌等异常值有极强的抗噪和防失真能力。

#### 3. 实战配置策略建议
*   **多元化风险分散**：组合内个股两两相关系数若普遍大于 **0.6**，表明您持有的是本质相同的贝塔风险。应配置相关性低于 **0.4** 的其他题材/红利/大宗资产以熨平净值波动。
*   **统计套利与配对交易**：当两只历史相关性极高（如 $\\rho > 0.85$）的同行股票因短期情绪错杀导致走势出现暂时背离时，交易员通常会“做空强势、做多弱势”等待其相关性收敛。
`;

export function Correlation() {
  const [codes, setCodes] = useState("000001,600519,000858,601318");
  const [days, setDays] = useState<number>(90);
  const [method, setMethod] = useState<"pearson" | "spearman">("pearson");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  const [labels, setLabels] = useState<string[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [matrix, setMatrix] = useState<number[][]>([]);

  const compute = async () => {
    setError(null);
    setLoading(true);
    try {
      const result = await request<{ labels: string[]; names: Record<string, string>; matrix: number[][] }>(
        `/correlation?codes=${encodeURIComponent(codes)}&days=${days}&method=${method}`
      );
      setLabels(result.labels);
      setNames(result.names ?? {});
      setMatrix(result.matrix);
    } catch (e) {
      setError(e instanceof Error ? e.message : i18n.t("correlation.failedToCompute"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto relative">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{i18n.t("correlation.title")}</h1>
        </div>
        <button
          onClick={() => setShowGuide(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary/20 hover:border-primary/40 bg-primary/5 hover:bg-primary/10 text-primary text-xs font-semibold transition-all hover:scale-102 active:scale-98"
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span>{i18n.language?.startsWith("zh") ? "量化配置指南" : "View Quant Guide"}</span>
        </button>
      </div>

      {/* Brief explanation card (100 words Chinese/English) */}
      <div className="flex items-start gap-3 p-4 rounded-xl border border-primary/10 bg-primary/2 dark:bg-primary/5 text-xs text-muted-foreground leading-relaxed shadow-sm">
        <HelpCircle className="h-4.5 w-4.5 text-primary shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-foreground">
            {i18n.language?.startsWith("zh") ? "如何理解和使用相关性矩阵？" : "Understanding Correlation Matrix"}
          </p>
          <p>
            {i18n.language?.startsWith("zh")
              ? "本功能计算多资产在特定窗口内的日收益率相关性（-1至1）。网格矩阵能帮助您识别强正相关的标的以防持仓过度集中，或发现弱/负相关资产以实现投资组合的多元风险分散与避险配置。"
              : "Computes daily return correlations (-1 to 1) for assets. Use it to avoid over-concentration in highly correlated assets, or build diversified portfolios using weakly or negatively correlated assets to mitigate risk."}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col gap-4 border rounded-lg p-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium">{i18n.t("correlation.assetCodes")}</label>
          <input
            type="text"
            value={codes}
            onChange={(e) => setCodes(e.target.value)}
            placeholder="000001,600519,000858"
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
          />
          <p className="text-xs text-muted-foreground">
            {i18n.language?.startsWith("zh") ? "逗号分隔的标的代码，如 000001,600519,000858" : "Comma-separated asset codes, e.g. 000001,600519,000858"}
          </p>
        </div>

        <div className="flex flex-wrap gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">{i18n.t("correlation.windowDays")}</label>
            <div className="flex gap-1.5">
              {WINDOWS.map((w) => (
                <button
                  key={w}
                  onClick={() => setDays(w)}
                  className={`px-3 py-1.5 rounded text-sm border transition-colors ${
                    days === w
                      ? "bg-primary text-primary-foreground"
                      : "border-muted-foreground/30 hover:border-primary"
                  }`}
                >
                  {w}d
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">{i18n.t("correlation.method")}</label>
            <div className="flex gap-1.5">
              {(["pearson", "spearman"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMethod(m)}
                  className={`px-3 py-1.5 rounded text-sm border transition-colors capitalize ${
                    method === m
                      ? "bg-primary text-primary-foreground"
                      : "border-muted-foreground/30 hover:border-primary"
                  }`}
                >
                  {i18n.t(`correlation.method_${m}`)}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={compute}
          disabled={loading}
          className="self-start px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {loading ? i18n.t("correlation.loading") : i18n.t("correlation.compute")}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="text-sm text-danger border border-danger/30 rounded p-3 bg-danger/5">
          {error}
        </div>
      )}

      {/* Chart */}
      {labels.length > 0 && <CorrelationMatrix labels={labels} names={names} matrix={matrix} height={520} />}

      {/* Full Guide Modal Overlay */}
      {showGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div 
            className="relative flex flex-col w-full max-w-3xl max-h-[85vh] bg-card border border-border rounded-2xl shadow-2xl p-6 overflow-hidden animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-border/60 shrink-0">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                {i18n.language?.startsWith("zh") ? "相关性矩阵量化分析指南" : "Quant Guide: Correlation Matrix"}
              </h2>
              <button
                onClick={() => setShowGuide(false)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto py-4 pr-1 scrollbar-thin">
              <div className="prose prose-xs md:prose-sm dark:prose-invert max-w-none text-muted-foreground leading-relaxed space-y-4">
                <ReactMarkdown>{GUIDE_MD}</ReactMarkdown>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex justify-end pt-3 border-t border-border/60 shrink-0">
              <button
                onClick={() => setShowGuide(false)}
                className="px-4 py-2 rounded-md bg-muted hover:bg-muted/80 text-sm font-semibold transition-colors"
              >
                {i18n.language?.startsWith("zh") ? "关闭" : "Close"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Minimal request helper (avoids importing the full api client which may have path issues)
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const BASE = "";
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}