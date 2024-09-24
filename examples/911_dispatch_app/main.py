# main.py

from typing import List
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from function_chain_coordinator import CoordinatorInstance, FunctionResponse
import example_911_dispatcher  # Ensure dispatcher functions are registered
import os
import logging
import asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow CORS for development (adjust as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# To ensure the dispatcher functions are registered
example_911_dispatcher.setup_dispatcher()

# In-memory storage for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket connection closed.")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message via WebSocket: {e}")

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/dispatch", response_class=HTMLResponse)
async def dispatch_call(request: Request, description: str = Form(...)):
    dispatch_id = id(description)  # Simple unique identifier based on object id
    
    # Get the coordinator instance
    coordinator = CoordinatorInstance.get_instance()
    
    # Run the coordinator with the description
    function_response: FunctionResponse = coordinator.run(description)
    
    # Extract the final output
    final_output = function_response.final_output
    
    return templates.TemplateResponse("result.html", {
        "request": request,
        "description": description,
        "dispatch_id": dispatch_id,
        "final_output": final_output
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open
            data = await websocket.receive_text()
            # You can handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/dispatch", response_class=JSONResponse)
async def receive_dispatch_data(data: dict):
    """
    Endpoint to receive callback data from the dispatcher functions.
    Broadcasts the data to all connected WebSocket clients.
    """
    logger.info(f"Received dispatch data: {data}")
    await manager.broadcast(data)
    return {"status": "success"}

# Background task to run the dispatcher
@app.on_event("startup")
async def startup_event():
    # Initialize the Coordinator and register dispatcher functions
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("Please set the OPENAI_API_KEY environment variable.")
        raise ValueError("OPENAI_API_KEY not set.")

    custom_system_prompt = "You are ChatGPT, a helpful function chain coordinator for a 911 dispatch system."
    CoordinatorInstance.initialize(openai_api_key=OPENAI_API_KEY, system_prompt=custom_system_prompt)
    coordinator = CoordinatorInstance.get_instance()

    # Register callback to send data to the FastAPI endpoint
    import requests

    def send_to_webserver(coordinator_instance, system_state):
        """
        Callback function to send execution data to the FastAPI web server.
        """
        payload = {
            "current_node": system_state["current_node"],
            "input_value": system_state["input_value"],
            "output_value": system_state["output_value"],
            "steps": [step.dict() for step in system_state["steps"]]
        }
        try:
            response = requests.post("http://localhost:8000/api/dispatch", json=payload)
            response.raise_for_status()
            logger.info("Successfully sent data to the web server.")
        except requests.RequestException as e:
            logger.error(f"Failed to send data to the web server: {e}")

    coordinator.add_callback("after_node_execution", send_to_webserver)

    logger.info("FastAPI application startup complete.")


