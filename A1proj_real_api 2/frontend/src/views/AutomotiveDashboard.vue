<template>
  <div class="device-screen">
    <ParticleBackground />

    <header class="top-bar">
      <span class="corner-tl"></span><span class="corner-br"></span>
      <span class="corner-tr"></span><span class="corner-bl"></span>
      <div class="tb-left"><span class="tb-deco">⚙️</span></div>
      <h1 class="tb-title">智能设备数据可视化大屏</h1>
      <div class="tb-right">
        <button class="theme-btn" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
          {{ theme === 'dark' ? '☀' : '☾' }}
        </button>
        <span class="tb-tag">● 实时</span>
        <span class="tb-time">{{ time }}</span>
      </div>
    </header>

    <div class="top-section">
      <aside class="col-left">
        <section class="box flex-3">
          <div class="box-head"><span class="bh-diamond">◇</span>主轴状态</div>
          <div class="gauge-row"><v-chart :option="gaugeSpindle" autoresize class="gauge-fill" /></div>
          <div class="metric-row">
            <div class="metric"><div class="m-label">主轴转速</div><div class="m-val c-cyan">{{ spindleRpm }}<span class="m-unit">rpm</span></div></div>
            <div class="metric"><div class="m-label">主轴温度</div><div class="m-val c-orange">{{ spindleTemp }}<span class="m-unit">°C</span></div></div>
          </div>
        </section>
        <section class="box flex-2">
          <div class="box-head"><span class="bh-diamond">◇</span>加工效率</div>
          <v-chart :option="efficiencyTrend" autoresize class="chart-fill" />
        </section>
      </aside>

      <main class="col-center">
        <section class="box flex-1">
          <div class="box-head"><span class="bh-diamond">◇</span>设备实时监控</div>
          <CarModel />
          <div class="center-stats">
            <div class="cs-item"><span class="cs-val">{{ spindleRpm }}</span><span class="cs-unit">rpm</span><span class="cs-lbl">主轴转速</span></div>
            <div class="cs-item"><span class="cs-val">{{ feedRate }}</span><span class="cs-unit">mm/min</span><span class="cs-lbl">进给速度</span></div>
            <div class="cs-item"><span class="cs-val">{{ partsCount }}</span><span class="cs-unit">件</span><span class="cs-lbl">今日产量</span></div>
            <div class="cs-item"><span class="cs-val">{{ toolLife }}</span><span class="cs-unit">%</span><span class="cs-lbl">刀具寿命</span></div>
          </div>
        </section>
      </main>

      <aside class="col-right">
        <section class="box flex-3">
          <div class="box-head"><span class="bh-diamond">◇</span>伺服驱动</div>
          <div class="gauge-row"><v-chart :option="gaugeServo" autoresize class="gauge-fill" /></div>
          <div class="metric-row">
            <div class="metric"><div class="m-label">X轴负载</div><div class="m-val c-orange">{{ xLoad }}<span class="m-unit">%</span></div></div>
            <div class="metric"><div class="m-label">Z轴负载</div><div class="m-val c-red">{{ zLoad }}<span class="m-unit">%</span></div></div>
          </div>
        </section>
        <section class="box flex-2">
          <div class="box-head"><span class="bh-diamond">◇</span>刀具寿命</div>
          <v-chart :option="toolBar" autoresize class="chart-fill" />
        </section>
        <section class="box flex-2">
          <div class="box-head"><span class="bh-diamond">◇</span>运行状态</div>
          <div class="status-list">
            <div v-for="s in machineStatus" :key="s.label" class="sl-row">
              <span class="sl-dot" :class="s.ok ? 'g' : 'r'"></span>
              <span class="sl-label">{{ s.label }}</span><span class="sl-val">{{ s.val }}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <div class="bottom-section">
      <section class="box flex-1">
        <div class="box-head"><span class="bh-diamond">◇</span>数控机床产业链</div>
        <div class="chain">
          <template v-for="(c, i) in chain" :key="i">
            <div class="chain-node"><div class="cn-icon">{{ c.icon }}</div><div class="cn-label">{{ c.label }}</div></div>
            <span v-if="i < chain.length - 1" class="chain-arrow">→</span>
          </template>
        </div>
      </section>
      <section class="box flex-1">
        <div class="box-head"><span class="bh-diamond">◇</span>加工精度趋势</div>
        <v-chart :option="precisionTrend" autoresize class="chart-fill" />
      </section>
      <section class="box flex-1">
        <div class="box-head"><span class="bh-diamond">◇</span>设备预警</div>
        <div class="alert-list">
          <div v-for="a in alerts" :key="a.id" class="alert-row" :class="a.level">
            <span class="al-time">{{ a.time }}</span><span class="al-msg">{{ a.msg }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import type { Ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart, GaugeChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import ParticleBackground from '../components/ParticleBackground.vue'
import CarModel from '../components/CarModel.vue'

use([BarChart, LineChart, GaugeChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const theme = inject<Ref<'dark' | 'light'>>('theme', ref<'dark' | 'light'>('dark'))
const toggleTheme = inject<() => void>('toggleTheme', () => {})
const spindleRpm = ref(8500); const spindleTemp = ref(42.5)
const toolLife = ref(68); const feedRate = ref(1200)
const xLoad = ref(45); const zLoad = ref(62); const partsCount = ref(143)
const time = ref('')

const machineStatus = [
  { label: '液压系统', val: '正常', ok: true }, { label: '润滑系统', val: '正常', ok: true },
  { label: '冷却系统', val: '正常', ok: true }, { label: '排屑系统', val: '正常', ok: true },
  { label: '刀库状态', val: '正常', ok: true }, { label: '防护门', val: '未闭合', ok: false },
]
const chain = [
  { icon: '🏗️', label: '铸件毛坯' }, { icon: '⚙️', label: '精密加工' }, { icon: '🔧', label: '核心部件' },
  { icon: '🖥️', label: '数控系统' }, { icon: '🔩', label: '整机装配' }, { icon: '📐', label: '精度检测' }, { icon: '🚛', label: '交付运维' },
]
const alerts = [
  { id: 1, time: '14:35', msg: 'T12 刀具剩余寿命低于 30%，建议更换', level: 'warn' },
  { id: 2, time: '14:20', msg: '冷却液液位降至 81%，请及时补充', level: 'info' },
  { id: 3, time: '13:55', msg: 'Z轴编码器信号强度下降至 94%', level: 'info' },
]

onMounted(() => { updateTime(); const t = window.setInterval(updateTime, 1000); onUnmounted(() => clearInterval(t)) })
function updateTime() { time.value = new Date().toLocaleString('zh-CN', { hour12: false }) }

const tc = computed(() => theme.value === 'light' ? '#475569' : '#88bbaa')
const ac = computed(() => theme.value === 'light' ? '#cbd5e1' : '#0d2a40')
const chartPrimaryText = computed(() => theme.value === 'light' ? '#1f2937' : '#ffffff')
const tooltipSkin = computed(() => theme.value === 'light'
  ? { backgroundColor: '#ffffff', borderColor: '#cbd5e1', textStyle: { color: '#1f2937' } }
  : { backgroundColor: '#0a1428', borderColor: '#0d4a7a', textStyle: { color: '#c0d0e0' } }
)

const gaugeSpindle = computed(() => ({
  backgroundColor: 'transparent',
  series: [{ type: 'gauge', radius: '88%', center: ['50%', '55%'], startAngle: 210, endAngle: -30, min: 0, max: 100, splitNumber: 10, axisLine: { lineStyle: { width: 10, color: [[0.3, '#ff4d4f'], [0.7, '#faad14'], [1, '#52c41a']] } }, pointer: { length: '55%', width: 5, itemStyle: { color: '#00ffcc' } }, detail: { valueAnimation: true, formatter: '{value}%', color: chartPrimaryText.value, fontSize: 14, offsetCenter: [0, '62%'] }, data: [{ value: 72 }] }],
}))

const gaugeServo = computed(() => ({
  backgroundColor: 'transparent',
  series: [{ type: 'gauge', radius: '88%', center: ['50%', '55%'], startAngle: 210, endAngle: -30, min: 0, max: 50, splitNumber: 10, axisLine: { lineStyle: { width: 10, color: [[0.4, '#52c41a'], [0.7, '#faad14'], [1, '#ff4d4f']] } }, pointer: { length: '55%', width: 5, itemStyle: { color: '#faad14' } }, detail: { valueAnimation: true, formatter: '{value}μm', color: chartPrimaryText.value, fontSize: 14, offsetCenter: [0, '62%'] }, data: [{ value: 8 }] }],
}))

const efficiencyTrend = computed(() => ({
  backgroundColor: 'transparent', tooltip: { trigger: 'axis', ...tooltipSkin.value }, grid: { left: '3%', right: '4%', top: '8%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: ['0h','4h','8h','12h','16h','20h','24h'], axisLabel: { color: tc.value, fontSize: 8 }, axisLine: { lineStyle: { color: ac.value } } },
  yAxis: { type: 'value', name: '%', nameTextStyle: { color: tc.value, fontSize: 8 }, axisLabel: { color: tc.value, fontSize: 8 }, splitLine: { lineStyle: { color: ac.value, type: 'dashed' } } },
  series: [{ data: [85,82,88,92,90,86,89], type: 'line', smooth: true, lineStyle: { color: '#00ffcc', width: 2, shadowBlur: 6, shadowColor: '#00ffcc' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,255,204,0.25)' },{ offset: 1, color: 'rgba(0,255,204,0)' }] } }, itemStyle: { color: '#00ffcc', shadowBlur: 6, shadowColor: '#00ffcc' }, symbol: 'circle', symbolSize: 6 }],
}))

const toolBar = computed(() => ({
  backgroundColor: 'transparent', grid: { left: '3%', right: '4%', top: '8%', bottom: '3%' },
  xAxis: { type: 'category', data: ['T08','T09','T10','T11','T12','T13'], axisLabel: { color: tc.value, fontSize: 8 }, axisLine: { lineStyle: { color: ac.value } } },
  yAxis: { type: 'value', name: '%', nameTextStyle: { color: tc.value, fontSize: 8 }, axisLabel: { color: tc.value, fontSize: 8 }, splitLine: { lineStyle: { color: ac.value, type: 'dashed' } } },
  series: [{ data: [92,85,78,73,68,95], type: 'bar', barWidth: '50%', itemStyle: { borderRadius: [3,3,0,0], color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#00ffcc' },{ offset: 1, color: 'rgba(0,150,130,0.2)' }] }, shadowBlur: 6, shadowColor: 'rgba(0,255,204,0.2)', shadowOffsetY: 3 } }],
}))

const precisionTrend = computed(() => ({
  backgroundColor: 'transparent', tooltip: { trigger: 'axis', ...tooltipSkin.value },
  legend: { data: ['加工精度', '粗糙度'], textStyle: { color: tc.value, fontSize: 9 }, top: 0 },
  grid: { left: '3%', right: '4%', top: '18%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: ['1月','2月','3月','4月','5月','6月'], axisLabel: { color: tc.value, fontSize: 8 }, axisLine: { lineStyle: { color: ac.value } } },
  yAxis: [{ type: 'value', name: 'μm', nameTextStyle: { color: tc.value, fontSize: 8 }, axisLabel: { color: tc.value, fontSize: 8 }, splitLine: { lineStyle: { color: ac.value, type: 'dashed' } } }, { type: 'value', name: 'Ra', nameTextStyle: { color: tc.value, fontSize: 8 }, axisLabel: { color: tc.value, fontSize: 8 }, splitLine: { show: false } }],
  series: [{ name: '加工精度', type: 'bar', data: [12,10,8,7,6,5], barWidth: '30%', itemStyle: { borderRadius: [3,3,0,0], color: '#00ffcc' } }, { name: '粗糙度', type: 'line', yAxisIndex: 1, data: [1.6,1.4,1.2,1.0,0.8,0.6], smooth: true, lineStyle: { color: '#52c41a', width: 2, shadowBlur: 4, shadowColor: '#52c41a' }, itemStyle: { color: '#52c41a' }, symbol: 'diamond', symbolSize: 8 }],
}))
</script>

<style scoped>
.device-screen { width:100vw;height:100vh;font-family:'Microsoft YaHei','PingFang SC',monospace;color:var(--dashboard-text, #e0f0ff);overflow:hidden;display:flex;flex-direction:column;padding:0 20px 8px;box-sizing:border-box;position:relative;z-index:1;background:var(--dashboard-bg, transparent); }
.top-bar { display:flex;align-items:center;justify-content:space-between;height:52px;flex-shrink:0;z-index:2;background:var(--dashboard-top-bg, linear-gradient(180deg,rgba(0,80,100,0.35),transparent));border-bottom:1px solid var(--dashboard-border, rgba(0,255,204,0.2));padding:0 20px;position:relative; }
.corner-tl,.corner-tr,.corner-bl,.corner-br { position:absolute;width:16px;height:16px;border-color:var(--primary-color);border-style:solid;opacity:.7; }
.corner-tl { top:8px;left:8px;border-width:2px 0 0 2px; }
.corner-tr { top:8px;right:8px;border-width:2px 2px 0 0; }
.corner-bl { bottom:8px;left:8px;border-width:0 0 2px 2px; }
.corner-br { bottom:8px;right:8px;border-width:0 2px 2px 0; }
.tb-left { display:flex;align-items:center;gap:8px; }
.tb-deco { color:var(--primary-color);font-size:18px;filter:drop-shadow(0 0 10px var(--primary-color)); }
.tb-title { font-size:22px;font-weight:800;background:var(--dashboard-title-gradient, linear-gradient(90deg,#00ffcc,#fff,#00ffcc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:5px;margin:0; }
.tb-right { display:flex;align-items:center;gap:16px; }
.theme-btn { width:28px;height:28px;border:1px solid var(--dashboard-border, rgba(0,255,204,.4));border-radius:50%;background:var(--dashboard-card-bg, rgba(3,15,35,.55));color:var(--primary-color);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;line-height:1; }
.theme-btn:hover { border-color:var(--primary-color);box-shadow:var(--shadow-neon-sm); }
.tb-tag { font-size:11px;color:var(--primary-color);border:1px solid var(--dashboard-border, rgba(0,255,204,.5));border-radius:12px;padding:2px 14px;text-shadow:0 0 8px var(--primary-color); }
.tb-time { font-size:14px;color:var(--dashboard-muted, #a0e8d0);font-variant-numeric:tabular-nums; }

.top-section { flex:0 0 72vh;display:flex;gap:20px;padding:10px 0;min-height:0;z-index:2; }
.bottom-section { flex:0 0 calc(28vh - 60px);display:flex;gap:20px;padding:0 0 8px;min-height:0;z-index:2; }

.col-left { flex:0 0 22%;display:flex;flex-direction:column;gap:20px;min-width:0; }
.col-center { flex:1;display:flex;flex-direction:column;min-width:0; }
.col-right { flex:0 0 28%;display:flex;flex-direction:column;gap:20px;min-width:0; }

.flex-1 { flex:1;min-height:0; }
.flex-2 { flex:2;min-height:0; }
.flex-3 { flex:3;min-height:0; }

.box { background:var(--dashboard-card-bg, linear-gradient(135deg,rgba(3,15,35,0.55),rgba(5,22,48,0.6)));border:1px solid var(--dashboard-border, rgba(0,255,204,0.22));border-radius:8px;padding:16px;backdrop-filter:blur(12px);box-shadow:var(--dashboard-shadow, 0 0 16px rgba(0,255,204,0.1),0 0 32px rgba(0,255,204,0.04),inset 0 0 16px rgba(0,255,204,0.04));position:relative;overflow:hidden;display:flex;flex-direction:column; }
.box::before { content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--primary-color),transparent);animation:sweep 3s ease-in-out infinite; }
@keyframes sweep { 0%,100%{opacity:.15;transform:scaleX(.1)} 50%{opacity:1;transform:scaleX(1)} }
.box-head { font-size:13px;font-weight:700;color:var(--dashboard-heading, #d0f0e8);margin-bottom:10px;display:flex;align-items:center;gap:6px;flex-shrink:0; }
.bh-diamond { color:var(--primary-color);font-size:12px;text-shadow:0 0 6px var(--primary-color); }
.chart-fill { flex:1;min-height:0; }
.gauge-row { position:relative;flex:1;min-height:0; }
.gauge-fill { width:100%;height:100%; }

.metric-row { display:flex;gap:10px;margin-top:6px; }
.metric { flex:1;text-align:center;padding:6px;background:var(--dashboard-soft-bg, rgba(0,255,204,0.04));border-radius:6px; }
.m-label { font-size:10px;color:var(--dashboard-muted, #88bbaa); }
.m-val { font-size:20px;font-weight:800; }
.m-unit { font-size:10px;margin-left:2px;opacity:0.7; }
.c-cyan { color:#00ffcc; }
.c-orange { color:#faad14; }
.c-red { color:#ff6b6b; }

.status-list { display:flex;flex-direction:column;gap:4px; }
.sl-row { display:flex;align-items:center;gap:8px;font-size:11px; }
.sl-dot { width:6px;height:6px;border-radius:50%;flex-shrink:0; }
.sl-dot.g { background:#52c41a;box-shadow:0 0 4px #52c41a; }
.sl-dot.r { background:#ff4d4f;box-shadow:0 0 4px #ff4d4f;animation:pulse 2s infinite; }
.sl-label { color:var(--dashboard-muted, #88bbaa);flex:1; }
.sl-val { color:var(--dashboard-heading, #d0e8e0); }

.center-stats { display:flex;gap:24px;justify-content:center;margin-top:8px; }
.cs-item { text-align:center; }
.cs-val { font-size:26px;font-weight:900;background:var(--dashboard-stat-gradient, linear-gradient(180deg,#fff,#66bbff));-webkit-background-clip:text;-webkit-text-fill-color:transparent; }
.cs-unit { font-size:10px;color:var(--dashboard-muted, #6aa090);margin-left:2px; }
.cs-lbl { display:block;font-size:10px;color:var(--dashboard-muted, #4a7a8a); }

.chain { display:flex;align-items:center;gap:0;flex:1; }
.chain-node { text-align:center;flex:1; }
.cn-icon { font-size:22px; }
.cn-label { font-size:9px;color:var(--dashboard-muted, #88bbaa);margin-top:2px; }
.chain-arrow { color:var(--dashboard-muted, #1e4a7a);font-size:14px;flex-shrink:0; }

.alert-list { display:flex;flex-direction:column;gap:5px; }
.alert-row { display:flex;gap:8px;font-size:10px;padding:4px 8px;border-radius:4px; }
.alert-row.warn { background:rgba(250,173,20,0.08);border-left:2px solid #faad14; }
.alert-row.info { background:rgba(0,255,204,0.04);border-left:2px solid #00ffcc; }
.al-time { color:var(--dashboard-muted, #6aa090);flex-shrink:0;font-variant-numeric:tabular-nums; }
.al-msg { color:var(--dashboard-heading, #d0e8e0); }

@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(1.5)} }

:global([data-theme="light"]) .particle-canvas { opacity: 0.08; }
:global([data-theme="light"]) .device-screen {
  --dashboard-bg: linear-gradient(180deg, #f8fafc 0%, #eef4f7 100%);
  --dashboard-text: #0f172a;
  --dashboard-heading: #1f2937;
  --dashboard-muted: #475569;
  --dashboard-border: rgba(0, 150, 136, 0.18);
  --dashboard-card-bg: rgba(255, 255, 255, 0.82);
  --dashboard-soft-bg: rgba(15, 23, 42, 0.035);
  --dashboard-top-bg: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,255,255,0.55));
  --dashboard-title-gradient: linear-gradient(90deg, #0f766e, #0f172a, #0891b2);
  --dashboard-stat-gradient: linear-gradient(180deg, #0f172a, #0e7490);
  --dashboard-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}
</style>
