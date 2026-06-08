import hashlib
from src.cache.redis_client import redis_client


class KnowledgeBaseCache:

    def make_key(
        self,
        query: str,
        role: str,
        report_type: str
    ):
        normalized = query.strip().lower()

        raw = f"{role}:{report_type}:{normalized}"

        return (
            "kb:"
            + hashlib.sha256(raw.encode()).hexdigest()
        )

    def get(
        self,
        role: str,
        query: str,
        report_type: str
    ):
        key = self.make_key(
            query=query,
            role=role,
            report_type=report_type
        )

        return redis_client.get(key)

    def set(
        self,
        query: str,
        role: str,
        report_type: str,
        answer: str,
        ttl: int = 86400,
    ):
        key = self.make_key(
            query=query,
            role=role,
            report_type=report_type
        )

        redis_client.setex(
            key,
            ttl,
            answer
        )


kb_cache = KnowledgeBaseCache()

