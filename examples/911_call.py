# example_911_dispatcher.py

from openai import OpenAI
from function_chain_coordinator import CoordinatorInstance, register_function, FunctionResponse
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Coordinator with your OpenAI API key and an optional system prompt
# You can set your OpenAI API key as an environment variable for security
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this environment variable is set
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# Optional: Define a custom system prompt for the Coordinator
# If not provided, a default prompt is used
custom_system_prompt = "You are ChatGPT, a helpful function chain coordinator for a 911 dispatch system."

CoordinatorInstance.initialize(openai_api_key=OPENAI_API_KEY, system_prompt=custom_system_prompt)
coordinator = CoordinatorInstance.get_instance()

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
                    #   "- If the description indicates a need for police, choose 'police_communicator'.\n"
                    #   "- If the description indicates a need for fire services, choose 'fire_communicator'.\n"
                    #   "- If the description indicates a need for EMS, choose 'ems_communicator'.\n"
                    #   "Respond with a JSON object containing 'reasoning_steps' and 'function_name', for example:\n"
                    #   "{\n"
                    #   "    \"reasoning_steps\": [\"Identified keywords related to police response\", \"Determined appropriate function to dispatch\"],\n"
                    #   "    \"function_name\": \"police_communicator\"\n"
                    #   "}")
    
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
    print("\n[Police Communicator]")
    print("Officer: Please provide more details about the situation.")
    
    # Simulate user response
    user_response = get_user_response("Police: ")
    
    # Decide the number of officers based on user response
    num_officers = determine_resources("police", user_response)
    print(f"Dispatching {num_officers} police officer(s) to the location.")
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
    print("\n[Fire Communicator]")
    print("Firefighter: Can you describe the fire?")
    
    # Simulate user response
    user_response = get_user_response("Firefighter: ")
    
    # Decide the number of fire engines based on user response
    num_engines = determine_resources("fire", user_response)
    print(f"Dispatching {num_engines} fire engine(s) to the location.")
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
    print("\n[EMS Communicator]")
    print("Paramedic: Are there any injured individuals?")
    
    # Simulate user response
    user_response = get_user_response("Paramedic: ")
    
    # Decide the number of ambulances based on user response
    num_ambulances = determine_resources("ems", user_response)
    print(f"Dispatching {num_ambulances} ambulance(s) to the location.")
    return num_ambulances

def get_user_response(prompt: str) -> str:
    """
    Simulates getting a response from the user. In a real system, this would capture user input.
    For demonstration, we'll use predefined responses based on the description.
    """
    # For demonstration purposes, we can parse the description to simulate responses
    # In a real-world scenario, you'd use input() or another input method
    # Here, we'll just return a default response
    # This function can be enhanced to simulate different scenarios
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

# Create edges
coordinator.create_edge(receive_call, router)               # receive_call -> router
coordinator.create_edge(router, police_communicator)        # router -> police_communicator
coordinator.create_edge(router, fire_communicator)          # router -> fire_communicator
coordinator.create_edge(router, ems_communicator)           # router -> ems_communicator

# Example usage with explicit router node
def simulate_911_call(description: str):
    print("\n--- 911 Dispatcher System ---")
    print(f"Incoming Call Description: {description}")
    function_response: FunctionResponse = coordinator.run(description)
    print("FINAL OUTPUT:", function_response.final_output)

# Simulate different types of emergency calls
if __name__ == "__main__":
    # Example 1: Police Emergency
    police_call_description = "There's a robbery in progress at the downtown bank."
    simulate_911_call(police_call_description)
    print("----------------------------------\n\n")
    
    # Example 2: Fire Emergency
    fire_call_description = "There's a large fire spreading in the warehouse."
    simulate_911_call(fire_call_description)
    print("----------------------------------\n\n")
    
    # Example 3: EMS Emergency
    ems_call_description = "A person is having a heart attack in their home."
    simulate_911_call(ems_call_description)
    print("----------------------------------\n\n")