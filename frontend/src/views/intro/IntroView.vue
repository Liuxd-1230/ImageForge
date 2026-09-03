<template>
  <div class="intro-root" :class="{ reduced, mobile: isMobile }">
    <!-- 纸纹（生成的颗粒，无图片请求） -->
    <div class="paper-grain" aria-hidden="true" />

    <!-- 墨线进度轨（桌面端）：随滚动书写，四幕落点 -->
    <aside v-if="!isMobile" class="ink-rail" aria-hidden="true">
      <svg viewBox="0 0 24 420" class="rail-svg">
        <path
          class="rail-line"
          :d="`M12 0 V ${railLen}`"
          :stroke-dasharray="railLen"
          :stroke-dashoffset="railLen * (1 - railProgress)"
        />
        <g v-for="(m, i) in railMarks" :key="m.label" :transform="`translate(12, ${(i + 1) * railLen / 5})`">
          <circle r="4.5" :class="['rail-dot', { on: railProgress >= (i + 1) / 5 }]" />
          <text x="14" y="4" class="rail-text">{{ m.label }}</text>
        </g>
      </svg>
    </aside>

    <!-- ═══════════ 序 · 一句话被写下 ═══════════ -->
    <section ref="heroEl" class="act hero">
      <span class="hero-vertical" aria-hidden="true">一句话的旅程</span>
      <div class="seal hero-seal" aria-hidden="true">炼</div>

      <div class="hero-inner">
        <p class="kicker mono">IMAGEFORGE · THE JOURNEY OF A SENTENCE</p>
        <h1 class="hero-title serif">
          <span class="ht-line">一句话，</span>
          <span class="ht-line">可以走<em class="ve">多远</em>？</span>
        </h1>

        <p class="seed" aria-label="第一句：夕阳下，蓝发少女在海边微笑">
          <span class="seed-tag mono">第一句</span>
          <button type="button" class="seed-text serif" title="再写一遍" @click="replayType">
            {{ typed }}<span class="cursor" :class="{ blink: typeDone }" aria-hidden="true" />
          </button>
        </p>

        <div class="hero-hint" aria-hidden="true">
          <span class="hint-stroke" />
          <span class="hint-text">向下，送它上路</span>
        </div>
      </div>

      <figure
        v-for="(s, i) in sparks"
        :key="s.src"
        class="spark"
        :class="`spark-${i}`"
        :style="{ transform: `translate3d(${s.dx}px, ${s.dy}px, 0) rotate(${s.rot}deg)` }"
      >
        <img :src="s.src" :alt="s.alt" loading="lazy" @error="removeSpark(i)" />
        <figcaption class="mono">{{ s.caption }}</figcaption>
      </figure>
    </section>

    <!-- ═══════════ 壹 · 拆解与编织（同一舞台，词不离场） ═══════════ -->
    <section ref="forgeEl" class="act forge">
      <div class="forge-stage">
        <h2 class="act-title serif"><span class="act-no">壹</span>拆解，是为了懂得</h2>

        <!-- 测量用幽灵布局（不可见但占位，三套锚点：句中 → 角色簇 → 编译槽） -->
        <div class="ghost ghost-inline serif" aria-hidden="true">
          <span v-for="t in words" :key="t.id" :data-ghost-inline="t.id" class="tok-ghost">{{ t.text }}</span>
        </div>
        <div
          v-for="r in clusterRoles"
          :key="r.key"
          class="ghost ghost-cluster serif"
          :class="`cluster-${r.key}`"
          :data-cluster-box="r.key"
          aria-hidden="true"
        >
          <span
            v-for="t in wordsOf(r.key)"
            :key="t.id"
            :data-ghost-cluster="t.id"
            class="tok-ghost"
          >{{ t.text }}</span>
        </div>
        <div class="ghost ghost-bar mono" aria-hidden="true">
          <span v-for="t in dockOrder" :key="t.id" :data-ghost-dock="t.id" class="tok-ghost dock-ghost">{{ t.text }}</span>
        </div>

        <!-- 活体词元：唯一的演员 -->
        <span
          v-for="t in words"
          :key="t.id"
          class="tok serif"
          :class="{ dim: focusedId && focusedId !== t.id }"
          :style="tokStyle[t.id] || {}"
          tabindex="0"
          :aria-label="`${t.text}，${roles[t.role].label}词`"
          @mouseenter="focusedId = t.id"
          @mouseleave="focusedId = null"
          @focus="focusedId = t.id"
          @blur="focusedId = null"
        >{{ t.text }}</span>
        <span class="tok tok-quality serif" :style="qualityStyle" aria-hidden="true">杰作级</span>

        <!-- 角色标注 -->
        <div
          v-for="r in clusterRoles"
          :key="r.key"
          class="role-label mono"
          :class="[`cluster-${r.key}`, { flash: focusedRole === r.key }]"
          :style="roleLabelStyle"
        >
          <span class="role-swatch" :style="{ background: r.color }" />{{ r.label }}
        </div>

        <!-- 编译槽框架 -->
        <div class="bar-frame" :style="barFrameStyle">
          <span class="bar-label mono">positive prompt</span>
          <svg class="bar-underline" viewBox="0 0 640 10" preserveAspectRatio="none" aria-hidden="true">
            <path
              d="M2 6 Q 160 2 320 6 T 638 5"
              :stroke-dasharray="640"
              :stroke-dashoffset="640 * (1 - underlineP)"
            />
          </svg>
          <span class="bar-quality-hint mono" :style="{ opacity: qualityHintP }">+ 编译器补全</span>
        </div>

        <p class="forge-note serif" :style="{ opacity: forgeNoteP }">同一句话。换了一副骨架。</p>
      </div>
    </section>

    <!-- ═══════════ 贰 · 结晶（词化为像素） ═══════════ -->
    <section ref="crystalEl" class="act crystal">
      <div class="crystal-stage">
        <h2 class="act-title serif"><span class="act-no">贰</span>然后，它成为画</h2>
        <div class="crystal-mat" :style="crystalMatStyle">
          <canvas
            ref="canvasEl"
            class="crystal-canvas"
            role="img"
            aria-label="由「夕阳下，蓝发少女在海边微笑」这句话生成的插画"
          />
          <div class="crystal-seal seal" :class="{ slam: sealSlam }" aria-hidden="true">炼</div>
        </div>
        <p class="crystal-ingredients mono" :style="{ opacity: ingredientsP }">
          杰作级 · 蓝发 少女 · 夕阳下 · 在海边 · 微笑
        </p>
        <p class="crystal-caption serif" :style="captionStyle">它先是一堆词，<br>然后才是一幅画。</p>
      </div>
    </section>

    <!-- ═══════════ 邀 · 写下你的第一句 ═══════════ -->
    <section class="act invite">
      <p class="kicker mono">YOUR TURN</p>
      <h2 class="invite-title serif">现在，<br />写你的第一句。</h2>
      <div class="invite-actions">
        <button type="button" class="cta mono" @click="go('/')">进入创作台</button>
        <button type="button" class="cta-ghost serif" @click="go('/history')">先看看别人的句子</button>
      </div>
      <p class="foot mono">ImageForge · Anima Prompt Studio · 一句话的旅程</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  clamp01, lerp, seg, easeInOutCubic, easeOutCubic, easeOutBack,
  stickyProgress, startChoreo, type ChoreoHandle,
} from './choreo'

