# Prompt Engine 规格

## 1. 设计目标

Prompt Engine 要解决的不是“写得更华丽”，而是：

1. 正确理解用户。
2. 正确区分人物。
3. 正确绑定人物属性。
4. 正确表达动作主客体。
5. 利用 Anima 的 tag + natural language 混合能力。
6. 尽量避免 LLM 自由脑补。

---

## 2. Anima 使用原则

Anima 不是纯 tag 模型。

产品应该利用：

- Danbooru/Gelbooru 类 tag
- 自然语言 caption
- 二者混合

基本策略：

### Tag
负责：

- quality
- safety
- count
- character trigger
- series
- artist
- general tags
- LoRA trigger

### Natural language
负责：

- attribute ownership
- action ownership
- subject/object relation
- spatial relation
- multi-character interaction
- complex scene semantics

这是系统设计原则，不是简单的“多人全部改自然语言”。

---

## 3. 为什么多人不能纯 Tag Soup

用户：

> 穗穗穿泳装，秧秧穿蓝色海军水手服，穗穗追秧秧。

坏结果：

```text
2girls, suisui, yangyang, swimsuit, blue sailor uniform, chasing
```

问题：

- swimsuit 属于谁不明确。
- blue sailor uniform 属于谁不明确。
- chasing 的主体不明确。

更合理：

```text
<quality tags>, 2girls, <suisui_trigger>, <yangyang_trigger>.
Suisui is wearing a swimsuit and chasing Yangyang.
Yangyang is wearing a blue sailor uniform and running away from Suisui.
```

---

## 4. 角色解析

### 4.1 角色书命中
用户角色书存在同名或明确 alias。

系统：

```text
source = user_defined
```

名字仅内部使用。

展开设定。

例：

角色书：

- 小夏
- long black hair
- green eyes
- petite
- white blouse
- black pleated skirt

用户：

> 小夏穿泳装。

最终概念：

```text
a petite young woman with long black hair and green eyes, wearing a swimsuit
```

默认服装被当前用户要求覆盖。

### 4.2 角色书未命中
系统：

```text
source = model_character
```

行为：

- Resolver 解析 canonical trigger。
- 不自动展开角色原始外貌。
- 当前用户属性追加。

例：

> 穗穗把头发扎成马尾，穿泳装。

最终要表达：

- canonical Suisui trigger
- ponytail
- swimsuit

不要额外补默认发色、眼睛、原作服装。

---

## 5. Trigger Resolver

职责只有：

```text
用户名称 → canonical Anima character trigger
```

允许：

- LLM 提议
- 用户查看
- 用户手动修改
- 保存缓存
- 已手工验证项优先

不得：

- 生成完整角色设定
- 自动补原作服装
- 自动补外貌

如果 Resolver 不确定：

- 允许输出候选。
- UI 应让用户修改。
- 不要自行虚构大量附加 tag。

---

## 6. 中间语义表示

目标：

- 弱模型容易输出
- 后端容易校验
- 新语义无需扩 schema
- 保留人物归属

推荐：

```json
{
  "entities": [
    {
      "id": "c1",
      "kind": "character",
      "name": "穗穗",
      "source": "model_character"
    }
  ],
  "statements": [
    {
      "kind": "attribute",
      "subject": "c1",
      "text": "wearing a swimsuit"
    }
  ]
}
```

关系：

```json
{
  "kind": "relation",
  "subject": "c1",
  "target": "c2",
  "text": "chasing"
}
```

场景可作为 entity 或 statement：

```json
{
  "kind": "scene",
  "text": "on a beach"
}
```

---

## 7. 为什么不用大固定 Schema

不要做：

```json
{
  "hair": "",
  "eyes": "",
  "outfit": "",
  "expression": "",
  "camera": "",
  "lighting": "",
  "weather": "",
  "pose": ""
}
```

原因：

- 用户没说时，LLM 会为了填字段而脑补。
- 每遇到新概念就想加字段。
- 新动作和奇怪场景扩展困难。

中间层只固定“实体和陈述的结构”，不固定世界中所有可能概念。

---

## 8. Statement 的开放性

允许：

```text
wearing a swimsuit
holding a baseball bat
looking back at
trying to grab an umbrella from
running away from
covered in mud
riding the same horse as
falling from a balcony
```

Prompt Compiler 不需要理解每一种现实动作。

它只需要知道：

- statement 是谁的
- 是否有 target
- statement 本身的英文语义

---

## 9. LLM 输出校验

至少校验：

1. 所有 `subject` 必须存在。
2. 所有 `target` 必须存在。
3. 不允许凭空增加角色。
4. 不允许 LLM 修改 Safe / NSFW。
5. 不允许 LLM 加用户没选择的 Artist。
6. 不允许 LLM 加用户没选择的 LoRA。
7. 原生角色不能被自动展开额外外貌。
8. 自定义角色不能偷偷变成 character trigger。

---

## 10. Prompt Writer

职责：

- 将中间事实组织成清晰英文。
- 优先保持 attribute ownership。
- 优先保持 relation subject/object。
- 适合 tag 的内容保留 tag。
- 复杂关系改为英文自然语言。

Prompt Writer 可以调整语法，不可以修改事实。

---

## 11. 确定性注入顺序

推荐逻辑：

1. quality / meta
2. safety
3. character count
4. model character triggers
5. series
6. artist tags
7. general stable tags
8. natural language relationship / ownership
9. LoRA triggers
10. 用户规则要求

不要把这个顺序写死到难以修改；应集中在一个可测试的 Prompt Policy 中。

---

## 12. Negative Prompt

第一版不要让 LLM 自由生成很长的 Negative Prompt。

建议：

- 基础模型默认 Negative
- 用户额外 Negative
- 必要的多人混淆防护词

合并后可预览。

---

## 13. 忠实模式

默认要求 LLM：

> 只抽取用户明确表达的事实，不推断视觉设定，不自行增强画面。

例：

输入：

> 穗穗坐着。

允许：

```text
Suisui is sitting.
```

不允许自动加入：

```text
smiling
classroom
sunlight
school uniform
looking at viewer
```

---

## 14. 未来创意模式

以后可以增加一个显式开关：

```text
创意补全：关闭 / 开启
```

只有开启时，LLM 才可以增加合理的非核心视觉细节。

这属于后续功能，不应影响 MVP 的忠实模式设计。
