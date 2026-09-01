import pytest
import asyncio
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.preset import Preset
from app.models.lora import Lora
from app.models.prompt_engine import (
    SemanticFacts,
    Entity,
    Statement,
    PromptBuildRequest,
    LoraBuildItem
)
from app.services.prompt_engine.pipeline import PromptPipeline

@pytest.fixture
def session():
    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as sess:
        preset = Preset(
            name="Standard",
            positive_prefix="",
            default_negative="lowres, bad anatomy, bad hands, text",
            default_safety="Safe",
            is_default=True
        )
        sess.add(preset)
        
        # Test character trigger cache fixtures
        sess.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui", caption_name="Suisui (girl)"))
        sess.add(CharacterTriggerCache(name="秧秧", canonical_tag="yangyang", caption_name="Yangyang (girl)"))
        sess.commit()
        yield sess

def test_case_01_single_model_character(session: Session):
    """Case 1: 单个模型角色 (穗穗穿着泳装)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗")],
        statements=[Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "wearing a swimsuit" in res.prompt
    assert "1girl" in res.prompt
    assert "smiling" not in res.prompt
    assert "classroom" not in res.prompt

def test_case_02_two_model_characters_with_ownership_and_actions(session: Session):
    """Case 2: 两个模型角色 + 服装归属 + 动作 (穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗追逐秧秧)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[
            Entity(id="c1", name="穗穗"),
            Entity(id="c2", name="秧秧")
        ],
        statements=[
            Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace"),
            Statement(kind="attribute", subject="c2", text="wearing a blue sailor uniform", facet="outfit", effect="replace"),
            Statement(kind="relation", subject="c1", target="c2", text="chasing")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "2girls" in res.prompt
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "Suisui (girl) is wearing a swimsuit and chasing Yangyang (girl)" in res.prompt
    assert "Yangyang (girl) is wearing a blue sailor uniform" in res.prompt

def test_case_03_custom_character(session: Session):
    """Case 3: 自定义角色小夏 (小夏坐在长椅上)"""
    char = Character(
        name="小夏",
        age_group="young adult",
        body="petite",
        gender="woman",
        hair_color="black",
        hair_style="straight",
        hair_length="long",
        eye_color="green",
        top="white blouse",
        bottom="black pleated skirt"
    )
    session.add(char)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="小夏")],
        statements=[Statement(kind="attribute", subject="c1", text="sitting on a bench")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "小夏" not in res.prompt
    assert "long straight black hair" in res.prompt
    assert "green eyes" in res.prompt
    assert "white blouse" in res.prompt
    assert "black pleated skirt" in res.prompt
    assert "sitting on a bench" in res.prompt

def test_case_04_outfit_override(session: Session):
    """Case 4: 当前服装覆盖角色书服装 (小夏穿泳装站在泳池边)"""
    char = Character(
        name="小夏",
        age_group="young adult",
        body="petite",
        gender="woman",
        hair_color="black",
        hair_style="straight",
        hair_length="long",
        eye_color="green",
        top="white blouse",
        bottom="black pleated skirt"
    )
    session.add(char)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="小夏")],
        statements=[
            Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace"),
            Statement(kind="scene", text="standing by a swimming pool")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "long straight black hair" in res.prompt
    assert "green eyes" in res.prompt
    assert "swimsuit" in res.prompt
    assert "white blouse" not in res.prompt
    assert "black pleated skirt" not in res.prompt
    assert "standing by a swimming pool" in res.prompt

def test_case_05_model_and_custom_character(session: Session):
    """Case 5: 模型角色 + 自定义角色 (穗穗追着穿黄色雨衣的小夏跑)"""
    char = Character(
        name="小夏",
        age_group="young adult",
        body="petite",
        gender="woman",
        hair_color="black",
        hair_style="straight",
        hair_length="long",
        eye_color="green",
        top="white blouse",
        bottom="black pleated skirt"
    )
    session.add(char)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[
            Entity(id="c1", name="穗穗"),
            Entity(id="c2", name="小夏")
        ],
        statements=[
            Statement(kind="attribute", subject="c2", text="wearing a yellow raincoat", facet="outfit", effect="replace"),
            Statement(kind="relation", subject="c1", target="c2", text="chasing")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "小夏" not in res.prompt
    assert "yellow raincoat" in res.prompt
    assert "chasing" in res.prompt

def test_case_06_model_character_appearance_override(session: Session):
    """Case 6: 用户修改模型角色外观 (穗穗把头发扎成马尾，穿泳装)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗")],
        statements=[
            Statement(kind="attribute", subject="c1", text="ponytail", facet="hairstyle", effect="replace"),
            Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "ponytail" in res.prompt
    assert "wearing a swimsuit" in res.prompt

def test_case_07_complex_action_without_fixed_schema(session: Session):
    """Case 7: 复杂新动作无需改 Schema (穗穗把手里的冰淇淋扔向正在骑自行车逃跑的秧秧)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗"), Entity(id="c2", name="秧秧")],
        statements=[
            Statement(kind="attribute", subject="c1", text="holding ice cream"),
            Statement(kind="relation", subject="c1", target="c2", text="throwing ice cream toward"),
            Statement(kind="attribute", subject="c2", text="riding a bicycle and escaping")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "holding ice cream" in res.prompt
    assert "throwing ice cream toward" in res.prompt
    assert "riding a bicycle and escaping" in res.prompt

def test_case_08_minimal_input(session: Session):
    """Case 8: 最小输入 (穗穗坐着)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗")],
        statements=[Statement(kind="attribute", subject="c1", text="sitting")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "sitting" in res.prompt
    assert "smiling" not in res.prompt
    assert "classroom" not in res.prompt
    assert "sunset" not in res.prompt

def test_case_09_scene(session: Session):
    """Case 9: 场景 (穗穗和秧秧在沙滩上)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗"), Entity(id="c2", name="秧秧")],
        statements=[Statement(kind="scene", text="on a beach")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "on a beach" in res.prompt

def test_case_10_emotion_ownership(session: Session):
    """Case 10: 表情归属 (穗穗生气地看着正在笑的秧秧)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗"), Entity(id="c2", name="秧秧")],
        statements=[
            Statement(kind="attribute", subject="c1", text="angry", facet="expression"),
            Statement(kind="relation", subject="c1", target="c2", text="looking at"),
            Statement(kind="attribute", subject="c2", text="smiling", facet="expression")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "Suisui (girl) is angry and looking at Yangyang (girl)" in res.prompt
    assert "Yangyang (girl) is smiling" in res.prompt

def test_case_11_props_ownership(session: Session):
    """Case 11: 道具归属 (穗穗拿着棒球棍，秧秧拿着雨伞)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗"), Entity(id="c2", name="秧秧")],
        statements=[
            Statement(kind="attribute", subject="c1", text="holding a baseball bat"),
            Statement(kind="attribute", subject="c2", text="holding an umbrella")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "Suisui (girl) is holding a baseball bat" in res.prompt
    assert "Yangyang (girl) is holding an umbrella" in res.prompt

def test_case_12_safety_determinism(session: Session):
    """Case 12: Safe / Sensitive / NSFW / Explicit 确定性注入 (一对一)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(entities=[Entity(id="c1", name="穗穗")], statements=[])
    
    res_safe = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "safe" in res_safe.prompt
    assert "nsfw" not in res_safe.prompt

    res_sens = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Sensitive"))
    assert "sensitive" in res_sens.prompt

    res_nsfw = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="NSFW"))
    assert "nsfw" in res_nsfw.prompt
    assert "safe" not in res_nsfw.prompt

    res_explicit = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Explicit"))
    assert "explicit" in res_explicit.prompt
    assert "nsfw" not in res_explicit.prompt

def test_case_13_artist_injection(session: Session):
    """Case 13: 画师 @artist 确定性注入 (下划线转为空格)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(entities=[Entity(id="c1", name="穗穗")], statements=[])
    
    # Without artist
    res_no_art = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "@" not in res_no_art.prompt

    # With artist
    res_art = pipeline.build_prompt(PromptBuildRequest(
        facts=facts,
        safety="Safe",
        artist_tags=["@mika_pikazo", "@tiv"]
    ))
    assert "@mika pikazo" in res_art.prompt
    assert "@tiv" in res_art.prompt

def test_case_14_lora_injection(session: Session):
    """Case 14: LoRA 联动与启用/禁用控制"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(entities=[Entity(id="c1", name="穗穗")], statements=[])
    
    res_lora = pipeline.build_prompt(PromptBuildRequest(
        facts=facts,
        safety="Safe",
        lora_items=[
            LoraBuildItem(trigger_words="water_dress, flowing_water", strength=0.8, is_enabled=True),
            LoraBuildItem(trigger_words="glowing_wings", strength=0.6, is_enabled=False)
        ]
    ))
    assert "water_dress, flowing_water" in res_lora.prompt
    assert "glowing_wings" not in res_lora.prompt

def test_case_15_trigger_cache_preference(session: Session):
    """Case 15: Trigger 手动修正优先 (下划线转为空格)"""
    existing = session.exec(select(CharacterTriggerCache).where(CharacterTriggerCache.name == "穗穗")).first()
    if existing:
        existing.canonical_tag = "suisui_custom_v2"
        existing.caption_name = "SuisuiV2"
        session.add(existing)
    else:
        session.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui_custom_v2", caption_name="SuisuiV2"))
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(entities=[Entity(id="c1", name="穗穗")], statements=[])
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui custom v2" in res.prompt

def test_case_16_unknown_character_fallback(session: Session):
    """Case 16: 未知于 Agent 但用户认为模型已训练 (希露菲)"""
    session.add(CharacterTriggerCache(name="希露菲", canonical_tag="sylphiette", caption_name="Sylphiette"))
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="希露菲")],
        statements=[Statement(kind="attribute", subject="c1", text="standing")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert res.facts.entities[0].source == "model_character"
    assert res.facts.entities[0].canonical_tag == "sylphiette"
    assert "sylphiette" in res.prompt
    assert "standing" in res.prompt

def test_case_17_multiple_complex_relations(session: Session):
    """Case 17: 多个复杂关系 (穗穗站在秧秧后面抓住帽子，秧秧回头看她)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗"), Entity(id="c2", name="秧秧")],
        statements=[
            Statement(kind="relation", subject="c1", target="c2", text="standing behind and grabbing hat from"),
            Statement(kind="relation", subject="c2", target="c1", text="looking back at")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "yangyang" in res.prompt
    assert "Suisui (girl) is standing behind and grabbing hat from Yangyang (girl)" in res.prompt
    assert "Yangyang (girl) is looking back at Suisui (girl)" in res.prompt

def test_case_18_creative_completion_default_off(session: Session):
    """Case 18: 自由补全默认关闭 (两人在雨里跑)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="girl1"), Entity(id="c2", name="girl2")],
        statements=[
            Statement(kind="attribute", subject="c1", text="running"),
            Statement(kind="attribute", subject="c2", text="running"),
            Statement(kind="scene", text="in the rain")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "in the rain" in res.prompt
    assert "running" in res.prompt
    assert "neon city" not in res.prompt
    assert "cinematic lighting" not in res.prompt
    assert "dramatic backlight" not in res.prompt

def test_case_19_action_attribution_not_scene(session: Session):
    """Case 19: 动作与地点修饰归属于人物而非全局 Scene (穗穗穿着泳装，在沙滩上奔跑)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="穗穗")],
        statements=[
            Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace"),
            Statement(kind="attribute", subject="c1", text="running on the beach")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "suisui" in res.prompt
    assert "Suisui (girl) is wearing a swimsuit and running on the beach" in res.prompt
    assert "Suisui (girl) is wearing a swimsuit. running on the beach." not in res.prompt

def test_case_20_dual_custom_characters_distinction(session: Session):
    """Case 20: 两个自定义角色区分 (小夏追着小雨跑，外貌特征区分，名字不作为 tag)"""
    char1 = Character(
        name="小夏",
        age_group="young adult",
        body="petite",
        gender="woman",
        hair_color="black",
        hair_style="straight",
        hair_length="long",
        eye_color="green",
        top="white blouse",
        bottom="black pleated skirt"
    )
    char2 = Character(
        name="小雨",
        age_group="young adult",
        body="tall",
        gender="woman",
        hair_color="brown",
        hair_style="twintails",
        hair_length="short",
        eye_color="blue",
        top="yellow hoodie",
        bottom="denim shorts"
    )
    session.add(char1)
    session.add(char2)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[
            Entity(id="c1", name="小夏"),
            Entity(id="c2", name="小雨")
        ],
        statements=[
            Statement(kind="relation", subject="c1", target="c2", text="chasing")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "小夏" not in res.prompt
    assert "小雨" not in res.prompt
    assert "black hair" in res.prompt
    assert "brown hair" in res.prompt
    assert "the young woman with black hair is chasing the young woman with brown hair" in res.prompt

@pytest.mark.asyncio
async def test_case_21_lora_scan_edit_preservation(session: Session, monkeypatch):
    """Case 21: LoRA 扫描与编辑触发词持久化 (执行真实 sync_comfyui_loras 不覆盖用户自定义 trigger 和属性)"""
    from app.api.loras import sync_comfyui_loras
    from app.services.comfyui.client import ComfyUIClient

    # 1. First ComfyUI scan discovers water_dress.safetensors
    monkeypatch.setattr(ComfyUIClient, "get_loras", lambda self: asyncio.sleep(0, result=["water_dress.safetensors", "other.safetensors"]))
    await sync_comfyui_loras(session=session)

    lora = session.exec(select(Lora).where(Lora.filename == "water_dress.safetensors")).first()
    assert lora is not None
    assert lora.trigger_words == ""

    # 2. User edits trigger words, name, and default strength
    lora.trigger_words = "water_dress, flowing_water"
    lora.name = "Water Dress Effect"
    lora.default_strength = 1.25
    session.add(lora)
    session.commit()

    # 3. Second ComfyUI scan runs
    await sync_comfyui_loras(session=session)

    # 4. Verify user custom edits are strictly preserved
    re_synced = session.exec(select(Lora).where(Lora.filename == "water_dress.safetensors")).first()
    assert re_synced is not None
    assert re_synced.trigger_words == "water_dress, flowing_water"
    assert re_synced.name == "Water Dress Effect"
    assert re_synced.default_strength == 1.25
    assert re_synced.is_valid_file is True