const router = useRouter()
function go(path: string) {
  router.push(path)
}

/* ─────────────────────────── 素材 ─────────────────────────── */
const SEED = '夕阳下，蓝发少女在海边微笑。'
const CRYSTAL_SRC = '/api/comfyui/generated/anima_20260902_231959_eca35084.png'
const sparks = reactive([
  { src: '/api/comfyui/generated/anima_20260902_094517_950a934f.png', alt: '海边微笑的蓝发少女插画', caption: '「在海边微笑」', dx: 0, dy: 0, rot: -3 },
  { src: '/api/comfyui/generated/anima_20260902_232048_a148c7a7.png', alt: '粉色长发少女全身插画', caption: '「少女」', dx: 0, dy: 0, rot: 2 },
  { src: '/api/comfyui/generated/anima_20260902_094456_f80808fa.png', alt: '另一张海边的蓝发少女插画', caption: '「蓝发」', dx: 0, dy: 0, rot: 4 },
])
function removeSpark(i: number) {
  sparks.splice(i, 1)
}

/* ─────────────────────── 词元与角色 ─────────────────────── */
type RoleKey = 'scene' | 'character' | 'action' | 'quality'
interface Word { id: string; text: string; role: RoleKey }
const roles: Record<RoleKey, { label: string; color: string }> = {
  scene: { label: '场景', color: '#6B7F4E' },
  character: { label: '角色', color: '#B54A32' },
  action: { label: '动作', color: '#4F6F8F' },
  quality: { label: '品质', color: '#A8842C' },
}
const words: Word[] = [
  { id: 'w1', text: '夕阳下', role: 'scene' },
  { id: 'w2', text: '蓝发', role: 'character' },
  { id: 'w3', text: '少女', role: 'character' },
  { id: 'w4', text: '在海边', role: 'scene' },
  { id: 'w5', text: '微笑', role: 'action' },
]
const qualityWord: Word = { id: 'wq', text: '杰作级', role: 'quality' }
const dockOrder: Word[] = [qualityWord, words[1], words[2], words[0], words[3], words[4]]
const clusterRoles = [
  { key: 'scene' as RoleKey, ...roles.scene },
  { key: 'character' as RoleKey, ...roles.character },
  { key: 'action' as RoleKey, ...roles.action },
]
const wordsOf = (r: RoleKey) => words.filter(w => w.role === r)

