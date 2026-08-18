
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from hermes.models.deps import Settings

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

deps = Settings()

@log
def generate_ollama_model(model:str = 'gpt-oss:120b-cloud'):
    ollama_model = OpenAIChatModel(
    model_name=model,
    provider=OllamaProvider(base_url='https://ollama.com/v1', api_key=deps.OLLAMA_API_KEY)  
)
    return ollama_model