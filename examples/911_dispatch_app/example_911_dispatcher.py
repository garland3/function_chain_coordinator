# example_911_dispatcher.py
from openai import OpenAI
from function_chain_coordinator import CoordinatorInstance, register_function, FunctionResponse, CallbackPoints
import logging
import os
# Configure logging
logger = logging.getLogger(__name__)

# Initialize the Coordinator (ensure this is done before registering callbacks and functions)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

custom_system_prompt = "You are ChatGPT, a helpful function chain coordinator for a 911 dispatch system."
CoordinatorInstance.initialize(openai_api_key=OPENAI_API_KEY, system_prompt=custom_system_prompt)
coordinator = CoordinatorInstance.get_instance()

# Define a callback function
def send_to_webserver(coordinator_instance, system_state):
    """
    Callback function to send execution data to the web server.
    """
    import requests
    # Example payload; modify as needed
    payload = {
        "current_node": system_state["current_node"],
        "input_value": system_state["input_value"],
        "output_value": system_state["output_value"],
        "steps": [step.dict() for step in system_state["steps"]]
    }
    try:
        response = requests.post("http://your-webserver-endpoint/api/dispatch", json=payload)
        response.raise_for_status()
        logger.info("Successfully sent data to the web server.")
    except requests.RequestException as e:
        logger.error(f"Failed to send data to the web server: {e}")

# Register the callback to desired points
coordinator.add_callback(CallbackPoints.AFTER_NODE_EXECUTION, send_to_webserver)

# Register your dispatcher functions as before
@register_function(
    input_type=str,
    output_type=str,
    description_for_routing="Receives the emergency call description from the user."
)
def receive_call(description: str) -> str:
    """
    Receives the emergency call description from the user.
    """
    logger.info(f"Received emergency call: {description}")
    return description

@register_function(
    input_type=str,
    output_type=str,
    is_router=True,
    direction_prompt=("You are deciding which public service to dispatch based on the emergency description.\n"),
    description_for_routing="Router to choose the next public service function based on the emergency description."
)
def router(description: str) -> str:
    # This function's logic is handled by the RouterNode and LLM
    return description

@register_function(
    input_type=str,
    output_type=int,
    description_for_routing="Communicates with the user to gather more information and determines the number of police resources to send."
)
def police_communicator(description: str) -> int:
    """
    Communicates with the user to gather more information and determines the number of police resources to send.
    """
    logger.info("Police Communicator activated.")
    user_response = get_user_response("Police: ")
    num_officers = determine_resources("police", user_response)
    logger.info(f"Dispatching {num_officers} police officer(s) to the location.")
    return num_officers

@register_function(
    input_type=str,
    output_type=int,
    description_for_routing="Communicates with the user to gather more information and determines the number of fire resources to send."
)
def fire_communicator(description: str) -> int:
    """
    Communicates with the user to gather more information and determines the number of fire resources to send.
    """
    logger.info("Fire Communicator activated.")
    user_response = get_user_response("Firefighter: ")
    num_engines = determine_resources("fire", user_response)
    logger.info(f"Dispatching {num_engines} fire engine(s) to the location.")
    return num_engines

@register_function(
    input_type=str,
    output_type=int,
    description_for_routing="Communicates with the user to gather more information and determines the number of EMS resources to send."
)
def ems_communicator(description: str) -> int:
    """
    Communicates with the user to gather more information and determines the number of EMS resources to send.
    """
    logger.info("EMS Communicator activated.")
    user_response = get_user_response("Paramedic: ")
    num_ambulances = determine_resources("ems", user_response)
    logger.info(f"Dispatching {num_ambulances} ambulance(s) to the location.")
    return num_ambulances

def get_user_response(prompt: str) -> str:
    """
    Simulates getting a response from the user. In a real system, this would capture user input.
    For demonstration, we'll use predefined responses based on the description.
    """
    # Placeholder for user interaction
    return "default response"

def determine_resources(service_type: str, user_response: str) -> int:
    """
    Determines the number of resources to send based on the service type and user response.
    This function uses the LLM to decide based on user responses.
    """
    direction_prompt = f"""
You are a dispatcher for the {service_type.upper()} department.
Based on the user's response: "{user_response}", determine how many {service_type} resources to send.
Provide a single integer representing the number of resources.
"""
    system_prompt = f"You are a dispatcher for the {service_type.upper()} department."
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": direction_prompt}
            ],
            max_tokens=10,
            n=1,
            stop=None,
            temperature=0.0,
        )
        num_resources_str = response.choices[0].message.content.strip()
        num_resources = int(num_resources_str)
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error determining resources: {e}. Defaulting to 1.")
        num_resources = 1  # Default to 1 if parsing fails
    return num_resources

# # Create edges between functions
# coordinator.create_edge(receive_call, router)               # receive_call -> router
# coordinator.create_edge(router, police_communicator)        # router -> police_communicator
# coordinator.create_edge(router, fire_communicator)          # router -> fire_communicator
# coordinator.create_edge(router, ems_communicator)           # router -> ems_communicator
def setup_dispatcher():
    """
    Sets up the dispatcher by creating edges between functions.
    """
    coordinator = CoordinatorInstance.get_instance()
    coordinator.create_edge(receive_call, router)               # receive_call -> router
    coordinator.create_edge(router, police_communicator)        # router -> police_communicator
    coordinator.create_edge(router, fire_communicator)          # router -> fire_communicator
    coordinator.create_edge(router, ems_communicator)           # router -> ems_communicator
    return coordinator