<script setup>
import { UploadCloud } from 'lucide-vue-next'

import JobProfileFields from '../components/JobProfileFields.vue'
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

      <JobProfileFields
        :model-value="platform.selectedJobProfileKey"
        :target-position="platform.targetPosition"
        :job-description="platform.jobDescription"
        :profiles="platform.jobProfileOptions"
        :presets="platform.jobProfilePresetOptions"
        @update:model-value="(value) => { platform.handleJobProfileChange(value) }"
        @update:target-position="(value) => { platform.targetPosition = value }"
        @update:job-description="(value) => { platform.jobDescription = value }"
      />

      <div class="submit-row">
        <button class="primary-action" :disabled="platform.loading">
          <UploadCloud :size="18" />
          {{ platform.loading ? '分析中…' : platform.parentRecordId ? '分析新版本' : '开始分析' }}
        </button>
        <span>{{ platform.enableAi ? '约 5 秒先出基础分析，AI 优化后台补齐' : '当前使用规则引擎分析' }}</span>
      </div>
    </form>

    <aside class="context-panel">
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">分析内容</span>
        <strong>您将获得</strong>
        <ul class="clean-list soft-list">
          <li>综合评分与各维度分项得分</li>
          <li>岗位匹配度、关键词覆盖与缺失项</li>
          <li>约 5 秒生成基础诊断、修改建议与规则改写参考</li>
          <li>开启 AI 时，深度诊断与改写会在后台自动补齐</li>
          <li>简历模板推荐与优化稿导出</li>
          <li>Word / PDF 评价报告一键导出</li>
        </ul>
      </section>
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">识别质量</span>
        <strong>上传建议</strong>
        <ul class="clean-list soft-list">
          <li>优先使用标准 DOCX 或可选中复制的 PDF</li>
          <li>避免纯图片/扫描版，否则识别准确率会下降</li>
          <li>板块标题建议用「教育背景」「实习经历」等常见写法</li>
          <li>文件名可含岗位方向，如「姓名-求职简历(平面设计).docx」</li>
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
          <li>重点关注缺失关键词与诊断与优化建议</li>
          <li>确认结果后导出报告，指导修改方向</li>
        </ul>
      </section>
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">隐私保护</span>
        <strong>数据安全</strong>
        <p>简历文件仅存储在本地，删除记录时同步清理。开启 AI 时先展示基础分析，智能诊断与改写稍后自动更新。</p>
      </section>
    </aside>
  </section>
</template>
