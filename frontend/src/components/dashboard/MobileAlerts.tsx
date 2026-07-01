import { AlertTriangle, Info, CheckCircle } from "lucide-react";

interface AlertItem {
  time: string;
  stockName: string;
  code: string;
  type: "breakout" | "volume" | "warning";
  message: string;
}

export function MobileAlerts() {
  const alerts: AlertItem[] = [
    { time: "14:28:12", stockName: "万丰奥威", code: "301550", type: "breakout", message: "突破 5 日高点压力位 16.10 元" },
    { time: "14:27:04", stockName: "宁德时代", code: "300750", type: "volume", message: "盘中出现机构大单主买成交 1.5 亿" },
    { time: "14:25:30", stockName: "大盘情绪", code: "INDEX", type: "warning", message: "情绪温度冲高回落至 82%，防范炸板风险" },
    { time: "14:22:15", stockName: "工业富联", code: "601138", type: "breakout", message: "封板率突破 90%，买单挂盘超 12 万手" }
  ];

  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 h-full rounded shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1.5">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">🚨 盘中高频移动监控预警 (MONITOR ALERTS)</span>
        <span className="h-1.5 w-1.5 rounded-full bg-rose-600 dark:bg-[#ff3366] animate-ping" />
      </div>

      <div className="space-y-2.5 flex-1 overflow-auto">
        {alerts.map((alert, idx) => {
          return (
            <div key={idx} className="flex gap-2 text-xs border-b border-slate-100 dark:border-[#181827] pb-2 last:border-0 last:pb-0">
              <div className="mt-0.5">
                {alert.type === "breakout" ? (
                  <CheckCircle className="h-3.5 w-3.5 text-rose-600 dark:text-[#ff3366]" />
                ) : alert.type === "volume" ? (
                  <Info className="h-3.5 w-3.5 text-[#00abc0] dark:text-[#00e5ff]" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-500" />
                )}
              </div>

              <div className="flex flex-col flex-1 min-w-0">
                <div className="flex justify-between text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                  <span>{alert.stockName} ({alert.code})</span>
                  <span>{alert.time}</span>
                </div>
                <p className="text-slate-800 dark:text-slate-300 mt-0.5 truncate font-sans">{alert.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
