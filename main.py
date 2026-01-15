from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from core.config import get_settings
from core.rate_limit import check_rate_limit

# Initialize App
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "service": "Yieldera AI Backend",
        "status": "operational",
        "mode": settings.ENV
    }

@app.get("/health")
def health_check():
    # TODO: Check Redis & OpenAI Connection
    return {"status": "ok"}

# ... imports ...
from schemas.request import ChatRequest
from core.planning import create_plan
from core.agent import process_user_query

# ... setup ...

@app.post("/chat")
async def chat_endpoint(request_data: ChatRequest):
    """
    Main Chat Interface.
    1. Rate Limit
    2. Plan
    3. Execute
    """
    user_id = request_data.context.user_id
    
    # 1. Check Rate Limit
    limit_info = await check_rate_limit(user_id)
    
    # 2. Plan (Reasoning)
    context_dict = request_data.context.model_dump()
    plan = await create_plan(request_data.message, context_dict)
    
    # 3. Execute (Agent)
    try:
        answer = await process_user_query(request_data.message, context_dict, plan)
    except Exception as e:
        # Fallback if OpenAI fails
        print(f"Agent Error: {e}")
        answer = "I apologize, but my connection to the Risk Engine was interrupted. Please try again in a moment."
    
    return {
        "response": answer,
        "plan": plan.model_dump(), # Exposure for debugging/UI
        "usage": limit_info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
