<script setup>
import { Database, LockKeyhole, ShieldCheck, X } from 'lucide-vue-next'

import { usePlatform } from '../stores/platform'

const platform = usePlatform()
</script>

<template>
  <div v-if="platform.settingsPanelOpen" class="drawer-backdrop" @click.self="platform.closeSettingsPanel">
    <aside class="auth-drawer settings-modal" aria-label="设置面板">
      <header class="drawer-header">
        <div>
          <span>设置</span>
          <h3>系统设置</h3>
        </div>
        <button class="icon-button" @click="platform.closeSettingsPanel" aria-label="关闭设置面板">
          <X :size="18" />
        </button>
      </header>

      <section class="modal-section">
        <div class="panel-heading"><h3>服务状态</h3></div>
        <dl class="kv-list">
          <div><dt>后端</dt><dd>{{ platform.healthStatus?.status === 'ok' ? '正常' : platform.healthStatus ? '异常' : '检测中…' }}</dd></div>
          <div><dt>数据库</dt><dd>{{ platform.healthStatus?.database === 'ok' ? '已连接' : platform.healthStatus ? '不可用' : '—' }}</dd></div>
          <div><dt>Redis</dt><dd>{{ platform.healthStatus?.redis === 'ok' ? '已连接' : platform.healthStatus?.redis === 'disabled' ? '未启用' : platform.healthStatus ? '不可用' : '—' }}</dd></div>
          <div><dt>任务队列</dt><dd>{{ platform.healthStatus?.worker === 'celery' ? 'Celery' : platform.healthStatus?.worker === 'background_tasks' ? '进程内后台' : '—' }}</dd></div>
        </dl>
      </section>

      <section class="modal-section">
        <div class="panel-heading"><h3>当前设置</h3></div>
        <dl class="kv-list">
          <div><dt>身份</dt><dd>{{ platform.currentIdentityLabel }}</dd></div>
          <div><dt>分析</dt><dd>{{ platform.modeLabel }}</dd></div>
          <div><dt>历史</dt><dd>{{ platform.historyCount }} 条</dd></div>
        </dl>
      </section>

      <section class="modal-section">
        <div class="panel-heading"><h3>分析模式</h3></div>
        <label class="switch-row">
          <input v-model="platform.enableAi" type="checkbox" />
          <span>启用 AI 深度优化</span>
        </label>
        <dl class="kv-list">
          <div><dt>当前模式</dt><dd>{{ platform.modeLabel }}</dd></div>
          <div><dt>后台优化</dt><dd>先生成可用结果，AI 优化完成后自动补齐</dd></div>
        </dl>
      </section>

      <section v-if="platform.auth.authenticated" class="modal-section">
        <div class="panel-heading">
          <h3>个人资料</h3>
          <p class="panel-subtitle">完善学校与专业信息，便于个性化分析建议。</p>
        </div>
        <p v-if="platform.profileMessage" class="account-message">{{ platform.profileMessage }}</p>
        <form class="profile-form" @submit.prevent="platform.submitUserProfile">
          <label class="field">
            <span>学校</span>
            <input v-model.trim="platform.userProfile.school" placeholder="例如：某某大学" />
          </label>
          <label class="field">
            <span>专业</span>
            <input v-model.trim="platform.userProfile.major" placeholder="例如：计算机科学与技术" />
          </label>
          <label class="field">
            <span>年级</span>
            <input v-model.trim="platform.userProfile.grade" placeholder="例如：2022 级 / 大三" />
          </label>
          <label class="field">
            <span>班级</span>
            <input v-model.trim="platform.userProfile.class_name" placeholder="例如：计科 2201 班" />
          </label>
          <label class="field">
            <span>手机</span>
            <input v-model.trim="platform.userProfile.phone" placeholder="选填，便于联系" />
          </label>
          <label class="field">
            <span>简介</span>
            <textarea v-model.trim="platform.userProfile.bio" rows="4" placeholder="简要介绍求职方向或特长"></textarea>
          </label>
          <button class="primary-action" :disabled="platform.profileLoading">
            {{ platform.profileLoading ? '保存中…' : '保存资料' }}
          </button>
        </form>
      </section>

      <section class="modal-section">
        <div class="panel-heading"><h3>数据安全</h3></div>
        <div class="security-list">
          <div><LockKeyhole :size="18" /> 文件格式与大小校验</div>
          <div><ShieldCheck :size="18" /> 压缩包安全解压</div>
          <div><Database :size="18" /> 删除记录时同步清理文件</div>
        </div>
      </section>
    </aside>
  </div>
</template>
