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
          <span class="subtle-pill">就业数据治理闭环</span>
          <div class="hero-stat-chips">
            <span><History :size="13" /> {{ platform.historyCount }}</span>
            <span><Download :size="13" /> {{ platform.reportCount }}</span>
          </div>
        </div>
        <h3>从个人诊断到班级洞察<br />再到岗位与简历质量沉淀</h3>
        <p>学生获得诊断与修改建议，教师看见班级共性问题，学校沉淀岗位需求与简历质量数据。</p>
        <div class="hero-feature-row">
          <span class="hero-feature-pill"><FileText :size="14" />学生诊断</span>
          <span class="hero-feature-pill"><BriefcaseBusiness :size="14" />岗位适配</span>
          <span class="hero-feature-pill"><History :size="14" />班级洞察</span>
          <span class="hero-feature-pill"><Download :size="14" />报告沉淀</span>
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
          <button v-else type="button" class="hero-score-empty" @click="platform.setActiveTab('single')">
            <FileText :size="32" />
            <span>上传第一份简历</span>
          </button>
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

    <section class="journey-grid platform-workflow">
      <article class="journey-card">
        <span class="journey-step">01</span>
        <strong>学生上传简历</strong>
        <p>完成结构化解析，沉淀可复用的简历资产。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">02</span>
        <strong>对接岗位要求</strong>
        <p>选用岗位模板或公开岗位库，明确适配依据。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">03</span>
        <strong>诊断与修改建议</strong>
        <p>多维评分、证据匹配与可执行修改建议。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">04</span>
        <strong>优化稿与面试训练</strong>
        <p>依据材料补强表达，并生成模拟面试题。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">05</span>
        <strong>教师班级洞察</strong>
        <p>汇总共性问题、热门岗位与评分分布。</p>
      </article>
      <article class="journey-card">
        <span class="journey-step">06</span>
        <strong>学校数据沉淀</strong>
        <p>岗位需求与简历质量数据持续沉淀，服务就业治理。</p>
      </article>
    </section>

    <section v-if="platform.auth.authenticated" class="panel profile-summary-panel">
      <div class="panel-heading">
        <div>
          <h3>个人资料</h3>
          <p class="panel-subtitle">完善学校与专业信息，便于教师端统计分析。</p>
        </div>
        <button class="secondary-action" type="button" @click="platform.openSettingsPanel()">编辑资料</button>
      </div>
      <dl class="kv-list">
        <div><dt>学校</dt><dd>{{ platform.userProfile.school || '未填写' }}</dd></div>
        <div><dt>专业</dt><dd>{{ platform.userProfile.major || '未填写' }}</dd></div>
        <div><dt>年级</dt><dd>{{ platform.userProfile.grade || '未填写' }}</dd></div>
        <div><dt>班级</dt><dd>{{ platform.userProfile.class_name || '未填写' }}</dd></div>
      </dl>
    </section>

    <section class="dashboard-grid">
      <div class="panel">
        <div class="panel-heading">
          <div>
            <h3>平台能力</h3>
            <p class="panel-subtitle">围绕就业数据治理，覆盖学生、教师与学校三类使用场景。</p>
          </div>
        </div>
        <div class="roadmap-list">
          <div><strong>01</strong><span>学生端：诊断问题、给出修改建议与优化稿。</span></div>
          <div><strong>02</strong><span>教师端：班级共性问题、均分与热门岗位洞察。</span></div>
          <div><strong>03</strong><span>学校侧：岗位需求与简历质量数据可沉淀、可复盘。</span></div>
          <div><strong>04</strong><span>分析可信度提示：证据不足时主动降置信，不盲目高分。</span></div>
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
