# AGENTS.md

## 1. 项目目标

本项目是一个面向 **Anima 二次元生图模型** 的本地优先 Web 创作工作台。

核心价值不是“让 AI 自由帮用户写 Prompt”，而是：

> 把用户已经表达的画面要求，可靠地转换为适合 Anima 的英文 Prompt，并管理角色、画师、LoRA、规则文件与 ComfyUI 生图流程。

产品优先级：

**忠实理解用户 > 人物与属性绑定正确 > Prompt 清晰 > 自动优化 > AI 自由发挥**

---

## 2. 核心不变量

### 2.1 用户输入优先
用户当前明确输入永远拥有最高优先级。

禁止 Agent、LLM 或编译器擅自加入：

- 用户没说的发型
- 用户没说的发色
- 用户没说的服装
- 用户没说的表情
- 用户没说的背景
- 用户没说的天气
- 用户没说的角色
- 用户没选的画师
- 用户没选的 LoRA
- 用户没选的 Safe / NSFW

### 2.2 角色书是“覆盖层”
如果角色存在于用户角色书：

- 视为用户自定义角色。
- 角色名字只用于 UI 和内部关系绑定。
- 不把角色名字作为 Anima character tag。
- 展开用户角色书中的设定。
- 当前场景要求可覆盖角色书中的默认服装或其他可覆盖属性。

如果角色不在角色书：

- 不判定为“未知角色”。
- 默认用户知道这是 Anima 已训练角色。
- 使用 canonical character trigger。
- 不自动补角色原作外貌。
- 只追加用户本次明确指定的变化。

### 2.3 Tag 与自然语言职责不同
Tag 适合表达：

- quality
- safety
- 人数
- character trigger
- series
- artist
- general tags
- LoRA trigger

自然语言适合表达：

- 谁穿什么
- 谁对谁做什么
- 多人动作关系
- 属性归属
- 空间关系
- 复杂构图
- 复杂事件

多人场景禁止退化成没有归属关系的纯 Tag Soup。

---

## 3. 默认语言

以下内容用中文：

- UI
- 项目文档
- Agent 汇报
- 错误提示
- 设置说明

以下内容最终发送给 Anima 时使用英文：

- Prompt
- Negative Prompt
- character trigger
- artist tag
- LoRA trigger
- Anima tags

---

## 4. 技术方向

前端：

- Vue 3
- Vite
- TypeScript
- Pinia
- 当前稳定版 Vuetify
- Material Design 3 视觉与交互原则

后端：

- Python
- FastAPI
- SQLite
- SQLModel 或 SQLAlchemy
- httpx
- WebSocket

LLM：

- 本地：LM Studio
- 云端：OpenAI-compatible API

生图：

- ComfyUI

不要把具体依赖小版本当作产品不变量。

---

## 5. 不要过度工程化

第一版不要主动引入：

- 微服务
- Redis
- PostgreSQL
- Kafka / RabbitMQ
- Kubernetes
- 多用户系统
- RBAC
- 云同步
- 插件市场
- CQRS
- 复杂 Repository / Port / Adapter 层
- 自建任务队列
- 可视化 Workflow 编辑器

除非后续需求明确证明必要。

---

## 6. Prompt Engine 数据流

保持：

```text
用户自然语言
  ↓
语义事实抽取
  ↓
角色解析
  ↓
本地约束校验
  ↓
Anima Prompt Writer
  ↓
确定性注入（Safety / Artist / LoRA / 规则）
  ↓
最终英文 Prompt
  ↓
ComfyUI
```

不要默认改成：

```text
用户输入 → LLM 直接自由生成最终 Prompt
```

---

## 7. 中间表示原则

不要建立包含几十个固定字段的大型 Scene JSON。

采用：

**稳定外壳 + 开放语义内容**

建议最小结构：

```json
{
  "entities": [],
  "statements": []
}
```

entity 只描述对象身份。

statement 只固定：

- `kind`
- `subject`
- `target`（可选）
- `text`

示例：

```json
{
  "kind": "attribute",
  "subject": "c1",
  "text": "wearing a swimsuit"
}
```

```json
{
  "kind": "relation",
  "subject": "c1",
  "target": "c2",
  "text": "chasing"
}
```

不要为每一种新动作增加 schema 字段。

---

## 8. 确定性层与语义层

### 程序必须确定性控制

- Safe / NSFW
- 角色书数据
- trigger 缓存
- 画师选择
- LoRA 选择
- LoRA strength
- 规则文件
- Provider
- ComfyUI workflow
- 用户当前明确参数

### LLM 负责

- 中文理解
- 实体识别
- 属性归属
- 主客体关系
- 中文到英文
- 自然语言组织
- 复杂多人语义表达

LLM 不得修改确定性层。

---

## 9. LM Studio

本地 LLM 只支持 LM Studio。

需要支持：

- 获取模型列表
- 加载模型
- 推理
- 卸载模型
- 是否思考
- 思考强度（仅能力支持时）

配置保持简单：

- 名称
- Base URL
- API Key
- 模型
- Thinking
- Reasoning Effort
- Auto Load
- Auto Unload

能力不支持时，UI 应禁用，而不是假装支持。

---

## 10. ComfyUI

ComfyUI 是第一版唯一生图后端。

需要：

- 在线检测
- 模型列表
- LoRA 列表
- 系统状态
- Workflow 提交
- WebSocket 进度
- 结果读取
- 清晰错误反馈

第一版使用预设 Workflow Template。

---

## 11. 开发行为

每次修改前：

1. 阅读相关规格。
2. 理解现有实现。
3. 找最小改动点。
4. 不无故重构。
5. 不新增无明确价值依赖。
6. 修改后运行测试。

每次完成后汇报：

- 完成了什么
- 修改了哪些文件
- 为什么这样实现
- 做了什么验证
- 已知限制

---

## 12. 参考文件

详细规格不要塞回本文件。

请阅读：

- `docs/PRODUCT.md`
- `docs/PROMPT_ENGINE.md`
- `docs/GOLDEN_CASES.md`
- `docs/UI_SPEC.md`
- `docs/API_REFERENCES.md`
- `docs/ROADMAP.md`
