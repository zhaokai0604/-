<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  Copy,
  Download,
  FileText,
  GitBranch,
  RefreshCw,
  RotateCcw,
  Sparkles,
  Stethoscope,
  UploadCloud,
  Wand2,
} from 'lucide-vue-next'

import { resolveReportDownloadUrl, rewriteReportUrl } from '../api/client'
import { usePlatform } from '../stores/platform'

const ScoreCharts = defineAsyncComponent(() => import('../components/ScoreCharts.vue'))
const VersionScoreChart = defineAsyncComponent(() => import('../components/VersionScoreChart.vue'))
const ResumeTemplatePanel = defineAsyncComponent(() => import('../components/ResumeTemplatePanel.vue'))
const AnalysisLiveStream = defineAsyncComponent(() => import('../components/AnalysisLiveStream.vue'))
const VersionDeltaPanel = defineAsyncComponent(() => import('../components/VersionDeltaPanel.vue'))

const platform = usePlatform()
const route = useRoute()
const activeTab = ref('overview')
const versionExpanded = ref(false)
const copyNotice = ref('')
const sectionRefs = ref({})
let scrollFrame = 0

const analysisSteps = [
  '提取正文与结构',
  '计算六维评分',
  '分析岗位匹配',
  '生成诊断与修改建议',
]

const reportSummary = computed(() => platform.buildReportSummary(platform.result))
const actionRoadmap = computed(() => platform.buildActionRoadmapFallback(platform.result))
const matchRate = computed(() => platform.matchRatePercent(platform.result))
const scoreGrade = computed(() => platform.scoreGradeLabel(platform.result?.total_score))
const scoreGradeTone = computed(() => platform.scoreGradeTone(platform.result?.total_score))
const docxReportUrl = computed(() => resolveReportDownloadUrl(platform.result, 'docx'))
const pdfReportUrl = computed(() => resolveReportDownloadUrl(platform.result, 'pdf'))
const missingSectionLabels = computed(() =>
  (platform.result?.missing_sections || []).map((key) => platform.sectionLabel(key)),
)
const parseReadableLabel = computed(() => {
  const q = platform.result?.parse_quality
  if (q === 'high') return '正文可读性较好'
  if (q === 'medium') return '正文可读，边界需核'
  if (q === 'low') return '正文可读性偏弱'
  return '待评估'
})
const analysisTrustLabel = computed(() => {
  const rel = platform.result?.score_reliability
  if (rel === 'low_parse_capped') return '已保守封顶'
  if (rel === 'layout_review' || rel === 'evidence_review') return '建议人工复核'
  const q = platform.result?.parse_quality
  if (q === 'low') return '可信度偏低'
  if (q === 'medium') return '可信度中等'
  if (q === 'high') return '可信度较高'
  return '按证据采信'
})
const rewriteItems = computed(() => platform.result?.rewrite_preview?.items || [])
const optimizedResume = computed(() => platform.result?.rewrite_preview?.optimized_resume || null)
const optimizedDiffs = computed(() => optimizedResume.value?.diffs || [])
const optimizedSections = computed(() => optimizedResume.value?.sections || {})
const hasOptimizedDraft = computed(
  () => Boolean(optimizedResume.value?.document_text || optimizedDiffs.value.length || rewriteItems.value.length),
)
const draftCompareItems = computed(() => (optimizedDiffs.value.length ? optimizedDiffs.value : rewriteItems.value))

function changeTypeLabel(value) {
  const key = String(value || '').trim().toLowerCase()
  const map = {
    rewrite: '改写',
    polish: '润色',
    expand: '补充',
    compress: '精简',
    insert: '新增',
    delete: '删减',
    metric: '量化',
    star: 'STAR 化',
  }
  return map[key] || value || ''
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function highlightKeywordsHtml(text, keywords) {
  const source = String(text || '')
  if (!source) return ''
  const terms = [...new Set((keywords || []).map((item) => String(item || '').trim()).filter(Boolean))]
    .sort((a, b) => b.length - a.length)
  if (!terms.length) return escapeHtml(source).replace(/\n/g, '<br>')

  const lower = source.toLowerCase()
  const ranges = []
  for (const term of terms) {
    const needle = term.toLowerCase()
    let from = 0
    while (from < lower.length) {
      const idx = lower.indexOf(needle, from)
      if (idx < 0) break
      ranges.push([idx, idx + term.length])
      from = idx + Math.max(term.length, 1)
    }
  }
  if (!ranges.length) return escapeHtml(source).replace(/\n/g, '<br>')

  ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1])
  const merged = []
  for (const range of ranges) {
    const last = merged[merged.length - 1]
    if (!last || range[0] >= last[1]) merged.push([...range])
    else last[1] = Math.max(last[1], range[1])
  }

  let html = ''
  let cursor = 0
  for (const [start, end] of merged) {
    if (start > cursor) html += escapeHtml(source.slice(cursor, start))
    html += `<mark class="jd-hit">${escapeHtml(source.slice(start, end))}</mark>`
    cursor = end
  }
  if (cursor < source.length) html += escapeHtml(source.slice(cursor))
  return html.replace(/\n/g, '<br>')
}

const resumeBodyText = computed(() => {
  const sections = platform.result?.sections || {}
  const lines = []
  for (const [key, values] of Object.entries(sections)) {
    if (String(key).startsWith('_') || !Array.isArray(values)) continue
    for (const line of values) {
      const text = String(line || '').trim()
      if (text) lines.push(text)
    }
  }
  return lines.join('\n')
})

