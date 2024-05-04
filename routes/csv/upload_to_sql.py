from routes.csv.connect_db import get_or_create_database
import pandas as pd

def upload_to_sql(project_id: str, df: pd.DataFrame, filename: str):
    """
    This function takes a DataFrame and uploads it to a SQL database.
    """
    try:
        print(f"Uploading DataFrame to SQL database {project_id}...")
        # Get the database engine
        engine = get_or_create_database(project_id)
        
        # Upload the DataFrame to the database
        df.to_sql(filename, engine, if_exists='replace', index=False)
        
        return True
    except Exception as e:
        print(f"Error uploading DataFrame to SQL: {e}")
        raise
        return False