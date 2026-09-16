import { ref, computed, onUnmounted } from 'vue'

export function useCountdown(targetTime: string) {
  const remaining = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  const days = computed(() => Math.floor(remaining.value / 86400))
  const hours = computed(() => Math.floor((remaining.value % 86400) / 3600))
  const minutes = computed(() => Math.floor((remaining.value % 3600) / 60))
  const seconds = computed(() => remaining.value % 60)
  const isExpired = computed(() => remaining.value <= 0)

  const formatted = computed(() => {
    const pad = (n: number) => String(n).padStart(2, '0')
    if (days.value > 0) return `${days.value}天${pad(hours.value)}:${pad(minutes.value)}:${pad(seconds.value)}`
    return `${pad(hours.value)}:${pad(minutes.value)}:${pad(seconds.value)}`
  })

  function update() {
    remaining.value = Math.max(0, Math.floor((new Date(targetTime).getTime() - Date.now()) / 1000))
    if (remaining.value <= 0) stop()
  }

  function start() {
    update()
    if (timer === null) {
      timer = setInterval(update, 1000)
    }
  }

  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  onUnmounted(stop)

  return { remaining, days, hours, minutes, seconds, isExpired, formatted, start, stop }
}
