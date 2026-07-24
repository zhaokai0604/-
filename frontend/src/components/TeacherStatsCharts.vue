<script setup>
import echarts from '../utils/echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: null,
  },
})

const scoreRef = ref(null)
const dailyRef = ref(null)
const schoolRef = ref(null)
let scoreChart
let dailyChart
let schoolChart

const palette = {
  primary: '#4f46e5',
  accent: '#6366f1',
  grid: '#e5e7eb',
  text: '#111827',
  muted: '#6b7280',
}

function renderCharts() {
  const scoreData = props.stats?.score_distribution || []
  const dailyData = props.stats?.daily_volume || []
  const schoolData = props.stats?.by_school || []

  if (!scoreChart && scoreRef.value) {
    scoreChart = echarts.init(scoreRef.value)
  }
  if (!dailyChart && dailyRef.value) {
    dailyChart = echarts.init(dailyRef.value)
  }
  if (!schoolChart && schoolRef.value) {
    schoolChart = echarts.init(schoolRef.value)
  }

  scoreChart?.setOption({
    color: [palette.primary],
    grid: { left: 42, right: 16, top: 28, bottom: 40 },
    xAxis: {
      type: 'category',
      data: scoreData.map((item) => item.band),
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'bar',
      data: scoreData.map((item) => item.count),
      barWidth: 28,
      itemStyle: { borderRadius: [6, 6, 0, 0] },
    }],
    tooltip: { trigger: 'axis' },
  })

  dailyChart?.setOption({
    color: [palette.accent],
    grid: { left: 42, right: 16, top: 28, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dailyData.map((item) => item.date),
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'line',
      smooth: true,
      data: dailyData.map((item) => item.count),
      areaStyle: { color: 'rgba(99, 102, 241, 0.12)' },
    }],
    tooltip: { trigger: 'axis' },
  })

  schoolChart?.setOption({
    color: [palette.primary],
    grid: { left: 100, right: 24, top: 16, bottom: 24 },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: 'category',
      data: schoolData.map((item) => item.name).reverse(),
      axisLabel: { color: palette.muted, width: 90, overflow: 'truncate' },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'bar',
      data: schoolData.map((item) => item.count).reverse(),
      barWidth: 16,
      itemStyle: { borderRadius: [0, 6, 6, 0] },
    }],
    tooltip: { trigger: 'axis' },
  })
}

function resizeCharts() {
  scoreChart?.resize()
  dailyChart?.resize()
  schoolChart?.resize()
}

onMounted(() => {
  renderCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  scoreChart?.dispose()
  dailyChart?.dispose()
  schoolChart?.dispose()
})

watch(() => props.stats, renderCharts, { deep: true })
</script>

<template>
  <section v-if="stats" class="chart-grid teacher-chart-grid">
    <section class="panel">
      <div class="panel-heading"><h3>分数分布</h3></div>
      <div ref="scoreRef" class="chart"></div>
    </section>
    <section class="panel">
      <div class="panel-heading"><h3>近 7 日分析量</h3></div>
      <div ref="dailyRef" class="chart"></div>
    </section>
    <section class="panel teacher-wide-chart">
      <div class="panel-heading"><h3>院校分布 Top</h3></div>
      <div ref="schoolRef" class="chart chart-tall"></div>
    </section>
  </section>
</template>
