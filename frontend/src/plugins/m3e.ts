/**
 * @m3e/web 模块注册（R1）
 *
 * 只 import 用到的组件模块，保证 tree shaking——绝不 import '@m3e/web/all'。
 * 每个模块自带 shadow-DOM 样式与 M3 baseline token 默认值；
 * 与 ImageForge 主题的对齐通过 style.css 的 --m3e-* 桥接完成。
 *
 * 图标：m3e-icon 依赖在线 Material Symbols 字体，与 local-first 相悖；
 * nav item 的 icon slot 直接放本地 @mdi/font 图标，不引入 m3e-icon。
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
