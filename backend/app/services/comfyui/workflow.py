import random
import json
from typing import Dict, Any, List, Optional
from app.models.prompt_engine import LoraBuildItem

def build_anima_29b_workflow(
    positive_prompt: str,
    negative_prompt: str,
    checkpoint: str = "anima-preview.safetensors",
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
    Constructs an authentic Anima-2.9B ComfyUI workflow.
    If custom_template is provided, replaces prompt/negative/seed/steps/cfg nodes dynamically.
    """
    if seed is None or seed == -1:
        seed = random.randint(1, 1125899906842624)

    if custom_template:
        # Clone custom workflow and substitute key parameters
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
            elif class_type in ["CheckpointLoaderSimple"]:
                if checkpoint:
                    inputs["ckpt_name"] = checkpoint
        return wf

    # Standard Anima-2.9B txt2img workflow
    prompt_nodes: Dict[str, Any] = {}

    # Node 4: Checkpoint Loader
    prompt_nodes["4"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": checkpoint
        }
    }

    current_model = ["4", 0]
    current_clip = ["4", 1]
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

    # Node 5: Empty Latent Image (Default Anima 1024x1536)
    prompt_nodes["5"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": width,
            "height": height,
            "batch_size": batch_size
        }
    }

    # Node 3: KSampler (Anima 2.9B settings: euler + sgm_uniform / beta, cfg 4.5)
    prompt_nodes["3"] = {
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

    # Node 8: VAE Decode
    prompt_nodes["8"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    }

    # Node 9: Save Image
    prompt_nodes["9"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "Anima29B_ImageForge",
            "images": ["8", 0]
        }
    }

    return prompt_nodes
