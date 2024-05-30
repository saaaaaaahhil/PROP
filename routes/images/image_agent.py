from routes.images.blob_storage_operations import get_image_urls
from config import Config
import os
from routes.llm_connections import openai_client

def query_images(project_id: str, query: str):
    """
    This function takes a query and returns a list of image URLs from Azure Blob Storage.
    """
    try:
        response = get_image_urls(project_id)
        if not response["success"]:
            return {"success" : False, "message" : "Failed to get image URLs."}
        
        messages = []
        messages.append({
            "role": "system",
            "content": os.environ['IMAGE_SYSTEM_PROMPT'],
        })
        user_content = []
        user_content.append({
            "type": "text",
            "text": query,
        })
        for url in response["urls"]:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                },
            })
        messages.append({
            "role": "user",
            "content": user_content,
        })

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4000
        )
        return {"success" : True, "answer" : response.choices[0].message.content}
    except Exception as e:
        print(f"Error querying images: {e}")
        return {"success" : False, "failure" : f"Error in image agent: {e}"}