<script setup>
import { UploadCloud } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="analysis-layout">
    <form class="panel form-panel upload-panel" @submit.prevent="platform.submitSingle">
      <div class="panel-heading">
        <h3>上传简历</h3>
        <span class="subtle-pill">DOCX / PDF</span>
      </div>

      <section v-if="platform.parentRecordId" class="version-upload-banner">
        <div>
          <strong>正在创建新版本</strong>
          <p>基于 {{ platform.parentRecordLabel }} 上传修改后的简历，系统将自动关联版本链。</p>
        </div>
        <button type="button" class="secondary-action" @click="platform.clearNewVersion">取消</button>
      </section>

      <label class="file-drop" @dragover="platform.onDragOver" @drop="platform.onFileDrop($event, 'single')">
        <input type="file" accept=".docx,.pdf" @change="platform.onSingleFile" />
        <UploadCloud :size="30" />
        <strong>{{ platform.singleFile?.name || (platform.parentRecordId ? '上传修改后的简历文件' : '点击或拖拽上传简历') }}</strong>
        <span>支持 Word / PDF 格式，文件安全存储于本地</span>
      </label>

      <div class="form-grid">
        <label class="field">
          <span>岗位模板</span>
          <select v-model.number="platform.selectedJobProfileId" @change="platform.handleJobProfileChange">
            <option :value="0">不使用模板，手动填写</option>
            <option v-for="profile in platform.jobProfileOptions" :key="profile.id" :value="profile.id">
              {{ profile.optionLabel }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>目标岗位</span>
          <input v-model="platform.targetPosition" placeholder="例如：数据分析师、产品经理、运营实习生" />
        </label>

        <label class="field">
          <span>岗位 JD</span>
          <textarea v-model="platform.jobDescription" rows="9" placeholder="粘贴岗位要求，用于计算岗位匹配度。"></textarea>
        </label>
      </div>

      <div class="submit-row">
        <button class="primary-action" :disabled="platform.loading">
          <UploadCloud :size="18" />
          {{ platform.loading ? '分析中…' : platform.parentRecordId ? '分析新版本' : '开始分析' }}
        </button>
        <span>{{ platform.enableAi ? 'AI 分析失败时自动切换规则引擎' : '当前使用规则引擎分析' }}</span>
      </div>
    </form>

    <aside class="context-panel">
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">分析内容</span>
        <strong>您将获得</strong>
        <ul class="clean-list soft-list">
          <li>综合评分与各维度分项得分</li>
          <li>岗位匹配度与缺失关键词</li>
          <li>问题诊断与具体修改建议</li>
        </ul>
      </section>
      <section v-if="platform.parentRecordId" class="compact-card single-guide-card">
        <span class="guide-kicker">版本管理</span>
        <strong>新版本说明</strong>
        <p>上传修改后的简历将自动成为 v{{ (platform.result?.version_no || 1) + 1 }}，可在详情页查看版本时间线并对比得分变化。</p>
      </section>
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">使用建议</span>
        <strong>推荐流程</strong>
        <ul class="clean-list soft-list">
          <li>先上传主简历，再填写目标岗位</li>
          <li>重点关注缺失关键词与诊断建议</li>
          <li>确认结果后导出报告，指导修改方向</li>
        </ul>
      </section>
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">隐私保护</span>
        <strong>数据安全</strong>
        <p>简历文件仅存储在本地，删除记录时同步清理。开启 AI 分析时优先使用智能诊断，不可用时自动回退规则引擎。</p>
      </section>
    </aside>
  </section>
</template>
