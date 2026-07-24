<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Clock3, Lightbulb, Mic, MicOff, RotateCcw, Star, Volume2 } from 'lucide-vue-next'

const props = defineProps({
  session: {
    type: Object,
    required: true,
  },
  recordId: {
    type: Number,
    required: true,
  },
})

const storageKey = computed(() => `mock-interview:${props.recordId}`)
const currentIndex = ref(0)
const showTip = ref(false)
const ratings = ref({})
const voiceNotes = ref({})
const elapsedSec = ref(0)
const isListening = ref(false)
const isSpeaking = ref(false)
const voiceError = ref('')
let timerId = null
let recognition = null

const speechSupported = computed(() => typeof window !== 'undefined' && 'speechSynthesis' in window)
const recognitionSupported = computed(() => {
  if (typeof window === 'undefined') {
    return false
  }
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
})

const steps = computed(() => props.session?.steps || [])
const currentStep = computed(() => steps.value[currentIndex.value] || null)
const currentNote = computed(() => voiceNotes.value[currentStep.value?.step_no] || '')
const progressPercent = computed(() => {
  if (!steps.value.length) {
    return 0
  }
  return Math.round(((currentIndex.value + 1) / steps.value.length) * 100)
})
const isComplete = computed(() => steps.value.length > 0 && currentIndex.value >= steps.value.length)
const ratedCount = computed(() => Object.keys(ratings.value).length)
const notedCount = computed(() => Object.values(voiceNotes.value).filter(Boolean).length)
const averageRating = computed(() => {
  const values = Object.values(ratings.value).map(Number).filter((value) => value > 0)
  if (!values.length) {
    return 0
  }
  return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 10) / 10
})

function restoreProgress() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) {
      return
    }
    const saved = JSON.parse(raw)
    if (saved?.ratings) {
      ratings.value = saved.ratings
    }
    if (saved?.voiceNotes) {
      voiceNotes.value = saved.voiceNotes
    }
    if (Number.isInteger(saved?.currentIndex) && saved.currentIndex < steps.value.length) {
      currentIndex.value = saved.currentIndex
    }
  } catch {
    // ignore invalid cache
  }
}

function persistProgress() {
  localStorage.setItem(
    storageKey.value,
    JSON.stringify({
      currentIndex: currentIndex.value,
      ratings: ratings.value,
      voiceNotes: voiceNotes.value,
    }),
  )
}

function startTimer() {
  stopTimer()
  elapsedSec.value = 0
  timerId = window.setInterval(() => {
    elapsedSec.value += 1
  }, 1000)
}

function stopTimer() {
  if (timerId) {
    window.clearInterval(timerId)
    timerId = null
  }
}

function stopSpeaking() {
  if (speechSupported.value) {
    window.speechSynthesis.cancel()
  }
  isSpeaking.value = false
}

function speakQuestion() {
  if (!speechSupported.value || !currentStep.value?.question) {
    return
  }
  stopSpeaking()
  const utter = new SpeechSynthesisUtterance(currentStep.value.question)
  utter.lang = 'zh-CN'
  utter.rate = 0.95
  utter.onstart = () => {
    isSpeaking.value = true
  }
  utter.onend = () => {
    isSpeaking.value = false
  }
  utter.onerror = () => {
    isSpeaking.value = false
  }
  window.speechSynthesis.speak(utter)
}

function stopListening() {
  if (recognition) {
    recognition.stop()
    recognition = null
  }
  isListening.value = false
}

function startListening() {
  if (!recognitionSupported.value || !currentStep.value) {
    voiceError.value = '当前浏览器不支持语音输入，请改用文字记录。'
    return
  }
  voiceError.value = ''
  stopListening()
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SpeechRecognitionCtor()
  recognition.lang = 'zh-CN'
  recognition.interimResults = true
  recognition.continuous = true
  recognition.onstart = () => {
    isListening.value = true
  }
  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || '')
      .join('')
      .trim()
    if (!transcript || !currentStep.value) {
      return
    }
    voiceNotes.value = {
      ...voiceNotes.value,
      [currentStep.value.step_no]: transcript,
    }
    persistProgress()
  }
  recognition.onerror = () => {
    voiceError.value = '语音识别中断，请检查麦克风权限后重试。'
    stopListening()
  }
  recognition.onend = () => {
    isListening.value = false
  }
  recognition.start()
}

function updateNote(value) {
  if (!currentStep.value) {
    return
  }
  voiceNotes.value = {
    ...voiceNotes.value,
    [currentStep.value.step_no]: value,
  }
  persistProgress()
}

function formatTime(totalSec) {
  const minutes = Math.floor(totalSec / 60)
  const seconds = totalSec % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function setRating(score) {
  if (!currentStep.value) {
    return
  }
  ratings.value = { ...ratings.value, [currentStep.value.step_no]: score }
  persistProgress()
}

function goNext() {
  stopSpeaking()
  stopListening()
  if (currentIndex.value < steps.value.length) {
    currentIndex.value += 1
    showTip.value = false
    voiceError.value = ''
    startTimer()
    persistProgress()
  }
}

function goPrev() {
  stopSpeaking()
  stopListening()
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
    showTip.value = false
    voiceError.value = ''
    startTimer()
    persistProgress()
  }
}

