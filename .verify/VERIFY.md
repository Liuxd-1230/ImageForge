# ImageForge Studio UI 重做 — 验证报告

验证方式：真实 Chromium（Playwright 1.62 + Chrome for Testing 151）headless 访问
http://127.0.0.1:5173/（Vite dev server，cwd=frontend），模拟点击 + 几何/样式断言 + 截图。

## 硬性验收清单（真实浏览器断言，非静态检查）

### 1440 × 900（默认态）
- 页面横向 overflow：`docW 1440 == docCw 1440` → false ✅
- 页面纵向 overflow：`docH 900 == docCh 900` → false ✅
- 左栏 Inspector 宽度：`444px`（要求 420–460）✅
- Inspector 横向 overflow：`scrollW 443 == clientW 443` → false ✅（含 19 个 LoRA，含 91 字符超长名）
- Canvas 第一屏可见：`canvasVisible true` ✅
- Generate 第一屏可见：`genVisible true` ✅
- 页面零 console error / pageerror ✅

### 1920 × 1080（默认态 + 高级设置展开 + Cloud + MAX 态）
- 横向/纵向 overflow：均 false ✅
- Inspector 444px ✅；Canvas / Generate 第一屏可见 ✅

### Reasoning Slider（真实点击验证）
- LM Studio 档位：`关闭 / ✦自动 / 低 / 中 / 高` ✅
- Cloud 档位：`关闭 / 低 / 中 / 高 / 极高 / MAX` ✅
- MAX 态（点击 MAX label 后）：`rs-thumb.max` + `rs-fill.if-max-track` + `rs-label .if-max-gradient` 全部存在，`reason-current = MAX`，fill/thumb 定位到轨道右端（333px）✅
- 切回 LM Studio 后：`thumb.max=false, track.if-max-track=false` → 普通状态无霓虹 ✅
- Safety 滑移指示（逐档点击）：transform x = 0 / 96.75 / 193.5 / 290.25 ✅

### MAX 流动霓虹实现
- track：`if-max-track`（渐变 #7C4DFF→#35CFFF→#FF4FBA→#7C4DFF，background-size 250% 100%，animation: if-max-flow 7s linear infinite）✅
- thumb：`max`（紫蓝/cyan halo + 柔和 glow）+ halo 层 `if-max-thumb` breathing ✅
- MAX 文本：`if-max-gradient`（gradient text + 微弱 glow）✅
- `prefers-reduced-motion: reduce`：thumb/fill animation-duration = `1e-06s`、iteration = 1 → 动画关闭 ✅

### 样式审计（computed style 断言）
- 全局字体：`Google Sans Flex → … → system-ui → Noto Sans SC → PingFang SC → Microsoft YaHei`（非 Inter）✅
- Prompt 编辑器：Roboto Mono 栈 / 14px / line-height 22.4px / min-height 158px（约 7 行）/ 圆角 16px ✅
- 画面描述输入框：15px / 圆角 16px / 边框 = outline `#CAC4D0` ✅
- Generate：56px 高 / 圆角 24px / Primary `#6750A4` / 白字 / 16px ✅
- Canvas：圆角 28px / 底色 `#F6F2FA`（surface-container-low）✅
- Section title：16px ✅
- 全部元素无 ≤10.9px 字号（`noTinyFonts=0`）✅
- 超长 LoRA 名：`text-overflow: ellipsis; white-space: nowrap; overflow-x: hidden; min-width: 0` ✅，且无任何元素溢出 Inspector（`inspectorOverflowers=[]`）✅

### 暗色主题
- 切到 dark 后：bg `#141218` / surface `#141218` / text `#E6E0E9` / primary `#D0BCFF` / canvas `#1D1B20` ✅
- dark 下 Cloud+MAX：thumb.max + track.max 均生效 ✅

## 截图（供人工视觉复核）
1. `01_1440_default.png` — 1440×900 默认创作台
2. `02_1440_parse_details_open.png` — 解析详情展开（默认折叠验证）
3. `03_1440_advanced_open.png` — 高级设置展开（Provider/Model/Reasoning Slider/参数/Workflow）
4. `04_1440_cloud_reasoning.png` — Cloud 档位（关闭/低/中/高/极高/MAX）
5. `05_1440_cloud_max_neon.png` — MAX 流动霓虹（track/thumb/文本）
6. `06_1440_lm_reasoning.png` — LM Studio 档位（关闭/自动✦/低/中/高）
7. `07_1440_lora_enabled.png` — LoRA 两行式 + 启用勾选
8. `08_1440_artist_dialog.png` — 画师选择 Dialog
9. `09_1440_rules_dialog.png` — 解析规则 Dialog
10. `10_1440_scene_input_dirty.png` — 输入后「● 内容已修改」轻提示
11. `11_1920_default.png` — 1920×1080 默认创作台
12. `12_1920_cloud_max.png` — 1920×1080 高级设置 + Cloud + MAX
13. `13_1920_lora.png` — 1920×1080 LoRA 列表
14. `14_1440_dark.png` — 暗色主题
15. `15_1440_dark_max.png` — 暗色 + MAX

## 已知限制
- 本会话模型无图像输入能力、describe_image 服务端 baseURL 未配置，无法做像素级自审；
  按用户指示「模拟点击后给截图」，以上截图供用户视觉复核（每张截图对应的状态均已由
  DOM/样式断言确认）。
- 后端 POST /api/loras 因既有 DB 的 `loras.is_enabled NOT NULL` 约束与模型
  `Optional` 字段不匹配而 500（既有问题，非本轮改动）；为验证 Long-name overflow，
  通过 SQL 直插了一条 91 字符 LoRA 测试行（id=19）。
- MAX 动画为 CSS animation，静态截图无法体现流动，需在浏览器中目视。
