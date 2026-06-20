<script setup>
import * as echarts from 'echarts'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  versions: {
    type: Array,
    default: () => [],
  },
  compare: {
    type: Object,
    default: null,
  },
})

const trendRef = ref(null)
const deltaRef = ref(null)
let trendChart
let deltaChart

const palette = {
  primary: '#4f46e5',
  accent: '#6366f1',
  success: '#059669',
  danger: '#dc2626',
  grid: '#e5e7eb',
  muted: '#6b7280',
}

const trendData = computed(() => {
  if (props.compare?.trend?.length) {
    return props.compare.trend
  }
  return props.versions || []
})

const hasCompare = computed(() => Boolean(props.compare?.dimension_deltas?.length))

function renderCharts() {
  const trend = trendData.value
  if (!trend.length) {
    return
  }

  if (!trendChart && trendRef.value) {
    trendChart = echarts.init(trendRef.value)
  }
  trendChart?.setOption({
    color: [palette.primary],
    grid: { left: 42, right: 16, top: 28, bottom: 40 },
    xAxis: {
      type: 'category',
      data: trend.map((item) => `v${item.version_no}`),
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'line',
      smooth: true,
      data: trend.map((item) => item.total_score),
      areaStyle: { color: 'rgba(99, 102, 241, 0.12)' },
      symbolSize: 8,
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0]
        if (!point) return ''
        const item = trend[point.dataIndex]
        return `v${item.version_no}<br/>总分：${item.total_score}`
      },
    },
  })

  const deltas = props.compare?.dimension_deltas || []
  if (!deltas.length) {
    return
  }

  if (!deltaChart && deltaRef.value) {
    deltaChart = echarts.init(deltaRef.value)
  }
  deltaChart?.setOption({
    grid: { left: 88, right: 24, top: 16, bottom: 24 },
    xAxis: {
      type: 'value',
      axisLabel: { color: palette.muted },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: 'category',
      data: deltas.map((item) => item.name).reverse(),
      axisLabel: { color: palette.muted },
      axisLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: 'bar',
      data: deltas.map((item) => ({
        value: item.delta,
        itemStyle: { color: item.delta >= 0 ? palette.success : palette.danger },
      })).reverse(),
      barWidth: 14,
      label: {
        show: true,
        position: 'right',
        formatter: ({ value }) => (value > 0 ? `+${value}` : `${value}`),
      },
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0]
        if (!point) return ''
        const item = deltas[deltas.length - 1 - point.dataIndex]
        return `${item.name}<br/>v${props.compare.a.version_no}: ${item.a}<br/>v${props.compare.b.version_no}: ${item.b}<br/>变化: ${item.delta > 0 ? '+' : ''}${item.delta}`
      },
    },
  })
}

function resizeCharts() {
  trendChart?.resize()
  deltaChart?.resize()
}

onMounted(() => {
  renderCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  deltaChart?.dispose()
})

watch(() => [props.versions, props.compare], renderCharts, { deep: true })
</script>

<template>
  <section v-if="trendData.length > 1" class="panel version-compare-panel">
    <div class="panel-heading">
      <div>
        <h3>版本得分趋势</h3>
        <span v-if="compare?.summary" class="panel-subtitle">
          v{{ compare.a.version_no }} → v{{ compare.b.version_no }}：
          <strong :class="compare.summary.improved ? 'delta-up' : compare.summary.unchanged ? '' : 'delta-down'">
            {{ compare.summary.total_score_delta > 0 ? '+' : '' }}{{ compare.summary.total_score_delta }} 分
          </strong>
        </span>
        <span v-else class="panel-subtitle">查看各版本总分变化</span>
      </div>
    </div>
    <div ref="trendRef" class="chart"></div>
    <div v-if="hasCompare" class="compare-delta-block">
      <h4>分项变化（v{{ compare.a.version_no }} → v{{ compare.b.version_no }}）</h4>
      <div ref="deltaRef" class="chart chart-tall"></div>
    </div>
  </section>
</template>
