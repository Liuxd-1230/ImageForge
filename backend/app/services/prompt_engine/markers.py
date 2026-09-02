"""显式角色标记 pre-parser：`<角色名>`。

纯确定性、无 LLM。把尖括号中的文本识别为“需要 Character Resolver / Trigger Cache
处理的具名角色”，并剥离尖括号后再进入 Fact Extraction。

合同：
- 识别 `<非空名称>`，支持一条输入多个
- strip 前后空格、去重
- 名称最大 64 字符
- 禁止嵌套 `<>`；含换行不识别
- 含结构控制符（`:` `(` `)` `[` `]` `=` `,` `/` `\`）不识别
  → `<lora:xxx:1>` 等已有 Prompt/LoRA 语法不会被误认为角色
- 其余 `<...>` 原样保留（不剥离）
"""
from __future__ import annotations

import re
from typing import List, Tuple

MAX_NAME_LEN = 64
_NAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff\u3040-\u30ff \-]{1,64}$")
_CONTROL_CHARS = set(":()[]=,<>/\\")


def _is_valid_name(name: str) -> bool:
    if not name or len(name) > MAX_NAME_LEN:
        return False
    if any(c in _CONTROL_CHARS for c in name):
        return False
    return bool(_NAME_RE.match(name))


def parse_explicit_markers(raw: str) -> Tuple[str, List[str]]:
    """Return (clean_text_without_angle_brackets, ordered_deduped_names)."""
    if not raw:
        return raw or "", []
    out: List[str] = []
    names: List[str] = []
    seen = set()
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if ch != "<":
            out.append(ch)
            i += 1
            continue
        j = raw.find(">", i + 1)
        if j == -1:
            out.append(raw[i:])
            break
        inner = raw[i + 1:j]
        # 含换行 / 嵌套 `<>` → 不是角色标记，原样保留
        if "\n" in inner or "<" in inner or ">" in inner:
            out.append(raw[i:j + 1])
            i = j + 1
            continue
        name = inner.strip()
        if name and _is_valid_name(name):
            if name not in seen:
                seen.add(name)
                names.append(name)
            out.append(name)  # 剥掉尖括号，名称本体回到 clean_text
            i = j + 1
            continue
        out.append(raw[i:j + 1])
        i = j + 1
    return "".join(out), names