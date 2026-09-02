# Prompt Benchmark

ImageForge Prompt Engine 的**语义正确性**基准测试（不是"好不好看"评估）。

## 原则

- 输入是**真实中文创作描述**，不为了测试方便改写成结构化语言。
- 每个案例记录**预期语义**（实体 + 必须出现的属性 + 关系 + 禁止绑定），
  而不是唯一 Prompt 字符串——因为 Prompt Writer 允许有多个正确答案。
- 自动检查只用**确定性规则**（实体数量、属性绑定、禁止绑定、未解析 trigger、
  来源、Artist/LoRA/Safety 注入、未指定属性不得脑补），**不用 LLM 自评打分**。
- 自由文案质量由人工复核。

## 文件

- `prompt_cases.json` — 25 个案例（单/多人物、角色书、动作主客体、场景、
  镜头/光照/表情、Artist、LoRA、Safety 四档、覆盖角色书默认、未指定不脑补、复杂长句）。
- `run_benchmark.py` — 运行器：每个案例跑完整流水线并分阶段记录
  `FACT EXTRACTION → CHARACTER RESOLUTION → FINAL FACTS → PROMPT ASSEMBLY`。
- `results/<timestamp>.json / .md` — 运行结果与失败阶段定位。

## 运行

```bash
# 需要 LM Studio 在跑并已加载模型
PYTHONPATH=backend python benchmark/run_benchmark.py
```

## 如何用

1. 当前版本先跑出 **Baseline A**，保存结果。
2. 分析失败集中在哪个阶段/哪类问题（例如"双人属性绑定错误"）。
3. **只针对那类问题修改**后跑 **Candidate B**，对比 A vs B：
   目标问题变好、其他类别没有退化。
4. 禁止：改 Prompt → 看两条样例不错 → 宣布提升。

## 待办（Roadmap，本轮不实现）

- Civitai / Civitai Red LoRA metadata、LoRA cover cache
- Artist 网络抓取 / community import pack
- Workflow Mapper / 节点可视化 / Placeholder mapping / 动态 LoRA slot editor
