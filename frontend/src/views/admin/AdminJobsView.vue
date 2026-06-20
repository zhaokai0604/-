<script setup>
import { BriefcaseBusiness, RefreshCw } from 'lucide-vue-next'

import { usePlatform } from '../../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="admin-stack">
    <p v-if="platform.adminMessage" class="account-message">{{ platform.adminMessage }}</p>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>全平台岗位模板</h3>
          <p class="panel-subtitle">查看各用户创建的岗位模板及归属信息，共 {{ platform.adminJobs.length }} 条。</p>
        </div>
        <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.loadAdminJobsList">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div v-if="platform.adminJobs.length" class="table-wrap admin-scroll-wrap">
        <table class="data-table admin-table">
          <thead>
            <tr>
              <th>模板</th><th>目标岗位</th><th>分类</th><th>状态</th><th>归属用户</th><th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in platform.adminJobs" :key="job.id">
              <td><strong>{{ job.name }}</strong></td>
              <td>{{ job.target_position || '-' }}</td>
              <td>{{ job.category || '-' }}</td>
              <td><span class="mode-tag" :class="job.status === 'active' ? 'success' : 'warning'">{{ job.status === 'active' ? '启用' : '草稿' }}</span></td>
              <td>
                {{ job.owner_name }}
                <div class="muted-cell">{{ job.username }}</div>
              </td>
              <td>{{ platform.formatDateTime(job.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-inline">
        <BriefcaseBusiness :size="24" />
        暂无岗位模板数据。
      </div>
    </section>
  </section>
</template>
