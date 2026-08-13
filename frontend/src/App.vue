<script setup>
import { onMounted, ref } from 'vue'

const signals = ref([])
const updatedAt = ref('')
const loading = ref(true)
const errorMessage = ref('')

const formattedUpdatedAt = () => {
  if (!updatedAt.value) return ''

  return new Date(updatedAt.value).toLocaleString('zh-TW', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8000/api/signals')
    if (!response.ok) {
      throw new Error('無法讀取新聞')
    }

    const data = await response.json()
    signals.value = data.signals || []
    updatedAt.value = data.updated_at
  } catch (error) {
    errorMessage.value = error.message || '載入失敗'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main>
    <h1>SignalBrief</h1>
    <p v-if="updatedAt && signals.length">Last updated: {{ formattedUpdatedAt() }}</p>
    <p v-if="loading">正在向 GDELT 抓新聞，可能需要 15–40 秒…</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <p v-else-if="signals.length === 0">
      目前沒有新聞。GDELT 可能正在限流，稍等再重整一次。
    </p>

    <article v-for="signal in signals" :key="signal.id">
      <h2>
        <a :href="signal.source_url" target="_blank" rel="noreferrer">
          {{ signal.title }}
        </a>
      </h2>
      <p>{{ signal.source_name }} · {{ signal.subcategory }}</p>
      <ul>
        <li v-for="point in signal.summary_points" :key="point">
          {{ point }}
        </li>
      </ul>
    </article>
  </main>
</template>
