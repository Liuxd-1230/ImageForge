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

---

# 第二轮：真实用户工作流审计修复（ec8c927 之后）

## 后端（24/24 自动化 API 测试通过，`.verify/backend_test.py`）

- **旧 DB 迁移**：启动时自动把 `loras.is_enabled` 从 NOT NULL 重建为 nullable（12 步
  SQLite 迁移）+ 新增 `loras.source_path` 列；`POST /api/loras` 在旧库不再 500。
- **来源管理**：新增 `lora_sources` 表（display_path/resolved_path/enabled/recursive/created_at）；
  `POST/GET/PUT/DELETE /api/loras/sources`；路径校验（存在/目录/可读/去重，409 重复）。
- **WSL 路径转译**：`D:\...` / `D:/...` → `/mnt/d/...`（仅 WSL 环境），native 路径不变；
  resolved 用 realpath/normpath 去重。
- **两阶段扫描**：`POST /api/loras/sources/{id}/scan` 只返回候选预览（不改库）；
  字段：relative_path/full_path/name_hint/exists_in_db/comfy_recognized/comfy_name/basename_conflict；
  摘要含 发现/新增/已存在/ComfyUI未识别/重名/ComfyUI离线。
  存在判定：精确文件标识 + 有 source_path 的记录按真实路径匹配；仅旧记录回退 basename
  （修复「同名不同文件被误判已存在」）。
- **选择导入**：`POST /api/loras/import` 幂等（重复导入跳过）；记录 `source_path`；
  ComfyUI 未识别文件 is_valid_file=False（显示「文件存在 · ComfyUI 未识别」）。
- **sync-comfyui 行为取消**：只更新既有记录 is_valid_file，不再自动导入全部。
- **图片持久化**：`POST /api/comfyui/persist-image` 从 ComfyUI 下载到
  `ImageForge/data/generated/anima_<ts>_<rand>.png`；`GET /api/comfyui/generated/{file}` 服务
  （basename 白名单防穿越，实测 traversal→404）。history 记录改为引用本地文件，
  ComfyUI 原始 URL 保留在 comfy_params_json.comfy_image_url。
- **settings**：`GENERATE_TIMEOUT_SECONDS`（默认 300）进入可编辑配置，GET 正确返回 int。

## 前端（Playwright 全流程验证 `.verify/r2/verify2.cjs`，全部 PASS）

- **LoRA 库**：1280/1440/1920 页面与列表均无横向 overflow；长名/路径/触发词 ellipsis；
  M3 tonal 搜索栏（外层 24 / 内嵌 16 / padding 8）；「仅看收藏」正常尺寸 tonal 按钮；
  来源管理 Dialog（路径预览 / 启用 / 递归 / 删除不删库记录）+ 扫描预览 Dialog
  （摘要计数 / 全选新增 / 单选 / ComfyUI 未识别与重名标记 / 导入所选）。
- **Studio 尺寸**：自由数字输入（不再固定 select）；推荐 812×1216/1152×1536/1536×1536
  仅快捷键；交换宽高；锁定比例（默认关，改宽自动算高）；100×9000 显示「尺寸异常」warning
  不静默修正。
- **Prompt**：占位符改为「描述你想生成的画面…」，默认空；空输入时「解析」disabled。
- **角色书**：新建角色 gender/age_group/body 默认空字符串（不再预填 woman/young adult/petite）。
- **Reasoning**：Store 默认 `off`，`instruct` 全部归一化为 `off`；Provider 切换记忆各自
  model+reasoning（Cloud MAX → LM → 回 Cloud 恢复 MAX，实测通过）。
- **Rules**：只显示 is_enabled=true 的规则（实测禁用规则不出现在 Dialog）。
- **生成体验**：去掉假百分比（30+attempts*2 删除），改为阶段文案（准备工作流 →
  已提交 · ComfyUI 生成中…）+ indeterminate 扫光进度；超时可配（Settings 字段）；
  超时文案明确「前端停止等待≠任务已取消」。
- **草稿恢复**：localStorage `imageforge_studio_draft_v1`（schema v1），关键状态
  debounce 500ms 保存；刷新后横幅「已恢复上次未完成的创作」+ 清空创作台；
  脏/旧草稿安全忽略（类型守卫 + try/catch）。

## 截图（`.verify/r2/`，供人工视觉复核）
`01_lora_library.png` `02_studio_advanced.png` `03_draft_restored.png`
`04_character_new.png` `05_studio_1920.png` `06_source_dialog.png`
`07_scan_preview.png` `08_scan_selected.png` `09_library_search.png`

## 未做（用户明确不要求本轮扩复杂度）
- 未接 ComfyUI 真实 queue/progress/cancel（按要求用阶段+indeterminate）。
- 未重做 Prompt Engine；Settings/Character 页仍未换 M3 视觉（用户优先级未含）。

---

# 第三轮：correctness follow-up（ae14f71 审计 15 项）

## 后端修复（`.verify/backend_test.py` 42/42）

