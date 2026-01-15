from openai import AsyncOpenAI
from core.config import get_settings
from core.audit import AuditLog
from tools.weather import get_weather_forecast
from tools.historical_weather import get_historical_weather
from tools.internal import get_fields_via_bridge
from tools.vegetation import get_vegetation_health
from tools.alerts import get_alerts_from_system, create_alert_in_system
from tools.insurance import get_insurance_quote
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_weather",
            "description": "Get HISTORICAL weather data (past temperatures) using dual consensus module (OpenMeteo + NASA POWER). IMPORTANT: Use field_id when asking about a specific field - this ensures accurate coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_id": {"type": "integer", "description": "Field ID (PREFERRED - use this when user asks about a field)"},
                    "lat": {"type": "number", "description": "Latitude (optional if field_id provided)"},
                    "lon": {"type": "number", "description": "Longitude (optional if field_id provided)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"}
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "Get active alerts from the REAL alerts system (NOT portfolio data). Use this when user asks about alerts, warnings, notifications, or configured monitoring rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["active", "all"], "default": "active"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": "Create a new weather/field alert with email notifications. Parse natural language like 'alert me when temp > 40 for field X' into structured parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_name": {"type": "string", "description": "Name of the field (e.g., 'Combined', 'Field Alpha')"},
                    "alert_type": {"type": "string", "enum": ["temperature", "windspeed", "rainfall", "ndvi"], "description": "Type of alert"},
                    "threshold": {"type": "number", "description": "Threshold value (e.g., 40 for temperature)"},
                    "operator": {"type": "string", "enum": [">", "<", ">=", "<=", "="], "description": "Comparison operator"},
                    "email": {"type": "string", "description": "Email address for notifications"}
                },
                "required": ["field_name", "alert_type", "threshold", "operator", "email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_insurance_quote",
            "description": "Generate crop insurance quotes. Supports 3 methods: field-based ('quote field P60'), coordinates ('quote lat -17.82, lon 30.99'), or region ('quote Mazowe'). Returns premium, sum insured, and AI risk analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quote_type": {"type": "string", "enum": ["field", "coordinates", "region"], "description": "Quote method"},
                    "field_id": {"type": "integer", "description": "Field ID (required if quote_type='field')"},
                    "latitude": {"type": "number", "description": "Latitude (required if quote_type='coordinates')"},
                    "longitude": {"type": "number", "description": "Longitude (required if quote_type='coordinates')"},
                    "region_name": {"type": "string", "description": "Region name like 'Mazowe' (required if quote_type='region')"},
                    "expected_yield": {"type": "number", "description": "Expected yield tons/ha (default: 5.0)"},
                    "price_per_ton": {"type": "number", "description": "Price per ton in $ (default: 300)"},
                    "year": {"type": "integer", "description": "Quote year (optional, defaults to next season)"},
                    "crop": {"type": "string", "description": "Crop type (default: 'maize')"},
                    "deductible_rate": {"type": "number", "description": "Deductible as decimal (default: 0.05 = 5%)"},
                    "area_ha": {"type": "number", "description": "Area in hectares (optional)"}
                },
                "required": ["quote_type"]
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
    
    ### CRITICAL: NEVER MAKE UP DATA
    1. **ONLY USE TOOL DATA:** You can ONLY provide information that comes from your tools.
    2. **NO GUESSING:** If you don't have access to specific data (historical weather, past NDVI, etc.), say "I don't have access to that data" - DO NOT invent numbers.
    3. **WEATHER TOOLS - DATE AWARENESS (CRITICAL):**
       - **Current date context**: It is January 2026
       - If user asks about dates BEFORE January 2026 (e.g., "July 2025", "June 2025") → Use `get_historical_weather` (PAST data)
       - If user asks about dates AFTER January 2026 (e.g., "next week", "February 2026") → Use `get_weather` (7-day FORECAST)
       - **NEVER say "forecasted" for past dates** - past data is historical, not forecasted
    4. **VEGETATION LIMITATIONS:** You can only check NDVI for specific past dates if the user provides a date. You cannot make up NDVI values.
    
    ### CONTEXT AWARENESS (CRITICAL)
    1. **TRACK CONVERSATION:** Pay close attention to the previous question's intent.
    2. **FOLLOW-UP QUESTIONS:** If user asks "what about field X?" after a data query, they want THE SAME DATA for field X.
       - Example: If they asked "lowest temp for field A in July" then ask "what about field B?" → Answer: lowest temp for field B in July (same query, different field)
    3. **DON'T JUST DESCRIBE:** If they already got data for one field and ask about another, DON'T just describe the field - provide the SAME type of data.
    
    ### DATA INSTRUCTIONS
    1. **USE THE DB:** The `get_fields` tool returns `risk_score`, `risk_reason`, and `growth_stage`. USE THEM.
    2. **DO NOT GUESS:** If asking about a specific field (e.g. "Field Alpha"), you MUST first call `get_fields` to find its ID, then use that ID for other tools (like `get_vegetation_health`).
    3. **VEGETATION CHECKS:** To check vegetation/NDVI, you need a Field ID and a Date. Find the ID first.
    4. **ALERTS:** Use `get_alerts` for alert queries, NOT portfolio data.
    5. **HISTORICAL WEATHER LIMITATION:** The `get_historical_weather` tool requires latitude and longitude coordinates. Field data does NOT include coordinates. 
       - If user asks for historical weather for a specific field, politely explain: "I don't have access to the coordinates for that field. You can check historical weather using the Frost Monitor page for field-specific data."
    6. **INSURANCE QUOTES - PDF DOWNLOAD (CRITICAL):**
       - When user requests an insurance quote, provide:
         1. The PDF download URL on its own line (plain URL, not markdown)
         2. Only 2-3 key numbers (Sum Insured, Premium, Rate)
       - Example response format:
         "Your insurance quote is ready. Download the full PDF report here:
         
         https://yieldera.net/dashboard/pricing.html?quote_id=XXX
         
         Sum Insured: $1,500 | Premium: $170.81 | Rate: 9.65%"
       - DO NOT add extra explanations or descriptions - keep it brief
       - The PDF contains all details, so you don't need to repeat everything
    
    ### STYLE GUIDELINES
    1. **Human & Professional:** Speak like a colleague. Be direct.
    2. **Confidence:** If data is missing, say so. If data exists, quote it.
    3. **Honesty:** "I don't have access to that data" is better than making up numbers.
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
                elif function_name == "get_historical_weather":
                    tool_result = get_historical_weather(
                        field_id=args.get("field_id"),
                        lat=args.get("lat"),
                        lon=args.get("lon"),
                        start_date=args.get("start_date"),
                        end_date=args.get("end_date")
                    )
                elif function_name == "get_alerts":
                    tool_result = get_alerts_from_system(context, args.get('status', 'active'))
                elif function_name == "create_alert":
                    tool_result = create_alert_in_system(
                        context,
                        args.get("field_name"),
                        args.get("alert_type"),
                        args.get("threshold"),
                        args.get("operator"),
                        args.get("email")
                    )
                elif function_name == "get_insurance_quote":
                    tool_result = get_insurance_quote(
                        context,
                        quote_type=args.get("quote_type"),
                        field_id=args.get("field_id"),
                        latitude=args.get("latitude"),
                        longitude=args.get("longitude"),
                        region_name=args.get("region_name"),
                        expected_yield=args.get("expected_yield", 5.0),
                        price_per_ton=args.get("price_per_ton", 300.0),
                        year=args.get("year"),
                        crop=args.get("crop", "maize"),
                        deductible_rate=args.get("deductible_rate", 0.05),
                        area_ha=args.get("area_ha")
                    )
                else:
                    tool_result = {"error": f"Unknown tool: {function_name}"}
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

