from typing import List, Dict
import re
from app.models.prompt_engine import SemanticFacts, Entity, Statement

class PromptWriter:
    @staticmethod
    def _display_name(entity: Entity) -> str:
        """可读名称优先级：caption_name → canonical_tag → entity.name → the character"""
        return entity.caption_name or entity.canonical_tag or entity.name or "the character"

    @staticmethod
    def resolve_entity_refs(text: str, entity_by_id: Dict[str, Entity]) -> str:
        """把 Statement.text 中的内部实体引用（c1/c2/...）替换为可读名称。

        - token/boundary-aware（\b...\b），避免 c1 误匹配 c10 / abc1；
        - 已知 ID 按长度降序处理，长 ID 先替换；
        - 只替换 entity_by_id 中真实存在的 ID；未知 ID（c99）保留原样，
          让 validator / benchmark 继续暴露异常。
        - 只影响最终 rendering，不改动 facts 本身。
        """
        if not text or not entity_by_id:
            return text
        known_ids = sorted((str(k) for k in entity_by_id if k), key=len, reverse=True)
        result = text
        for eid in known_ids:
            ent = entity_by_id[eid]
            if not ent:
                continue
            name = PromptWriter._display_name(ent)
            result = re.sub(rf"\b{re.escape(eid)}\b", name, result)
        return result

    def write_natural_language_scene(self, facts: SemanticFacts) -> str:
        """Transforms statements into natural language scene sentences preserving attribute & action ownership."""
        if not facts.statements and not facts.entities:
            return ""

        entity_by_id: Dict[str, Entity] = {e.id: e for e in facts.entities}
        
        # Group statements
        char_statements: Dict[str, List[Statement]] = {e.id: [] for e in facts.entities}
        scene_statements: List[Statement] = []
        general_statements: List[Statement] = []

        for s in facts.statements:
            if s.kind == "scene":
                scene_statements.append(s)
            elif s.kind == "general":
                general_statements.append(s)
            elif s.subject and s.subject in char_statements:
                char_statements[s.subject].append(s)
            else:
                scene_statements.append(s)

        sentence_parts: List[str] = []

        # Process each character's actions/attributes
        for e_id, entity in entity_by_id.items():
            stmts = char_statements.get(e_id, [])
            if not stmts:
                continue

            # Determine subject name in natural language
            subj_name = PromptWriter._display_name(entity)

            actions: List[str] = []
            for s in stmts:
                # 统一先解析已知实体引用（c1/c2 → 可读名称），再决定是否追加 target
                text = PromptWriter.resolve_entity_refs(s.text.strip(), entity_by_id)
                if s.kind == "relation" and s.target and s.target in entity_by_id:
                    target_entity = entity_by_id[s.target]
                    target_name = PromptWriter._display_name(target_entity)
                    # 替换后文本已含 target 名则不再追加（避免 "… Suisui Suisui"）
                    if target_name.lower() not in text.lower():
                        actions.append(f"{text} {target_name}")
                    else:
                        actions.append(text)
                else:
                    actions.append(text)

            if actions:
                # Formulate natural sentence
                joined_actions = " and ".join(actions)
                # If actions start with "wearing" or "sitting" or "chasing", prefix with "is"
                first_word = joined_actions.split()[0].lower() if joined_actions else ""
                if first_word.endswith("ing") or first_word in ["angry", "smiling", "happy", "sad"]:
                    sentence_parts.append(f"{subj_name} is {joined_actions}")
                else:
                    sentence_parts.append(f"{subj_name} {joined_actions}")

        # Scene and general statements（同样解析实体引用）
        for s in scene_statements:
            text = PromptWriter.resolve_entity_refs(s.text.strip(), entity_by_id)
            if text:
                sentence_parts.append(text)
                
        for s in general_statements:
            text = PromptWriter.resolve_entity_refs(s.text.strip(), entity_by_id)
            if text:
                sentence_parts.append(text)

        # Join into sentences
        final_nl = ". ".join([p.rstrip(".") for p in sentence_parts if p])
        if final_nl and not final_nl.endswith("."):
            final_nl += "."
        return final_nl
