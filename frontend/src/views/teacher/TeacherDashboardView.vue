<script setup>
import { BarChart3, GraduationCap, RefreshCw, School, UsersRound } from 'lucide-vue-next'

import TeacherStatsCharts from '../../components/TeacherStatsCharts.vue'
import { usePlatform } from '../../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="admin-stack">
    <p v-if="platform.teacherMessage" class="account-message">{{ platform.teacherMessage }}</p>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>指导数据看板</h3>
          <p class="panel-subtitle">聚合学生画像与评分分布，仅展示统计元数据，不含简历正文。</p>
        </div>
        <button class="secondary-action" :disabled="platform.teacherLoading" @click="platform.loadTeacherData">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div class="admin-metrics">
        <div><UsersRound :size="20" /><span>完善资料学生</span><strong>{{ platform.teacherStats?.summary?.students_with_profile ?? '--' }}</strong></div>
        <div><BarChart3 :size="20" /><span>分析总量</span><strong>{{ platform.teacherStats?.summary?.total_records ?? '--' }}</strong></div>
        <div><GraduationCap :size="20" /><span>今日分析</span><strong>{{ platform.teacherStats?.summary?.today_records ?? '--' }}</strong></div>
        <div><School :size="20" /><span>近 7 日</span><strong>{{ platform.teacherStats?.summary?.week_records ?? '--' }}</strong></div>
        <div><BarChart3 :size="20" /><span>平均得分</span><strong>{{ platform.teacherStats?.summary?.avg_score ?? '--' }}</strong></div>
      </div>
    </section>

    <TeacherStatsCharts :stats="platform.teacherStats" />

    <section class="layout-two">
      <div class="panel">
        <div class="panel-heading"><h3>专业分布</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.by_major || []" :key="item.name">
            <span>{{ item.name }}</span><strong>{{ item.count }}</strong>
          </li>
          <li v-if="!platform.teacherStats?.by_major?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
      <div class="panel">
        <div class="panel-heading"><h3>年级分布</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.by_grade || []" :key="item.name">
            <span>{{ item.name }}</span><strong>{{ item.count }}</strong>
          </li>
          <li v-if="!platform.teacherStats?.by_grade?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading"><h3>热门岗位模板</h3></div>
      <ul class="rank-list">
        <li v-for="item in platform.teacherStats?.top_job_profiles || []" :key="item.name">
          <span>{{ item.name }}</span><strong>{{ item.count }}</strong>
        </li>
        <li v-if="!platform.teacherStats?.top_job_profiles?.length" class="table-empty">暂无数据</li>
      </ul>
    </section>
  </section>
</template>
