<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { FileText, MessageCircle, RefreshCw, Sparkles } from 'lucide-vue-next'

import { fetchHistoryDetail, refreshInterviewPrep } from '../api/client'
import MockInterviewPanel from '../components/MockInterviewPanel.vue'
import { usePlatform } from '../stores/platform'

const platform = usePlatform()
const selectedRecordId = ref(0)
const detail = ref(null)
const loading = ref(false)
const generating = ref(false)
const localError = ref('')

const availableRecords = computed(() =>
  platform.history.filter((record) => record.status === 'success'),
)
const selectedRecord = computed(() =>
  availableRecords.value.find((record) => record.record_id === selectedRecordId.value) || null,
)
const interviewPrep = computed(() => detail.value?.interview_prep || {})
const mockInterview = computed(() => detail.value?.mock_interview || {})
const questionCount = computed(() =>
  interviewPrep.value?.question_count
    || interviewPrep.value?.categories?.reduce((sum, category) => sum + (category.questions?.length || 0), 0)
    || 0,
)

async function ensureHistory() {
  if (!platform.history.length && !platform.historyLoading) {
    await platform.loadHistory()
  }
  if (!selectedRecordId.value && availableRecords.value.length) {
    selectedRecordId.value = availableRecords.value[0].record_id
  }
}

async function loadSelectedRecord() {
  if (!selectedRecordId.value) {
    detail.value = null
    return
  }
  loading.value = true
  localError.value = ''
  try {
    detail.value = await fetchHistoryDetail(selectedRecordId.value)
  } catch (err) {
    detail.value = null
    localError.value = err.message || '加载简历记录失败。'
  } finally {
    loading.value = false
  }
}

async function generateInterview(enableAi = true) {
  if (!selectedRecordId.value) {
    localError.value = '请先选择一份已完成分析的简历。'
    return
  }
  generating.value = true
  localError.value = ''
  try {
    const payload = await refreshInterviewPrep(selectedRecordId.value, enableAi)
    detail.value = {
      ...(detail.value || {}),
      record_id: selectedRecordId.value,
      interview_prep: payload.interview_prep || payload,
      mock_interview: payload.mock_interview || detail.value?.mock_interview,
    }
  } catch (err) {
    localError.value = err.message || '生成面试题失败。'
  } finally {
    generating.value = false
  }
}

watch(selectedRecordId, () => {
  void loadSelectedRecord()
})

onMounted(() => {
  void ensureHistory()
})
</script>

<template>
  <section class="interview-workspace">
    <aside class="panel interview-record-panel">
      <div class="panel-heading">
        <div>
          <h3>选择简历</h3>
          <span class="panel-subtitle">从已完成分析的记录中生成面试训练题</span>
        </div>
        <button class="icon-button" type="button" :disabled="platform.historyLoading" @click="platform.loadHistory">
          <RefreshCw :size="16" :class="{ 'spin-icon': platform.historyLoading }" />
        </button>
      </div>

      <div v-if="platform.historyLoading" class="empty-inline">正在加载简历记录…</div>
      <div v-else-if="!availableRecords.length" class="empty-inline">
        暂无可用记录。请先完成一次单份或批量简历分析。
      </div>
      <div v-else class="interview-record-list">
        <button
          v-for="record in availableRecords"
          :key="record.record_id"
          type="button"
          class="interview-record-item"
          :class="{ active: record.record_id === selectedRecordId }"
          @click="selectedRecordId = record.record_id"
        >
          <FileText :size="16" />
          <span>
            <strong>{{ record.filename }}</strong>
            <small>{{ record.target_position || '通用岗位' }} · {{ record.total_score }} 分</small>
          </span>
        </button>
      </div>
    </aside>

    <div class="interview-main-stack">
      <section class="panel">
        <div class="panel-heading">
          <div>
            <h3><MessageCircle :size="18" /> 面试训练</h3>
            <span class="panel-subtitle">
              {{ selectedRecord ? `${selectedRecord.filename} · ${selectedRecord.target_position || '通用岗位'}` : '请选择一份简历' }}
              · 每次重新生成都会换一套训练题
            </span>
          </div>
          <button
            class="primary-action"
            type="button"
            :disabled="generating || loading || !selectedRecordId"
            @click="generateInterview(true)"
          >
            <Sparkles :size="16" />
            {{ generating ? '生成中…' : questionCount || mockInterview.steps?.length ? '换一套题目' : '生成面试题' }}
          </button>
        </div>

        <p v-if="localError" class="alert">{{ localError }}</p>
        <div v-if="loading" class="empty-inline">正在加载记录详情…</div>
        <div v-else-if="questionCount" class="interview-summary-grid">
          <div>
            <span>题目总数</span>
            <strong>{{ questionCount }}</strong>
          </div>
          <div>
            <span>模拟轮次</span>
            <strong>{{ mockInterview.total_steps || mockInterview.steps?.length || 0 }}</strong>
          </div>
          <div>
            <span>生成模式</span>
            <strong>{{ interviewPrep.mode === 'deepseek' ? '增强' : '规则' }}</strong>
          </div>
        </div>
        <p v-else class="empty-inline">
          面试题会基于岗位匹配、诊断建议和简历经历生成，不再占用简历分析详情页。
        </p>
      </section>

      <MockInterviewPanel
        v-if="mockInterview.steps?.length"
        :session="mockInterview"
        :record-id="selectedRecordId"
      />
    </div>
  </section>
</template>
