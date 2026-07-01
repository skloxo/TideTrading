interface KolItem {
  author: string;
  stockName: string;
  code: string;
  sentiment: "bull" | "bear" | "neutral";
  followers: string;
  content: string;
  timestamp: string;
}

export function KolOpinions() {
  const opinions: KolItem[] = [
    { 
      author: "量化复盘大师", 
      stockName: "万丰奥威", 
      code: "301550", 
      sentiment: "bull", 
      followers: "450k", 
      content: "低空航空进入2.0主升浪，今日万丰强势封死，底部筹码牢固，短期还有15-20%空间。", 
      timestamp: "14:15" 
    },
    { 
      author: "价值研报哥", 
      stockName: "宁德时代", 
      code: "300750", 
      sentiment: "bull", 
      followers: "120k", 
      content: "锂电池中报业绩超预期，出货量保持30%增长，上游碳酸锂下跌利好净利润，估值见底。", 
      timestamp: "13:58" 
    },
    { 
      author: "短线打板王", 
      stockName: "工商银行", 
      code: "601398", 
      sentiment: "bear", 
      followers: "280k", 
      content: "大金融板块护盘任务基本完成，资金有明显的从小盘向高弹性题材转移趋势，短期离场回避。", 
      timestamp: "13:42" 
    }
  ];

  return (
    <div className="border border-slate-200 dark:border-[#222233] bg-white dark:bg-[#10101a]/80 p-3 flex flex-col gap-2 h-full rounded shadow-sm dark:shadow-none">
      <div className="flex justify-between items-center border-b border-slate-200 dark:border-[#222233] pb-1.5">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">👥 热门大V盘中观点与情绪 (KOL SENTIMENT)</span>
        <span className="text-[9px] text-rose-600 dark:text-[#ff3366] font-bold">SENTIMENT: BULLISH</span>
      </div>

      <div className="space-y-3 flex-1 overflow-auto">
        {opinions.map((item, idx) => {
          const isBull = item.sentiment === "bull";
          const isBear = item.sentiment === "bear";
          return (
            <div key={idx} className="text-xs border-b border-slate-100 dark:border-[#181827] pb-2.5 last:border-0 last:pb-0">
              <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-900 dark:text-white font-bold">{item.author}</span>
                  <span className="text-[8px] text-slate-500 dark:text-slate-400">粉丝 {item.followers}</span>
                </div>
                <span className={`text-[9px] px-1.5 py-0.2 font-bold font-mono rounded ${
                  isBull ? "bg-rose-50 dark:bg-[#ff3366]/20 text-rose-600 dark:text-[#ff3366]" :
                  isBear ? "bg-emerald-50 dark:bg-[#00ff88]/20 text-emerald-600 dark:text-[#00ff88]" :
                  "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                }`}>
                  {isBull ? "看多" : isBear ? "看空" : "中性"}
                </span>
              </div>
              <p className="text-[10px] text-slate-600 dark:text-slate-400 leading-normal font-sans">{item.content}</p>
              
              <div className="flex justify-between items-center text-[8px] text-slate-500 dark:text-slate-600 mt-1.5 font-mono">
                <span>相关: <span className="text-slate-600 dark:text-slate-500 font-sans">{item.stockName}</span> ({item.code})</span>
                <span>{item.timestamp}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
