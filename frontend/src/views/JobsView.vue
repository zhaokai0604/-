<script setup>
import { computed, ref, watch } from 'vue'
import { BriefcaseBusiness, ChevronDown, ChevronUp, RefreshCw, Sparkles, Trash2 } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
const selectedPresetCategory = ref('全部')
const selectedMarketCity = ref('全部')
const selectedMarketCategory = ref('全部')
const selectedMarketEducation = ref('全部')
const marketKeyword = ref('')
const expandedJobId = ref('')

const EDUCATION_BUCKETS = [
  { id: '硕士', match: (text) => /硕士|研究生|博士/.test(text) },
  { id: '本科', match: (text) => /本科|学士/.test(text) },
  { id: '大专', match: (text) => /大专|专科|高职/.test(text) },
  { id: '中专', match: (text) => /中专|中技/.test(text) },
  { id: '不限', match: (text) => !text || /不限|未明确|未显示|初中/.test(text) },
]

const presetCategories = computed(() => [
  '全部',
  ...Array.from(new Set(platform.jobProfilePresets.map((item) => item.category).filter(Boolean))),
])

const filteredPresets = computed(() => {
  if (selectedPresetCategory.value === '全部') {
    return platform.jobProfilePresets
  }
  return platform.jobProfilePresets.filter((item) => item.category === selectedPresetCategory.value)
})

function normalizeEducation(raw) {
  const text = String(raw || '').trim()
  for (const bucket of EDUCATION_BUCKETS) {
    if (bucket.id !== '不限' && bucket.match(text)) return bucket.id
  }
  return '不限'
}

function countBy(items, getter) {
  const counter = new Map()
  for (const item of items) {
    const key = getter(item) || '未分类'
    counter.set(key, (counter.get(key) || 0) + 1)
  }
  return [...counter.entries()]
    .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), 'zh'))
    .map(([value, count]) => ({ value, count }))
}

const marketCities = computed(() => [
  { value: '全部', count: platform.jobMarket.length },
  ...countBy(platform.jobMarket, (item) => item.city || '全国'),
])

const marketCategories = computed(() => [
  { value: '全部', count: platform.jobMarket.length },
  ...countBy(platform.jobMarket, (item) => item.category || '未分类'),
])

const marketEducations = computed(() => {
  const buckets = EDUCATION_BUCKETS.map((bucket) => ({
    value: bucket.id,
    count: platform.jobMarket.filter((item) => normalizeEducation(item.education) === bucket.id).length,
  })).filter((item) => item.count > 0)
  return [{ value: '全部', count: platform.jobMarket.length }, ...buckets]
})

const filteredMarketJobs = computed(() => {
  const keyword = marketKeyword.value.trim().toLowerCase()
  return platform.jobMarket.filter((item) => {
    if (selectedMarketCity.value !== '全部' && (item.city || '全国') !== selectedMarketCity.value) {
      return false
    }
    if (selectedMarketCategory.value !== '全部' && (item.category || '未分类') !== selectedMarketCategory.value) {
      return false
    }
    if (selectedMarketEducation.value !== '全部' && normalizeEducation(item.education) !== selectedMarketEducation.value) {
      return false
    }
    if (!keyword) return true
    const haystack = [item.target_position, item.company, item.category, ...(item.must_skills || [])]
      .join(' ')
      .toLowerCase()
    return haystack.includes(keyword)
  })
})

watch(
  () => platform.jobMarket.length,
  () => {
    if (selectedMarketCity.value !== '全部' && !marketCities.value.some((item) => item.value === selectedMarketCity.value)) {
      selectedMarketCity.value = '全部'
    }
    if (selectedMarketCategory.value !== '全部' && !marketCategories.value.some((item) => item.value === selectedMarketCategory.value)) {
      selectedMarketCategory.value = '全部'
    }
    if (selectedMarketEducation.value !== '全部' && !marketEducations.value.some((item) => item.value === selectedMarketEducation.value)) {
      selectedMarketEducation.value = '全部'
    }
  },
)

