<script setup>
import { Archive, PauseCircle, RefreshCw, RotateCcw } from 'lucide-vue-next'

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

      <label class="field">
        <span>岗位模板</span>
        <select v-model.number="platform.selectedJobProfileId" @change="platform.handleJobProfileChange">
          <option :value="0">不使用模板，手动填写</option>
          <option v-for="profile in platform.jobProfileOptions" :key="profile.id" :value="profile.id">
            {{ profile.optionLabel }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>目标岗位</span>
        <input v-model="platform.targetPosition" placeholder="例如：数据分析实习生" />
      </label>

      <label class="field">
        <span>岗位 JD</span>
        <textarea v-model="platform.jobDescription" rows="8" placeholder="粘贴统一岗位要求，用于批量岗位匹配分析。"></textarea>
      </label>

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
        <strong>{{ platform.batchResult.processed_files || 0 }}/{{ platform.batchResult.total_files || 0 }}</strong>
        <span>{{ platform.batchResult.status_label || '已提交批量任务' }}</span>
      </div>
      <div v-if="platform.batchResult" class="batch-progress-block">
        <div class="batch-progress-meta">
          <span :class="['mode-tag', platform.batchStatusTone(platform.batchResult.status)]">{{ platform.batchResult.status_label }}</span>
          <small>成功 {{ platform.batchResult.success_count || 0 }} / 失败 {{ platform.batchResult.failed_count || 0 }}</small>
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
          <thead><tr><th>文件</th><th>状态</th><th>解析</th><th>分数</th></tr></thead>
          <tbody>
            <tr
              v-for="item in platform.batchResult.results"
              :key="item.filename"
              :class="{ 'clickable-row': item.record_id }"
              @click="platform.openBatchResultRecord(item)"
            >
              <td>{{ item.filename }}</td>
              <td>{{ item.status }}</td>
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
