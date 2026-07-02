import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface YuziItem {
  name: string;
  stockName: string;
  stockCode: string;
  action: "buy" | "sell";
  amount: number; // 亿
  type: string; // 游资流派
}

interface YuziMovementProps {
  data?: YuziItem[];
}

export function YuziMovement({ data }: YuziMovementProps) {
  const fallbackList: YuziItem[] = [
    { name: "宁波解放路", stockName: "万丰奥威", stockCode: "301550", action: "buy", amount: 1.25, type: "一线游资" },
    { name: "呼家楼", stockName: "宁德时代", stockCode: "300750", action: "buy", amount: 2.80, type: "顶级席位" },
    { name: "小鳄鱼", stockName: "工业富联", stockCode: "601138", action: "buy", amount: 0.95, type: "新生代游资" },
    { name: "温州帮", stockName: "中兴通讯", stockCode: "000063", action: "sell", amount: -0.68, type: "庄股游资" },
    { name: "上海分公司", stockName: "比亚迪", stockCode: "002594", action: "buy", amount: 1.40, type: "量化大本营" }
  ];

  const yuziList = data && data.length > 0 ? data : fallbackList;

  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 h-full rounded shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1.5">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">🕵️ 游资盘中大单动向 (YUZI MOVEMENT)</span>
        <span className="text-[8px] px-1 py-0.2 bg-rose-50 dark:bg-[#ff3366]/20 text-rose-600 dark:text-[#ff3366] rounded font-mono border border-rose-100 dark:border-transparent">LIVE FEED</span>
      </div>

      <div className="space-y-2 flex-1 overflow-auto">
        {yuziList.map((item, idx) => {
          const isBuy = item.action === "buy";
          return (
            <div key={idx} className="flex justify-between items-center text-xs border-b border-slate-100 dark:border-[#181827] pb-1.5 last:border-b-0">
              <div className="flex flex-col">
                <span className="text-slate-900 dark:text-white font-bold">{item.name}</span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">{item.type}</span>
              </div>

              <div className="flex flex-col items-center">
                <span className="text-slate-700 dark:text-slate-300 font-sans">{item.stockName}</span>
                <span className="text-[9px] text-slate-500 dark:text-slate-400 font-mono">{item.stockCode}</span>
              </div>

              <div className="text-right flex items-center gap-1">
                <div className="flex flex-col items-end">
                  <span className={`font-bold font-mono ${isBuy ? "text-rose-600 dark:text-[#ff3366]" : "text-emerald-600 dark:text-[#00ff88]"}`}>
                    {isBuy ? "净买入" : "净卖出"} {Math.abs(item.amount).toFixed(2)}亿
                  </span>
                </div>
                {isBuy ? (
                  <ArrowUpRight className="h-3.5 w-3.5 text-rose-600 dark:text-[#ff3366]" />
                ) : (
                  <ArrowDownRight className="h-3.5 w-3.5 text-emerald-600 dark:text-[#00ff88]" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
