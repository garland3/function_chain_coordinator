# example_scrape_and_route.py

from function_chain_coordinator import CoordinatorInstance, register_function, FunctionResponse
import os
import requests
from bs4 import BeautifulSoup

# Initialize the Coordinator with your OpenAI API key and an optional system prompt
# You can set your OpenAI API key as an environment variable for security
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this environment variable is set
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# Optional: Define a custom system prompt for the Coordinator
# If not provided, a default prompt is used
custom_system_prompt = "You are ChatGPT, a helpful function chain coordinator."

CoordinatorInstance.initialize(openai_api_key=OPENAI_API_KEY, system_prompt=custom_system_prompt)
coordinator = CoordinatorInstance.get_instance()

@register_function(input_type=str, output_type=str)
def scrape_website(url):
    """
    Scrapes the content of the given website URL.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Failed to retrieve content from {url}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # For demonstration, extract all paragraph texts
    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
    content = ' '.join(paragraphs)
    return content
@register_function(input_type=str, output_type=str)
def send_email_to_engineering(content):
    """
    Sends an email to the Engineering Department with the scraped content and returns the email.
    """
    email = "Subject: Scraped Content: Machine Learning\n\nWe found some content about machine learning."
    return email

@register_function(input_type=str, output_type=str)
def send_email_to_accounting(content):
    """
    Sends an email to the Accounting Department with the scraped content and returns the email as a string.
    """
    email = "Subject: Scraped Content: Finance\n\nWe found some content about finance."
    return email

@register_function(
    input_type=str,
    output_type=str,
    is_router=True,
    direction_prompt="""You are picking the next function to run based on the content of the website.
- If the website content is about machine learning, choose 'send_email_to_engineering'.
- If the website content is about finance, choose 'send_email_to_accounting'.
Respond with the function name in JSON format, e.g., {"next_function": "send_email_to_engineering"}."""
)
def router(content):
    # This function's logic is handled by the RouterNode and LLM
    return content

# Create edges
coordinator.create_edge(scrape_website, router)             # scrape_website -> router
coordinator.create_edge(router, send_email_to_engineering)  # router -> send_email_to_engineering
coordinator.create_edge(router, send_email_to_accounting)   # router -> send_email_to_accounting

# Example usage with explicit router node
# input_url = "https://example-machine-learning-website.com"  # Replace with a real website URL about machine learning
input_url = "https://www.together.ai/"
function_response: FunctionResponse = coordinator.run(input_url)

print("FINAL OUTPUT:", function_response.final_output)
