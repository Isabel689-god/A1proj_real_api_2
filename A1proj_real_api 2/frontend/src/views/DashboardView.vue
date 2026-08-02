<template>
  <StarField />
  <div class="big-screen">

    <header class="top-bar">
      <span class="corner-tl"></span><span class="corner-br"></span>
      <span class="corner-tr"></span><span class="corner-bl"></span>
      <div class="tb-left"><span class="tb-deco">◈</span></div>
      <h1 class="tb-title">智能检修数据中台</h1>
      <div class="tb-right">
        <button class="theme-btn" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
          {{ theme === 'dark' ? '☀' : '☾' }}
        </button>
        <span class="tb-tag">● 实时</span>
        <span class="tb-time">{{ now }}</span>
      </div>
    </header>

    <div class="top-section">
      <aside class="col-left">
        <section class="box flex-2">
          <div class="box-head"><span class="bh-diamond">◇</span>相关信息</div>
          <div class="cards-2x3">
            <div v-for="c in overviewCards" :key="c.label" class="mini-card">
              <div class="mc-val" :style="{color:c.color}">{{ c.display }}</div>
              <div class="mc-icon">{{ c.icon }}</div>
              <div class="mc-label">{{ c.label }}</div>
            </div>
          </div>
        </section>
        <section class="box flex-3">
          <div class="box-head"><span class="bh-diamond">◇</span>故障类型分布</div>
          <v-chart :option="faultTypeRadar" autoresize class="chart-fill" />
        </section>
      </aside>

      <main class="col-center">
        <section class="box flex-1">
          <div class="box-head">
            <span class="bh-diamond">◇</span>知识图谱
            <span class="legend-row">
              <span class="lg-dot" style="background:#00ffcc"></span>设备
              <span class="lg-dot" style="background:#52c41a"></span>部件
              <span class="lg-dot" style="background:#ff4d4f"></span>故障
              <span class="lg-dot" style="background:#faad14"></span>原因
              <span class="lg-dot" style="background:#13c2c2"></span>方案
            </span>
          </div>
          <v-chart :option="graphOption" autoresize class="chart-fill" />
        </section>
      </main>

      <aside class="col-right">
        <section class="box flex-2">
          <div class="box-head"><span class="bh-diamond">◇</span>全局检修记录</div>
          <div class="dyn-table">
            <div class="dt-hdr"><span>时间</span><span>检修记录</span><span>状态</span></div>
            <div v-for="(r, i) in dynamics" :key="i" class="dt-row">
              <span class="dtr-time">{{ r.time }}</span><span class="dtr-msg">{{ r.msg }}</span><span class="dtr-st" :class="r.st"><span class="st-icon">{{ r.icon }}</span>{{ r.stText }}</span>
            </div>
          </div>
        </section>
        <section class="box flex-3">
          <div class="box-head"><span class="bh-diamond">◇</span>故障严重度分布</div>
          <v-chart :option="pyramidOption" autoresize class="chart-fill" />
        </section>
      </aside>
    </div>

    <div class="bottom-section">
      <section class="box flex-1">
        <div class="box-head"><span class="bh-diamond">◇</span>知识标签热度</div>
        <v-chart :option="tagBar" autoresize class="chart-fill" />
      </section>
      <section class="box flex-1">
        <div class="box-head"><span class="bh-diamond">◇</span>诊断调用趋势</div>
        <v-chart :option="trendLine" autoresize class="chart-fill" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, inject } from 'vue'
