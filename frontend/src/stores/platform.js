import {
  Archive,
  BarChart3,
  BriefcaseBusiness,
  ClipboardList,
  Download,
  History,
} from 'lucide-vue-next'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { installRouteGuards } from '../router'
import {
  analyzeResume,
  analyzeZip,
  copyJobProfilePreset,
  createJobProfile,
  deleteAdminRecord,
  deleteHistory,
  deleteHistoryBulk,
  deleteJobProfile,
  fetchAdminAiConfig,
  fetchAdminScoreConfig,
  cleanupAdminStorage,
  teacherStatsExportUrl,
  saveAdminScoreConfig,
  fetchAdminAuditLogs,
  fetchAdminJobs,
  fetchAdminRecords,
  fetchAdminStats,
  fetchAdminUsers,
  fetchBatchTask,
  fetchCurrentUser,
  fetchHealth,
  fetchHistory,
  fetchHistoryDetail,
  fetchHistoryStatus,
  fetchJobProfiles,
  fetchJobProfilePresets,
  fetchRecordVersions,
  fetchReports,
  fetchTasks,
  fetchTeacherStats,
  fetchTeacherClasses,
  fetchTeacherRecords,
  fetchResumeTemplateCatalog,
  fetchUserProfile,
  fetchVersionCompare,
  importGuestHistory,
  loginUser,
  logoutUser,
  pauseBatchTask,
  registerUser,
  retryBatchTask,
  retryHistoryAnalysis,
  refreshInterviewPrep,
  refreshRewritePreview,
  rewriteReportUrl,
  saveAdminAiConfig,
  sourceResumeUrl,
  updateJobProfile,
  updateAdminUserStatus,
  updateAdminUserRole,
  updateUserProfile,
  resetAdminUserPassword,
  setUnauthorizedHandler,
  isBackendUnavailableText,
} from '../api/client'

let platformInstance = null

export function usePlatform() {
  if (!platformInstance) {
    const router = useRouter()
    const route = useRoute()
    platformInstance = createPlatformStore(router, route)
  }
  return platformInstance
}

