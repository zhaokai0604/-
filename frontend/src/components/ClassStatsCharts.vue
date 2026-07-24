<script setup>
import echarts from '../utils/echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  classes: {
    type: Array,
    default: () => [],
  },
})

const chartRef = ref(null)
let chart

function renderChart() {
  const rows = props.classes || []
  if (!chart && chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
  chart?.setOption({
    color: ['#4f46e5'],
    grid: { left: 100, right: 24, top: 16, bottom: 24 },
    xAxis: {
      type: 'value',
      minInterval: 1,
      max: 100,
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'category',
      data: rows.map((item) => item.name).reverse(),
      axisLabel: { color: '#6b7280', width: 90, overflow: 'truncate' },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    series: [{
      type: 'bar',
      data: rows.map((item) => item.avg_score || 0).reverse(),
      barWidth: 16,
      itemStyle: { borderRadius: [0, 6, 6, 0] },
      label: {
        show: true,
        position: 'right',
        formatter: ({ value }) => `${value} 分`,
      },
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0]
        if (!point) return ''
        const item = rows[rows.length - 1 - point.dataIndex]
        return `${item.name}<br/>均分：${item.avg_score}<br/>学生：${item.student_count}<br/>分析：${item.record_count}`
      },
    },
  })
}

function resizeChart() {
  chart?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})

watch(() => props.classes, renderChart, { deep: true })
</script>

<template>
  <section v-if="classes.length" class="panel">
    <div class="panel-heading"><h3>班级均分对比</h3></div>
    <div ref="chartRef" class="chart chart-tall"></div>
  </section>
</template>