import type { Ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart, PieChart, GraphChart, RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StarField from '../components/StarField.vue'

use([BarChart, LineChart, PieChart, GraphChart, RadarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const theme = inject<Ref<'dark' | 'light'>>('theme', ref<'dark' | 'light'>('dark'))
const toggleTheme = inject<() => void>('toggleTheme', () => {})

const now = ref('')
let t: number
onMounted(() => { tick(); t = window.setInterval(tick, 1000); onUnmounted(() => clearInterval(t)) })
function tick() { now.value = new Date().toLocaleString('zh-CN', { hour12: false }) }

const overviewCards = reactive([
  { label: '设备型号', val: 0, display: 0, icon: '🖥️', color: '#00ffcc' },
  { label: '部件类型', val: 0, display: 0, icon: '⚙️', color: '#52c41a' },
  { label: '故障类型', val: 0, display: 0, icon: '⚠️', color: '#ff4d4f' },
  { label: '故障原因', val: 0, display: 0, icon: '🔍', color: '#faad14' },
  { label: '解决方案', val: 0, display: 0, icon: '✅', color: '#13c2c2' },
  { label: '知识文档', val: 0, display: 0, icon: '📄', color: '#a78bfa' },
])

let animId = 0
function startCountUp() {
  const step = () => {
    let running = false
    for (const c of overviewCards) {
      if (Math.abs(c.display - c.val) < 1) { c.display = c.val; continue }
      c.display = Math.round(c.display + (c.val - c.display) * 0.18)
      running = true
    }
    if (running) animId = requestAnimationFrame(step)
  }
  cancelAnimationFrame(animId)
  animId = requestAnimationFrame(step)
}

const dynamics = reactive([
  { time: '14:32', msg: '0i Mate-D 主轴异响检修完成', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '14:18', msg: '西门子 808D 驱动器过热排查', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '14:05', msg: '三菱 M700 急停回路检修中', st: 'warn', stText: '检修中', icon: '⟳' },
  { time: '13:55', msg: '数控铣床刀库卡刀清理完成', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '13:30', msg: '加工中心润滑系统保养', st: 'ok', stText: '已完成', icon: '✓' },
  { time: '13:12', msg: 'Fanuc 0i-TF 伺服电机异响排查', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '12:45', msg: '海德汉 iTNC530 光栅尺清洁', st: 'ok', stText: '已完成', icon: '✓' },
  { time: '12:20', msg: '马扎克 VCN 冷却液泵更换', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '11:48', msg: '大连机床 CK6150 尾座偏移校正', st: 'warn', stText: '检修中', icon: '⟳' },
  { time: '11:15', msg: '沈阳机床 VMC850 换刀臂卡滞修复', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '10:40', msg: '德马吉 DMU50 五轴精度校准', st: 'ok', stText: '已完成', icon: '✓' },
  { time: '10:05', msg: '兄弟 S500Z 主轴拉刀力检测', st: 'ok', stText: '已修复', icon: '✓' },
  { time: '09:30', msg: '牧野 F5 导轨防护罩更换完成', st: 'ok', stText: '已完成', icon: '✓' },
])

const deviceFaultLinks = ref<{ name: string; value: number }[]>([])
const tagDistribution = ref<{ name: string; value: number }[]>([])
const faultCauseDist = ref<{ name: string; value: number }[]>([])
const entitySummary = ref<{ name: string; value: number }[]>([])
const graphNodes = ref<any[]>([])
const graphEdges = ref<any[]>([])
const graphCats = ref<any[]>([])

async function fetchData() {
  try {
    const [r1, r2] = await Promise.all([fetch(`${API_BASE}/dashboard/overview`), fetch(`${API_BASE}/knowledge/graph`)])
    const j1 = await r1.json(); const j2 = await r2.json()
    if (j1.code === 200) {
      const d = j1.data
      overviewCards[0].val = d.overview.total_devices; overviewCards[1].val = d.overview.total_components
      overviewCards[2].val = d.overview.total_faults; overviewCards[3].val = d.overview.total_causes
      overviewCards[4].val = d.overview.total_solutions; overviewCards[5].val = d.overview.total_documents
      startCountUp()
      deviceFaultLinks.value = d.device_fault_links || []; tagDistribution.value = d.tag_distribution || []
      faultCauseDist.value = d.fault_cause_distribution || []; entitySummary.value = d.entity_summary || []
    }
    if (j2.code === 200 || j2.data) { const g = j2.data || j2; graphNodes.value = g.nodes || []; graphEdges.value = g.edges || []; graphCats.value = g.categories || [] }
  } catch(e) { console.error(e) }
}
onMounted(() => { fetchData(); const i = window.setInterval(fetchData, 15000); onUnmounted(() => clearInterval(i)) })

const tc = computed(() => theme.value === 'light' ? '#475569' : '#88bbaa')
const ac = computed(() => theme.value === 'light' ? '#cbd5e1' : '#0d2a40')
const tooltipSkin = computed(() => theme.value === 'light'
  ? { backgroundColor: '#ffffff', borderColor: '#cbd5e1', textStyle: { color: '#1f2937' } }
  : { backgroundColor: '#0a1428', borderColor: '#0d4a7a', textStyle: { color: '#c0d0e0' } }
)

const faultTypeRadar = computed(() => {
  const items = entitySummary.value.length ? entitySummary.value : [{ name: '加载中', value: 1 }, { name: '...', value: 1 }]
  const maxVal = Math.max(...items.map(x => x.value), 1)
  return { backgroundColor:'transparent', tooltip:{...tooltipSkin.value},
    radar:{ center:['50%','52%'],radius:'62%', indicator:items.map(d=>({name:d.name,max:maxVal*1.2})), axisName:{color:tc.value,fontSize:9},
      splitArea:{areaStyle:{color:['rgba(0,255,204,0.03)','rgba(0,255,204,0.06)']}}, splitLine:{lineStyle:{color:'rgba(0,255,204,0.2)'}}, axisLine:{lineStyle:{color:'rgba(0,255,204,0.3)'}} },
    series:[{ type:'radar',
      data:[{ value:items.map(d=>d.value),name:'知识实体',
        areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(0,255,204,0.2)'},{offset:1,color:'rgba(0,255,204,0.02)'}]}},
        lineStyle:{color:'#00ffcc',width:2,shadowBlur:8,shadowColor:'#00ffcc'},
        itemStyle:{color:'#00ffcc',shadowBlur:6,shadowColor:'#00ffcc'},
        symbol:'circle',symbolSize:5 }],
      animationDuration:1500,
    }],
  }
})

const tagBar = computed(() => ({
  backgroundColor:'transparent', tooltip:{trigger:'axis',...tooltipSkin.value}, grid:{left:'3%',right:'4%',top:'8%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:tagDistribution.value.slice(0,8).map(d=>d.name),axisLabel:{color:tc.value,fontSize:9,rotate:30},axisLine:{lineStyle:{color:ac.value}}},
  yAxis:{type:'value',axisLabel:{color:tc.value,fontSize:9},splitLine:{lineStyle:{color:ac.value,type:'dashed'}}},
  series:[{type:'bar',barWidth:'55%',
    data:tagDistribution.value.slice(0,8).map(d=>({value:d.value,
      itemStyle:{borderRadius:[4,4,0,0],
        color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'#00ffcc'},{offset:0.5,color:'rgba(0,200,160,0.6)'},{offset:1,color:'rgba(0,50,80,0.3)'}]},
        shadowBlur:8,shadowColor:'rgba(0,255,204,0.3)',shadowOffsetY:4}})),
    animationDuration:1500}],
}))

const graphOption = computed(() => ({
  backgroundColor:'transparent', tooltip:{...tooltipSkin.value},
  series:[{ type:'graph',layout:'force',roam:true,draggable:false, force:{repulsion:600,edgeLength:[50,180],gravity:0.04,friction:0.6}, edgeSymbol:['none','none'],
    lineStyle:{color:'rgba(0,255,204,0.3)',curveness:0.2,opacity:0.5,shadowBlur:3,shadowColor:'rgba(0,255,204,0.2)'},
    label:{show:true,color:theme.value === 'light' ? '#1f2937' : '#ffffff',fontSize:8,position:'right',formatter:(p:any)=>p.name.length>10?p.name.slice(0,10)+'…':p.name},
    emphasis:{focus:'adjacency',label:{show:true,color:theme.value === 'light' ? '#111827' : '#fff',fontSize:11},itemStyle:{shadowBlur:25,shadowColor:'#00ffcc'}},
    categories:graphCats.value.length?graphCats.value:[
      {name:'device',itemStyle:{color:'#00ffcc',shadowBlur:10,shadowColor:'#00ffcc'}},
      {name:'component',itemStyle:{color:'#52c41a',shadowBlur:8,shadowColor:'#52c41a'}},
      {name:'fault',itemStyle:{color:'#ff4d4f',shadowBlur:12,shadowColor:'#ff4d4f'}},
      {name:'fault_cause',itemStyle:{color:'#faad14',shadowBlur:8,shadowColor:'#faad14'}},
      {name:'solution',itemStyle:{color:'#13c2c2',shadowBlur:8,shadowColor:'#13c2c2'}},
    ],
    nodes:graphNodes.value,edges:graphEdges.value, animationDuration:2000,animationEasingUpdate:'elasticOut',
  }],
}))

const pyramidOption = computed(() => ({
  backgroundColor:'transparent', tooltip:{trigger:'item',...tooltipSkin.value},
  series:[{ type:'pie',radius:['55%','82%'],center:['50%','52%'],
    itemStyle:{borderRadius:4,borderColor:'rgba(0,255,204,0.3)',borderWidth:1.5},
    label:{color:tc.value,fontSize:9,formatter:'{b}\n{d}%'},
    emphasis:{scaleSize:10,shadowBlur:25,shadowColor:'rgba(0,255,204,0.4)',label:{fontSize:13,fontWeight:'bold',color:theme.value === 'light' ? '#111827' : '#fff'}},
    data:[
      {value:45,name:'轻微',itemStyle:{color:{type:'linear',x:0,y:0,x2:1,y2:1,colorStops:[{offset:0,color:'#00ff88'},{offset:1,color:'#52c41a'}]}}},
      {value:28,name:'普通',itemStyle:{color:{type:'linear',x:0,y:0,x2:1,y2:1,colorStops:[{offset:0,color:'#00ffcc'},{offset:1,color:'#0099aa'}]}}},
      {value:12,name:'严重',itemStyle:{color:{type:'linear',x:0,y:0,x2:1,y2:1,colorStops:[{offset:0,color:'#ff6b6b'},{offset:1,color:'#ff4d4f'}]}}},
    ],
    animationType:'scale',animationEasing:'elasticOut',animationDuration:1500,
  }],
  graphic:[{type:'text',left:'center',top:'42%',style:{text:'85条',textAlign:'center',fill:theme.value === 'light' ? '#1f2937' : '#d0f0e8',fontSize:18,fontWeight:'bold'}},{type:'text',left:'center',top:'52%',style:{text:'故障总计',textAlign:'center',fill:tc.value,fontSize:11}}],
}))

const trendLine = computed(() => ({
  backgroundColor:'transparent', tooltip:{trigger:'axis',...tooltipSkin.value}, grid:{left:'3%',right:'4%',top:'8%',bottom:'3%',containLabel:true},
  xAxis:{type:'category',data:['周一','周二','周三','周四','周五','周六','周日'],axisLabel:{color:tc.value,fontSize:9},axisLine:{lineStyle:{color:ac.value}}},
  yAxis:{type:'value',axisLabel:{color:tc.value,fontSize:9},splitLine:{lineStyle:{color:ac.value,type:'dashed'}}},
  series:[{type:'line',smooth:true,data:[45,52,38,61,55,43,58],
    lineStyle:{color:'#00ffcc',width:2.5,shadowBlur:8,shadowColor:'#00ffcc'},
    areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(0,255,204,0.3)'},{offset:1,color:'rgba(0,255,204,0)'}]}},
    itemStyle:{color:'#00ffcc',shadowBlur:10,shadowColor:'#00ffcc'},
    symbol:'circle',symbolSize:7,
  }],
}))
</script>

<style scoped>
.big-screen { width:100vw;height:100vh;font-family:'Microsoft YaHei','PingFang SC',monospace;color:var(--dashboard-text, #e0f0ff);overflow:hidden;display:flex;flex-direction:column;padding:0 20px 8px;box-sizing:border-box;position:relative;background:var(--dashboard-bg, transparent); }

/* ═══ 顶部 ═══ */
.top-bar { display:flex;align-items:center;justify-content:space-between;height:52px;flex-shrink:0;z-index:2;background:var(--dashboard-top-bg, linear-gradient(180deg,rgba(0,80,100,0.35),transparent));border-bottom:1px solid var(--dashboard-border, rgba(0,255,204,0.2));padding:0 20px;position:relative; }
.corner-tl,.corner-tr,.corner-bl,.corner-br { position:absolute;width:16px;height:16px;border-color:var(--primary-color);border-style:solid;opacity:.7; }
.corner-tl { top:8px;left:8px;border-width:2px 0 0 2px; }
.corner-tr { top:8px;right:8px;border-width:2px 2px 0 0; }
.corner-bl { bottom:8px;left:8px;border-width:0 0 2px 2px; }
.corner-br { bottom:8px;right:8px;border-width:0 2px 2px 0; }
.tb-left { display:flex;align-items:center;gap:8px; }
.tb-deco { color:var(--primary-color);font-size:18px;animation:spin 6s linear infinite;filter:drop-shadow(0 0 10px var(--primary-color)); }
@keyframes spin { to{transform:rotate(360deg)} }
.tb-title { font-size:22px;font-weight:800;background:var(--dashboard-title-gradient, linear-gradient(90deg,#00ffcc,#fff,#00ffcc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:5px;margin:0; }
.tb-right { display:flex;align-items:center;gap:16px; }
.theme-btn { width:28px;height:28px;border:1px solid var(--dashboard-border, rgba(0,255,204,.4));border-radius:50%;background:var(--dashboard-card-bg, rgba(3,15,35,.55));color:var(--primary-color);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;line-height:1; }
.theme-btn:hover { border-color:var(--primary-color);box-shadow:var(--shadow-neon-sm); }
.tb-tag { font-size:11px;color:var(--primary-color);border:1px solid var(--dashboard-border, rgba(0,255,204,.5));border-radius:12px;padding:2px 14px;text-shadow:0 0 8px var(--primary-color); }
.tb-time { font-size:14px;color:var(--dashboard-muted, #a0e8d0);font-variant-numeric:tabular-nums; }

/* ═══ 上下分层 ═══ */
.top-section { flex:0 0 72vh;display:flex;gap:20px;padding:10px 0;min-height:0;z-index:2; }
.bottom-section { flex:0 0 calc(28vh - 60px);display:flex;gap:20px;padding:0 0 8px;min-height:0;z-index:2; }

/* ═══ 三栏比例 ═══ */
.col-left { flex:0 0 20%;display:flex;flex-direction:column;gap:20px;min-width:0; }
.col-center { flex:0 0 50%;display:flex;flex-direction:column;min-width:0; }
.col-right { flex:0 0 30%;display:flex;flex-direction:column;gap:20px;min-width:0; }

/* ═══ 弹性高度分配 ═══ */
.flex-1 { flex:1;min-height:0; }
.flex-2 { flex:2;min-height:0; }
.flex-3 { flex:3;min-height:0; }

/* ═══ 模块框 ═══ */
.box { background:var(--dashboard-card-bg, linear-gradient(135deg,rgba(3,15,35,0.55),rgba(5,22,48,0.6)));border:1px solid var(--dashboard-border, rgba(0,255,204,0.22));border-radius:8px;padding:16px;backdrop-filter:blur(12px);box-shadow:var(--dashboard-shadow, 0 0 16px rgba(0,255,204,0.1),0 0 32px rgba(0,255,204,0.04),inset 0 0 16px rgba(0,255,204,0.04));position:relative;overflow:hidden;display:flex;flex-direction:column; }
.box::before { content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--primary-color),transparent);animation:sweep 3s ease-in-out infinite; }
@keyframes sweep { 0%,100%{opacity:.15;transform:scaleX(.1)} 50%{opacity:1;transform:scaleX(1)} }
.box-head { font-size:13px;font-weight:700;color:var(--dashboard-heading, #d0f0e8);margin-bottom:10px;display:flex;align-items:center;gap:6px;flex-shrink:0; }
.bh-diamond { color:var(--primary-color);font-size:12px;text-shadow:0 0 6px var(--primary-color); }
.legend-row { display:flex;align-items:center;gap:5px;margin-left:auto;font-size:10px;color:var(--dashboard-muted, #88bbaa);font-weight:400; }
.lg-dot { width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0;box-shadow:0 0 4px currentColor; }
.chart-fill { flex:1;min-height:0; }

/* ═══ 卡片 ═══ */
.cards-2x3 { display:grid;grid-template-columns:1fr 1fr;gap:8px;flex:1; }
.mini-card { background:var(--dashboard-soft-bg, linear-gradient(135deg,rgba(0,255,204,0.06),rgba(0,100,120,0.03)));border:1px solid var(--dashboard-border, rgba(0,255,204,0.18));border-radius:6px;padding:12px 8px;text-align:center;transition:transform .3s,border-color .3s,box-shadow .3s;display:flex;flex-direction:column;justify-content:center;box-shadow:0 0 8px rgba(0,255,204,0.06); }
.mini-card:hover { transform:translateY(-2px);border-color:var(--primary-color);box-shadow:var(--shadow-neon-sm); }
.mc-val { font-size:26px;font-weight:900;font-variant-numeric:tabular-nums; }
.mc-icon { font-size:18px;margin:2px 0; }
.mc-label { font-size:11px;color:var(--dashboard-muted, #88bbaa); }

/* ═══ 动态表格 ═══ */
.dyn-table { font-size:11px;flex:1;overflow:auto; }
.dt-hdr { display:flex;gap:8px;color:var(--dashboard-muted, #6aa090);border-bottom:1px solid var(--dashboard-border, rgba(0,255,204,.12));padding-bottom:6px;margin-bottom:4px;font-weight:600; }
.dt-hdr span:first-child { width:42px; }
.dt-hdr span:nth-child(2) { flex:1; }
.dt-hdr span:last-child { width:46px; }
.dt-row { display:flex;gap:8px;padding:4px 0;align-items:center;border-bottom:1px solid var(--dashboard-row-border, rgba(0,255,204,.04)); }
.dtr-time { width:42px;color:var(--dashboard-muted, #6aa090);flex-shrink:0;font-variant-numeric:tabular-nums; }
.dtr-msg { flex:1;color:var(--dashboard-heading, #d0e8e0);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.dtr-st { width:52px;text-align:center;font-size:9px;padding:2px 6px;border-radius:4px;flex-shrink:0;display:flex;align-items:center;gap:2px;justify-content:center; }
.st-icon { font-size:9px; }
.dtr-st.ok { color:#00ffcc;background:rgba(0,255,204,.12);border:1px solid rgba(0,255,204,.2); }
.dtr-st.warn { color:#ffaa00;background:rgba(255,170,0,.12);border:1px solid rgba(255,170,0,.25); }

:global([data-theme="light"]) .star-bg { opacity: 0.08; }
:global([data-theme="light"]) .big-screen {
  --dashboard-bg: linear-gradient(180deg, #f8fafc 0%, #eef4f7 100%);
  --dashboard-text: #0f172a;
  --dashboard-heading: #1f2937;
  --dashboard-muted: #475569;
  --dashboard-border: rgba(0, 150, 136, 0.18);
  --dashboard-row-border: rgba(15, 23, 42, 0.08);
  --dashboard-card-bg: rgba(255, 255, 255, 0.82);
  --dashboard-soft-bg: rgba(15, 23, 42, 0.035);
  --dashboard-top-bg: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,255,255,0.55));
  --dashboard-title-gradient: linear-gradient(90deg, #0f766e, #0f172a, #0891b2);
  --dashboard-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}
</style>
