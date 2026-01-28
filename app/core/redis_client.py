"""Client Redis singleton pour l'application."""

import redis
from typing import Optional
from app.core.config import settings


class RedisClient:
    """Client Redis singleton avec pool de connexions."""

    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Retourne l'instance singleton du client Redis."""
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,  # Décoder automatiquement en string
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
        return cls._instance

    @classmethod
    def close(cls):
        """Ferme la connexion Redis (à appeler lors de l'arrêt de l'app)."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_redis() -> redis.Redis:
    """Fonction helper pour récupérer le client Redis."""
    return RedisClient.get_client()