/* ─────────────────────── 环境开关 ─────────────────────── */
const reduced = ref(false)
const isMobile = ref(false)
let mqReduced: MediaQueryList | null = null
let mqMobile: MediaQueryList | null = null

/* ─────────────────────── 打字机（序） ─────────────────────── */
const typed = ref('')
const typeDone = ref(false)
let typeTimer: ReturnType<typeof setTimeout> | null = null
function replayType() {
  if (reduced.value) return
  if (typeTimer) clearTimeout(typeTimer)
  typed.value = ''
  typeDone.value = false
  let i = 0
  const tick = () => {
    i++
    typed.value = SEED.slice(0, i)
    if (i < SEED.length) {
      // 45–110ms  jitter：像人写，不像机器吐
      typeTimer = setTimeout(tick, 45 + Math.random() * 65)
    } else {
      typeDone.value = true
    }
  }
  typeTimer = setTimeout(tick, 420)
}

/* ─────────────────────── 锚点测量 ─────────────────────── */
const heroEl = ref<HTMLElement>()
const forgeEl = ref<HTMLElement>()
const crystalEl = ref<HTMLElement>()
const canvasEl = ref<HTMLCanvasElement>()

interface Anchor { x: number; y: number }
const inlineA: Record<string, Anchor> = {}
const clusterA: Record<string, Anchor> = {}
const dockA: Record<string, Anchor> = {}
let measured = false
let dockScale = 0.45   // 词元入槽时的缩小比（大衬线 → 槽内小字）

function measureGhosts() {
  const stage = forgeEl.value?.querySelector('.forge-stage') as HTMLElement | null
  if (!stage) return
  const sr = stage.getBoundingClientRect()
  const grab = (attr: string, out: Record<string, Anchor>) => {
    stage.querySelectorAll(`[${attr}]`).forEach(el => {
      const r = (el as HTMLElement).getBoundingClientRect()
      out[(el as HTMLElement).getAttribute(attr)!] = { x: r.left - sr.left, y: r.top - sr.top }
    })
  }
  grab('data-ghost-inline', inlineA)
  grab('data-ghost-cluster', clusterA)
  grab('data-ghost-dock', dockA)
  // 入槽缩小比：幽灵槽高 / 活体词元高
  const dockGhost = stage.querySelector('[data-ghost-dock]') as HTMLElement | null
  const liveTok = stage.querySelector('.tok') as HTMLElement | null
  if (dockGhost && liveTok && liveTok.offsetHeight > 0) {
    dockScale = Math.min(0.85, Math.max(0.2, dockGhost.offsetHeight / liveTok.offsetHeight))
  }
  console.warn("[measure]", JSON.stringify(dockA), "mobile=", document.querySelector(".intro-root")?.classList.contains("mobile"))
  measured = true
}

/* ─────────────────────── 编舞状态 ─────────────────────── */
const tokStyle = reactive<Record<string, Record<string, string>>>({})
const qualityStyle = reactive<Record<string, string>>({ opacity: '0' })
const barFrameStyle = reactive<Record<string, string>>({ opacity: '0' })
const underlineP = ref(0)
const qualityHintP = ref(0)
const forgeNoteP = ref(0)
const roleLabelStyle = reactive<Record<string, string>>({ opacity: '0' })
const focusedId = ref<string | null>(null)
const focusedRole = computed(() => words.find(w => w.id === focusedId.value)?.role ?? null)

/* 编织幕的分段（scrub 时间轴）：休整 → 拆解 → 驻留 → 入槽 → 收笔 */
const EX0 = 0.06      // 拆解起点
const EX_STAG = 0.055 // 每个词的拆解阶梯
const EX_DUR = 0.24   // 单词飞行时长
const DK0 = 0.60      // 入槽起点
const DK_STAG = 0.045
const DK_DUR = 0.20
/* 飞行弓形参数（px）：按目标方向分道——左上双词"欲扬先抑"下沉低道，
   右上双词"扶摇直上"高道，动作词贴地直落；三层航线永不相交 */
const ARCS = [
  { ex: 120, dk: -18 },  // 夕阳下（左上）下沉低道
  { ex: -130, dk: 14 },  // 蓝发（右上）高道
  { ex: -190, dk: 16 },  // 少女（右上）更高道，与蓝发错峰
  { ex: 170, dk: -20 },  // 在海边（左上）更低道，与夕阳下错层
  { ex: 40, dk: -12 },   // 微笑（正下）贴地微沉
]

