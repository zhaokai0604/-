<script setup>
import {
  Archive,
  BriefcaseBusiness,
  Download,
  FileText,
  History,
  UploadCloud,
} from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="dashboard-stack">
    <section class="dashboard-hero">
      <div class="dashboard-hero-copy">
        <div class="hero-top-row">
          <span class="subtle-pill">AI 驱动 · 简历分析</span>
          <div class="hero-stat-chips">
            <span><History :size="13" /> {{ platform.historyCount }}</span>
            <span><Download :size="13" /> {{ platform.reportCount }}</span>
          </div>
        </div>
        <h3>让每一份简历<br />都更接近目标岗位</h3>
        <p>上传简历，智能评分、诊断问题、匹配岗位，导出专业分析报告。</p>
        <div class="hero-feature-row">
          <span class="hero-feature-pill"><FileText :size="14" />智能解析</span>
          <span class="hero-feature-pill"><BriefcaseBusiness :size="14" />岗位匹配</span>
          <span class="hero-feature-pill"><Download :size="14" />报告导出</span>
        </div>
        <div class="panel-actions">
          <button class="primary-action hero-cta" @click="platform.setActiveTab('single')">
            <UploadCloud :size="18" />开始分析
          </button>
          <button class="ghost-action" @click="platform.setActiveTab('batch')">
            <Archive :size="16" />批量分析
          </button>
        </div>
      </div>
      <div class="dashboard-hero-side">
        <div class="hero-side-card">
          <div class="hero-score-ring" v-if="platform.latestResumeRecord">
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" class="ring-bg" />
              <circle
                cx="60" cy="60" r="52"
                class="ring-fill"
                :style="{ strokeDashoffset: 327 - (platform.latestResumeRecord.total_score / 100) * 327 }"
              />
            </svg>
            <div class="hero-score-value">
              <strong>{{ platform.latestResumeRecord.total_score }}</strong>
              <small>最近评分</small>
            </div>
          </div>
          <div v-else class="hero-score-empty">
            <FileText :size="32" />
            <span>上传第一份简历</span>
          </div>
          <dl class="hero-side-list">
            <div><dt>身份</dt><dd>{{ platform.currentIdentityLabel }}</dd></div>
            <div><dt>模式</dt><dd>{{ platform.modeLabel }}</dd></div>
            <div><dt>状态</dt><dd>{{ platform.latestTaskState }}</dd></div>
          </dl>
          <button
            v-if="platform.latestResumeRecord"
            class="secondary-action full-width"
            @click="platform.openRecord(platform.latestResumeRecord)"
          >
            <FileText :size="15" />继续查看「{{ platform.latestResumeRecord.filename }}」
          </button>
        </div>
      </div>
    </section>

    <section class="dashboard-metric-grid">
      <button
        v-for="card in platform.dashboardCards"
        :key="card.label"
        class="metric-card"
        type="button"
        @click="platform.setActiveTab(card.tab)"
      >
        <component :is="card.icon" :size="20" class="metric-icon" />
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </button>
    </section>

    <section class="journey-grid">
      <article class="journey-card">
        <span class="journey-step">01</span>
        <strong>上传简历</strong>
        <p>支持 Word / PDF 格式，上传当前要投递的简历版本。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">02</span>
        <strong>匹配岗位</strong>
        <p>选择岗位模板或粘贴 JD，让评分围绕真实投递方向展开。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">03</span>
        <strong>查看报告</strong>
        <p>获取评分、诊断与修改建议，导出报告指导下一轮优化。</p>
      </article>
    </section>

    <section class="dashboard-grid">
      <div class="panel">
        <div class="panel-heading">
          <div>
            <h3>平台能力</h3>
            <p class="panel-subtitle">从上传到导出，覆盖简历分析全流程。</p>
          </div>
        </div>
        <div class="roadmap-list">
          <div><strong>01</strong><span>历史记录持久保存，支持随时回看、对比与导出。</span></div>
          <div><strong>02</strong><span>岗位模板一键复用，无需每次重新填写 JD。</span></div>
          <div><strong>03</strong><span>多格式报告导出，便于修改简历与面试准备。</span></div>
          <div><strong>04</strong><span>账号数据隔离，分析记录安全可靠。</span></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-heading">
          <div>
            <h3>最近分析</h3>
            <p class="panel-subtitle">快速继续上一次的简历优化工作。</p>
          </div>
        </div>
        <div v-if="platform.latestResumeRecord" class="resume-highlight">
          <strong>{{ platform.latestResumeRecord.filename }}</strong>
          <span>目标岗位：{{ platform.latestResumeRecord.target_position || '未填写' }}</span>
          <span>综合评分：{{ platform.latestResumeRecord.total_score }} 分</span>
          <div class="panel-actions">
            <button class="secondary-action" @click="platform.openRecord(platform.latestResumeRecord)">
              <FileText :size="16" />查看详情
            </button>
            <a
              v-if="platform.resolvedSourceResumeUrl(platform.latestResumeRecord)"
              class="secondary-action"
              :href="platform.resolvedSourceResumeUrl(platform.latestResumeRecord)"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download :size="16" />原文件
            </a>
          </div>
        </div>
        <section v-else class="empty-inline">
          暂无分析记录，点击「开始分析」上传第一份简历。
        </section>
      </div>
    </section>
  </section>
</template>
