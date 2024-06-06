from routes.llm_connections import groq_llm, portkey_openai
from strictjson import *
from routes.mongo_db_functions import get_chat_history
import os
import json

def get_context_aware_query(chat_id, project_id, user_query, user_id = None):
    """
    Retrieve last 3 chats from mongo db 
    Pass these messages to LLM so that it can change the query to be more context aware 
    """
    try:
        print(chat_id)
        message_history = get_chat_history(chat_id)
        print(message_history)

        complete_user_prompt = f"""chat_history = {message_history}\nnew_query = {user_query}"""
        
        system_prompt = """You are an advanced language model designed to handle conversational context and refine user queries based on recent chat history. Your task is to analyze the recent messages of a conversation between user and agent along with a new user query. Give more importance to the latest message in the chat history when determining if additional context is required for the new query. Only if the new query is context-dependent and lacks necessary context, you should modify the query to include the required context from the chat history. Most importantly, if the new query is already self-sufficient and understandable without additional context, do not modify the query.
        The messages will be provided as a list of dictionaries in the following format:
        [
            { 
                'text': 'user input or bot response',
                'role': 'user' or 'bot'
            }
        ]

        For example, if the previous query is: "What is the price of unit 103?" and the new query is: "Is it sold?", then by analyzing the previous message, you should modify the query to: "Is unit 103 unsold?" (adding the context from the previous messages).

        Your output should be in the following JSON format:
        {
            'query': modified-query
        }

        Ensure that the modified query is self-sufficient, understandable, and contains enough context from the recent chat history to make sense on its own. **Only modify the query if some context is missing in the query; otherwise, don't modify the query.**

        Example Input:
        chat_history = [
            {'text': 'How many units in Tembusu Grand are sold?', 'role': 'user'},
            {'text': 'Out of 100 units, 70 are sold.', 'role': 'bot'},
            {'text': 'Are there any ongoing offers unit 103?', 'role': 'user'},
            {'text': 'Currently, there are no offers on unit 103.', 'role': 'bot'}
        ]
        new_query = "Is it sold?"

        Output:
        {
            'query': 'Is unit 103 unsold?'
        }
        Thought Process: The new query "Is it sold?" lacks context on which unit it refers to. Given the latest message in the chat history discussing unit 103, it is likely that the user is asking if unit 103 is sold. Therefore, the query should be modified to include this context.

        Example Input:
        chat_history = [
            {'text': 'What is price of unit 1002?', 'role': 'user'},
            {'text': 'The price of unit 1002 is 3,418,000.', 'role': 'bot'}
        ]
        new_query = "What are the number of bathrooms in 4 bed unit?"

        Output:
        {
            'query': 'What are the number of bathrooms in 4 bed unit?'
        }
        Thought Process: The new query is self-sufficient and does not require any additional context from the chat history. Therefore, the query remains unchanged.

        Example Input:
        chat_history = [
            {'text': 'Does the 3 bed in tembusu grand come with separate washer & dryer?', 'role' : 'user'}
            {'text': 'Yes, according to the specifications provided, the 3-bedroom units at Tembusu Grand come with a separate Smeg washer and dryer.', 'role': 'bot'}
        ]
        new_query = "what are the wall and floor finishes in the yard area in tembusu grand?"
        Example Output:
        {
            'query': 'what are the wall and floor finishes in the yard area in tembusu grand?'
        }
        Thought Process: The new query is self-sufficient and does not require any additional context from the chat history. Therefore, the query remains unchanged.

        """
        # res = strict_json(system_prompt = system_prompt,
        #             user_prompt = complete_user_prompt,
        #             output_format ={
        #                             'query': 'modified query'
        #                         },
        #             llm = groq_llm,
        #             chat_args= {'temperature': 0.5})

        # print(res)
        # return res['query']

        response = portkey_openai.with_options(
            metadata = {
            "_user": user_id,
            "environment": os.environ['ENVIRONMENT'],
            "project_id": project_id
        }).chat.completions.create(
        messages = [{"role": "system", "content": system_prompt},{ "role": 'user', "content": complete_user_prompt}],
        model = 'gpt-4o',
        response_format={"type": "json_object"},
        temperature=0.3)
        
        json_string = response.choices[0].message.content
        query = json.loads(json_string)
        print(query)
        return query.get('query', [])
    
    except Exception as e:
        print(f"Error generating modified query: {e}")




