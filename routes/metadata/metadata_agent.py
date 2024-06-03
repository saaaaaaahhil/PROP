import os
import json
from config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from strictjson import *
from routes.llm_connections import groq_client, groq_llm
from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)


MODEL = 'llama3-70b-8192'
# MODEL='gpt-4o'

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_query_category(user_query: str):
    """
    This function takes a query and returns the category of query for eg. healthcare/landmark.
    """
    try:
        messages=[
            {
                "role": "system",
                    "content": """You are a Natural Language Processing API capable of Named Entity Recognition that responds in JSON. The JSON schema should include:
                    {
                        'category' : 'healthcare | entertainment | landmark | restaurant '
                    }
                    You need to identify the category of user query amongst the following categories : air_quality_index,education,healthcare,entertainment,landmark,restaurant,shopping. Do not provide any additional information or explanation in your response. Respond with proper json schema."""
            },
            {
                "role": "user",
                "content": user_query 
            }
        ]
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None
        )
        response_message = response.choices[0].message.content
        json_string = response_message
        json_object = json.loads(json_string)
        return json_object["category"]

    except Exception as e:
        print(f"Error predicting category: {e}")
        raise RetryableException(f"Error predicting category: {e}")

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_query_response(data: str, user_query: str):
    """
    This function takes a query and data to be inferred upon and returns the answer to user query.
    """
    encoded_query =  user_query + "\n" + str(data)
    try:
        system_prompt = """
        You are a Natural Language Processing API capable of answering user queries by analyzing the data provided to you. You should respond in JSON format with the following schema:
        {
            'answer': 'output in string format'
        }

        You need to identify what is required in the query and appropriately answer the query using the project data provided to you along with the query. The data provided to you belongs to a certain project, and from that, you can answer queries like what is the AQI around the property, how far is the project from certain landmarks, what are the nearest hospitals/schools, etc., from the property. If the answer is not found in the data, return 'No results found!' as the answer.

        Format the 'answer' field using Markdown. Use the following guidelines:
        - Use headings for important sections, indicated by `#` for the main heading.
        - Use subheadings, indicated by `##`, for secondary sections.
        - Use bullet points `-` for listing items.
        - Use bold text `**` for highlighting important information.
        - Use code blocks for any structured data or examples.

        Example response format:

        {
            "answer": "# Key Information\\n\\n- **AQI:** 42\\n- **Nearest Hospital:** XYZ Hospital\\n- **Distance to Landmark:** 2.5 km\\n\\nNo results found!"
        }

        Ensure the 'answer' field in the JSON response is properly formatted in Markdown and the JSON response is valid. Do not include any extra escape characters or newline characters inside the JSON object.
        """
        res = strict_json(system_prompt = system_prompt,
                    user_prompt = encoded_query,
                    output_format ={
                                    "answer": "## Key Information\n- **AQI:** 42\n- **Nearest Hospital:** XYZ Hospital\n- **Distance to Landmark:** 2.5 km\n\n`No results found!`"},
                    llm = groq_llm,
                    chat_args={'temperature': 1, 'max_tokens':1024, 'top_p': 1})
        
        return res['answer']

    except Exception as e:
        print(f"Error generating answer: {e}")
        raise RetryableException(f"Error generating answer: {e}")

