# UI 规格 — Material 3 Expressive（现行设计系统）

> 本文件描述**当前已实施**的 UI 设计系统，不是目标清单。
> 评价标尺：Google M3 Expressive 采用度量（component / motion / color / shape / typography，
> 见 `m3.material.io/blog/building-with-m3-expressive`），不以"用了 M3 色板和圆角"为验收。

---

## 1. 视觉目标

项目是专业创作工具，不是 AI 营销网站。

目标：

- Material 3 **Expressive**（不是教科书默认 M3 模板感）
- 中文
- 桌面优先（1440/1920），可用响应式
- 信息密度中等偏高
- 高频操作路径短
- 有明确的视觉身份（主题族），但每个页面不各自为政

避免：

- AI 科技风渐变滥用、霓虹滥用（霓虹只允许出现在 MAX reasoning 局部）
- 玻璃拟态
- wireframe 感重描边盒子
- 每一 section 都套 Card
- 无意义动效（opacity + translateY 批量 reveal 不是我们的主要动画语言）

---

## 2. 框系统（Box System）——三条死规则

全站统一的层级语义，新页面必须遵守，不再混搭：

| 元素 | 样式 | 语义 |
|---|---|---|
| **功能面板**（toolbar / 分组容器） | tonal 填充 `surface-container`，**无描边**（全局类 `.if-panel`） | "这是工具/分组" |
| **数据卡片**（一条记录） | `surface` 白底 + 1px `outline-variant` hairline | "这是一条数据" |
| **输入控件** | `surface` 白底 + hairline，focus 变 primary | 永远白底细线 |
| 卡片内嵌内容区 | `surface-container-low`（比卡面深/浅半度） | inset 区域 |

记忆法：**紫在外 = 面板，白在外 = 数据卡**。

关键事实：

- Vuetify outlined 控件默认描边是 on-surface 实色（wireframe 感根源），
  已在 `style.css` 全局降为 `outline-variant` hairline + 统一 16px 圆角。
- 空状态统一 `.if-empty` tonal 占位面板，不再各自写描边盒子。
- hover：数据卡片边框变 primary + 柔和投影；禁止再用偏色 `#4F46E5`。

---

## 3. Radius tokens

`style.css :root`：

- `--if-radius-field: 16px`（输入控件）
- `--if-radius-container: 24px`（面板 / filter bar）
- `--if-radius-card: 20px`（页面卡片）
- `--if-radius-dialog: 24px`（弹窗）
- `--if-radius-button: 12px`
- `--if-radius-pill: 999px`（chip / status / CTA）

Gemini 主题族下 `--if-radius-field` 提升到 22px（药丸几何）。

---

## 4. Motion 系统

### 4.1 统一 tokens（自定义容器禁止各自发明 cubic-bezier）

- `--if-motion-fast-effects: 110ms`（颜色/透明度）
- `--if-motion-fast-spatial: 180ms spring`
- `--if-motion-default-effects: 160ms`
- `--if-motion-default-spatial: 260ms spring`
- `--if-motion-slow-effects: 240ms`

### 4.2 全站动效层（已实现）

- 路由页过渡：fade + 10px 上浮，out-in 不叠页
- 卡片/行入场：`.if-enter` rise + `--i` 索引阶梯延迟（封顶 14 项）
- 折叠面板：`grid 0fr→1fr` 平滑展开，不用固定高度
- 画布出图：scale(0.985)→1 + fade 落定，按图片 URL keyed

### 4.3 原则

- 动效是编舞，不是元素出现方式：章节之间要有状态延续或视觉因果
- 生成进度用**真实数据**驱动（见 §8），绝不伪造百分比
- `prefers-reduced-motion` 时全站动效关闭（`.if-*` 与路由过渡已接 m3e 组件内部机制）

---

## 5. 主题族（Theme Families）

侧栏底部 swatch 切换，`localStorage` 持久化（`if-theme-family` / `if-theme-mode`）：

| 族 | 亮色 | 暗色 |
|---|---|---|
| **ImageForge 紫**（默认） | M3 violet 系 tonal surface | 同族暗色 |
| **Gemini**（Neural Expressive 方向） | `#F0F4F8` 灰白底 + Google Blue `#0B57D0` 克制强调 | 浓郁近黑 `#131314` + 浅蓝 `#A8C7FA` |
| **Antigravity Mono** | 纯白底 + 中性灰 + `#121317` 近黑 CTA | `#121317` 木烟黑 + 白色 CTA，无彩色 hue |

实现约束：

- 一切颜色走 `--v-theme-*` 变量，新增主题只加 token 不改组件
- `@m3e/web` 组件颜色经 `--m3e-* ↔ --v-theme-*` 桥接对齐（style.css）

---

## 6. @m3e/web 组件采用（R1 已落地）

第三方 M3E Web Component 实现（`matraic/m3e`，**非 Google 官方库**）。

接入纪律：

- 模块化 import（`src/plugins/m3e.ts`），**禁止** `@m3e/web/all`（tree shaking）
- Vite：`m3e-*` 注册为 Vue custom elements
- `m3e-icon` 不引入（在线字体违背 local-first）；icon slot 用本地 @mdi/font
- 停止用普通 HTML + 手写 CSS 模仿 M3E 原生控件

R1 已替换（Studio）：

