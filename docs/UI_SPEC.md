# UI 规格 — Material Design 3

## 1. 视觉目标

项目是专业创作工具，不是 AI 营销网站。

目标：

- Google Material Design 3
- 中文
- 桌面优先
- 支持响应式
- 深浅主题
- 信息密度中等偏高
- 温和、清楚、专业
- 高频操作路径短

避免：

- 大面积 AI 渐变
- 霓虹紫蓝
- 玻璃拟态
- 大量大圆角 Card
- 每一个 section 都套 Card
- 巨大空白
- 夸张动效
- Emoji 作为主要功能图标
- 首页 Hero Banner

---

## 2. 主框架

桌面端建议：

```text
┌──────────────┬──────────────────────────────┐
│ Navigation   │ Top App Bar                  │
│ Rail /       ├──────────────────────────────┤
│ Drawer       │ Main Content                 │
│              │                              │
│ 创作台       │                              │
│ 角色书       │                              │
│ 画师库       │                              │
│ LoRA         │                              │
│ 规则         │                              │
│ ComfyUI      │                              │
│ 历史         │                              │
│ 设置         │                              │
└──────────────┴──────────────────────────────┘
```

---

## 3. 创作台

推荐三块信息区，不要求机械等宽三栏。

### 输入区
核心：

- 大文本输入框
- Safe / NSFW segmented control
- Provider / Model
- Thinking
- Reasoning effort
- 角色
- Artist
- LoRA
- Rules

### 解析区
展示：

- 识别人物
- 来源：模型角色 / 用户角色书
- 事实列表
- Trigger
- 可编辑解析

原始 JSON 默认折叠到“调试信息”。

### 生成区
展示：

- 最终 Prompt
- Negative Prompt
- ComfyUI 状态
- Checkpoint
- 生图高级参数折叠
- 生成按钮
- 进度
- 图片

---

## 4. MD3 组件原则

使用：

- Navigation Rail / Navigation Drawer
- Top App Bar
- Filled Button：主要动作
- Filled Tonal Button：次主要动作
- Text Button：低强调
- Filter Chip：筛选
- Input Chip：已选角色/Artist/LoRA
- Segmented Button：Safe / NSFW
- Dialog：创建和编辑资源
- Side Sheet / Drawer：详情和高级设置
- Snackbar：短状态提示
- Inline error：连接和校验错误

不要为了“MD3”机械使用大量 Card。

---

## 5. 画师库

参考 Anima Style Explorer 的核心价值：

- 快速浏览
- 分类
- 收藏
- 一键选用
- 可看到 tag 串

推荐：

- 左侧分类筛选或顶部 filter chips
- 中间自适应网格
- 卡片尺寸紧凑
- 收藏图标
- 点击打开详情
- 详情里展示 tag string
- “加入当前 Prompt”按钮

用户自定义画师与内置画师使用同一视觉体系。

---

## 6. 角色书

列表页：

- 搜索
- 分类
- 收藏
- 新增

编辑页不应一次把几十字段平铺到底。

建议按：

- 基础
- 头部
- 身材
- 服装
- 其他

分组折叠。

空字段允许。

---

## 7. LoRA 页面

重点不是模型商店，而是本地管理。

列表显示：

- 名称
- 文件状态
- trigger
- strength
- enabled
- favorite
- category

如果 ComfyUI 文件失效：

- 明确 warning
- 不静默忽略

---

## 8. 状态设计

LM Studio：

- 已连接
- 未连接
- 模型加载中
- 模型已加载
- 模型卸载中
- 卸载失败

ComfyUI：

- 已连接
- 未连接
- 队列中
- 生成中
- 完成
- 错误

状态应该清楚但不过度抢眼。

---

## 9. 完整成品交互参考

用户输入：

> 穗穗穿着泳装，秧秧穿蓝色海军水手服，穗穗在沙滩上追秧秧。

点击：

**解析提示词**

系统展示：

```text
人物
● 穗穗    模型角色
● 秧秧    模型角色

事实
穗穗 → 穿着 → 泳装
秧秧 → 穿着 → 蓝色海军水手服
穗穗 → 追逐 → 秧秧
场景 → 沙滩
```

每条都能修改。

之后显示：

```text
最终 Anima Prompt
[英文内容]
```

用户再选择 Artist 与 LoRA。

右侧：

```text
ComfyUI
● 已连接

Checkpoint: ...
1024 × 1536

[生成]
```

图片直接回到页面。

这是 MVP 应达到的完整闭环。
