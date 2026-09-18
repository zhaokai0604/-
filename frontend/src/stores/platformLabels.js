/** 平台展示层纯函数：标签、摘要与状态文案（无响应式状态）。 */

const ANALYSIS_MODE_LABELS = {
  ai_first: '规则分析',
  deepseek: '增强分析已完成',
  core: '规则分析',
  offline_fallback: '规则分析',
  offline: '规则分析',
}

const TARGET_SOURCE_LABELS = {
  manual: '手动输入岗位',
  selected: '点选推荐岗位',
  detected: '简历识别岗位',
  generic: '通用建议',
}

const PARSE_QUALITY_LABELS = {
  high: '分析可信度高',
  medium: '分析可信度中等',
  low: '分析可信度偏低',
}

export const SECTION_LABELS = {
  basic_info: '个人信息',
  education: '教育背景',
  internship: '实习/工作经历',
  projects: '项目/实训经历',
  campus: '校园实践',
  skills: '技能证书',
  awards: '荣誉奖项',
  summary: '自我评价/求职意向',
}

const SCORE_DIMENSION_LABELS = {
  content_completeness: '内容完整性',
  experience_match: '经历相关性',
  language_professionalism: '语言专业性',
  format_standardization: '格式规范性',
  highlight_strength: '亮点量化程度',
  job_match: '岗位语义匹配',
}

export function analysisModeLabel(mode) {
  return ANALYSIS_MODE_LABELS[mode] || mode || '未知'
}

export function displayAnalysisModeLabel(payload) {
  if (!payload) {
    return '未知'
  }
  if (payload.ai_requested) {
    const status = payload.ai_enhancement_status || ''
    if (payload.analysis_mode === 'deepseek' || status === 'success') {
      return '增强分析已完成'
    }
    if (status === 'pending' || status === 'processing') {
      return '增强分析进行中'
    }
    return analysisModeLabel(payload.analysis_mode)
  }
  if (payload.analysis_mode_label && payload.analysis_mode_label !== 'AI 智能分析') {
    return payload.analysis_mode_label
  }
  return analysisModeLabel(payload.analysis_mode)
}

export function displayAnalysisModeClass(payload) {
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

export function shouldShowAiWorking(payload) {
  return Boolean(payload?.ai_requested) && ['pending', 'processing'].includes(payload?.ai_enhancement_status || '')
}

export function targetSourceLabel(source) {
  return TARGET_SOURCE_LABELS[source] || '通用建议'
}

export function parseQualityLabel(quality) {
  return PARSE_QUALITY_LABELS[quality] || '分析可信度未知'
}

export function sectionLabel(key) {
  return SECTION_LABELS[key] || key || '其他'
}

export function confidenceLabel(confidence) {
  const value = Number(confidence) || 0
  if (value >= 0.85) return '识别较完整'
  if (value >= 0.65) return '基本识别'
  return '识别偏弱'
}

export function scoreGradeLabel(score) {
  const value = Number(score) || 0
  if (value >= 90) return '优秀'
  if (value >= 80) return '良好'
  if (value >= 70) return '中等'
  if (value >= 60) return '待提升'
  return '需加强'
}

export function scoreGradeTone(score) {
  const value = Number(score) || 0
  if (value >= 85) return 'strong'
  if (value >= 70) return 'mid'
  return 'weak'
}

export function matchRatePercent(result) {
  if (result?.match_rate != null) return Math.round(Number(result.match_rate))
  const matched = result?.matched_keywords?.length || 0
  const missing = result?.missing_keywords?.length || 0
  const total = matched + missing
  if (!total) return null
  return Math.round((matched / total) * 100)
}

export function priorityLabel(priority) {
  const labels = {
    urgent: '紧急',
    high: '优先',
    medium: '建议',
  }
  return labels[priority] || '建议'
}

export function buildActionRoadmapFallback(result) {
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

export function buildReportSummary(result) {
  if (!result?.scores) return ''
  const scoreEntries = Object.entries(result.scores)
    .filter(([key]) => key !== 'total_score')
    .map(([key, value]) => ({
      key,
      value: Number(value) || 0,
      label: SCORE_DIMENSION_LABELS[key] || key,
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

export function parseQualityTone(quality) {
  if (quality === 'high') return 'success'
  if (quality === 'low') return 'danger'
  return 'warning'
}

export function batchItemStatusLabel(status) {
  const labels = {
    success: '成功',
    failed: '失败',
    skipped: '跳过',
  }
  return labels[status] || status || '未知'
}

export function batchItemStatusTone(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'skipped') return 'warning'
  return 'processing'
}

export function scoreReliabilityLabel(reliability) {
  const labels = {
    low_parse_capped: '低解析封顶',
    normal: '',
  }
  return labels[reliability] || ''
}

export function rewriteModeLabel(mode) {
  const labels = {
    deepseek: '增强改写',
    offline_star: 'STAR 成稿参考',
    offline: '规则成稿参考',
  }
  return labels[mode] || '规则成稿参考'
}

export function recordStatusDone(status) {
  return !['processing', 'pending'].includes(status)
}

export function batchStatusDone(status) {
  return ['success', 'partial_success', 'failed', 'paused'].includes(status)
}

export function batchStatusTone(status) {
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

export function roleLabel(role) {
  if (role === 'admin') return '管理员'
  if (role === 'teacher') return '教师'
  return '用户'
}
