#The goal here is to incorporate inline evals after every response
# Factualness , hallucination, etc. This will just be an LLM Judge call
# Can use pydantic AI's built in evaluator
from pydantic_ai import Agent, ModelSettings
from hermes.agents.helpers import generate_ollama_model
import json

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#maybe we should pass run context in here
#TODO , should this be async , how would it work in the CLI loop
@log
async def inline_evals(user_prompt: str, output: str) -> dict:
    eval_judge = Agent(
        model=generate_ollama_model(),
        instructions="""
        You are an LLM judge. Evaluate the agent output against the user prompt.

        Rubric — score each from 0.0 to 1.0:
        - hallucination: 1.0 = no hallucination, 0.0 = fully hallucinated
        - factualness:   1.0 = fully factual,    0.0 = entirely inferred/fabricated
        - obsidian_brain_ground: 1.0 = agent called obisidan brain, it returned results, the agent used results, 0.0 = agent called obsidian brain, 
        results were returned, and agent ignored results, 0.5: default if not results returned from obsidian brain.

        Output ONLY valid JSON, no preamble, no markdown, no explanation:
        {"hallucination": 0.9, "factualness": 0.8, "obsidian_brain_ground": 0.5}
        """,
        model_settings=ModelSettings(
            max_tokens=200,
            temperature=0.0
        )
    )

    result = await eval_judge.run(
        user_prompt=f"user_prompt: {user_prompt}\noutput: {output}"
    )

    try:
        clean = result.output.strip().replace("```json", "").replace("```", "")
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"hallucination": None, "factualness": None, "error": result.output}