<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
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
  '生成诊断与 AI 改写',
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
const rewriteItems = computed(() => platform.result?.rewrite_preview?.items || [])
const aiEnhancementPending = computed(() => platform.aiEnhancementPending(platform.result))
const tabs = computed(() => {
  const r = platform.result
  if (!r) return []
  return [
    { id: 'overview', label: '概览', icon: BarChart3 },
    {
      id: 'diagnosis',
      label: '诊断与优化',
      icon: Stethoscope,
      count: (r.structured_suggestions?.length || 0) + (r.diagnosis?.length || 0) + rewriteItems.value.length,
    },
    {
      id: 'match',
      label: '岗位匹配',
      icon: Briefcase,
      count: (r.matched_keywords?.length || 0) + (r.evidence_snippets?.length || 0),
    },
    { id: 'reports', label: '版本/报告', icon: FileText, count: platform.recordVersions.length || 0 },
  ]
})

watch(
  () => platform.result?.record_id,
  () => {
    activeTab.value = 'overview'
    versionExpanded.value = false
    copyNotice.value = ''
    nextTick(() => updateActiveSection())
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
          <FileText :size="16" />查看简历
        </a>
        <a v-if="docxReportUrl" :href="docxReportUrl" target="_blank">
          <Download :size="16" />Word
        </a>
        <a v-if="pdfReportUrl" :href="pdfReportUrl" target="_blank">
          <Download :size="16" />PDF
        </a>
        <a
          v-if="rewriteItems.length"
          :href="rewriteReportUrl(platform.result.record_id)"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download :size="16" />优化稿
        </a>
      </div>
    </section>

    <section v-if="aiEnhancementPending" class="ai-enhancement-banner">
      <div>
        <strong>
          <Sparkles :size="16" />
          智能优化生成中
        </strong>
        <p>
          当前结果已可使用，AI 诊断与改写完成后会自动刷新。
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
        <div>
          <strong>{{ platform.parseQualityLabel(platform.result.parse_quality) }}</strong>
          <span v-if="platform.result.parse_quality === 'low'">评分仅供参考，请优先检查文件正文是否能被正确提取。</span>
          <span v-else-if="platform.result.parse_quality === 'medium'">已完成分析，部分建议会受简历结构识别质量影响。</span>
          <span v-else>正文和核心模块识别较完整。</span>
        </div>
        <ul v-if="platform.result.parse_warnings?.length">
          <li v-for="warning in platform.result.parse_warnings" :key="warning">{{ warning }}</li>
        </ul>
        <p v-if="missingSectionLabels.length" class="parse-extra">
          未明显识别到：{{ missingSectionLabels.join('、') }}。建议在新版本中补齐对应内容。
        </p>
        <p v-if="platform.result.score_reliability === 'low_parse_capped'" class="parse-extra">
          因正文提取不足，总分已做保守封顶处理。
        </p>
      </section>

      <ScoreCharts :data="platform.result.chart_data" />
    </section>

    <section :ref="(el) => setSectionRef('diagnosis', el)" class="detail-tab-panel detail-section">
      <section class="panel diagnosis-intro-panel">
        <p class="diagnosis-intro">
          这里把问题诊断、修改方向和可复制改写合并在一起。先看证据和影响，再直接复制参考表达去修改简历。
        </p>
      </section>

      <section v-if="platform.result.structured_suggestions?.length" class="panel evidence-suggestion-panel">
        <div class="panel-heading">
          <h3>证据级优化建议</h3>
          <span class="panel-subtitle">每条建议绑定原文证据、影响和改写方向</span>
        </div>
        <article v-for="(item, index) in platform.result.structured_suggestions" :key="index" class="evidence-suggestion-card">
          <div class="card-title-row">
            <strong>{{ item.problem }}</strong>
            <button v-if="item.example" type="button" class="text-link copy-btn" @click="handleCopy(item.example)">
              <Copy :size="14" />复制示例
            </button>
          </div>
          <p><span>证据</span>{{ item.evidence }}</p>
          <p><span>影响</span>{{ item.impact }}</p>
          <p><span>方向</span>{{ item.direction }}</p>
          <p v-if="item.example" class="example-line"><span>示例</span>{{ item.example }}</p>
        </article>
      </section>

      <section v-else class="layout-two">
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

      <section v-if="rewriteItems.length" class="panel rewrite-panel">
        <div class="panel-heading">
          <div>
            <h3><Wand2 :size="18" /> 优化版表达预览</h3>
            <span class="panel-subtitle">
              {{ platform.result.rewrite_preview.summary }}
              <span v-if="platform.result.rewrite_preview.mode" class="subtle-pill">
                {{ platform.rewriteModeLabel(platform.result.rewrite_preview.mode) }}
              </span>
            </span>
          </div>
          <button
            v-if="platform.enableAi || platform.result.rewrite_preview.mode === 'deepseek'"
            class="secondary-action"
            :disabled="platform.rewritePreviewLoading"
            @click="platform.refreshRewritePreviewForRecord(true)"
          >
            <Sparkles :size="16" />{{ platform.rewritePreviewLoading ? '生成中…' : '重新生成改写' }}
          </button>
        </div>
        <article v-for="(item, index) in rewriteItems" :key="index" class="rewrite-item">
          <span class="subtle-pill">{{ item.section }}</span>
          <div class="rewrite-compare">
            <div class="rewrite-col original">
              <h4>原文</h4>
              <p>{{ item.original }}</p>
            </div>
            <div class="rewrite-col suggested">
              <div class="rewrite-col-head">
                <h4>参考改写</h4>
                <button type="button" class="text-link copy-btn" @click="handleCopy(item.suggested)">
                  <Copy :size="14" />复制
                </button>
              </div>
              <p>{{ item.suggested }}</p>
            </div>
          </div>
          <small>{{ item.focus }}</small>
        </article>
      </section>
      <section v-else class="panel">
        <div class="panel-heading">
          <h3><Wand2 :size="18" /> 优化版表达预览</h3>
        </div>
        <p class="table-empty">当前记录还没有改写预览，可按需生成 AI 深度改写。</p>
        <button
          class="secondary-action"
          :disabled="platform.rewritePreviewLoading"
          @click="platform.refreshRewritePreviewForRecord(true)"
        >
          <Sparkles :size="16" />{{ platform.rewritePreviewLoading ? '生成中…' : '生成 AI 深度改写' }}
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
            <p><strong>采用岗位：</strong>{{ platform.result.match_result?.target_position || '未识别，使用通用建议' }}</p>
            <p><strong>岗位来源：</strong>{{ platform.targetSourceLabel(platform.result.match_result?.target_source || platform.result.target_position_source) }}</p>
            <p v-if="platform.result.match_confidence"><strong>匹配置信度：</strong>{{ Math.round((platform.result.match_confidence || 0) * 100) }}%</p>
            <p class="match-summary-text">{{ platform.result.match_result?.summary }}</p>
          </div>
        </div>
        <template v-else>
          <p v-if="platform.result.job_profile?.name"><strong>岗位模板：</strong>{{ platform.result.job_profile.name }}</p>
          <p><strong>采用岗位：</strong>{{ platform.result.match_result?.target_position || '未识别，使用通用建议' }}</p>
          <p><strong>岗位来源：</strong>{{ platform.targetSourceLabel(platform.result.match_result?.target_source || platform.result.target_position_source) }}</p>
          <p>{{ platform.result.match_result?.summary }}</p>
        </template>

        <div v-if="platform.result.matched_keywords?.length || platform.result.missing_keywords?.length" class="match-bar-wrap">
          <div class="match-bar">
            <i class="matched" :style="{ width: `${matchRate != null ? matchRate : 50}%` }" />
          </div>
          <div class="match-bar-labels">
            <span>已匹配 {{ platform.result.matched_keywords?.length || 0 }}</span>
            <span>缺失 {{ platform.result.missing_keywords?.length || 0 }}</span>
          </div>
        </div>

        <div v-if="platform.result.matched_keywords?.length" class="keyword-row">
          <span class="keyword-label">已匹配关键词</span>
          <div class="keyword-chips matched">
            <span v-for="word in platform.result.matched_keywords" :key="word">{{ word }}</span>
          </div>
        </div>
        <div v-if="platform.result.missing_keywords?.length" class="keyword-row">
          <span class="keyword-label">缺失关键词</span>
          <div class="keyword-chips missing">
            <span v-for="word in platform.result.missing_keywords" :key="word">{{ word }}</span>
          </div>
        </div>
      </section>

      <section v-if="platform.result.evidence_snippets?.length" class="panel evidence-panel">
        <div class="panel-heading">
          <h3>匹配证据</h3>
          <span class="panel-subtitle">从简历正文中提取的关键词命中片段</span>
        </div>
        <ul class="evidence-list">
          <li v-for="(item, index) in platform.result.evidence_snippets" :key="`${item.keyword}-${index}`">
            <span class="evidence-keyword">{{ item.keyword }}</span>
            <p>{{ item.text }}</p>
          </li>
        </ul>
      </section>
    </section>

    <section :ref="(el) => setSectionRef('reports', el)" class="detail-tab-panel detail-section">
      <section class="panel">
        <div class="panel-heading">
          <h3>报告与原文件</h3>
          <span class="panel-subtitle">评价报告按需生成，优化稿需先有改写预览</span>
        </div>
        <div class="download-actions">
          <a v-if="platform.resolvedSourceResumeUrl(platform.result)" :href="platform.resolvedSourceResumeUrl(platform.result)" target="_blank" rel="noopener noreferrer">
            <FileText :size="16" />查看原简历
          </a>
          <a v-if="docxReportUrl" :href="docxReportUrl" target="_blank">
            <Download :size="16" />下载 Word 报告
          </a>
          <a v-if="pdfReportUrl" :href="pdfReportUrl" target="_blank">
            <Download :size="16" />下载 PDF 报告
          </a>
          <a v-if="rewriteItems.length" :href="rewriteReportUrl(platform.result.record_id)" target="_blank" rel="noopener noreferrer">
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
