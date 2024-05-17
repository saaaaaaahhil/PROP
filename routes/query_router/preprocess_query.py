import os
from openai import AzureOpenAI, OpenAI
import json


client = AzureOpenAI(
    api_key=os.environ['AZURE_OPENAI_API_KEY'],  
    api_version=os.environ['AZURE_OPENAI_API_VERSION'],
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
)

system_prompt = "Analyze the given query and classify it into one of the following categories: \
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
  - 'other' if the query does not fall into either of the previous categories. \
  If the input from user contains more than one query(i.e. composite query), separate and process each query independently. For example: What is the price of unit 123 in the given project and what are the nearby hospitals from the project?\
  Respond with a list of JSON objects in the following format: { 'result': [{query:<atomic-query>,\n'category': 'vision' | 'csv' | 'return_image' | 'metadata' | 'other' },....]}. \
  The list will contain multiple json objects each one of them will have the atomic query and its category \
  Do not provide any explanation or additional information in your response."

def preprocess_query(query: str):
    """
    This function classifies the query into one of the relevant categories(also breaking the query into granular queries if needed).
    """
    try:
        response = client.chat.completions.create(
            model=os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'],
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            max_tokens=4096,
            response_format={"type": "json_object"}
        )

        print(response)
        content = response.choices[0].message.content
        json_object = json.loads(content)
        print(json_object)
        return json_object["result"]        

    except Exception as e:
        print(f"Error preprocessing query: {e}")
        raise
        return None