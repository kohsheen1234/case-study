import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from core.routers import router
import uvicorn

# Load environment variables from the .env file
load_dotenv()

app = FastAPI()

# Retrieve the secret key from the .env file
secret_key = os.getenv("SECRET_KEY")

app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Add session middleware with the secret key
# Allow CORS from any origin (allow_origins=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def read_root():
    return {"Hello": "World"}

app.include_router(
    router,
    prefix="",
)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