function resetMarketFilters() {
  selectedMarketCity.value = '全部'
  selectedMarketCategory.value = '全部'
  selectedMarketEducation.value = '全部'
  marketKeyword.value = ''
  expandedJobId.value = ''
}

async function refreshMarketJobs() {
  platform.jobMarketFilters.city = ''
  platform.jobMarketFilters.category = ''
  platform.jobMarketFilters.education = ''
  await platform.loadJobMarket()
}

function toggleJobDetails(jobId) {
  expandedJobId.value = expandedJobId.value === jobId ? '' : jobId
}

function listPreview(items, fallback, limit = 4) {
  const values = Array.isArray(items)
    ? items.filter((item) => {
        const text = String(item || '').trim()
        if (!text) return false
        return !/岗位详情已核验|技能需人工复核|待人工复核|技能待补充/.test(text)
      })
    : []
  if (!values.length) return fallback
  return values.slice(0, limit).join('、')
}

function getJobSummary(job) {
  const parts = []
  const must = listPreview(job?.must_skills, '', 4)
  const nice = listPreview(job?.nice_skills, '', 3)
  const resp = listPreview(job?.responsibilities, '', 1)
  if (must) parts.push(`必备：${must}`)
  if (nice) parts.push(`加分：${nice}`)
  if (resp) parts.push(`职责：${resp}`)
  if (parts.length) return parts.join(' · ')
  return job?.requirement_summary || job?.description || '职责已收录，技能摘要待补充'
}

function getRequirementTags(job) {
  return [
    job?.category || '岗位',
    normalizeEducation(job?.education),
    job?.experience || '经验不限',
  ]
}
</script>

