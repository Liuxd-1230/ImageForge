# Golden Cases — Prompt Engine 验收案例

这些案例既是产品示例，也是自动化测试与 Agent 验收标准。

---

## Case 1：单个模型角色

输入：

> 穗穗穿着泳装。

角色书：

- 无“穗穗”

应理解：

```text
穗穗 = model_character
穗穗 → wearing a swimsuit
```

必须：

- 使用 canonical trigger。
- 加 swimsuit。

禁止：

- 自动补发色
- 自动补眼睛
- 自动补身材
- 自动补背景
- 自动补表情

---

## Case 2：两个模型角色 + 服装归属 + 动作

输入：

> 穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗追逐秧秧。

正确语义：

```text
穗穗 → wearing a swimsuit
秧秧 → wearing a blue sailor uniform
穗穗 → chasing → 秧秧
```

最终形态应类似：

```text
<quality/safety tags>, 2girls, <suisui_trigger>, <yangyang_trigger>.
Suisui is wearing a swimsuit and chasing Yangyang.
Yangyang is wearing a blue sailor uniform and running away from Suisui.
```

禁止：

```text
2girls, swimsuit, blue sailor uniform, chasing
```

作为唯一多人表达。

---

## Case 3：自定义角色

角色书：

```text
小夏
young adult woman
petite
long black hair
green eyes
white blouse
black pleated skirt
```

输入：

> 小夏坐在长椅上。

正确：

- 不使用“小夏”作为 Anima character tag。
- 展开角色书外观。
- 保留默认服装。
- 加 sitting on a bench。

---

## Case 4：当前服装覆盖角色书服装

角色书同 Case 3。

输入：

> 小夏穿泳装站在泳池边。

正确：

- long black hair
- green eyes
- petite
- swimsuit
- standing by a swimming pool

禁止同时保留：

- white blouse
- black pleated skirt

---

## Case 5：模型角色 + 自定义角色

角色书：

- 小夏已存在

输入：

> 穗穗追着穿黄色雨衣的小夏跑。

正确：

```text
穗穗 = model_character
小夏 = user_defined
穗穗 → chasing → 小夏
小夏 → wearing a yellow raincoat
```

两类角色允许使用不同表达策略。

---

## Case 6：用户修改模型角色外观

输入：

> 穗穗今天把头发扎成马尾，穿泳装。

正确：

- canonical trigger
- ponytail
- swimsuit

禁止：

因为“模型本来认识她”就忽略用户修改。

---

## Case 7：复杂新动作无需改 Schema

输入：

> 穗穗把手里的冰淇淋扔向正在骑自行车逃跑的秧秧。

系统必须可以表达：

- 穗穗 holding ice cream
- 穗穗 throwing ice cream toward 秧秧
- 秧秧 riding a bicycle
- 秧秧 running/escaping from 穗穗

不得因为系统没有专门的 `icecream_throw` 字段而失败。

---

## Case 8：最小输入

输入：

> 穗穗坐着。

结果只需要表达：

- 角色身份
- sitting

禁止自动加入：

- smiling
- school uniform
- classroom
- sunset
- looking at viewer

---

## Case 9：场景

输入：

> 穗穗和秧秧在沙滩上。

正确：

- 两角色
- scene: on a beach

没有动作时不要发明动作。

---

## Case 10：表情归属

输入：

> 穗穗生气地看着正在笑的秧秧。

正确：

```text
穗穗 → angry
穗穗 → looking at → 秧秧
秧秧 → smiling
```

禁止交换表情。

---

## Case 11：道具归属

输入：

> 穗穗拿着棒球棍，秧秧拿着雨伞。

正确：

- baseball bat 属于穗穗
- umbrella 属于秧秧

禁止纯粹输出：

```text
baseball bat, umbrella
```

而不表达 ownership。

---

## Case 12：Safe / NSFW

用户选择：

```text
Safe
```

LLM 无论如何都不得修改为 NSFW。

用户选择：

```text
NSFW
```

LLM也不得自行改回 Safe。

这是程序状态，不是 LLM 推断。

---

## Case 13：Artist

用户没有选择 Artist。

最终 Prompt 禁止自动出现 artist tag。

用户选择某 Artist 后：

- 编译器确定性注入。
- 不由 LLM 决定。

---

## Case 14：LoRA

用户启用：

```text
LoRA A
trigger = abc_trigger
strength = 0.8
```

最终：

- Prompt 出现 `abc_trigger`
- ComfyUI Workflow 使用 strength 0.8

关闭后两者都不应继续生效。

---

## Case 15：Trigger 手动修正

首次 Resolver：

```text
穗穗 → trigger_A
```

用户修正为：

```text
trigger_B
```

保存后再次输入“穗穗”：

必须优先使用 `trigger_B`。

---

## Case 16：未知于 Agent，但用户认为模型已训练

用户输入一个 Agent 自己不认识的角色名。

角色书没有记录。

正确行为：

- 不阻止。
- 不要求建立角色书。
- 尝试 Resolver。
- 允许用户手动修正 trigger。

错误行为：

> “我不知道这个角色，所以请先填写角色卡。”

---

## Case 17：多个复杂关系

输入：

> 穗穗站在秧秧后面，用一只手抓住秧秧的帽子，秧秧回头看她。

必须保留：

- 穗穗 behind 秧秧
- 穗穗 grabbing 秧秧's hat
- 秧秧 looking back at 穗穗

不得把关系压扁成：

```text
behind, hat, looking back
```

---

## Case 18：自由补全默认关闭

输入：

> 两人在雨里跑。

系统没有用户角色信息之外的额外视觉要求时：

不要自行加入：

- neon city
- cinematic lighting
- crying
- dramatic backlight

除非未来“创意补全”明确开启。
