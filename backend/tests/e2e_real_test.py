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
    print("   ImageForge 端到端真实硬件实机全链路验收测试 (E2E)   ")
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
        print(f"\n[1/7] LM Studio 连接检测: {health.get('status')}, 发现模型: {health.get('models')}")
        model_name = "qwen3.6-35b-a3b-uncensored-genesis-hermes-v6"
        
        # Load model into VRAM
        print(f"\n[2/7] 请求 LM Studio 加载模型: {model_name}...")
        load_res = await lm_provider.load_model(model_name)
        instance_id = load_res.get("instance_id")
        print(f"      加载结果: instance_id = {instance_id}")

        try:
            # 3. Real Fact Extraction + Character Trigger Resolution via LM Studio
            pipeline = PromptPipeline(session=session, llm_provider=lm_provider)
            user_input = "穗穗穿着泳装，在沙滩上奔跑。"
            print(f"\n[3/7] 用户输入中文描述: \"{user_input}\"")
            print("      正在调用 LM Studio 抽取语义事实并解析角色 Trigger...")
            facts = await pipeline.parse_and_extract(
                raw_text=user_input,
                model=model_name,
                reasoning_effort="off"
            )
            print(f"      抽取实体: {[e.model_dump() for e in facts.entities]}")
            print(f"      抽取陈述: {[s.model_dump() for s in facts.statements]}")

            # 4. Build Final English Prompt
            print(f"\n[4/7] 确定性策略组装最终英文 Prompt (下划线转空格规范)...")
            build_res = pipeline.build_prompt(PromptBuildRequest(
                facts=facts,
                safety="Safe",
                artist_tags=["@mika_pikazo"]
            ))
            print(f"      最终 Positive Prompt:\n      >> {build_res.prompt}")
            print(f"      最终 Negative Prompt:\n      >> {build_res.negative_prompt}")

        finally:
            # 5. Unload LM Studio Model VRAM
            print(f"\n[5/7] 释放显存: 正在请求 LM Studio 卸载 instance_id = {instance_id}...")
            if instance_id:
                unload_res = await lm_provider.unload_model(instance_id)
                print(f"      卸载成功: {unload_res}")

        # 6. ComfyUI Anima 2.9B Blueprint Execution
        print(f"\n[6/7] ComfyUI Anima-2.9B Blueprint 工作流提交与生图渲染...")
        comfy_client = ComfyUIClient(base_url="http://127.0.0.1:8188")
        comfy_health = await comfy_client.check_health()
        print(f"      ComfyUI 在线状态: {comfy_health.get('status')}")
        
        workflow = build_anima_29b_workflow(
            positive_prompt=build_res.prompt,
            negative_prompt=build_res.negative_prompt,
            unet_name="anima29B_v10.safetensors",
            clip_name="qwen_3_06b_base.safetensors",
            vae_name="qwen_image_vae.safetensors",
            clip_type="stable_diffusion",
            width=1024,
            height=1536,
            steps=28,
            cfg=4.5,
            sampler_name="euler",
            scheduler="sgm_uniform",
            seed=42
        )

        submit_res = await comfy_client.queue_prompt(workflow, "imageforge_e2e_real_test")
        prompt_id = submit_res.get("prompt_id")
        print(f"      工作流入队成功: prompt_id = {prompt_id}, 错误节点: {submit_res.get('node_errors')}")
        assert prompt_id is not None, "ComfyUI 任务提交未返回 prompt_id"

        # Poll history for rendered output image
        print(f"\n[7/7] 正在轮询 ComfyUI 生图完成状态并读取渲染图片...")
        generated_image_info = None
        for i in range(90):
            await asyncio.sleep(2.0)
            try:
                hist_data = await comfy_client.get_history(prompt_id)
                task_hist = hist_data.get(prompt_id, {})
                outputs = task_hist.get("outputs", {})
                for nid, nout in outputs.items():
                    if "images" in nout and len(nout["images"]) > 0:
                        generated_image_info = nout["images"][0]
                        break
                if generated_image_info:
                    break
            except Exception as e:
                pass
            print(f"      等待渲染中... ({(i+1)*2}s)")

        if not generated_image_info:
            raise RuntimeError("ComfyUI 生图超时或未产生图像输出")

        filename = generated_image_info.get("filename")
        subfolder = generated_image_info.get("subfolder", "")
        img_type = generated_image_info.get("type", "output")
        print(f"      生图完成！输出文件: {filename}, 子目录: '{subfolder}'")

        # Fetch actual image binary bytes from ComfyUI /view
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            view_url = f"http://127.0.0.1:8188/view?filename={filename}&subfolder={subfolder}&type={img_type}"
            img_resp = await http_client.get(view_url)
            assert img_resp.status_code == 200, f"获取图片失败: HTTP {img_resp.status_code}"
            assert img_resp.headers.get("content-type", "").startswith("image/"), "响应不是有效图片媒体类型"
            img_bytes = img_resp.content
            print(f"      图片验证成功！数据大小: {len(img_bytes)} bytes ({len(img_bytes) / 1024:.2f} KB), Content-Type: {img_resp.headers.get('content-type')}")

    print("\n==================================================")
    print("   ImageForge 端到端真实实机 E2E 完整闭环全部成功！   ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
