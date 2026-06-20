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

import {
  analyzeResume,
  analyzeZip,
  createJobProfile,
  deleteAdminRecord,
  deleteHistory,
  deleteHistoryBulk,
  deleteJobProfile,
  fetchAdminAiConfig,
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
  fetchJobProfiles,
  fetchRecordVersions,
  fetchReports,
  fetchTasks,
  fetchTeacherStats,
  fetchUserProfile,
  fetchVersionCompare,
  importGuestHistory,
  loginUser,
  logoutUser,
  pauseBatchTask,
  registerUser,
  retryBatchTask,
  saveAdminAiConfig,
  sourceResumeUrl,
  updateJobProfile,
  updateAdminUserStatus,
  updateAdminUserRole,
  updateUserProfile,
  resetAdminUserPassword,
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
  const error = ref('')
  const healthStatus = ref(null)
  const result = ref(null)
  const batchResult = ref(null)
  const history = ref([])
  const tasks = ref([])
  const taskSummary = ref({ pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 })
  const reports = ref([])
  const jobProfiles = ref([])
  const jobsLoading = ref(false)
  const jobsMessage = ref('')
  const selectedJobProfileId = ref(0)
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
  const userProfile = ref({ school: '', major: '', grade: '', phone: '', bio: '' })
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
  const teacherStats = ref(null)
  const teacherLoading = ref(false)
  const teacherMessage = ref('')
  const recordVersions = ref([])
  const versionCompare = ref(null)
  const parentRecordId = ref(0)
  const parentRecordLabel = ref('')

  const tabRouteMap = {
    dashboard: { name: 'dashboard' },
    single: { name: 'workspace-analyze' },
    batch: { name: 'workspace-batch' },
    jobs: { name: 'workspace-jobs' },
    tasks: { name: 'workspace-tasks' },
    reports: { name: 'workspace-reports' },
    history: { name: 'workspace-resumes' },
    'admin-users': { name: 'admin-users' },
    'admin-jobs': { name: 'admin-jobs' },
    'admin-system': { name: 'admin-system' },
    'teacher-dashboard': { name: 'teacher-dashboard' },
  }

  const breadcrumbLabel = computed(() => {
    const labels = {
      dashboard: '平台工作台',
      single: '工作区 / 单份分析',
      batch: '工作区 / 批量分析',
      jobs: '工作区 / 岗位库',
      tasks: '工作区 / 任务中心',
      reports: '工作区 / 报告中心',
      result: '工作区 / 简历详情',
      history: '工作区 / 简历空间',
      'admin-users': '管理后台 / 用户管理',
      'admin-jobs': '管理后台 / 岗位模板',
      'admin-system': '管理后台 / 系统',
      'teacher-dashboard': '指导端 / 数据看板',
    }
    return labels[activeTab.value] || '平台工作台'
  })

  const pageTitle = computed(() => {
    const titles = {
      dashboard: '平台工作台',
      single: '单份简历分析',
      batch: '批量分析工作区',
      jobs: '岗位库',
      tasks: '分析任务中心',
      reports: '报告中心',
      result: '简历详情与评价报告',
      history: '简历工作台',
      'admin-users': '用户管理',
      'admin-jobs': '岗位模板管理',
      'admin-system': '系统管理',
      'teacher-dashboard': '指导数据看板',
    }
    return titles[activeTab.value] || '简历评价智能体'
  })

  const pageSubtitle = computed(() => {
    const subtitles = {
      dashboard: '概览简历资产、分析任务与报告，快速进入常用功能。',
      single: '上传简历并填写目标岗位，系统将生成结构化评价报告。',
      batch: '批量上传简历压缩包，后台自动逐份分析并汇总结果。',
      jobs: '管理常用岗位模板，在分析时一键套用 JD 与岗位要求。',
      tasks: '查看单份与批量分析任务的执行状态与进度。',
      reports: '集中下载已生成的 Word / PDF 评价报告。',
      result: '查看评分详情、岗位匹配度、诊断建议，并导出报告。',
      history: '管理已分析的简历记录，支持查看详情与批量清理。',
      'admin-users': '查看系统统计与用户账号，启用、禁用或重置密码。',
      'admin-jobs': '查看全平台岗位模板及归属用户。',
      'admin-system': '大模型配置、记录元数据与安全审计。',
      'teacher-dashboard': '按院校、专业、年级查看学生活跃度与评分分布。',
    }
    return subtitles[activeTab.value] || ''
  })

  const modeLabel = computed(() => (enableAi.value ? 'AI 智能分析' : '规则引擎分析'))
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
    if (!batchResult.value?.total_files) {
      return 0
    }
    return Math.min(100, Math.round((batchResult.value.processed_files || 0) / batchResult.value.total_files * 100))
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
  const selectedJobProfile = computed(() => jobProfiles.value.find((item) => item.id === selectedJobProfileId.value) || null)
  const jobProfileOptions = computed(() => jobProfiles.value.map((profile) => ({
    ...profile,
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

  const isAdminTab = (tab) => ['admin-users', 'admin-jobs', 'admin-system'].includes(tab)
  const isTeacherTab = (tab) => tab === 'teacher-dashboard'

  function routeToTab(currentRoute) {
    if (currentRoute.name === 'workspace-analyze') return 'single'
    if (currentRoute.name === 'workspace-batch') return 'batch'
    if (currentRoute.name === 'workspace-jobs') return 'jobs'
    if (currentRoute.name === 'workspace-tasks') return 'tasks'
    if (currentRoute.name === 'workspace-reports') return 'reports'
    if (currentRoute.name === 'workspace-resumes') return 'history'
    if (currentRoute.name === 'workspace-resume-detail') return 'result'
    if (currentRoute.name === 'admin-users') return 'admin-users'
    if (currentRoute.name === 'admin-jobs') return 'admin-jobs'
    if (currentRoute.name === 'admin-system') return 'admin-system'
    if (currentRoute.name === 'teacher-dashboard') return 'teacher-dashboard'
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

  function analysisModeLabel(mode) {
    const labels = {
      deepseek: 'DeepSeek 已使用',
      offline_fallback: 'DeepSeek 不可用，已回退离线规则分析',
      offline: '离线规则分析',
    }
    return labels[mode] || mode || '未知'
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

  function parseQualityTone(quality) {
    if (quality === 'high') return 'success'
    if (quality === 'low') return 'danger'
    return 'warning'
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

  function handleJobProfileChange() {
    applySelectedJobProfile(selectedJobProfile.value)
  }

  function syncTargetPositionFromResult(data, overwrite = false) {
    const nextTargetPosition = data?.target_position?.trim()
    if (!nextTargetPosition) {
      return
    }
    if (overwrite || !targetPosition.value.trim()) {
      targetPosition.value = nextTargetPosition
    }
  }

  async function setActiveTab(tab) {
    if (isAdminTab(tab) && !isAdmin.value) {
      return
    }
    if (isTeacherTab(tab) && !isTeacherOrAdmin.value) {
      return
    }
    error.value = ''
    if (tab === 'single' && !targetPosition.value.trim()) {
      syncTargetPositionFromResult(result.value, true)
    }
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
      userProfile.value = { school: '', major: '', grade: '', phone: '', bio: '' }
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
      userProfile.value = { school: '', major: '', grade: '', phone: '', bio: '' }
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
      const [records, auditLogs, aiConfig] = await Promise.all([
        fetchAdminRecords(),
        fetchAdminAuditLogs(),
        fetchAdminAiConfig(),
      ])
      adminRecords.value = records
      adminAuditLogs.value = auditLogs
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
      }
    } catch (err) {
      jobsMessage.value = err.message || '加载岗位库失败。'
    } finally {
      jobsLoading.value = false
    }
  }

  async function loadTasks() {
    try {
      const data = await fetchTasks()
      tasks.value = data.tasks || []
      taskSummary.value = data.summary || { pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 }
    } catch (err) {
      tasks.value = []
      taskSummary.value = { pending: 0, processing: 0, paused: 0, success: 0, failed: 0, partial_success: 0 }
      error.value = err.message || '加载任务列表失败。'
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
      selectedJobProfileId.value = profile.id
      applySelectedJobProfile(profile)
      resetJobProfileForm()
    } catch (err) {
      jobsMessage.value = err.message || '保存岗位模板失败。'
    } finally {
      jobsLoading.value = false
    }
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
      batchResult.value = await fetchBatchTask(batchTaskId)
      if (batchStatusDone(batchResult.value.status)) {
        stopBatchPolling()
        await loadHistory()
        await loadTasks()
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

  async function submitSingle() {
    if (!singleFile.value) {
      error.value = '请选择 .docx 或 .pdf 文件。'
      return
    }
    await runTask(async () => {
      result.value = await analyzeResume({
        file: singleFile.value,
        targetPosition: targetPosition.value,
        jobDescription: jobDescription.value,
        jobProfileId: selectedJobProfileId.value,
        enableAi: enableAi.value,
        parentRecordId: parentRecordId.value > 0 ? parentRecordId.value : undefined,
      })
      syncTargetPositionFromResult(result.value)
      clearNewVersion()
      await loadHistory()
      await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(result.value.record_id) } })
    })
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
    selectedJobProfileId.value = source.job_profile?.id || 0
    if (source.job_profile) {
      applySelectedJobProfile(source.job_profile)
    }
    await setActiveTab('single')
  }

  function clearNewVersion() {
    parentRecordId.value = 0
    parentRecordLabel.value = ''
  }

  async function submitZip() {
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
    try {
      history.value = await fetchHistory()
      const validIds = new Set(history.value.map((record) => record.record_id))
      selectedRecordIds.value = selectedRecordIds.value.filter((recordId) => validIds.has(recordId))
    } catch (err) {
      history.value = []
      clearHistorySelection()
      error.value = err.message || '加载简历历史失败。'
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
    result.value = null
    error.value = ''
    try {
      result.value = await fetchHistoryDetail(recordId)
      syncTargetPositionFromResult(result.value, true)
      await loadRecordVersions(recordId)
      if (route.name !== 'workspace-resume-detail') {
        await navigateToRoute({ name: 'workspace-resume-detail', params: { recordId: String(recordId) } })
      }
    } catch (err) {
      result.value = null
      recordVersions.value = []
      error.value = err.message || '加载简历详情失败。'
    } finally {
      detailLoading.value = false
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

    if (nextTab === 'single' && !targetPosition.value.trim()) {
      syncTargetPositionFromResult(result.value, true)
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
    if (nextTab === 'jobs') {
      await loadJobProfiles()
    }
    if (nextTab === 'tasks') {
      await loadTasks()
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
    if (route.name === 'workspace-resume-detail') {
      const recordId = Number(route.params.recordId || 0)
      if (recordId && recordId !== Number(result.value?.record_id || 0)) {
        await openRecordById(recordId)
      }
    }
  }

  let stopWatchers = null

  function initPlatform() {
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
      await Promise.all([loadHistory(), loadJobProfiles(), loadTasks(), loadReports()])
      await restoreActiveBatch()
      await syncRouteState()
    })()
  }

  function destroyPlatform() {
    stopBatchPolling()
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
    error,
    healthStatus,
    result,
    batchResult,
    history,
    tasks,
    taskSummary,
    reports,
    jobProfiles,
    jobsLoading,
    jobsMessage,
    selectedJobProfileId,
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
    teacherStats,
    teacherLoading,
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
    dashboardCards,
    latestTaskState,
    latestResumeRecord,
    setActiveTab,
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
    loadTasks,
    loadReports,
    loadHistory,
    loadAdminUsersData,
    loadAdminJobsList,
    loadAdminSystemData,
    loadAdminData,
    loadTeacherData,
    distributionWidth,
    submitJobProfile,
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
    formatDateTime,
    analysisModeLabel,
    targetSourceLabel,
    parseQualityLabel,
    parseQualityTone,
    resolvedSourceResumeUrl,
    batchStatusTone,
    submitSingle,
    startNewVersion,
    clearNewVersion,
    submitZip,
    pauseCurrentBatchTask,
    retryCurrentBatchTask,
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
