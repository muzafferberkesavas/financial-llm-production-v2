<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import "@/lib/echarts";
import { C, MONO } from "@/lib/echarts";

const props = defineProps<{
  positions: { ticker: string; allocation_weight: number }[];
  cashPct: number;
}>();

const PALETTE = ["#5b9dff", "#34d399", "#f0b454", "#a78bfa", "#22d3ee", "#fb7185", "#4ade80"];

const invested = computed(() => props.positions.reduce((a, p) => a + p.allocation_weight, 0));

const option = computed(() => ({
  tooltip: {
    trigger: "item", backgroundColor: "#0d1117", borderColor: C.border,
    textStyle: { color: C.text, fontSize: 11 },
    formatter: (p: any) => `${p.name} · ${p.value.toFixed(1)}%`,
  },
  series: [{
    type: "pie", radius: ["62%", "88%"], center: ["50%", "50%"],
    avoidLabelOverlap: false, label: { show: false }, labelLine: { show: false },
    itemStyle: { borderColor: C.bg, borderWidth: 2 },
    data: [
      ...props.positions.map((p, i) => ({
        name: p.ticker, value: p.allocation_weight,
        itemStyle: { color: PALETTE[i % PALETTE.length] },
      })),
      { name: "Nakit", value: props.cashPct, itemStyle: { color: "#1f2835" } },
    ],
  }],
  graphic: [
    { type: "text", left: "center", top: "42%",
      style: { text: `${invested.value.toFixed(0)}%`, fill: C.text, fontSize: 26, fontFamily: MONO, fontWeight: 600 } },
    { type: "text", left: "center", top: "58%",
      style: { text: "yatırılan", fill: C.muted, fontSize: 11 } },
  ],
}));
</script>

<template>
  <VChart :option="option" autoresize style="height: 200px" />
</template>
