"""FinGPT model yükleme — LoRA adapter Llama-2 üzerine bindirilir.

Akış (sentiment ve forecaster için aynı):
    1. Llama-2 base modeli yükle (4-bit GPU ya da fp16)
    2. FinGPT LoRA adapter'ı PEFT ile bindir
    3. Singleton döndür
"""
from __future__ import annotations

from functools import lru_cache

import torch
from loguru import logger
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from app.config import settings


def _device() -> str:
    if settings.device != "auto":
        return settings.device
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _bnb_config() -> BitsAndBytesConfig | None:
    if not settings.load_in_4bit or _device() != "cuda":
        return None
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )


@lru_cache(maxsize=1)
def load_sentiment():
    device = _device()
    logger.info(f"FinGPT-Sentiment yükleniyor → device={device}, base={settings.base_llama_model}")
    bnb = _bnb_config()
    tokenizer = AutoTokenizer.from_pretrained(
        settings.base_llama_model, token=settings.hf_token, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    kwargs = {"token": settings.hf_token, "trust_remote_code": True}
    if bnb:
        kwargs["quantization_config"] = bnb
        kwargs["device_map"] = "auto"
    else:
        kwargs["torch_dtype"] = torch.float16 if device != "cpu" else torch.float32

    base = AutoModelForCausalLM.from_pretrained(settings.base_llama_model, **kwargs)
    model = PeftModel.from_pretrained(base, settings.sentiment_model, token=settings.hf_token)
    model.eval()
    if not bnb:
        model = model.to(device)
    return tokenizer, model, device


@lru_cache(maxsize=1)
def load_forecaster():
    device = _device()
    logger.info(f"FinGPT-Forecaster yükleniyor → device={device}")
    bnb = _bnb_config()
    tokenizer = AutoTokenizer.from_pretrained(
        settings.base_llama_model, token=settings.hf_token, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    kwargs = {"token": settings.hf_token, "trust_remote_code": True}
    if bnb:
        kwargs["quantization_config"] = bnb
        kwargs["device_map"] = "auto"
    else:
        kwargs["torch_dtype"] = torch.float16 if device != "cpu" else torch.float32

    base = AutoModelForCausalLM.from_pretrained(settings.base_llama_model, **kwargs)
    model = PeftModel.from_pretrained(base, settings.forecaster_model, token=settings.hf_token)
    model.eval()
    if not bnb:
        model = model.to(device)
    return tokenizer, model, device
