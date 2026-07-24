<script setup>
import { RefreshCw } from 'lucide-vue-next'

import { usePlatform } from '../../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="admin-stack">
    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>学生分析概览</h3>
          <p class="panel-subtitle">仅展示元数据（账号、班级、岗位、得分），不含简历正文，符合指导端隐私边界。</p>
        </div>
        <button class="secondary-action" :disabled="platform.teacherRecordsLoading" @click="platform.loadTeacherRecords">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
    </section>

    <section v-if="platform.teacherRecordsLoading" class="empty-state compact">
      <RefreshCw :size="28" class="spin-icon" />
      <span>正在加载学生记录…</span>
    </section>

    <section v-else class="panel">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>学生</th><th>班级</th><th>专业</th><th>岗位</th><th>得分</th><th>诊断项</th><th>状态</th><th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in platform.teacherRecords" :key="item.record_id">
              <td>
                <strong>{{ item.display_name }}</strong>
                <div class="muted-cell">{{ item.username }}</div>
              </td>
              <td>{{ item.class_name || '-' }}</td>
              <td>{{ item.major || '-' }}</td>
              <td>{{ item.target_position || '-' }}</td>
              <td>{{ item.total_score ?? '-' }}</td>
              <td>{{ item.diagnosis_count }}</td>
              <td><span :class="['mode-tag', platform.batchStatusTone(item.status)]">{{ item.status }}</span></td>
              <td>{{ platform.formatDateTime(item.created_at) }}</td>
            </tr>
            <tr v-if="!platform.teacherRecords.length">
              <td colspan="8" class="table-empty">暂无学生分析记录。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
