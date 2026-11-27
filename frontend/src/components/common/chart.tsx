import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import { useTheme } from '@/lib/theme'

/** ECharts — ranglar dizayn tokenlaridan, ikkala mavzuda bir xil uslub. */
export function useChartTheme() {
  const { theme } = useTheme()
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement)
    const v = (n: string) => cs.getPropertyValue(n).trim()
    return {
      text: v('--muted-foreground'),
      fg: v('--foreground'),
      grid: v('--border'),
      bg: v('--popover'),
      series: [v('--chart-1'), v('--chart-2'), v('--chart-3'), v('--chart-4'), v('--chart-5')],
      success: v('--success'),
      danger: v('--danger'),
      warning: v('--warning'),
      neutral: v('--neutral'),
      theme,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme])
}

export function baseOption(t: ReturnType<typeof useChartTheme>) {
  return {
    color: t.series,
    textStyle: { fontFamily: 'Inter Variable, sans-serif', color: t.text },
    grid: { left: 44, right: 16, top: 28, bottom: 28, containLabel: false },
    tooltip: { trigger: 'axis', backgroundColor: t.bg, borderColor: t.grid, textStyle: { color: t.fg, fontSize: 12 } },
    legend: { top: 0, right: 0, textStyle: { color: t.text, fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
    xAxis: { axisLine: { lineStyle: { color: t.grid } }, axisLabel: { color: t.text, fontSize: 11 }, splitLine: { show: false } },
    yAxis: { axisLine: { show: false }, axisLabel: { color: t.text, fontSize: 11 }, splitLine: { lineStyle: { color: t.grid } } },
    animationDuration: 200,
  }
}

export function Chart({ option, height = 220, className, onEvents }: { option: object; height?: number | string; className?: string; onEvents?: Record<string, (e: unknown) => void> }) {
  return <ReactECharts option={option} style={{ height, width: '100%' }} className={className} notMerge lazyUpdate opts={{ renderer: 'canvas' }} onEvents={onEvents} />
}
