<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { UploadCloud } from 'lucide-vue-next'

import JobProfileFields from '../components/JobProfileFields.vue'
import { usePlatform } from '../stores/platform'

const AnalysisLiveStream = defineAsyncComponent(() => import('../components/AnalysisLiveStream.vue'))
const platform = usePlatform()

const liveRecordId = ref(null)
const showLive = computed(
  () => Boolean(liveRecordId.value) && (platform.loading || platform.result?.status === 'processing' || platform.detailLoading),
)

watch(
  () => platform.result,
  (value) => {
    if (value?.stream && value?.record_id && value?.status === 'processing') {
      liveRecordId.value = value.record_id
    }
    if (value?.status === 'success' || value?.status === 'failed') {
      // 保留流面板到用户离开前，不再强制清空
    }
  },
  { deep: true },
)

async function onLiveDone() {
  const id = liveRecordId.value || platform.result?.record_id
  if (!id) return
  platform.stopSinglePolling()
  await platform.openRecordById(id)
}

function onLiveError() {
  const id = liveRecordId.value || platform.result?.record_id
  // 后台有约 12s 认领等待后的兜底执行，这里用轮询接住结果
  if (id) platform.startSinglePolling(id)
}
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

      <label class="switch-row target-match-switch">
        <input :checked="platform.enableTargetMatch" type="checkbox" @change="platform.setTargetMatchEnabled($event.target.checked)" />
        <span>指定目标岗位后再匹配（默认关闭：只做通用分析，下方推荐岗可点选）</span>
      </label>

      <section v-if="platform.enableTargetMatch" class="target-match-panel">
        <p v-if="platform.targetPosition" class="target-match-banner">
          将按「{{ platform.targetPosition }}」做岗位匹配。不想套岗请关闭上方开关或点清空。
        </p>
        <JobProfileFields
          :model-value="platform.selectedJobProfileKey"
          :target-position="platform.targetPosition"
          :job-description="platform.jobDescription"
          :profiles="platform.jobProfileOptions"
          :presets="platform.jobProfilePresetOptions"
          @update:model-value="(value) => { platform.handleJobProfileChange(value) }"
          @update:target-position="(value) => { platform.targetPosition = value }"
          @update:job-description="(value) => { platform.jobDescription = value }"
          @clear="platform.clearTargetJobInputs"
        />
      </section>
      <p v-else class="muted-cell target-match-hint">
        当前不会采用任何目标岗。分析完成后可在结果页从推荐列表点选岗位查看专属评价。
      </p>

      <div class="submit-row">
        <button class="primary-action" :disabled="platform.loading">
          <UploadCloud :size="18" />
          {{ platform.loading ? '分析中…' : platform.parentRecordId ? '分析新版本' : '开始分析' }}
        </button>
        <span>{{ platform.enableAi ? '实时推送分析事件并落库，增强分析后台补齐' : '当前使用规则引擎实时分析并落库' }}</span>
      </div>

      <AnalysisLiveStream
        v-if="showLive"
        :record-id="liveRecordId"
        :live="true"
        :auto-play="true"
        @done="onLiveDone"
        @error="onLiveError"
      />
    </form>

    <aside class="context-panel">
      <section class="compact-card single-guide-card">
        <span class="guide-kicker">分析内容</span>
        <strong>您将获得</strong>
        <ul class="clean-list soft-list">
          <li>综合评分与各维度分项得分</li>
          <li>未填目标岗：通用分析 + 相似岗位推荐（点击后再出该岗评价）</li>
          <li>已填目标岗：按意向岗位做匹配度与缺失项分析</li>
          <li>上传后实时推送阅读/匹配事件，完成后直接落库</li>
          <li>在初稿上打磨出可下载优化稿</li>
          <li>开启增强分析时，诊断与优化稿会在后台自动加深</li>
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
    </aside>
  </section>
</template>
