const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const DEFAULT_TIMEOUT_MS = 120_000
const BACKEND_UNAVAILABLE_MESSAGE = '前端无法连接后端，请检查后端是否启动或代理端口是否正确。'

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

function normalizeDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || String(item)).join('；')
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  return detail
}

export function isBackendUnavailableText(text) {
  return /ECONNREFUSED|ECONNRESET|proxy error|connect .*127\.0\.0\.1:(8000|8001)|Failed to fetch|NetworkError|前端无法连接后端|后端无法连接|后端未启动|端口配置不一致|代理端口|无法连接服务器|请使用 start_backend\.bat|请使用 start_dev\.bat/i.test(text || '')
}

function parseJsonSafely(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize)
    binary += String.fromCharCode(...chunk)
  }
  return window.btoa(binary)
}

async function fileToBase64(file) {
  const buffer = await file.arrayBuffer()
  return arrayBufferToBase64(buffer)
}

async function request(path, options = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      signal: controller.signal,
      ...fetchOptions,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试。')
    }
    if (isBackendUnavailableText(err?.message)) {
      throw new Error(BACKEND_UNAVAILABLE_MESSAGE)
    }
    throw new Error(BACKEND_UNAVAILABLE_MESSAGE)
  } finally {
    window.clearTimeout(timer)
  }

  if (response.status === 401 && unauthorizedHandler) {
    unauthorizedHandler()
  }

  if (!response.ok) {
    let message = response.status === 413
      ? '上传文件过大：请压缩文件、减少 ZIP 内简历数量，或在配置中调大上传限制。'
      : response.status === 504
        ? '批量分析等待超时：请稍后刷新历史记录查看已完成结果，或减少 ZIP 内简历数量后重试。'
        : response.status >= 500
          ? '服务器处理失败，请稍后再试。'
          : `请求失败：${response.status}`
    let responseText = ''
    try {
      responseText = await response.text()
    } catch {
      responseText = ''
    }
    if (response.status >= 500 && isBackendUnavailableText(responseText)) {
      message = BACKEND_UNAVAILABLE_MESSAGE
    } else {
      const body = parseJsonSafely(responseText)
      message = normalizeDetail(body?.detail) || message
    }
    throw new Error(message)
  }
  return response.json()
}

export async function fetchCurrentUser() {
  return request('/auth/me')
}

export async function fetchHealth() {
  return request('/health', { timeoutMs: 8000 })
}

export async function registerUser(payload) {
  return request('/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function loginUser(payload) {
  return request('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function logoutUser() {
  return request('/auth/logout', { method: 'POST' })
}

export async function importGuestHistory() {
  return request('/auth/import-guest-history', { method: 'POST' })
}

export async function analyzeResume(payload) {
  return request('/resumes/analyze-direct', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: payload.file.name,
      content_base64: await fileToBase64(payload.file),
      target_position: payload.targetPosition || '',
      job_description: payload.jobDescription || '',
      job_profile_id: Number(payload.jobProfileId || 0),
      target_match_enabled: Boolean(payload.targetMatchEnabled),
      enable_ai: Boolean(payload.enableAi),
      parent_record_id: payload.parentRecordId ? Number(payload.parentRecordId) : 0,
      stream: payload.stream !== false,
    }),
    timeoutMs: 180_000,
  })
}

export async function analyzeZip(payload) {
  const form = new FormData()
  form.append('file', payload.file)
  form.append('target_position', payload.targetPosition || '')
  form.append('job_description', payload.jobDescription || '')
  form.append('job_profile_id', String(payload.jobProfileId || 0))
  form.append('target_match_enabled', String(Boolean(payload.targetMatchEnabled)))
  form.append('enable_ai', String(Boolean(payload.enableAi)))
  return request('/resumes/analyze-zip', { method: 'POST', body: form, timeoutMs: 180_000 })
}

export async function fetchJobProfiles() {
  return request('/job-profiles')
}

export async function fetchJobProfilePresets() {
  return request('/job-profile-presets')
}

export async function fetchJobMarket(params = {}) {
  const query = new URLSearchParams()
  if (params.city) query.set('city', params.city)
  if (params.category) query.set('category', params.category)
  if (params.education) query.set('education', params.education)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/job-market${suffix}`)
}

export async function copyJobProfilePreset(id) {
  return request(`/job-profile-presets/${encodeURIComponent(id)}/copy`, { method: 'POST' })
}

export async function createJobProfile(payload) {
  return request('/job-profiles', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function updateJobProfile(id, payload) {
  return request(`/job-profiles/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function deleteJobProfile(id) {
  return request(`/job-profiles/${id}`, { method: 'DELETE' })
}

export async function fetchBatchTask(id, { includeResults = true } = {}) {
  const query = includeResults ? '' : '?include_results=false'
  return request(`/batch-tasks/${id}${query}`)
}

export async function pauseBatchTask(id) {
  return request(`/batch-tasks/${id}/pause`, { method: 'POST' })
}

export async function fetchHistory(params = {}) {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.includeTotal === false) query.set('include_total', 'false')
  const suffix = query.toString() ? `?${query.toString()}` : ''
  const data = await request(`/history${suffix}`)
  if (Array.isArray(data)) {
    return data
  }
  return data.items || []
}

