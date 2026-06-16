<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import "@/lib/echarts";
import { C, MONO } from "@/lib/echarts";

// Macro→sector appetite: horizontal bars, colored bull(green)→neutral→bear(red).
const props = defineProps<{ sectors: { sector: string; appetite: number; rationale?: string }[] }>();

function color(a: number): string {
  if (a >= 0.5) {
    const t = (a - 0.5) / 0.5;             // 0.5→1 : muted → green
    return mix("#5a657a", C.bull, t);
  }
  const t = (0.5 - a) / 0.5;               // 0.5→0 : muted → red
  return mix("#5a657a", C.bear, t);
}
function mix(a: string, b: string, t: number): string {
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [r1, g1, b1] = p(a), [r2, g2, b2] = p(b);
  const c = (x: number, y: number) => Math.round(x + (y - x) * Math.min(1, Math.max(0, t)));
  return `rgb(${c(r1, r2)},${c(g1, g2)},${c(b1, b2)})`;
}

const sorted = computed(() => [...props.sectors].sort((a, b) => b.appetite - a.appetite));

const option = computed(() => ({
  grid: { left: 130, right: 28, top: 6, bottom: 6 },
  tooltip: {
    trigger: "axis", axisPointer: { type: "none" },
    backgroundColor: "#0d1117", borderColor: C.border, textStyle: { color: C.text, fontSize: 11 },
    formatter: (p: any) => {
      const d = sorted.value[p[0].dataIndex];
      return `<b>${d.sector}</b> · iştah ${d.appetite.toFixed(2)}<br/><span style="color:${C.muted};max-width:240px;display:inline-block;white-space:normal">${d.rationale ?? ""}</span>`;
    },
  },
  xAxis: { type: "value", min: 0, max: 1, show: false },
  yAxis: {
    type: "category", inverse: true,
    data: sorted.value.map((s) => s.sector),
    axisLine: { show: false }, axisTick: { show: false },
    axisLabel: { color: C.muted, fontSize: 11, width: 120, overflow: "truncate" },
  },
  series: [{
    type: "bar", barWidth: 11,
    data: sorted.value.map((s) => ({
      value: s.appetite,
      itemStyle: { color: color(s.appetite), borderRadius: 3 },
    })),
    label: {
      show: true, position: "right", color: C.muted, fontSize: 10, fontFamily: MONO,
      formatter: (p: any) => sorted.value[p.dataIndex].appetite.toFixed(2),
    },
    markLine: {
      silent: true, symbol: "none",
      lineStyle: { color: "#2b3645", type: "dashed", width: 1 },
      data: [{ xAxis: 0.5 }], label: { show: false },
    },
  }],
}));
</script>

<template>
  <VChart :option="option" autoresize :style="{ height: Math.max(120, sectors.length * 20) + 'px' }" />
</template>
