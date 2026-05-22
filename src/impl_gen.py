# src/impl_gen.py
import json
from src.llm import call_llm
from templates import IMPL_GEN_PROMPT

def generate_implementations(
    description: str,
    signature: str,
    oracle_inputs: list[str],
    n: int = 5
) -> list[str]:
    prompt = IMPL_GEN_PROMPT.format(
        n=n,
        description=description,
        signature=signature,
        oracle_inputs="\n".join(oracle_inputs)
    )
    raw = call_llm(prompt, temperature=0.8)
    try:
        impls = json.loads(raw)
        return [str(impl) for impl in impls[:n]]
    except json.JSONDecodeError:
        # Fallback: split by double newline if JSON fails
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        return blocks[:n]
