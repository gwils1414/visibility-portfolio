#--Placeholder for spinning up subagents--#
from pydantic_ai import Agent
from hermes.models.deps import Settings
from pydantic_ai.settings import ModelSettings
from hermes.agents.helpers import generate_ollama_model
from typing import Literal

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)



#TODO, we can add a tools parameter , if we want to give one deep research capbility for example.
#Import all the tools here, add a literal for tools to add.
#If tools parameter is provided. agent.tool = tool for tool in tools.

@log
async def sub_agent(agent_name:str,
                    instructions:str, 
                    user_prompt:str,
                    model:Literal['gpt-oss:120b-cloud','gemma4:31b-cloud']):
    '''
    This is your tool to spin up a sub agent if you want to..
     1. cross reference a theory
     2. work on something in parallel

    For example, 3 agents all research the best way to build a data pipeline
    All 3 agents return their responses, and you cross reference which responses are consitent, or diverge across the results.
    This helps better educate you for any other decision making.

    Parameters:
     - agent_name : name of the agent you are calling
     - instructions: instructions you want to pass to the agent
     - user_prompt: what you want the agent to do
     - model: model you want to use
    '''
    model = generate_ollama_model(model)
    
    agent = Agent(name = agent_name,
                model = model,
                instructions= instructions,
                model_settings= ModelSettings(
                    max_tokens=10000,
                    timeout = 30
                ))
    #TODO, pass in agent tools from tool list
    #agent.tool = tool
    result = await agent.run(user_prompt=user_prompt)
    return result


#Tools list should stay with the current HITL set up. All tools are set up internally with
#questionary , requiring HTIL
#We can spin up sub agents , but users cannot currently save that agent set up
