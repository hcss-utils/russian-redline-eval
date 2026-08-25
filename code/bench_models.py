"""Model registry for the RedLineBench demo run.

NATIVE APIs ONLY. OpenRouter is deliberately excluded: for open-weight models it
load-balances across third-party hosts serving quantized/stale weights, so any
number it produces measures a random host, not the model.

`model` strings for the non-OpenAI/Anthropic providers are UNVERIFIED until the
probe run confirms them -- treat a probe failure as "find the real id", never as
"substitute a neighbouring model".
"""
OAI_COMPAT = "openai_compatible"

MODELS = [
    # --- Anthropic (native SDK) -------------------------------------------------
    dict(key="fable-5",        provider="anthropic", model="claude-fable-5",   reasoning=True,  note="thinking always on; cannot be disabled"),
    dict(key="opus-5-think",   provider="anthropic", model="claude-opus-5",    reasoning=True),
    dict(key="opus-5-nothink", provider="anthropic", model="claude-opus-5",    reasoning=False, note="paired control for the reasoning axis"),
    dict(key="sonnet-5",       provider="anthropic", model="claude-sonnet-5",  reasoning=True),
    dict(key="haiku-4.5",      provider="anthropic", model="claude-haiku-4-5", reasoning=False),

    # --- OpenAI -----------------------------------------------------------------
    dict(key="gpt-5.6-sol",   provider="openai", model="gpt-5.6-sol",   reasoning=True),
    dict(key="gpt-5.6-terra", provider="openai", model="gpt-5.6-terra", reasoning=True),
    dict(key="gpt-5.6-luna",  provider="openai", model="gpt-5.6-luna",  reasoning=True),

    # --- Google -----------------------------------------------------------------
    dict(key="gemini-3.6-flash", provider="gemini", model="gemini-3.6-flash", reasoning=True),

    # --- OpenAI-compatible third parties (native endpoints) ---------------------
    dict(key="deepseek-v4-pro",   provider=OAI_COMPAT, model="deepseek-v4-pro",
         base_url="https://api.deepseek.com/v1", key_env="DEEPSEEK_API_KEY", reasoning=True),
    dict(key="deepseek-v4-flash", provider=OAI_COMPAT, model="deepseek-v4-flash",
         base_url="https://api.deepseek.com/v1", key_env="DEEPSEEK_API_KEY", reasoning=True),
    dict(key="qwen3.7-max",       provider=OAI_COMPAT, model="qwen3.7-max",
         base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1", key_env="DASHSCOPE_API_KEY", reasoning=True),
    dict(key="glm-5.2",           provider=OAI_COMPAT, model="glm-5.2",
         base_url="https://open.bigmodel.cn/api/paas/v4", key_env="GLM_API_KEY", reasoning=True),
    dict(key="kimi-k3",           provider=OAI_COMPAT, model="kimi-k3",
         base_url="https://api.moonshot.ai/v1", key_env="MOONSHOT_API_KEY", reasoning=True),
    dict(key="minimax-m3",        provider=OAI_COMPAT, model="MiniMax-M3",
         base_url="https://api.minimax.io/v1", key_env="MINIMAX_API_KEY", reasoning=True,
         note="native endpoint per rule 6d; emits <think>...</think> before JSON"),
]

BY_KEY = {m["key"]: m for m in MODELS}
