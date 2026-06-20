<script setup>
import { Download, FileText, GitBranch, RefreshCw, UploadCloud } from 'lucide-vue-next'

import ScoreCharts from '../components/ScoreCharts.vue'
import VersionScoreChart from '../components/VersionScoreChart.vue'
import { reportUrl } from '../api/client'
import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <div v-if="platform.detailLoading" class="empty-state">
    <RefreshCw :size="32" class="spin-icon" />
    <strong>正在加载简历详情…</strong>
  </div>
  <div v-else-if="platform.result" class="result-stack">
    <section class="score-strip">
      <div class="score-block">
        <span>总评分</span>
        <strong>{{ platform.result.total_score }}</strong>
        <small>满分 100</small>
      </div>
      <div class="score-meta">
        <strong>{{ platform.result.filename }}</strong>
        <span v-if="platform.result.version_no > 1" class="version-tag">v{{ platform.result.version_no }}</span>
        <span class="mode-tag" :class="platform.result.analysis_mode">{{ platform.result.analysis_mode_label || platform.analysisModeLabel(platform.result.analysis_mode) }}</span>
      </div>
      <div class="download-actions">
        <button class="secondary-action" @click="platform.startNewVersion(platform.result)">
          <UploadCloud :size="16" />上传新版本
        </button>
        <a v-if="platform.resolvedSourceResumeUrl(platform.result)" :href="platform.resolvedSourceResumeUrl(platform.result)" target="_blank" rel="noopener noreferrer">
          <FileText :size="16" />查看简历
        </a>
        <a v-if="platform.result.reports?.docx" :href="reportUrl(platform.result.reports.docx, 'docx')" target="_blank">
          <Download :size="16" />Word
        </a>
        <a v-if="platform.result.reports?.pdf" :href="reportUrl(platform.result.reports.pdf, 'pdf')" target="_blank">
          <Download :size="16" />PDF
        </a>
      </div>
    </section>

    <section v-if="platform.recordVersions.length > 1" class="panel version-panel">
      <div class="panel-heading">
        <h3><GitBranch :size="18" /> 版本历史</h3>
        <span class="panel-subtitle">同一简历的多轮分析与优化记录</span>
      </div>
      <VersionScoreChart :versions="platform.recordVersions" :compare="platform.versionCompare" />
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

    <section v-if="platform.result.parse_quality" :class="['parse-note', platform.result.parse_quality]">
      <div>
        <strong>{{ platform.parseQualityLabel(platform.result.parse_quality) }}</strong>
        <span v-if="platform.result.parse_quality === 'low'">评分仅供参考，请优先检查文件正文是否能被正确提取。</span>
        <span v-else-if="platform.result.parse_quality === 'medium'">已完成分析，建议核对部分模块识别结果。</span>
        <span v-else>正文和核心模块识别较完整。</span>
      </div>
      <ul v-if="platform.result.parse_warnings?.length">
        <li v-for="warning in platform.result.parse_warnings" :key="warning">{{ warning }}</li>
      </ul>
    </section>

    <ScoreCharts :data="platform.result.chart_data" />

    <section class="layout-two">
      <div class="panel">
        <div class="panel-heading"><h3>问题诊断</h3></div>
        <ul class="clean-list"><li v-for="item in platform.result.diagnosis" :key="item">{{ item }}</li></ul>
      </div>
      <div class="panel">
        <div class="panel-heading"><h3>修改建议</h3></div>
        <ul class="clean-list"><li v-for="item in platform.result.suggestions" :key="item">{{ item }}</li></ul>
      </div>
    </section>

    <section class="panel match-panel">
      <div class="panel-heading"><h3>岗位匹配</h3></div>
      <p v-if="platform.result.job_profile?.name"><strong>岗位模板：</strong>{{ platform.result.job_profile.name }}</p>
      <p><strong>采用岗位：</strong>{{ platform.result.match_result?.target_position || '未识别，使用通用建议' }}</p>
      <p><strong>岗位来源：</strong>{{ platform.targetSourceLabel(platform.result.match_result?.target_source || platform.result.target_position_source) }}</p>
      <p v-if="platform.result.match_confidence"><strong>匹配置信度：</strong>{{ Math.round((platform.result.match_confidence || 0) * 100) }}%</p>
      <p>{{ platform.result.match_result?.summary }}</p>

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

    <section v-if="platform.result.blocks?.length" class="panel blocks-panel">
      <div class="panel-heading">
        <h3>结构化模块</h3>
        <span class="panel-subtitle">简历各板块识别结果与置信度</span>
      </div>
      <details v-for="block in platform.result.blocks" :key="block.section" class="block-item">
        <summary>
          <strong>{{ block.section }}</strong>
          <span class="block-confidence">{{ Math.round((block.confidence || 0) * 100) }}%</span>
        </summary>
        <ul>
          <li v-for="(line, idx) in block.lines" :key="idx">{{ line }}</li>
        </ul>
      </details>
    </section>
  </div>
  <section v-else class="empty-state">
    <FileText :size="36" />
    <strong>暂无报告</strong>
    <span>完成分析或从历史记录打开报告后，这里会显示结果。</span>
  </section>
</template>
