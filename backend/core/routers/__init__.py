from fastapi import APIRouter, Request, HTTPException

from core.controllers.ai_agent import ask_agent

router = APIRouter()


@router.get("/agent/")
async def get_ai_message(message: str, request: Request):
    """
    Handle incoming requests from the frontend, pass the message to the AI agent,
    and return the AI's response with session memory.

    """
    try:
        _ = request.session.get("memory_key", "")  # You can track user sessions here for specific memory

        # Ask the agent the question
        response = ask_agent(message)
        return {"response": response}
    
    except Exception as e:
        # Log the error and return an HTTP 500 error
        print(f"Error processing the stupid request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



   