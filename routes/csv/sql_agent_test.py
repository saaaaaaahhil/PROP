from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.llms.openai import OpenAI 
from langchain.agents import AgentExecutor 
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from urllib.parse import quote_plus
import os

from config import Config

# have optional agent type with default zero-shot-react-description
def run_test_query(project_id: str, query: str, model: str = "claude-3-sonnet-20240229", agent_type: str = "zero-shot-react-description"):
    """
    This function takes a query and runs it on the specified database.
    """

    try:
        # Database connection parameters
        db_username = Config.POSTGRES_USER
        db_password = Config.POSTGRES_PASSWORD
        db_host = Config.POSTGRES_HOST
        db_port = Config.POSTGRES_PORT
        db_name = project_id

        encoded_password = quote_plus(db_password)

        pg_uri = f'postgresql+psycopg2://{db_username}:{encoded_password}@{db_host}:{db_port}/{db_name}'

        db = SQLDatabase.from_uri(pg_uri)

        if "claude" in model:
            llm = ChatAnthropic(temperature=0, model_name=model)
        elif "gpt" in model:
            llm = AzureChatOpenAI(
                azure_deployment=os.environ['AZURE_OPENAI_MODEL_NAME'],
                openai_api_version=os.environ['AZURE_OPENAI_API_VERSION']
            )
        elif "llama" in model:
            llm = ChatGroq(model=model, temperature=0)
        elif "mixtral" in model:
            llm = ChatGroq(model=model, temperature=0)
        else:
            raise ValueError(f"Model {model} not supported.")
        # llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0) # best, performs well with tool-calling
        # llm = ChatGroq(model="llama3-70b-8192", temperature=0) # correct results, performs best with zero-shot
        # # llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0) # very bad
        # llm = ChatAnthropic(temperature=0, model_name="claude-3-sonnet-20240229")

        toolkit = SQLDatabaseToolkit(db=db, llm=llm)

        agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=True,
            suffix="I should look at the tables in the database to see what I can query.  Then I should query the schema of the most relevant tables and join wherever needed. I should not limit the number of results. I should also not make any reference to input data schema in the response.",
            # agent_type="tool-calling",
            agent_type="zero-shot-react-description",
            agent_executor_kwargs={
                "handle_parsing_errors":True
            }
        )
        result = agent_executor.invoke(query)
        return result['output']
    except Exception as e:
        print(f"Error running query: {e}")
        raise
        return None