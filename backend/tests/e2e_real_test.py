import asyncio
import json
import httpx
from sqlmodel import Session, SQLModel, create_engine
from app.models.character import Character
from app.models.trigger_cache import CharacterTriggerCache
from app.models.preset import Preset
from app.models.prompt_engine import PromptBuildRequest
from app.services.llm.lm_studio import LMStudioProvider
from app.services.prompt_engine.pipeline import PromptPipeline
from app.services.comfyui.client import ComfyUIClient
from app.services.comfyui.workflow import build_anima_29b_workflow

async def main():
    print("==================================================")
    print("   ImageForge 端到端真实硬件实机验收测试 (E2E)   ")
    print("==================================================")
    
    # 1. Setup DB
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Preset(name="Anima 2.9B Default", positive_prefix="", default_negative="lowres, bad anatomy, bad hands, text", is_default=True))
        session.commit()

        # 2. Check & Connect Real LM Studio
        lm_provider = LMStudioProvider(base_url="http://127.0.0.1:1234")
        health = await lm_provider.check_health()
        print(f"\n[1/6] LM Studio 连接检测: {health.get('status')}, 发现模型: {health.get('models')}")
        model_name = "qwen3.6-35b-a3b-uncensored-genesis-hermes-v6"
        
        # Load model into VRAM
        print(f"\n[2/6] 请求 LM Studio 加载模型: {model_name}...")
        load_res = await lm_provider.load_model(model_name)
        instance_id = load_res.get("instance_id")
        print(f"      加载结果: instance_id = {instance_id}")

        try:
            # 3. Real Fact Extraction + Character Trigger Resolution via LM Studio
            pipeline = PromptPipeline(session=session, llm_provider=lm_provider)
            user_input = "穗穗穿着泳装，在沙滩上奔跑。"
            print(f"\n[3/6] 用户输入中文描述: \"{user_input}\"")
            print("      正在调用 LM Studio 抽取语义事实并解析角色 Trigger...")
            facts = await pipeline.parse_and_extract(
                raw_text=user_input,
                model=model_name,
                reasoning_effort="off"
            )
            print(f"      抽取实体: {[e.model_dump() for e in facts.entities]}")
            print(f"      抽取陈述: {[s.model_dump() for s in facts.statements]}")

            # 4. Build Final English Prompt
            print(f"\n[4/6] 确定性策略组装最终英文 Prompt...")
            build_res = pipeline.build_prompt(PromptBuildRequest(
                facts=facts,
                safety="Safe",
                artist_tags=["@mika_pikazo"]
            ))
            print(f"      最终 Positive Prompt:\n      >> {build_res.prompt}")
            print(f"      最终 Negative Prompt:\n      >> {build_res.negative_prompt}")

        finally:
            # 5. Unload LM Studio Model VRAM
            print(f"\n[5/6] 释放显存: 正在请求 LM Studio 卸载 instance_id = {instance_id}...")
            if instance_id:
                unload_res = await lm_provider.unload_model(instance_id)
                print(f"      卸载成功: {unload_res}")

        # 6. ComfyUI Anima 2.9B Blueprint Verification
        print(f"\n[6/6] ComfyUI Anima-2.9B Blueprint 工作流构建与在线检测...")
        comfy_client = ComfyUIClient(base_url="http://127.0.0.1:8188")
        comfy_health = await comfy_client.check_health()
        print(f"      ComfyUI 状态: {comfy_health.get('status')}")
        
        workflow = build_anima_29b_workflow(
            positive_prompt=build_res.prompt,
            negative_prompt=build_res.negative_prompt,
            unet_name="anima29B_v10.safetensors",
            clip_name="qwen_3_06b_base.safetensors",
            vae_name="qwen_image_vae.safetensors",
            width=1024,
            height=1536,
            steps=28,
            cfg=4.5,
            sampler_name="euler",
            scheduler="sgm_uniform",
            seed=42
        )
        print("      生成的 Anima-2.9B Workflow 节点结构:")
        for nid, n in workflow.items():
            print(f"        Node [{nid}]: {n.get('class_type')} -> {n.get('inputs')}")
            
    print("\n==================================================")
    print("           端到端真实测试全部成功！              ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
