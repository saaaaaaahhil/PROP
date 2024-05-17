from groq import Groq
import os
import json


client = Groq(api_key=os.environ['GROQ_API_KEY'])
MODEL = 'llama3-70b-8192'


def get_query_category(user_query: str):
    """
    This function takes a query and returns the category of query for eg. healthcare/landmark.
    """
    try:
        messages=[
            {
                "role": "system",
                "content": "You are a Natural Language Processing API capable of Named Entity Recognition that responds in JSON.\nThe JSON schema should include:\n{\n \"category\" : \"hospital/entertainment\",\n}\n\nYou need to identify the category of user query amongst the following categories :\nair_quality_index,education,healthcare,entertainment,landmark,restaurant,shopping.\n"
            },
            {
                "role": "user",
                "content": user_query 
            }
        ]
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=1,
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
        raise


def get_query_response(data: str, user_query: str):
    """
    This function takes a query and data to be inferred upon and returns the answer to user query.
    """
    encoded_query =  user_query + "\n" + str(data)
    try:
        messages=[
            {
                "role": "system",
                "content": "You are a Natural Language Processing API capable of answering user queries by analyzing the data provided to you that responds in JSON. The JSON schema should include:{ \"answer\" : <Interpreted-Answer>}\nYou need to identify the what is required in the query and appropriately answer the query from the project data provided to you along with query. The data provided to you belongs to a certain project and from that you can answer queries like what is the aqi around property, how far is the project from certain landmark, what are the nearest hospitals/schools,etc from the property. If answer is not found in data return 'No results found !' as answer."
            },
            {
                "role": "user",
                "content": encoded_query
            }
        ]
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None
        )
        response_message = response.choices[0].message.content
        json_string = response_message
        json_object = json.loads(json_string)
        return json_object["answer"]
    
    except Exception as e:
        print(f"Error generating answer: {e}")
        raise
