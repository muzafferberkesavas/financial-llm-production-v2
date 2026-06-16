<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import "@/lib/echarts";
import { C, MONO } from "@/lib/echarts";

const props = withDefaults(defineProps<{
  value: number;          // 0..1
  color?: string;
  size?: number;
  label?: string;
}>(), { color: C.accent, size: 96, label: "" });

const pct = computed(() => Math.round(props.value * 100));

const option = computed(() => ({
  series: [{
    type: "gauge", startAngle: 220, endAngle: -40, radius: "100%",
    center: ["50%", "55%"], min: 0, max: 1,
    progress: { show: true, width: 7, roundCap: true, itemStyle: { color: props.color } },
    axisLine: { lineStyle: { width: 7, color: [[1, "#1f2835"]] } },
    pointer: { show: false }, axisTick: { show: false },
    splitLine: { show: false }, axisLabel: { show: false },
    anchor: { show: false },
    detail: {
      valueAnimation: true, offsetCenter: [0, "2%"],
      formatter: () => `${pct.value}`, color: C.text,
      fontSize: props.size * 0.26, fontFamily: MONO, fontWeight: 600,
    },
    data: [{ value: props.value }],
  }],
}));
</script>

<template>
  <div class="relative grid place-items-center" :style="{ width: size + 'px', height: size + 'px' }">
    <VChart :option="option" autoresize />
    <span v-if="label" class="pointer-events-none absolute bottom-1 text-[10px] text-muted">{{ label }}</span>
  </div>
</template>
