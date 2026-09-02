import json
import re
import logging
from typing import Optional, List, Dict, Any
from app.models.prompt_engine import SemanticFacts, Entity, Statement
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a strict semantic fact extractor for anime image generation prompts.
Your job is to read the user's input and extract ONLY explicitly mentioned entities and statements into a structured JSON object.

CRITICAL RULES:
1. FAITHFULNESS IS ABSOLUTE: Do NOT assume, infer, invent, or add ANY details the user did not explicitly state (no hair color, eye color, smile, lighting, classroom, weather, background, or pose unless mentioned).
2. DO NOT determine character origin. Just assign IDs ("c1", "c2", ...) and original names.
3. Translate descriptive actions, clothing, items, and attributes into accurate, concise English.
4. If a statement modifies or replaces an attribute (like wearing a swimsuit, ponytailed hair), set optional "facet" (e.g. "outfit", "hairstyle", "expression", "accessory") and optional "effect" ("replace", "add", "modify").
5. ACTIONS BELONG TO CHARACTERS: When a location or manner modifies an entity's action (e.g. "在沙滩上奔跑" -> "running on the beach", "坐在长椅上" -> "sitting on a bench"), assign it as an attribute/action of that character (subject="c1"), NOT as a global scene statement. Only pure background environment descriptions without character actions (e.g. "on a beach", "sunny day", "in a classroom") should have kind="scene".
6. ANONYMOUS/UNNAMED CHARACTERS: If the user mentions unnamed characters (e.g. "一个女孩", "另一个女孩", "一个男生", "一个人", "路人"), name them sequentially as "girl1", "girl2", "boy1", "boy2", "person1", "person2".
7. COMPLETED ITEM TRANSFER (完成式人物间物品转移): when the original sentence states an explicit final visual outcome for an item handed from one character to another — e.g. 把帽子戴到B头上 / 把围巾围到B脖子上 / 把外套披到B身上 / 把眼镜戴到B脸上 / 递给B且B接住 — you MUST emit BOTH:
   (a) a relation from source to target describing the transfer (kind="relation", subject=A, target=B, text like "putting the coat on c2"), AND
   (b) the target's final visual state as an attribute of B (kind="attribute", subject=B, text like "wearing the coat", facet="outfit", effect="add").
   The transient source action (taking off / removing) may additionally be kept as its own attribute of A.
8. IN-PROGRESS / UNCONFIRMED TRANSFER: when the original sentence describes an ongoing or attempted action whose outcome is NOT confirmed — e.g. 正在给B戴帽子 / 正准备把书递给B / 朝B递出一件外套 — emit ONLY the transfer action (relation or attribute). You MUST NOT invent that B is already wearing/holding the item. Do not add a target final state that the user did not confirm.
9. NEVER invent a final possession (wearing/holding) for a character when the sentence only describes an action toward them (handing, showing, offering).
10. Output ONLY valid JSON matching this schema:
{
  "entities": [
    { "id": "c1", "name": "林澄" },
    { "id": "c2", "name": "周遥" }
  ],
  "statements": [
    { "kind": "attribute", "subject": "c1", "text": "wearing a swimsuit", "facet": "outfit", "effect": "replace" },
    { "kind": "attribute", "subject": "c1", "text": "running on the beach" },
    { "kind": "attribute", "subject": "c2", "text": "wearing a blue sailor uniform", "facet": "outfit", "effect": "replace" },
    { "kind": "relation", "subject": "c1", "target": "c2", "text": "chasing" }
  ]
}

COMPLETED TRANSFER EXAMPLE — input "林澄把自己的外套脱下来，披到周遥身上。":
{
  "entities": [ { "id": "c1", "name": "林澄" }, { "id": "c2", "name": "周遥" } ],
  "statements": [
    { "kind": "attribute", "subject": "c1", "text": "taking off her coat", "facet": "outfit", "effect": "replace" },
    { "kind": "relation", "subject": "c1", "target": "c2", "text": "putting the coat on c2", "facet": null, "effect": null },
    { "kind": "attribute", "subject": "c2", "text": "wearing the coat", "facet": "outfit", "effect": "add" }
  ]
}

IN-PROGRESS TRANSFER EXAMPLE — input "林澄正在给周遥披外套。":
{
  "entities": [ { "id": "c1", "name": "林澄" }, { "id": "c2", "name": "周遥" } ],
  "statements": [
    { "kind": "relation", "subject": "c1", "target": "c2", "text": "putting the coat on c2" }
  ]
}
"""

class FactExtractor:
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider

    def _clean_json_response(self, raw_text: str) -> str:
        text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]
        return text

    async def extract(
        self,
        user_input: str,
        rules_context: Optional[str] = None,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = "instruct"
    ) -> SemanticFacts:
        if not user_input.strip():
            return SemanticFacts(entities=[], statements=[])

        if not self.llm_provider:
            raise RuntimeError("未配置或连接 LLM Provider，无法执行语义抽取")

        sys_content = EXTRACTION_SYSTEM_PROMPT
        if rules_context:
            sys_content += f"\n\nUser Guidelines / Reference:\n{rules_context}"

        messages = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": f"User Input: {user_input}\nRespond with JSON only:"}
        ]

        # Attempt 1
        try:
            raw_output = await self.llm_provider.chat(
                messages=messages,
                model=model,
                temperature=0.1,
                reasoning_effort=reasoning_effort
            )
            cleaned = self._clean_json_response(raw_output)
            data = json.loads(cleaned)
            entities = [Entity(**e) for e in data.get("entities", [])]
            statements = [Statement(**s) for s in data.get("statements", [])]
            return SemanticFacts(entities=entities, statements=statements)
        except Exception as e1:
            logger.warning(f"LLM extraction attempt 1 failed ({e1}). Retrying with explicit schema reminder...")

        # Attempt 2: Strict schema reminder
        retry_messages = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": f"User Input: {user_input}\nIMPORTANT: Output ONLY valid JSON object with keys 'entities' and 'statements'. Translate descriptive actions into concise English statements. Do not output thinking tags or explanations."}
        ]
        try:
            raw_output = await self.llm_provider.chat(
                messages=retry_messages,
                model=model,
                temperature=0.1,
                reasoning_effort=reasoning_effort
            )
            cleaned = self._clean_json_response(raw_output)
            data = json.loads(cleaned)
            entities = [Entity(**e) for e in data.get("entities", [])]
            statements = [Statement(**s) for s in data.get("statements", [])]
            return SemanticFacts(entities=entities, statements=statements)
        except Exception as e2:
            raise RuntimeError(f"语义事实抽取失败: LLM 输出未能解析为有效结构化 JSON ({str(e2)})")
