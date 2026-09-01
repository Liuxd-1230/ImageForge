from typing import List, Dict
from app.models.prompt_engine import SemanticFacts, Entity, Statement

class PromptWriter:
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
            subj_name = entity.caption_name
            if not subj_name:
                subj_name = entity.canonical_tag or "the character"

            actions: List[str] = []
            for s in stmts:
                text = s.text.strip()
                if s.kind == "relation" and s.target and s.target in entity_by_id:
                    target_entity = entity_by_id[s.target]
                    target_name = target_entity.caption_name or target_entity.canonical_tag or "the other character"
                    # Make sure relation text mentions target if not already
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

        # Scene and general statements
        for s in scene_statements:
            text = s.text.strip()
            if text:
                sentence_parts.append(text)
                
        for s in general_statements:
            text = s.text.strip()
            if text:
                sentence_parts.append(text)

        # Join into sentences
        final_nl = ". ".join([p.rstrip(".") for p in sentence_parts if p])
        if final_nl and not final_nl.endswith("."):
            final_nl += "."
        return final_nl
