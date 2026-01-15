from openai import AsyncOpenAI
from core.config import get_settings
from core.audit import AuditLog
from tools.weather import get_weather_forecast
from tools.internal import get_fields_via_bridge
import json

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Tool Definitions for OpenAI
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_fields",
            "description": "Get the user's fields, crops, and locations.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather forecast for a specific location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "days": {"type": "integer", "default": 7}
                },
                "required": ["lat", "lon"]
            }
        }
    }
]

async def process_user_query(message: str, context: dict, plan: object):
    """
    Main Agent Loop:
    1. System Prompt (Constraint)
    2. User Query
    3. Function Execution Loop
    4. Final Answer
    """
    
    system_prompt = f"""
    You are the Yieldera AI Risk Analyst, a Senior Agricultural Consultant.
    Your goal is to provide expert, data-driven advice to the user ({context.get('user_name')}, Role: {context.get('role')}).
    
    PLAN: {json.dumps(plan.model_dump())}
    
    ### DATA INSTRUCTIONS
    1. **USE THE DB:** The `get_fields` tool returns `risk_score`, `risk_reason` (summary), and `growth_stage`. USE THEM.
    2. **DO NOT GUESS:** If the tool says `risk_score` is 0, the field is SAFE. Do not invent "potential risks" unless asked for general knowledge.
    3. **BE SPECIFIC:** Refer to fields by Name and ID (e.g., "Field Alpha (ID: 102)").
    
    ### STYLE GUIDELINES
    1. **Human & Professional:** Speak like a colleague, not a robot. Avoid phrases like "Based on the provided data" or "I have processed your request."
    2. **Direct:** Start with the answer. "You have 3 high-risk fields."
    3. **Confidence:** If the database says it's high risk, say it's high risk.
    
    ### CRITICAL RULES
    - If `risk_score` > 0, that field is your PRIORITY. highlight it.
    - If `growth_stage` is 'Late-season', mention harvest planning.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    # Audit Start
    AuditLog.log_event(context.get('user_id'), "START_TURN", {"query": message})
    
    # 1. First Call (Reasoning)
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto"
    )
    
    response_msg = response.choices[0].message
    tool_calls = response_msg.tool_calls
    
    # 2. Tool Execution Loop
    if tool_calls:
        messages.append(response_msg) # Extend conversation with assistant's thought
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            tool_result = None
            
            if function_name == "get_fields":
                tool_result = get_fields_via_bridge(context)
            elif function_name == "get_weather":
                tool_result = get_weather_forecast(args['lat'], args['lon'])
                
            # Feed result back
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_result)
            })
            
            AuditLog.log_event(context.get('user_id'), "TOOL_RESULT", {"tool": function_name})

        # 3. Final Answer after tools
        final_response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages
        )
        answer = final_response.choices[0].message.content
        
    else:
        # No tools needed
        answer = response_msg.content

    AuditLog.log_decision(context.get('user_id'), message, answer, [t.function.name for t in (tool_calls or [])])
    return answer
