<script setup>
import { computed } from 'vue'
import { ArrowDown, ArrowRight, ArrowUp, GitBranch } from 'lucide-vue-next'

const props = defineProps({
  compare: { type: Object, default: null },
})

const summary = computed(() => props.compare?.summary || null)
const deltas = computed(() => {
  const items = props.compare?.dimension_deltas || []
  return [...items].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
})

function deltaClass(delta) {
  if (delta > 0) return 'up'
  if (delta < 0) return 'down'
  return 'flat'
}

function formatDelta(delta) {
  if (delta > 0) return `+${delta}`
  return `${delta}`
}
</script>

<template>
  <section v-if="compare && deltas.length" class="panel version-delta-panel">
    <div class="panel-heading">
      <div>
        <h3><GitBranch :size="18" /> 版本时光机</h3>
        <span class="panel-subtitle">
          v{{ compare.a.version_no }} → v{{ compare.b.version_no }}
          <template v-if="summary">
            · 总分
            <strong :class="deltaClass(summary.total_score_delta)">
              {{ formatDelta(summary.total_score_delta) }}
            </strong>
          </template>
        </span>
      </div>
    </div>

    <div class="version-delta-total">
      <div class="version-delta-score">
        <span>v{{ compare.a.version_no }}</span>
        <strong>{{ compare.a.total_score }}</strong>
      </div>
      <ArrowRight :size="18" class="version-delta-arrow" />
      <div class="version-delta-score">
        <span>v{{ compare.b.version_no }}</span>
        <strong>{{ compare.b.total_score }}</strong>
      </div>
      <div class="version-delta-badge" :class="deltaClass(summary?.total_score_delta || 0)">
        <ArrowUp v-if="(summary?.total_score_delta || 0) > 0" :size="16" />
        <ArrowDown v-else-if="(summary?.total_score_delta || 0) < 0" :size="16" />
        <span>{{ formatDelta(summary?.total_score_delta || 0) }} 分</span>
      </div>
    </div>

    <ul class="version-delta-list">
      <li v-for="item in deltas" :key="item.key || item.name" :class="deltaClass(item.delta)">
        <span class="dim-name">{{ item.name }}</span>
        <span class="dim-scores">{{ item.a }} → {{ item.b }}</span>
        <span class="dim-delta">
          <ArrowUp v-if="item.delta > 0" :size="14" />
          <ArrowDown v-else-if="item.delta < 0" :size="14" />
          <ArrowRight v-else :size="14" />
          {{ formatDelta(item.delta) }}
        </span>
      </li>
    </ul>
  </section>
</template>
