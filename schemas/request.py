from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserContext(BaseModel):
    user_id: str = Field(..., description="Unique User ID from PHP Session")
    user_name: str
    role: str = Field("farmer", description="miner, farmer, insurer, etc.")
    entity_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1000)
    context: UserContext
    conversation_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Is it safe to plant maize tomorrow?",
                "context": {
                    "user_id": "123",
                    "user_name": "Kudzai",
                    "role": "farmer"
                }
            }
        }

class AIResponse(BaseModel):
    answer: str
    tool_calls: List[str] = []
    confidence: float = 1.0
    usage: Dict[str, int] # Token usage