function createPlatformStore(router, route) {
  const activeTab = ref('dashboard')
  const singleFile = ref(null)
  const zipFile = ref(null)
  const targetPosition = ref('')
  const jobDescription = ref('')
  const enableAi = ref(localStorage.getItem('enableAi') !== 'false')
  const loading = ref(false)
  const detailLoading = ref(false)
  const analysisPhase = ref(0)
  const analysisPhaseTimer = ref(null)
  const ANALYSIS_PHASES = [
    '正在提取简历正文与板块…',
    '正在计算六维评分…',
    '正在分析岗位匹配度…',
    '正在生成诊断与优化建议…',
  ]
  const interviewPrepLoading = ref(false)
  const rewritePreviewLoading = ref(false)
  const detailError = ref('')
  const error = ref('')
  const healthStatus = ref(null)
  const result = ref(null)
  const batchResult = ref(null)
  const history = ref([])
  const historyLoading = ref(false)
  const tasks = ref([])
  const taskSummary = ref({ pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 })
  const reports = ref([])
  const jobProfiles = ref([])
  const jobProfilePresets = ref([])
  const jobsLoading = ref(false)
  const jobsMessage = ref('')
  const selectedJobProfileId = ref(0)
  const selectedJobProfileKey = ref('0')
  const editingJobProfileId = ref(0)
  const jobProfileForm = ref({
    name: '',
    category: '',
    targetPosition: '',
    requirementSummary: '',
    description: '',
    status: 'active',
  })
  const batchPollingId = ref(null)
  const singlePollingId = ref(null)
  const tasksLoading = ref(false)
  const selectedRecordIds = ref([])
  const authPanelOpen = ref(false)
  const settingsPanelOpen = ref(false)
  const auth = ref({
    authenticated: false,
    user: null,
    mode: 'guest',
    guest_history_count: 0,
    wechat: { configured: false, enabled: false },
    platform: { allow_register: true, max_upload_size_mb: 20, max_zip_total_size_mb: 120 },
  })
  const authMode = ref('login')
  const authLoading = ref(false)
  const authMessage = ref('')
  const authForm = ref({
    username: '',
    displayName: '',
    password: '',
    confirmPassword: '',
  })
  const userProfile = ref({ school: '', major: '', grade: '', class_name: '', phone: '', bio: '' })
  const profileLoading = ref(false)
  const profileMessage = ref('')
  const adminStats = ref(null)
  const adminUsers = ref([])
  const adminJobs = ref([])
  const adminRecords = ref([])
  const adminAuditLogs = ref([])
  const adminLoading = ref(false)
  const adminMessage = ref('')
  const adminAiConfig = ref({
    provider: 'deepseek',
    api_url: '',
    model: '',
    api_key: '',
    clear_api_key: false,
    api_key_configured: false,
    api_key_masked: '',
    using_local_override: false,
    provider_options: [],
    model_suggestions: [],
  })
  const adminScoreConfig = ref({
    active_template: 'default',
    available_templates: [],
    templates: {},
    using_local_override: false,
  })
  const teacherStats = ref(null)
  const teacherClassPanel = ref(null)
  const teacherRecords = ref([])
  const teacherLoading = ref(false)
  const teacherClassLoading = ref(false)
  const teacherRecordsLoading = ref(false)
  const teacherMessage = ref('')
  const recordVersions = ref([])
  const versionCompare = ref(null)
  const parentRecordId = ref(0)
  const parentRecordLabel = ref('')

  const tabRouteMap = {
    dashboard: { name: 'dashboard' },
    single: { name: 'workspace-analyze' },
    batch: { name: 'workspace-batch' },
    interview: { name: 'workspace-interview' },
    jobs: { name: 'workspace-jobs' },
    tasks: { name: 'workspace-tasks' },
    reports: { name: 'workspace-reports' },
    history: { name: 'workspace-resumes' },
    'admin-users': { name: 'admin-users' },
    'admin-jobs': { name: 'admin-jobs' },
    'admin-system': { name: 'admin-system' },
    'teacher-dashboard': { name: 'teacher-dashboard' },
    'teacher-classes': { name: 'teacher-classes' },
    'teacher-records': { name: 'teacher-records' },
  }

  const breadcrumbLabel = computed(() => {
    const labels = {
      dashboard: '平台工作台',
      single: '工作区 / 单份分析',
      batch: '工作区 / 批量分析',
      interview: '工作区 / 面试训练',
      jobs: '工作区 / 岗位库',
      tasks: '工作区 / 任务中心',
      reports: '工作区 / 报告中心',
      result: '工作区 / 简历详情',
      history: '工作区 / 简历空间',
      'admin-users': '管理后台 / 用户管理',
      'admin-jobs': '管理后台 / 岗位模板',
      'admin-system': '管理后台 / 系统',
      'teacher-dashboard': '指导端 / 数据看板',
      'teacher-classes': '指导端 / 班级分析',
      'teacher-records': '指导端 / 学生概览',
    }
    return labels[activeTab.value] || '平台工作台'
  })

  const pageTitle = computed(() => {
    const titles = {
      dashboard: '平台工作台',
      single: '单份简历分析',
      batch: '批量分析工作区',
      interview: '面试训练',
      jobs: '岗位库',
      tasks: '分析任务中心',
      reports: '报告中心',
      result: '简历详情与评价报告',
      history: '简历工作台',
      'admin-users': '用户管理',
      'admin-jobs': '岗位模板管理',
      'admin-system': '系统管理',
      'teacher-dashboard': '指导数据看板',
      'teacher-classes': '班级分析面板',
      'teacher-records': '学生分析概览',
    }
    return titles[activeTab.value] || '简析智评'
  })

  const pageSubtitle = computed(() => {
    const subtitles = {
      dashboard: '概览简历资产、分析任务与报告，快速进入常用功能。',
      single: '上传简历并填写目标岗位，系统将生成结构化评价报告。',
      batch: '批量上传简历压缩包，后台自动逐份分析并汇总结果。',
      interview: '从已完成分析的简历中生成面试题与模拟训练，不占用简历分析流程。',
      jobs: '管理常用岗位模板，在分析时一键套用 JD 与岗位要求。',
      tasks: '查看单份与批量分析任务的执行状态与进度。',
      reports: '集中下载已生成的 Word / PDF 评价报告。',
      result: '查看评分详情、岗位匹配度、诊断建议，并导出报告。',
      history: '管理已分析的简历记录，支持查看详情与批量清理。',
      'admin-users': '查看系统统计与用户账号，启用、禁用或重置密码。',
      'admin-jobs': '查看全平台岗位模板及归属用户。',
      'admin-system': '大模型配置、记录元数据与安全审计。',
      'teacher-dashboard': '按院校、专业、年级查看学生活跃度与评分分布。',
      'teacher-classes': '按班级查看学生规模、均分与热门投递岗位。',
      'teacher-records': '查看学生分析元数据，不含简历正文。',
    }
    return subtitles[activeTab.value] || ''
  })

  const modeLabel = computed(() => (enableAi.value ? 'AI 深度优化' : '快速规则分析'))
  const historyCount = computed(() => history.value.length)
  const taskCount = computed(() => tasks.value.length)
  const reportCount = computed(() => reports.value.length)
  const jobProfileCount = computed(() => jobProfiles.value.length)
  const selectedHistoryCount = computed(() => selectedRecordIds.value.length)
  const allHistorySelected = computed(() => history.value.length > 0 && selectedRecordIds.value.length === history.value.length)
  const someHistorySelected = computed(() => selectedRecordIds.value.length > 0 && !allHistorySelected.value)
  const batchTaskRunning = computed(() => {
    if (['pending', 'processing'].includes(batchResult.value?.status || '')) {
      return true
    }
    return tasks.value.some(
      (task) => task.task_type === 'batch_analysis' && ['pending', 'processing'].includes(task.status),
    )
  })
  const batchTaskPaused = computed(() => batchResult.value?.status === 'paused')
  const batchTaskRetriable = computed(() => ['failed', 'paused'].includes(batchResult.value?.status || ''))
  const batchProgress = computed(() => {
    const batch = batchResult.value
    if (!batch) {
      return 0
    }
    const total = (batch.total_files || 0) + (batch.skipped_count || 0)
    if (!total) {
      return 0
    }
    return Math.min(100, Math.round((batch.processed_files || 0) / total * 100))
  })

  const currentIdentityLabel = computed(() => {
    if (auth.value.authenticated) {
      return auth.value.user?.display_name || auth.value.user?.username || '已登录用户'
    }
    return '访客模式'
  })

  const passwordChecks = computed(() => {
    const password = authForm.value.password
    return [
      { label: '至少 8 位', ok: password.length >= 8 },
      { label: '包含字母', ok: /[A-Za-z]/.test(password) },
      { label: '包含数字', ok: /\d/.test(password) },
      { label: '建议包含大小写和符号', ok: /[a-z]/.test(password) && /[A-Z]/.test(password) && /[^A-Za-z0-9]/.test(password) },
    ]
  })

  const passwordStrength = computed(() => {
    const password = authForm.value.password
    let score = 0
    if (password.length >= 8) score += 1
    if (/[A-Za-z]/.test(password)) score += 1
    if (/\d/.test(password)) score += 1
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
    if (/[^A-Za-z0-9]/.test(password)) score += 1
    if (score >= 5 && password.length >= 12) return { key: 'strong', label: '强' }
    if (score >= 3) return { key: 'medium', label: '中' }
    return { key: 'weak', label: '弱' }
  })

  const isAdmin = computed(() => auth.value.authenticated && auth.value.user?.role === 'admin')
  const isTeacher = computed(() => auth.value.authenticated && auth.value.user?.role === 'teacher')
  const isTeacherOrAdmin = computed(() => isAdmin.value || isTeacher.value)
  const allowRegister = computed(() => auth.value.platform?.allow_register !== false)
  const selectedJobProfile = computed(() => {
    if (selectedJobProfileKey.value.startsWith('preset:')) {
      const presetId = selectedJobProfileKey.value.slice('preset:'.length)
      return jobProfilePresets.value.find((item) => item.id === presetId) || null
    }
    return jobProfiles.value.find((item) => item.id === selectedJobProfileId.value) || null
  })
  const jobProfileOptions = computed(() => jobProfiles.value.map((profile) => ({
    ...profile,
    optionKey: `user:${profile.id}`,
    optionLabel: profile.category ? `${profile.name} / ${profile.category}` : profile.name,
  })))
  const jobProfilePresetOptions = computed(() => jobProfilePresets.value.map((profile) => ({
    ...profile,
    optionKey: `preset:${profile.id}`,
    optionLabel: profile.category ? `${profile.name} / ${profile.category}` : profile.name,
  })))
  const dashboardCards = computed(() => [
    { label: '简历资产', value: historyCount.value, hint: '已分析简历', tab: 'history', icon: History },
    { label: '岗位模板', value: jobProfileCount.value, hint: '可复用 JD', tab: 'jobs', icon: BriefcaseBusiness },
    { label: '分析任务', value: taskCount.value, hint: '进行中与已完成', tab: 'tasks', icon: ClipboardList },
    { label: '评价报告', value: reportCount.value, hint: '可下载导出', tab: 'reports', icon: Download },
  ])
  const latestTaskState = computed(() => {
    if (taskSummary.value.processing) return '有任务正在处理中'
    if (taskSummary.value.pending) return '有任务等待执行'
    if (taskSummary.value.failed) return '有任务执行失败，建议排查'
    return '当前任务中心运行稳定'
  })
  const latestResumeRecord = computed(() => history.value[0] || null)
  const showBackButton = computed(() => !['dashboard', 'login', 'register'].includes(route.name || ''))

  const isAdminTab = (tab) => ['admin-users', 'admin-jobs', 'admin-system'].includes(tab)
  const isTeacherTab = (tab) => ['teacher-dashboard', 'teacher-classes', 'teacher-records'].includes(tab)

  function routeToTab(currentRoute) {
    if (currentRoute.name === 'workspace-analyze') return 'single'
    if (currentRoute.name === 'workspace-batch') return 'batch'
    if (currentRoute.name === 'workspace-interview') return 'interview'
    if (currentRoute.name === 'workspace-jobs') return 'jobs'
    if (currentRoute.name === 'workspace-tasks') return 'tasks'
    if (currentRoute.name === 'workspace-reports') return 'reports'
    if (currentRoute.name === 'workspace-resumes') return 'history'
    if (currentRoute.name === 'workspace-resume-detail') return 'result'
    if (currentRoute.name === 'admin-users') return 'admin-users'
    if (currentRoute.name === 'admin-jobs') return 'admin-jobs'
    if (currentRoute.name === 'admin-system') return 'admin-system'
    if (currentRoute.name === 'teacher-dashboard') return 'teacher-dashboard'
    if (currentRoute.name === 'teacher-classes') return 'teacher-classes'
    if (currentRoute.name === 'teacher-records') return 'teacher-records'
    return 'dashboard'
  }

  function currentRouteTarget() {
    if (route.name === 'workspace-resume-detail' && result.value?.record_id) {
      return { name: 'workspace-resume-detail', params: { recordId: String(result.value.record_id) } }
    }
    if (route.name === 'login' || route.name === 'register') {
      return tabRouteMap.dashboard
    }
    return tabRouteMap[activeTab.value] || tabRouteMap.dashboard
  }

  async function navigateToRoute(target) {
    if (!target?.name) {
      return
    }
    const sameRoute = route.name === target.name && JSON.stringify(route.params || {}) === JSON.stringify(target.params || {})
    if (!sameRoute) {
      await router.push(target)
    }
  }

  function fallbackBackTarget() {
    const name = route.name
    if (name === 'workspace-resume-detail') {
      return tabRouteMap.history
    }
    if (name === 'teacher-classes' || name === 'teacher-records') {
      return tabRouteMap['teacher-dashboard']
    }
    if (name === 'admin-jobs' || name === 'admin-system') {
      return tabRouteMap['admin-users']
    }
    return tabRouteMap.dashboard
  }

  async function goBack() {
    error.value = ''
    const previousPath = window.history.state?.back
    if (previousPath && previousPath !== route.fullPath) {
      router.back()
      return
    }
    await navigateToRoute(fallbackBackTarget())
  }

  function analysisModeLabel(mode) {
    const labels = {
      ai_first: '快速规则分析',
      deepseek: 'AI 深度优化已完成',
      core: '快速规则分析',
      offline_fallback: '快速规则分析',
      offline: '快速规则分析',
    }
    return labels[mode] || mode || '未知'
  }

  function displayAnalysisModeLabel(payload) {
    if (!payload) {
      return '未知'
    }
    if (payload.ai_requested) {
      const status = payload.ai_enhancement_status || ''
      if (payload.analysis_mode === 'deepseek' || status === 'success') {
        return 'AI 深度优化已完成'
      }
      if (status === 'pending' || status === 'processing') {
        return 'AI 深度优化中'
      }
      return analysisModeLabel(payload.analysis_mode)
    }
    if (payload.analysis_mode_label && payload.analysis_mode_label !== 'AI 智能分析') {
      return payload.analysis_mode_label
    }
    return analysisModeLabel(payload.analysis_mode)
  }

  function displayAnalysisModeClass(payload) {
    if (!payload) {
      return 'offline'
    }
    if (payload.ai_requested) {
      const status = payload.ai_enhancement_status || ''
      if (payload.analysis_mode === 'deepseek' || status === 'success') {
        return 'deepseek'
      }
      if (status === 'pending' || status === 'processing') {
        return 'ai'
      }
      return payload.analysis_mode || 'offline'
    }
    return payload.analysis_mode || 'offline'
  }

  function shouldShowAiWorking(payload = result.value) {
    return Boolean(payload?.ai_requested) && ['pending', 'processing'].includes(payload?.ai_enhancement_status || '')
  }

  function targetSourceLabel(source) {
    const labels = {
      manual: '手动输入岗位',
      detected: '简历识别岗位',
      generic: '通用建议',
    }
    return labels[source] || '通用建议'
  }

  function parseQualityLabel(quality) {
    const labels = {
      high: '解析质量高',
      medium: '解析质量中',
      low: '解析质量低',
    }
    return labels[quality] || '解析质量未知'
  }

  const SECTION_LABELS = {
    basic_info: '个人信息',
    education: '教育背景',
    internship: '实习/工作经历',
    projects: '项目/实训经历',
    campus: '校园实践',
    skills: '技能证书',
    awards: '荣誉奖项',
    summary: '自我评价/求职意向',
  }

  function sectionLabel(key) {
    return SECTION_LABELS[key] || key || '其他'
  }

  function confidenceLabel(confidence) {
    const value = Number(confidence) || 0
    if (value >= 0.85) return '识别较完整'
    if (value >= 0.65) return '基本识别'
    return '识别偏弱'
  }

  function scoreGradeLabel(score) {
    const value = Number(score) || 0
    if (value >= 90) return '优秀'
    if (value >= 80) return '良好'
    if (value >= 70) return '中等'
    if (value >= 60) return '待提升'
    return '需加强'
  }

  function scoreGradeTone(score) {
    const value = Number(score) || 0
    if (value >= 85) return 'strong'
    if (value >= 70) return 'mid'
    return 'weak'
  }

  function matchRatePercent(result) {
    if (result?.match_rate != null) return Math.round(Number(result.match_rate))
    const matched = result?.matched_keywords?.length || 0
    const missing = result?.missing_keywords?.length || 0
    const total = matched + missing
    if (!total) return null
    return Math.round((matched / total) * 100)
  }

  function priorityLabel(priority) {
    const labels = {
      urgent: '紧急',
      high: '优先',
      medium: '建议',
    }
    return labels[priority] || '建议'
  }

  function buildActionRoadmapFallback(result) {
    if (result?.action_roadmap?.length) {
      return result.action_roadmap
    }
    const items = []
    if (result?.parse_quality === 'low') {
      items.push({
        priority: 'urgent',
        title: '修复文件解析',
        detail: '正文提取不足，请更换为可选中文本的 DOCX 或文字版 PDF 后重新分析。',
        action_tab: 'diagnosis',
      })
    }
    for (const item of (result?.structured_suggestions || []).slice(0, 2)) {
      if (!item?.problem) continue
      items.push({
        priority: 'high',
        title: item.problem,
        detail: item.direction || item.impact || '',
        action_tab: 'diagnosis',
      })
    }
    if (result?.missing_keywords?.length) {
      items.push({
        priority: 'medium',
        title: '补充岗位关键词',
        detail: `建议写入：${result.missing_keywords.slice(0, 5).join('、')}`,
        action_tab: 'match',
      })
    }
    return items.slice(0, 5)
  }

  function buildReportSummary(result) {
    if (!result?.scores) return ''
    const scoreEntries = Object.entries(result.scores)
      .filter(([key]) => key !== 'total_score')
      .map(([key, value]) => ({
        key,
        value: Number(value) || 0,
        label: {
          content_completeness: '内容完整性',
          experience_match: '经历相关性',
          language_professionalism: '语言专业性',
          format_standardization: '格式规范性',
          highlight_strength: '亮点量化程度',
          job_match: '岗位语义匹配',
        }[key] || key,
      }))
    if (!scoreEntries.length) return ''
    const sorted = [...scoreEntries].sort((a, b) => a.value - b.value)
    const weakest = sorted[0]
    const strongest = sorted[sorted.length - 1]
    const total = Number(result.total_score) || 0
    let tone = '整体表现良好'
    if (total < 70) tone = '仍有较大提升空间'
    else if (total < 85) tone = '基础扎实，可针对性优化'
    const diagnosisCount = (result.diagnosis?.length || 0) + (result.structured_suggestions?.length || 0)
    const parts = [
      `综合得分 ${total} 分，${tone}。`,
      `最强项为「${strongest.label}」（${strongest.value} 分），建议优先补强「${weakest.label}」（${weakest.value} 分）。`,
    ]
    if (diagnosisCount > 0) {
      parts.push(`系统识别出 ${diagnosisCount} 条可执行优化建议，详见「诊断与优化」分区。`)
    }
    if (result.parse_quality === 'low') {
      parts.push('正文提取偏弱，建议更换标准 DOCX/PDF 后重新分析。')
    }
    return parts.join('')
  }

  function parseQualityTone(quality) {
    if (quality === 'high') return 'success'
    if (quality === 'low') return 'danger'
    return 'warning'
  }

  function batchItemStatusLabel(status) {
    const labels = {
      success: '成功',
      failed: '失败',
      skipped: '跳过',
    }
    return labels[status] || status || '未知'
  }

  function batchItemStatusTone(status) {
    if (status === 'success') return 'success'
    if (status === 'failed') return 'danger'
    if (status === 'skipped') return 'warning'
    return 'processing'
  }

  function scoreReliabilityLabel(reliability) {
    const labels = {
      low_parse_capped: '低解析封顶',
      normal: '',
    }
    return labels[reliability] || ''
  }

  function rewriteModeLabel(mode) {
    const labels = {
      deepseek: 'AI 深度改写',
      offline_star: 'STAR 成稿参考',
      offline: '规则成稿参考',
    }
    return labels[mode] || '规则成稿参考'
  }

  function resolvedSourceResumeUrl(record) {
    if (!record?.record_id) {
      return ''
    }
    return record.source_resume_url || sourceResumeUrl(record.record_id)
  }

  function resetJobProfileForm() {
    editingJobProfileId.value = 0
    jobProfileForm.value = {
      name: '',
      category: '',
      targetPosition: '',
      requirementSummary: '',
      description: '',
      status: 'active',
    }
  }

  function populateJobProfileForm(profile) {
    editingJobProfileId.value = profile?.id || 0
    jobProfileForm.value = {
      name: profile?.name || '',
      category: profile?.category || '',
      targetPosition: profile?.target_position || '',
      requirementSummary: profile?.requirement_summary || '',
      description: profile?.description || '',
      status: profile?.status || 'active',
    }
  }

  function applySelectedJobProfile(profile) {
    if (!profile) {
      return
    }
    targetPosition.value = profile.target_position || profile.name || ''
    jobDescription.value = profile.requirement_summary || profile.description || ''
  }

  function setSelectedJobProfileKey(key) {
    const nextKey = String(key || '0')
    selectedJobProfileKey.value = nextKey
    if (nextKey.startsWith('user:')) {
      selectedJobProfileId.value = Number(nextKey.slice('user:'.length) || 0)
      return
    }
    selectedJobProfileId.value = 0
  }

  function handleJobProfileChange(key = selectedJobProfileKey.value) {
    setSelectedJobProfileKey(key)
    applySelectedJobProfile(selectedJobProfile.value)
  }

  async function setActiveTab(tab) {
    if (isAdminTab(tab) && !isAdmin.value) {
      return
    }
    if (isTeacherTab(tab) && !isTeacherOrAdmin.value) {
      return
    }
    error.value = ''
    if (tab === 'result') {
      const recordId = result.value?.record_id
      if (recordId) {
        await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(recordId) } })
      } else {
        await navigateToRoute(tabRouteMap.history)
      }
      return
    }
    await navigateToRoute(tabRouteMap[tab] || tabRouteMap.dashboard)
  }

  async function openAuthPanel(nextMode = 'login', syncRoute = true) {
    authMode.value = nextMode
    authMessage.value = ''
    authPanelOpen.value = true
    if (syncRoute) {
      await navigateToRoute({ name: nextMode === 'register' ? 'register' : 'login' })
    }
  }

  async function closeAuthPanel(syncRoute = true) {
    authPanelOpen.value = false
    if (syncRoute && (route.name === 'login' || route.name === 'register')) {
      await navigateToRoute(currentRouteTarget())
    }
  }

  async function openSettingsPanel() {
    settingsPanelOpen.value = true
    void loadHealthStatus()
    if (auth.value.authenticated) {
      void loadUserProfile()
    }
  }

  function closeSettingsPanel() {
    settingsPanelOpen.value = false
  }

  function clearHistorySelection() {
    selectedRecordIds.value = []
  }

  function syncResultAfterDeletion(deletedRecordIds) {
    if (deletedRecordIds.includes(result.value?.record_id)) {
      result.value = null
      void navigateToRoute(tabRouteMap.history)
    }
  }

  function toggleAllHistory(event) {
    if (event.target.checked) {
      selectedRecordIds.value = history.value.map((record) => record.record_id)
      return
    }
    clearHistorySelection()
  }

  async function loadAuth() {
    try {
      auth.value = await fetchCurrentUser()
    } catch (err) {
      auth.value = {
        authenticated: false,
        user: null,
        mode: 'guest',
        guest_history_count: 0,
        wechat: { configured: false, enabled: false },
        platform: { allow_register: true, max_upload_size_mb: 20, max_zip_total_size_mb: 120 },
      }
      error.value = err.message || '无法连接服务器，请确认后端已启动。'
    }
    if (!isAdmin.value && isAdminTab(activeTab.value)) {
      await navigateToRoute(tabRouteMap.dashboard)
    }
  }

  async function loadUserProfile() {
    if (!auth.value.authenticated) {
      userProfile.value = { school: '', major: '', grade: '', class_name: '', phone: '', bio: '' }
      return
    }
    profileLoading.value = true
    profileMessage.value = ''
    try {
      const data = await fetchUserProfile()
      userProfile.value = { ...data.profile }
    } catch (err) {
      profileMessage.value = err.message || '加载个人资料失败。'
    } finally {
      profileLoading.value = false
    }
  }

  async function submitUserProfile() {
    if (!auth.value.authenticated) {
      profileMessage.value = '请先登录后再更新资料。'
      return
    }
    profileLoading.value = true
    profileMessage.value = ''
    try {
      const data = await updateUserProfile({
        school: userProfile.value.school,
        major: userProfile.value.major,
        grade: userProfile.value.grade,
        class_name: userProfile.value.class_name,
        phone: userProfile.value.phone,
        bio: userProfile.value.bio,
      })
      userProfile.value = { ...data.profile }
      if (data.user) {
        auth.value = { ...auth.value, user: data.user }
      }
      profileMessage.value = '个人资料已保存。'
    } catch (err) {
      profileMessage.value = err.message || '保存个人资料失败。'
    } finally {
      profileLoading.value = false
    }
  }

  function resetAuthForm(keepUsername = false) {
    authForm.value = {
      username: keepUsername ? authForm.value.username : '',
      displayName: '',
      password: '',
      confirmPassword: '',
    }
  }

  async function submitAuth() {
    authLoading.value = true
    authMessage.value = ''
    error.value = ''
    try {
      if (authMode.value === 'register') {
        auth.value = await registerUser({
          username: authForm.value.username,
          display_name: authForm.value.displayName,
          password: authForm.value.password,
          confirm_password: authForm.value.confirmPassword,
        })
        authMessage.value = '注册成功，已自动登录。'
      } else {
        auth.value = await loginUser({
          username: authForm.value.username,
          password: authForm.value.password,
        })
        authMessage.value = '登录成功。'
      }
      resetAuthForm()
      clearHistorySelection()
      result.value = null
      await loadHistory()
      if (isAdmin.value) {
        await loadAdminUsersData()
      }
      await closeAuthPanel()
    } catch (err) {
      authMessage.value = err.message || '账号操作失败。'
    } finally {
      authLoading.value = false
    }
  }

  async function logout() {
    authLoading.value = true
    authMessage.value = ''
    try {
      await logoutUser()
      await loadAuth()
      clearHistorySelection()
      result.value = null
      userProfile.value = { school: '', major: '', grade: '', class_name: '', phone: '', bio: '' }
      await loadHistory()
      adminStats.value = null
      adminUsers.value = []
      adminJobs.value = []
      adminRecords.value = []
      adminAuditLogs.value = []
      adminAiConfig.value = {
        provider: 'deepseek',
        api_url: '',
        model: '',
        api_key: '',
        clear_api_key: false,
        api_key_configured: false,
        api_key_masked: '',
        using_local_override: false,
        provider_options: [],
        model_suggestions: [],
      }
      authMessage.value = '已退出登录，当前为游客模式。'
      if (isAdminTab(activeTab.value)) {
        await navigateToRoute(tabRouteMap.dashboard)
      }
    } catch (err) {
      authMessage.value = err.message || '退出失败。'
    } finally {
      authLoading.value = false
    }
  }

  async function importGuestRecords() {
    if (!auth.value.authenticated) {
      authMessage.value = '请先登录后再导入游客历史。'
      return
    }
    if (!window.confirm('确认将访客期间的分析记录导入到当前账号吗？')) {
      return
    }
    authLoading.value = true
    authMessage.value = ''
    try {
      const data = await importGuestHistory()
      await loadAuth()
      await loadHistory()
      authMessage.value = `已导入 ${data.imported_count || 0} 条游客历史。`
    } catch (err) {
      authMessage.value = err.message || '导入游客历史失败。'
    } finally {
      authLoading.value = false
    }
  }

  function onSingleFile(event) {
    singleFile.value = event.target.files?.[0] || null
    error.value = ''
  }

  function onDragOver(event) {
    event.preventDefault()
  }

  function onFileDrop(event, target) {
    event.preventDefault()
    const file = event.dataTransfer?.files?.[0]
    if (!file) {
      return
    }
    if (target === 'single') {
      singleFile.value = file
    } else {
      zipFile.value = file
    }
    error.value = ''
  }

  async function loadAdminUsersData() {
    if (!isAdmin.value) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const [stats, users] = await Promise.all([
        fetchAdminStats(),
        fetchAdminUsers(),
      ])
      adminStats.value = stats
      adminUsers.value = users
    } catch (err) {
      adminMessage.value = err.message || '加载用户管理数据失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function loadAdminJobsList() {
    if (!isAdmin.value) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      adminJobs.value = await fetchAdminJobs()
    } catch (err) {
      adminMessage.value = err.message || '加载岗位模板失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function loadAdminSystemData() {
    if (!isAdmin.value) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const [records, auditLogs, aiConfig, scoreConfig] = await Promise.all([
        fetchAdminRecords(),
        fetchAdminAuditLogs(),
        fetchAdminAiConfig(),
        fetchAdminScoreConfig(),
      ])
      adminRecords.value = records
      adminAuditLogs.value = auditLogs
      adminScoreConfig.value = scoreConfig
      adminAiConfig.value = {
        ...adminAiConfig.value,
        ...aiConfig,
        api_key: '',
        clear_api_key: false,
      }
    } catch (err) {
      adminMessage.value = err.message || '加载系统管理数据失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function loadAdminData() {
    await Promise.all([
      loadAdminUsersData(),
      loadAdminJobsList(),
      loadAdminSystemData(),
    ])
  }

  async function loadJobProfiles() {
    jobsLoading.value = true
    jobsMessage.value = ''
    try {
      jobProfiles.value = await fetchJobProfiles()
      if (selectedJobProfileId.value && !jobProfiles.value.some((item) => item.id === selectedJobProfileId.value)) {
        selectedJobProfileId.value = 0
        selectedJobProfileKey.value = '0'
      }
    } catch (err) {
      jobsMessage.value = err.message || '加载岗位库失败。'
    } finally {
      jobsLoading.value = false
    }
  }

  async function loadJobProfilePresets() {
    try {
      jobProfilePresets.value = await fetchJobProfilePresets()
      if (
        selectedJobProfileKey.value.startsWith('preset:')
        && !jobProfilePresets.value.some((item) => `preset:${item.id}` === selectedJobProfileKey.value)
      ) {
        setSelectedJobProfileKey('0')
      }
    } catch (err) {
      jobProfilePresets.value = []
      jobsMessage.value = err.message || '加载系统岗位模板失败。'
    }
  }

  async function loadJobProfileCatalog() {
    await Promise.all([loadJobProfiles(), loadJobProfilePresets()])
  }

  async function loadTasks() {
    tasksLoading.value = true
    try {
      const data = await fetchTasks()
      tasks.value = data.tasks || []
      taskSummary.value = data.summary || { pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 }
    } catch (err) {
      tasks.value = []
      taskSummary.value = { pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 }
      error.value = err.message || '加载任务列表失败。'
    } finally {
      tasksLoading.value = false
    }
  }

  async function loadReports() {
    try {
      reports.value = await fetchReports()
    } catch (err) {
      reports.value = []
      error.value = err.message || '加载报告列表失败。'
    }
  }

  async function restoreActiveBatch() {
    const active = tasks.value.find(
      (task) => task.task_type === 'batch_analysis' && ['pending', 'processing'].includes(task.status),
    )
    if (!active?.batch_task_id) {
      return
    }
    try {
      batchResult.value = await fetchBatchTask(active.batch_task_id)
      if (!batchStatusDone(batchResult.value.status)) {
        startBatchPolling(active.batch_task_id)
      }
    } catch {
      // ignore restore errors
    }
  }

  async function openTask(task) {
    if (task.task_type === 'batch_analysis' && task.batch_task_id) {
      await runTask(async () => {
        batchResult.value = await fetchBatchTask(task.batch_task_id)
        if (!batchStatusDone(batchResult.value.status)) {
          startBatchPolling(task.batch_task_id)
        }
        await navigateToRoute(tabRouteMap.batch)
      })
      return
    }
    if (task.record_id) {
      await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(task.record_id) } })
    }
  }

  async function openBatchResultRecord(item) {
    if (!item.record_id) {
      return
    }
    await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(item.record_id) } })
  }

  async function loadHealthStatus() {
    try {
      healthStatus.value = await fetchHealth()
      if (error.value && isBackendUnavailableText(error.value)) {
        error.value = ''
      }
    } catch {
      healthStatus.value = { status: 'error', database: 'error' }
    }
  }

  async function submitJobProfile() {
    jobsLoading.value = true
    jobsMessage.value = ''
    try {
      const payload = {
        name: jobProfileForm.value.name,
        category: jobProfileForm.value.category,
        target_position: jobProfileForm.value.targetPosition,
        requirement_summary: jobProfileForm.value.requirementSummary,
        description: jobProfileForm.value.description,
        status: jobProfileForm.value.status,
      }
      const profile = editingJobProfileId.value
        ? await updateJobProfile(editingJobProfileId.value, payload)
        : await createJobProfile(payload)
      jobsMessage.value = editingJobProfileId.value ? '岗位模板已更新。' : '岗位模板已创建。'
      await loadJobProfiles()
      setSelectedJobProfileKey(`user:${profile.id}`)
      applySelectedJobProfile(profile)
      resetJobProfileForm()
    } catch (err) {
      jobsMessage.value = err.message || '保存岗位模板失败。'
    } finally {
      jobsLoading.value = false
    }
  }

  async function savePresetToMyProfiles(preset) {
    if (!preset?.id) {
      return
    }
    jobsLoading.value = true
    jobsMessage.value = ''
    try {
      const payload = await copyJobProfilePreset(preset.id)
      const profile = payload.profile
      await loadJobProfiles()
      if (profile?.id) {
        setSelectedJobProfileKey(`user:${profile.id}`)
        applySelectedJobProfile(profile)
      }
      jobsMessage.value = payload.created ? '系统模板已保存到我的岗位库。' : '我的岗位库中已有该模板，已为你选中。'
    } catch (err) {
      jobsMessage.value = err.message || '保存系统模板失败。'
    } finally {
      jobsLoading.value = false
    }
  }

  async function usePresetForAnalysis(preset) {
    if (!preset?.id) {
      return
    }
    handleJobProfileChange(`preset:${preset.id}`)
    await navigateToRoute(tabRouteMap.single)
  }

  function editJobProfile(profile) {
    populateJobProfileForm(profile)
  }

  async function removeJobProfile(profile) {
    if (!window.confirm(`确认归档岗位模板「${profile.name}」吗？历史分析记录不会受影响。`)) {
      return
    }
    jobsLoading.value = true
    jobsMessage.value = ''
    try {
      await deleteJobProfile(profile.id)
      if (selectedJobProfileId.value === profile.id) {
        selectedJobProfileId.value = 0
        selectedJobProfileKey.value = '0'
      }
      if (editingJobProfileId.value === profile.id) {
        resetJobProfileForm()
      }
      await loadJobProfiles()
      jobsMessage.value = '岗位模板已归档。'
    } catch (err) {
      jobsMessage.value = err.message || '归档岗位模板失败。'
    } finally {
      jobsLoading.value = false
    }
  }

  async function changeUserRole(user, nextRole) {
    if (!window.confirm(`确认将账号 ${user.username} 的角色调整为「${roleLabel(nextRole)}」吗？`)) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      await updateAdminUserRole(user.id, { role: nextRole })
      await loadAdminUsersData()
      adminMessage.value = `账号 ${user.username} 的角色已更新为 ${roleLabel(nextRole)}。`
    } catch (err) {
      adminMessage.value = err.message || '更新用户角色失败。'
    } finally {
      adminLoading.value = false
    }
  }

  function roleLabel(role) {
    if (role === 'admin') return '管理员'
    if (role === 'teacher') return '教师'
    return '用户'
  }

  async function changeUserStatus(user, nextStatus) {
    if (!window.confirm(`确认将账号 ${user.username} ${nextStatus === 'disabled' ? '禁用' : '启用'}吗？`)) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      await updateAdminUserStatus(user.id, { status: nextStatus })
      await loadAdminUsersData()
      adminMessage.value = `账号 ${user.username} 已${nextStatus === 'disabled' ? '禁用' : '启用'}。`
    } catch (err) {
      adminMessage.value = err.message || '更新账号状态失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function resetUserPassword(user) {
    if (!window.confirm(`确认为账号 ${user.username} 生成临时密码吗？旧密码会立即失效。`)) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const data = await resetAdminUserPassword(user.id)
      await loadAdminUsersData()
      adminMessage.value = `账号 ${user.username} 的临时密码：${data.temporary_password}`
    } catch (err) {
      adminMessage.value = err.message || '重置密码失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function removeAdminRecord(record) {
    if (!window.confirm(`确认删除 ${record.username} 的记录「${record.filename}」吗？关联文件和报告也会同步清理。`)) {
      return
    }
    adminLoading.value = true
    adminMessage.value = ''
    try {
      await deleteAdminRecord(record.record_id)
      await loadAdminSystemData()
      await loadHistory()
      syncResultAfterDeletion([record.record_id])
      adminMessage.value = '记录已删除，并已写入审计日志。'
    } catch (err) {
      adminMessage.value = err.message || '无法删除用户记录，请检查关联数据后再试。'
    } finally {
      adminLoading.value = false
    }
  }

  async function saveScoreConfig() {
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const saved = await saveAdminScoreConfig({
        active_template: adminScoreConfig.value.active_template,
      })
      adminScoreConfig.value = { ...adminScoreConfig.value, ...saved }
      adminMessage.value = '评分权重模板已更新。'
    } catch (err) {
      adminMessage.value = err.message || '保存评分配置失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function cleanupStorage(dryRun = false) {
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const result = await cleanupAdminStorage({ dry_run: dryRun })
      adminMessage.value = dryRun
        ? `扫描 ${result.scanned} 个文件，预计可清理 ${result.removed} 个孤儿文件。`
        : `已清理 ${result.removed} 个无引用文件。`
    } catch (err) {
      adminMessage.value = err.message || '文件清理失败。'
    } finally {
      adminLoading.value = false
    }
  }

  async function saveAiConfig() {
    adminLoading.value = true
    adminMessage.value = ''
    try {
      const saved = await saveAdminAiConfig({
        provider: adminAiConfig.value.provider,
        api_url: adminAiConfig.value.api_url,
        model: adminAiConfig.value.model,
        api_key: adminAiConfig.value.api_key,
        clear_api_key: adminAiConfig.value.clear_api_key,
      })
      adminAiConfig.value = {
        ...adminAiConfig.value,
        ...saved,
        api_key: '',
        clear_api_key: false,
      }
      adminMessage.value = '大模型配置已保存，新的分析任务会使用最新设置。'
    } catch (err) {
      adminMessage.value = err.message || '保存大模型配置失败。'
    } finally {
      adminLoading.value = false
    }
  }

  function formatDateTime(value) {
    return value ? new Date(value).toLocaleString() : '--'
  }

  function onZipFile(event) {
    zipFile.value = event.target.files?.[0] || null
    error.value = ''
  }

  function stopBatchPolling() {
    if (batchPollingId.value) {
      window.clearInterval(batchPollingId.value)
      batchPollingId.value = null
    }
  }

  function stopSinglePolling() {
    if (singlePollingId.value) {
      window.clearInterval(singlePollingId.value)
      singlePollingId.value = null
    }
    if (analysisPhaseTimer.value) {
      window.clearInterval(analysisPhaseTimer.value)
      analysisPhaseTimer.value = null
    }
    analysisPhase.value = 0
  }

  function startAnalysisPhaseTimer() {
    analysisPhase.value = 0
    if (analysisPhaseTimer.value) {
      window.clearInterval(analysisPhaseTimer.value)
    }
    analysisPhaseTimer.value = window.setInterval(() => {
      analysisPhase.value = Math.min(analysisPhase.value + 1, ANALYSIS_PHASES.length - 1)
    }, 2800)
  }

  function analysisPhaseLabel() {
    return ANALYSIS_PHASES[analysisPhase.value] || ANALYSIS_PHASES[0]
  }

  async function copyText(text) {
    const value = String(text || '').trim()
    if (!value) {
      return false
    }
    try {
      await navigator.clipboard.writeText(value)
      return true
    } catch {
      return false
    }
  }

  function recordStatusDone(status) {
    return !['processing', 'pending'].includes(status)
  }

  function aiEnhancementPending(payload = result.value) {
    return shouldShowAiWorking(payload)
  }

  function startSinglePolling(recordId) {
    stopSinglePolling()
    startAnalysisPhaseTimer()
    singlePollingId.value = window.setInterval(async () => {
      try {
        const status = await fetchHistoryStatus(recordId)
        if (!recordStatusDone(status.status)) {
          if (result.value) {
            result.value = { ...result.value, ...status, status: status.status || 'processing' }
          }
          return
        }
        const detail = await fetchHistoryDetail(recordId)
        result.value = detail
        detailLoading.value = false
        detailError.value = ''
        await Promise.all([loadRecordVersions(recordId), loadHistory(), loadTasks()])
        if (aiEnhancementPending(detail)) {
          return
        }
        stopSinglePolling()
      } catch (err) {
        stopSinglePolling()
        detailLoading.value = false
        detailError.value = err.message || '分析任务刷新失败。'
      }
    }, 1500)
  }

  function batchStatusDone(status) {
    return ['success', 'partial_success', 'failed', 'paused'].includes(status)
  }

  function batchStatusTone(status) {
    if (status === 'success') {
      return 'success'
    }
    if (status === 'partial_success' || status === 'paused') {
      return 'warning'
    }
    if (status === 'failed') {
      return 'danger'
    }
    return 'processing'
  }

  async function refreshBatchTask(batchTaskId, quiet = false) {
    try {
      const includeResults = !quiet
      batchResult.value = await fetchBatchTask(batchTaskId, { includeResults })
      if (batchStatusDone(batchResult.value.status)) {
        stopBatchPolling()
        if (!includeResults) {
          batchResult.value = await fetchBatchTask(batchTaskId, { includeResults: true })
        }
        await Promise.all([loadHistory(), loadTasks()])
      }
    } catch (err) {
      if (!quiet) {
        error.value = err.message || '刷新批量任务失败。'
      }
    }
  }

  function startBatchPolling(batchTaskId) {
    stopBatchPolling()
    batchPollingId.value = window.setInterval(() => {
      if (document.hidden || !['batch', 'tasks'].includes(activeTab.value)) {
        return
      }
      refreshBatchTask(batchTaskId, true)
    }, 3000)
  }

  async function pauseCurrentBatchTask() {
    if (!batchResult.value?.batch_task_id || batchResult.value.status !== 'processing') {
      return
    }
    await runTask(async () => {
      batchResult.value = await pauseBatchTask(batchResult.value.batch_task_id)
      stopBatchPolling()
    })
  }

  async function retryCurrentBatchTask() {
    if (!batchResult.value?.batch_task_id || !batchTaskRetriable.value) {
      return
    }
    await runTask(async () => {
      batchResult.value = await retryBatchTask(batchResult.value.batch_task_id)
      if (!batchStatusDone(batchResult.value.status)) {
        startBatchPolling(batchResult.value.batch_task_id)
      }
      await loadTasks()
    })
  }

  function taskCanRetry(task) {
    if (!task) {
      return false
    }
    if (task.task_type === 'batch_analysis') {
      return ['failed', 'partial_success', 'paused'].includes(task.status)
    }
    return task.status === 'failed' && Boolean(task.record_id)
  }

  async function retryTask(task, event) {
    event?.stopPropagation?.()
    if (!taskCanRetry(task)) {
      return
    }
    await runTask(async () => {
      if (task.task_type === 'batch_analysis' && task.batch_task_id) {
        batchResult.value = await retryBatchTask(task.batch_task_id)
        if (!batchStatusDone(batchResult.value.status)) {
          startBatchPolling(task.batch_task_id)
        }
      } else if (task.record_id) {
        await retryHistoryAnalysis(task.record_id)
      }
      await loadTasks()
    })
  }

  function clearError() {
    error.value = ''
  }

  async function submitSingle() {
    if (loading.value) {
      return
    }
    if (!singleFile.value) {
      error.value = '请选择 .docx 或 .pdf 文件。'
      return
    }
    await runTask(async () => {
      const payload = await analyzeResume({
        file: singleFile.value,
        targetPosition: targetPosition.value,
        jobDescription: jobDescription.value,
        jobProfileId: selectedJobProfileId.value,
        enableAi: enableAi.value,
        parentRecordId: parentRecordId.value > 0 ? parentRecordId.value : undefined,
      })
      const wasNewVersion = parentRecordId.value > 0
      const usedJobProfile = selectedJobProfileId.value > 0
      clearNewVersion()
      if (!wasNewVersion && !usedJobProfile) {
        targetPosition.value = ''
        jobDescription.value = ''
      }
      singleFile.value = null
      await loadHistory()
      await loadTasks()
      await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(payload.record_id) } })
      if (payload.status === 'processing') {
        result.value = payload
        detailLoading.value = true
        startSinglePolling(payload.record_id)
      } else {
        result.value = payload
      }
    })
  }

  async function retryFailedRecord(record) {
    if (!record?.record_id) {
      return
    }
    await runTask(async () => {
      const payload = await retryHistoryAnalysis(record.record_id)
      await loadHistory()
      await loadTasks()
      result.value = payload
      detailLoading.value = true
      startSinglePolling(record.record_id)
    })
  }

  async function refreshInterviewPrepForRecord(enableAi = false) {
    if (!result.value?.record_id || result.value.status !== 'success') {
      return
    }
    interviewPrepLoading.value = true
    try {
      const payload = await refreshInterviewPrep(result.value.record_id, enableAi)
      if (result.value) {
        result.value = {
          ...result.value,
          interview_prep: payload.interview_prep || payload,
          mock_interview: payload.mock_interview || result.value.mock_interview,
        }
      }
    } catch (err) {
      error.value = err.message || '面试题生成失败。'
    } finally {
      interviewPrepLoading.value = false
    }
  }

  async function refreshRewritePreviewForRecord(enableAi = false) {
    if (!result.value?.record_id || result.value.status !== 'success') {
      return
    }
    rewritePreviewLoading.value = true
    try {
      const payload = await refreshRewritePreview(result.value.record_id, enableAi)
      if (result.value && payload.rewrite_preview) {
        result.value = {
          ...result.value,
          rewrite_preview: payload.rewrite_preview,
          template_recommendations: payload.template_recommendations || result.value.template_recommendations,
        }
      }
    } catch (err) {
      error.value = err.message || '深度改写生成失败。'
    } finally {
      rewritePreviewLoading.value = false
    }
  }

  async function startNewVersion(record) {
    if (!record?.record_id) {
      return
    }
    let source = record
    if (!record.job_description) {
      try {
        source = await fetchHistoryDetail(record.record_id)
      } catch {
        source = record
      }
    }
    parentRecordId.value = source.record_id
    parentRecordLabel.value = `${source.filename || '简历'} · v${source.version_no || 1}`
    targetPosition.value = source.target_position || ''
    jobDescription.value = source.job_description || ''
    if (source.job_profile?.id) {
      setSelectedJobProfileKey(`user:${source.job_profile.id}`)
      applySelectedJobProfile(source.job_profile)
    } else {
      setSelectedJobProfileKey('0')
    }
    await navigateToRoute({
      name: 'workspace-analyze',
      query: { parentRecordId: String(source.record_id) },
    })
  }

  function clearNewVersion() {
    parentRecordId.value = 0
    parentRecordLabel.value = ''
  }

  async function submitZip() {
    if (loading.value) {
      return
    }
    if (batchTaskRunning.value) {
      error.value = '当前已有批量任务正在处理中，请等待本次任务完成后再提交新的 ZIP。'
      return
    }
    if (!zipFile.value) {
      error.value = '请选择 .zip 文件。'
      return
    }
    await runTask(async () => {
      batchResult.value = await analyzeZip({
        file: zipFile.value,
        targetPosition: targetPosition.value,
        jobDescription: jobDescription.value,
        jobProfileId: selectedJobProfileId.value,
        enableAi: enableAi.value,
      })
      if (batchResult.value.reused) {
        error.value = '已有批量任务正在处理，已恢复显示当前任务进度。'
      }
      if (!batchStatusDone(batchResult.value.status)) {
        startBatchPolling(batchResult.value.batch_task_id)
      }
      await navigateToRoute(tabRouteMap.batch)
    })
  }

  async function runTask(task) {
    loading.value = true
    error.value = ''
    try {
      await task()
    } catch (err) {
      error.value = err.message || '操作失败。'
    } finally {
      loading.value = false
    }
  }

  async function loadHistory() {
    historyLoading.value = true
    try {
      history.value = await fetchHistory({ includeTotal: false })
      const validIds = new Set(history.value.map((record) => record.record_id))
      selectedRecordIds.value = selectedRecordIds.value.filter((recordId) => validIds.has(recordId))
    } catch (err) {
      history.value = []
      clearHistorySelection()
      error.value = err.message || '加载简历历史失败。'
    } finally {
      historyLoading.value = false
    }
  }

  async function loadTeacherRecords() {
    if (!isTeacherOrAdmin.value) {
      return
    }
    teacherRecordsLoading.value = true
    try {
      const data = await fetchTeacherRecords()
      teacherRecords.value = data.items || []
    } catch (err) {
      teacherMessage.value = err.message || '加载学生记录失败。'
    } finally {
      teacherRecordsLoading.value = false
    }
  }

  async function loadTeacherClassData() {
    if (!isTeacherOrAdmin.value) {
      return
    }
    teacherClassLoading.value = true
    teacherMessage.value = ''
    try {
      teacherClassPanel.value = await fetchTeacherClasses()
    } catch (err) {
      teacherMessage.value = err.message || '加载班级数据失败。'
    } finally {
      teacherClassLoading.value = false
    }
  }

  async function loadTeacherData() {
    if (!isTeacherOrAdmin.value) {
      return
    }
    teacherLoading.value = true
    teacherMessage.value = ''
    try {
      teacherStats.value = await fetchTeacherStats()
    } catch (err) {
      teacherMessage.value = err.message || '加载指导数据失败。'
    } finally {
      teacherLoading.value = false
    }
  }

  function distributionWidth(count, mode = 'score') {
    const values = mode === 'daily'
      ? (teacherStats.value?.daily_volume || []).map((item) => item.count)
      : (teacherStats.value?.score_distribution || []).map((item) => item.count)
    const max = Math.max(...values, 1)
    return `${Math.round((count / max) * 100)}%`
  }

  async function loadRecordVersions(recordId) {
    if (!recordId) {
      recordVersions.value = []
      versionCompare.value = null
      return
    }
    try {
      const data = await fetchRecordVersions(recordId)
      recordVersions.value = data.versions || []
      await loadVersionCompare(recordId)
    } catch {
      recordVersions.value = []
      versionCompare.value = null
    }
  }

  async function loadVersionCompare(recordId) {
    const versions = recordVersions.value
    if (versions.length < 2) {
      versionCompare.value = null
      return
    }
    const current = versions.find((item) => item.record_id === recordId) || versions[versions.length - 1]
    const previous = versions.filter((item) => item.version_no < current.version_no).at(-1)
    if (!previous) {
      versionCompare.value = null
      return
    }
    try {
      versionCompare.value = await fetchVersionCompare(previous.record_id, current.record_id)
    } catch {
      versionCompare.value = null
    }
  }

  async function openRecordById(recordId) {
    detailLoading.value = true
    detailError.value = ''
    stopSinglePolling()
    try {
      const detail = await fetchHistoryDetail(recordId)
      if (detail.status === 'processing') {
        result.value = detail
        startSinglePolling(recordId)
        if (route.name !== 'workspace-resume-detail') {
          await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(recordId) } })
        }
        return
      }
      result.value = detail
      await loadRecordVersions(recordId)
      if (route.name !== 'workspace-resume-detail') {
        await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(recordId) } })
      }
    } catch (err) {
      result.value = null
      recordVersions.value = []
      detailError.value = err.message || '加载简历详情失败。'
    } finally {
      if (!singlePollingId.value) {
        detailLoading.value = false
      }
    }
  }

  async function openRecord(record) {
    await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(record.record_id) } })
  }

  async function removeRecord(record) {
    await runTask(async () => {
      await deleteHistory(record.record_id)
      syncResultAfterDeletion([record.record_id])
      clearHistorySelection()
      await loadHistory()
    })
  }

  async function removeSelectedRecords() {
    if (!selectedHistoryCount.value) {
      return
    }
    if (!window.confirm(`确认删除已选中的 ${selectedHistoryCount.value} 条历史记录吗？相关文件和报告也会一起删除。`)) {
      return
    }
    await runTask(async () => {
      const deletedRecordIds = [...selectedRecordIds.value]
      await deleteHistoryBulk({
        record_ids: deletedRecordIds,
        delete_all: false,
      })
      syncResultAfterDeletion(deletedRecordIds)
      clearHistorySelection()
      await loadHistory()
    })
  }

  async function clearAllHistory() {
    if (!history.value.length) {
      return
    }
    if (!window.confirm('确认清空全部历史记录吗？此操作会删除所有本地历史记录、原始文件和报告文件，且无法撤销。')) {
      return
    }
    await runTask(async () => {
      const deletedRecordIds = history.value.map((record) => record.record_id)
      await deleteHistoryBulk({
        record_ids: [],
        delete_all: true,
      })
      syncResultAfterDeletion(deletedRecordIds)
      clearHistorySelection()
      await loadHistory()
    })
  }

  async function syncRouteState() {
    const nextTab = routeToTab(route)
    if (isAdminTab(nextTab) && !isAdmin.value) {
      await navigateToRoute(tabRouteMap.dashboard)
      return
    }
    if (isTeacherTab(nextTab) && !isTeacherOrAdmin.value) {
      await navigateToRoute(tabRouteMap.dashboard)
      return
    }
    activeTab.value = nextTab
    error.value = ''

    if (route.name === 'login' || route.name === 'register') {
      if (route.name === 'register' && !allowRegister.value) {
        await navigateToRoute({ name: 'login' })
        await openAuthPanel('login', false)
        return
      }
      await openAuthPanel(route.name === 'register' ? 'register' : 'login', false)
    } else if (authPanelOpen.value) {
      await closeAuthPanel(false)
    }

    if (nextTab === 'single' && route.query.parentRecordId) {
      const parentId = Number(route.query.parentRecordId || 0)
      if (parentId > 0 && parentId !== parentRecordId.value) {
        const parent = history.value.find((item) => item.record_id === parentId)
        if (parent) {
          startNewVersion(parent)
        }
      }
    }
    if (nextTab !== 'single' && parentRecordId.value) {
      clearNewVersion()
    }
    if (nextTab === 'dashboard' && auth.value.authenticated) {
      await loadUserProfile()
    }
    if (nextTab === 'jobs') {
      await loadJobProfileCatalog()
    }
    if (nextTab === 'single' || nextTab === 'batch') {
      await loadJobProfileCatalog()
    }
    if (nextTab === 'tasks') {
      await loadTasks()
    }
    if (nextTab === 'interview') {
      await loadHistory()
    }
    if (nextTab === 'reports') {
      await loadReports()
    }
    if (nextTab === 'admin-users') {
      await loadAdminUsersData()
    }
    if (nextTab === 'admin-jobs') {
      await loadAdminJobsList()
    }
    if (nextTab === 'admin-system') {
      await loadAdminSystemData()
    }
    if (nextTab === 'teacher-dashboard') {
      await loadTeacherData()
    }
    if (nextTab === 'teacher-classes') {
      await loadTeacherClassData()
    }
    if (nextTab === 'teacher-records') {
      await loadTeacherRecords()
    }
    if (route.name === 'workspace-resume-detail') {
      const recordId = Number(route.params.recordId || 0)
      if (recordId && recordId !== Number(result.value?.record_id || 0)) {
        await openRecordById(recordId)
      }
    }
  }

  let stopWatchers = null

  let routeGuardsInstalled = false

  function initPlatform() {
    if (!routeGuardsInstalled) {
      installRouteGuards(usePlatform)
      routeGuardsInstalled = true
    }
    setUnauthorizedHandler(() => {
      void openAuthPanel('login', false)
    })

    watch(enableAi, (value) => {
      localStorage.setItem('enableAi', String(value))
    })

    const stopRouteWatch = watch(
      () => [route.name, route.params.recordId, isAdmin.value, isTeacherOrAdmin.value],
      () => {
        void syncRouteState()
      },
    )

    stopWatchers = () => {
      stopRouteWatch()
    }

    void (async () => {
      await loadAuth()
      await loadHistory()
      await loadHealthStatus()
      await restoreActiveBatch()
      await syncRouteState()
    })()
  }

  function destroyPlatform() {
    stopBatchPolling()
    stopSinglePolling()
    if (stopWatchers) {
      stopWatchers()
      stopWatchers = null
    }
  }

  return reactive({
    activeTab,
    singleFile,
    zipFile,
    targetPosition,
    jobDescription,
    enableAi,
    loading,
    detailLoading,
    analysisPhase,
    analysisPhaseLabel,
    copyText,
    interviewPrepLoading,
    rewritePreviewLoading,
    detailError,
    error,
    healthStatus,
    result,
    batchResult,
    history,
    historyLoading,
    tasks,
    tasksLoading,
    taskSummary,
    reports,
    jobProfiles,
    jobProfilePresets,
    jobsLoading,
    jobsMessage,
    selectedJobProfileId,
    selectedJobProfileKey,
    editingJobProfileId,
    jobProfileForm,
    selectedRecordIds,
    authPanelOpen,
    settingsPanelOpen,
    auth,
    authMode,
    authLoading,
    authMessage,
    authForm,
    userProfile,
    profileLoading,
    profileMessage,
    adminStats,
    adminUsers,
    adminJobs,
    adminRecords,
    adminAuditLogs,
    adminLoading,
    adminMessage,
    adminAiConfig,
    adminScoreConfig,
    teacherStats,
    teacherClassPanel,
    teacherRecords,
    teacherLoading,
    teacherClassLoading,
    teacherRecordsLoading,
    teacherMessage,
    recordVersions,
    versionCompare,
    parentRecordId,
    parentRecordLabel,
    breadcrumbLabel,
    pageTitle,
    pageSubtitle,
    modeLabel,
    historyCount,
    taskCount,
    reportCount,
    jobProfileCount,
    selectedHistoryCount,
    allHistorySelected,
    someHistorySelected,
    batchTaskRunning,
    batchTaskPaused,
    batchTaskRetriable,
    batchProgress,
    currentIdentityLabel,
    passwordChecks,
    passwordStrength,
    isAdmin,
    isTeacher,
    isTeacherOrAdmin,
    allowRegister,
    selectedJobProfile,
    jobProfileOptions,
    jobProfilePresetOptions,
    dashboardCards,
    latestTaskState,
    latestResumeRecord,
    showBackButton,
    setActiveTab,
    goBack,
    openAuthPanel,
    closeAuthPanel,
    openSettingsPanel,
    closeSettingsPanel,
    toggleAllHistory,
    submitAuth,
    logout,
    importGuestRecords,
    resetAuthForm,
    onSingleFile,
    onDragOver,
    onFileDrop,
    onZipFile,
    loadUserProfile,
    submitUserProfile,
    loadJobProfiles,
    loadJobProfilePresets,
    loadJobProfileCatalog,
    loadTasks,
    loadReports,
    loadHistory,
    loadAdminUsersData,
    loadAdminJobsList,
    loadAdminSystemData,
    loadAdminData,
    loadTeacherData,
    loadTeacherClassData,
    loadTeacherRecords,
    distributionWidth,
    submitJobProfile,
    savePresetToMyProfiles,
    usePresetForAnalysis,
    editJobProfile,
    removeJobProfile,
    handleJobProfileChange,
    applySelectedJobProfile,
    resetJobProfileForm,
    changeUserStatus,
    changeUserRole,
    roleLabel,
    resetUserPassword,
    removeAdminRecord,
    saveAiConfig,
    saveScoreConfig,
    cleanupStorage,
    formatDateTime,
    analysisModeLabel,
    displayAnalysisModeLabel,
    displayAnalysisModeClass,
    targetSourceLabel,
    parseQualityLabel,
    parseQualityTone,
    sectionLabel,
    confidenceLabel,
    buildReportSummary,
    scoreGradeLabel,
    scoreGradeTone,
    matchRatePercent,
    priorityLabel,
    buildActionRoadmapFallback,
    batchItemStatusLabel,
    batchItemStatusTone,
    scoreReliabilityLabel,
    aiEnhancementPending,
    rewriteModeLabel,
    resolvedSourceResumeUrl,
    batchStatusTone,
    submitSingle,
    startNewVersion,
    clearNewVersion,
    submitZip,
    pauseCurrentBatchTask,
    retryCurrentBatchTask,
    retryFailedRecord,
    retryTask,
    taskCanRetry,
    clearError,
    refreshInterviewPrepForRecord,
    refreshRewritePreviewForRecord,
    refreshBatchTask,
    openTask,
    openBatchResultRecord,
    openRecord,
    openRecordById,
    removeRecord,
    removeSelectedRecords,
    clearAllHistory,
    clearHistorySelection,
    initPlatform,
    destroyPlatform,
  })
}