| # | 审计项 | 修复 |
|---|--------|------|
| 1 | **fresh DB 首次启动崩溃(P0)** | `_migrate_legacy_sqlite()` 先查 sqlite_master，`loras` 表不存在即 no-op（create_all 后再建）；新增「全新空目录 + 全新 DB 首次启动」测试（迁移→建表→写入→列 nullable 断言） |
| 2 | **import 信任前端路径(P0)** | 契约改为 `{source_id, relative_paths[]}`；服务端重验：realpath(root/rel) 必须仍在 source root 内（commonpath）、文件存在、扩展名、重新查询 ComfyUI、重新判重复/冲突；恶意路径（`../`、绝对、盘符、非 lora 扩展名）与过期路径（文件已删）分别返回 errors |
| 3 | **同批同 filename 重复写入(P0/P1)** | import 循环内即时更新 `seen_filenames`/`db_filenames`/`seen_src_paths`，同请求重复提交第二个被跳过（测试通过） |
| 4 | **跨来源同 basename / basename fallback(P0/P1)** | 纯函数 `_match_comfy`：exact/相对路径匹配优先；basename fallback 仅当「ComfyUI 中该 basename 唯一 且 本批无同名」时启用；`scan`/`import` 计算跨来源同名（`_other_sources_basenames`）计入 `ambiguous` → 两个不同文件不会同时标「已识别」（单元测试断言三种情形） |
| 5 | **ComfyUI 离线检测(P1)** | `_fetch_comfy_loras()` 显式 `check_health()` 判定（get_loras 吞异常返回 [] 不再导致误报在线）；可注入 client 便于测试（不可达端口 → False） |
| 7 | **路径预览由后端解析(P0/P1)** | 新增 `POST /api/loras/resolve-path`（resolved + exists/readable + lora 文件计数）；前端删除「见 D: 就猜 /mnt」逻辑，改调后端 API（Playwright 断言确实发出该请求、显示值=后端返回值；本机为 WSL2 故 `/mnt/d/` 正确） |
| 14 | **GENERATED_DIR 受 cwd 影响(P1)** | 改为属性：锚定在数据库文件所在目录下 `data/generated`，repo root 或 `cd backend` 启动均指向同一稳定绝对路径 |
| 15 | **Settings 无差别 int 转换(P2)** | `_parse_value(key, val)` 按声明字段类型解析（bool/int/其余保持 str）；数字形式 API Key/model 不再被转成 int（测试：timeout=int、base url=str） |

## 前端修复（`.verify/r3/verify3.cjs` + `r2/verify2.cjs` 回归，全部 PASS）

| # | 审计项 | 修复 |
|---|--------|------|
| 6 | 扫描预览默认全选(P1) | 默认 0 选中；「全选新增」为主动操作（实测 foot-hint「已选 0 项」+ 无 `.on` 行） |
| 8 | 草稿未保存语义状态(P1) | draft v2：保存 `facts/lastParsedInput/isSemanticDirty/isPositive/negativePromptDirty`；无可信 facts（旧版 v1/异常）→ `isSemanticDirty=true`；`buildPrompt` 增加空 facts 保护——非 force 时若 facts 为空且 Prompt 非空，不用空 facts 重编译覆盖恢复的 Prompt（实测：恢复后改 Safety，Prompt 保持不变） |
| 9 | 清空创作台不清语义(P1) | `clearDraft()` 清 facts/lastParsedInput/dirty flags/generation stale state（实测：清空后展开解析详情为空态） |
| 10 | 尺寸静默 clamp(P1) | 输入不再 `Math.min/max` 修正，原值保留（实测 9000 保留）；Generate 前硬校验（64–8192 + 宽高比 0.25–4），越界明确报错且「未修改你的输入」 |
| 11 | 锁比例 swap 不反转 ratio(P1) | `swapSize()` 在锁定时 `lockedRatio = 1/lockedRatio`（实测 1000×2000 锁 0.5 → swap 后 ratio 2 → 改宽 500 → 高 250） |
| 12 | 生成可重复提交(P1) | `generateImage()` 顶部 `if (isGenerating) return`；Generate 与「再生成」按钮生成期间 disabled（实测同步双击仅 1 次提交 + 生成中按钮 disabled） |
| 13 | 本地持久化失败伪装成功(P1) | 新增 `generationPersisted`；persist 失败不再显示「生成完成！」而是「图片已生成，但本地历史归档失败——历史记录当前依赖 ComfyUI output」；history metadata 记录 `persisted` |

## 截图（`.verify/r2/`，本轮无视觉改动）
沿用 `01_lora_library.png` … `09_library_search.png`；本轮只改行为不改外观。

---

# 第四轮：correctness closure（be3e91d 之后，仅 3 项，不扩范围）

1. **sync-comfyui 复用权威匹配**（`_apply_sync_validity` 可测化 + `_fetch_comfy_loras`）：
   - 显式 health check；ComfyUI 离线 → 返回 `comfy_available:false, validity_updated:0`，**不把整个库标 invalid**；
   - exact / relative 匹配优先；basename fallback 仅当 ComfyUI 中该 basename 唯一且库内无同 basename 记录；
   - 两个同 basename 的不同文件不会同时 valid（单元断言 `[True, False, True]`）。
