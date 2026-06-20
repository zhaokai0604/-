<script setup>
import {
  CheckCircle2,
  Database,
  KeyRound,
  LockKeyhole,
  LogIn,
  LogOut,
  ShieldCheck,
  UserPlus,
  X,
} from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <div v-if="platform.authPanelOpen" class="drawer-backdrop" @click.self="platform.closeAuthPanel">
    <aside class="auth-drawer" aria-label="账号面板">
      <header class="drawer-header">
        <div>
          <span>账号</span>
          <h3>{{ platform.auth.authenticated ? '当前身份' : platform.authMode === 'login' ? '账号登录' : '账号注册' }}</h3>
        </div>
        <button class="icon-button" @click="platform.closeAuthPanel" aria-label="关闭账号面板">
          <X :size="18" />
        </button>
      </header>

      <p v-if="platform.authMessage" class="account-message">{{ platform.authMessage }}</p>

      <form v-if="!platform.auth.authenticated" class="auth-form" @submit.prevent="platform.submitAuth">
        <label class="field">
          <span>用户名</span>
          <input v-model.trim="platform.authForm.username" autocomplete="username" placeholder="3-30 位字母、数字、下划线或短横线" />
        </label>
        <label v-if="platform.authMode === 'register'" class="field">
          <span>昵称</span>
          <input v-model.trim="platform.authForm.displayName" autocomplete="nickname" placeholder="用于页面显示，可不填" />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="platform.authForm.password" autocomplete="current-password" type="password" placeholder="至少 8 位，并包含字母和数字" />
        </label>
        <div v-if="platform.authMode === 'register'" class="password-strength">
          <div class="strength-row">
            <span>密码强度</span>
            <strong :class="platform.passwordStrength.key">{{ platform.passwordStrength.label }}</strong>
          </div>
          <div class="strength-meter"><span :class="platform.passwordStrength.key"></span></div>
          <div class="check-grid">
            <span v-for="item in platform.passwordChecks" :key="item.label" :class="{ ok: item.ok }">
              <CheckCircle2 :size="14" />{{ item.label }}
            </span>
          </div>
        </div>
        <label v-if="platform.authMode === 'register'" class="field">
          <span>确认密码</span>
          <input v-model="platform.authForm.confirmPassword" autocomplete="new-password" type="password" placeholder="再次输入密码" />
        </label>
        <button class="primary-action" :disabled="platform.authLoading">
          <KeyRound :size="18" />
          {{ platform.authLoading ? '处理中' : platform.authMode === 'login' ? '登录' : '注册并登录' }}
        </button>
        <button
          v-if="platform.allowRegister"
          class="text-action"
          type="button"
          @click="platform.authMode = platform.authMode === 'login' ? 'register' : 'login'; platform.authMessage = ''; platform.resetAuthForm(true)"
        >
          <UserPlus v-if="platform.authMode === 'login'" :size="16" />
          <LogIn v-else :size="16" />
          {{ platform.authMode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </button>
      </form>

      <section v-else class="identity-card">
        <div class="avatar">{{ platform.currentIdentityLabel.slice(0, 1) }}</div>
        <strong>{{ platform.currentIdentityLabel }}</strong>
        <span>{{ platform.auth.user?.username }}</span>
        <span>{{ platform.isAdmin ? '管理员账号' : '普通用户账号' }}</span>
        <button class="secondary-action" type="button" :disabled="platform.authLoading" @click="platform.logout">
          <LogOut :size="16" />退出登录
        </button>
        <button
          v-if="platform.auth.guest_history_count"
          class="secondary-action"
          type="button"
          :disabled="platform.authLoading"
          @click="platform.importGuestRecords"
        >
          <Database :size="16" />导入 {{ platform.auth.guest_history_count }} 条访客记录
        </button>
      </section>

      <div class="drawer-notes">
        <div><LockKeyhole :size="17" /> 密码经安全哈希存储</div>
        <div><ShieldCheck :size="17" /> 登录态使用安全 Cookie</div>
      </div>
    </aside>
  </div>
</template>
