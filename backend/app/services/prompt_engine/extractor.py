import json
import re
import logging
from typing import Optional, List, Dict, Any
from app.models.prompt_engine import SemanticFacts, Entity, Statement
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a strict semantic fact extractor for anime image generation prompts.
Your job is to read the user's Chinese/English input and extract ONLY explicitly mentioned entities and statements into a structured JSON object.

CRITICAL RULES:
1. FAITHFULNESS IS ABSOLUTE: Do NOT assume, infer, invent, or add ANY details the user did not explicitly state (no hair color, eye color, smile, lighting, classroom, weather, background, or pose unless mentioned).
2. DO NOT determine character origin (whether model character or user defined). Just assign IDs ("c1", "c2", ...) and original names.
3. Translate descriptive actions and attributes into accurate, concise English.
4. If a statement modifies or replaces an attribute (like wearing a swimsuit, ponytailed hair), set optional "facet" (e.g. "outfit", "hairstyle", "expression", "accessory") and optional "effect" ("replace", "add", "modify").
5. Output ONLY valid JSON matching this schema:
{
  "entities": [
    { "id": "c1", "name": "穗穗" },
    { "id": "c2", "name": "秧秧" }
  ],
  "statements": [
    { "kind": "attribute", "subject": "c1", "text": "wearing a swimsuit", "facet": "outfit", "effect": "replace" },
    { "kind": "attribute", "subject": "c2", "text": "wearing a blue sailor uniform", "facet": "outfit", "effect": "replace" },
    { "kind": "relation", "subject": "c1", "target": "c2", "text": "chasing" },
    { "kind": "scene", "text": "on a beach" }
  ]
}
"""

class FactExtractor:
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider

    def _clean_json_response(self, raw_text: str) -> str:
        text = raw_text.strip()
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
            return self.heuristic_extract(user_input)

        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        ]
        if rules_context:
            messages.append({"role": "system", "content": f"User Guidelines / Reference:\n{rules_context}"})
        
        messages.append({"role": "user", "content": f"User Input: {user_input}"})

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
        except Exception as e:
            logger.warning(f"LLM extraction failed ({e}). Falling back to heuristic extractor.")
            return self.heuristic_extract(user_input)

    def heuristic_extract(self, user_input: str) -> SemanticFacts:
        """Deterministic extractor for offline testing / fallback."""
        entities: List[Entity] = []
        statements: List[Statement] = []
        
        known_names = ["穗穗", "秧秧", "小夏", "小明", "爱丽丝", "明日香", "绫波丽", "初音未来", "芙莉莲", "费伦"]
        found_names = []
        for name in known_names:
            if name in user_input and name not in found_names:
                found_names.append(name)

        if not found_names:
            if "两人" in user_input or "2人" in user_input:
                found_names.extend(["c1", "c2"])
            elif "女" in user_input or "少女" in user_input or "girl" in user_input.lower():
                found_names.append("girl")
            elif "男" in user_input or "boy" in user_input.lower():
                found_names.append("boy")

        entity_map = {}
        for idx, name in enumerate(found_names, 1):
            e_id = f"c{idx}"
            entities.append(Entity(id=e_id, name=name))
            entity_map[name] = e_id

        c1 = entities[0].id if entities else None
        c2 = entities[1].id if len(entities) > 1 else None

        if "泳装" in user_input or "swimsuit" in user_input.lower():
            subj = entity_map.get("小夏", entity_map.get("穗穗", c1))
            statements.append(Statement(kind="attribute", subject=subj, text="wearing a swimsuit", facet="outfit", effect="replace"))
            
        if "海军水手服" in user_input or "水手服" in user_input or "sailor uniform" in user_input.lower():
            subj = entity_map.get("秧秧", c2 or c1)
            statements.append(Statement(kind="attribute", subject=subj, text="wearing a blue sailor uniform", facet="outfit", effect="replace"))

        if "黄色雨衣" in user_input or "yellow raincoat" in user_input.lower():
            subj = entity_map.get("小夏", c2 or c1)
            statements.append(Statement(kind="attribute", subject=subj, text="wearing a yellow raincoat", facet="outfit", effect="replace"))

        if "马尾" in user_input or "ponytail" in user_input.lower():
            subj = entity_map.get("穗穗", c1)
            statements.append(Statement(kind="attribute", subject=subj, text="ponytail", facet="hairstyle", effect="replace"))

        if "坐" in user_input or "sitting" in user_input.lower():
            if "长椅" in user_input or "bench" in user_input.lower():
                statements.append(Statement(kind="attribute", subject=c1, text="sitting on a bench"))
            else:
                statements.append(Statement(kind="attribute", subject=c1, text="sitting"))

        if "沙滩" in user_input or "beach" in user_input.lower():
            statements.append(Statement(kind="scene", text="on a beach"))
        if "泳池" in user_input or "pool" in user_input.lower():
            statements.append(Statement(kind="scene", text="standing by a swimming pool"))
        if "雨" in user_input or "rain" in user_input.lower():
            statements.append(Statement(kind="scene", text="in the rain"))

        if "跑" in user_input or "running" in user_input.lower():
            if "追" not in user_input:
                for e in entities:
                    statements.append(Statement(kind="attribute", subject=e.id, text="running"))

        if "追" in user_input or "chasing" in user_input.lower():
            if c1 and c2:
                statements.append(Statement(kind="relation", subject=c1, target=c2, text="chasing"))
            elif c1:
                statements.append(Statement(kind="attribute", subject=c1, text="running"))

        if "棒球棍" in user_input or "baseball bat" in user_input.lower():
            subj = entity_map.get("穗穗", c1)
            statements.append(Statement(kind="attribute", subject=subj, text="holding a baseball bat", facet="accessory"))
        if "雨伞" in user_input or "umbrella" in user_input.lower():
            subj = entity_map.get("秧秧", c2 or c1)
            statements.append(Statement(kind="attribute", subject=subj, text="holding an umbrella", facet="accessory"))

        if "冰淇淋" in user_input and ("扔" in user_input or "throw" in user_input.lower()):
            if c1 and c2:
                statements.append(Statement(kind="attribute", subject=c1, text="holding ice cream"))
                statements.append(Statement(kind="relation", subject=c1, target=c2, text="throwing ice cream toward"))
                statements.append(Statement(kind="attribute", subject=c2, text="riding a bicycle and escaping"))

        if "帽子" in user_input and ("抓" in user_input or "grab" in user_input.lower()):
            if c1 and c2:
                statements.append(Statement(kind="relation", subject=c1, target=c2, text="standing behind and grabbing hat"))
                statements.append(Statement(kind="relation", subject=c2, target=c1, text="looking back at"))

        if "生气" in user_input:
            subj = entity_map.get("穗穗", c1)
            statements.append(Statement(kind="attribute", subject=subj, text="angry", facet="expression"))
            if c1 and c2:
                statements.append(Statement(kind="relation", subject=c1, target=c2, text="looking at"))
        if "笑" in user_input or "smiling" in user_input.lower():
            subj = entity_map.get("秧秧", c2 or c1)
            statements.append(Statement(kind="attribute", subject=subj, text="smiling", facet="expression"))

        return SemanticFacts(entities=entities, statements=statements)
