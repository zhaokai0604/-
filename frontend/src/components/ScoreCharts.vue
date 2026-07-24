<script setup>
import echarts from '../utils/echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
})

const barRef = ref(null)
const radarRef = ref(null)
let barChart
let radarChart

const palette = {
  primary: '#4f46e5',
  accent: '#6366f1',
  grid: '#e5e7eb',
  text: '#111827',
  muted: '#6b7280',
  fill: 'rgba(99, 102, 241, 0.15)',
}

function renderCharts() {
  const bar = props.data?.bar || []
  const radar = props.data?.radar || []
  if (!bar.length && !radar.length) {
    return
  }

  if (!barChart && barRef.value) {
    barChart = echarts.init(barRef.value)
  }
  if (!radarChart && radarRef.value) {
    radarChart = echarts.init(radarRef.value)
  }

  barChart?.setOption({
    animationDuration: 450,
    color: [palette.primary],
    grid: { left: 42, right: 16, top: 28, bottom: 52 },
    xAxis: {
      type: 'category',
      data: bar.map((item) => item.name),
      axisLabel: { color: palette.muted, interval: 0, rotate: 24 },
      axisLine: { lineStyle: { color: palette.grid } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'bar',
      data: bar.map((item) => item.value),
      barWidth: 24,
      itemStyle: { borderRadius: [6, 6, 0, 0], color: palette.primary },
    }],
    tooltip: { trigger: 'axis' },
  })

  radarChart?.setOption({
    animationDuration: 450,
    radar: {
      indicator: radar.map((item) => ({ name: item.name, max: 100 })),
      radius: '62%',
      axisName: { color: palette.text },
      splitLine: { lineStyle: { color: palette.grid } },
      splitArea: { areaStyle: { color: ['#ffffff', '#f5f8fb'] } },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'radar',
      data: [{ value: radar.map((item) => item.value), name: '评分' }],
      symbolSize: 5,
      areaStyle: { color: palette.fill },
      lineStyle: { color: palette.accent, width: 2 },
      itemStyle: { color: palette.accent },
    }],
    tooltip: {},
  })
}

function resizeCharts() {
  barChart?.resize()
  radarChart?.resize()
}

onMounted(() => {
  renderCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  barChart?.dispose()
  radarChart?.dispose()
})

watch(() => props.data, renderCharts, { deep: true })
</script>

<template>
  <div v-if="data?.bar?.length || data?.radar?.length" class="chart-grid">
    <section class="panel">
      <div class="panel-heading">
        <h3>分项评分</h3>
      </div>
      <div ref="barRef" class="chart"></div>
    </section>
    <section class="panel">
      <div class="panel-heading">
        <h3>能力雷达</h3>
      </div>
      <div ref="radarRef" class="chart"></div>
    </section>
  </div>
</template>
