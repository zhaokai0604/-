<script setup>
import { RefreshCw } from 'lucide-vue-next'

import { reportUrl } from '../api/client'
import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h3>报告中心</h3>
        <p class="panel-subtitle">集中下载 Word / PDF 报告，并查看来源简历和岗位模板。</p>
      </div>
      <button class="secondary-action" @click="platform.loadReports">
        <RefreshCw :size="16" />刷新
      </button>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>文件</th><th>岗位</th><th>总分</th><th>模式</th><th>时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in platform.reports" :key="item.record_id">
            <td>{{ item.filename }}</td>
            <td>
              {{ item.target_position || '-' }}
              <div v-if="item.job_profile?.name" class="muted-cell">{{ item.job_profile.name }}</div>
            </td>
            <td><strong>{{ item.total_score }}</strong></td>
            <td><span class="mode-tag" :class="item.analysis_mode">{{ item.analysis_mode_label || platform.analysisModeLabel(item.analysis_mode) }}</span></td>
            <td>{{ platform.formatDateTime(item.created_at) }}</td>
            <td class="row-actions">
              <a v-if="item.source_resume_url" :href="item.source_resume_url" target="_blank" rel="noopener noreferrer">简历</a>
              <a v-if="item.reports?.docx" :href="reportUrl(item.reports.docx, 'docx')" target="_blank">Word</a>
              <a v-if="item.reports?.pdf" :href="reportUrl(item.reports.pdf, 'pdf')" target="_blank">PDF</a>
            </td>
          </tr>
          <tr v-if="!platform.reports.length">
            <td colspan="6" class="table-empty">暂无报告数据。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
