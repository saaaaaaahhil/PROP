from routes.llm_connections import groq_llm, gpt_llm
from routes.images.blob_storage_operations import get_container_client, get_blob_url
from strictjson import *


def return_image_from_store(project_id: str, query: str):
    """
    This function returns the url of image requested in the query.
    """
    try:

        #Retrieve the names of the image stored in blob storage
        images_list = get_images_list(project_id)

        #Select the most appropriate image from the list based on user query.
        image_name = get_image_name(images_list, query)

        #Check if image name is valid
        if image_name  == 'no_match':
            return {'success': True, 'answer': "No matching image found in database."}
        
        #Get the image url from storage
        image_url = get_blob_url(image_name, project_id)

        return {'success': True, 'answer': f'IMAGE_URL: {image_url}'}

    except Exception as e:
        print(f"Error returning image: {e}")
        return {'success': False, 'failure': f"Error returning image: {e}"}


def get_images_list(project_id: str):
    """
    This function returns the list of image names stored in blob storage.
    """
    try:
        container_client = get_container_client(project_id)
        blob_list = container_client.list_blobs()
        image_names = []
        for blob in blob_list:
            image_names.append(blob.name)
        print(image_names)
        return image_names
    except Exception as e:
        print(f"Failed to retrieve the image list from storage: {e}")
        raise e
    
def get_image_name(images_list: list, user_query: str):
    """
    This function return the name of most appropriate image from the list provided.
    """
    try:
        system_prompt = f"""Given the user query, return the name of the image (as it is) in the list {str(images_list)} that best matches the query. If there is no match, return 'no_match'. 
        Respond with a JSON object in the following format:
        {{
            "name": "name of the image from the list" | "no_match"
        }}.
        Ensure the image name exactly matches one from the provided list. Do not provide any explanation or additional information in your response.
        """
        
        res = strict_json(system_prompt = system_prompt,
                    user_prompt = user_query,
                    output_format ={
                        'name': 'name of the image'
                    },
                    llm = gpt_llm,
                    chat_args={'temperature': 0, 'max_tokens':1024, 'top_p': 1})
        print(res)
        return res.get('name', 'no_match')
    
    except Exception as e:
        print(f'Unable to get image name: {e}')
        raise e