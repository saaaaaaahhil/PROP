from routes.llm_connections import openai_client
import json
from openai import AzureOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from routes.query_router.preprocess_query import preprocess_query

from config import Config
from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)

# MODEL = os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME']
MODEL = "gpt-4o"

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def generate_queries_from_pitch(user_query: str):
    """
    This function takes a pitch query and returns the list of generated queries.
    """
    try:
        messages=[
            {
                "role": "system",
                "content":"""You are a Natural Language Understanding API that functions as a professional real estate agent. Your task is to generate granular queries from user input and classify each query into one of the specified categories. Finally, you should return the classified queries in a JSON format.

                Step-by-Step Instructions:

                1. Analyze the user input to generate granular queries that address specific aspects of the user's requirements. Ensure that each distinct requirement is broken down into a separate query.
                For example:
                Input: "Customer- David, Family of 6,2 kids, 1 school-going and 1 in college, elderly parents. Want kids to spend time outdoors. Wife does WFH mostly, husband works at Changi business park. Will take a mortgage."

                Granular queries: 
                'Which units are suitable and can accommodate a family of 6 people comfortably?', 'What are the nearest schools from the location?', 'What are the nearby colleges from the location?', 'What are the amenities available for elderly parents?', 'What are the outdoor activities available for children?', 'Are there any amenities available for people working from home since the wife works from home mostly?', 'Are there any amenities or spaces suitable for practicing yoga?', 'How far is Changi Business Park from the location?', 'What are the public transport options from the location?', 'What mortgage options are available for purchase since the customer is willing to take a mortgage?'

                2. Classify each granular query into one of the following categories:
                - 'metadata' if the query is related to location, connectivity (roads, metro/MRT) & social infrastructure near the project. \
                    Some example queries: \
                    1. What are the nearby schools, hospitals, and shopping malls? \
                    2. How far is the project from the nearest metro station? \
                    3. What are the nearby landmarks? \
                    4. What is the air quality index around property? \
                - 'vision' if answering the query would require access to a floor plan or master plan or unit plan. \
                    Some example queries: \
                    1. Number of rooms \
                    2. Size of rooms \
                    3. Presence of specific rooms or spaces in a unit type - eg, does the 2 bed unit have balcony/study room/helper room/servant quarters/house shelter? \
                    4. Mapping unit type to blocks or towers within a project - eg, which blocks/tower have 2 bed + study unit? \
                    5. Area of a specific unit type - eg, what is the area of 2 Bed unit? \
                - 'csv' if the query is associated with a specific unit number.  \
                    Some example queries: \
                    1. What is the price of unit 123? \
                    2. What is the view of unit 123? Is it unsold? \
                - 'csv' if the query is related to offers/discounts for customers or brokers/agents. \
                    Some example queries: \
                    1. Any ongoing offers for 3 beds? \
                    2. What is the brokerage offer/commission slab for this project/quarter? \
                    3. Any special commission/brokerage offers/kickers? \
                -  'csv' if query is associated with price of units, down payment, emi. \
                    Some example queries\
                    1. What units might fit into monthly mortgage of $2000?\
                    2. Which units can be purchased with down payment of $200000?\
                    3. What are the options for 2-bedder units with monthly emi $3000 and a downpayment of $500000?\
                - 'return_image' if the query is related to returning an image or a floor plan or a master plan. \
                    Some example queries: \
                    1. Can you show me the floor plan of the 2 bed unit? \
                    2. Can you show me the master plan? \
                    3. Can you show me the site map? \
                - 'general' if query is related to rules and regulations, taxes and other standard operating procedures  \
                    Some example queries: \
                    1. What is the capital gains tax treatment for non-resident purchasers from Dubai? How are my rentals taxed?\
                    2. Broker A shared the lead of international customer Peter on 3rd Dec. Later broker B shared the same lead but with the customer in email loop on 10th Dec. Whom should the lead credit go to? (SOP's regarding sales)\
                - 'docs' if the query is related to amenities, facilities, construction details, materials used, design specifics, or any other detailed documentation about the project. \
                    Some example queries: \
                    1. What are the amenities/facilities available in the project? \
                    2. What is the material used in the kitchen? \
                    3. What’s the ceiling height in the bathrooms? \
                    4. Are there any energy-efficient features in the building design? \
                - 'other' if the query does not fall into either of the previous categories. \

                For example, based on the generated queries, you should return the following JSON:
                {
                'result': [
                    {'query': 'Which units are suitable and can accommodate a family of 6 people comfortably and why?', 'category': 'vision'},
                    {'query': 'What are the nearest schools from the location?', 'category': 'metadata'},
                    {'query': 'What are the nearby colleges from the location?', 'category': 'metadata'},
                    {'query': 'What are the amenities available for elderly people?', 'category': 'docs'},
                    {'query': 'What are the outdoor activities available for children?', 'category': 'docs'},
                    {'query': 'Are there any amenities available for people working from home?', 'category': 'docs'},
                    {'query': 'Are there any amenities or spaces suitable for practicing yoga?', 'category': 'docs'},
                    {'query': 'How far is the Changi Business Park from the location?', 'category': 'metadata'},
                    {'query': 'What are the public transport options from the location?', 'category': 'metadata'},
                    {'query': 'What are the mortgage options available for purchase?', 'category': 'docs'}
                ]
                }

                Return the classified queries in JSON format. Do not provide any additional information or explanation in your response."""
            },
            {
                "role": "user",
                "content": user_query 
            }
        ]
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=4096,   
            response_format={"type": "json_object"},
        )
        response_message = response['choices'][0]['message']['content']
        json_string = response_message
        json_object = json.loads(json_string)
        return json_object["result"]

    except Exception as e:
        print(f"Error generating queries: {e}")
        raise RetryableException(f"Error generating queries: {e}")


def get_query_category(queries: list):
    """
    This function takes a query and data to be inferred upon and returns the answer to user query.
    """
    classified_queries = []
    try:
        for query in queries:
            result = preprocess_query(query)
            for res in result:
                classified_queries.append(res)
        return classified_queries
    except Exception as e:
        print(f"Error classifying queries: {e}")
        raise e

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def summarize_to_generate_pitch(query: str, data: str):
    """
    This function takes the user query and data extracted from database and generates a pitch
    """
    try:
        encoded_query = query + '\n' + data
        print(encoded_query)

        messages=[
            {
                "role": "system",
                "content": "You are a Natural Language Understanding API and consider yourself as a real estate agent. You will be given a user input and data from database and you need to write a good professional sales pitch. The pitch should include the appropriate greetings and opening statement at the beginning. By analyzing the input(user query and data) you need consider customer requirements and generate a adept pitch for the customer. The pitch should cover all the aspects and should include a closing note as well. The response should be in json format as follows: {'pitch' : generated pitch in string format}."
            },
            {
                "role": "user",
                "content": encoded_query 
            }
        ]
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=4096,
            temperature=1,   
        )
        response_message = response.choices[0].message.content
        json_string = response_message
        json_object = json.loads(json_string)
        print(json_string)
        return json_object

    except Exception as e:
        print(f"Error generating pitch: {e}")
        raise RetryableException(f"Error generating pitch: {e}")
