<script setup lang="ts">
import { computed } from "vue";
import type { SignalType } from "@/types";
import { ACTION_META } from "@/types";

const props = withDefaults(defineProps<{ action: SignalType; size?: "sm" | "md" }>(), { size: "md" });
const meta = computed(() => ACTION_META[props.action]);
const tone = computed(() => ({
  bull: "bg-bull/12 text-bull ring-bull/25",
  bear: "bg-bear/12 text-bear ring-bear/25",
  watch: "bg-watch/12 text-watch ring-watch/25",
}[meta.value.tone]));
const dot = computed(() => ({ bull: "bg-bull", bear: "bg-bear", watch: "bg-watch" }[meta.value.tone]));
</script>

<template>
  <span class="inline-flex items-center gap-1.5 rounded-lg font-semibold ring-1 ring-inset"
        :class="[tone, size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs']">
    <span class="h-1.5 w-1.5 rounded-full" :class="dot" />
    {{ meta.label }}
  </span>
</template>
