const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
  })
  if (!response.ok) {
    let message = response.status === 413
      ? '上传文件过大：请压缩文件、减少 ZIP 内简历数量，或在配置中调大上传限制。'
      : response.status === 504
        ? '批量分析等待超时：DeepSeek 批量分析耗时较长，请稍后刷新历史记录查看已完成结果，或减少 ZIP 内简历数量后重试。'
      : response.status >= 500
        ? '服务器处理失败，请稍后再试。'
        : `请求失败：${response.status}`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // keep default message
    }
    throw new Error(message)
  }
  return response.json()
}

export async function fetchCurrentUser() {
  return request('/auth/me')
}

export async function fetchHealth() {
  return request('/health')
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
  const form = new FormData()
  form.append('file', payload.file)
  form.append('target_position', payload.targetPosition || '')
  form.append('job_description', payload.jobDescription || '')
  form.append('job_profile_id', String(payload.jobProfileId || 0))
  form.append('enable_ai', String(Boolean(payload.enableAi)))
  if (payload.parentRecordId) {
    form.append('parent_record_id', String(payload.parentRecordId))
  }
  return request('/resumes/analyze', { method: 'POST', body: form })
}

export async function analyzeZip(payload) {
  const form = new FormData()
  form.append('file', payload.file)
  form.append('target_position', payload.targetPosition || '')
  form.append('job_description', payload.jobDescription || '')
  form.append('job_profile_id', String(payload.jobProfileId || 0))
  form.append('enable_ai', String(Boolean(payload.enableAi)))
  return request('/resumes/analyze-zip', { method: 'POST', body: form })
}

export async function fetchJobProfiles() {
  return request('/job-profiles')
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

export async function fetchBatchTask(id) {
  return request(`/batch-tasks/${id}`)
}

export async function pauseBatchTask(id) {
  return request(`/batch-tasks/${id}/pause`, { method: 'POST' })
}

export async function fetchHistory() {
  return request('/history')
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

export function reportUrl(id, format) {
  return `${API_BASE}/reports/${id}/download?format=${format}`
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
