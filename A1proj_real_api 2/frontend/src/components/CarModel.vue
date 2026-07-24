<template>
  <div class="machine-stage">
    <svg viewBox="0 0 640 380" class="machine-svg" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bodyGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#1e3555" />
          <stop offset="40%" stop-color="#294870" />
          <stop offset="100%" stop-color="#152640" />
        </linearGradient>
        <linearGradient id="darkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0f1e35" />
          <stop offset="100%" stop-color="#182d48" />
        </linearGradient>
        <linearGradient id="metalGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#2a4060" />
          <stop offset="50%" stop-color="#3a5580" />
          <stop offset="100%" stop-color="#253a55" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2.5" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="panelGlow">
          <feGaussianBlur stdDeviation="1.5" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      <!-- 地面投影 -->
      <ellipse cx="320" cy="355" rx="280" ry="10" fill="rgba(0,255,204,0.03)" />

      <!-- ═══ 底座 ═══ -->
      <rect x="60" y="310" width="520" height="18" rx="3" fill="url(#bodyGrad)" stroke="rgba(0,255,204,0.35)" stroke-width="1.2" />
      <!-- 底座加强肋 -->
      <rect x="70" y="300" width="500" height="10" rx="2" fill="url(#metalGrad)" stroke="rgba(0,255,204,0.2)" stroke-width="0.8" />
      <!-- 地脚螺栓 -->
      <circle cx="100" cy="324" r="4" fill="#1a3050" stroke="rgba(0,255,204,0.3)" stroke-width="0.8" />
      <circle cx="540" cy="324" r="4" fill="#1a3050" stroke="rgba(0,255,204,0.3)" stroke-width="0.8" />

      <!-- ═══ 工作台 ═══ -->
      <rect x="100" y="265" width="260" height="35" rx="4" fill="url(#darkGrad)" stroke="rgba(0,255,204,0.35)" stroke-width="1" />
      <!-- T型槽 -->
      <line x1="130" y1="275" x2="130" y2="298" stroke="rgba(0,255,204,0.25)" stroke-width="2" />
      <line x1="180" y1="275" x2="180" y2="298" stroke="rgba(0,255,204,0.25)" stroke-width="2" />
      <line x1="230" y1="275" x2="230" y2="298" stroke="rgba(0,255,204,0.25)" stroke-width="2" />
      <line x1="280" y1="275" x2="280" y2="298" stroke="rgba(0,255,204,0.25)" stroke-width="2" />
      <line x1="330" y1="275" x2="330" y2="298" stroke="rgba(0,255,204,0.25)" stroke-width="2" />
      <text x="230" y="295" fill="#6aa090" font-size="8" text-anchor="middle">工作台 1200×500mm</text>

      <!-- 工件 -->
      <rect x="170" y="250" width="100" height="15" rx="4" fill="#3a5070" stroke="#00ffcc" stroke-width="1" filter="url(#panelGlow)" />
      <text x="220" y="261" fill="#d0e8e0" font-size="7" text-anchor="middle" font-weight="600">工件</text>

      <!-- ═══ 立柱 ═══ -->
      <rect x="440" y="100" width="70" height="210" rx="5" fill="url(#bodyGrad)" stroke="rgba(0,255,204,0.4)" stroke-width="1.2" />
      <!-- 立柱导轨 -->
      <line x1="460" y1="110" x2="460" y2="305" stroke="rgba(0,255,204,0.25)" stroke-width="2.5" />
      <line x1="490" y1="110" x2="490" y2="305" stroke="rgba(0,255,204,0.25)" stroke-width="2.5" />
      <text x="475" y="210" fill="#6aa090" font-size="8" text-anchor="middle" transform="rotate(-90,475,210)">Z轴导轨</text>

      <!-- ═══ 主轴箱 ═══ -->
      <rect x="390" y="80" width="130" height="65" rx="6" fill="url(#darkGrad)" stroke="#00ffcc" stroke-width="1.5" filter="url(#glow)" />
      <text x="455" y="103" fill="#00ffcc" font-size="10" text-anchor="middle" font-weight="700">主轴箱</text>
      <text x="455" y="118" fill="#88bbaa" font-size="7" text-anchor="middle">BT40 · 12000rpm · 15kW</text>
      <text x="455" y="133" fill="#6aa090" font-size="7" text-anchor="middle">伺服直驱 · 油雾润滑</text>

      <!-- ═══ 主轴 ═══ -->
      <rect x="430" y="145" width="50" height="65" rx="4" fill="url(#metalGrad)" stroke="rgba(0,255,204,0.5)" stroke-width="1.2" />
      <!-- 主轴拉杆 -->
      <line x1="455" y1="150" x2="455" y2="208" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
      <text x="455" y="180" fill="#00ffcc" font-size="8" text-anchor="middle" font-weight="700">主轴</text>
      <!-- 主轴前端 -->
      <rect x="440" y="210" width="30" height="10" rx="2" fill="#ffaa00" stroke="#faad14" stroke-width="0.8" filter="url(#panelGlow)" />

      <!-- ═══ 刀柄 + 刀具 ═══ -->
      <rect x="447" y="220" width="16" height="18" rx="2" fill="#2a5070" stroke="#00ffcc" stroke-width="0.8" />
      <text x="455" y="232" fill="#c0d0e0" font-size="6" text-anchor="middle">BT40</text>
      <rect x="449" y="238" width="12" height="40" rx="1" fill="#ff8800" stroke="#faad14" stroke-width="0.8" filter="url(#glow)" />
      <text x="455" y="255" fill="#fff" font-size="7" text-anchor="middle" font-weight="700">T12</text>
      <text x="455" y="268" fill="#ffdd88" font-size="5" text-anchor="middle">φ20</text>

      <!-- 切削示意 -->
      <line x1="455" y1="278" x2="220" y2="260" stroke="rgba(255,170,0,0.2)" stroke-width="1" stroke-dasharray="3,3" />

      <!-- ═══ 刀库 ═══ -->
      <rect x="520" y="130" width="55" height="45" rx="5" fill="url(#darkGrad)" stroke="rgba(0,255,204,0.35)" stroke-width="1" />
      <text x="548" y="150" fill="#88bbaa" font-size="8" text-anchor="middle">刀库</text>
      <text x="548" y="165" fill="#52c41a" font-size="11" text-anchor="middle" font-weight="700">24</text>
      <!-- 刀套 -->
      <circle cx="535" cy="148" r="4" fill="none" stroke="rgba(0,255,204,0.25)" stroke-width="0.8" />
      <circle cx="560" cy="148" r="4" fill="none" stroke="rgba(0,255,204,0.25)" stroke-width="0.8" />
      <circle cx="548" cy="140" r="4" fill="none" stroke="rgba(0,255,204,0.25)" stroke-width="0.8" />

      <!-- ═══ 数控面板 ═══ -->
      <rect x="520" y="190" width="65" height="60" rx="5" fill="#0a1628" stroke="rgba(0,255,204,0.45)" stroke-width="1" />
      <!-- 屏幕 -->
      <rect x="528" y="198" width="49" height="30" rx="3" fill="#030c18" stroke="#00ffcc" stroke-width="0.6" filter="url(#panelGlow)" />
      <text x="553" y="210" fill="#00ffcc" font-size="7" text-anchor="middle" font-weight="700">FANUC</text>
      <text x="553" y="222" fill="#88bbaa" font-size="6" text-anchor="middle">0i-MF Plus</text>
      <!-- 按键 -->
      <rect x="528" y="234" width="10" height="4" rx="1" fill="#1e3a5f" stroke="rgba(0,255,204,0.2)" stroke-width="0.5" />
      <rect x="542" y="234" width="10" height="4" rx="1" fill="#1e3a5f" stroke="rgba(0,255,204,0.2)" stroke-width="0.5" />
      <rect x="556" y="234" width="10" height="4" rx="1" fill="#00ffcc" stroke="rgba(0,255,204,0.4)" stroke-width="0.5" filter="url(#panelGlow)" />
      <rect x="528" y="242" width="10" height="4" rx="1" fill="#1e3a5f" stroke="rgba(0,255,204,0.2)" stroke-width="0.5" />

      <!-- ═══ 防护罩 ═══ -->
      <path d="M70,260 L70,120 L355,120 L355,260" fill="rgba(0,255,204,0.02)" stroke="rgba(0,255,204,0.12)" stroke-width="1" stroke-dasharray="8,4" />
      <line x1="200" y1="120" x2="200" y2="260" stroke="rgba(0,255,204,0.08)" stroke-width="0.5" stroke-dasharray="5,5" />
      <text x="212" y="135" fill="rgba(0,255,204,0.2)" font-size="7">防护罩</text>

      <!-- ═══ 冷却液管 ═══ -->
      <path d="M455,240 C420,250 380,255 340,258" fill="none" stroke="#00ffcc" stroke-width="0.8" stroke-dasharray="3,2" opacity="0.4" />
      <circle cx="340" cy="258" r="2.5" fill="none" stroke="#00ffcc" stroke-width="0.6" opacity="0.5" />
      <text x="395" y="252" fill="rgba(0,255,204,0.25)" font-size="6">冷却液</text>

      <!-- ═══ 排屑器 ═══ -->
      <rect x="80" y="295" width="30" height="10" rx="2" fill="#1e3550" stroke="rgba(0,255,204,0.2)" stroke-width="0.6" />
      <text x="95" y="302" fill="rgba(0,255,204,0.25)" font-size="5" text-anchor="middle">排屑</text>

      <!-- ═══ 数据流线 ═══ -->
      <!-- 面板→主轴箱 -->
      <path d="M552,190 L500,145" fill="none" stroke="rgba(0,255,204,0.3)" stroke-width="0.6" stroke-dasharray="2,4">
        <animate attributeName="stroke-dashoffset" from="0" to="-12" dur="1.5s" repeatCount="indefinite" />
      </path>
      <!-- 主轴箱→刀库 -->
      <path d="M520,112 L548,130" fill="none" stroke="rgba(82,196,26,0.25)" stroke-width="0.5" stroke-dasharray="2,3">
        <animate attributeName="stroke-dashoffset" from="0" to="-10" dur="1.8s" repeatCount="indefinite" />
      </path>

      <!-- 粒子数据流 · 面板→主轴 -->
      <circle r="2.5" fill="#00ffcc" opacity="0.7" filter="url(#glow)">
        <animateMotion dur="2s" repeatCount="indefinite" path="M552,190 L500,145 L455,145" />
      </circle>

      <!-- 粒子数据流 · 主轴→工件 -->
      <circle r="2" fill="#ffaa00" opacity="0.5" filter="url(#glow)">
        <animateMotion dur="3s" repeatCount="indefinite" path="M455,278 L340,265 L220,258" />
      </circle>
    </svg>
    <div class="machine-label">立式加工中心 · VMC850 · CNC Machining Center</div>
  </div>
</template>

<style scoped>
.machine-stage { display:flex;flex-direction:column;align-items:center;justify-content:center; }
.machine-svg { width:580px;height:auto;filter:drop-shadow(0 0 18px rgba(0,255,204,0.06)); }
.machine-label { font-size:11px;color:#4a7a9a;margin-top:4px;letter-spacing:3px; }
</style>
