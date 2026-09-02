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

---

# 第六轮：Candidate B — 修复 PromptWriter 实体引用泄漏

根因：`write_natural_language_scene` 直接把含内部实体 id 的 `Statement.text` 拼进最终
Prompt，且 relation 的 target 检查基于未解析文本 → `holding c2's wrist Suisui`。

修复（仅 `backend/app/services/prompt_engine/writer.py`）：
- 新增确定性 helper `resolve_entity_refs(text, entity_by_id)`：token/boundary-aware
  （`\b...\b`，按 id 长度降序），只替换 facts 中真实存在的 id；未知 id（c99）保留给
  validator/benchmark 暴露；名称优先级 caption_name → canonical_tag → name → the character。
- 对所有 statement kind（attribute/relation/scene/general）统一先解析引用再组装；
  relation 的 target 追加改为「替换后文本已含 target 名则不追加」。
- **只改最终 rendering，facts 保持 c1/c2 不变。**

单元测试（`backend/tests/test_writer_refs.py`，无 LLM，9/9）：
`c2's→Suisui's`、attribute 引用、relation 已含 target 不重复、c1 与 c10 不部分匹配、
未知 c99 保留、scene/general 引用、两个原失败案例的精确期望、名称优先级。

## A/B 分层对比

| 层 | 内容 | 结果 |
|----|------|------|
| Baseline A | 完整 pipeline（`20260902_102015`） | **23/25**（2 例 c1/c2 泄漏） |
| **B1** | 冻结 Baseline A `3_final_facts`，只重跑 assembly（`20260902_105602_frozen`） | **25/25**，原 23 例 0 回归 |
| **B2** | 完整 pipeline 重跑（`20260902_105946`） | **25/25** |

成功条件全部满足：
- `action_b_to_a_08` → `Yangyang is catching up with Suisui and holding Suisui's wrist.`（无 c1/c2，方向不变）
- `complex_long_25` → `Suisui is wearing a white swimsuit and holding hands with Yangyang ...`（无泄漏，泳装仍绑定 Suisui，两人 smiling/look at sunset，seaside at dusk 保留）
- invariant：泄漏检查改为「按本案例 facts 的实体 id 精确检测 unresolved internal entity reference」，不笼统删 c数字。

附：`test_golden_cases.py::test_case_21` 更新为匹配 closure 轮既定语义
（sync-comfyui = validate-only，不自动导入、不覆盖用户编辑）；全部 38 个后端测试通过。

---

# 第七轮：Semantic Stress Benchmark（只建压力测试+跑+分析+报告，未改产品代码）

新增 `benchmark/stress_cases.json`（47 例，覆盖 38 个压力类别）+ runner 扩展
（双数据集、variants、ambiguity_expected、capability_gap、失败重跑 3 次稳定性分类）。
**未修改任何产品代码**（仅 benchmark/）。

## 结果（`benchmark/results/stress_20260902_124320.json/.md`）

- 总 72 例：**68 PASS**（baseline 25/25，stress 43/47）；4 个失败全部 **deterministic**（4/4 复现）。
- 失败按阶段：全部 extraction（4 例）。
- 失败按类别：所有权帽子转移(1)、共享属性(1)、否定(1)、复杂长句(1)。

## Confirmed deterministic failures（2 个真实问题）

1. **ownership_hat_transfer_03** — 帽子转移被逐字渲染：
   `Suisui is taking off hat and putting hat on Yangyang. Yangyang is wearing hat.`
   hat 同时出现在原属主（穗穗）与最终穿戴者（秧秧）身上，静态图像会呈现转移中间态。
   （对照：body_ownership_05 的 `c2's wrist→Suisui's wrist`、`c1's hair→Yangyang's hair`
   已正确——Candidate B 的属格引用修复在真实管线中生效。）
2. **complex_long_34** — 非人实体「小狗」被当成第 4 个角色实体：
   `safe, ..., inu. Xiaoxia ... playing with Dog.`（entity_count 4 vs 3，
   并新增 canonical trigger `inu`）。

## Capability gaps（2 个，已声明、未扩 schema）

- **shared_two_18 / negation_hat_20** — 否定句以字面 `not wearing a raincoat/hat`
  statement 表示（schema 无独立 negative fact 类型）。抽取**未误转 positive**（正确），
  但渲染为 `Xiaoxia not wearing a raincoat`，与图像语义（不出现该物品）有表达差距。

