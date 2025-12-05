"""
FastAPI Backend for Cloud AI Bank Onboarding
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agent import conv_agent

# Initialize FastAPI app
app = FastAPI(
    title="Cloud AI Bank Onboarding API",
    description="API for banking customer onboarding with AI agent",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"], # Allow ony GET, POST etc
    allow_headers=["*"], # Contorls which requests headers are allowed
)


# Request/Response Models
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    message: str


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        message="Cloud AI Bank Onboarding API is running"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for conversing with the onboarding agent
    
    - **session_id**: Unique identifier for the conversation session
    - **message**: User's message
    """
    try:
        # Invoke agent with session management
        response = conv_agent.invoke(
            {"input": request.message},
            config={"configurable": {"session_id": request.session_id}}
        )
        
        # Extract output from agent response
        agent_response = response.get("output", "")
        
        return ChatResponse(
            response=agent_response,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "Cloud AI Bank Onboarding API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST)",
            "docs": "/docs"
        }
    }


# Run with: uvicorn src.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)