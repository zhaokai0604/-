<script setup>
defineProps({
  modelValue: {
    type: [String, Number],
    default: '0',
  },
  targetPosition: {
    type: String,
    default: '',
  },
  jobDescription: {
    type: String,
    default: '',
  },
  profiles: {
    type: Array,
    default: () => [],
  },
  presets: {
    type: Array,
    default: () => [],
  },
  textareaRows: {
    type: Number,
    default: 9,
  },
})

const emit = defineEmits(['update:modelValue', 'update:targetPosition', 'update:jobDescription', 'profile-change', 'clear'])

function onProfileChange(event) {
  const value = String(event.target.value || '0')
  emit('update:modelValue', value)
  emit('profile-change', value)
}

function onClear() {
  emit('update:modelValue', '0')
  emit('update:targetPosition', '')
  emit('update:jobDescription', '')
  emit('clear')
}
</script>

<template>
  <div class="form-grid">
    <label class="field">
      <span>岗位模板</span>
      <select :value="modelValue" @change="onProfileChange">
        <option value="0">不使用模板，手动填写</option>
        <optgroup v-if="profiles.length" label="我的岗位模板">
          <option v-for="profile in profiles" :key="profile.optionKey || `user:${profile.id}`" :value="profile.optionKey || `user:${profile.id}`">
            {{ profile.optionLabel || profile.name }}
          </option>
        </optgroup>
        <optgroup v-if="presets.length" label="系统岗位模板">
          <option v-for="profile in presets" :key="profile.optionKey || `preset:${profile.id}`" :value="profile.optionKey || `preset:${profile.id}`">
            {{ profile.optionLabel || profile.name }}
          </option>
        </optgroup>
      </select>
    </label>

    <label class="field">
      <span class="field-label-row">
        <span>目标岗位</span>
        <button
          v-if="targetPosition || jobDescription || String(modelValue) !== '0'"
          type="button"
          class="text-link field-clear-btn"
          @click="onClear"
        >
          清空目标岗
        </button>
      </span>
      <input
        :value="targetPosition"
        placeholder="可留空：不做套岗，仅通用分析 + 推荐岗位"
        @input="emit('update:targetPosition', $event.target.value)"
      />
    </label>

    <label class="field">
      <span>岗位 JD</span>
      <textarea
        :value="jobDescription"
        :rows="textareaRows"
        placeholder="可留空；粘贴岗位要求后用于计算岗位匹配度。"
        @input="emit('update:jobDescription', $event.target.value)"
      ></textarea>
    </label>
  </div>
</template>
