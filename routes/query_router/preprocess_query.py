import os
from openai import AzureOpenAI, OpenAI
from groq import Groq
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config

from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=Config.RETRY_MULTIPLIER, min=Config.RETRY_MIN, max=Config.RETRY_MAX)
RETRY_ATTEMPTS = Config.RETRY_ATTEMPTS

# client = AzureOpenAI(
#     api_key=os.environ['AZURE_OPENAI_API_KEY'],  
#     api_version=os.environ['AZURE_OPENAI_API_VERSION'],
#     azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
# )
# client = OpenAI()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

system_prompt_multiquery = """Analyze the given query and classify it into one of the following categories: \
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
  If the input from user contains more than one query(i.e. composite query), that should be separated into individual queries for classification, separate and process each query independently. \
  For example: How many units have price less than 2M, are unsold and have a pool view and which are the nearby schools to the property? \
  Respond with a list of JSON objects in the following format \
  Output: 
  {
    'result': [
      {
        "query": "How many units have price less than 2M, are unsold and have a pool view?",
        "category": "csv"
      },
      {
        "query": "Which are the nearby schools to the property?",
        "category": "metadata"
      }
    ]
  } 
  Do not provide any explanation or additional information in your response."""


system_prompt_singlequery = """Analyze the given query and classify it into one of the following categories: \
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
  
  Respond with a JSON object in the following format: 
    {
    "result": [
      {
        "query": "<query>",
        "category": "vision"
      },
      {
        "query": "<query>",
        "category": "csv"
      },
      {
        "query": "<query>",
        "category": "return_image"
      },
      {
        "query": "<query>",
        "category": "metadata"
      },
      {
        "query": "<query>",
        "category": "general"
      },
      {
        "query": "<query>",
        "category": "other"
      }
    ]
  }. \
  
  Do not provide any explanation or additional information in your response."""

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def preprocess_query(query: str):
    """
    This function classifies the query into one of the relevant categories(also breaking the query into granular queries if needed).
    """
    try:
        response = client.chat.completions.create(
            # model=os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'],
            # model="gpt-4o",
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt_multiquery
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            max_tokens=4096,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        # print(content)
        json_object = json.loads(content)
        print(json_object)
        # return content
        return json_object['result']        

    except Exception as e:
        print(f"Error preprocessing query: {e}")
        raise RetryableException(f"Error preprocessing query: {e}")
        return None
    

def aggregate_queries(queries: list):
    """
    This function aggregates all the vision and doc queries.
    """
    aggregated_queries = []
    doc_queries = []
    vision_queries = []

    #Create separate list for each category
    for query in queries:
        if query['category'] == 'docs':
            doc_queries.append(query['query'])
        elif query['category'] == 'vision':
            vision_queries.append(query['query'])
        else:
            aggregated_queries.append(query)

    #Concatenate all doc queries
    if len(doc_queries) != 0:
        combined_doc_query = ""
        for query in doc_queries:
            combined_doc_query += query + ". "
        aggregated_queries.append({'query': combined_doc_query, 'category': 'docs'})

    #Concatenate all vision queries
    if len(vision_queries) != 0:
        combined_vision_query = ""
        for query in vision_queries:
            combined_vision_query += query + ". "
        aggregated_queries.append({'query': combined_vision_query, 'category': 'vision'})
    print(aggregated_queries)
    return aggregated_queries
       
      
         

    
            