## 稳定性 / 歧义

- 无 intermittent / unstable；4 个失败全部 deterministic。
- 歧义案例 pronoun_ambiguous_06 **通过**（未新增第三人、红伞保留、无脑补）。
- temporal_overwrite_23 声明的能力缺口**未触发**（引擎恰好输出最终态白裙）。
- 标点变体（分号/而/然后/同时）全部通过——无明显标点不稳定。
- partial_shared_19 案例输入曾为匿名三女孩（期望误写具名），已修正为具名后通过。

## 推荐下一步（等待确认，不自动进入 Candidate C）

只修 **ownership_hat_transfer_03** 一类：动作转移（摘下/戴上/递给）的最终视觉状态归属。
候选：assembly 阶段对 `take off / put on / hand to` 类动作做「最终穿戴者优先」归并，
把转移动作简化为最终状态（`Yangyang is wearing a hat`），同时不引入新 schema。

---

# 第八轮：Candidate C — Static Visual State Rendering

目标：完成式物品转移不再同时渲染中间态（taking off X）与最终态；facts 保持不变。

实现（仅 `backend/app/services/prompt_engine/writer.py` + benchmark）：
- `compute_transient_suppression`：**结构组合**判定——同一物体同时存在
  ① A removal（take off/remove/untie...）＋ ② A→B transfer（put/hand/pass/wrap... on/to/around）
  ＋ ③ B final possession（wearing/holding/catching...）时，才抑制 ① 的渲染。
  非关键词删句器：单独 "taking off hat" 仍保留；无 target final state 不抑制；异物体不抑制。
- 物体名词规范化（去冠词/属格 + 地点短语终止符如 "wearing a hat on her head"）。
- 原案例 ownership_hat_transfer_03 重归类：facts 语义正确不再判 extraction，
  改为验证 转移保留 + 最终穿戴者 + 渲染无冲突瞬态（prompt_has/not_has_en 渲染级检查）。

## 结果

| 层 | 结果 |
|----|------|
| writer 单测（`test_writer_visual_state.py`，无 LLM） | **13/13**（完成转移/仅摘保留/仅戴/异物体/自身换装/眼镜/地点短语/facts 不变） |
| **C1** 冻结原 72 例 facts 只跑 assembly（`stress_20260902_134932_frozen`） | 03 FAIL→**PASS**；原 68 通过 **0 回归**；剩余失败恰为 C 范围外 3 项 |
| **C2** 完整 pipeline（`stress_20260902_140016`） | **75/79**；03 PASS；transfer 控制案例（围巾/眼镜/包/书/仅移除/异物体）全过；原 72 例 **0 回归** |

03 最终渲染（facts 未变）：
`Suisui is putting her hat on Yangyang. Yangyang is wearing hat.`（taking off hat 已抑制）。

## 新的确定性发现（Candidate D 候选，本轮不修 Extractor）

- **transfer_coat_47**：`穗穗把外套脱下来披到秧秧身上` → 抽取**稳定省略接收方最终态**
  （facts 只有 taking off + putting on，无秧秧 wearing）→ 按规则正确不抑制，
  输出 `Suisui is taking off her coat and putting the coat on her Yangyang`。
  这是 extraction 完整性缺口（转移场景缺 target final state），非渲染 bug。

## 未处理（按用户范围）

- shared_two_18 / negation_hat_20：NEGATION CAPABILITY GAP（不扩 schema）。
- complex_long_34：非人实体，单独记录。
- 无 intermittent/unstable（本轮 failures 全部 deterministic）。

---

# 第九轮：Candidate D — Completed Transfer Semantics

范围：D1 relation target 代词渲染 + D2/D3 extraction contract（只改 system prompt，不扩 schema）
+ D4 成对案例 + D6 稳定性 ×4 + D8 frozen 回归 + D9 tooling 修复。

## D1 — relation-target rendering（`writer.py`）

`_render_relation_target`：仅当 relation text 尾部**介词宾语位**为 target 代词
（to/on/onto/around/for/toward/at + her/him/them）时替换为结构化 target 可读名；
不全局替换 her/him/them（`holding her own hat` 不受影响）；已含 target 名不重复。
`putting the coat on her + c2/Yangyang → putting the coat on Yangyang`（不再 her Yangyang）。
确定性单测 8/8（`test_writer_relation_target.py`）。

## D2/D3 — extraction contract（`extractor.py` EXTRACTION_SYSTEM_PROMPT）

