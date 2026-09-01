import asyncio
import os
import json
import httpx
from typing import List, Dict, Any
from sqlmodel import Session, create_engine, SQLModel
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.preset import Preset
from app.models.prompt_engine import PromptBuildRequest, LoraBuildItem
from app.services.llm.lm_studio import LMStudioProvider
from app.services.prompt_engine.pipeline import PromptPipeline
from app.services.comfyui.client import ComfyUIClient
from app.services.comfyui.workflow import build_anima_29b_workflow

BENCHMARK_CASES = [
    {
        "id": "case_01",
        "title": "单人物 + 基础服装",
        "input": "穗穗穿着白色泳装站在沙滩上。",
        "tag_only": "safe, 1girl, suisui, white swimsuit, standing, on a beach",
        "nl_heavy": "safe, 1girl, suisui. Suisui is wearing a white swimsuit and standing on a beach."
    },
    {
        "id": "case_02",
        "title": "单人物 + 多个外貌修改",
        "input": "穗穗把金发扎成双马尾，戴着红框眼镜，穿着黑色水手服。",
        "tag_only": "safe, 1girl, suisui, blonde hair, twintails, red-framed glasses, black sailor uniform",
        "nl_heavy": "safe, 1girl, suisui. Suisui with blonde twintails hair, wearing red-framed glasses and a black sailor uniform."
    },
    {
        "id": "case_03",
        "title": "两人物不同服装归属",
        "input": "穗穗穿着红色连衣裙，秧秧穿着蓝色海军水手服。",
        "tag_only": "safe, 2girls, suisui, yangyang, red dress, blue sailor uniform",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is wearing a red dress, while Yangyang is wearing a blue sailor uniform."
    },
    {
        "id": "case_04",
        "title": "两人物动作交互与拥抱",
        "input": "穗穗微笑着拥抱秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, smiling, hugging",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is smiling and hugging Yangyang."
    },
    {
        "id": "case_05",
        "title": "前后追逐动作关系",
        "input": "穗穗在草地上追逐秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, on grass, chasing",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is chasing Yangyang on a grassy field."
    },
    {
        "id": "case_06",
        "title": "多人物不同道具归属",
        "input": "穗穗拿着魔法杖，秧秧拿着遮阳伞。",
        "tag_only": "safe, 2girls, suisui, yangyang, holding magic wand, holding parasol",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is holding a magic wand, and Yangyang is holding a parasol."
    },
    {
        "id": "case_07",
        "title": "原生角色 + 自定义角色",
        "input": "穗穗看着穿着黄色雨衣的小夏。",
        "tag_only": "safe, 2girls, suisui, black hair, yellow raincoat, looking at",
        "nl_heavy": "safe, 2girls, suisui, the young woman with long black hair. Suisui is looking at the young woman with long black hair who is wearing a yellow raincoat."
    },
    {
        "id": "case_08",
        "title": "双自定义角色区分",
        "input": "小夏把手里的冰淇淋递给小雨。",
        "tag_only": "safe, 2girls, black hair, brown hair, handing ice cream",
        "nl_heavy": "safe, 2girls, the young woman with black hair, the young woman with brown hair. The young woman with black hair is handing ice cream to the young woman with brown hair."
    },
    {
        "id": "case_09",
        "title": "三人物群像互动",
        "input": "穗穗、秧秧和小夏一起坐在野餐垫上吃西瓜。",
        "tag_only": "safe, 3girls, suisui, yangyang, black hair, sitting on picnic mat, eating watermelon",
        "nl_heavy": "safe, 3girls, suisui, yangyang, the young woman with black hair. Suisui, Yangyang, and the young woman with black hair are sitting together on a picnic mat, eating watermelon."
    },
    {
        "id": "case_10",
        "title": "复杂动作与空间关系",
        "input": "穗穗站在桥上向远处挥手，秧秧在旁边拍照。",
        "tag_only": "safe, 2girls, suisui, yangyang, standing on bridge, waving, taking photo",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is standing on a bridge waving toward the distance, while Yangyang is taking a photo beside her."
    },
    {
        "id": "case_11",
        "title": "极简稀疏 Prompt",
        "input": "穗穗坐着。",
        "tag_only": "safe, 1girl, suisui, sitting",
        "nl_heavy": "safe, 1girl, suisui. Suisui is sitting."
    },
    {
        "id": "case_12",
        "title": "画师风格注入",
        "input": "穗穗穿着华丽礼服站在星空下，画师 Mika Pikazo。",
        "tag_only": "safe, 1girl, suisui, @mika pikazo, ornate dress, under starry sky",
        "nl_heavy": "safe, 1girl, suisui, @mika pikazo. Suisui is wearing an ornate dress, standing under a starry night sky."
    },
    {
        "id": "case_13",
        "title": "LoRA 触发词联动",
        "input": "穗穗穿着流动水纹裙子。",
        "tag_only": "safe, 1girl, suisui, aesthetic_boost, flowing water dress",
        "nl_heavy": "safe, 1girl, suisui, aesthetic_boost. Suisui is wearing a dress made of flowing water."
    },
    {
        "id": "case_14",
        "title": "动作与地点修饰绑定",
        "input": "穗穗穿着泳装，在沙滩上奔跑。",
        "tag_only": "safe, 1girl, suisui, swimsuit, running, beach",
        "nl_heavy": "safe, 1girl, suisui. Suisui is wearing a swimsuit and running on the beach."
    },
    {
        "id": "case_15",
        "title": "遮挡与视线空间关系",
        "input": "穗穗躲在树后面偷偷看着坐在长椅上的秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, hiding behind tree, looking at, sitting on bench",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is hiding behind a tree, secretly looking at Yangyang who is sitting on a bench."
    },
    {
        "id": "case_16",
        "title": "情绪与表情反差互动",
        "input": "穗穗气鼓鼓地转过身，秧秧在一旁无奈地笑。",
        "tag_only": "safe, 2girls, suisui, yangyang, pouting, turning away, awkward smile",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is pouting and turning her body away, while Yangyang is giving an awkward smile beside her."
    }
]

async def run_benchmark(output_dir: str = "backend/data/benchmark_results"):
    os.makedirs(output_dir, exist_ok=True)
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Seed test characters
        session.add(CharacterTriggerCache(name="穗穗", canonical_tag="suisui", caption_name="Suisui"))
        session.add(CharacterTriggerCache(name="秧秧", canonical_tag="yangyang", caption_name="Yangyang"))
        session.add(Character(name="小夏", age_group="young adult", gender="woman", hair_color="black", hair_style="straight", hair_length="long", top="white blouse", bottom="black pleated skirt"))
        session.add(Character(name="小雨", age_group="young adult", gender="woman", hair_color="brown", hair_style="twintails", hair_length="short", top="yellow hoodie", bottom="denim shorts"))
        session.commit()

        pipeline = PromptPipeline(session=session)
        
        print("=========================================================")
        print(f"  Anima-2.9B Prompt Benchmark 对照基准生成 ({len(BENCHMARK_CASES)} 组用例)")
        print("=========================================================\n")

        results = []
        for case in BENCHMARK_CASES:
            case_id = case["id"]
            title = case["title"]
            user_input = case["input"]

            case_result = {
                "id": case_id,
                "title": title,
                "input": user_input,
                "variants": {
                    "tag_only": case["tag_only"],
                    "nl_heavy": case["nl_heavy"]
                }
            }
            results.append(case_result)

        # Save benchmark manifest
        manifest_path = os.path.join(output_dir, "benchmark_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Benchmark 用例清单已成功生成: {manifest_path}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
