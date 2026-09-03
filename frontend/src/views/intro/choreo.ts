/**
 * 《一句话的旅程》choreo engine — hand-rolled, dependency-free.
 *
 * 设计原则：
 * - 一个 rAF 循环驱动全站编舞；滚动值经 lerp 平滑（画面的"重量感"来源）；
 * - 每个 act 自己把 (section rect, viewport) 换算成 0..1 的 scrub 进度；
 * - 只写 transform / opacity / CSS var；canvas 重绘按值变化门控；
 * - 页面不可见时暂停；prefers-reduced-motion 时只渲染终态。
 */

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t

/** 子区间进度：p 在 [a, b] 内映射到 0..1 */
export const seg = (p: number, a: number, b: number) => clamp01((p - a) / (b - a))

export const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)
/** 入槽带回弹（编织幕的"磁吸"手感） */
export const easeOutBack = (t: number) => {
  const c1 = 1.35
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

/** section 的 sticky 编舞进度：0 = section 顶到视口顶，1 = 走完 (height - vh) */
export function stickyProgress(el: HTMLElement, vh: number): number {
  const r = el.getBoundingClientRect()
  const total = el.offsetHeight - vh
  if (total <= 0) return 1
  return clamp01(-r.top / total)
}

export interface ChoreoHandle {
  stop: () => void
  /** 强制立刻对齐到真实滚动位置（reduced-motion / 首帧用） */
  snap: () => void
}

/**
 * 启动编舞循环。onFrame(smoothedScrollY, rawScrollY) 每帧调用。
 * smooth 追赶 raw 的系数决定全站"惯性"——0.16 有重量但不拖泥。
 */
export function startChoreo(onFrame: (sy: number, raw: number) => void): ChoreoHandle {
  let raf = 0
  let running = false
  let smooth = window.scrollY
  let first = true

  const frame = () => {
    if (!running) return
    const raw = window.scrollY
    smooth = lerp(smooth, raw, first ? 1 : 0.16)
    first = false
    onFrame(smooth, raw)
    raf = requestAnimationFrame(frame)
  }
  const start = () => {
    if (running) return
    running = true
    raf = requestAnimationFrame(frame)
  }
  const stop = () => {
    running = false
    cancelAnimationFrame(raf)
  }
  const onVis = () => (document.hidden ? stop() : start())
  document.addEventListener('visibilitychange', onVis)
  start()

  return {
    stop: () => {
      stop()
      document.removeEventListener('visibilitychange', onVis)
    },
    snap: () => {
      smooth = window.scrollY
      first = true
    },
  }
}
