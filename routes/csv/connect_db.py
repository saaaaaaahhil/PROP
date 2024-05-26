from sqlalchemy import create_engine, text
import re
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus
from threading import Lock
from config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=Config.RETRY_MULTIPLIER, min=Config.RETRY_MIN, max=Config.RETRY_MAX)
RETRY_ATTEMPTS = Config.RETRY_ATTEMPTS

# Global dictionary to store database engines
engines = {}
locks = {}

global_lock = Lock()

def get_lock(project_id):
    global global_lock, locks

    # Ensure thread safety while accessing locks dictionary
    with global_lock:
        if project_id not in locks:
            locks[project_id] = Lock()
        return locks[project_id]

def sanitize_project_id(project_id):
    # Ensure the project_id starts with a letter and replace invalid characters with an underscore
    if not project_id[0].isalpha():
        project_id = 'p_' + project_id
    sanitized_id = re.sub(r'[^a-zA-Z0-9_]', '_', project_id)
    return sanitized_id

def get_engine(db_name):
    global engines

    with get_lock(db_name):
        # Check if engine already exists
        if db_name in engines:
            return engines[db_name]

        db_username = Config.POSTGRES_USER
        db_password = Config.POSTGRES_PASSWORD
        db_host = Config.POSTGRES_HOST
        db_port = Config.POSTGRES_PORT

        # Encode password for inclusion in URI
        encoded_password = quote_plus(db_password)

        # PostgreSQL connection string
        connection_str = f'postgresql://{db_username}:{encoded_password}@{db_host}:{db_port}/{db_name}'
        engine = create_engine(connection_str, pool_pre_ping=True)
        engines[db_name] = engine
        return engine

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_or_create_database(project_id):
    sanitized_project_id = sanitize_project_id(project_id)
    try:
        with get_lock(sanitized_project_id):
            if sanitized_project_id in engines:
                print(f"Engine for {sanitized_project_id} already exists.")
                return engines[sanitized_project_id]

            default_db = Config.POSTGRES_DEFAULT_DB  # Typically 'postgres'
            engine = get_engine(default_db)

            # Connection in autocommit mode for operations that can't run in a transaction
            connection = engine.connect()
            connection.execution_options(isolation_level="AUTOCOMMIT")

            try:
                # Check if database already exists
                result = connection.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{sanitized_project_id}'"))
                exists = result.fetchone()
                if not exists:
                    # Create new database if it doesn't exist
                    connection.execute(text(f"CREATE DATABASE {sanitized_project_id}"))
                    print(f"Database {sanitized_project_id} created.")
                else:
                    print(f"Database {sanitized_project_id} already exists.")
            except SQLAlchemyError as e:
                print(f"Error creating database: {str(e)}")
                raise
            finally:
                connection.close()
                engine.dispose()

        # Return the engine connected to the newly created or existing database
        return get_engine(sanitized_project_id)
    except Exception as e:
        print(f"Error creating database: {e}")
        raise RetryableException(f"Error creating database: {e}")
        return None
