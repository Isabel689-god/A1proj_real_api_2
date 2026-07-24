<template>
  <canvas ref="c" class="star-bg"></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const c = ref<HTMLCanvasElement | null>(null)
let id = 0

onMounted(() => {
  if (!c.value) return
  const ctx = c.value.getContext('2d')!
  let W = 0, H = 0

  interface Star { x: number; y: number; r: number; alpha: number; va: number; phase: number; vx: number; vy: number; hue: number }
  interface Meteor { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; r: number }

  const stars: Star[] = []
  const meteors: Meteor[] = []

  function resize() { W = c.value!.width = innerWidth; H = c.value!.height = innerHeight }
  resize()
  addEventListener('resize', resize)

  // 1500 颗星星
  for (let i = 0; i < 1500; i++) {
    stars.push({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() < 0.04 ? 3.5 + Math.random() * 2.5 : Math.random() * 2.8 + 0.2,
      alpha: Math.random() * 0.9 + 0.1,
      va: (Math.random() - 0.5) * 0.008,
      phase: Math.random() * Math.PI * 2,
      vx: (Math.random() - 0.5) * 0.07,
      vy: (Math.random() - 0.5) * 0.07,
      hue: Math.random() < 0.2 ? 180 + Math.random() * 75 : 0,
    })
  }

  function spawnMeteor() {
    if (meteors.length > 6) return
    meteors.push({
      x: Math.random() * W * 0.6 + W * 0.2,
      y: Math.random() * H * 0.15,
      vx: (Math.random() - 0.15) * 3.5,
      vy: Math.random() * 4 + 3,
      life: 1, maxLife: Math.random() * 60 + 30,
      r: Math.random() * 1.5 + 0.5,
    })
  }

  let meteorCooldown = 0

  function draw() {
    ctx.clearRect(0, 0, W, H)

    const bg = ctx.createRadialGradient(W * 0.5, H * 0.3, 0, W * 0.5, H * 0.3, W * 0.95)
    bg.addColorStop(0, '#0e2040')
    bg.addColorStop(0.3, '#081630')
    bg.addColorStop(0.65, '#030c1c')
    bg.addColorStop(1, '#010308')
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H)

    const t = Date.now() * 0.001

    // 6 处星云光斑
    const nebulae = [
      { x: W * 0.2, y: H * 0.15, r: W * 0.45, c: '0,220,240' },
      { x: W * 0.75, y: H * 0.5, r: W * 0.4, c: '120,200,255' },
      { x: W * 0.1, y: H * 0.7, r: W * 0.35, c: '80,160,230' },
      { x: W * 0.85, y: H * 0.2, r: W * 0.3, c: '0,255,180' },
      { x: W * 0.5, y: H * 0.8, r: W * 0.3, c: '40,140,220' },
      { x: W * 0.35, y: H * 0.4, r: W * 0.25, c: '160,220,255' },
    ]
    for (const nb of nebulae) {
      const ng = ctx.createRadialGradient(nb.x, nb.y, 0, nb.x, nb.y, nb.r)
      ng.addColorStop(0, `rgba(${nb.c},0.05)`)
      ng.addColorStop(0.5, `rgba(${nb.c},0.015)`)
      ng.addColorStop(1, 'transparent')
      ctx.fillStyle = ng; ctx.fillRect(0, 0, W, H)
    }

    for (const s of stars) {
      s.x += s.vx; s.y += s.vy
      if (s.x < -20) s.x = W + 20; if (s.x > W + 20) s.x = -20
      if (s.y < -20) s.y = H + 20; if (s.y > H + 20) s.y = -20
      s.alpha += s.va
      if (s.alpha > 0.92 || s.alpha < 0.06) s.va *= -1

      const flicker = Math.sin(t * 3.5 + s.phase) * 0.4 + 0.6
      const a = Math.max(0.05, s.alpha * flicker)

      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)

      if (s.hue > 0) {
        ctx.fillStyle = `hsla(${s.hue},85%,78%,${a.toFixed(3)})`
        ctx.shadowColor = `hsla(${s.hue},100%,70%,0.9)`
        ctx.shadowBlur = s.r * 3.5
      } else {
        ctx.fillStyle = `rgba(210,240,255,${a.toFixed(3)})`
        ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0
      }
      ctx.fill()
      ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0

      if (s.r > 1.8 && s.alpha > 0.35) {
        const glow = a * 0.4
        ctx.save(); ctx.globalAlpha = glow
        const len = s.r * 9
        ctx.beginPath()
        ctx.moveTo(s.x - len, s.y); ctx.lineTo(s.x + len, s.y)
        ctx.moveTo(s.x, s.y - len); ctx.lineTo(s.x, s.y + len)
        ctx.strokeStyle = s.hue > 0 ? `hsla(${s.hue},90%,85%,0.8)` : 'rgba(190,230,255,0.9)'
        ctx.lineWidth = 0.7; ctx.stroke(); ctx.restore()

        ctx.beginPath(); ctx.arc(s.x, s.y, s.r * 6, 0, Math.PI * 2)
        ctx.fillStyle = s.hue > 0
          ? `hsla(${s.hue},80%,65%,${(glow * 0.18).toFixed(3)})`
          : `rgba(160,220,255,${(glow * 0.15).toFixed(3)})`
        ctx.fill()
      }
    }

    meteorCooldown--
    if (meteorCooldown <= 0 && Math.random() < 0.5) { spawnMeteor(); meteorCooldown = 45 }
    for (let i = meteors.length - 1; i >= 0; i--) {
      const m = meteors[i]
      m.x += m.vx; m.y += m.vy; m.life--
      if (m.life <= 0 || m.y > H + 60) { meteors.splice(i, 1); continue }
      const a = m.life / m.maxLife
      const tail = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * 50, m.y - m.vy * 50)
      tail.addColorStop(0, `rgba(255,255,255,${(a * 0.95).toFixed(3)})`)
      tail.addColorStop(0.4, `rgba(180,220,255,${(a * 0.4).toFixed(3)})`)
      tail.addColorStop(1, 'transparent')
      ctx.beginPath(); ctx.moveTo(m.x, m.y); ctx.lineTo(m.x - m.vx * 50, m.y - m.vy * 50)
      ctx.strokeStyle = tail; ctx.lineWidth = m.r * 2
      ctx.shadowColor = '#a0e0ff'; ctx.shadowBlur = 12 * a
      ctx.stroke()
      ctx.shadowBlur = 0
      ctx.beginPath(); ctx.arc(m.x, m.y, m.r * 3, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255,255,255,${(a * 0.98).toFixed(3)})`
      ctx.shadowColor = '#ffffff'; ctx.shadowBlur = 15 * a
      ctx.fill()
      ctx.shadowBlur = 0
    }

    id = requestAnimationFrame(draw)
  }
  draw()
  onUnmounted(() => { removeEventListener('resize', resize); cancelAnimationFrame(id) })
})
</script>

<style scoped>
.star-bg { position:fixed;inset:0;z-index:0; }
</style>
