<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Radio } from 'lucide-vue-next'

import { analysisStreamUrl } from '../api/client'

const props = defineProps({
  recordId: { type: [Number, String], default: null },
  autoPlay: { type: Boolean, default: false },
  /** live=true 走上传时真实分析并落库；false 为完成后的重放 */
  live: { type: Boolean, default: false },
})

const emit = defineEmits(['done', 'error'])

const lines = ref([])
const currentStep = ref('')
const playing = ref(false)
let source = null
let endedCleanly = false

function stop() {
  if (source) {
    source.close()
    source = null
  }
  playing.value = false
}

function pushLine(text, tone = 'info') {
  if (!text) return
  lines.value = [...lines.value.slice(-40), { text, tone, at: Date.now() }]
}

function play() {
  if (!props.recordId || playing.value) return
  stop()
  endedCleanly = false
  lines.value = []
  currentStep.value = props.live ? '连接实时分析流…' : '连接解析流…'
  playing.value = true
  source = new EventSource(analysisStreamUrl(props.recordId, { live: props.live }), { withCredentials: true })

  const handle = (eventName, tone) => (event) => {
    try {
      const data = JSON.parse(event.data || '{}')
      const message = data.message || data.text || eventName
      currentStep.value = message
      pushLine(message, tone)
      if (eventName === 'done') {
        endedCleanly = true
        stop()
        emit('done', data)
      }
      if (eventName === 'stream_error') {
        endedCleanly = true
        stop()
        emit('error', data)
      }
    } catch {
      pushLine(event.data || eventName, tone)
    }
  }

  source.addEventListener('step', handle('step', 'step'))
  source.addEventListener('parse_line', handle('parse_line', 'read'))
  source.addEventListener('section_found', handle('section_found', 'ok'))
  source.addEventListener('structured', handle('structured', 'ok'))
  source.addEventListener('keyword_hit', handle('keyword_hit', 'ok'))
  source.addEventListener('keyword_miss', handle('keyword_miss', 'warn'))
  source.addEventListener('semantic', handle('semantic', 'info'))
  source.addEventListener('low_snr', handle('low_snr', 'warn'))
  source.addEventListener('skill_hint', handle('skill_hint', 'info'))
  source.addEventListener('score_dim', handle('score_dim', 'info'))
  source.addEventListener('done', handle('done', 'ok'))
  // 避免与 EventSource 原生 error 冲突，服务端业务错误用 stream_error
  source.addEventListener('stream_error', handle('stream_error', 'warn'))
  source.onerror = () => {
    if (!playing.value || endedCleanly) return
    pushLine('解析流已结束或连接中断', 'warn')
    stop()
    emit('error', { message: '解析流连接中断' })
  }
}

function maybeAutoPlay() {
  if (props.recordId && props.autoPlay && !playing.value) {
    play()
  }
}

watch(
  () => [props.recordId, props.live, props.autoPlay],
  () => {
    stop()
    lines.value = []
    currentStep.value = ''
    maybeAutoPlay()
  },
  { immediate: true },
)

onMounted(maybeAutoPlay)
onBeforeUnmount(stop)

defineExpose({ play, stop })
</script>

<template>
  <section class="panel live-stream-panel">
    <div class="panel-heading">
      <div>
        <h3><Radio :size="18" /> {{ live ? '实时分析流' : '实时解析流' }}</h3>
        <span class="panel-subtitle">
          {{
            currentStep
              || (live
                ? '正在真实执行分析并落库（非事后重放）'
                : '重放阅读与匹配过程（事件来自真实分析结果）')
          }}
        </span>
      </div>
      <button type="button" class="secondary-action" :disabled="!recordId || playing" @click="play">
        {{ playing ? '播放中…' : live ? '开始实时分析' : '播放解析过程' }}
      </button>
    </div>
    <div class="live-stream-body">
      <div class="live-stream-feed">
        <p v-if="!lines.length" class="table-empty">
          {{ live ? '上传后将自动推送阅读、匹配与落库事件。' : '点击播放，逐行查看系统如何阅读简历、命中关键词并标记低信噪比区。' }}
        </p>
        <div v-for="(item, index) in lines" :key="`${item.at}-${index}`" class="live-stream-line" :class="item.tone">
          {{ item.text }}
        </div>
      </div>
    </div>
  </section>
</template>
