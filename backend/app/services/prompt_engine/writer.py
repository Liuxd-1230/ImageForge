from typing import List, Dict, Tuple, Optional, Set
import re
from app.models.prompt_engine import SemanticFacts, Entity, Statement

# ─────────────────────────────────────────────────────────────────────────────
# Static visual-state rendering：完成式物品转移的瞬态抑制（Candidate C）
#
# 只有当同一物体同时存在：
#   ① source-side transient removal（A: taking off X）
#   ② source → target transfer（A → B: putting X on ...）
#   ③ target final possession（B: wearing/holding X）
# 时才把 ① 视为被 ②③ 覆盖的冗余瞬态，仅从最终渲染中抑制；facts 保持原样。
# 不是关键词删句器：单独的 "taking off hat" 依然保留。
# ─────────────────────────────────────────────────────────────────────────────

_OBJECT_TOKEN = r"(?:the |a |an |my |her |his |their |our )?([a-z][a-z\- ]+?)"


def _canon_object(text: str) -> str:
    """规范化物体名词：去冠词/属格，取名词头（末词）。"""
    t = (text or "").strip().lower().strip(".,;'\"!?")
    while True:
        m = re.match(r"^(?:the|a|an|my|her|his|their|our|your)\s+", t)
        if m:
            t = t[m.end():]
            continue
        break
    words = [w for w in t.split() if w]
    return words[-1] if words else ""


def _removal_object(text: str) -> Optional[str]:
    """提取移除瞬态语句中的物体（taking X off / taking off X / removing X / untying X）。"""
    t = (text or "").lower().strip().rstrip(".")
    # remove/removes/removing/untie/unties/untying/undo/undoing 不需要 off
    # （不含 slip：'slipping on X' 是 put-on 语义，避免误判）
    m = re.search(rf"\b(?:remove|removes|removing|untie|unties|untying|undo|undoing)\s+{_OBJECT_TOKEN}(?:$|[,.;]| and |\bwhile\b)", t)
    if m:
        return _canon_object(m.group(1))
    m = re.search(rf"\b(?:take|takes|taking|pull|pulls|pulling)\s+{_OBJECT_TOKEN}\s+off\b", t)
    if m:
        return _canon_object(m.group(1))
    m = re.search(rf"\b(?:take|takes|taking|pull|pulls|pulling)\s+off\s+{_OBJECT_TOKEN}(?:$|[,.;]| and |\bwhile\b)", t)
    if m:
        return _canon_object(m.group(1))
    return None


def _transfer_object(text: str) -> Optional[str]:
    """提取转移动作中的物体（putting X on/onto/to / handing/passing X to / wrapping X around）。"""
    t = (text or "").lower().strip().rstrip(".")
    m = re.search(rf"\b(?:put|puts|putting|place|places|placing|hand|hands|handing|give|gives|giving|pass|passes|passing|wrap|wraps|wrapping|set|sets|setting)\s+{_OBJECT_TOKEN}\s+(?:on|onto|to|around)\b", t)
    if m:
        return _canon_object(m.group(1))
    return None


def _possession_object(text: str) -> Optional[str]:
    """提取最终持有/穿戴语句中的物体（wearing/holding/carrying/catching X, with X）。
    物体后若带地点/细节短语（on/at/over/in ...）只取物品名词本身。"""
    t = (text or "").lower().strip().rstrip(".")
    term = r"(?:$|[,.;]| and |\bwhile\b|\bon\b|\bonto\b|\bat\b|\bover\b|\bin\b|\bwith\b)"
    for verb in ("wearing", "wear", "holding", "hold", "carrying", "carry", "catching", "catch", "receiving", "receive"):
        m = re.search(rf"\b{verb}\s+{_OBJECT_TOKEN}{term}", t)
        if m:
            return _canon_object(m.group(1))
    m = re.search(rf"\bwith\s+{_OBJECT_TOKEN}{term}", t)
    if m:
        return _canon_object(m.group(1))
    return None


def compute_transient_suppression(entity_by_id: Dict[str, Entity], char_statements: Dict[str, List[Statement]]) -> Set[Tuple[str, int]]:
    """返回需要抑制渲染的 (entity_id, stmt_index)。仅当 移除+转移+目标最终态 三件套
    覆盖同一物体时抑制 source-side 瞬态；facts 本身不变。"""
    suppress: Set[Tuple[str, int]] = set()
    for a_id in entity_by_id:
        stmts = char_statements.get(a_id, [])
        # A 发出的转移（关系 target=B，或 attribute 文本引用另一实体 B）
        transfers: List[Tuple[int, str, str]] = []
        for idx, s in enumerate(stmts):
            if s.kind == "relation" and s.target and s.target in entity_by_id:
                obj = _transfer_object(s.text or "")
                if obj:
                    transfers.append((idx, obj, s.target))
            elif s.subject == a_id:
                for b_id in entity_by_id:
                    if b_id == a_id or not b_id:
                        continue
                    if re.search(rf"\b{re.escape(str(b_id))}\b", s.text or ""):
                        obj = _transfer_object(s.text or "")
                        if obj:
                            transfers.append((idx, obj, b_id))
                        break
        for idx, s in enumerate(stmts):
            ro = _removal_object(s.text or "")
            if not ro:
                continue
            for _t_idx, to, b_id in transfers:
                if to != ro:
                    continue
                if any(_possession_object(bs.text or "") == ro for bs in char_statements.get(b_id, [])):
                    suppress.add((a_id, idx))
                    break
    return suppress


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

        # 结构组合式瞬态抑制：仅当 移除+转移+目标最终态 覆盖同一物体时（Candidate C）
        suppress = compute_transient_suppression(entity_by_id, char_statements)

        sentence_parts: List[str] = []

        # Process each character's actions/attributes
        for e_id, entity in entity_by_id.items():
            stmts = char_statements.get(e_id, [])
            if not stmts:
                continue

            # Determine subject name in natural language
            subj_name = PromptWriter._display_name(entity)

            actions: List[str] = []
            for s_idx, s in enumerate(stmts):
                if (e_id, s_idx) in suppress:
                    continue  # source-side transient removal 已被最终态覆盖，不渲染
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
