from routes.metadata.metadata_agent import get_query_category,get_query_response
from routes.metadata.mongo_db_operations import get_project_data


def run_md_query(project_id:str , query: str):
        try:        
            query_category = get_query_category(query)
            data = get_project_data(project_id,query_category)
            response = get_query_response(data, query)
            return {"success": True, 'answer' : response}
        
        except Exception as e:
            print(f"Error running metadata query. {e}")
            raise