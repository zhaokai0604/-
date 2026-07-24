<script setup>
import { defineAsyncComponent } from 'vue'
import { GraduationCap, RefreshCw, UsersRound } from 'lucide-vue-next'

import { usePlatform } from '../../stores/platform'

const ClassStatsCharts = defineAsyncComponent(() => import('../../components/ClassStatsCharts.vue'))

const platform = usePlatform()
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
        <div class="panel-heading"><h3>班级维度共性问题</h3></div>
        <ul class="rank-list issue-list">
          <li v-for="item in platform.teacherClassPanel?.common_issues || []" :key="item.issue">
            <span>{{ item.issue }}</span><strong>{{ item.count }}</strong>
          </li>
          <li v-if="!platform.teacherClassPanel?.common_issues?.length" class="table-empty">暂无数据</li>
        </ul>
      </section>
    </template>
  </section>
</template>
