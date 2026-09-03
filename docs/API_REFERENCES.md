# API 与外部参考

实现相关模块前，Agent 必须优先查当前官方文档。

不要只依赖本文件里写的接口示例，因为外部 API 可能变化。

---

## 1. Anima

用途：

- Prompt 训练方式
- Tag 规则
- character / artist / series 写法
- Natural language caption
- 多人 Prompt 习惯

优先查：

- 官方或主要发布模型卡
- Hugging Face 模型卡与 README

实现 Prompt Engine 前必须确认当前模型卡。

---

## 2. Anima Style Explorer

参考：

`https://anima.mooshieblob.com/`

用途：

- 画师浏览交互
- 画师 tag 展示
- 分类与快速选择体验

只参考产品交互价值。

不要复制其源码或视觉。

---

## 3. LM Studio

官方文档：

`https://lmstudio.ai/docs/developer/rest`

重点：

- `/api/v1/chat`
- `/api/v1/models`
- `/api/v1/models/load`
- `/api/v1/models/unload`

当前已知 unload 形式：

```text
POST /api/v1/models/unload
```

使用具体接口前重新检查官方文档。

本项目本地 LLM 第一版仅支持 LM Studio。

Thinking / reasoning effort：

- 不要假设所有模型与接口都支持。
- 使用 capability detection。
- 官方文档没有明确支持时，不要编造参数。

---

## 4. ComfyUI

官方开发文档：

`https://docs.comfy.org/development/comfyui-server/comms_routes`

重点：

- `/prompt`
- `/ws`
- `/models`
- `/models/{folder}`
- `/system_stats`
- `/object_info`
- `/history`
- `/view`

具体实现前检查当前官方文档和实际 `/object_info`。

不要凭经验猜自定义节点名称。

---

## 5. Material Design 3 Expressive

参考：

- `https://m3.material.io/`
- `https://m3.material.io/blog/building-with-m3-expressive`（采用度量 rubric：
  Good / Better / Excellent，按 component / motion / color / shape / typography 五类评估）

目标：

- M3E 信息层级与 component 配置（nav rail、segmented button、slider、switch、
  loading indicator、wavy progress）
- spring motion 与统一 motion tokens
- 新 shape 语言（loading indicator shape morph）

不要把"MD3"简化成"紫色 + 大圆角"，也不以"用了 M3 色板和圆角"为验收。

### 5.1 matraic/m3e（Web 实现）

GitHub：

`https://github.com/matraic/m3e`

用途：

- R1 起提供真实 M3E Web Components（`@m3e/web`）

注意：

- 这是**第三方** Material 3 Expressive 实现，不是 Google 官方库
- 只模块化 import（tree shaking），禁止 `@m3e/web/all`
- 使用具体组件前检查 repo README / exports / component docs（版本以 npm latest 为准）

---

## 6. Vuetify

使用当前稳定版 Vuetify。

官网：

`https://vuetifyjs.com/`

不要把小版本写死。

---

## 7. TE_MAN

GitHub：

`https://github.com/tl2012tl/TE_MAN`

用途：

- 后续实验性 3D Director / 创作流程研究

MVP：

- 不强依赖
- 不深度耦合
- 不为了 TE_MAN 改核心架构
