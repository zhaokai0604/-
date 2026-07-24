<script setup>
import { defineAsyncComponent } from 'vue'
import { BarChart3, Download, GraduationCap, RefreshCw, School, UsersRound } from 'lucide-vue-next'

const TeacherStatsCharts = defineAsyncComponent(() => import('../../components/TeacherStatsCharts.vue'))
import { teacherStatsExportUrl } from '../../api/client'
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
        <div class="panel-actions">
          <a class="secondary-action" :href="teacherStatsExportUrl()" target="_blank" rel="noopener noreferrer">
            <Download :size="16" />导出 CSV
          </a>
          <button class="secondary-action" :disabled="platform.teacherLoading" @click="platform.loadTeacherData">
            <RefreshCw :size="16" />刷新
          </button>
        </div>
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
        <div class="panel-heading"><h3>专业均分</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.score_by_major || []" :key="`score-${item.name}`">
            <span>{{ item.name }}</span><strong>{{ item.avg_score }} 分 · {{ item.count }} 份</strong>
          </li>
          <li v-if="!platform.teacherStats?.score_by_major?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
    </section>

    <section class="layout-two">
      <div class="panel">
        <div class="panel-heading"><h3>班级分布</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.by_class || []" :key="`class-${item.name}`">
            <span>{{ item.name }}</span><strong>{{ item.count }}</strong>
          </li>
          <li v-if="!platform.teacherStats?.by_class?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
      <div class="panel">
        <div class="panel-heading"><h3>班级均分</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.score_by_class || []" :key="`class-score-${item.name}`">
            <span>{{ item.name }}</span><strong>{{ item.avg_score }} 分 · {{ item.count }} 份</strong>
          </li>
          <li v-if="!platform.teacherStats?.score_by_class?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
    </section>

    <section class="layout-two">
      <div class="panel">
        <div class="panel-heading"><h3>年级分布</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.by_grade || []" :key="item.name">
            <span>{{ item.name }}</span><strong>{{ item.count }}</strong>
          </li>
          <li v-if="!platform.teacherStats?.by_grade?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
      <div class="panel">
        <div class="panel-heading"><h3>年级均分</h3></div>
        <ul class="rank-list">
          <li v-for="item in platform.teacherStats?.score_by_grade || []" :key="`grade-score-${item.name}`">
            <span>{{ item.name }}</span><strong>{{ item.avg_score }} 分 · {{ item.count }} 份</strong>
          </li>
          <li v-if="!platform.teacherStats?.score_by_grade?.length" class="table-empty">暂无数据</li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading"><h3>共性问题 Top</h3></div>
      <ul class="rank-list issue-list">
        <li v-for="item in platform.teacherStats?.common_issues || []" :key="item.issue">
          <span>{{ item.issue }}</span><strong>{{ item.count }}</strong>
        </li>
        <li v-if="!platform.teacherStats?.common_issues?.length" class="table-empty">暂无数据</li>
      </ul>
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
