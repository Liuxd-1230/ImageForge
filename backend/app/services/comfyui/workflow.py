import random
import json
from typing import Dict, Any, List, Optional
from app.models.prompt_engine import LoraBuildItem

def build_anima_29b_workflow(
    positive_prompt: str,
    negative_prompt: str,
    unet_name: str = "anima29B_v10.safetensors",
    clip_name: str = "qwen_3_06b_base.safetensors",
    vae_name: str = "qwen_image_vae.safetensors",
    clip_type: str = "stable_diffusion",
    loras: Optional[List[LoraBuildItem]] = None,
    width: int = 1024,
    height: int = 1536,
    batch_size: int = 1,
    steps: int = 28,
    cfg: float = 4.5,
    sampler_name: str = "euler",
    scheduler: str = "sgm_uniform",
    seed: Optional[int] = None,
    custom_template: Optional[Dict[str, Any]] = None,
    override_models: bool = False
) -> Dict[str, Any]:
    """
    Constructs an authentic Anima-2.9B ComfyUI workflow based on official blueprint:
    UNETLoader + CLIPLoader (qwen_3_06b_base) + VAELoader (qwen_image_vae) + KSampler + VAEDecode.
    If custom_template is provided, automatically injects positive/negative prompts, sampling params and dimensions.
    """
    if seed is None or seed == -1:
        seed = random.randint(1, 1125899906842624)

    if custom_template:
        wf = json.loads(json.dumps(custom_template))
        positive_injected = False
        negative_injected = False

        # 1. Trace KSampler positive and negative input links
        pos_node_ids = set()
        neg_node_ids = set()
        for nid, node in wf.items():
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})
            if class_type in ["KSampler", "KSamplerAdvanced", "KSamplerProgress"]:
                pos_link = inputs.get("positive")
                if isinstance(pos_link, list) and len(pos_link) > 0:
                    pos_node_ids.add(str(pos_link[0]))
                neg_link = inputs.get("negative")
                if isinstance(neg_link, list) and len(neg_link) > 0:
                    neg_node_ids.add(str(neg_link[0]))

                # Inject sampling params into KSampler
                if "seed" in inputs: inputs["seed"] = seed
                if "steps" in inputs: inputs["steps"] = steps
                if "cfg" in inputs: inputs["cfg"] = cfg
                if "sampler_name" in inputs: inputs["sampler_name"] = sampler_name
                if "scheduler" in inputs: inputs["scheduler"] = scheduler

            elif class_type in ["EmptyLatentImage", "EmptySD3LatentImage"]:
                if "width" in inputs: inputs["width"] = width
                if "height" in inputs: inputs["height"] = height
                if "batch_size" in inputs: inputs["batch_size"] = batch_size

            elif override_models:
                if class_type == "UNETLoader" and unet_name:
                    inputs["unet_name"] = unet_name
                elif class_type == "CLIPLoader" and clip_name:
                    inputs["clip_name"] = clip_name
                elif class_type == "VAELoader" and vae_name:
                    inputs["vae_name"] = vae_name

        # 2. Inject prompts into traced CLIPTextEncode conditioning nodes
        for pos_nid in pos_node_ids:
            if pos_nid in wf and wf[pos_nid].get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"]:
                wf[pos_nid]["inputs"]["text"] = positive_prompt
                positive_injected = True

        for neg_nid in neg_node_ids:
            if neg_nid in wf and wf[neg_nid].get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"]:
                wf[neg_nid]["inputs"]["text"] = negative_prompt
                negative_injected = True

        # 3. Fallback: Search for {{positive}} and {{negative}} placeholders
        if not positive_injected or not negative_injected:
            for _, node in wf.items():
                inputs = node.get("inputs", {})
                class_type = node.get("class_type", "")
                if class_type in ["CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"]:
                    text_val = str(inputs.get("text", ""))
                    if ("{{positive}}" in text_val or inputs.get("is_positive")) and not positive_injected:
                        inputs["text"] = positive_prompt
                        positive_injected = True
                    elif ("{{negative}}" in text_val or inputs.get("is_negative")) and not negative_injected:
                        inputs["text"] = negative_prompt
                        negative_injected = True

        # 4. Chain LoRAs if enabled
        enabled_loras = [l for l in (loras or []) if l.is_enabled]
        if enabled_loras:
            ksampler_nid = None
            for nid, node in wf.items():
                if node.get("class_type") in ["KSampler", "KSamplerAdvanced", "KSamplerProgress"]:
                    ksampler_nid = nid
                    break

            clip_link = None
            for pos_nid in pos_node_ids:
                if pos_nid in wf and "clip" in wf[pos_nid].get("inputs", {}):
                    clip_link = wf[pos_nid]["inputs"]["clip"]
                    break

            if ksampler_nid and "model" in wf[ksampler_nid].get("inputs", {}):
                current_model = wf[ksampler_nid]["inputs"]["model"]
                current_clip = clip_link

                digit_ids = [int(k) for k in wf.keys() if k.isdigit()]
                next_node_id = (max(digit_ids) if digit_ids else 100) + 1

                for lora in enabled_loras:
                    node_id = str(next_node_id)
                    lora_inputs: Dict[str, Any] = {
                        "lora_name": lora.filename,
                        "strength_model": lora.strength,
                        "strength_clip": lora.strength,
                        "model": current_model
                    }
                    if current_clip:
                        lora_inputs["clip"] = current_clip

                    wf[node_id] = {
                        "class_type": "LoraLoader",
                        "inputs": lora_inputs
                    }
                    current_model = [node_id, 0]
                    if current_clip:
                        current_clip = [node_id, 1]
                    next_node_id += 1

                wf[ksampler_nid]["inputs"]["model"] = current_model

                if current_clip:
                    for pos_nid in pos_node_ids:
                        if pos_nid in wf and "clip" in wf[pos_nid].get("inputs", {}):
                            wf[pos_nid]["inputs"]["clip"] = current_clip
                    for neg_nid in neg_node_ids:
                        if neg_nid in wf and "clip" in wf[neg_nid].get("inputs", {}):
                            wf[neg_nid]["inputs"]["clip"] = current_clip

        if not positive_injected:
            raise ValueError("导入的 ComfyUI API 工作流中未找到连接至 KSampler 的 Positive 提示词节点 (CLIPTextEncode)")
        if not negative_injected:
            raise ValueError("导入的 ComfyUI API 工作流中未找到连接至 KSampler 的 Negative 提示词节点 (CLIPTextEncode)")

        return wf

    # Official Anima-2.9B ComfyUI Blueprint Architecture
    prompt_nodes: Dict[str, Any] = {}

    # Node 1: UNETLoader (Diffusion Model)
    prompt_nodes["1"] = {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": unet_name,
            "weight_dtype": "default"
        }
    }

    # Node 2: CLIPLoader (Qwen3 0.6B Base Text Encoder)
    prompt_nodes["2"] = {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": clip_name,
            "type": clip_type
        }
    }

    # Node 3: VAELoader (Qwen Image VAE)
    prompt_nodes["3"] = {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": vae_name
        }
    }

    current_model = ["1", 0]
    current_clip = ["2", 0]
    node_id_counter = 100  # Start dynamic LoRA node IDs from 100 to avoid conflicts

    # Dynamic LoRA Loader chain
    if loras:
        for lora in loras:
            if lora.is_enabled:
                node_id = str(node_id_counter)
                prompt_nodes[node_id] = {
                    "class_type": "LoraLoader",
                    "inputs": {
                        "lora_name": lora.filename,
                        "strength_model": lora.strength,
                        "strength_clip": lora.strength,
                        "model": current_model,
                        "clip": current_clip
                    }
                }
                current_model = [node_id, 0]
                current_clip = [node_id, 1]
                node_id_counter += 1

    # Node 6: CLIPTextEncode (Positive Prompt)
    prompt_nodes["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": positive_prompt,
            "clip": current_clip
        }
    }

    # Node 7: CLIPTextEncode (Negative Prompt)
    prompt_nodes["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": negative_prompt,
            "clip": current_clip
        }
    }

    # Node 5: EmptyLatentImage (Resolution & Latent Canvas)
    prompt_nodes["5"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": width,
            "height": height,
            "batch_size": batch_size
        }
    }

    # Node 8: KSampler (Sampling engine)
    prompt_nodes["8"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": current_model,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        }
    }

    # Node 9: VAEDecode (Decode Latent to RGB Image)
    prompt_nodes["9"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["8", 0],
            "vae": ["3", 0]
        }
    }

    # Node 99: SaveImage (Save Generated PNG Image)
    prompt_nodes["99"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "Anima29B_ImageForge",
            "images": ["9", 0]
        }
    }

    return prompt_nodes
