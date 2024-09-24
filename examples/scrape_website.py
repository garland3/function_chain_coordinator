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

@register_function(input_type=str, output_type=bool)
def send_email_to_engineering(content):
    """
    Sends an email to the Engineering Department with the scraped content.
    """
    # Dummy implementation: Print to console
    print("Sending email to Engineering Department with the following content:")
    print(content)
    # To implement actual email sending, uncomment and configure the following:
    """
    import smtplib
    from email.mime.text import MIMEText

    sender_email = "your_email@example.com"
    receiver_email = "engineering@example.com"
    subject = "Scraped Content: Machine Learning"
    body = content

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login(sender_email, 'your_password')
        server.send_message(msg)
    """
    print("Email sent to Engineering Department.")
    return True

@register_function(input_type=str, output_type=bool)
def send_email_to_accounting(content):
    """
    Sends an email to the Accounting Department with the scraped content.
    """
    # Dummy implementation: Print to console
    print("\n\n--------------------\nSending email to Accounting Department with the following content:")
    print(content)
    # To implement actual email sending, uncomment and configure the following:
    """
    import smtplib
    from email.mime.text import MIMEText

    sender_email = "your_email@example.com"
    receiver_email = "accounting@example.com"
    subject = "Scraped Content: Finance"
    body = content

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login(sender_email, 'your_password')
        server.send_message(msg)
    """
    print("Email sent to Accounting Department.")
    return True
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