2. **DATABASE_URL / GENERATED_DIR cwd 无关**：
   - `PROJECT_ROOT`（由 `backend/app/config.py` 的 `__file__` 推导）+ `DATABASE_URL_ABS`（SQLite 相对路径一律锚定项目根）；
   - `database.py` 的 engine 与迁移默认改用 `DATABASE_URL_ABS`；`GENERATED_DIR` 派生自它；
   - 测试用子进程分别以 `cwd=repo root` 与 `cwd=backend` 探测，两者 DB URL 与 GENERATED_DIR 完全一致，且均落在项目根下。
3. **Settings POST/GET 统一按声明类型转换**（`_coerce` 共用）：
   - `GENERATE_TIMEOUT_SECONDS` 收到字符串 `"300"` → 运行时与 GET 均为 int 300；
   - 数字形式的 API Key / model 字段保持 string（`"123456"` 不被 int 化）。

后端 `backend_test.py` 56/56；`verify2.cjs` / `verify3.cjs` 前端回归 ALL PASS；前端无代码改动。
本 commit 后按用户要求停止 correctness/structure audit。

---

# 第五轮：真实生成体验 + Prompt Benchmark 基线

## Milestone A 生成体验（`.verify/r4/verifyA.cjs` 20/20 ALL PASS，真实 ComfyUI 生成）

先核实 ComfyUI 0.34.2 真实 API（`.verify/r4/comfy_probe.py`）：
- WS `progress {value,max,node}` 提供**真实 KSampler step 进度**；`/queue` 项为 `[number,prompt_id,inputs]`；
- 坏模型提交即 400，body 带 `node_errors`；
- **`DELETE /queue/{prompt_id}` → 405（无 task-scoped cancel）**；`POST /interrupt` 为**全局**中断（`execution_interrupted`）。

实现：
- 后端 `services/comfyui/monitor.py`：持 WS（client_id 与提交一致）收集 per-prompt 状态
  （queued/running/saving/done/error/cancelled + 真实进度）；`/api/comfyui/queue`、
  `/status/{prompt_id}`（含 queue_position/is_running）、`/interrupt`；提交期错误分类
  （连接/Workflow 校验/找不到模型/LoRA——解析 node_errors）。
- Store：`lastGeneratedSeed` + `GenerationSnapshot`（active/last，A9 提交即定格）；
  `seed` 三态（-1 随机 / 固定 / 使用上一张）；生成流程改 monitor 轮询（真实进度 /
  队列位置 / 停止等待 / 中断门控）；persist 失败不伪装；saveHistory 用快照值。
- StudioView：Canvas metadata 显示真实 seed（`384 × 384 · Seed 523941558 · 8 Steps`）；
  工具栏「使用此 Seed / 再生成 / 导出」+「已归档」标记；Seed 三态控件；错误摘要 + 查看详情；
  尺寸预设 人像/横版/方形（带实际尺寸）。

验证（20 项全过）：真实 seed 显示、使用此 Seed 固定复现、固定 seed 再生成相同、
History 恢复 seed/尺寸、双击仅 1 次提交、生成中改参数不污染 metadata、
ComfyUI 断开错误清晰、执行错误摘要+详情、真实 step 进度、真实中断→cancelled。

A12 默认参数：web_search 不可用（key 失效），仓库内来源为
`docs/BENCHMARK_PLAN.md` 固定 Euler + sgm_uniform + 28 步 + CFG 4.5，
**无外部证据，未改动默认值**（遵守"不凭模型常识改参数"）。

## Milestone B Prompt Benchmark（`benchmark/`，Baseline A）

- `benchmark/prompt_cases.json`：25 例真实中文描述，覆盖 B1 全部 25 类；
  每例记录预期语义（实体 must_have / 关系 / must_not_bind / 覆盖 / 不脑补）。
- `benchmark/run_benchmark.py`：分阶段保存
  INPUT → FACT EXTRACTION → CHARACTER RESOLUTION → FINAL FACTS → PROMPT ASSEMBLY；
  确定性规则检查（实体数/属性绑定/禁止绑定/关系主客体/未解析 trigger/来源/
  Artist/LoRA/Safety/占位符泄漏），不用 LLM 自评。
- 结果：`benchmark/results/20260902_102015.json` + `.md`

**Baseline A = 23/25**。唯一失败类别（2 例）：
- `action_b_to_a_08`、`complex_long_25` — **实体占位符（c1/c2）泄漏进最终 Prompt**
  （"Yangyang is ... holding c2's wrist" / "holding hands with c2"），
  即含他人引用的关系/属性文本未把实体 id 替换成角色名。
- 其余 23 例（含双人服装/发色绑定、动作主客体、角色书、覆盖角色书默认、不脑补、
  Artist 双 Artist、LoRA 有/无 trigger、Safety 四档、三人物、复杂长句）全部确定性通过。

**本轮未改 Prompt Engine**（按用户要求：先报告，等确认后再进入针对性修复）。

