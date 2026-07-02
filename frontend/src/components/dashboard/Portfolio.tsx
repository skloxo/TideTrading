interface PositionItem {
  code: string;
  name: string;
  shares: number;
  cost: number;
  price: number;
  profit: number; // 累计盈亏（万）
  profitRate: number;
}

interface PortfolioProps {
  data?: PositionItem[];
  netAsset?: number;
}

export function Portfolio({ data, netAsset }: PortfolioProps) {
  const fallbackPositions: PositionItem[] = [
    { code: "300750", name: "宁德时代", shares: 8000, cost: 185.20, price: 218.40, profit: 26.56, profitRate: 17.92 },
    { code: "301550", name: "万丰奥威", shares: 45000, cost: 12.40, price: 16.28, profit: 17.46, profitRate: 31.29 },
    { code: "601398", name: "工商银行", shares: 150000, cost: 5.69, price: 5.62, profit: -1.05, profitRate: -1.23 }
  ];

  const positions = data && data.length > 0 ? data : fallbackPositions;
  const displayNetAsset = netAsset !== undefined ? `${netAsset.toFixed(2)}M` : "4.82M";

  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 h-full rounded shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1.5">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">💼 我的证券持仓明细 (PORTFOLIO)</span>
        <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">净资产: {displayNetAsset}</span>
      </div>

      <div className="space-y-2 flex-1 overflow-auto">
        <div className="grid grid-cols-12 text-[9px] font-bold text-slate-400 dark:text-slate-500 px-1 py-0.5 border-b border-slate-100 dark:border-[#1c1c2b]">
          <span className="col-span-3">名称</span>
          <span className="col-span-3 text-right">持仓/成本</span>
          <span className="col-span-3 text-right">现价</span>
          <span className="col-span-3 text-right">浮动盈亏</span>
        </div>

        {positions.map((pos) => {
          const isUp = pos.profit >= 0;
          return (
            <div key={pos.code} className="grid grid-cols-12 text-xs items-center px-1 py-1.5 hover:bg-slate-50 dark:hover:bg-[#1a1a2e] rounded transition-colors">
              <div className="col-span-3 flex flex-col">
                <span className="text-slate-900 dark:text-white font-sans font-bold truncate">{pos.name}</span>
                <span className="text-[9px] text-slate-500 dark:text-slate-400 font-mono">{pos.code}</span>
              </div>

              <div className="col-span-3 flex flex-col items-end">
                <span className="text-slate-800 dark:text-slate-200 font-mono tabular-nums">{pos.shares}</span>
                <span className="text-[9px] text-slate-500 dark:text-slate-400 font-mono tabular-nums">{pos.cost.toFixed(2)}</span>
              </div>

              <span className="col-span-3 text-right text-slate-700 dark:text-slate-300 font-bold font-mono tabular-nums">
                {pos.price.toFixed(2)}
              </span>

              <div className="col-span-3 flex flex-col items-end">
                <span className={`font-bold font-mono tabular-nums ${isUp ? "text-rose-600 dark:text-[#ff3366]" : "text-emerald-600 dark:text-[#00ff88]"}`}>
                  {isUp ? "+" : ""}{pos.profit.toFixed(2)}万
                </span>
                <span className={`text-[9px] font-bold font-mono tabular-nums ${isUp ? "text-rose-600 dark:text-[#ff3366]" : "text-emerald-600 dark:text-[#00ff88]"}`}>
                  {isUp ? "+" : ""}{pos.profitRate.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