| 位置 | 组件 |
|---|---|
| 全局导航 | `m3e-nav-rail`（compact 80px，8 项目 + selected indicator） |
| Safety 四档 | `m3e-segmented-button` |
| Seed 随机/固定 | `m3e-segmented-button` |
| 复用上次 seed | `m3e-button`（tonal） |
| LoRA 启用 | `m3e-switch` |
| LoRA 权重 | `m3e-slider`（0~1.5 / step 0.05） |
| Reasoning 档位 | `m3e-slider`（LM 5 档 / Cloud 6 档；MAX 霓虹限 slider 局部） |
| 短等待（解析等） | `m3e-loading-indicator`（保留 shape morph） |
| 生成真实进度 | `m3e-circular-progress-indicator variant="wavy"` |

R2 暂不替换（下轮再定）：

- Dialog、Prompt editor、Facts board、Artist / Rules dialog
- History 页、LoRA 资源库页

---

## 7. 主框架与创作台布局

```text
┌────────┬────────────┬──────────────────┬────────────────┐
│ nav    │ Context    │ The Forge        │ Canvas         │
│ rail   │ Rail       │ (工坊流水线)      │ (画布)          │
│ 80px   │ 272px      │ 500–680px        │ 弹性剩余         │
│        │            │                  │                │
│ 创作台 │ Safety     │ 01 画面描述+解析   │ ComfyUI 状态    │
│ 角色书 │ 规则集      │ 02 Facts Pipeline │ 画布/HUD       │
│ 画师库 │ 画师       │ 03 Final Prompt  │ 进度(wavy)      │
│ LoRA  │ LoRA shelf │                  │ 生成 CTA + Seed │
│ 规则   │ 登场角色    │                  │ Filmstrip      │
│ 预设   │            │                  │                │
│ 历史   │            │                  │                │
│ 设置   │            │                  │                │
└────────┴────────────┴──────────────────┴────────────────┘
```

事实：

- `m3e-nav-rail` compact 80px（库默认 96px，用 `--m3e-nav-rail-compact-width` 收敛）
- `.v-application__wrap` 需显式 `flex-direction: row` + `v-main { min-width: 0 }`
- Context Rail 可折叠为 56px 图标轨
- 旧版 3600 行单文件创作台保留在 `/legacy-studio` 供回归比对

---

## 8. 状态与进度表达

### 进度（生成）

- **主进度 = `m3e-circular-progress-indicator variant="wavy"`**：
  真实 ComfyUI WS step（`generationProgressValue/Max`），中央 % + 下方 "8 / 12 steps 采样计算中"
- 提交完成但 WS step 未到（preparing / queued）：
  `m3e-loading-indicator`，**不伪造百分比**
- WS progress 到达后自然 transition 到 determinate wavy
- 不再使用线性矩形进度条（避免圆环+线条抢视觉）

### 短等待

Prompt parsing / character online resolve / workflow preparing / metadata waiting：
统一 `m3e-loading-indicator`（soft-burst → cookie → pentagon → pill → sunny 的 shape morph），
不再用普通 spinner。

### 服务状态

LM Studio / ComfyUI：pill + 状态点 + 文字（已连接 / 未连接 / 异常），
状态不靠颜色小点猜。

---

## 9. 页面级指引

### 画师库

- tonal filter bar（`.if-panel`）+ 搜索 + 分类 tonal chips + 收藏
- 数据卡片网格（白底 hairline）；无预览图时内嵌 `surface-container-low` 占位
- 用户自定义与内置画师同一视觉体系

### 角色书

- 已解析 / 自定义 双 tab segmented
- tonal toolbar + 白底 hairline 行卡
- 编辑按 基础 / 头部 / 身材 / 服装 / 其他 分组折叠，空字段允许

### LoRA 资源库

- Card / List 双视图（localStorage 记忆）；Card 有封面、List 无封面
- Civitai 元数据（V1）：远端 trigger 本地空时以 "Civitai ·" 轻标记 fallback 展示；
  推荐权重与本地权重并列展示但绝不自动覆盖
- 本地文件失效：明确 warning（`local_file_not_found` / `local_file_ambiguous`），不静默

### 规则文件

- 数据卡片（白底 hairline）+ 内嵌 container-low 内容预览盒
- markdown 源码预览是已知粗糙点（R2+ 候选：渲染或摘要）

### 历史

- 图片卡片网格（白底 hairline），内嵌 container-low prompt 摘录
- 恢复到创作台（完整参数回填）

---

## 10. 体验页 `/intro`

《一句话的旅程》——独立艺术指导的沉浸式滚动编舞（纸·墨·朱 + 衬线 + 打字机 +
词元分道飞行 + canvas 马赛克结晶）。它是**自足视觉系统**，不随 app 主题族换肤；
plain 路由（无 nav rail）。其动效原则（编舞、状态延续、真实数据）与主站一致。

---

## 11. 完整成品交互参考

用户输入：

> 穗穗穿着泳装，秧秧穿蓝色海军水手服，穗穗在沙滩上追秧秧。

点击 **语义抽取**（按钮内 loading indicator shape morph）。

Facts Pipeline 展示实体与关系（模型角色 / 角色书来源标注），每条可修改。

Final Prompt 编译出英文内容；用户再选 Artist / LoRA（switch + slider）。

右侧 ComfyUI 已连接 → 点击 **生成图片**：
排队（loading indicator）→ 采样中（wavy circular 真实 8/12 steps）→ 图片落版到画布。

这是当前已达到的完整闭环。
