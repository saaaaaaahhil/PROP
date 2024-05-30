from groq import Groq
from openai import OpenAI, AzureOpenAI
import os
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_groq import ChatGroq

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