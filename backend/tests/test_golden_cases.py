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

def test_case_22_empty_gender_neutrality(session: Session):
    """Case 22: 自定义角色 gender 为空时不强制推断为 woman，使用中性称谓且不生成性别人数 tag"""
    char = Character(
        name="神秘人",
        age_group="young adult",
        gender="",  # Explicitly empty gender
        hair_color="silver",
        hair_style="straight",
        hair_length="short",
        top="cloak"
    )
    session.add(char)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="神秘人")],
        statements=[Statement(kind="attribute", subject="c1", text="walking in the dark")]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    assert "神秘人" not in res.prompt
    assert "1girl" not in res.prompt
    assert "woman" not in res.prompt
    assert "the young character with silver hair" in res.prompt

def test_case_23_effect_add_preserves_default_outfit(session: Session):
    """Case 23: statement effect='add' 时保留角色书默认服装，不作 replace 抑制"""
    char = Character(
        name="小夏",
        gender="woman",
        hair_color="black",
        top="white blouse",
        bottom="black pleated skirt"
    )
    session.add(char)
    session.commit()

    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="小夏")],
        statements=[
            Statement(kind="attribute", subject="c1", text="wearing a red ribbon", facet="accessories", effect="add")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    # Default blouse and skirt must be preserved because effect is 'add'
    assert "white blouse" in res.prompt
    assert "black pleated skirt" in res.prompt
    assert "wearing a red ribbon" in res.prompt

def test_case_24_custom_api_workflow_injection():
    """Case 24: 自定义 ComfyUI API Workflow 智能插槽与模型保留测试"""
    from app.services.comfyui.workflow import build_anima_29b_workflow

    raw_api_workflow = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "custom_unet_turbo.safetensors"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "custom_clip.safetensors", "type": "stable_diffusion"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "custom_vae.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "dummy positive", "clip": ["2", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "dummy negative", "clip": ["2", 0]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
                "seed": 100,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras"
            }
        },
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "99": {"class_type": "SaveImage", "inputs": {"images": ["9", 0]}}
    }

    # 1. Test injection with override_models=False (Preserves original workflow models)
    injected_wf = build_anima_29b_workflow(
        positive_prompt="safe, suisui. Suisui is smiling.",
        negative_prompt="lowres, bad quality",
        unet_name="anima29B_v10.safetensors",
        clip_name="qwen_3_06b_base.safetensors",
        vae_name="qwen_image_vae.safetensors",
        width=1024,
        height=1536,
        steps=28,
        cfg=4.5,
        sampler_name="euler",
        scheduler="sgm_uniform",
        seed=42,
        custom_template=raw_api_workflow,
        override_models=False
    )

    assert injected_wf["6"]["inputs"]["text"] == "safe, suisui. Suisui is smiling."
    assert injected_wf["7"]["inputs"]["text"] == "lowres, bad quality"
    assert injected_wf["8"]["inputs"]["seed"] == 42
    assert injected_wf["8"]["inputs"]["steps"] == 28
    assert injected_wf["8"]["inputs"]["cfg"] == 4.5
    assert injected_wf["8"]["inputs"]["sampler_name"] == "euler"
    assert injected_wf["8"]["inputs"]["scheduler"] == "sgm_uniform"
    assert injected_wf["5"]["inputs"]["width"] == 1024
    assert injected_wf["5"]["inputs"]["height"] == 1536
    # Original model loaders must be kept untouched
    assert injected_wf["1"]["inputs"]["unet_name"] == "custom_unet_turbo.safetensors"
    assert injected_wf["2"]["inputs"]["clip_name"] == "custom_clip.safetensors"

    # 2. Test injection with override_models=True (Overwrites models)
    injected_wf_override = build_anima_29b_workflow(
        positive_prompt="safe, suisui.",
        negative_prompt="lowres",
        unet_name="anima29B_v10.safetensors",
        clip_name="qwen_3_06b_base.safetensors",
        vae_name="qwen_image_vae.safetensors",
        seed=42,
        custom_template=raw_api_workflow,
        override_models=True
    )
    assert injected_wf_override["1"]["inputs"]["unet_name"] == "anima29B_v10.safetensors"
    assert injected_wf_override["2"]["inputs"]["clip_name"] == "qwen_3_06b_base.safetensors"

    # 3. Test LoRA dynamic chaining in Custom Workflow
    lora_items = [
        LoraBuildItem(filename="water_dress.safetensors", trigger_words="water_dress", strength=1.2, is_enabled=True)
    ]
    injected_wf_lora = build_anima_29b_workflow(
        positive_prompt="safe, suisui.",
        negative_prompt="lowres",
        loras=lora_items,
        custom_template=raw_api_workflow
    )
    # LoRA node should be created
    lora_node = None
    for nid, node in injected_wf_lora.items():
        if node.get("class_type") == "LoraLoader":
            lora_node = node
            lora_nid = nid
            break
    assert lora_node is not None
    assert lora_node["inputs"]["lora_name"] == "water_dress.safetensors"
    assert lora_node["inputs"]["strength_model"] == 1.2
    # KSampler model input must point to the new LoRA node
    assert injected_wf_lora["8"]["inputs"]["model"] == [lora_nid, 0]

