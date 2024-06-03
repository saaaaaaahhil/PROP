from groq import Groq
from openai import OpenAI, AzureOpenAI
import os
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_groq import ChatGroq
from routes.exceptions import RetryableException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)

try:
    groq_client = Groq(api_key=os.environ['GROQ_API_KEY'])
    openai_client = OpenAI()
    azure_openai_client = AzureOpenAI(
        api_key=os.environ['AZURE_OPENAI_API_KEY'],  
        api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT']
    )
    llm_openai = ChatOpenAI(temperature=0.7, model="gpt-4o")
    llm_azure_openai = AzureChatOpenAI(azure_deployment=os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'], openai_api_version=os.environ['AZURE_OPENAI_API_VERSION'])
    llm_groq = ChatGroq(model="llama3-70b-8192", temperature=0)

except Exception as e:
    print(f"Error connecting to client: {e}")

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def groq_llm(system_prompt: str, user_prompt: str, **kwargs):
    try:
        # ensure your LLM imports are all within this function
        from groq import Groq

        # define your own LLM here
        client = Groq(api_key=os.environ['GROQ_API_KEY'])
        MODEL = 'llama3-70b-8192'


        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            **kwargs
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response from groq: {e}")
        raise RetryableException(e)
    
@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def gpt_llm(system_prompt: str, user_prompt: str, **kwargs):
    try:
        # ensure your LLM imports are all within this function
        from openai import OpenAI

        # define your own LLM here
        client = OpenAI()
        MODEL = 'gpt-4o'


        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            **kwargs
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response from groq: {e}")
        raise RetryableException(e)