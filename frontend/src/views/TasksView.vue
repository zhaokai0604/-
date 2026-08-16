<script setup>
import { Archive, BarChart3, CheckCircle2, ClipboardList, PauseCircle, RefreshCw, RotateCcw, X } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()

function taskTypeLabel(task) {
  const map = {
    batch_analysis: '批量分析',
    single_analysis: '单份分析',
  }
  if (task?.task_type && map[task.task_type]) return map[task.task_type]
  const label = String(task?.task_type_label || '').trim()
  // 兼容历史接口里被错误编码的中文标签
  if (!label || /[鍗鎵嗘瀽]/.test(label)) {
    return map[task?.task_type] || '分析任务'
  }
  return label
}
</script>

<template>
  <section class="admin-stack">
    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>任务概览</h3>
          <p class="panel-subtitle">统一查看单份分析和批量分析任务，点击行可跳转详情。</p>
        </div>
        <button class="secondary-action" :disabled="platform.tasksLoading" @click="platform.loadTasks">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div class="admin-metrics">
        <div><ClipboardList :size="20" /><span>全部任务</span><strong>{{ platform.taskCount }}</strong></div>
        <div><Archive :size="20" /><span>处理中</span><strong>{{ platform.taskSummary.processing || 0 }}</strong></div>
        <div><PauseCircle :size="20" /><span>已暂停</span><strong>{{ platform.taskSummary.paused || 0 }}</strong></div>
        <div><CheckCircle2 :size="20" /><span>已完成</span><strong>{{ platform.taskSummary.success || 0 }}</strong></div>
        <div><BarChart3 :size="20" /><span>部分完成</span><strong>{{ platform.taskSummary.partial_success || 0 }}</strong></div>
        <div><X :size="20" /><span>失败</span><strong>{{ platform.taskSummary.failed || 0 }}</strong></div>
      </div>
    </section>

    <section v-if="platform.tasksLoading" class="empty-state compact">
      <RefreshCw :size="28" class="spin-icon" />
      <span>正在加载任务列表…</span>
    </section>

    <section v-else class="panel">
      <div class="panel-heading">
        <div>
          <h3>任务列表</h3>
          <p class="panel-subtitle">失败任务可直接重试，无需进入详情页。</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>类型</th><th>文件</th><th>岗位</th><th>状态</th><th>进度</th><th>时间</th><th class="actions-col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in platform.tasks"
              :key="task.task_key"
              class="clickable-row"
              @click="platform.openTask(task)"
            >
              <td>{{ taskTypeLabel(task) }}</td>
              <td>{{ task.filename }}</td>
              <td>
                {{ task.target_position || task.job_profile?.target_position || '-' }}
                <div v-if="task.job_profile?.name" class="muted-cell">{{ task.job_profile.name }}</div>
              </td>
              <td><span :class="['mode-tag', platform.batchStatusTone(task.status)]">{{ task.status_label }}</span></td>
              <td>
                <span v-if="task.total_files > 1">{{ task.processed_files || 0 }}/{{ task.total_files || 0 }}</span>
                <span v-else>{{ task.total_score ?? '-' }}</span>
              </td>
              <td>{{ platform.formatDateTime(task.created_at) }}</td>
              <td class="actions-col" @click.stop>
                <button
                  v-if="platform.taskCanRetry(task)"
                  class="secondary-action compact-action"
                  :disabled="platform.loading"
                  @click="platform.retryTask(task, $event)"
                >
                  <RotateCcw :size="14" />重试
                </button>
                <span v-else class="muted-cell">—</span>
              </td>
            </tr>
            <tr v-if="!platform.tasks.length">
              <td colspan="7" class="table-empty">暂无任务数据。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
