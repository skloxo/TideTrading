import { useEffect, useRef } from "react";
import i18n from "@/i18n";
import { echarts } from "@/lib/echarts";
import { getChartTheme } from "@/lib/chart-theme";

interface Props {
  labels: string[];
  matrix: number[][];
  names?: Record<string, string>;
  height?: number;
}

export function CorrelationMatrix({ labels, matrix, names = {}, height = 500 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || labels.length === 0 || matrix.length === 0) return;

    const t = getChartTheme();
    const chart = echarts.init(ref.current);

    // Build heatmap data: [xIdx, yIdx, value]
    const data: [number, number, number][] = [];
    for (let i = 0; i < labels.length; i++) {
      for (let j = 0; j < labels.length; j++) {
        const val = matrix[i]?.[j] ?? 0;
        data.push([j, i, parseFloat(val.toFixed(4))]);
      }
    }

    const minVal = -1;
    const maxVal = 1;

    const formatAxisLabel = (value: string) => {
      const name = names[value] || value;
      const parts = value.split(".");
      const code = parts[0];
      const suffix = parts[1] || "";
      if (name && name !== value) {
        const displayCode = suffix ? `${suffix.toUpperCase()}${code}` : code;
        return `${name}\n${displayCode}`;
      }
      return value;
    };

    chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        position: "top",
        backgroundColor: t.tooltipBg,
        borderColor: t.tooltipBorder,
        textStyle: { color: t.tooltipText, fontSize: 12 },
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, number] };
          const [x, y, v] = p.data;
          const nameX = names[labels[x]] || labels[x];
          const nameY = names[labels[y]] || labels[y];
          return `<b>${nameX}</b> (${labels[x]})<br/>vs<br/><b>${nameY}</b> (${labels[y]})<br/>r = <b>${v.toFixed(4)}</b>`;
        },
      },
      grid: { left: "4%", right: "10%", top: "8%", bottom: "16%", containLabel: true },
      xAxis: {
        type: "category",
        data: labels,
        axisLabel: {
          color: t.textColor,
          fontSize: 10,
          rotate: 0,
          interval: 0,
          lineHeight: 14,
          formatter: formatAxisLabel,
        },
        axisLine: { lineStyle: { color: t.axisColor } },
        splitArea: { show: false },
      },
      yAxis: {
        type: "category",
        data: labels,
        axisLabel: {
          color: t.textColor,
          fontSize: 10,
          interval: 0,
          lineHeight: 14,
          formatter: formatAxisLabel,
        },
        axisLine: { lineStyle: { color: t.axisColor } },
        splitArea: { show: false },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        precision: 2,
        calculable: true,
        orient: "vertical",
        right: 8,
        top: "center",
        textStyle: { color: t.textColor, fontSize: 11 },
        inRange: {
          color: ["#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#f7f7f7", "#fddbc7", "#f4a582", "#d6604d", "#b2182b"],
        },
      },
      series: [
        {
          name: "Correlation",
          type: "heatmap",
          data,
          label: {
            show: labels.length <= 8,
            fontSize: 10,
            color: t.textColor,
            formatter: (params: unknown) => {
              const p = params as { value: [number, number, number] };
              return p.value[2].toFixed(2);
            },
          },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.5)" },
          },
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current!);
    return () => { ro.disconnect(); chart.dispose(); };
  }, [labels, matrix]);

  if (labels.length === 0) {
    return <div className="text-muted-foreground text-sm p-4">{i18n.t("charts.noCorrelationData")}</div>;
  }
  return <div ref={ref} style={{ height }} />;
}