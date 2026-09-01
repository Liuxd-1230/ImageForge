import random
import json
from typing import Dict, Any, List, Optional, Tuple
from app.models.prompt_engine import LoraBuildItem

# Single Source of Truth for Anima-2.9B Default ComfyUI Parameters
DEFAULT_UNET_NAME = "anima29B_v10.safetensors"
DEFAULT_CLIP_NAME = "qwen_3_06b_base.safetensors"
DEFAULT_VAE_NAME = "qwen_image_vae.safetensors"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1536
DEFAULT_STEPS = 28
DEFAULT_CFG = 4.5
DEFAULT_SAMPLER = "euler"
DEFAULT_SCHEDULER = "sgm_uniform"

def _attach_lora_chain(
    prompt_nodes: Dict[str, Any],
    initial_model: List[Any],
    initial_clip: Optional[List[Any]],
    loras: Optional[List[LoraBuildItem]],
    start_node_id: int = 100
) -> Tuple[List[Any], Optional[List[Any]]]:
    """
    Unified LoRA chain builder.
    Attaches chained LoraLoader nodes between model/clip loaders and conditioning/samplers.
    """
    current_model = initial_model
    current_clip = initial_clip
    node_id_counter = start_node_id

    for lora in (loras or []):
        if lora.is_enabled:
            node_id = str(node_id_counter)
            inputs: Dict[str, Any] = {
                "lora_name": lora.filename,
                "strength_model": lora.strength,
                "strength_clip": lora.strength,
                "model": current_model
            }
            if current_clip is not None:
                inputs["clip"] = current_clip
            prompt_nodes[node_id] = {
                "class_type": "LoraLoader",
                "inputs": inputs
            }
            current_model = [node_id, 0]
            if current_clip is not None:
                current_clip = [node_id, 1]
            node_id_counter += 1

    return current_model, current_clip

def build_anima_29b_workflow(
    positive_prompt: str,
    negative_prompt: str,
    unet_name: str = DEFAULT_UNET_NAME,
    clip_name: str = DEFAULT_CLIP_NAME,
    vae_name: str = DEFAULT_VAE_NAME,
    clip_type: str = "stable_diffusion",
    loras: Optional[List[LoraBuildItem]] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    batch_size: int = 1,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    sampler_name: str = DEFAULT_SAMPLER,
    scheduler: str = DEFAULT_SCHEDULER,
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
        
        # Guard: explicitly check for single primary KSampler workflow
        ksampler_nodes = [nid for nid, n in wf.items() if n.get("class_type") in ["KSampler", "KSamplerAdvanced", "KSamplerProgress"]]
        if len(ksampler_nodes) > 1:
            raise ValueError(f"当前自动注入仅支持单主 KSampler API Workflow，检测到 {len(ksampler_nodes)} 个 KSampler 节点。复杂多采样工作流请拆分或使用单采样主链。")
        if len(ksampler_nodes) == 0:
            raise ValueError("导入的 ComfyUI API 工作流中未找到 KSampler 节点。")

        positive_injected = False
        negative_injected = False
        pos_node_ids = set()
        neg_node_ids = set()
        ksampler_nid = ksampler_nodes[0]

        for nid, node in wf.items():
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})
            if nid == ksampler_nid:
                pos_link = inputs.get("positive")
                if isinstance(pos_link, list) and len(pos_link) > 0:
                    pos_node_ids.add(str(pos_link[0]))
                neg_link = inputs.get("negative")
                if isinstance(neg_link, list) and len(neg_link) > 0:
                    neg_node_ids.add(str(neg_link[0]))

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

        # Inject prompts into traced CLIPTextEncode conditioning nodes
        for pos_nid in pos_node_ids:
            if pos_nid in wf and wf[pos_nid].get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"]:
                wf[pos_nid]["inputs"]["text"] = positive_prompt
                positive_injected = True

        for neg_nid in neg_node_ids:
            if neg_nid in wf and wf[neg_nid].get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"]:
                wf[neg_nid]["inputs"]["text"] = negative_prompt
                negative_injected = True

        # Fallback: Search for {{positive}} and {{negative}} placeholders
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

        # Attach LoRA chain if enabled
        enabled_loras = [l for l in (loras or []) if l.is_enabled]
        if enabled_loras and "model" in wf[ksampler_nid].get("inputs", {}):
            initial_model = wf[ksampler_nid]["inputs"]["model"]
            clip_link = None
            for pos_nid in pos_node_ids:
                if pos_nid in wf and "clip" in wf[pos_nid].get("inputs", {}):
                    clip_link = wf[pos_nid]["inputs"]["clip"]
                    break

            digit_ids = [int(k) for k in wf.keys() if k.isdigit()]
            start_id = (max(digit_ids) if digit_ids else 100) + 1

            new_model, new_clip = _attach_lora_chain(
                prompt_nodes=wf,
                initial_model=initial_model,
                initial_clip=clip_link,
                loras=enabled_loras,
                start_node_id=start_id
            )

            wf[ksampler_nid]["inputs"]["model"] = new_model
            if new_clip:
                for pos_nid in pos_node_ids:
                    if pos_nid in wf and "clip" in wf[pos_nid].get("inputs", {}):
                        wf[pos_nid]["inputs"]["clip"] = new_clip
                for neg_nid in neg_node_ids:
                    if neg_nid in wf and "clip" in wf[neg_nid].get("inputs", {}):
                        wf[neg_nid]["inputs"]["clip"] = new_clip

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

    # Dynamic LoRA Loader chain
    current_model, current_clip = _attach_lora_chain(
        prompt_nodes=prompt_nodes,
        initial_model=["1", 0],
        initial_clip=["2", 0],
        loras=loras,
        start_node_id=100
    )

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
