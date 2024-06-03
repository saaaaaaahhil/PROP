from routes.images.blob_storage_operations import get_image_urls
import os
from routes.llm_connections import openai_client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config
from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
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