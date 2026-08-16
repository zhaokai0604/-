<script setup>
import {
  Archive,
  ArrowLeft,
  BarChart3,
  BriefcaseBusiness,
  ClipboardList,
  Download,
  FileText,
  History,
  Menu,
  MessageCircle,
  Settings,
  ShieldCheck,
  Sparkles,
  GraduationCap,
  UploadCloud,
  UserRound,
  UsersRound,
  X,
} from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { usePlatform } from '../stores/platform'
import brandLogo from '../assets/jianxi-logo.png'
import beianBadge from '../assets/beian-badge.png'

const platform = usePlatform()
const route = useRoute()
const sidebarOpen = ref(false)

const showTopbar = computed(() => route.name !== 'dashboard' && route.name !== 'login' && route.name !== 'register')
const showHomeFooter = computed(() => route.name === 'dashboard')
const showResumeDetailNav = computed(() => route.name === 'workspace-resume-detail')

function closeSidebar() {
  sidebarOpen.value = false
}

function navigateTab(tab) {
  closeSidebar()
  void platform.setActiveTab(tab)
}

watch(
  () => route.fullPath,
  () => closeSidebar(),
)
</script>

<template>
  <main class="app-shell" :class="{ 'sidebar-open': sidebarOpen }">
    <button type="button" class="mobile-nav-toggle" aria-label="打开导航菜单" @click="sidebarOpen = true">
      <Menu :size="22" />
    </button>
    <div class="sidebar-backdrop" aria-hidden="true" @click="closeSidebar" />

    <aside class="app-sidebar">
      <div class="sidebar-inner">
        <div class="brand brand-block">
          <div class="brand-mark">
            <img :src="brandLogo" alt="简析智评" />
          </div>
          <div>
            <h1>简析智评</h1>
            <p>大学生简历诊断与求职成长平台</p>
          </div>
          <button type="button" class="sidebar-close" aria-label="关闭导航" @click="closeSidebar">
            <X :size="20" />
          </button>
        </div>

        <div class="sidebar-scroll">
          <section class="sidebar-panel">
            <span class="sidebar-label">工作区</span>
            <nav class="side-nav" aria-label="主导航">
              <button :class="{ active: platform.activeTab === 'dashboard' }" @click="navigateTab('dashboard')">
                <BarChart3 :size="17" />工作台
              </button>
              <button :class="{ active: platform.activeTab === 'single' }" @click="navigateTab('single')">
                <UploadCloud :size="17" />单份分析
              </button>
              <button :class="{ active: platform.activeTab === 'batch' }" @click="navigateTab('batch')">
                <Archive :size="17" />批量分析
              </button>
              <button :class="{ active: platform.activeTab === 'interview' }" @click="navigateTab('interview')">
                <MessageCircle :size="17" />面试训练
              </button>
              <button :class="{ active: platform.activeTab === 'history' }" @click="navigateTab('history')">
                <History :size="17" />简历空间
              </button>
              <button :class="{ active: platform.activeTab === 'jobs' }" @click="navigateTab('jobs')">
                <BriefcaseBusiness :size="17" />岗位库
              </button>
              <button :class="{ active: platform.activeTab === 'tasks' }" @click="navigateTab('tasks')">
                <ClipboardList :size="17" />任务中心
              </button>
              <button :class="{ active: platform.activeTab === 'reports' }" @click="navigateTab('reports')">
                <Download :size="17" />报告中心
              </button>
              <button
                v-if="showResumeDetailNav"
                :class="{ active: platform.activeTab === 'result' }"
                @click="navigateTab('result')"
              >
                <FileText :size="17" />简历详情
              </button>
            </nav>
          </section>

          <section v-if="platform.isTeacherOrAdmin" class="sidebar-panel">
            <span class="sidebar-label">指导端</span>
            <nav class="side-nav">
              <button :class="{ active: platform.activeTab === 'teacher-dashboard' }" @click="navigateTab('teacher-dashboard')">
                <BarChart3 :size="17" />数据看板
              </button>
              <button :class="{ active: platform.activeTab === 'teacher-classes' }" @click="navigateTab('teacher-classes')">
                <GraduationCap :size="17" />班级分析
              </button>
              <button :class="{ active: platform.activeTab === 'teacher-records' }" @click="navigateTab('teacher-records')">
                <ClipboardList :size="17" />学生概览
              </button>
            </nav>
          </section>

          <section v-if="platform.isAdmin" class="sidebar-panel">
            <span class="sidebar-label">管理后台</span>
            <nav class="side-nav">
              <button :class="{ active: platform.activeTab === 'admin-users' }" @click="navigateTab('admin-users')">
                <UsersRound :size="17" />用户管理
              </button>
              <button :class="{ active: platform.activeTab === 'admin-jobs' }" @click="navigateTab('admin-jobs')">
                <BriefcaseBusiness :size="17" />岗位模板
              </button>
              <button :class="{ active: platform.activeTab === 'admin-system' }" @click="navigateTab('admin-system')">
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
        </div>

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
        <button
          v-if="platform.showBackButton"
          type="button"
          class="topbar-back-button"
          aria-label="返回上一页"
          @click="platform.goBack"
        >
          <ArrowLeft :size="17" />
          <span>返回</span>
        </button>
        <div class="workspace-topbar-copy">
          <div class="breadcrumb">{{ platform.breadcrumbLabel }}</div>
          <h2>{{ platform.pageTitle }}</h2>
          <p>{{ platform.pageSubtitle }}</p>
        </div>
      </header>

      <section class="workspace" :class="{ 'workspace--dashboard': route.name === 'dashboard' || route.name === 'login' || route.name === 'register' }">
        <div v-if="platform.error" class="alert alert-dismissible" role="alert">
          <span>{{ platform.error }}</span>
          <button type="button" class="alert-close" aria-label="关闭提示" @click="platform.clearError">
            <X :size="16" />
          </button>
        </div>
        <router-view v-slot="{ Component }">
          <Transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </section>
      <footer v-if="showHomeFooter" class="site-footer" aria-label="备案信息">
        <div class="site-footer-inner">
          <span>
            工信部备案号：
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
              陕ICP备2026002284号-3
            </a>
          </span>
          <span class="public-security-record">
            <img :src="beianBadge" alt="" aria-hidden="true" />
            <span>公安备案号：陕公网安备61012402000330号</span>
          </span>
        </div>
      </footer>
    </section>
  </main>
</template>
