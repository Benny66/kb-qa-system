import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toast', () => {
  const toasts = ref([])

  function show(message, type = 'info', duration = 3000) {
    const id = Date.now()
    toasts.value.push({ id, message, type })
    setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== id)
    }, duration)
  }

  const success = (msg) => show(msg, 'success')
  const error = (msg) => show(msg, 'error', 4000)
  const info = (msg) => show(msg, 'info')

  return { toasts, success, error, info }
})
