<script setup>
import { Archive, BarChart3, CheckCircle2, ClipboardList, PauseCircle, RefreshCw, X } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="admin-stack">
    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>任务概览</h3>
          <p class="panel-subtitle">统一查看单份分析和批量分析任务。</p>
        </div>
        <button class="secondary-action" @click="platform.loadTasks">
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

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>任务列表</h3>
          <p class="panel-subtitle">单份分析和批量分析任务按时间倒序展示。</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>类型</th><th>文件</th><th>岗位</th><th>状态</th><th>进度</th><th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in platform.tasks"
              :key="task.task_key"
              class="clickable-row"
              @click="platform.openTask(task)"
            >
              <td>{{ task.task_type_label }}</td>
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
            </tr>
            <tr v-if="!platform.tasks.length">
              <td colspan="6" class="table-empty">暂无任务数据。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
