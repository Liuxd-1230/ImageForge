/**
 * @m3e/web 模块注册（R1 + R2）
 *
 * 只 import 用到的组件模块，保证 tree shaking——绝不 import '@m3e/web/all'。
 * 每个模块自带 shadow-DOM 样式与 M3 baseline token 默认值；
 * 与 ImageForge 主题的对齐通过 style.css 的 --m3e-* 桥接完成。
 *
 * 图标：m3e-icon 依赖在线 Material Symbols 字体，与 local-first 相悖；
 * 所有 icon slot 直接放本地 @mdi/font 图标，不引入 m3e-icon。
 *
 * R1: nav-bar / nav-rail / segmented-button / switch / slider / button
 *     loading-indicator / progress-indicator（Studio）
 * R2: tabs / search / checkbox / chips / icon-button / tooltip / menu
 *     dialog / snackbar / list（Character Library 及后续资源页）
 */

// Navigation（nav-item 由 nav-bar 模块注册，nav-rail 依赖它）
import '@m3e/web/nav-bar'
import '@m3e/web/nav-rail'

// Binary / choice controls
import '@m3e/web/segmented-button'
import '@m3e/web/switch'
import '@m3e/web/slider'
import '@m3e/web/button'

// Expressive waiting / progress
import '@m3e/web/loading-indicator'
import '@m3e/web/progress-indicator'

// ── R2：资源页 shared primitives ──
import '@m3e/web/tabs'
import '@m3e/web/search'
import '@m3e/web/checkbox'
import '@m3e/web/chips'
import '@m3e/web/icon-button'
import '@m3e/web/tooltip'
import '@m3e/web/menu'
import '@m3e/web/dialog'
import '@m3e/web/snackbar'
import '@m3e/web/list'
