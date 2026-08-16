<script setup>
import { onMounted, ref, watch } from 'vue'
import { RefreshCw, Trash2 } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
const historySelectAllRef = ref(null)

watch([() => platform.someHistorySelected, () => platform.allHistorySelected], () => {
  if (historySelectAllRef.value) {
    historySelectAllRef.value.indeterminate = platform.someHistorySelected
  }
})

onMounted(() => {
  if (historySelectAllRef.value) {
    historySelectAllRef.value.indeterminate = platform.someHistorySelected
  }
})
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h3>历史分析</h3>
        <p class="panel-subtitle">{{ platform.historyCount }} 条记录，当前身份：{{ platform.currentIdentityLabel }}</p>
      </div>
      <div class="history-actions">
        <span class="selection-note">已选 {{ platform.selectedHistoryCount }}</span>
        <button class="secondary-action" :disabled="platform.loading || !platform.selectedHistoryCount" @click="platform.removeSelectedRecords">
          <Trash2 :size="16" />删除所选
        </button>
        <button class="secondary-action danger-action" :disabled="platform.loading || !platform.history.length" @click="platform.clearAllHistory">
          <Trash2 :size="16" />清空
        </button>
        <button class="secondary-action" :disabled="platform.loading || platform.historyLoading" @click="platform.loadHistory">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
    </div>
    <div v-if="platform.historyLoading" class="empty-state compact">
      <RefreshCw :size="28" class="spin-icon" />
      <span>正在加载历史记录…</span>
    </div>
    <div v-else class="table-wrap">
      <table class="data-table history-table">
        <thead>
          <tr>
            <th class="select-col">
              <input
                ref="historySelectAllRef"
                class="table-check"
                type="checkbox"
                :checked="platform.allHistorySelected"
                :disabled="!platform.history.length"
                @change="platform.toggleAllHistory"
              />
            </th>
            <th class="history-file-col">文件</th>
            <th class="history-target-col">岗位</th>
            <th class="history-score-col">总分</th>
            <th class="history-mode-col">模式</th>
            <th class="history-time-col">时间</th>
            <th class="history-action-col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in platform.history" :key="record.record_id">
            <td class="select-col">
              <input v-model="platform.selectedRecordIds" class="table-check" type="checkbox" :value="record.record_id" />
            </td>
            <td>
              {{ record.filename }}
              <div v-if="record.version_no > 1" class="muted-cell">v{{ record.version_no }}</div>
              <div v-if="record.score_reliability === 'low_parse_capped'" class="record-badges">
                <span v-if="record.score_reliability === 'low_parse_capped'" class="subtle-pill warn">低解析封顶</span>
              </div>
            </td>
            <td>
              <div class="history-target-text" :title="record.target_position || '-'">{{ record.target_position || '-' }}</div>
              <div v-if="record.job_profile?.name" class="muted-cell">{{ record.job_profile.name }}</div>
            </td>
            <td>
              <strong :class="['score-cell', platform.scoreGradeTone(record.total_score)]">{{ record.total_score }}</strong>
              <div v-if="record.parse_quality" class="muted-cell">
                <span class="subtle-pill" :class="platform.parseQualityTone(record.parse_quality)">
                  {{ platform.parseQualityLabel(record.parse_quality) }}
                </span>
              </div>
              <div v-if="record.score_reliability === 'layout_review'" class="muted-cell">
                <span class="subtle-pill warn">版式需复核</span>
              </div>
            </td>
            <td><span class="mode-tag" :class="platform.displayAnalysisModeClass(record)">{{ platform.displayAnalysisModeLabel(record) }}</span></td>
            <td>{{ platform.formatDateTime(record.created_at) }}</td>
            <td class="row-actions">
              <button @click="platform.openRecord(record)">查看</button>
              <button @click="platform.startNewVersion(record)">新版本</button>
              <a v-if="platform.resolvedSourceResumeUrl(record)" :href="platform.resolvedSourceResumeUrl(record)" target="_blank" rel="noopener noreferrer">简历</a>
              <button class="danger" @click="platform.removeRecord(record)"><Trash2 :size="15" />删除</button>
            </td>
          </tr>
          <tr v-if="!platform.history.length">
            <td colspan="7" class="table-empty">暂无历史记录。上传简历后会自动保存到这里。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
