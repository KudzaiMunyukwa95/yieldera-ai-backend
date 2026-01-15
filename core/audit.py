import logging
import json
from datetime import datetime
from typing import Any, Dict

# Configure Logging to output JSON
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yieldera.audit")

class AuditLog:
    """
    Structured Logger for AI Decisions.
    Ensures every recommendation is traceable.
    """
    
    @staticmethod
    def log_event(
        user_id: str,
        event_type: str,
        details: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ):
        """
        Log an event in a structured JSON format.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "event_type": event_type, # e.g., "USER_QUERY", "TOOL_EXECUTION", "FINAL_ANSWER"
            "details": details,
            "metadata": metadata or {},
            "service": "yieldera-ai-backend"
        }
        
        # Log as a JSON string for Datadog/CloudWatch parsing
        logger.info(json.dumps(entry))

    @staticmethod
    def log_decision(
        user_id: str,
        query: str,
        recommendation: str,
        factors: list
    ):
        """
        Specific logger for Insurance/Advisory logs.
        """
        AuditLog.log_event(user_id, "AI_DECISION", {
            "query": query,
            "recommendation": recommendation,
            "influencing_factors": factors
        })
