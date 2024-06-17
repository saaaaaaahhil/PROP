import os
import json
from routes.exceptions import RetryableException
from config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai


# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)

# Initialize the OpenAI client
openai.api_key = os.environ['OPENAI_API_KEY']

MODEL = 'gpt-4o'  # or 'llama3-70b-8192' if you have access

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_query_category(user_query: str, project_id: str, user_id: str):
    """
    This function takes a query and returns the category of the query, e.g., healthcare, landmark.
    """
    try:
        messages = [
            {
                "role": "system",
                "content": """You are a Natural Language Processing API capable of Named Entity Recognition that responds in JSON. The JSON schema should include:
                {
                    'category': 'healthcare | entertainment | landmark | restaurant'
                }
                You need to identify the category of the user query amongst the following categories: air_quality_index, education, healthcare, entertainment, landmark, restaurant, shopping. Do not provide any additional information or explanation in your response. Respond with a proper JSON schema."""
            },
            {
                "role": "user",
                "content": user_query 
            }
        ]
        client = openai(api_key=os.environ['OPENAI_API_KEY'])
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            top_p=1
        )
        response_message = response.choices[0].message.content
        json_object = json.loads(response_message)
        return json_object["category"]

    except Exception as e:
        print(f"Error predicting category: {e}")
        raise RetryableException(f"Error predicting category: {e}")

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_query_response(data: str, user_query: str, project_id: str, user_id: str):
    """
    This function takes a query and data to be inferred upon and returns the answer to the user query.
    """
    try:
        messages = []
        encoded_query = user_query + "\n" + str(data)
        system_prompt = """
        You are a Natural Language Processing API capable of answering user queries by analyzing the data provided to you.

        You need to identify what is required in the query and appropriately answer the query using the project data provided to you along with the query. The data provided to you belongs to a certain project, and from that, you can answer queries like what is the AQI around the property, how far is the project from certain landmarks, what are the nearest hospitals/schools, etc., from the property. If the answer is not found in the data, return 'No results found!' as the answer.

        While generating the response, use the following guidelines:
        - Use headings for important sections, indicated by `#` for the main heading.
        - Use subheadings, indicated by `##`, for secondary sections.
        - Use bullet points `-` for listing items.
        - Use bold text `**` for highlighting important information.
        - Use code blocks for any structured data or examples.

        Ensure the response is properly formatted in Markdown format.
        """
        
        messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': encoded_query})
         
        client = openai(api_key=os.environ['OPENAI_API_KEY'])

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            top_p=1
        )
        response_message = response.choices[0].message.content
        return response_message

    except Exception as e:
        print(f"Error generating answer: {e}")
        raise RetryableException(f"Error generating answer: {e}")
