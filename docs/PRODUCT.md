# 产品规格 — Anima Prompt Studio

## 1. 产品定位

这是一个面向 Anima 的提示词与生图工作台。

用户不应该需要理解复杂的 Anima Prompt 工程，也不需要手动维护大量多人关系 tag。

用户只需：

1. 自然语言描述画面。
2. 可选角色。
3. 可选画师。
4. 可选 LoRA。
5. 选择 Safe / NSFW。
6. 预览系统理解。
7. 生成英文 Prompt。
8. 交给 ComfyUI 生图。

---

## 2. 用户核心流程

示例：

用户输入：

> 穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗在沙滩上追秧秧。

系统展示：

### 人物
- 穗穗 — 模型角色
- 秧秧 — 模型角色

### 事实
- 穗穗 → wearing → swimsuit
- 秧秧 → wearing → blue sailor uniform
- 穗穗 → chasing → 秧秧
- scene → beach

用户可以修改任何解析结果。

然后生成最终英文 Prompt。

用户再选择：

- Artist
- LoRA
- LoRA Strength
- Safe / NSFW

最后点击“生成”，由 ComfyUI 返回图片。

---

## 3. 页面

### 创作台
主要入口。三栏工作区（详见 `docs/UI_SPEC.md` §7）：

- 全局 `m3e-nav-rail`（compact 80px）
- Context Rail：Safety（segmented）、规则集、画师、LoRA（switch + slider）、登场角色
- The Forge（工坊流水线）：自然语言输入 + 语义抽取 → Facts Pipeline → Final Prompt
- Canvas：ComfyUI 状态、画布 HUD、wavy 真实进度、生成 CTA、Seed（segmented + tonal 复用）、Filmstrip

高级设置在独立 dialog（Provider / Model / Reasoning slider / 尺寸 / Steps / CFG / Workflow）。

旧版单文件创作台保留在 `/legacy-studio` 供回归比对。

另有独立体验页 `/intro`（《一句话的旅程》，plain 路由无导航栏）。

### 角色书
只保存用户自己定义的角色。

支持：

- 新增
- 编辑
- 删除
- 分类
- 收藏
- 导入 / 导出

角色字段允许为空。

推荐字段：

- 名称
- 别名
- 性别
- 年龄段
- 身材
- 发色
- 发型
- 发长
- 瞳色
- 脸部特征
- 头饰
- 上衣
- 外套
- 下装
- 袜子
- 鞋
- 其他配饰
- 默认表情
- 默认姿态
- 禁止特征
- 补充描述

### 画师库
参考 Anima Style Explorer 的浏览价值：

- 搜索
- 分类
- 收藏
- 预览画师串
- 一键加入
- 用户自定义画师
- 导入 / 导出

不要复制其源码或视觉。

### LoRA 库
支持：

- 从 ComfyUI 发现（validate-only 同步）
- 来源目录扫描与导入
- trigger words（本地权威；Civitai trainedWords 展示并可手动采用）
- 默认 strength（本地权威；Civitai 推荐权重展示并可手动采用）
- 启用 / 禁用
- 分类
- 收藏
- 检查文件存在
- 删除映射
- Civitai 元数据（SHA256 识别、Red/Green 双 host、封面缓存、
  Usage Tips：推荐 strength / clipSkip / steps / epochs、模型简介与版本说明）

生成时必须同时：

- 注入 trigger
- 写入 ComfyUI LoRA strength

本地字段（名称 / 描述 / trigger / strength）永远不被远端覆盖。

### 规则文件
支持：

- `.md`
- `.txt`
- `.yaml`

可：

- 添加
- 启用 / 禁用
- 排序
- 删除
- 预览

### 设置
包括：

- LM Studio
- 云端 Provider
- ComfyUI URL
- 主题族（ImageForge 紫 / Gemini / Antigravity Mono × 亮暗）
- Civitai Host（Red / Green）与可选 API Token
- 默认 Safe / NSFW
- 默认模型

### 历史
保存：

- 原始输入
- 解析结果
- 角色
- Provider
- 模型
- Thinking
- Prompt
- Negative Prompt
- Artist
- LoRA
- Strength
- Safe / NSFW
- ComfyUI 参数
- 图片

支持恢复。

---

## 4. 角色书语义

角色书不是“Anima 所有角色数据库”。

角色书是：

> 用户主动声明“这个名字要按我定义的角色来处理”的覆盖层。

若角色名存在于角色书：

- 使用用户定义。
- 不使用角色名作为 Anima tag。

若不存在：

- 默认按模型角色处理。
- 使用 canonical trigger。
- 不自动补角色外貌。

---

## 5. Safe / NSFW

必须是用户显式选项。

模型不能自行改变。

这是确定性状态。

---

## 6. Prompt 模式

默认：

**忠实模式**

只表达用户明确要求和必要语法关系。

未来可以增加：

**创意补全模式**

允许 AI 自由增加：

- 光线
- 环境细节
- 镜头
- 氛围
- 表情等

但必须是用户主动开启，不能成为 MVP 默认行为。

---

## 7. 第一版不做

- 多用户
- 登录
- 云同步
- 在线角色数据库
- 自动抓取大型角色库
- 可视化 Workflow 编辑器
- TE_MAN 深度耦合
- ControlNet 自动编排
- 高级区域人物绑定
- 多生图后端统一调度

TE_MAN 可以在后续实验阶段评估。
