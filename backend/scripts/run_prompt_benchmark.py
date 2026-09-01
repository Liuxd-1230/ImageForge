import asyncio
import os
import sys
import json
import argparse
import httpx
from typing import List, Dict, Any, Optional
from sqlmodel import Session, create_engine, SQLModel
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.preset import Preset
from app.models.prompt_engine import (
    SemanticFacts,
    Entity,
    Statement,
    PromptBuildRequest,
    LoraBuildItem
)
from app.services.llm.lm_studio import LMStudioProvider
from app.services.prompt_engine.pipeline import PromptPipeline
from app.services.comfyui.client import ComfyUIClient
from app.services.comfyui.workflow import build_anima_29b_workflow

# 16 Benchmark Cases with strictly equivalent semantic content across variants
BENCHMARK_CASES = [
    {
        "id": "case_01",
        "title": "单人物 + 基础服装",
        "input": "穗穗穿着白色泳装站在沙滩上。",
        "tag_only": "safe, 1girl, suisui, white swimsuit, standing on beach",
        "nl_heavy": "safe, 1girl, suisui. Suisui is wearing a white swimsuit and standing on a beach.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[
                Statement(kind="attribute", subject="c1", text="wearing a white swimsuit", facet="outfit", effect="replace"),
                Statement(kind="attribute", subject="c1", text="standing on a beach")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_02",
        "title": "单人物 + 多个外貌修改",
        "input": "穗穗把金发扎成双马尾，戴着红框眼镜，穿着黑色水手服。",
        "tag_only": "safe, 1girl, suisui, blonde hair, twintails, red-framed glasses, black sailor uniform",
        "nl_heavy": "safe, 1girl, suisui. Suisui has blonde twintails, and is wearing red-framed glasses and a black sailor uniform.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[
                Statement(kind="attribute", subject="c1", text="blonde hair", facet="hair_color", effect="replace"),
                Statement(kind="attribute", subject="c1", text="twintails", facet="hairstyle", effect="replace"),
                Statement(kind="attribute", subject="c1", text="wearing red-framed glasses", facet="accessory", effect="add"),
                Statement(kind="attribute", subject="c1", text="wearing a black sailor uniform", facet="outfit", effect="replace")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_03",
        "title": "两人物不同服装归属",
        "input": "穗穗穿着红色连衣裙，秧秧穿着蓝色海军水手服。",
        "tag_only": "safe, 2girls, suisui, yangyang, red dress, blue sailor uniform",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is wearing a red dress, while Yangyang is wearing a blue sailor uniform.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="wearing a red dress", facet="outfit", effect="replace"),
                Statement(kind="attribute", subject="c2", text="wearing a blue sailor uniform", facet="outfit", effect="replace")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_04",
        "title": "两人物动作交互与拥抱",
        "input": "穗穗微笑着拥抱秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, smiling, hugging",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is smiling and hugging Yangyang.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="smiling", facet="expression", effect="modify"),
                Statement(kind="relation", subject="c1", target="c2", text="hugging")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_05",
        "title": "前后追逐动作关系",
        "input": "穗穗在草地上追逐秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, on grassy field, chasing",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is chasing Yangyang on a grassy field.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="relation", subject="c1", target="c2", text="chasing on a grassy field")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_06",
        "title": "多人物不同道具归属",
        "input": "穗穗拿着魔法杖，秧秧拿着遮阳伞。",
        "tag_only": "safe, 2girls, suisui, yangyang, holding magic wand, holding parasol",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is holding a magic wand, and Yangyang is holding a parasol.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="holding a magic wand", facet="item", effect="add"),
                Statement(kind="attribute", subject="c2", text="holding a parasol", facet="item", effect="add")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_07",
        "title": "原生角色 + 自定义角色",
        "input": "穗穗看着穿着黄色雨衣的小夏。",
        "tag_only": "safe, 2girls, suisui, black hair, yellow raincoat, looking at",
        "nl_heavy": "safe, 2girls, suisui, the young woman with long black hair. Suisui is looking at the young woman with long black hair who is wearing a yellow raincoat.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="小夏", source="user_defined", custom_description="the young woman with long black hair", caption_name="the young woman with long black hair")
            ],
            statements=[
                Statement(kind="attribute", subject="c2", text="wearing a yellow raincoat", facet="outfit", effect="replace"),
                Statement(kind="relation", subject="c1", target="c2", text="looking at")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_08",
        "title": "双自定义角色区分",
        "input": "小夏把手里的冰淇淋递给小雨。",
        "tag_only": "safe, 2girls, black hair, brown hair, handing ice cream",
        "nl_heavy": "safe, 2girls, the young woman with black hair, the young woman with brown hair. The young woman with black hair is handing ice cream to the young woman with brown hair.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="小夏", source="user_defined", custom_description="the young woman with black hair", caption_name="the young woman with black hair"),
                Entity(id="c2", name="小雨", source="user_defined", custom_description="the young woman with brown hair", caption_name="the young woman with brown hair")
            ],
            statements=[
                Statement(kind="relation", subject="c1", target="c2", text="handing ice cream to")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_09",
        "title": "三人物群像互动",
        "input": "穗穗、秧秧和小夏一起坐在野餐垫上吃西瓜。",
        "tag_only": "safe, 3girls, suisui, yangyang, black hair, sitting on picnic mat, eating watermelon",
        "nl_heavy": "safe, 3girls, suisui, yangyang, the young woman with black hair. Suisui, Yangyang, and the young woman with black hair are sitting together on a picnic mat, eating watermelon.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang"),
                Entity(id="c3", name="小夏", source="user_defined", custom_description="the young woman with black hair", caption_name="the young woman with black hair")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="sitting on a picnic mat and eating watermelon"),
                Statement(kind="attribute", subject="c2", text="sitting on a picnic mat and eating watermelon"),
                Statement(kind="attribute", subject="c3", text="sitting on a picnic mat and eating watermelon")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_10",
        "title": "复杂动作与空间关系",
        "input": "穗穗站在桥上向远处挥手，秧秧在旁边拍照。",
        "tag_only": "safe, 2girls, suisui, yangyang, standing on bridge, waving, taking photo",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is standing on a bridge waving toward the distance, while Yangyang is taking a photo beside her.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="standing on a bridge and waving toward the distance"),
                Statement(kind="attribute", subject="c2", text="taking a photo beside her")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_11",
        "title": "极简稀疏 Prompt",
        "input": "穗穗坐着。",
        "tag_only": "safe, 1girl, suisui, sitting",
        "nl_heavy": "safe, 1girl, suisui. Suisui is sitting.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[Statement(kind="attribute", subject="c1", text="sitting")]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_12",
        "title": "画师风格注入",
        "input": "穗穗穿着华丽礼服站在星空下，画师 Mika Pikazo。",
        "tag_only": "safe, 1girl, suisui, @mika pikazo, ornate dress, under starry night sky",
        "nl_heavy": "safe, 1girl, suisui, @mika pikazo. Suisui is wearing an ornate dress and standing under a starry night sky.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[
                Statement(kind="attribute", subject="c1", text="wearing an ornate dress", facet="outfit", effect="replace"),
                Statement(kind="attribute", subject="c1", text="standing under a starry night sky")
            ]
        ),
        "artist_tags": ["@mika_pikazo"],
        "lora_items": []
    },
    {
        "id": "case_13",
        "title": "LoRA 触发词联动 (语义严格等价)",
        "input": "穗穗穿着流动水纹裙子。",
        "tag_only": "safe, 1girl, suisui, aesthetic_boost, flowing water print dress",
        "nl_heavy": "safe, 1girl, suisui, aesthetic_boost. Suisui is wearing a dress with flowing water patterns.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[
                Statement(kind="attribute", subject="c1", text="wearing a dress with flowing water patterns", facet="outfit", effect="replace")
            ]
        ),
        "artist_tags": [],
        "lora_items": [
            LoraBuildItem(filename="anima\\anima-highres-aesthetic-boost.safetensors", trigger_words="aesthetic_boost", strength=0.8, is_enabled=True)
        ]
    },
    {
        "id": "case_14",
        "title": "动作与地点修饰绑定",
        "input": "穗穗穿着泳装，在沙滩上奔跑。",
        "tag_only": "safe, 1girl, suisui, swimsuit, running on beach",
        "nl_heavy": "safe, 1girl, suisui. Suisui is wearing a swimsuit and running on the beach.",
        "facts": SemanticFacts(
            entities=[Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui")],
            statements=[
                Statement(kind="attribute", subject="c1", text="wearing a swimsuit", facet="outfit", effect="replace"),
                Statement(kind="attribute", subject="c1", text="running on the beach")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_15",
        "title": "遮挡与视线空间关系",
        "input": "穗穗躲在树后面偷偷看着坐在长椅上的秧秧。",
        "tag_only": "safe, 2girls, suisui, yangyang, hiding behind tree, looking at, sitting on bench",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is hiding behind a tree, secretly looking at Yangyang who is sitting on a bench.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="hiding behind a tree"),
                Statement(kind="attribute", subject="c2", text="sitting on a bench"),
                Statement(kind="relation", subject="c1", target="c2", text="secretly looking at")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    },
    {
        "id": "case_16",
        "title": "情绪与表情反差互动",
        "input": "穗穗气鼓鼓地转过身，秧秧在一旁无奈地笑。",
        "tag_only": "safe, 2girls, suisui, yangyang, pouting, turning body away, awkward smile",
        "nl_heavy": "safe, 2girls, suisui, yangyang. Suisui is pouting and turning her body away, while Yangyang is giving an awkward smile beside her.",
        "facts": SemanticFacts(
            entities=[
                Entity(id="c1", name="穗穗", source="model_character", canonical_tag="suisui", caption_name="Suisui"),
                Entity(id="c2", name="秧秧", source="model_character", canonical_tag="yangyang", caption_name="Yangyang")
            ],
            statements=[
                Statement(kind="attribute", subject="c1", text="pouting and turning her body away"),
                Statement(kind="attribute", subject="c2", text="giving an awkward smile beside her")
            ]
        ),
        "artist_tags": [],
        "lora_items": []
    }
]

async def main():
    parser = argparse.ArgumentParser(description="ImageForge Anima-2.9B Prompt Benchmark Pipeline")
    parser.add_argument("--render", action="store_true", help="Render images via ComfyUI")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 1337], help="List of seeds to render")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases to process")
    parser.add_argument("--output-dir", type=str, default="backend/data/benchmark_results", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    renders_dir = os.path.join(args.output_dir, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        session.add(Preset(name="Default", positive_prefix="", default_negative="lowres, bad anatomy, bad hands, text", is_default=True))
        session.commit()

        pipeline = PromptPipeline(session=session)
        comfy_client = ComfyUIClient(base_url="http://127.0.0.1:8188")
        
        print("=========================================================")
        print(f"  Anima-2.9B Prompt Benchmark 真实流水线 ({len(BENCHMARK_CASES)} 组用例)")
        print(f"  模式: {'ComfyUI 真实图像渲染' if args.render else 'Prompt 变体清单生成'}")
        print(f"  对照变体: Tag-only / ImageForge Mixed / NL-heavy")
        print(f"  固定 Seeds: {args.seeds}")
        print("=========================================================\n")

        cases_to_process = BENCHMARK_CASES[:args.limit] if args.limit else BENCHMARK_CASES
        manifest_data = []
        scorecard_template = {}
        total_renders = 0

        for case in cases_to_process:
            case_id = case["id"]
            title = case["title"]
            user_input = case["input"]
            facts = case["facts"]
            artist_tags = case.get("artist_tags", [])
            lora_items = case.get("lora_items", [])

            # Real execution of ImageForge Prompt Engine
            build_req = PromptBuildRequest(
                facts=facts,
                safety="Safe",
                artist_tags=artist_tags,
                lora_items=lora_items
            )
            built_res = pipeline.build_prompt(build_req)
            imageforge_mixed = built_res.prompt

            variants = {
                "tag_only": case["tag_only"],
                "imageforge_mixed": imageforge_mixed,
                "nl_heavy": case["nl_heavy"]
            }

            case_entry = {
                "id": case_id,
                "title": title,
                "input": user_input,
                "variants": variants,
                "facts": facts.model_dump()
            }
            manifest_data.append(case_entry)

            print(f"[{case_id}] {title}")
            print(f"  - 输入:             \"{user_input}\"")
            print(f"  - Tag-only:         {variants['tag_only']}")
            print(f"  - ImageForge Mixed: {variants['imageforge_mixed']}")
            print(f"  - NL-heavy:         {variants['nl_heavy']}")

            # Scorecard template entry
            scorecard_template[case_id] = {
                "title": title,
                "input": user_input,
                "scores": {}
            }

            for seed in args.seeds:
                scorecard_template[case_id]["scores"][f"seed_{seed}"] = {
                    "tag_only": {"faithfulness": None, "binding": None, "interaction": None, "quality": None, "image_file": f"{case_id}_tag_only_seed{seed}.png"},
                    "imageforge_mixed": {"faithfulness": None, "binding": None, "interaction": None, "quality": None, "image_file": f"{case_id}_imageforge_mixed_seed{seed}.png"},
                    "nl_heavy": {"faithfulness": None, "binding": None, "interaction": None, "quality": None, "image_file": f"{case_id}_nl_heavy_seed{seed}.png"}
                }

                if args.render:
                    for v_name, v_prompt in variants.items():
                        print(f"    -> 正在渲染: {case_id} [{v_name}] (Seed {seed})...")
                        workflow = build_anima_29b_workflow(
                            positive_prompt=v_prompt,
                            negative_prompt="lowres, bad anatomy, bad hands, text",
                            unet_name="anima29B_v10.safetensors",
                            clip_name="qwen_3_06b_base.safetensors",
                            vae_name="qwen_image_vae.safetensors",
                            clip_type="stable_diffusion",
                            loras=lora_items,
                            width=1024,
                            height=1536,
                            steps=28,
                            cfg=4.5,
                            sampler_name="euler",
                            scheduler="sgm_uniform",
                            seed=seed
                        )
                        submit_res = await comfy_client.queue_prompt(workflow, f"bench_{case_id}_{v_name}_{seed}")
                        prompt_id = submit_res.get("prompt_id")
                        assert prompt_id is not None, f"任务提交失败: {submit_res}"

                        # Wait for image
                        img_info = None
                        for _ in range(90):
                            await asyncio.sleep(2.0)
                            try:
                                h = await comfy_client.get_history(prompt_id)
                                task_h = h.get(prompt_id, {})
                                outputs = task_h.get("outputs", {})
                                for _, nout in outputs.items():
                                    if "images" in nout and len(nout["images"]) > 0:
                                        img_info = nout["images"][0]
                                        break
                                if img_info:
                                    break
                            except Exception:
                                pass

                        if img_info:
                            filename = img_info.get("filename")
                            subfolder = img_info.get("subfolder", "")
                            img_type = img_info.get("type", "output")
                            async with httpx.AsyncClient(timeout=30.0) as http_client:
                                img_url = f"http://127.0.0.1:8188/view?filename={filename}&subfolder={subfolder}&type={img_type}"
                                r = await http_client.get(img_url)
                                if r.status_code == 200:
                                    out_img_path = os.path.join(renders_dir, f"{case_id}_{v_name}_seed{seed}.png")
                                    with open(out_img_path, "wb") as f:
                                        f.write(r.content)
                                    print(f"       已保存图像: {out_img_path} ({len(r.content) / 1024:.1f} KB)")
                                    total_renders += 1

            print()

        # Save manifest
        manifest_file = os.path.join(args.output_dir, "benchmark_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        # Save scorecard template
        scorecard_file = os.path.join(args.output_dir, "scorecard_template.json")
        with open(scorecard_file, "w", encoding="utf-8") as f:
            json.dump(scorecard_template, f, ensure_ascii=False, indent=2)

        print("=========================================================")
        print(f"✅ Benchmark 执行完毕！")
        print(f"   - Manifest: {manifest_file} (包含全部 3 个变体)")
        print(f"   - 打分卡模板: {scorecard_file}")
        if args.render:
            print(f"   - 实际渲染生成图像: {total_renders} 张 -> {renders_dir}")
        print("=========================================================")

if __name__ == "__main__":
    asyncio.run(main())