<template>
  <section class="jobs-stack">
    <section class="panel preset-library-panel">
      <div class="panel-heading">
        <div>
          <h3>推荐岗位模板</h3>
          <p class="panel-subtitle">系统内置常见校招 / 实习岗位，可直接套用分析，也可保存到自己的岗位库继续编辑。</p>
        </div>
        <button class="secondary-action" :disabled="platform.jobsLoading" @click="platform.loadJobProfileCatalog">
          <RefreshCw :size="16" />刷新
        </button>
      </div>

      <div class="preset-filter-row">
        <button
          v-for="category in presetCategories"
          :key="category"
          type="button"
          class="preset-filter"
          :class="{ active: selectedPresetCategory === category }"
          @click="selectedPresetCategory = category"
        >
          {{ category }}
        </button>
      </div>

      <div v-if="filteredPresets.length" class="preset-card-grid">
        <article v-for="preset in filteredPresets" :key="preset.id" class="preset-card">
          <div class="preset-card-head">
            <div class="card-head-line">
              <span class="mode-tag ai">{{ preset.category || '岗位模板' }}</span>
              <strong>{{ preset.name }}</strong>
            </div>
            <small>{{ preset.target_position }}</small>
          </div>
          <p class="card-summary">{{ preset.requirement_summary }}</p>
          <div class="preset-card-actions">
            <button type="button" class="secondary-action" @click="platform.usePresetForAnalysis(preset)">
              <Sparkles :size="16" />套用分析
            </button>
            <button type="button" class="secondary-action" :disabled="platform.jobsLoading" @click="platform.savePresetToMyProfiles(preset)">
              <BriefcaseBusiness :size="16" />保存到我的岗位库
            </button>
          </div>
        </article>
      </div>
      <div v-else class="empty-inline">暂无系统岗位模板。</div>
    </section>

    <section class="panel preset-library-panel">
      <div class="panel-heading">
        <div>
          <h3>真实公开岗位库</h3>
          <p class="panel-subtitle">仅展示已核验的公开详情页岗位。可用城市 / 类别 / 学历筛选，搜索结果候选不进入核心匹配。</p>
        </div>
        <div class="panel-actions">
          <button class="secondary-action" type="button" @click="resetMarketFilters">重置筛选</button>
          <button class="secondary-action" :disabled="platform.jobsLoading" @click="refreshMarketJobs">
            <RefreshCw :size="16" />刷新
          </button>
        </div>
      </div>

      <div class="market-filter-stack">
        <div class="market-filter-group">
          <span class="market-filter-label">城市</span>
          <div class="preset-filter-row">
            <button
              v-for="item in marketCities"
              :key="`city-${item.value}`"
              type="button"
              class="preset-filter"
              :class="{ active: selectedMarketCity === item.value }"
              @click="selectedMarketCity = item.value"
            >
              {{ item.value }} · {{ item.count }}
            </button>
          </div>
        </div>

        <div class="market-filter-group">
          <span class="market-filter-label">类别</span>
          <div class="preset-filter-row">
            <button
              v-for="item in marketCategories"
              :key="`cat-${item.value}`"
              type="button"
              class="preset-filter"
              :class="{ active: selectedMarketCategory === item.value }"
              @click="selectedMarketCategory = item.value"
            >
              {{ item.value }} · {{ item.count }}
            </button>
          </div>
        </div>

        <div class="market-filter-group">
          <span class="market-filter-label">学历</span>
          <div class="preset-filter-row">
            <button
              v-for="item in marketEducations"
              :key="`edu-${item.value}`"
              type="button"
              class="preset-filter"
              :class="{ active: selectedMarketEducation === item.value }"
              @click="selectedMarketEducation = item.value"
            >
              {{ item.value }} · {{ item.count }}
            </button>
          </div>
        </div>

        <label class="field market-search-field">
          <span>关键词</span>
          <input v-model.trim="marketKeyword" placeholder="搜岗位名 / 公司 / 技能，如：测试、Java、运营" />
        </label>
      </div>

      <div class="submit-row market-result-meta">
        <span>
          共 {{ platform.jobMarketTotal || platform.jobMarket.length }} 条核验岗位 ·
          当前显示 {{ filteredMarketJobs.length }} 条
        </span>
      </div>

      <div v-if="filteredMarketJobs.length" class="preset-card-grid market-card-grid">
        <article v-for="job in filteredMarketJobs" :key="job.id" class="preset-card job-card" :class="{ expanded: expandedJobId === job.id }">
          <div class="preset-card-head">
            <div class="card-head-line">
              <span class="mode-tag success">{{ job.city || '全国' }}</span>
              <strong>{{ job.target_position }}</strong>
            </div>
            <small>{{ job.company || '公开岗位' }}</small>
          </div>

          <div class="job-meta-row">
            <span v-for="tag in getRequirementTags(job)" :key="tag">{{ tag }}</span>
          </div>

          <p class="card-summary">{{ getJobSummary(job) }}</p>

          <div class="preset-card-actions job-card-actions">
            <button type="button" class="secondary-action" @click="platform.usePublicJobForAnalysis(job)">
              <Sparkles :size="16" />套用分析
            </button>
            <a class="secondary-action" :href="job.source_url" target="_blank" rel="noreferrer">查看来源</a>
            <button type="button" class="secondary-action" @click="toggleJobDetails(job.id)">
              <component :is="expandedJobId === job.id ? ChevronUp : ChevronDown" :size="16" />
              {{ expandedJobId === job.id ? '收起详情' : '展开详情' }}
            </button>
          </div>

          <div v-if="expandedJobId === job.id" class="job-detail">
            <div v-if="job.must_skills?.length" class="job-detail-block">
              <strong>必备技能</strong>
              <p>{{ job.must_skills.join('、') }}</p>
            </div>
            <div v-if="job.nice_skills?.length" class="job-detail-block">
              <strong>加分技能</strong>
              <p>{{ job.nice_skills.join('、') }}</p>
            </div>
            <div v-if="job.responsibilities?.length" class="job-detail-block">
              <strong>岗位职责</strong>
              <p>{{ job.responsibilities.join('；') }}</p>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="empty-inline">暂无符合条件的真实详情页岗位，试试切换筛选或清空关键词。</div>
    </section>

    <section class="analysis-layout">
      <form class="panel form-panel" @submit.prevent="platform.submitJobProfile">
        <div class="panel-heading">
          <div>
            <h3>{{ platform.editingJobProfileId ? '编辑岗位模板' : '新建岗位模板' }}</h3>
            <p class="panel-subtitle">把常用 JD、岗位要求和岗位名称沉淀下来，后续分析直接复用。</p>
          </div>
          <div class="panel-actions">
            <button v-if="platform.editingJobProfileId" class="secondary-action" type="button" @click="platform.resetJobProfileForm">
              <RefreshCw :size="16" />新建一条
            </button>
          </div>
        </div>

        <p v-if="platform.jobsMessage" class="account-message">{{ platform.jobsMessage }}</p>

        <div class="form-grid">
          <label class="field">
            <span>模板名称</span>
            <input v-model.trim="platform.jobProfileForm.name" placeholder="例如：数据分析岗校招模板" />
          </label>
          <label class="field">
            <span>岗位分类</span>
            <input v-model.trim="platform.jobProfileForm.category" placeholder="例如：数据 / 产品 / 运营 / 前端" />
          </label>
          <label class="field">
            <span>目标岗位</span>
            <input v-model.trim="platform.jobProfileForm.targetPosition" placeholder="例如：数据分析师" />
          </label>
          <label class="field">
            <span>状态</span>
            <select v-model="platform.jobProfileForm.status">
              <option value="active">启用</option>
              <option value="draft">草稿</option>
            </select>
          </label>
        </div>

        <label class="field">
          <span>岗位要求摘要</span>
          <textarea v-model="platform.jobProfileForm.requirementSummary" rows="7" placeholder="提炼最关键的岗位要求、技能关键词和业务场景。"></textarea>
        </label>
        <label class="field">
          <span>补充说明</span>
          <textarea v-model="platform.jobProfileForm.description" rows="6" placeholder="可记录更多上下文，例如岗位画像、关注点、评估口径。"></textarea>
        </label>

        <div class="submit-row">
          <button class="primary-action" :disabled="platform.jobsLoading">
            <BriefcaseBusiness :size="18" />
            {{ platform.jobsLoading ? '保存中...' : platform.editingJobProfileId ? '更新模板' : '保存模板' }}
          </button>
          <span>保存后可在单份分析和批量分析页面直接复用。</span>
        </div>
      </form>

      <section class="panel batch-result-panel">
        <div class="panel-heading">
          <div>
            <h3>已保存岗位模板</h3>
            <p class="panel-subtitle">当前账号下共 {{ platform.jobProfileCount }} 条岗位模板。</p>
          </div>
          <button class="secondary-action" :disabled="platform.jobsLoading" @click="platform.loadJobProfiles">
            <RefreshCw :size="16" />刷新
          </button>
        </div>

        <div v-if="platform.jobProfiles.length" class="table-wrap batch-result-table">
          <table class="data-table">
            <thead>
              <tr>
                <th>模板</th>
                <th>目标岗位</th>
                <th>分类</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="profile in platform.jobProfiles" :key="profile.id">
                <td>
                  <strong>{{ profile.name }}</strong>
                  <div class="muted-cell">{{ profile.requirement_summary || profile.description || '暂无摘要' }}</div>
                </td>
                <td>{{ profile.target_position || '-' }}</td>
                <td>{{ profile.category || '-' }}</td>
                <td>
                  <span class="mode-tag" :class="profile.status === 'active' ? 'success' : 'warning'">
                    {{ profile.status === 'active' ? '启用' : '草稿' }}
                  </span>
                </td>
                <td>{{ platform.formatDateTime(profile.updated_at) }}</td>
                <td class="row-actions">
                  <button @click="platform.handleJobProfileChange(`user:${profile.id}`)">套用</button>
                  <button @click="platform.editJobProfile(profile)">编辑</button>
                  <button class="danger" @click="platform.removeJobProfile(profile)"><Trash2 :size="15" />归档</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-inline">还没有岗位模板。先保存一条常用 JD，后续分析就能直接复用。</div>
      </section>
    </section>
  </section>
</template>
