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
        <button class="secondary-action" :disabled="platform.loading" @click="platform.loadHistory">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table">
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
            <th>文件</th><th>岗位</th><th>总分</th><th>模式</th><th>时间</th><th>操作</th>
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
            </td>
            <td>
              {{ record.target_position || '-' }}
              <div v-if="record.job_profile?.name" class="muted-cell">{{ record.job_profile.name }}</div>
            </td>
            <td><strong>{{ record.total_score }}</strong></td>
            <td><span class="mode-tag" :class="record.analysis_mode">{{ record.analysis_mode_label || platform.analysisModeLabel(record.analysis_mode) }}</span></td>
            <td>{{ new Date(record.created_at).toLocaleString() }}</td>
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