function renderForge(p: number) {
  if (!measured) return
  for (let i = 0; i < words.length; i++) {
    const w = words[i]
    const a0 = inlineA[w.id] || { x: 0, y: 0 }
    const a1 = clusterA[w.id] || a0
    const a2 = dockA[w.id] || a1
    const dockIdx = dockOrder.findIndex(d => d.id === w.id)

    const tEx = easeInOutCubic(seg(p, EX0 + i * EX_STAG, EX0 + i * EX_STAG + EX_DUR))
    const tDk = easeOutBack(seg(p, DK0 + dockIdx * DK_STAG, DK0 + dockIdx * DK_STAG + DK_DUR))
    // 弧线飞行：每词带垂直于路径的弓形偏移，避免中途相撞（编舞而非直线搬运）
    const arc = Math.sin(Math.PI * tEx) * ARCS[i].ex + Math.sin(Math.PI * Math.min(1, tDk)) * ARCS[i].dk
    const x = lerp(lerp(a0.x, a1.x, tEx), a2.x, tDk)
    const y = lerp(lerp(a0.y, a1.y, tEx), a2.y, tDk) + arc

    const isFocused = focusedId.value === w.id
    // 入槽时从大衬线缩成槽内小字；悬停放大仅在拆解驻留期生效
    const base = lerp(1, dockScale, tDk)
    const scale = base * (isFocused && tEx > 0.9 && tDk === 0 ? 1.14 : 1)
    // 角色色随拆解进度上墨
    const color = `color-mix(in srgb, #16130E ${(1 - tEx) * 100}%, ${roles[w.role].color} ${tEx * 100}%)`
    tokStyle[w.id] = {
      transform: `translate3d(${x}px, ${y}px, 0) scale(${scale})`,
      color,
      opacity: focusedId.value && !isFocused ? '0.28' : '1',
      zIndex: isFocused ? '5' : '2',
    }
  }
  // 品质词（编译器补全）：入槽时直接落在槽位，带弹性
  const qa = dockA[qualityWord.id]
  if (qa) {
    const tQ = easeOutBack(seg(p, DK0, DK0 + DK_DUR))
    qualityStyle.transform = `translate3d(${qa.x}px, ${qa.y}px, 0) scale(${lerp(dockScale * 1.5, dockScale, tQ)})`
    qualityStyle.opacity = String(seg(p, DK0 - 0.02, DK0 + 0.06))
    qualityStyle.color = roles.quality.color
  }
  barFrameStyle.opacity = String(seg(p, 0.54, 0.62))
  roleLabelStyle.opacity = String(seg(p, 0.40, 0.52))
  underlineP.value = seg(p, 0.94, 1)
  qualityHintP.value = seg(p, 0.78, 0.86) * (1 - seg(p, 0.96, 1))
  forgeNoteP.value = seg(p, 0.9, 0.98)
}

/* ─────────────────────── 结晶幕 ─────────────────────── */
const crystalMatStyle = reactive<Record<string, string>>({})
const ingredientsP = ref(0)
const captionStyle = reactive<Record<string, string>>({ opacity: '0' })
const sealSlam = ref(false)
let heroImg: HTMLImageElement | null = null
let lastBlock = -1

function drawCrystal(p: number) {
  const cv = canvasEl.value
  if (!cv || !heroImg?.complete || !heroImg.naturalWidth) return
  const ctx = cv.getContext('2d')
  if (!ctx) return
  const e = easeInOutCubic(p)
  // 马赛克：64px 色块 → 原图（幂次让后段"定格式"清晰）
  const block = Math.max(1, Math.round(64 * Math.pow(1 - e, 2.4)))
  if (block === lastBlock) return
  lastBlock = block

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const W = cv.width / dpr
  const H = cv.height / dpr
  // cover 裁切
  const iw = heroImg.naturalWidth
  const ih = heroImg.naturalHeight
  const scale = Math.max(W / iw, H / ih)
  const sw = W / scale
  const sh = H / scale
  const sx = (iw - sw) / 2
  const sy = (ih - sh) / 2

  ctx.save()
  ctx.scale(dpr, dpr)
  ctx.imageSmoothingEnabled = false
  if (block <= 1) {
    ctx.imageSmoothingEnabled = true
    ctx.drawImage(heroImg, sx, sy, sw, sh, 0, 0, W, H)
  } else {
    const tw = Math.max(1, Math.ceil(W / block))
    const th = Math.max(1, Math.ceil(H / block))
    const off = document.createElement('canvas')
    off.width = tw
    off.height = th
    const octx = off.getContext('2d')!
    octx.drawImage(heroImg, sx, sy, sw, sh, 0, 0, tw, th)
    ctx.clearRect(0, 0, W, H)
    ctx.drawImage(off, 0, 0, tw, th, 0, 0, W, H)
  }
  ctx.restore()
}

