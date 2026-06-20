<script setup>
import {
  Archive,
  BarChart3,
  BriefcaseBusiness,
  ClipboardList,
  Download,
  FileText,
  History,
  Settings,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserRound,
  UsersRound,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
const route = useRoute()

const showTopbar = computed(() => route.name !== 'dashboard' && route.name !== 'login' && route.name !== 'register')
const showResumeDetailNav = computed(() => platform.result || platform.activeTab === 'result')
</script>

<template>
  <main class="app-shell">
    <aside class="app-sidebar">
      <div class="sidebar-inner">
        <div class="brand brand-block">
          <div class="brand-mark">
            <Sparkles :size="20" />
          </div>
          <div>
            <h1>简历评价智能体</h1>
            <p>高校学生求职简历分析与优化平台</p>
          </div>
        </div>

        <section class="sidebar-panel">
          <span class="sidebar-label">工作区</span>
          <nav class="side-nav" aria-label="主导航">
            <button :class="{ active: platform.activeTab === 'dashboard' }" @click="platform.setActiveTab('dashboard')">
              <BarChart3 :size="17" />工作台
            </button>
            <button :class="{ active: platform.activeTab === 'single' }" @click="platform.setActiveTab('single')">
              <UploadCloud :size="17" />单份分析
            </button>
            <button :class="{ active: platform.activeTab === 'batch' }" @click="platform.setActiveTab('batch')">
              <Archive :size="17" />批量分析
            </button>
            <button :class="{ active: platform.activeTab === 'history' }" @click="platform.setActiveTab('history')">
              <History :size="17" />简历空间
            </button>
            <button :class="{ active: platform.activeTab === 'jobs' }" @click="platform.setActiveTab('jobs')">
              <BriefcaseBusiness :size="17" />岗位库
            </button>
            <button :class="{ active: platform.activeTab === 'tasks' }" @click="platform.setActiveTab('tasks')">
              <ClipboardList :size="17" />任务中心
            </button>
            <button :class="{ active: platform.activeTab === 'reports' }" @click="platform.setActiveTab('reports')">
              <Download :size="17" />报告中心
            </button>
            <button
              v-if="showResumeDetailNav"
              :class="{ active: platform.activeTab === 'result' }"
              @click="platform.setActiveTab('result')"
            >
              <FileText :size="17" />简历详情
            </button>
          </nav>
        </section>

        <section v-if="platform.isTeacherOrAdmin" class="sidebar-panel">
          <span class="sidebar-label">指导端</span>
          <nav class="side-nav">
            <button :class="{ active: platform.activeTab === 'teacher-dashboard' }" @click="platform.setActiveTab('teacher-dashboard')">
              <BarChart3 :size="17" />数据看板
            </button>
          </nav>
        </section>

        <section v-if="platform.isAdmin" class="sidebar-panel">
          <span class="sidebar-label">管理后台</span>
          <nav class="side-nav">
            <button :class="{ active: platform.activeTab === 'admin-users' }" @click="platform.setActiveTab('admin-users')">
              <UsersRound :size="17" />用户管理
            </button>
            <button :class="{ active: platform.activeTab === 'admin-jobs' }" @click="platform.setActiveTab('admin-jobs')">
              <BriefcaseBusiness :size="17" />岗位模板
            </button>
            <button :class="{ active: platform.activeTab === 'admin-system' }" @click="platform.setActiveTab('admin-system')">
              <ShieldCheck :size="17" />系统管理
            </button>
          </nav>
        </section>

        <section class="sidebar-panel">
          <span class="sidebar-label">系统</span>
          <nav class="side-nav">
            <button :class="{ active: platform.settingsPanelOpen }" @click="platform.openSettingsPanel">
              <Settings :size="17" />设置
            </button>
          </nav>
        </section>

        <div class="sidebar-spacer" />

        <section class="sidebar-status">
          <div class="status-chip" :class="{ enhanced: platform.enableAi }">
            <Sparkles v-if="platform.enableAi" :size="15" />
            <ShieldCheck v-else :size="15" />
            <span>{{ platform.modeLabel }}</span>
          </div>
          <div class="status-card">
            <strong>{{ platform.currentIdentityLabel }}</strong>
            <span>{{ platform.auth.authenticated ? '数据已隔离保护' : '登录后可同步历史记录' }}</span>
            <button class="account-button full-width" @click="platform.openAuthPanel('login')">
              <UserRound :size="17" />
              <span>{{ platform.auth.authenticated ? '查看账号' : '登录 / 注册' }}</span>
            </button>
          </div>
        </section>
      </div>
    </aside>

    <section class="app-main">
      <header v-if="showTopbar" class="workspace-topbar">
        <div class="workspace-topbar-copy">
          <div class="breadcrumb">{{ platform.breadcrumbLabel }}</div>
          <h2>{{ platform.pageTitle }}</h2>
          <p>{{ platform.pageSubtitle }}</p>
        </div>
      </header>

      <section class="workspace" :class="{ 'workspace--dashboard': route.name === 'dashboard' || route.name === 'login' || route.name === 'register' }">
        <p v-if="platform.error" class="alert">{{ platform.error }}</p>
        <router-view />
      </section>
    </section>
  </main>
</template>