export async function fetchHistoryStatus(id) {
  return request(`/history/${id}/status`, { timeoutMs: 8000 })
}

export async function fetchHistoryDetail(id) {
  return request(`/history/${id}`)
}

export async function fetchRecordVersions(id) {
  return request(`/history/${id}/versions`)
}

export async function fetchVersionCompare(a, b) {
  return request(`/history/compare?a=${a}&b=${b}`)
}

export async function fetchTeacherStats() {
  return request('/teacher/stats')
}

export async function fetchTeacherClasses() {
  return request('/teacher/classes')
}

export async function createTeacherTrainingTask(payload) {
  return request('/teacher/training-tasks', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchTeacherRecords() {
  return request('/teacher/records')
}

export async function fetchResumeTemplateCatalog() {
  return request('/resume-templates/catalog')
}

export async function fetchTasks() {
  return request('/tasks')
}

export async function fetchReports() {
  return request('/reports')
}

export async function deleteHistory(id) {
  return request(`/history/${id}`, { method: 'DELETE' })
}

export async function deleteHistoryBulk(payload) {
  return request('/history/bulk-delete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchAdminStats() {
  return request('/admin/stats')
}

export async function fetchAdminUsers() {
  return request('/admin/users')
}

export async function updateAdminUserStatus(id, payload) {
  return request(`/admin/users/${id}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function updateAdminUserRole(id, payload) {
  return request(`/admin/users/${id}/role`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function resetAdminUserPassword(id, payload = {}) {
  return request(`/admin/users/${id}/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchAdminRecords() {
  return request('/admin/records')
}

export async function deleteAdminRecord(id) {
  return request(`/admin/records/${id}`, { method: 'DELETE' })
}

export async function fetchAdminAuditLogs() {
  return request('/admin/audit-logs')
}

export async function fetchAdminAiConfig() {
  return request('/admin/ai-config')
}

export async function saveAdminAiConfig(payload) {
  return request('/admin/ai-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchAdminScoreConfig() {
  return request('/admin/score-config')
}

export async function saveAdminScoreConfig(payload) {
  return request('/admin/score-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function cleanupAdminStorage(payload = { dry_run: false }) {
  return request('/admin/storage/cleanup', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export function teacherStatsExportUrl() {
  return `${API_BASE}/teacher/stats/export`
}

export function reportUrl(id, format) {
  return `${API_BASE}/reports/${id}/download?format=${format}`
}

export function recordReportUrl(recordId, format) {
  return `${API_BASE}/history/${recordId}/report/download?format=${format}`
}

export function resolveReportDownloadUrl(item, format) {
  const reportId = item?.reports?.[format]
  if (reportId) {
    return reportUrl(reportId, format)
  }
  if (item?.reports_on_demand && item?.status === 'success' && item?.record_id) {
    return recordReportUrl(item.record_id, format)
  }
  return ''
}

export function sourceResumeUrl(recordId) {
  return `${API_BASE}/resumes/${recordId}/source`
}

export async function fetchUserProfile() {
  return request('/users/me/profile')
}

export async function updateUserProfile(payload) {
  return request('/users/me/profile', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function fetchAdminJobs() {
  return request('/admin/jobs')
}

export async function retryBatchTask(id) {
  return request(`/batch-tasks/${id}/retry`, { method: 'POST' })
}

export function rewriteReportUrl(recordId) {
  return `${API_BASE}/history/${recordId}/rewrite-report`
}

export function analysisStreamUrl(recordId, { live = false } = {}) {
  const suffix = live ? 'analysis-live' : 'analysis-stream'
  return `${API_BASE}/history/${recordId}/${suffix}`
}

export async function retryHistoryAnalysis(id) {
  return request(`/history/${id}/retry`, { method: 'POST' })
}

export async function refreshInterviewPrep(recordId, enableAi = false) {
  const query = enableAi ? '?enable_ai=true' : ''
  return request(`/history/${recordId}/interview-prep/refresh${query}`, { method: 'POST' })
}

export async function refreshRewritePreview(recordId, enableAi = false) {
  const query = enableAi ? '?enable_ai=true' : ''
  return request(`/history/${recordId}/rewrite-preview/refresh${query}`, { method: 'POST' })
}

export async function applyRecommendedJob(recordId, { jobId = '', sourceUrl = '', targetPosition = '' } = {}) {
  return request(`/history/${recordId}/apply-job`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      job_id: jobId || '',
      source_url: sourceUrl || '',
      target_position: targetPosition || '',
    }),
    timeoutMs: 120_000,
  })
}
