interface ConceptItem {
  name: string;
  leadStock: string;
  leadStockCode: string;
  heat: number; // 0-100
  sentiment: "bull" | "bear" | "neutral";
  change: number;
}

export function ConceptRotation() {
  const concepts: ConceptItem[] = [
    { name: "低空经济", leadStock: "万丰奥威", leadStockCode: "301550", heat: 98, sentiment: "bull", change: 5.62 },
    { name: "华为智驾", leadStock: "赛力斯", leadStockCode: "601127", heat: 92, sentiment: "bull", change: 3.18 },
    { name: "AI算力", leadStock: "工业富联", leadStockCode: "601138", heat: 88, sentiment: "bull", change: 4.10 },
    { name: "生物医药", leadStock: "恒瑞医药", leadStockCode: "600276", heat: 45, sentiment: "bear", change: -1.85 },
    { name: "中特估", leadStock: "工商银行", leadStockCode: "601398", heat: 60, sentiment: "neutral", change: 0.23 }
  ];

  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 h-full rounded shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1.5">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">📡 题材板块热度轮动 (CONCEPT ROTATION)</span>
        <span className="text-[9px] text-rose-600 dark:text-[#ff3366] font-bold">24H HEAT</span>
      </div>

      <div className="space-y-3 flex-1 overflow-auto">
        {concepts.map((concept, idx) => {
          const isUp = concept.change >= 0;
          return (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-900 dark:text-white font-bold">{concept.name}</span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400">
                  领涨: <span className="text-slate-700 dark:text-slate-300 font-sans">{concept.leadStock}</span> ({concept.leadStockCode})
                </span>
                <span className={`font-bold font-mono ${isUp ? "text-rose-600 dark:text-[#ff3366]" : "text-emerald-600 dark:text-[#00ff88]"}`}>
                  {isUp ? "+" : ""}{concept.change.toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-slate-100 dark:bg-[#1e1e2f] h-1 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${isUp ? "bg-rose-600 dark:bg-[#ff3366]" : "bg-emerald-600 dark:bg-[#00ff88]"}`}
                    style={{ width: `${concept.heat}%` }}
                  />
                </div>
                <span className="text-[9px] text-slate-400 dark:text-slate-500 font-mono w-6 text-right">热 {concept.heat}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
