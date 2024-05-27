# from redisvl.extensions.llmcache import SemanticCache
# import os

# try:
#     llmcache = SemanticCache(
#         name="llmcache",                     # underlying search index name
#         prefix="llmcache",                   # redis key prefix for hash entries
#         redis_url=os.environ['REDIS_URL'],  # redis connection url string
#         distance_threshold=os.environ['REDIS_DISTANCE_THRESHOLD'] # semantic cache distance threshold
#     )
# except Exception as e:
#     print(f"Error connecting to redis: {e}")