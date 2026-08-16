<script setup>
import { Archive, PauseCircle, RefreshCw, RotateCcw } from 'lucide-vue-next'

import JobProfileFields from '../components/JobProfileFields.vue'
import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="analysis-layout">
    <form class="panel form-panel upload-panel" @submit.prevent="platform.submitZip">
      <div class="panel-heading">
        <h3>上传压缩包</h3>
        <span class="subtle-pill">ZIP</span>
      </div>

      <label class="file-drop" @dragover="platform.onDragOver" @drop="platform.onFileDrop($event, 'batch')">
        <input type="file" accept=".zip" @change="platform.onZipFile" />
        <Archive :size="30" />
        <strong>{{ platform.zipFile?.name || '点击或拖拽上传 ZIP 压缩包' }}</strong>
        <span>压缩包内可包含多份 Word / PDF 简历</span>
      </label>

      <label class="switch-row target-match-switch">
        <input :checked="platform.enableTargetMatch" type="checkbox" @change="platform.setTargetMatchEnabled($event.target.checked)" />
        <span>指定目标岗位后再匹配（默认关闭）</span>
      </label>

      <section v-if="platform.enableTargetMatch" class="target-match-panel">
        <JobProfileFields
          :model-value="platform.selectedJobProfileKey"
          :target-position="platform.targetPosition"
          :job-description="platform.jobDescription"
          :profiles="platform.jobProfileOptions"
          :presets="platform.jobProfilePresetOptions"
          :textarea-rows="8"
          @update:model-value="(value) => { platform.handleJobProfileChange(value) }"
          @update:target-position="(value) => { platform.targetPosition = value }"
          @update:job-description="(value) => { platform.jobDescription = value }"
          @clear="platform.clearTargetJobInputs"
        />
      </section>
      <p v-else class="muted-cell target-match-hint">当前批量任务不会套用目标岗，仅做通用分析。</p>
      <button class="primary-action" :disabled="platform.loading || platform.batchTaskRunning">
        <Archive :size="18" />
        {{ platform.loading ? '正在提交批量任务' : platform.batchTaskRunning ? '后台任务处理中' : '开始批量分析' }}
      </button>
    </form>

    <section class="panel batch-result-panel">
      <div class="panel-heading">
        <h3>批量结果</h3>
        <div class="panel-actions">
          <button
            v-if="platform.batchResult?.batch_task_id && platform.batchResult.status === 'processing'"
            class="secondary-action"
            type="button"
            :disabled="platform.loading"
            @click="platform.pauseCurrentBatchTask"
          >
            <PauseCircle :size="16" />暂停
          </button>
          <button
            v-if="platform.batchResult?.batch_task_id && platform.batchTaskRetriable"
            class="secondary-action"
            type="button"
            :disabled="platform.loading"
            @click="platform.retryCurrentBatchTask"
          >
            <RotateCcw :size="16" />重试
          </button>
          <button
            v-if="platform.batchResult?.batch_task_id"
            class="secondary-action"
            type="button"
            @click="platform.refreshBatchTask(platform.batchResult.batch_task_id)"
          >
            <RefreshCw :size="16" />刷新
          </button>
        </div>
      </div>

      <div v-if="platform.batchResult" class="batch-summary">
        <strong>{{ platform.batchResult.processed_files || 0 }}/{{ (platform.batchResult.total_files || 0) + (platform.batchResult.skipped_count || 0) }}</strong>
        <span>{{ platform.batchResult.status_label || '已提交批量任务' }}</span>
      </div>
      <div v-if="platform.batchResult" class="batch-progress-block">
        <div class="batch-progress-meta">
          <span :class="['mode-tag', platform.batchStatusTone(platform.batchResult.status)]">{{ platform.batchResult.status_label }}</span>
          <small>
            成功 {{ platform.batchResult.success_count || 0 }}
            / 失败 {{ platform.batchResult.failed_count || 0 }}
            <template v-if="platform.batchResult.skipped_count"> / 跳过 {{ platform.batchResult.skipped_count }}</template>
          </small>
        </div>
        <div class="batch-progress-bar">
          <div class="batch-progress-fill" :style="{ width: `${platform.batchProgress}%` }"></div>
        </div>
        <small v-if="platform.batchResult.status === 'processing'">后台正在逐份分析，可以切换页面继续使用。</small>
        <small v-else-if="platform.batchTaskPaused">当前任务已暂停，已完成结果会保留。可点击重试继续处理。</small>
        <small v-else-if="platform.batchResult.status === 'failed'">任务执行失败，可点击重试继续处理未完成的简历。</small>
      </div>
      <div v-else class="empty-inline">上传 ZIP 压缩包后，将在此展示每份简历的处理进度与评分。</div>

      <div class="table-wrap batch-result-table" v-if="platform.batchResult">
        <table class="data-table">
          <thead><tr><th>文件</th><th>状态</th><th>模式</th><th>解析</th><th>分数</th></tr></thead>
          <tbody>
            <tr
              v-for="item in platform.batchResult.results"
              :key="item.filename"
              :class="{ 'clickable-row': item.record_id }"
              @click="platform.openBatchResultRecord(item)"
            >
              <td>
                {{ item.filename }}
                <span v-if="item.reused" class="subtle-pill">复用</span>
              </td>
              <td><span :class="['mode-tag', platform.batchItemStatusTone(item.status)]">{{ platform.batchItemStatusLabel(item.status) }}</span></td>
              <td>
                <span v-if="item.analysis_mode_label || item.analysis_mode" class="mode-tag" :class="platform.displayAnalysisModeClass(item)">{{ platform.displayAnalysisModeLabel(item) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <div class="batch-parse-cell">
                  <span :class="['mode-tag', platform.parseQualityTone(item.parse_quality)]">{{ platform.parseQualityLabel(item.parse_quality) }}</span>
                  <small v-if="item.error">{{ item.error }}</small>
                  <small v-else-if="item.parse_warnings?.length">{{ item.parse_warnings[0] }}</small>
                </div>
              </td>
              <td>{{ item.total_score ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
