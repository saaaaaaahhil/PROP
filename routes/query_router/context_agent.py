from routes.llm_connections import groq_llm
from strictjson import *
from routes.mongo_db_functions import get_chat_history

def get_context_aware_query(chat_id, project_id, user_query):
    """
    Retrieve last 3 chats from mongo db 
    Pass these messages to LLM so that it can change the query to be more context aware 
    """
    try:
        message_history = get_chat_history(chat_id)
        print(message_history)

        complete_user_prompt = f"""chat_history = {message_history}\nnew_query = {user_query}"""
        
        system_prompt = """You are an advanced language model designed to handle conversational context and refine user queries based on recent chat history. Your task is to analyze the recent messages of a conversation between user and agent along with a new user query. If the new query is context-dependent and lacks necessary context, you should modify the query to include the required context from the chat history. If the new query is already self-sufficient and understandable without additional context, do not modify the query.
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
            {'text': 'What is the price of unit 103?', 'role': 'user'},
            {'text': 'The price of unit 103 is $500,000.', 'role': 'bot'},
            {'text': 'Does unit 103 come with parking?', 'role': 'user'},
            {'text': 'Yes, unit 103 includes one parking space.', 'role': 'bot'},
            {'text': 'Are there any ongoing offers unit 103?', 'role': 'user'},
            {'text': 'Currently, there are no offers on unit 103.', 'role': 'bot'}
        ]
        new_query = "Is it sold?"

        Example Output:
        {
            'query': 'Is unit 103 unsold?'
        }

        Example Input:
        chat_history = [
            {'text': 'Is unit 1002 sold?', 'role': 'user'},
            {'text': 'No, unit 1002 is not sold.', 'role': 'bot'},
            {'text': 'What is price of unit 1002?', 'role': 'user'},
            {'text': 'The price of unit 1002 is 3,418,000.', 'role': 'bot'}
        ]
        new_query = "What are the number of bathrooms in 4 bed unit?"

        Example Output:
        {
            'query': 'What are the number of bathrooms in 4 bed unit?'
        }

        new_query = "What are the nearby schools and restaurants?"

        Example Output:
        {
            'query': 'What are the nearby schools and restaurants?'
        }
        
        Process the input chat history and the new user query to generate the modified query.
        """
        res = strict_json(system_prompt = system_prompt,
                    user_prompt = complete_user_prompt,
                    output_format ={
                                    'query': 'modified query'
                                },
                    llm = groq_llm,
                    chat_args= {'temperature': 0.5})
        
        print(res)
        return res['query']
    
    except Exception as e:
        print(f"Error generating modified query: {e}")