const matchedKeywordList = computed(() => platform.result?.matched_keywords || [])
const missingKeywordList = computed(() => platform.result?.missing_keywords || [])
const marketMatch = computed(() => platform.result?.job_market_match || {})
const relatedJobs = computed(() => {
  const items = marketMatch.value?.related_jobs
  return Array.isArray(items) ? items.slice(0, 5) : []
})
const requirementBasis = computed(() => marketMatch.value?.requirement_basis || null)

function relatedJobKey(job) {
  return `${job?.id || ''}|${job?.source_url || ''}|${job?.target_position || ''}`
}

function isAppliedRelatedJob(job) {
  const current = platform.result?.job_market_match || {}
  if (job?.source_url && current.source_url && job.source_url === current.source_url) return true
  if (job?.id && current.id && String(job.id) === String(current.id)) return true
  const adopted = platform.result?.match_result?.target_position || platform.result?.target_position || ''
  return Boolean(job?.target_position && adopted && job.target_position === adopted && current.adopted_as_target)
}

function isApplyingRelatedJob(job) {
  return Boolean(platform.applyJobLoading && platform.applyingJobKey === relatedJobKey(job))
}

const highlightedResumeHtml = computed(() => highlightKeywordsHtml(resumeBodyText.value, matchedKeywordList.value))

const lowSnrZones = computed(() => platform.result?.low_snr_zones || [])
const skillHints = computed(() => platform.result?.skill_graph?.hints || [])
const structuredProfile = computed(() => platform.result?.structured || platform.result?.parse_entities?.structured || null)
const structuredStats = computed(() => structuredProfile.value?.stats || null)
const structuredSkillNames = computed(() =>
  (structuredProfile.value?.skills || []).slice(0, 12).map((item) => item.canonical || item.name).filter(Boolean),
)
const structuredEducationSummary = computed(() => {
  const first = (structuredProfile.value?.education || [])[0]
  if (!first) return ''
  return [first.school, first.major, first.degree].filter(Boolean).join(' · ')
})
const experienceYearsLabel = computed(() => {
  const years = Number(structuredStats.value?.experience_years)
  if (!years || Number.isNaN(years)) return ''
  return `${years} 年`
})
const atsBreakdown = computed(() => platform.result?.ats_breakdown || platform.result?.match_result?.ats_breakdown || null)
const criticalGaps = computed(() => platform.result?.critical_gaps || platform.result?.match_result?.critical_gaps || [])
const minorGaps = computed(() => platform.result?.minor_gaps || platform.result?.match_result?.minor_gaps || [])
const evidenceConfidencePct = computed(() => {
  const value = platform.result?.evidence_confidence
  if (value == null || Number.isNaN(Number(value))) return null
  return Math.round(Number(value) * 100)
})
const aiEnhancementPending = computed(() => platform.aiEnhancementPending(platform.result))
const tabs = computed(() => {
  const r = platform.result
  if (!r) return []
  return [
    { id: 'overview', label: '概览', icon: BarChart3 },
    {
      id: 'diagnosis',
      label: '诊断与优化稿',
      icon: Stethoscope,
      count:
        (r.structured_suggestions?.length || 0) +
        (r.diagnosis?.length || 0) +
        (optimizedDiffs.value.length || rewriteItems.value.length),
    },
    {
      id: 'match',
      label: '岗位匹配',
      icon: Briefcase,
      count: (r.matched_keywords?.length || 0) + (r.evidence_snippets?.length || 0) + skillHints.value.length,
    },
    { id: 'reports', label: '版本/报告', icon: FileText, count: platform.recordVersions.length || 0 },
  ]
})

watch(
  () => platform.result?.record_id,
  () => {
    activeTab.value = 'overview'
    versionExpanded.value = Boolean(platform.versionCompare)
    copyNotice.value = ''
    nextTick(() => updateActiveSection())
  },
)

watch(
  () => platform.versionCompare,
  (compare) => {
    if (compare?.dimension_deltas?.length) {
      versionExpanded.value = true
    }
  },
)

function normalizeTab(tab) {
  return tab === 'parse' || tab === 'enhance' ? 'diagnosis' : (tab || 'diagnosis')
}

function setSectionRef(id, el) {
  if (el) {
    sectionRefs.value[id] = el
  } else {
    delete sectionRefs.value[id]
  }
}

function updateActiveSection() {
  const ids = tabs.value.map((tab) => tab.id)
  if (!ids.length) return
  const offset = 122
  let current = ids[0]
  ids.forEach((id) => {
    const el = sectionRefs.value[id]
    if (el && el.getBoundingClientRect().top <= offset) {
      current = id
    }
  })
  activeTab.value = current
}

function handleScroll() {
  if (scrollFrame) return
  scrollFrame = window.requestAnimationFrame(() => {
    scrollFrame = 0
    updateActiveSection()
  })
}

