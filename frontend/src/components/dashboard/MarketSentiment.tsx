import { Activity } from "lucide-react";

export function MarketSentiment() {
  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 relative overflow-hidden h-full rounded shadow-sm dark:shadow-none">
      <div className="absolute top-0 right-0 w-24 h-24 bg-[#ff3366]/5 rounded-full blur-xl pointer-events-none" />
      <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-400">
        <span>A股大盘情绪温度 (SENTIMENT TEMP)</span>
        <Activity className="h-3.5 w-3.5 text-rose-600 dark:text-[#ff3366]" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-extrabold tracking-tighter text-rose-600 dark:text-[#ff3366]">82</span>
        <span className="text-xs font-bold font-sans text-rose-600 dark:text-[#ff3366]">GREED (极度贪婪)</span>
      </div>
      <div className="w-full bg-slate-100 dark:bg-[#1e1e2f] h-1.5 rounded-full overflow-hidden">
        <div className="bg-rose-600 dark:bg-[#ff3366] h-full" style={{ width: "82%" }} />
      </div>
      <div className="flex justify-between text-[8px] text-slate-400 dark:text-slate-600">
        <span>0 (恐慌)</span>
        <span>50 (中性)</span>
        <span>100 (狂热)</span>
      </div>

      <div className="mt-2 pt-2 border-t border-slate-100 dark:border-[#1a1a2e] grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <span className="text-slate-400 dark:text-slate-500 block">今日首板率</span>
          <span className="text-slate-900 dark:text-white font-bold font-mono">74.2%</span>
        </div>
        <div>
          <span className="text-slate-400 dark:text-slate-500 block">炸板率</span>
          <span className="text-emerald-600 dark:text-[#00ff88] font-bold font-mono">18.5%</span>
        </div>
      </div>
    </div>
  );
}
