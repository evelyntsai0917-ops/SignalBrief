<script setup>
import { onMounted, ref } from 'vue'

const signals = ref([])
const updatedAt = ref('')
const formattedUpdatedAt = () => {
  if (!updatedAt.value) return ''

  return new Date(updatedAt.value).toLocaleString('zh-TW', {
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit'
})
}

onMounted(async () => {
  const response = await fetch('http://localhost:8000/api/signals')
  const data = await response.json()
  signals.value = data.signals
  updatedAt.value = data.updated_at
})
</script>

<template>
  <h1>SignalBrief</h1>
  <p>Last updated: {{ formattedUpdatedAt() }}</p>
  <div v-for="signal in signals" :key="signal.id">
    <h2>{{ signal.title }}</h2>
     <ul>
      <li v-for="point in signal.summary_points" :key="point">
        {{ point }}
      </li>
    </ul>
  </div>
</template>