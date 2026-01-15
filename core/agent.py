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
    You are the Yieldera AI Risk Analyst.
    Your goal is to provide specific, actionable agricultural advice.
    User Role: {context.get('role')}
    User Name: {context.get('user_name')}
    
    PLAN: {json.dumps(plan.model_dump())}
    
    1. Use the Tools defined in the Plan.
    2. Be concise. Start with the most important risk or action.
    3. Do not invent data. If tool fails, say "I cannot access that data right now."
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