function scrollToSection(id) {
  activeTab.value = id
  nextTick(() => {
    sectionRefs.value[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

async function handleCopy(text) {
  const ok = await platform.copyText(text)
  copyNotice.value = ok ? '已复制到剪贴板' : '复制失败，请手动选择文本'
  window.setTimeout(() => {
    copyNotice.value = ''
  }, 1600)
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  window.addEventListener('resize', handleScroll)
  nextTick(() => updateActiveSection())
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('resize', handleScroll)
  if (scrollFrame) {
    window.cancelAnimationFrame(scrollFrame)
  }
})
</script>

<template>
  <div v-if="platform.detailLoading" class="empty-state processing-state">
    <RefreshCw :size="32" class="spin-icon" />
    <strong>{{ platform.result?.status === 'processing' ? '正在分析简历' : '正在加载简历详情' }}</strong>
    <span v-if="platform.result?.status === 'processing'">{{ platform.analysisPhaseLabel() }}</span>
    <span v-else>请稍候，正在加载分析详情…</span>
    <div v-if="platform.result?.status === 'processing'" class="analysis-progress-steps">
      <div
        v-for="(step, index) in analysisSteps"
        :key="step"
        class="analysis-progress-step"
        :class="{ active: index <= platform.analysisPhase, done: index < platform.analysisPhase }"
      >
        <i>{{ index + 1 }}</i>
        <span>{{ step }}</span>
      </div>
    </div>
  </div>

  <div v-else-if="platform.result?.status === 'failed'" class="empty-state">
    <FileText :size="36" />
    <strong>分析失败</strong>
    <span>{{ platform.result.ai_fallback_reason || platform.result.error_message || '请稍后重试。' }}</span>
    <button class="secondary-action" @click="platform.retryFailedRecord(platform.result)">
      <RotateCcw :size="16" />重试分析
    </button>
  </div>

  <div v-else-if="platform.result" class="result-stack detail-page">
    <p v-if="copyNotice" class="copy-notice">{{ copyNotice }}</p>

    <section class="score-strip">
      <div class="score-block" :class="scoreGradeTone">
        <span>总评分</span>
        <strong>{{ platform.result.total_score }}</strong>
        <small>{{ scoreGrade }} · 满分 100</small>
      </div>
      <div class="score-meta">
        <strong>{{ platform.result.filename }}</strong>
        <div class="score-meta-tags">
          <span v-if="platform.result.version_no > 1" class="version-tag">v{{ platform.result.version_no }}</span>
          <span v-if="platform.result.weight_template" class="subtle-pill">权重模板：{{ platform.result.weight_template }}</span>
          <span v-if="matchRate != null" class="subtle-pill match-rate-pill">关键词覆盖 {{ matchRate }}%</span>
          <span class="mode-tag" :class="platform.displayAnalysisModeClass(platform.result)">{{ platform.displayAnalysisModeLabel(platform.result) }}</span>
        </div>
      </div>
      <div class="download-actions">
        <button class="secondary-action" @click="platform.startNewVersion(platform.result)">
          <UploadCloud :size="16" />上传新版本
        </button>
        <a v-if="platform.resolvedSourceResumeUrl(platform.result)" :href="platform.resolvedSourceResumeUrl(platform.result)" target="_blank" rel="noopener noreferrer">
          <FileText :size="16" />下载原简历
        </a>
        <a v-if="docxReportUrl" :href="docxReportUrl" target="_blank">
          <Download :size="16" />Word
        </a>
        <a v-if="pdfReportUrl" :href="pdfReportUrl" target="_blank">
          <Download :size="16" />PDF
        </a>
        <a
          v-if="hasOptimizedDraft"
          class="primary-action"
          :href="rewriteReportUrl(platform.result.record_id)"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download :size="16" />下载优化稿
        </a>
      </div>
    </section>

    <section v-if="aiEnhancementPending" class="ai-enhancement-banner">
      <div>
        <strong>
          <Sparkles :size="16" />
          增强分析生成中
        </strong>
        <p>
          当前规则分析结果已可使用，增强诊断与改写完成后会自动刷新。
        </p>
      </div>
    </section>

    <nav class="detail-tabs" aria-label="详情分区">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="detail-tab"
        :class="{ active: activeTab === tab.id }"
        :aria-current="activeTab === tab.id ? 'true' : undefined"
        @click="scrollToSection(tab.id)"
      >
        <component :is="tab.icon" :size="16" />
        {{ tab.label }}
        <span v-if="tab.count" class="detail-tab-count">{{ tab.count }}</span>
      </button>
    </nav>

    <section :ref="(el) => setSectionRef('overview', el)" class="detail-tab-panel detail-section">
      <AnalysisLiveStream :record-id="platform.result.record_id" />

      <VersionDeltaPanel :compare="platform.versionCompare" />

      <section
        v-if="lowSnrZones.length || evidenceConfidencePct != null || platform.result.low_snr_penalty?.applied"
        class="panel low-snr-panel"
      >
        <div class="panel-heading">
          <h3>分析可信度 / 待补强材料区</h3>
          <span class="panel-subtitle">
            <template v-if="evidenceConfidencePct != null">分析可信度 {{ evidenceConfidencePct }}%</template>
            <template v-if="platform.result.low_snr_penalty?.applied">
              · 已扣分 {{ platform.result.low_snr_penalty.applied }}
            </template>
          </span>
        </div>
        <p
          v-for="(reason, index) in platform.result.low_snr_penalty?.reasons || []"
          :key="`snr-reason-${index}`"
          class="snr-reason"
        >
          {{ reason }}
        </p>
        <article v-for="(zone, index) in lowSnrZones" :key="`snr-${index}`" class="snr-zone">
          <span class="subtle-pill warn-pill">{{ zone.label || '待补充区（低信噪比）' }}</span>
          <p>{{ zone.text }}</p>
          <small>{{ zone.reason }}</small>
        </article>
      </section>

      <section v-if="actionRoadmap.length" class="panel action-roadmap-panel">
        <div class="panel-heading">
          <h3>优先行动清单</h3>
          <span class="panel-subtitle">按影响程度排序，点击可跳转到对应分区</span>
        </div>
        <ol class="action-roadmap-list">
          <li v-for="(item, index) in actionRoadmap" :key="`${item.title}-${index}`">
            <button type="button" class="roadmap-item" @click="scrollToSection(normalizeTab(item.action_tab))">
              <span class="roadmap-priority" :class="item.priority">{{ platform.priorityLabel(item.priority) }}</span>
              <div class="roadmap-body">
                <strong>{{ item.title }}</strong>
                <p>{{ item.detail }}</p>
              </div>
            </button>
          </li>
        </ol>
      </section>

      <section v-if="reportSummary" class="panel report-summary-panel">
        <div class="panel-heading">
          <h3>评价摘要</h3>
          <span class="panel-subtitle">基于评分、岗位匹配和诊断结果自动生成</span>
        </div>
        <p class="report-summary-text">{{ reportSummary }}</p>
        <div class="report-quick-actions">
          <button type="button" class="text-link" @click="scrollToSection('diagnosis')">查看诊断与优化 →</button>
          <button type="button" class="text-link" @click="scrollToSection('match')">查看岗位匹配 →</button>
        </div>
      </section>

      <section v-if="platform.result.scores" class="panel score-dimension-panel">
        <div class="panel-heading">
          <h3>维度得分</h3>
          <span class="panel-subtitle">点击数值可快速定位优化方向</span>
        </div>
        <div class="dimension-grid">
          <button
            v-for="item in platform.result.chart_data?.bar || []"
            :key="item.name"
            type="button"
            class="dimension-chip"
            :class="{ weak: item.value < 70, strong: item.value >= 85 }"
            @click="scrollToSection('diagnosis')"
          >
            <span>{{ item.name }}</span>
            <strong>{{ item.value }}</strong>
          </button>
        </div>
      </section>

      <section v-if="platform.result.parse_quality" :class="['parse-note', platform.result.parse_quality]">
        <div class="trust-layers" aria-label="指标分层">
          <div class="trust-layer">
            <span class="trust-layer-k">链路</span>
            <strong>分析已完成</strong>
            <em>成功率 ≠ 质量</em>
          </div>
          <div class="trust-layer">
            <span class="trust-layer-k">可读</span>
            <strong>{{ parseReadableLabel }}</strong>
            <em>OCR/版式影响文本</em>
          </div>
          <div class="trust-layer">
            <span class="trust-layer-k">可信</span>
            <strong>{{ analysisTrustLabel }}</strong>
            <em>证据不足会告警或封顶</em>
          </div>
        </div>
        <div>
          <strong>{{ platform.parseQualityLabel(platform.result.parse_quality) }}</strong>
          <span v-if="platform.result.parse_quality === 'low'">
            该简历存在版式复杂 / 扫描质量较低 / 字段证据不足等问题，因此本次评分可信度偏低，建议优先补全可复制文本信息后再评估。
          </span>
          <span v-else-if="platform.result.parse_quality === 'medium'">
            该简历存在版式复杂或字段证据不足，因此本次评分可信度为中等；结论可参考，但建议优先补全文本信息并人工核验关键模块。
          </span>
          <span v-else>正文和核心模块识别较完整，分析可信度较高。</span>
        </div>
        <ul v-if="platform.result.parse_warnings?.length">
          <li v-for="warning in platform.result.parse_warnings" :key="warning">{{ warning }}</li>
        </ul>
        <p v-if="missingSectionLabels.length" class="parse-extra">
          未明显识别到：{{ missingSectionLabels.join('、') }}。建议在新版本中补齐对应内容。
        </p>
        <p v-if="platform.result.score_reliability === 'low_parse_capped'" class="parse-extra">
          因正文提取不足，总分已做保守封顶处理——系统在证据不足时不会给出虚高结论。
        </p>
        <p v-else-if="platform.result.score_reliability === 'layout_review'" class="parse-extra">
          版式复杂但正文已提取，建议人工核验模块边界；复杂度本身不直接扣分。
        </p>
        <p v-else-if="platform.result.score_reliability === 'evidence_review'" class="parse-extra">
          当前证据覆盖率较低，岗位匹配和经历评分建议结合原文复核。
        </p>
        <p v-if="platform.result.evidence_coverage != null" class="parse-extra">
          证据覆盖率 {{ Math.round(Number(platform.result.evidence_coverage) * 100) }}%
          <span v-if="platform.result.layout_complexity != null">
            · 版式复杂度 {{ Number(platform.result.layout_complexity).toFixed(1) }}
          </span>
        </p>
        <ul v-if="platform.result.quality_warnings?.length" class="parse-extra-list">
          <li v-for="warning in platform.result.quality_warnings" :key="warning">{{ warning }}</li>
        </ul>
        <div v-if="structuredStats" class="structured-parse-box">
          <strong>结构化抽取</strong>
          <p>
            教育 {{ structuredStats.education_count || 0 }} ·
            经历 {{ structuredStats.experience_count || 0 }} ·
            技能 {{ structuredStats.skill_count || 0 }} ·
            获奖 {{ structuredStats.award_count || 0 }}
            <template v-if="structuredStats.avg_confidence">
              · 均置信度 {{ Math.round(Number(structuredStats.avg_confidence) * 100) }}%
            </template>
          </p>
          <p v-if="structuredEducationSummary" class="parse-extra">教育：{{ structuredEducationSummary }}</p>
          <p v-if="experienceYearsLabel" class="parse-extra">经历时长（日期归一）：约 {{ experienceYearsLabel }}</p>
          <p v-if="structuredSkillNames.length" class="parse-extra">技能归一：{{ structuredSkillNames.join('、') }}</p>
          <p v-if="structuredStats.implicit_skill_count" class="parse-extra">
            其中隐式技能 {{ structuredStats.implicit_skill_count }} 项（从经历推断）
          </p>
        </div>
      </section>

      <ScoreCharts :data="platform.result.chart_data" />
    </section>

    <section :ref="(el) => setSectionRef('diagnosis', el)" class="detail-tab-panel detail-section diagnosis-workspace">
      <section class="panel diagnosis-intro-panel">
        <div class="diagnosis-flow">
          <span>1. 看问题</span>
          <ArrowRight :size="14" />
          <span>2. 对照初稿 / 优化稿</span>
          <ArrowRight :size="14" />
          <span>3. 复制或下载成稿</span>
        </div>
        <p class="diagnosis-intro">先读诊断与证据，再在下方逐条对照改写；不确定的量化处保留【待补充】，勿编造经历。</p>
      </section>

      <section v-if="platform.result.structured_suggestions?.length" class="panel evidence-suggestion-panel">
        <div class="panel-heading">
          <h3>依据材料补强建议</h3>
          <span class="panel-subtitle">{{ platform.result.structured_suggestions.length }} 条 · 绑定原文证据</span>
        </div>
        <article
          v-for="(item, index) in platform.result.structured_suggestions"
          :key="index"
          class="evidence-suggestion-card"
        >
          <div class="card-title-row">
            <div class="evidence-title">
              <i>{{ index + 1 }}</i>
              <strong>{{ item.problem }}</strong>
            </div>
            <button v-if="item.example" type="button" class="text-link copy-btn" @click="handleCopy(item.example)">
              <Copy :size="14" />复制示例
            </button>
          </div>
          <dl class="evidence-meta">
            <div><dt>证据</dt><dd>{{ item.evidence }}</dd></div>
            <div><dt>影响</dt><dd>{{ item.impact }}</dd></div>
            <div><dt>方向</dt><dd>{{ item.direction }}</dd></div>
            <div v-if="item.example" class="evidence-example"><dt>示例</dt><dd>{{ item.example }}</dd></div>
          </dl>
        </article>
      </section>

      <section v-else class="layout-two diagnosis-fallback-grid">
        <div class="panel">
          <div class="panel-heading">
            <h3>问题诊断</h3>
            <span class="panel-subtitle">{{ platform.result.diagnosis?.length || 0 }} 条</span>
          </div>
          <ol v-if="platform.result.diagnosis?.length" class="numbered-list">
            <li v-for="item in platform.result.diagnosis" :key="item">{{ item }}</li>
          </ol>
          <p v-else class="table-empty">暂无明显诊断项。</p>
        </div>
        <div class="panel">
          <div class="panel-heading">
            <h3>修改建议</h3>
            <span class="panel-subtitle">{{ platform.result.suggestions?.length || 0 }} 条</span>
          </div>
          <ol v-if="platform.result.suggestions?.length" class="numbered-list">
            <li v-for="item in platform.result.suggestions" :key="item">{{ item }}</li>
          </ol>
          <p v-else class="table-empty">暂无建议。</p>
        </div>
      </section>

      <ResumeTemplatePanel :recommendations="platform.result.template_recommendations" />

      <section v-if="hasOptimizedDraft" class="panel rewrite-panel optimized-draft-panel">
        <div class="panel-heading rewrite-panel-heading">
          <div>
            <h3><Wand2 :size="18" /> 初稿 → 优化稿</h3>
            <span class="panel-subtitle">
              {{ optimizedResume?.summary || platform.result.rewrite_preview?.summary }}
            </span>
            <div class="rewrite-meta-pills">
              <span v-if="platform.result.rewrite_preview?.mode" class="subtle-pill">
                {{ platform.rewriteModeLabel(platform.result.rewrite_preview.mode) }}
              </span>
              <span v-if="optimizedResume?.change_count" class="subtle-pill">
                {{ optimizedResume.change_count }} 处改动
              </span>
              <span class="subtle-pill">{{ draftCompareItems.length }} 条对照</span>
            </div>
          </div>
          <div class="panel-actions">
            <a
              class="primary-action"
              :href="rewriteReportUrl(platform.result.record_id)"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download :size="16" />下载完整优化稿
            </a>
            <button
              v-if="platform.enableAi || platform.result.rewrite_preview?.mode === 'deepseek'"
              class="secondary-action"
              :disabled="platform.rewritePreviewLoading"
              @click="platform.refreshRewritePreviewForRecord(true)"
            >
              <Sparkles :size="16" />{{ platform.rewritePreviewLoading ? '生成中…' : '生成增强改写' }}
            </button>
          </div>
        </div>

        <div class="rewrite-legend" aria-hidden="true">
          <span>初稿</span>
          <ArrowRight :size="14" />
          <span>优化稿（可复制）</span>
        </div>

        <div class="rewrite-list">
          <article
            v-for="(item, index) in draftCompareItems"
            :key="`diff-${index}`"
            class="rewrite-item"
          >
            <header class="rewrite-item-head">
              <div class="rewrite-item-tags">
                <i class="rewrite-index">{{ index + 1 }}</i>
                <span class="subtle-pill">{{ item.section || item.section_key || '改动' }}</span>
                <span v-if="item.focus" class="subtle-pill soft">{{ item.focus }}</span>
                <span v-if="item.change_type" class="subtle-pill soft">{{ changeTypeLabel(item.change_type) }}</span>
              </div>
              <button
                type="button"
                class="text-link copy-btn"
                @click="handleCopy(item.optimized || item.suggested)"
              >
                <Copy :size="14" />复制优化稿
              </button>
            </header>
            <div class="rewrite-compare">
              <div class="rewrite-col original">
                <p>{{ item.original || '（新增内容）' }}</p>
              </div>
              <div class="rewrite-arrow" aria-hidden="true">
                <ArrowRight :size="16" />
              </div>
              <div class="rewrite-col suggested">
                <p>{{ item.optimized || item.suggested }}</p>
              </div>
            </div>
          </article>
        </div>

        <details v-if="Object.keys(optimizedSections).length" class="optimized-full-doc">
          <summary>预览完整优化稿正文</summary>
          <div class="optimized-full-body">
            <div v-for="(lines, key) in optimizedSections" :key="key" class="optimized-section-block">
              <h4>{{ platform.sectionLabel(key) || key }}</h4>
              <p v-for="(line, lineIndex) in lines" :key="`${key}-${lineIndex}`">{{ line }}</p>
            </div>
          </div>
        </details>
      </section>
      <section v-else class="panel rewrite-empty-panel">
        <div class="panel-heading">
          <h3><Wand2 :size="18" /> 初稿 → 优化稿</h3>
        </div>
        <p class="table-empty">当前记录还没有优化稿，可生成增强改写版。</p>
        <button
          class="secondary-action"
          :disabled="platform.rewritePreviewLoading"
          @click="platform.refreshRewritePreviewForRecord(true)"
        >
          <Sparkles :size="16" />{{ platform.rewritePreviewLoading ? '生成中…' : '生成优化稿' }}
        </button>
      </section>
    </section>

    <section :ref="(el) => setSectionRef('match', el)" class="detail-tab-panel detail-section">
      <section class="panel match-panel">
        <div class="panel-heading"><h3>岗位匹配</h3></div>

        <div v-if="matchRate != null" class="match-rate-card">
          <div class="match-rate-ring" :class="matchRate >= 70 ? 'good' : matchRate >= 45 ? 'mid' : 'low'">
            <strong>{{ matchRate }}%</strong>
            <span>关键词覆盖率</span>
          </div>
          <div class="match-rate-detail">
            <p v-if="platform.result.job_profile?.name"><strong>岗位模板：</strong>{{ platform.result.job_profile.name }}</p>
            <p><strong>采用岗位：</strong>{{ platform.result.match_result?.target_position || (marketMatch.recommendation_only ? '未指定（通用分析，下方仅为推荐，未自动套用）' : '未识别，使用通用建议') }}</p>
            <p><strong>岗位来源：</strong>{{ platform.targetSourceLabel(platform.result.match_result?.target_source || platform.result.target_position_source) }}</p>
            <p v-if="platform.result.match_confidence"><strong>匹配置信度：</strong>{{ Math.round((platform.result.match_confidence || 0) * 100) }}%</p>
            <p v-if="platform.result.rule_score != null || platform.result.match_result?.rule_score != null">
              <strong>规则分：</strong>{{ platform.result.rule_score ?? platform.result.match_result?.rule_score }}
              <template v-if="(platform.result.semantic_score ?? platform.result.match_result?.semantic_score) != null">
                · <strong>语义分：</strong>{{ platform.result.semantic_score ?? platform.result.match_result?.semantic_score }}
              </template>
              <template v-if="platform.result.match_backend || platform.result.match_result?.match_backend">
                · <strong>融合：</strong>{{ platform.result.match_backend || platform.result.match_result?.match_backend }}
              </template>
            </p>
            <p class="match-summary-text">{{ platform.result.match_result?.summary }}</p>
          </div>
        </div>
        <template v-else>
          <p v-if="platform.result.job_profile?.name"><strong>岗位模板：</strong>{{ platform.result.job_profile.name }}</p>
          <p><strong>采用岗位：</strong>{{ platform.result.match_result?.target_position || (marketMatch.recommendation_only ? '未指定（通用分析，下方仅为推荐，未自动套用）' : '未识别，使用通用建议') }}</p>
          <p><strong>岗位来源：</strong>{{ platform.targetSourceLabel(platform.result.match_result?.target_source || platform.result.target_position_source) }}</p>
          <p>{{ platform.result.match_result?.summary }}</p>
        </template>

        <div v-if="marketMatch.target_position || marketMatch.fallback_used || relatedJobs.length || marketMatch.recommendation_only" class="market-match-proof">
          <div class="panel-heading">
            <h4>{{ marketMatch.recommendation_only && !marketMatch.adopted_as_target ? '岗位推荐' : '真实岗位库核验' }}</h4>
            <span class="mode-tag" :class="marketMatch.adopted_as_target ? 'success' : 'warning'">
              {{ marketMatch.adopted_as_target ? '已采用点选/匹配岗位' : (marketMatch.recommendation_only ? '仅推荐未自动套岗' : '已使用保底') }}
            </span>
          </div>
          <p v-if="marketMatch.adopted_as_target && marketMatch.target_position"><strong>匹配岗位：</strong>{{ marketMatch.target_position }} · {{ marketMatch.company || '公开岗位' }} · {{ marketMatch.city || '全国' }}</p>
          <p v-if="marketMatch.adopted_as_target"><strong>证据覆盖：</strong>{{ Math.round((marketMatch.evidence_coverage || 0) * 100) }}% · <strong>命中关键词：</strong>{{ (marketMatch.matched_keywords || []).slice(0, 8).join('、') || '暂无' }}</p>
          <p v-if="marketMatch.adopted_as_target && marketMatch.match_explanation"><strong>适配提示：</strong>必备要求 {{ Math.round((marketMatch.match_explanation.must_coverage || 0) * 100) }}% · 学历 {{ marketMatch.match_explanation.education_alignment || '未知' }} · 经验 {{ marketMatch.match_explanation.experience_alignment || '未知' }}</p>
          <a v-if="marketMatch.adopted_as_target && marketMatch.source_url" class="text-link" :href="marketMatch.source_url" target="_blank" rel="noreferrer">查看岗位公开来源</a>
          <p v-if="marketMatch.quality_warning" class="muted-cell">{{ marketMatch.quality_warning }}</p>

          <div v-if="marketMatch.adopted_as_target && requirementBasis && (requirementBasis.must_skills?.length || requirementBasis.education)" class="requirement-basis-block">
            <div class="panel-heading">
              <h4>岗位适配依据</h4>
              <span class="panel-subtitle">公开岗位要求进入分析链路，而非仅作背景数据</span>
            </div>
            <dl class="kv-list requirement-basis-list">
              <div v-if="requirementBasis.education"><dt>学历要求</dt><dd>{{ requirementBasis.education }}</dd></div>
              <div v-if="requirementBasis.must_skills?.length"><dt>技能要求</dt><dd>{{ requirementBasis.must_skills.join(' / ') }}</dd></div>
              <div v-if="requirementBasis.experience_requirements?.length"><dt>经历要求</dt><dd>{{ requirementBasis.experience_requirements.join('、') }}</dd></div>
              <div>
                <dt>当前简历证据</dt>
                <dd>
                  命中 {{ requirementBasis.hit_count ?? 0 }} 项
                  <template v-if="requirementBasis.hit_skills?.length">（{{ requirementBasis.hit_skills.slice(0, 4).join('、') }}）</template>
                  ，缺失 {{ requirementBasis.miss_count ?? 0 }} 项
                  <template v-if="requirementBasis.missing_skills?.length">（{{ requirementBasis.missing_skills.slice(0, 4).join('、') }}）</template>
                </dd>
              </div>
            </dl>
          </div>

          <div v-if="relatedJobs.length" class="related-jobs-board">
            <div class="panel-heading">
              <h4>{{ marketMatch.recommendation_only || !platform.result?.match_result?.target_position ? '为你推荐的匹配岗位' : '相关岗位 Top5' }}</h4>
              <span class="panel-subtitle">
                {{ marketMatch.recommendation_only
                  ? '未指定目标岗时不会自动套岗；点击岗位可生成该岗专属评价与匹配报告'
                  : '点击可切换为该岗评价；本地已核验公开岗位库，非现场联网抓取' }}
              </span>
            </div>
            <div class="related-jobs-list">
              <article
                v-for="job in relatedJobs"
                :key="`${job.rank}-${job.id || ''}-${job.target_position}-${job.company}`"
                class="related-job-row"
                :class="{
                  active: isAppliedRelatedJob(job),
                  loading: isApplyingRelatedJob(job),
                }"
              >
                <div class="related-job-rank">{{ job.rank }}</div>
                <div class="related-job-main">
                  <strong>{{ job.target_position || '公开岗位' }}</strong>
                  <small>{{ job.city || '全国' }} · {{ job.company || '公开岗位' }} · {{ job.category || '未分类' }}</small>
                  <p v-if="job.matched_keywords?.length">命中：{{ job.matched_keywords.slice(0, 5).join('、') }}</p>
                </div>
                <div class="related-job-score">
                  <strong>{{ job.match_percent ?? Math.round((job.match_score || 0) * 100) }}</strong>
                  <span>匹配分</span>
                  <button
                    type="button"
                    class="secondary-action related-job-apply"
                    :disabled="platform.applyJobLoading"
                    @click="platform.applyRecommendedJobForRecord(job)"
                  >
                    {{ isApplyingRelatedJob(job) ? '评价中…' : (isAppliedRelatedJob(job) ? '当前岗位' : '查看该岗评价') }}
                  </button>
                  <a v-if="job.source_url" class="text-link" :href="job.source_url" target="_blank" rel="noreferrer">来源</a>
                </div>
              </article>
            </div>
          </div>
          <p v-else-if="marketMatch.recommendation_only" class="muted-cell">
            当前简历与公开岗位库暂无足够相似的岗位推荐；可返回上传页填写目标岗位后再分析。
          </p>
        </div>

        <div v-if="platform.result.matched_keywords?.length || platform.result.missing_keywords?.length" class="match-bar-wrap">
          <div class="match-bar">
            <i class="matched" :style="{ width: `${matchRate != null ? matchRate : 50}%` }" />
          </div>
          <div class="match-bar-labels">
            <span>已匹配 {{ platform.result.matched_keywords?.length || 0 }}</span>
            <span>缺失 {{ platform.result.missing_keywords?.length || 0 }}</span>
          </div>
        </div>

        <section v-if="atsBreakdown" class="ats-breakdown-panel">
          <h4>ATS 分项</h4>
          <div class="ats-bars">
            <div class="ats-bar-row">
              <span>关键词匹配 55%</span>
              <div class="ats-bar"><i :style="{ width: `${atsBreakdown.keyword_match || 0}%` }" /></div>
              <strong>{{ atsBreakdown.keyword_match || 0 }}</strong>
            </div>
            <div class="ats-bar-row">
              <span>技能覆盖 25%</span>
              <div class="ats-bar"><i :style="{ width: `${atsBreakdown.skills_coverage || 0}%` }" /></div>
              <strong>{{ atsBreakdown.skills_coverage || 0 }}</strong>
            </div>
            <div class="ats-bar-row">
              <span>板块完整 20%</span>
              <div class="ats-bar"><i :style="{ width: `${atsBreakdown.section_completeness || 0}%` }" /></div>
              <strong>{{ atsBreakdown.section_completeness || 0 }}</strong>
            </div>
            <p class="ats-overall">综合 ATS：{{ atsBreakdown.overall || 0 }}</p>
          </div>
        </section>

        <div v-if="matchedKeywordList.length" class="keyword-row">
          <span class="keyword-label">已匹配关键词</span>
          <div class="keyword-chips matched">
            <span v-for="word in matchedKeywordList" :key="word">{{ word }}</span>
          </div>
        </div>
        <div v-if="criticalGaps.length" class="keyword-row">
          <span class="keyword-label">核心缺口（必填）</span>
          <div class="keyword-chips missing">
            <span v-for="word in criticalGaps" :key="`c-${word}`">{{ word }}</span>
          </div>
        </div>
        <div v-if="minorGaps.length" class="keyword-row">
          <span class="keyword-label">次要缺口（加分项）</span>
          <div class="keyword-chips minor">
            <span v-for="word in minorGaps" :key="`m-${word}`">{{ word }}</span>
          </div>
        </div>
        <div v-else-if="missingKeywordList.length" class="keyword-row">
          <span class="keyword-label">建议补充（正文未命中）</span>
          <div class="keyword-chips missing">
            <span v-for="word in missingKeywordList" :key="word">{{ word }}</span>
          </div>
        </div>

        <section v-if="resumeBodyText" class="jd-highlight-panel">
          <div class="jd-highlight-head">
            <h4>简历正文关键词高亮</h4>
            <span>绿色为已命中岗位关键词；下方清单为建议补充项</span>
          </div>
          <div class="jd-highlight-body" v-html="highlightedResumeHtml" />
          <p v-if="!matchedKeywordList.length" class="table-empty">当前无命中关键词，可先完善技能与项目表述。</p>
        </section>

        <div v-if="skillHints.length" class="skill-graph-block">
          <h4>技能图谱提示</h4>
          <ul class="clean-list">
            <li v-for="(hint, index) in skillHints" :key="`hint-${index}`">{{ hint.message }}</li>
          </ul>
        </div>
      </section>

      <section v-if="platform.result.evidence_snippets?.length" class="panel evidence-panel">
        <div class="panel-heading">
          <h3>匹配证据</h3>
          <span class="panel-subtitle">优先锚定分节正文（技能/项目/实习），附板块来源</span>
        </div>
        <ul class="evidence-list">
          <li v-for="(item, index) in platform.result.evidence_snippets" :key="`${item.keyword}-${index}`">
            <span class="evidence-keyword">{{ item.keyword }}</span>
            <span v-if="item.section_label" class="evidence-section">{{ item.section_label }}</span>
            <p>{{ item.text }}</p>
          </li>
        </ul>
      </section>
    </section>

    <section :ref="(el) => setSectionRef('reports', el)" class="detail-tab-panel detail-section">
      <section class="panel">
        <div class="panel-heading">
          <h3>报告与原文件</h3>
          <span class="panel-subtitle">原简历保留原始内容；评价报告记录本次分析；优化稿仅供修改参考</span>
        </div>
        <div class="download-actions">
          <a v-if="platform.resolvedSourceResumeUrl(platform.result)" :href="platform.resolvedSourceResumeUrl(platform.result)" target="_blank" rel="noopener noreferrer">
            <FileText :size="16" />下载原简历
          </a>
          <a v-if="docxReportUrl" :href="docxReportUrl" target="_blank">
            <Download :size="16" />下载 Word 报告
          </a>
          <a v-if="pdfReportUrl" :href="pdfReportUrl" target="_blank">
            <Download :size="16" />下载 PDF 报告
          </a>
          <a v-if="hasOptimizedDraft" :href="rewriteReportUrl(platform.result.record_id)" target="_blank" rel="noopener noreferrer">
            <Download :size="16" />下载优化稿
          </a>
        </div>
      </section>

      <section v-if="platform.recordVersions.length > 1" class="panel version-panel compact">
        <div class="panel-heading">
          <h3><GitBranch :size="18" /> 版本历史</h3>
          <button type="button" class="text-link" @click="versionExpanded = !versionExpanded">
            {{ versionExpanded ? '收起图表' : '展开对比图' }}
          </button>
        </div>
        <VersionDeltaPanel :compare="platform.versionCompare" />
        <VersionScoreChart v-if="versionExpanded" :versions="platform.recordVersions" :compare="platform.versionCompare" />
        <div class="version-timeline">
          <button
            v-for="version in platform.recordVersions"
            :key="version.record_id"
            class="version-chip"
            :class="{ active: version.is_current }"
            @click="platform.openRecordById(version.record_id)"
          >
            <strong>v{{ version.version_no }}</strong>
            <span>{{ version.total_score }} 分</span>
            <small
              v-if="platform.versionCompare && version.record_id === platform.versionCompare.b?.record_id"
              class="version-chip-delta"
              :class="platform.versionCompare.summary?.direction || ''"
            >
              {{ platform.versionCompare.summary?.total_score_delta > 0 ? '↑' : platform.versionCompare.summary?.total_score_delta < 0 ? '↓' : '→' }}
              {{ platform.versionCompare.summary?.total_score_delta > 0 ? '+' : '' }}{{ platform.versionCompare.summary?.total_score_delta }}
            </small>
            <small>{{ platform.formatDateTime(version.created_at) }}</small>
          </button>
        </div>
      </section>
      <section v-else class="panel">
        <p class="table-empty">暂无历史版本。上传新版本后，这里会显示版本链和得分变化。</p>
      </section>
    </section>
  </div>

  <div v-else-if="platform.detailError && route.name === 'workspace-resume-detail'" class="empty-state">
    <FileText :size="36" />
    <strong>加载失败</strong>
    <span>{{ platform.detailError }}</span>
    <button class="secondary-action" @click="platform.openRecordById(Number(route.params.recordId))">
      <RefreshCw :size="16" />重试
    </button>
  </div>

  <section v-else class="empty-state">
    <FileText :size="36" />
    <strong>暂无报告</strong>
    <span>完成分析或从历史记录打开报告后，这里会显示结果。</span>
  </section>
</template>
