<script setup>
defineProps({
  recommendations: {
    type: Object,
    default: null,
  },
})
</script>

<template>
  <section v-if="recommendations?.templates?.length" class="panel template-panel">
    <div class="panel-heading">
      <div>
        <h3>简历模板推荐</h3>
        <span class="panel-subtitle">{{ recommendations.summary }}</span>
      </div>
    </div>

    <article v-for="item in recommendations.templates" :key="item.id" class="template-card">
      <div class="template-card-head">
        <strong>{{ item.name }}</strong>
        <span class="subtle-pill">匹配度 {{ item.match_score }}</span>
      </div>
      <ul v-if="item.reasons?.length" class="template-reasons">
        <li v-for="reason in item.reasons" :key="reason">{{ reason }}</li>
      </ul>
      <div class="template-sections">
        <span>推荐结构</span>
        <div class="keyword-chips matched">
          <span v-for="section in item.sections" :key="section">{{ section }}</span>
        </div>
      </div>
      <ul v-if="item.highlights?.length" class="clean-list compact">
        <li v-for="highlight in item.highlights" :key="highlight">{{ highlight }}</li>
      </ul>
      <p class="template-tip">{{ item.tips }}</p>
    </article>
  </section>
</template>
