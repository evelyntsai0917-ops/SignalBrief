<script setup>
import { onMounted, ref } from 'vue'

const signals = ref([])

onMounted(async () => {
  const response = await fetch('http://localhost:8000/api/signals')
  const data = await response.json()
  signals.value = data
})
</script>

<template>
  <h1>SignalBrief</h1>
  <<div v-for="signal in signals" :key="signal.id">
    <h2>{{ signal.title }}</h2>
    <p>{{ signal.summary }}</p>
  </div>
</template>