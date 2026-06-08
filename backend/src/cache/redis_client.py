# import redis

# redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
import os
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv(override=True)

redis_client = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN"),
)
