import os
from openai import AzureOpenAI, OpenAI
from groq import Groq
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config
from routes.llm_connections import groq_llm, openai_client
from routes.exceptions import RetryableException
from strictjson import *

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)


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
  - 'csv' if the query is associated with a specific unit number details.  \
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
  If the input from user contains more than one query(i.e. composite query), that should be separated into individual queries, that are self-sufficient and include enough context to be understood independently, for classification. \
  Respond with a list of JSON objects in the following format \
  Example 1: How many units have price less than 2M, are unsold and have a pool view and which are the nearby schools to the property?  \
  Output 1: 
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
  Example 2: What is the price of unit 123? Is it unsold? \
  Output 2:
  {
    'result': [
      {
        "query": "What is the price of unit 123?",
        "category": "csv"
      },
      {
        "query": "Is unit 123 unsold?",
        "category": "csv"
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
  - 'vision' if answering the query would require access to a floor plan or master plan or unit plan.
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
    1. What is the plan for 2 bed units?
    1. Show me the plan of the 2 bed unit? \
    2. Give me the master plan \
    3. Can you show me the site map? \
    - 'general' if the query is related to rules and regulations, taxes, standard operating     procedures, warranty, or defect liability period.
    Some example queries:
    1. What is the capital gains tax treatment for non-resident purchasers from Dubai? How are my rentals taxed?
    2. Broker A shared the lead of international customer Peter on 3rd Dec. Later broker B shared the same lead but with the customer in email loop on 10th Dec. Whom should the lead credit go to? (SOP's regarding sales)
    3. What is the defect liability period?
  - 'docs' if the query is related to amenities, facilities, construction details, materials used, design specifics, or any other detailed documentation about the project. \
    Some example queries: \
    1. What are the amenities/facilities available in the project? \
    2. What is the material used in the kitchen? \
    3. What's the ceiling height in the bathrooms? \
    4. Are there any energy-efficient features in the building design? \
  - 'general_csv' if the query is regarding extracting detailed real estate market information and performing financial analysis to support investment decisions, market analysis, and property management.
    Some example queries are:
     1. What is the average price PSF (per square foot) of 2 beds in Grand duman project?
     2. What is the approx. rental values for 3 beds at cashew heights condo located near myst project?
     3. How many 1 beds have been sold at Continuum and what's the average transaction value?
  - 'siteplan' if the query is concerned with the relative location of units or blocks within the project or requires the site plan to answer.
    Some example queries:
    1. Which block is closest to the entrance drop-off in the project?
    2. Which units have the best view of the central garden?
    3. Is unit 23 in tembusu grand a corner unit?
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
        "category": "general_csv"
      },
      {
        "query": "<query>",
        "category": "siteplan"
      },
      {
        "query": "<query>",
        "category": "other"
      }
    ]
  }. \
  
  Do not provide any explanation or additional information in your response."""

system_prompt_breakdown = """
Analyze the given query and break it down into granular, self-sufficient queries only when necessary for understanding or completeness. Each query should be independently understandable and include enough context. Combine closely related parts of the query if it makes sense for clarity and context. Only break down queries if it makes sense to do so. 

For example:
Composite Query: "What is the price of unit 208? Is it unsold?"
Output: {"result": ["What is the price of unit 208?", "Is unit 208 unsold?"]}
Thought process: This query naturally splits into two distinct questions that provide complete and clear information independently.

Composite Query: "How many units have price less than 2M, are unsold and have a pool view and which are the nearby schools to the property?"
Output: {"result": ["How many units have price less than 2M, are unsold and have a pool view?", "Which are the nearby schools to the property?"]}
Thought process: The query contains two separate aspects: one about the units and another about nearby schools. Splitting them ensures clarity.

Composite Query: "What is the approx. rental values for 3 beds at cashew heights condo located near myst project?"
Output: {"result": ["What is the approx. rental values for 3 beds at cashew heights condo located near myst project?"]}
Thought process: This query is already clear, self-sufficient and complete, providing specific information about rental values at a particular location.

Composite Query: "Which blocks are 1 Bed + study units located in tembusu grand?"
Output: {"result": ["Which blocks have 1 Bed + study units in Tembusu Grand?"]}
Thought process: This query is straightforward and specific, needing no further breakdown for clarity.

Respond with a list of JSON objects in the following format:
{
  "result": [<granular_query1>, <granular_query2>, ...]
}
"""

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def classify_queries(queries: list):
    try:
        # response = client.chat.completions.create(
        #     # model="gpt-3.5-turbo",
        #     model="llama3-70b-8192",

        #     messages=[
        #         {"role": "system", "content": system_prompt_singlequery},
        #         {"role": "user", "content": str(queries)}
        #     ],
        #     max_tokens=4096,
        #     temperature=0.5,
        #     response_format={"type": "json_object"}
        # )

        # content = response.choices[0].message.content
        # json_object = json.loads(content)
        # print(json_object)
        # return json_object['result']
        print(queries)
        res = strict_json(system_prompt = system_prompt_singlequery,
                    user_prompt = str(queries),
                    output_format ={
                                    "result": "List of query objects"
                                  },
                    llm = groq_llm,
                    chat_args = { "max_tokens": 4096, 'temperature': 0.5})
        print(res)
        
        return res['result']
    except Exception as e:
        print(f"Error classifying queries: {e}")
        raise RetryableException(f"Error classifying queries: {e}")


@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def preprocess_composite_query(query: str):
    try:
        # response = openai_client.chat.completions.create(
        #     model="gpt-3.5-turbo",
        #     # model="llama3-70b-8192",
        #     messages=[
        #         {"role": "system", "content": system_prompt_breakdown},
        #         {"role": "user", "content": query}
        #     ],
        #     max_tokens=4096,
        #     temperature=0,
        #     response_format={"type": "json_object"}
        # )

        # content = response.choices[0].message.content
        # json_object = json.loads(content)
        # print(json_object)
        # return json_object['result']
        res = strict_json(system_prompt = system_prompt_breakdown,
                    user_prompt = query,
                    output_format = {
                                      'result': 'List of queries'
                                    },
                    llm = groq_llm,
                    chat_args = { "max_tokens": 4096, 'temperature': 0})
        print(res)
        return res['result']

    except Exception as e:
        print(f"Error breaking down query: {e}")
        raise RetryableException(f"Error preprocessing query: {e}")

def preprocess_query(query: str):
    """
    This function classifies the query into one of the relevant categories(also breaking the query into granular queries if needed).
    """
    try:
        queries = preprocess_composite_query(query)
        if queries:
            classified_queries = classify_queries(queries)
            return classified_queries
        else:
            return []       

    except Exception as e:
        print(f"Error preprocessing query: {e}")
        raise RetryableException(f"Error preprocessing query: {e}")
        return None
    

def aggregate_queries(queries: list):
    """
    This function aggregates all the vision and doc queries.
    """
    aggregated_queries = []
    # doc_queries = []
    vision_queries = []

    #Create separate list for each category
    for query in queries:
        if query['category'] == 'docs':
            # doc_queries.append(query['query'])
            aggregated_queries.append(query)
        elif query['category'] == 'vision':
            vision_queries.append(query['query'])
        else:
            aggregated_queries.append(query)

    # #Concatenate all doc queries
    # if len(doc_queries) != 0:
    #     combined_doc_query = ""
    #     for query in doc_queries:
    #         combined_doc_query += query + ". "
    #     aggregated_queries.append({'query': combined_doc_query, 'category': 'docs'})

    #Concatenate all vision queries
    if len(vision_queries) != 0:
        combined_vision_query = ""
        for query in vision_queries:
            combined_vision_query += query + ". "
        aggregated_queries.append({'query': combined_vision_query, 'category': 'vision'})
    print(aggregated_queries)
    return aggregated_queries
        