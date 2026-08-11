<script setup>
import { onMounted, ref } from 'vue'

const message = ref('Loading...')

onMounted(async () => {
  const response = await fetch('http://localhost:8000/')
  const data = await response.json()
  message.value = data.message
})
</script>

<template>
  <h1>SignalBrief</h1>
  <p>{{ message }}</p>
</template>