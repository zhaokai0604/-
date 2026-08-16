<script setup>
import { computed, defineAsyncComponent, ref } from 'vue'
import { ClipboardList, GraduationCap, RefreshCw, UsersRound } from 'lucide-vue-next'

import { createTeacherTrainingTask } from '../../api/client'
import { usePlatform } from '../../stores/platform'

const ClassStatsCharts = defineAsyncComponent(() => import('../../components/ClassStatsCharts.vue'))

const platform = usePlatform()
const trainingLoading = ref(false)
const trainingTask = ref(null)
const trainingError = ref('')
const copyNotice = ref('')

const commonIssues = computed(() => platform.teacherClassPanel?.common_issues || [])

async function createTask(issue, className = '') {
  trainingLoading.value = true
  trainingError.value = ''
  copyNotice.value = ''
  try {
    const payload = await createTeacherTrainingTask({ issue, class_name: className })
    trainingTask.value = payload.task || payload
  } catch (err) {
    trainingError.value = err.message || '生成训练任务失败'
  } finally {
    trainingLoading.value = false
  }
}

async function copyStudentMessage() {
  const text = trainingTask.value?.student_message
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copyNotice.value = '已复制给学生推送文案（不含简历正文）'
  } catch {
    copyNotice.value = '复制失败，请手动选择文本'
  }
}
</script>

<template>
  <section class="admin-stack">
    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>班级分析面板</h3>
          <p class="panel-subtitle">按班级聚合学生人数、分析量与均分，辅助就业指导分班施策。</p>
        </div>
        <button class="secondary-action" :disabled="platform.teacherClassLoading" @click="platform.loadTeacherClassData">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div class="admin-metrics">
        <div><GraduationCap :size="20" /><span>班级数</span><strong>{{ platform.teacherClassPanel?.summary?.class_count ?? '--' }}</strong></div>
        <div><UsersRound :size="20" /><span>建档学生</span><strong>{{ platform.teacherClassPanel?.summary?.students_with_profile ?? '--' }}</strong></div>
        <div><GraduationCap :size="20" /><span>分析总量</span><strong>{{ platform.teacherClassPanel?.summary?.total_records ?? '--' }}</strong></div>
      </div>
    </section>

    <section v-if="platform.teacherClassLoading" class="empty-state compact">
      <RefreshCw :size="28" class="spin-icon" />
      <span>正在加载班级数据…</span>
    </section>

    <template v-else>
      <ClassStatsCharts :classes="platform.teacherClassPanel?.classes || []" />

      <section class="panel">
        <div class="panel-heading"><h3>班级明细</h3></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>班级</th><th>学生</th><th>分析量</th><th>均分</th><th>专业</th><th>热门岗位</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in platform.teacherClassPanel?.classes || []" :key="item.name">
                <td>{{ item.name }}</td>
                <td>{{ item.student_count }}</td>
                <td>{{ item.record_count }}</td>
                <td>{{ item.avg_score || '-' }}</td>
                <td>{{ item.majors?.join('、') || '-' }}</td>
                <td>{{ item.top_positions?.map((row) => row.name).join('、') || '-' }}</td>
              </tr>
              <tr v-if="!platform.teacherClassPanel?.classes?.length">
                <td colspan="6" class="table-empty">暂无班级数据，请引导学生完善「班级」资料。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <div>
            <h3>班级维度共性问题</h3>
            <span class="panel-subtitle">可一键生成专题训练任务（只推模板，不暴露简历正文）</span>
          </div>
        </div>
        <ul class="rank-list issue-list">
          <li v-for="item in commonIssues" :key="item.issue" class="issue-with-action">
            <span>{{ item.issue }}</span>
            <div class="issue-actions">
              <strong>{{ item.count }}</strong>
              <button
                type="button"
                class="secondary-action"
                :disabled="trainingLoading"
                @click="createTask(item.issue)"
              >
                <ClipboardList :size="14" />一键成课
              </button>
            </div>
          </li>
          <li v-if="!commonIssues.length" class="table-empty">暂无数据</li>
        </ul>
        <p v-if="trainingError" class="form-error">{{ trainingError }}</p>
        <p v-if="copyNotice" class="copy-notice">{{ copyNotice }}</p>
      </section>

      <section v-if="trainingTask" class="panel training-task-panel">
        <div class="panel-heading">
          <div>
            <h3>{{ trainingTask.title }}</h3>
            <span class="panel-subtitle">
              {{ trainingTask.class_name }} · 覆盖约 {{ trainingTask.coverage_percent }}%
              （{{ trainingTask.affected_count }} 条相关诊断）
            </span>
          </div>
          <button type="button" class="primary-action" @click="copyStudentMessage">复制推送文案</button>
        </div>
        <p><strong>训练目标：</strong>{{ trainingTask.goal }}</p>
        <p><strong>任务安排：</strong>{{ trainingTask.tasks }}</p>
        <p><strong>验收标准：</strong>{{ trainingTask.checklist }}</p>
        <p class="panel-subtitle">{{ trainingTask.privacy_note }}</p>
        <pre class="training-message">{{ trainingTask.student_message }}</pre>
      </section>
    </template>
  </section>
</template>