function sizeCanvas() {
  const cv = canvasEl.value
  if (!cv) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const r = cv.getBoundingClientRect()
  cv.width = Math.max(1, Math.round(r.width * dpr))
  cv.height = Math.max(1, Math.round(r.height * dpr))
  lastBlock = -1
}

function renderCrystal(p: number) {
  drawCrystal(p)
  ingredientsP.value = 0.85 * (1 - seg(p, 0.55, 0.8))
  const cap = seg(p, 0.78, 0.92)
  captionStyle.opacity = String(cap)
  captionStyle.transform = `translate3d(0, ${lerp(14, 0, easeOutCubic(cap))}px, 0)`
  crystalMatStyle.transform = `scale(${lerp(1.045, 1, easeOutCubic(seg(p, 0, 0.5)))})`
  sealSlam.value = p >= 0.965
}

/* ─────────────────────── 墨线轨 ─────────────────────── */
const railLen = 420
const railProgress = ref(0)
const railMarks = [{ label: '序' }, { label: '词' }, { label: '画' }, { label: '邀' }]

/* ─────────────────────── 星火漂移（序） ─────────────────────── */
function renderSparks(t: number) {
  for (let i = 0; i < sparks.length; i++) {
    const s = sparks[i]
    s.dx = Math.sin(t / 2400 + i * 2.1) * (10 + i * 3)
    s.dy = Math.cos(t / 3100 + i * 1.4) * (8 + i * 2)
  }
}

/* ─────────────────────── 主循环 ─────────────────────── */
let choreo: ChoreoHandle | null = null
let resizeTimer: ReturnType<typeof setTimeout> | null = null
let lateMeasureTimer: ReturnType<typeof setTimeout> | null = null

function onFrame() {
  const vh = window.innerHeight
  if (forgeEl.value) renderForge(stickyProgress(forgeEl.value, vh))
  if (crystalEl.value) renderCrystal(stickyProgress(crystalEl.value, vh))
  renderSparks(performance.now())
  const doc = document.documentElement
  railProgress.value = clamp01(window.scrollY / Math.max(1, doc.scrollHeight - vh))
}

function renderFinalStates() {
  // reduced-motion：直接落到各幕终态，无过程动画
  typed.value = SEED
  typeDone.value = true
  renderForge(1)
  renderCrystal(1)
  sealSlam.value = true
  railProgress.value = 1
}

function remeasure() {
  sizeCanvas()
  measureGhosts()
  if (reduced.value) renderFinalStates()
}

onMounted(async () => {
  mqReduced = window.matchMedia('(prefers-reduced-motion: reduce)')
  mqMobile = window.matchMedia('(max-width: 767px)')
  reduced.value = mqReduced.matches
  isMobile.value = mqMobile.matches
  const onMq = async () => {
    reduced.value = mqReduced!.matches
    isMobile.value = mqMobile!.matches
    await nextTick()          // class 切换后布局变了，锚点必须重量
    remeasure()
    if (reduced.value) renderFinalStates()
  }
  mqReduced.addEventListener('change', onMq)
  mqMobile.addEventListener('change', onMq)

  heroImg = new Image()
  heroImg.src = CRYSTAL_SRC
  heroImg.onload = () => {
    lastBlock = -1
    if (reduced.value) drawCrystal(1)
  }

  sizeCanvas()
  await nextTick()            // 等 mobile/reduced class 上屏后再量锚点
  measureGhosts()
  // 衬线字体落地后重测锚点（词元位置依赖字宽）
  ;(document as any).fonts?.ready?.then(() => remeasure()).catch(() => {})
  // 防御早期样式竞态：双 rAF + 延迟各补一次（幂等便宜，choreo 逐帧读锚点自动修正）
  requestAnimationFrame(() => requestAnimationFrame(() => measureGhosts()))
  lateMeasureTimer = setTimeout(() => remeasure(), 600)

  if (reduced.value) {
    renderFinalStates()
  } else {
    replayType()
    choreo = startChoreo(onFrame)
  }

  const onResize = () => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(remeasure, 180)
  }
  window.addEventListener('resize', onResize)
  onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    mqReduced?.removeEventListener('change', onMq)
    mqMobile?.removeEventListener('change', onMq)
    choreo?.stop()
    if (typeTimer) clearTimeout(typeTimer)
    if (resizeTimer) clearTimeout(resizeTimer)
    if (lateMeasureTimer) clearTimeout(lateMeasureTimer)
  })
})
</script>

<style scoped>
/* ══════════════════════════════════════════════════════════════
   《一句话的旅程》— 纸 · 墨 · 朱
   独立于产品主题的自足视觉系统（.art piece，不随 app 换肤）
   ══════════════════════════════════════════════════════════════ */