新增规则 7-9 + 两个 few-shot：
- **完成式转移**（戴到B头上/围到B脖子上/披到B身上/戴到B脸上/递给B且B接住）：
  必须同时输出 relation(转移) + 接收方 final visual state attribute（wearing/holding X）。
- **进行式/未确认**（正在给B戴/正准备递/朝B递出）：只输出转移动作，**禁止脑补**接收方已持有。
- 不扩 schema（仍是 entity/statement 最小结构）。

## D4 — transfer pair cases

新增 5 例（`D_hat_progress_52` / `D_coat_progress_53` / `D_scarf_progress_54` /
`D_glasses_progress_55` 进行式 + `D_book_handover_56` 递书不确认）；既有 5 个 completed
案例加 `d_contract` 元数据。总案例 84（baseline 25 + stress 59）。

## D6 — extraction contract 稳定性（×4/例，`transfer_stability_20260902_142627`）

| 类型 | 接收方 final state 出现 |
|------|------|
| completed ×5（hat/scarf/glasses/coat/bag） | **4/4**（契约稳定达成） |
| in_progress ×4 + unconfirmed ×1 | **0/4**（零脑补） |

## D8 — frozen regression（D1 改动后，`stress_20260902_143131_frozen`）

原 79 例冻结只重跑 assembly：**0 regression**；Candidate B（c1/c2）与 Candidate C（瞬态抑制）无退化。

## 最终全量 pipeline（`stress_20260902_145802`）

**81/84**（baseline 25/25，stress 56/59）。原 79 例 **0 回归**；
`transfer_coat_47`（C 轮确定性失败）转 **PASS**：
`Suisui is putting the coat on Yangyang. Yangyang is wearing the coat.`
（契约补齐秧秧 wearing → C 规则抑制 taking off 瞬态；D1 无 "her Yangyang"）。
剩余 3 项失败全部在 D 范围外：shared_two_18 / negation_hat_20（否定 gap）、complex_long_34（非人实体）。

## D9 — benchmark tooling

`fail_by_stage` 改为统计 **unique 失败案例**，另加 `failed_checks_by_stage` 记录 constraint 总数。

---

# 第十轮：Candidate D follow-up — 聚合修复 + production fixture 净化

## D9 聚合 bug 修复（`run_benchmark.py`）

上一轮实现有个二次包装 bug：`fail_by_stage` 已在循环里转成 `{stage:{count,cases}}`，
report dict 里又用 `{k:{count:len(v), cases:v}}` 再包一层 → 产生
`count=2(字典键数), cases={count,cases}` 的嵌套对象。

修复：抽 `summarize_failures(results)` helper（fail_by_stage 按 unique case、
failed_checks_by_stage 按 constraint 总数、fail_by_category 按案例），report 直接用。
MD 报告同步改。加确定性测试 `test_benchmark_aggregation.py`（3 例：unique-case 计数、
无嵌套对象回归、全过无阶段）。

真实报告验证（`stress_20260902_163251`）：
```json
"fail_by_stage": { "extraction": { "count": 3, "cases": ["complex_long_34","negation_hat_20","shared_two_18"] } },
"failed_checks_by_stage": { "extraction": 3 }
```

## production few-shot 人名净化

`EXTRACTION_SYSTEM_PROMPT`（schema 示例 + 完成式/进行式 few-shot）与
`resolver.py` production prompt 里的 benchmark 角色名 穗穗/秧秧/Suisui/Yangyang
→ 无关虚构名 **林澄 / 周遥 / Lin Cheng**（`lincheng`）。JSON 结构、c1/c2、语义内容完全不变。
同步替换 pydantic 字段描述里的示例名（不进 LLM，为语义层冻结保持一致）。

## 验证

- backend tests：**53 passed**（50 + 聚合 3）。
- D6 transfer stability ×4：**10/10**（completed 4/4 final-state、in_progress+递书 0/4 脑补）——人名替换无副作用。
- 全量 Baseline/Stress：**81/84**（baseline 25/25，stress 56/59），与原结果一致，0 回归。
- D9 聚合修复在真实报告结构验证通过。

commit message 澄清：上一轮实际 50 测试（非 58），本轮 53。

## 附带修复（benchmark 数据）

`action_b_to_a_08` 关系关键词补 chase/hold（LLM 措辞 chase vs catch up 变体）——非产品回归。

