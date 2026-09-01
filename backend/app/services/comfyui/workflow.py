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
    clip_type: str = "qwen_image",
    loras: Optional[List[LoraBuildItem]] = None,
    width: int = 1024,
    height: int = 1536,
    batch_size: int = 1,
    steps: int = 28,
    cfg: float = 4.5,
    sampler_name: str = "euler",
    scheduler: str = "sgm_uniform",
    seed: Optional[int] = None,
    custom_template: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs an authentic Anima-2.9B ComfyUI workflow based on official blueprint:
    UNETLoader + CLIPLoader (qwen_3_06b_base) + VAELoader (qwen_image_vae) + KSampler + VAEDecode.
    """
    if seed is None or seed == -1:
        seed = random.randint(1, 1125899906842624)

    if custom_template:
        wf = json.loads(json.dumps(custom_template))
        for _, node in wf.items():
            inputs = node.get("inputs", {})
            class_type = node.get("class_type", "")
            if class_type in ["CLIPTextEncode", "CLIPTextEncodeFlux"]:
                if "text" in inputs:
                    if "{{positive}}" in inputs["text"] or inputs.get("is_positive"):
                        inputs["text"] = positive_prompt
                    elif "{{negative}}" in inputs["text"] or inputs.get("is_negative"):
                        inputs["text"] = negative_prompt
            elif class_type in ["KSampler", "KSamplerAdvanced"]:
                if "seed" in inputs:
                    inputs["seed"] = seed
                if "steps" in inputs:
                    inputs["steps"] = steps
                if "cfg" in inputs:
                    inputs["cfg"] = cfg
                if "sampler_name" in inputs:
                    inputs["sampler_name"] = sampler_name
                if "scheduler" in inputs:
                    inputs["scheduler"] = scheduler
            elif class_type in ["EmptyLatentImage", "EmptySD3LatentImage"]:
                if "width" in inputs:
                    inputs["width"] = width
                if "height" in inputs:
                    inputs["height"] = height
            elif class_type in ["UNETLoader"]:
                if unet_name:
                    inputs["unet_name"] = unet_name
            elif class_type in ["CLIPLoader"]:
                if clip_name:
                    inputs["clip_name"] = clip_name
            elif class_type in ["VAELoader"]:
                if vae_name:
                    inputs["vae_name"] = vae_name
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
    node_id_counter = 10

    # Chain LoRA loaders
    if loras:
        for lora in loras:
            if lora.is_enabled and lora.filename:
                lora_node_id = str(node_id_counter)
                node_id_counter += 1
                prompt_nodes[lora_node_id] = {
                    "class_type": "LoraLoader",
                    "inputs": {
                        "model": current_model,
                        "clip": current_clip,
                        "lora_name": lora.filename,
                        "strength_model": lora.strength,
                        "strength_clip": lora.strength
                    }
                }
                current_model = [lora_node_id, 0]
                current_clip = [lora_node_id, 1]

    # Node 6: Positive Prompt CLIPTextEncode
    prompt_nodes["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": positive_prompt,
            "clip": current_clip
        }
    }

    # Node 7: Negative Prompt CLIPTextEncode
    prompt_nodes["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": negative_prompt,
            "clip": current_clip
        }
    }

    # Node 5: Empty Latent Image (1024x1536)
    prompt_nodes["5"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": width,
            "height": height,
            "batch_size": batch_size
        }
    }

    # Node 8: KSampler (Anima 2.9B: Euler + sgm_uniform / beta, cfg 4.5)
    prompt_nodes["8"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": current_model,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": 1.0
        }
    }

    # Node 9: VAE Decode
    prompt_nodes["9"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["8", 0],
            "vae": ["3", 0]
        }
    }

    # Node 10: Save Image
    prompt_nodes["10"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "Anima29B_ImageForge",
            "images": ["9", 0]
        }
    }

    return prompt_nodes
