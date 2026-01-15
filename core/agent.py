from openai import AsyncOpenAI
from core.config import get_settings
from core.audit import AuditLog
from tools.weather import get_weather_forecast
from tools.weather import get_weather_forecast
from tools.internal import get_fields_via_bridge
from tools.vegetation import get_vegetation_health
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_vegetation_health",
            "description": "Get historical vegetation health (NDVI) for a specific field and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_id": {
                        "type": "integer",
                        "description": "The ID of the field to analyze."
                    },
                    "date": {
                        "type": "string",
                        "description": "The target date in YYYY-MM-DD format."
                    }
                },
                "required": ["field_id", "date"]
            }
        }
    }
]

async def process_user_query(message: str, context: dict, plan: object, history: list = []):
    """
    Main Agent Loop (Multi-Step):
    1. System Prompt
    2. Append History (Context)
    3. User Query
    4. Reasoning Loop (While Needs Tools -> Execute -> Feed Back -> Repeat)
    5. Final Answer
    """
    
    system_prompt = f"""
    You are the Yieldera AI Risk Analyst, a Senior Agricultural Consultant.
    Your goal is to provide expert, data-driven advice to the user ({context.get('user_name')}, Role: {context.get('role')}).
    
    PLAN: {json.dumps(plan.model_dump())}
    
    ### DATA INSTRUCTIONS
    1. **USE THE DB:** The `get_fields` tool returns `risk_score`, `risk_reason`, and `growth_stage`. USE THEM.
    2. **DO NOT GUESS:** If asking about a specific field (e.g. "Field Alpha"), you MUST first call `get_fields` to find its ID, then use that ID for other tools (like `get_vegetation_health`).
    3. **VEGETATION CHECKS:** To check vegetation/NDVI, you need a Field ID and a Date. Find the ID first.
    
    ### STYLE GUIDELINES
    1. **Human & Professional:** Speak like a colleague. Be direct.
    2. **Confidence:** If data is missing, say so. If data exists, quote it.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append History (limited to last 10 messages to save context window)
    for msg in history[-10:]:
        messages.append({"role": msg.get("role"), "content": msg.get("content")})
        
    messages.append({"role": "user", "content": message})
    
    # Audit Start
    AuditLog.log_event(context.get('user_id'), "START_TURN", {"query": message})
    
    # Multi-Step Tool Loop
    MAX_STEPS = 5
    step = 0
    
    while step < MAX_STEPS:
        step += 1
        
        # 1. Ask Model
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        
        response_msg = response.choices[0].message
        tool_calls = response_msg.tool_calls
        
        # 2. If no tools, we are done
        if not tool_calls:
            AuditLog.log_decision(context.get('user_id'), message, response_msg.content, [])
            return response_msg.content
            
        # 3. Execute Tools
        messages.append(response_msg) # Add AI thought to context
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            tool_result = None
            
            try:
                if function_name == "get_fields":
                    tool_result = get_fields_via_bridge(context)
                elif function_name == "get_weather":
                    tool_result = get_weather_forecast(args['lat'], args['lon'])
                elif function_name == "get_vegetation_health":
                    tool_result = get_vegetation_health(context, args['field_id'], args['date'])
            except Exception as e:
                tool_result = {"error": str(e)}
                
            # Feed result back
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_result)
            })
            
            AuditLog.log_event(context.get('user_id'), "TOOL_EXECUTION", {"tool": function_name})
            
    # Fallback if max steps reached
    return "I needed to perform too many steps to answer this. Please try narrowing down your request."