def test_case_25_unresolved_trigger_raises_error(session: Session):
    """Case 25: 未知角色在 parse 时返回未解析卡片以便人工填入，但在 build 时严格拒绝编译"""
    import json
    import pytest
    import asyncio
    from app.services.prompt_engine.resolver import CharacterResolver
    from app.services.prompt_engine.pipeline import PromptPipeline

    class MockFailingLLM:
        async def chat(self, *args, **kwargs):
            return json.dumps({"characters": []})  # Returns empty resolution

    resolver = CharacterResolver(session=session, llm_provider=MockFailingLLM())
    facts_entities = [Entity(id="c1", name="完全未知的超稀有角色")]
    
    # 1. Async resolver returns entity with canonical_tag=None so UI can show editable cards
    resolved = asyncio.run(resolver.resolve_entities_async(facts_entities, []))
    assert len(resolved) == 1
    assert resolved[0].canonical_tag is None

    # 2. Build prompt strictly rejects compilation until trigger is filled
    pipeline = PromptPipeline(session=session)
    unresolved_facts = SemanticFacts(entities=resolved, statements=[])
    with pytest.raises(ValueError) as exc_info:
        pipeline.build_prompt(PromptBuildRequest(facts=unresolved_facts, safety="Safe"))
    
    assert "未能解析 Trigger 标签" in str(exc_info.value) or "未解析 Trigger 标签" in str(exc_info.value)

def test_case_26_generic_person_does_not_invent_girl_tag(session: Session):
    """Case 26: 匿名通用人物 (person / character) 不得脑补 1girl，保留中性自然语言表达"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[Entity(id="c1", name="person")],
        statements=[
            Statement(kind="attribute", subject="c1", text="running"),
            Statement(kind="scene", text="in the rain")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    # Must NOT invent 1girl or 1boy
    assert "1girl" not in res.prompt
    assert "1boy" not in res.prompt
    assert "the person is running in the rain" in res.prompt or "the person is running" in res.prompt

def test_case_27_anonymous_multi_girls_distinction(session: Session):
    """Case 27: 两个匿名女孩 + 独立服装 (girl1 穿红裙，girl2 穿蓝裙)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[
            Entity(id="c1", name="girl1"),
            Entity(id="c2", name="girl2")
        ],
        statements=[
            Statement(kind="attribute", subject="c1", text="wearing a red dress", facet="outfit", effect="replace"),
            Statement(kind="attribute", subject="c2", text="wearing a blue dress", facet="outfit", effect="replace"),
            Statement(kind="relation", subject="c1", target="c2", text="chasing")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    # Must correctly compute 2girls tag
    assert "2girls" in res.prompt
    # Natural language must distinguish between the first girl and the second girl
    assert "the first girl is wearing a red dress and chasing the second girl" in res.prompt
    assert "the second girl is wearing a blue dress" in res.prompt
    # Must not duplicate "the girl is chasing the girl"
    assert "the girl is chasing the girl" not in res.prompt

def test_case_28_anonymous_multi_person_neutral_actions(session: Session):
    """Case 28: 两个匿名通用人物 + 动作 (person1 追着 person2 跑)"""
    pipeline = PromptPipeline(session=session)
    facts = SemanticFacts(
        entities=[
            Entity(id="c1", name="person1"),
            Entity(id="c2", name="person2")
        ],
        statements=[
            Statement(kind="attribute", subject="c1", text="running"),
            Statement(kind="relation", subject="c1", target="c2", text="chasing")
        ]
    )
    res = pipeline.build_prompt(PromptBuildRequest(facts=facts, safety="Safe"))
    # Must NOT invent gender tags
    assert "1girl" not in res.prompt
    assert "2girls" not in res.prompt
    assert "1boy" not in res.prompt
    assert "2boys" not in res.prompt
    # Natural language must distinguish between the first person and the second person
    assert "the first person is running and chasing the second person" in res.prompt

def test_case_29_custom_workflow_rejects_advanced_sampler(session: Session):
    """Case 29: 自定义 API Workflow 严格拒绝 KSamplerAdvanced / KSamplerProgress 等非标准节点"""
    import pytest
    from app.services.comfyui.workflow import build_anima_29b_workflow
    
    mixed_wf = {
        "1": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0]}},
        "2": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["1", 0]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "hello"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad"}}
    }
    with pytest.raises(ValueError) as exc_info:
        build_anima_29b_workflow(
            positive_prompt="safe",
            negative_prompt="lowres",
            custom_template=mixed_wf
        )
    assert "当前自动注入仅支持标准 KSampler" in str(exc_info.value)
