import openai
from routes.exceptions import RetryableException
import os
import json
from routes.mongo_db_functions import get_chat_history

# Set the OpenAI API type and API key
openai.api_type = "openai"
openai.api_key = os.getenv("OPENAI_API_KEY")

def preprocess_query(query: str, user_id=None, project_id=None, chat_id=None):
    """
    This function breaks the user query into granular queries if required and classifies each of the query into categories provided.
    """
    try:
        # Retrieve chat history if chat_id is provided
        context = []
        if chat_id is not None:
            context = get_chat_history(chat_id)
        
        message_history = json.dumps(context)
        
        system_prompt = """
        Analyze the given query and break it down into granular, self-sufficient queries only when necessary for understanding or completeness. Each query should be independently understandable and include enough context. Combine closely related parts of the query if it makes sense for clarity and context. Only break down queries if it makes sense to do so. Ensure the breakdown maintains the context and clarity of the original query.

        Once the queries are broken down, classify each query into one of the following categories:

        - 'metadata' for queries about location, connectivity, and nearby social infrastructure.
        Some example queries:
        1. What are the nearby schools, hospitals, and shopping malls?
        2. How far is the project from the nearest metro station?
        3. What is the air quality index around property?
        
        - 'vision' for queries about floor plan, master plan or unit plan.
        Some example queries:
        1. How many rooms in 4 bed unit?
        2. Does the 2 bed unit have balcony?
        3. Mapping unit type to blocks or towers within a project - eg, which blocks/tower have 2 bed + study unit?
        4. Area of a specific unit type - eg, what is the area of 2 Bed unit?
        
        - 'csv' if the query is associated with a specific unit number.
        Some example queries:
        1. What is the price of unit 123?
        2. What is the view of unit 123? Is it unsold?
        3. What are the parking options for unit 123?

        - 'docs' if the query is related to offers/discounts for customers or brokers/agents.
        Some example queries:
        1. Any ongoing offers for 3 beds?
        2. What is the brokerage offer/commission slab for this project/quarter?
        3. Any special commission/brokerage offers/kickers?
        
        - 'csv' if the query is associated with price of units, down payment, emi.
        Some example queries:
        1. What units might fit into monthly mortgage of $2000?
        2. Which units can be purchased with down payment of $200000?
        3. What are the options for 2-bedder units with monthly emi $3000 and a downpayment of $500000?
        
        - 'return_image' if the query is related to returning an image or a floor plan or a master plan.
        Some example queries:
        1. Show me the plan of the 2 bed unit?
        2. Give me the master plan
        
        - 'general' if the query is related to rules and regulations, taxes, standard operating procedures, warranty, or defect liability period.
        Some example queries:
        1. What is the capital gains tax treatment for non-resident purchasers from Dubai? How are my rentals taxed?
        2. Broker A shared the lead of international customer Peter on 3rd Dec. Later broker B shared the same lead but with the customer in email loop on 10th Dec. Whom should the lead credit go to? (SOP's regarding sales)
        3. What is the defect liability period?
        
        - 'docs' if the query is related to amenities, facilities, construction details, materials used, design specifics, or any other detailed documentation about the project.
        Some example queries:
        1. What are the amenities/facilities available in the project?
        2. What is the material used in the kitchen?
        3. What's the ceiling height in the bathrooms?
        4. Are there any energy-efficient features in the building design?
        
        - 'docs' if the query is related to appliances within a unit.
        Some example queries:
        1. Does the 3 bed unit have a washer?
        
        - 'vision' if the query is concerned with the relative location of units or blocks within the project or requires the site plan to answer.
        Some example queries:
        1. Which block is closest to the entrance drop-off in the project?
        2. Which units have the best view of the central garden?
        3. Is unit 23 in tembusu grand a corner unit?
        
        - 'other' if the query does not fall into either of the previous categories.

        Example:

        Composite Query: "What are the nearby schools, and is there a swimming pool in the project?"
        Output:
        {
            "result": [
                {
                    "query": "What are the nearby schools?",
                    "category": "metadata"
                },
                {
                    "query": "Is there a swimming pool in the project?",
                    "category": "docs"
                }
            ]
        }

        Composite Query: "How many units have price less than 2M, are unsold and have a pool view and which are the nearby schools to the property?"
        Output:
        {
            "result": [
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

        Composite Query: "Which blocks are 1 Bed + study units located in tembusu grand?"
        Output: 
        {
            "result": [
                {
                   "query" : "Which blocks have 1 Bed + study units in Tembusu Grand?",
                   "category": "vision"
                }
            ]
        }
        Thought process: This query is straightforward and specific, needing no further breakdown for clarity.

        Composite Query: "An international channel partner/broker has registered a customer lead by marking a mail to sales team member. Hope lead registration is valid for Sky eden."
        Output: 
        {
            "result": [
                {
                    "query": "Is the lead registration valid if an international channel partner/broker has registered a customer lead by marking a mail to a sales team member for Sky Eden?",
                    "category": "general"
                }
            ]
        }
        Thought process: This query can be combined into a single coherent question for clarity.

        Provide response in json format as mentioned in above examples.
        Note: Maintain the context and combine related parts if it improves clarity.
        """

        # Initialize OpenAI client
        client = openai

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
            top_p=1
        )

        # Accessing response content using dot notation
        json_string = response.choices[0].message.content
        queries = json.loads(json_string)
        print(queries)
        return queries.get('result', [])

    except Exception as e:
        print(f'Error preprocessing query: {e}')
        raise RetryableException(e)