.intro-root {
  --paper: #F6F1E8;
  --paper-deep: #EDE4D3;
  --ink: #16130E;
  --ink-soft: #4A4235;
  --ink-faint: rgba(22, 19, 14, 0.08);
  --ve: #C63F2A; /* 朱 */
  --serif: 'Songti SC', 'Noto Serif SC', 'Source Han Serif SC', 'STSong', 'SimSun', serif;
  --mono: 'Roboto Mono', 'JetBrains Mono', 'SF Mono', 'Cascadia Code', monospace;

  position: relative;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  min-height: 100vh;
  /* 注意：不可设 overflow-x —— 任何祖先 overflow 都会折断 sticky 舞台；
     防溢出由每个 act 自己 overflow:hidden 负责 */
}
.serif { font-family: var(--serif); }
.mono { font-family: var(--mono); }
.ve { color: var(--ve); font-style: normal; }

.paper-grain {
  position: fixed;
  inset: 0;
  z-index: 40;
  pointer-events: none;
  opacity: 0.55;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.05 0'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ── 印章 ── */
.seal {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  background: var(--ve);
  color: var(--paper);
  font-family: var(--serif);
  font-size: 26px;
  font-weight: 700;
  border-radius: 8px;
  box-shadow: 2px 3px 0 rgba(22, 19, 14, 0.22);
  user-select: none;
}

/* ── 墨线进度轨 ── */
.ink-rail {
  position: fixed;
  left: 30px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 30;
}
.rail-svg { height: 46vh; width: 40px; overflow: visible; }
.rail-line {
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
  fill: none;
  opacity: 0.85;
}
.rail-dot {
  fill: var(--paper);
  stroke: var(--ink);
  stroke-width: 1.5;
  transition: fill 240ms ease;
}
.rail-dot.on { fill: var(--ve); stroke: var(--ve); }
.rail-text {
  font-family: var(--serif);
  font-size: 11px;
  fill: var(--ink-soft);
}

/* ═══════════ 序 ═══════════ */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 8vh 8vw 12vh;
  overflow: hidden;
}
.hero-vertical {
  position: absolute;
  right: 4vw;
  top: 50%;
  transform: translateY(-50%);
  writing-mode: vertical-rl;
  font-family: var(--serif);
  font-size: clamp(90px, 14vw, 220px);
  font-weight: 700;
  letter-spacing: 0.08em;
  color: transparent;
  -webkit-text-stroke: 1px rgba(22, 19, 14, 0.1);
  user-select: none;
  pointer-events: none;
}
.hero-seal {
  position: absolute;
  top: 6vh;
  right: 6vw;
  transform: rotate(6deg);
}
.hero-inner { position: relative; max-width: 900px; z-index: 2; }
.kicker {
  font-size: 11px;
  letter-spacing: 0.32em;
  color: var(--ink-soft);
  margin: 0 0 4vh;
}
.hero-title {
  margin: 0;
  font-size: clamp(52px, 8.5vw, 124px);
  font-weight: 700;
  line-height: 1.12;
  letter-spacing: 0.01em;
}
.ht-line { display: block; }
.hero-title em { font-style: normal; color: var(--ve); }

.seed {
  margin: 6vh 0 0;
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}
.seed-tag {
  font-size: 10px;
  letter-spacing: 0.28em;
  color: var(--paper);
  background: var(--ink);
  padding: 5px 10px 4px;
  border-radius: 4px;
}
.seed-text {
  border: 0;
  background: transparent;
  padding: 0 0 4px;
  font-size: clamp(19px, 2.4vw, 28px);
  color: var(--ink);
  border-bottom: 2px solid var(--ink-faint);
  cursor: pointer;
  text-align: left;
}
.seed-text:hover { border-bottom-color: var(--ve); }
.cursor {
  display: inline-block;
  width: 3px;
  height: 1.05em;
  margin-left: 3px;
  background: var(--ve);
  vertical-align: -0.15em;
}
.cursor.blink { animation: cur-blink 1.1s steps(2) infinite; }
@keyframes cur-blink { 50% { opacity: 0; } }

.hero-hint {
  position: absolute;
  left: 0;
  bottom: -9vh;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ink-soft);
  font-size: 13px;
}
.hint-stroke {
  width: 44px;
  height: 2px;
  background: var(--ink);
  transform-origin: left;
  animation: hint-draw 2.2s cubic-bezier(0.2, 0, 0, 1) infinite;
}
@keyframes hint-draw {
  0% { transform: scaleX(0); }
  45% { transform: scaleX(1); }
  100% { transform: scaleX(1); opacity: 0.2; }
}

