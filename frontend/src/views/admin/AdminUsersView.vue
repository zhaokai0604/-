<script setup>
import {
  Archive,
  BarChart3,
  ClipboardList,
  FileText,
  GraduationCap,
  KeyRound,
  RefreshCw,
  UserCog,
  UsersRound,
} from 'lucide-vue-next'

import { usePlatform } from '../../stores/platform'

const platform = usePlatform()
const roleOptions = [
  { value: 'user', label: '用户' },
  { value: 'teacher', label: '教师' },
  { value: 'admin', label: '管理员' },
]
</script>

<template>
  <section class="admin-stack">
    <p v-if="platform.adminMessage" class="account-message">{{ platform.adminMessage }}</p>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>系统概览</h3>
          <p class="panel-subtitle">管理员只查看统计和元数据，默认不查看用户简历正文。</p>
        </div>
        <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.loadAdminUsersData">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div class="admin-metrics">
        <div><UsersRound :size="20" /><span>用户</span><strong>{{ platform.adminStats?.users?.total ?? '--' }}</strong></div>
        <div><UserCog :size="20" /><span>管理员</span><strong>{{ platform.adminStats?.users?.admins ?? '--' }}</strong></div>
        <div><GraduationCap :size="20" /><span>教师</span><strong>{{ platform.adminStats?.users?.teachers ?? '--' }}</strong></div>
        <div><FileText :size="20" /><span>分析记录</span><strong>{{ platform.adminStats?.records?.total ?? '--' }}</strong></div>
        <div><BarChart3 :size="20" /><span>今日分析</span><strong>{{ platform.adminStats?.records?.today ?? '--' }}</strong></div>
        <div><Archive :size="20" /><span>批量任务</span><strong>{{ platform.adminStats?.batch_tasks?.total ?? '--' }}</strong></div>
        <div><ClipboardList :size="20" /><span>审计日志</span><strong>{{ platform.adminStats?.audit_logs?.total ?? '--' }}</strong></div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>用户管理</h3>
          <p class="panel-subtitle">管理员可调整角色、启用/禁用账号或重置密码。</p>
        </div>
      </div>
      <div class="table-wrap admin-scroll-wrap">
        <table class="data-table admin-table">
          <thead>
            <tr>
              <th>账号</th><th>角色</th><th>状态</th><th>记录</th><th>最近登录</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in platform.adminUsers" :key="user.id">
              <td><strong>{{ user.display_name }}</strong><br /><span class="muted-cell">{{ user.username }}</span></td>
              <td>
                <select
                  v-if="user.username !== 'guest' && user.id !== platform.auth.user?.id"
                  class="role-select"
                  :value="user.role"
                  :disabled="platform.adminLoading"
                  @change="platform.changeUserRole(user, $event.target.value)"
                >
                  <option v-for="option in roleOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <span v-else class="mode-tag" :class="user.role === 'admin' ? 'success' : 'offline'">{{ platform.roleLabel(user.role) }}</span>
              </td>
              <td><span class="mode-tag" :class="user.status === 'active' ? 'success' : 'danger'">{{ user.status === 'active' ? '启用' : '禁用' }}</span></td>
              <td>{{ user.record_count }}</td>
              <td>{{ platform.formatDateTime(user.last_login_at) }}</td>
              <td>{{ platform.formatDateTime(user.created_at) }}</td>
              <td class="row-actions">
                <button
                  v-if="user.status === 'active'"
                  :disabled="platform.adminLoading || user.username === 'guest' || user.id === platform.auth.user?.id"
                  @click="platform.changeUserStatus(user, 'disabled')"
                >禁用</button>
                <button v-else :disabled="platform.adminLoading" @click="platform.changeUserStatus(user, 'active')">启用</button>
                <button :disabled="platform.adminLoading || user.username === 'guest'" @click="platform.resetUserPassword(user)">
                  <KeyRound :size="15" />重置密码
                </button>
              </td>
            </tr>
            <tr v-if="!platform.adminUsers.length">
              <td colspan="7" class="table-empty">暂无用户数据。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
