from routes.images.blob_storage_operations import get_image_urls
from config import Config
import os
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.environ['AZURE_OPENAI_API_KEY'],  
    api_version=os.environ['AZURE_OPENAI_API_VERSION'],
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
)

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

        response = client.chat.completions.create(
            model=os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'],
            messages=messages,
            max_tokens=4000
        )
        return {"success" : True, "answer" : response.choices[0].message.content}
    except Exception as e:
        print(f"Error querying images: {e}")
        raise
        return {"success" : False, "message" : f"Error querying images: {e}"}