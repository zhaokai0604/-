<script setup>
import { BriefcaseBusiness, RefreshCw, Trash2 } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
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
          {{ platform.jobsLoading ? '保存中' : platform.editingJobProfileId ? '更新模板' : '保存模板' }}
        </button>
        <span>保存后可在单份分析和批量分析页直接复用。</span>
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
              <th>模板</th><th>目标岗位</th><th>分类</th><th>状态</th><th>更新时间</th><th>操作</th>
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
              <td><span class="mode-tag" :class="profile.status === 'active' ? 'success' : 'warning'">{{ profile.status === 'active' ? '启用' : '草稿' }}</span></td>
              <td>{{ platform.formatDateTime(profile.updated_at) }}</td>
              <td class="row-actions">
                <button @click="platform.selectedJobProfileId = profile.id; platform.applySelectedJobProfile(profile)">套用</button>
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
</template>
