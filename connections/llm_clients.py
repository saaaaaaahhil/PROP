from groq import Groq
import os
from openai import AzureOpenAI


groq_client = Groq(api_key=os.environ['GROQ_API_KEY'])
MODEL = 'llama3-70b-8192'