function restartSession() {
  stopSpeaking()
  stopListening()
  currentIndex.value = 0
  showTip.value = false
  ratings.value = {}
  voiceNotes.value = {}
  voiceError.value = ''
  localStorage.removeItem(storageKey.value)
  startTimer()
}

watch(
  () => props.recordId,
  () => {
    stopSpeaking()
    stopListening()
    currentIndex.value = 0
    showTip.value = false
    ratings.value = {}
    voiceNotes.value = {}
    voiceError.value = ''
    restoreProgress()
    startTimer()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopTimer()
  stopSpeaking()
  stopListening()
  persistProgress()
})
</script>

<template>
  <section v-if="session?.steps?.length" class="panel mock-interview-panel">
    <div class="panel-heading">
      <div>
        <h3>模拟面试</h3>
        <span class="panel-subtitle">{{ session.summary }}</span>
      </div>
      <button class="secondary-action" type="button" @click="restartSession">
        <RotateCcw :size="16" />重新开始
      </button>
    </div>

    <div v-if="speechSupported || recognitionSupported" class="mock-voice-toolbar">
      <button
        v-if="speechSupported"
        class="secondary-action"
        type="button"
        :disabled="isComplete || isSpeaking"
        @click="speakQuestion"
      >
        <Volume2 :size="16" />{{ isSpeaking ? '朗读中…' : '朗读题目' }}
      </button>
      <button
        v-if="recognitionSupported"
        class="secondary-action"
        type="button"
        :disabled="isComplete"
        @click="isListening ? stopListening() : startListening()"
      >
        <Mic v-if="!isListening" :size="16" /><MicOff v-else :size="16" />
        {{ isListening ? '停止录音' : '语音作答' }}
      </button>
      <small v-if="!recognitionSupported">当前浏览器不支持语音输入，可直接在下方记录要点。</small>
    </div>

    <div v-if="!isComplete" class="mock-progress">
      <div class="mock-progress-bar">
        <span :style="{ width: `${progressPercent}%` }" />
      </div>
      <small>第 {{ currentIndex + 1 }} / {{ steps.length }} 题 · {{ currentStep?.category }}</small>
    </div>

    <article v-if="!isComplete && currentStep" class="mock-step-card">
      <div class="mock-step-meta">
        <span class="subtle-pill">{{ currentStep.focus || '综合' }}</span>
        <span class="mock-timer"><Clock3 :size="14" /> {{ formatTime(elapsedSec) }} / 建议 {{ currentStep.time_limit_sec }}s</span>
      </div>
      <p class="mock-question">{{ currentStep.question }}</p>

      <ul v-if="currentStep.rubric?.length" class="mock-rubric">
        <li v-for="item in currentStep.rubric" :key="item">{{ item }}</li>
      </ul>

      <label class="field mock-note-field">
        <span>作答记录</span>
        <textarea
          :value="currentNote"
          rows="4"
          placeholder="点击「语音作答」自动转写，或直接输入你的回答要点…"
          @input="updateNote($event.target.value)"
        />
      </label>
      <p v-if="voiceError" class="mock-voice-error">{{ voiceError }}</p>

      <div class="mock-rating-row">
        <span>自评（1-5）</span>
        <div class="mock-stars">
          <button
            v-for="score in 5"
            :key="score"
            type="button"
            :class="{ active: ratings[currentStep.step_no] === score }"
            @click="setRating(score)"
          >
            <Star :size="16" />
          </button>
        </div>
      </div>

      <button v-if="!showTip" class="ghost-action" type="button" @click="showTip = true">
        <Lightbulb :size="16" />查看答题提示
      </button>
      <p v-else class="mock-tip"><Lightbulb :size="15" /> {{ currentStep.tip }}</p>

      <div class="mock-nav">
        <button class="secondary-action" type="button" :disabled="currentIndex === 0" @click="goPrev">
          <ChevronLeft :size="16" />上一题
        </button>
        <button class="primary-action" type="button" @click="goNext">
          {{ currentIndex + 1 >= steps.length ? '完成' : '下一题' }}
          <ChevronRight :size="16" />
        </button>
      </div>
    </article>

    <article v-else class="mock-complete-card">
      <strong>本轮模拟面试完成</strong>
      <p>共练习 {{ steps.length }} 题，已评分 {{ ratedCount }} 题，记录要点 {{ notedCount }} 题。</p>
      <p v-if="averageRating">平均自评：{{ averageRating }} / 5</p>
      <p class="mock-complete-hint">建议结合「优化版表达预览」修改简历后上传新版本，再次模拟巩固。</p>
      <button class="secondary-action" type="button" @click="restartSession">
        <RotateCcw :size="16" />再练一轮
      </button>
    </article>
  </section>
</template>
