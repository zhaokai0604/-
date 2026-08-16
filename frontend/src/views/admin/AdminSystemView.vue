<script setup>
import { RefreshCw, Sparkles, Trash2 } from 'lucide-vue-next'

import { usePlatform } from '../../stores/platform'

const platform = usePlatform()
</script>

<template>
  <section class="admin-stack">
    <p v-if="platform.adminMessage" class="account-message">{{ platform.adminMessage }}</p>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>增强分析配置</h3>
          <p class="panel-subtitle">修改系统默认增强分析模型，保存后新的分析任务会立即使用。</p>
        </div>
        <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.saveAiConfig">
          <Sparkles :size="16" />保存配置
        </button>
      </div>
      <div class="admin-config-grid">
        <label class="field">
          <span>模型提供方</span>
          <select v-model="platform.adminAiConfig.provider">
            <option v-for="option in platform.adminAiConfig.provider_options" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>模型名称</span>
          <input v-model.trim="platform.adminAiConfig.model" list="admin-model-suggestions" placeholder="例如：deepseek-chat" />
          <datalist id="admin-model-suggestions">
            <option v-for="item in platform.adminAiConfig.model_suggestions" :key="item" :value="item" />
          </datalist>
        </label>
      </div>
      <label class="field">
        <span>API 地址</span>
        <input v-model.trim="platform.adminAiConfig.api_url" placeholder="https://api.deepseek.com/chat/completions" />
      </label>
      <label class="field">
        <span>API Key</span>
        <input v-model.trim="platform.adminAiConfig.api_key" type="password" placeholder="留空表示保持当前 Key 不变" />
      </label>
      <label class="switch-row">
        <input v-model="platform.adminAiConfig.clear_api_key" type="checkbox" />
        <span>清空当前 API Key，仅保留快速本地分析</span>
      </label>
      <dl class="kv-list">
        <div><dt>当前 Key</dt><dd>{{ platform.adminAiConfig.api_key_masked || '未配置' }}</dd></div>
        <div><dt>当前状态</dt><dd>{{ platform.adminAiConfig.api_key_configured ? '已配置增强分析' : '未配置，默认离线' }}</dd></div>
        <div><dt>配置来源</dt><dd>{{ platform.adminAiConfig.using_local_override ? '管理员本地覆盖' : '环境变量默认值' }}</dd></div>
      </dl>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>记录元数据</h3>
          <p class="panel-subtitle">展示记录归属与评分摘要，删除操作将同步清理文件。</p>
        </div>
        <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.loadAdminSystemData">
          <RefreshCw :size="16" />刷新
        </button>
      </div>
      <div class="table-wrap admin-scroll-wrap">
        <table class="data-table admin-table">
          <thead>
            <tr>
              <th>文件</th><th>用户</th><th>岗位</th><th>总分</th><th>模式</th><th>时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in platform.adminRecords" :key="record.record_id">
              <td>{{ record.filename }}</td>
              <td>{{ record.display_name }}<br /><span class="muted-cell">{{ record.username }}</span></td>
              <td>{{ record.target_position || '-' }}</td>
              <td><strong>{{ record.total_score }}</strong></td>
              <td><span class="mode-tag" :class="platform.displayAnalysisModeClass(record)">{{ platform.displayAnalysisModeLabel(record) }}</span></td>
              <td>{{ platform.formatDateTime(record.created_at) }}</td>
              <td class="row-actions">
                <button class="danger" :disabled="platform.adminLoading" @click="platform.removeAdminRecord(record)">
                  <Trash2 :size="15" />删除
                </button>
              </td>
            </tr>
            <tr v-if="!platform.adminRecords.length">
              <td colspan="7" class="table-empty">暂无分析记录。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>评分权重模板</h3>
          <p class="panel-subtitle">按岗位类型切换评分维度权重。</p>
        </div>
        <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.saveScoreConfig">
          保存模板
        </button>
      </div>
      <label class="field">
        <span>当前生效模板</span>
        <select v-model="platform.adminScoreConfig.active_template">
          <option v-for="name in platform.adminScoreConfig.available_templates" :key="name" :value="name">
            {{ name }}
          </option>
        </select>
      </label>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>文件生命周期</h3>
          <p class="panel-subtitle">清理 uploads / reports 中无数据库引用的孤儿文件。</p>
        </div>
        <div class="panel-actions">
          <button class="secondary-action" :disabled="platform.adminLoading" @click="platform.cleanupStorage(true)">
            扫描预览
          </button>
          <button class="secondary-action danger-action" :disabled="platform.adminLoading" @click="platform.cleanupStorage(false)">
            <Trash2 :size="16" />执行清理
          </button>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>安全审计</h3>
          <p class="panel-subtitle">记录登录、账号状态变更、密码重置和管理员删除等关键操作。</p>
        </div>
      </div>
      <div class="table-wrap admin-scroll-wrap">
        <table class="data-table admin-table">
          <thead>
            <tr>
              <th>时间</th><th>操作者</th><th>动作</th><th>对象</th><th>结果</th><th>IP</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in platform.adminAuditLogs" :key="log.id">
              <td>{{ platform.formatDateTime(log.created_at) }}</td>
              <td>{{ log.actor_username }}</td>
              <td>{{ log.action }}</td>
              <td>{{ log.target_type }} #{{ log.target_id || '-' }}</td>
              <td><span class="mode-tag success">{{ log.result }}</span></td>
              <td>{{ log.ip_address || '-' }}</td>
            </tr>
            <tr v-if="!platform.adminAuditLogs.length">
              <td colspan="6" class="table-empty">暂无审计日志。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