.spark {
  position: absolute;
  z-index: 1;
  width: clamp(120px, 15vw, 210px);
  margin: 0;
  padding: 10px 10px 8px;
  background: #FFFDF8;
  border: 1px solid var(--ink-faint);
  box-shadow: 0 14px 34px rgba(22, 19, 14, 0.14);
  will-change: transform;
}
.spark img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; }
.spark figcaption {
  margin-top: 7px;
  font-size: 10.5px;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
  text-align: center;
}
.spark-0 { right: 22vw; top: 12vh; }
.spark-1 { right: 8vw; top: 34vh; }
.spark-2 { right: 20vw; bottom: 8vh; }

/* ═══════════ 壹 · 拆解与编织 ═══════════ */
.forge { height: 320vh; }
.forge-stage {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
}
.act-title {
  position: absolute;
  top: 7vh;
  left: 8vw;
  margin: 0;
  font-size: clamp(26px, 3.4vw, 44px);
  font-weight: 700;
  z-index: 3;
}
.act-no {
  display: inline-block;
  margin-right: 14px;
  font-size: 0.5em;
  color: var(--ve);
  border: 1.5px solid var(--ve);
  border-radius: 6px;
  padding: 0.18em 0.42em;
  vertical-align: 0.28em;
}

/* 幽灵布局：不可见但占位（测量锚点用） */
.ghost { visibility: hidden; position: absolute; }
.tok-ghost { display: inline-block; padding: 8px 6px; white-space: nowrap; }
.ghost-inline {
  left: 50%;
  top: 44%;
  transform: translate(-50%, -50%);
  font-size: clamp(24px, 3.6vw, 46px);
}
.ghost-cluster {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  font-size: clamp(22px, 3vw, 38px);
}
.cluster-scene { left: 9%; top: 24%; }
.cluster-character { right: 9%; top: 24%; }
.cluster-action { left: 50%; bottom: 16%; transform: translateX(-50%); }
.ghost-bar {
  left: 50%;
  top: 58%;
  transform: translate(-50%, -50%);
  display: flex;
  font-size: clamp(14px, 1.5vw, 19px);
}
.dock-ghost { padding: 12px 14px; margin-right: 14px; }
.dock-ghost:last-child { margin-right: 0; }

/* 活体词元 */
.tok {
  position: absolute;
  left: 0;
  top: 0;
  transform-origin: 0 0;
  padding: 8px 6px;
  white-space: nowrap;
  font-size: clamp(24px, 3.6vw, 46px);
  font-weight: 700;
  will-change: transform, opacity;
  cursor: default;
  transition: opacity 200ms ease;
}
.tok:focus-visible { outline: 2px solid var(--ve); outline-offset: 4px; border-radius: 4px; }
.tok-quality { color: var(--ve); z-index: 2; }

.role-label {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  letter-spacing: 0.3em;
  color: var(--ink-soft);
  z-index: 3;
  transition: color 180ms ease;
}
.role-label.cluster-scene { left: 9%; top: 20%; }
.role-label.cluster-character { right: 9%; top: 20%; }
.role-label.cluster-action { left: 50%; bottom: 12%; transform: translateX(-50%); }
.role-label.flash { color: var(--ink); font-weight: 700; }
.role-swatch { width: 10px; height: 10px; border-radius: 2px; }

.bar-frame {
  position: absolute;
  left: 50%;
  top: 58%;
  transform: translate(-50%, -50%);
  width: min(76vw, 720px);
  height: 92px;
  border: 1.5px solid var(--ink-faint);
  border-radius: 14px;
  background: rgba(255, 253, 248, 0.55);
  z-index: 1;
}
.bar-label {
  position: absolute;
  left: 16px;
  top: -9px;
  padding: 0 8px;
  background: var(--paper);
  font-size: 10px;
  letter-spacing: 0.24em;
  color: var(--ink-soft);
}
.bar-underline {
  position: absolute;
  left: 5%;
  bottom: 10px;
  width: 90%;
  height: 10px;
}
.bar-underline path {
  stroke: var(--ve);
  stroke-width: 3;
  fill: none;
  stroke-linecap: round;
}
.bar-quality-hint {
  position: absolute;
  right: 14px;
  top: -9px;
  background: var(--paper);
  padding: 0 8px;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--ve);
}
.forge-note {
  position: absolute;
  left: 50%;
  bottom: 7vh;
  transform: translateX(-50%);
  margin: 0;
  font-size: clamp(16px, 1.8vw, 22px);
  color: var(--ink-soft);
  white-space: nowrap;
}

