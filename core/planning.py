from pydantic import BaseModel, Field
from typing import List
from openai import AsyncOpenAI
from core.config import get_settings
from core.audit import AuditLog

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class AIPlan(BaseModel):
    goal: str = Field(..., description="What needs to be achieved")
    required_info: List[str] = Field(..., description="Information needed (e.g. 'Field Location', 'Weather Forecast')")
    tools_needed: List[str] = Field(..., description="Tools to use (e.g. 'get_fields', 'get_weather')")

async def create_plan(message: str, context: dict) -> AIPlan:
    """
    Reasoning Step: Generates a plan of execution before taking action.
    """
    system_prompt = f"""
    You are the Strategic Planner for Yieldera AI.
    User Role: {context.get('role')}
    
    Your job is to breakdown the user's request into a concrete plan.
    Available Tools:
    - get_fields: List user's fields and locations.
    - get_weather: Forecast for a specific coordinate.
    - index_calc: Pricing engine.
    
    Output JSON.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # Use cheaper model for planning
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            functions=[{
                "name": "submit_plan",
                "description": "Submit the execution plan",
                "parameters": AIPlan.model_json_schema()
            }],
            function_call={"name": "submit_plan"}
        )
        
        args = response.choices[0].message.function_call.arguments
        import json
        plan_dict = json.loads(args)
        return AIPlan(**plan_dict)

    except Exception:
        # Fallback plan if planning fails
        return AIPlan(goal="Answer directly", required_info=[], tools_needed=[])
