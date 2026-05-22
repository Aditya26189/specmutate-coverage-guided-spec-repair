# src/spec_gen.py
from src.llm import call_llm
from templates import SPEC_GEN_PROMPT

def generate_spec(description: str, function_name: str, temperature: float = 0.0) -> str:
    prompt = SPEC_GEN_PROMPT.format(
        description=description,
        function_name=function_name
    )
    return call_llm(prompt, temperature=temperature)