/* ═══════════ 贰 · 结晶 ═══════════ */
.crystal { height: 260vh; }
.crystal-stage {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.crystal .act-title { left: 8vw; }
.crystal-mat {
  position: relative;
  margin-top: 5vh;
  padding: clamp(10px, 1.6vw, 20px);
  background: #FFFDF8;
  border: 1px solid var(--ink);
  box-shadow: 0 24px 60px rgba(22, 19, 14, 0.18);
  will-change: transform;
}
.crystal-canvas {
  display: block;
  width: min(62vw, 54vh);
  aspect-ratio: 1;
  background: var(--paper-deep);
}
.crystal-seal {
  position: absolute;
  right: -16px;
  bottom: -16px;
  transform: rotate(-8deg) scale(1.6);
  opacity: 0;
}
.crystal-seal.slam {
  animation: seal-slam 420ms cubic-bezier(0.2, 2.1, 0.35, 1) forwards;
}
@keyframes seal-slam {
  from { transform: rotate(-8deg) scale(1.6); opacity: 0; }
  60% { transform: rotate(-8deg) scale(0.94); opacity: 1; }
  to { transform: rotate(-8deg) scale(1); opacity: 1; }
}
.crystal-ingredients {
  margin-top: 3.5vh;
  font-size: 11.5px;
  letter-spacing: 0.18em;
  color: var(--ink-soft);
}
.crystal-caption {
  margin: 3vh 0 0;
  font-size: clamp(22px, 3vw, 38px);
  font-weight: 700;
  text-align: center;
  line-height: 1.5;
  will-change: transform, opacity;
}

/* ═══════════ 邀 ═══════════ */
.invite {
  min-height: 96vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 10vh 6vw;
  background:
    radial-gradient(120% 90% at 50% 110%, rgba(198, 63, 42, 0.07), transparent 60%),
    var(--paper);
}
.invite-title {
  margin: 0 0 6vh;
  font-size: clamp(46px, 7.5vw, 108px);
  font-weight: 700;
  line-height: 1.18;
}
.invite-actions {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
  justify-content: center;
}
.cta {
  border: 2px solid var(--ink);
  border-radius: 999px;
  padding: 16px 38px;
  background: var(--ve);
  color: var(--paper);
  font-size: 14px;
  letter-spacing: 0.22em;
  cursor: pointer;
  box-shadow: 3px 4px 0 var(--ink);
  transition: transform 180ms cubic-bezier(0.2, 0.85, 0.25, 1.08),
    box-shadow 180ms cubic-bezier(0.2, 0.85, 0.25, 1.08);
}
.cta:hover {
  transform: translate(-1px, -2px);
  box-shadow: 5px 7px 0 var(--ink);
}
.cta:active {
  transform: translate(2px, 3px);
  box-shadow: 1px 1px 0 var(--ink);
}
.cta-ghost {
  border: 0;
  background: transparent;
  padding: 12px 4px;
  font-size: 17px;
  color: var(--ink);
  border-bottom: 1.5px solid var(--ink-faint);
  cursor: pointer;
  transition: border-color 160ms ease, color 160ms ease;
}
.cta-ghost:hover { color: var(--ve); border-bottom-color: var(--ve); }
.cta:focus-visible, .cta-ghost:focus-visible {
  outline: 2px solid var(--ve);
  outline-offset: 4px;
}
.foot {
  margin-top: 9vh;
  font-size: 10.5px;
  letter-spacing: 0.22em;
  color: var(--ink-soft);
}

/* ═══════════ 移动端 ═══════════ */
.mobile .hero { padding: 10vh 7vw 14vh; }
.mobile .hero-vertical { font-size: 74px; right: 2vw; }
.mobile .hero-seal { width: 42px; height: 42px; font-size: 20px; top: 4vh; right: 5vw; }
.mobile .spark { position: static; display: inline-block; width: 27vw; margin: 4vh 2.5vw 0 0; }
.mobile .spark-0, .mobile .spark-1, .mobile .spark-2 { position: static; }
.mobile .forge { height: 260vh; }
.mobile .act-title { left: 6vw; }
.mobile .cluster-scene { left: 6%; top: 20%; }
.mobile .cluster-character { right: 6%; top: 20%; }
.mobile .cluster-action { bottom: 24%; }
.mobile .role-label.cluster-scene { left: 6%; top: 16.5%; }
.mobile .role-label.cluster-character { right: 6%; top: 16.5%; }
.mobile .role-label.cluster-action { bottom: 20.5%; }
.mobile .ghost-bar { top: 62%; width: 86vw; flex-wrap: wrap; justify-content: center; font-size: 12px; }
.mobile .ghost-bar .dock-ghost { margin-right: 8px; padding: 8px 9px; }
.mobile .bar-frame { top: 62%; width: 86vw; height: 108px; }
.mobile .crystal-canvas { width: 78vw; }

/* ═══════════ reduced motion：终态直出 ═══════════ */
.reduced .hint-stroke,
.reduced .cursor.blink { animation: none; }
.reduced .crystal-seal { opacity: 1; transform: rotate(-8deg) scale(1); }
</style>
