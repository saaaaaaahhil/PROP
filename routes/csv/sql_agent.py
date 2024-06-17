from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.llms.openai import OpenAI 
from langchain.agents import AgentExecutor 
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI, AzureChatOpenAI
# from langchain_groq import ChatGroq  # Commented out as it might use Portkey
# from langchain_anthropic import ChatAnthropic  # Commented out as it might use Portkey
from urllib.parse import quote_plus
import os
from threading import Lock
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config
from routes.exceptions import RetryableException
from routes.csv.connect_db import sanitize_project_id
# from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL  # Commented out as it's not to be used

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)

# Global cache for database connections and a lock for thread-safe operations
# TODO : Test the concurrency of agent_executor.  If it is not thread-safe, we need to create a new agent_executor for each thread.
agent_cache = {}
cache_locks = {}

global_lock = Lock()

def get_lock(db_name):
    global global_lock, cache_locks
    # Ensure thread safety while accessing the cache_locks dictionary
    with global_lock:
        if db_name not in cache_locks:
            cache_locks[db_name] = Lock()
        return cache_locks[db_name]

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_agent_executor(project_id: str):
    global global_lock, agent_cache
    sanitized_project_id = sanitize_project_id(project_id)

    try:
        llm_openai = ChatOpenAI(
            temperature=0.3, 
            model="gpt-4o",  # Changed model to "gpt-4" as "gpt-4o" may not be valid without Portkey
            api_key=os.environ['OPENAI_API_KEY']  # Directly using OpenAI API key
        )

        agent_lock = get_lock(sanitized_project_id)
        with agent_lock:
            if sanitized_project_id in agent_cache:
                agent_executor = agent_cache[sanitized_project_id]
            else:
                # Database connection parameters
                db_username = Config.POSTGRES_USER
                db_password = Config.POSTGRES_PASSWORD
                db_host = Config.POSTGRES_HOST
                db_port = Config.POSTGRES_PORT
                db_name = sanitized_project_id

                encoded_password = quote_plus(db_password)

                pg_uri = f'postgresql+psycopg2://{db_username}:{encoded_password}@{db_host}:{db_port}/{db_name}'

                db = SQLDatabase.from_uri(pg_uri)

                toolkit = SQLDatabaseToolkit(db=db, llm=llm_openai)

                agent_executor = create_sql_agent(
                    llm=llm_openai,
                    toolkit=toolkit,
                    verbose=True,
                    suffix=os.environ['SQL_AGENT_PROMPT_SUFFIX'],
                    agent_type="tool-calling",
                    # agent_type="zero-shot-react-description",
                    # agent_type="openai-functions",
                    agent_executor_kwargs={
                        "handle_parsing_errors": True
                    }
                )
                agent_cache[sanitized_project_id] = agent_executor
        return agent_executor
    except Exception as e:
        print(f"Error getting agent executor: {e}")
        raise RetryableException(f"Error getting agent executor: {e}")

def run_query(project_id: str, query: str, user_id: str = None):
    """
    This function takes a query and runs it on the specified database.
    """
    try:
        agent_executor = get_agent_executor(project_id)
        result = agent_executor.invoke(query)
        return {"success": True, "answer": result['output']}
    except Exception as e:
        print(f"Error running query: {e}")
        return {"success": False, "failure": f'Failure in csv agent: {e}'}
