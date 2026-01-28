"""
Gestionnaire de sessions applicatives avec Redis.

Gère les locks d'édition sur les ressources pour éviter les conflits
d'édition concurrente entre plusieurs utilisateurs.
"""

import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from enum import Enum

from app.core.redis_client import get_redis
from app.core.config import settings


class ResourceType(str, Enum):
    """Types de ressources verrouillables."""
    PATIENT = "patient"
    AGGIR_EVALUATION = "aggir_evaluation"
    # Ajouter d'autres types selon les besoins


class LockInfo:
    """Informations sur un lock d'édition."""

    def __init__(
            self,
            user_id: int,
            user_name: str,
            user_email: str,
            started_at: datetime,
            expires_at: datetime
    ):
        self.user_id = user_id
        self.user_name = user_name
        self.user_email = user_email
        self.started_at = started_at
        self.expires_at = expires_at

    def to_dict(self) -> Dict:
        """Sérialise en dictionnaire."""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_email": self.user_email,
            "started_at": self.started_at.isoformat(),
            "expires_at": self.expires_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "LockInfo":
        """Désérialise depuis un dictionnaire."""
        return cls(
            user_id=data["user_id"],
            user_name=data["user_name"],
            user_email=data["user_email"],
            started_at=datetime.fromisoformat(data["started_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
        )

    def is_expired(self) -> bool:
        """Vérifie si le lock a expiré."""
        return datetime.utcnow() > self.expires_at

    def time_remaining_seconds(self) -> int:
        """Retourne le temps restant avant expiration (en secondes)."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class SessionManager:
    """
    Gestionnaire de sessions applicatives avec Redis.

    Fonctionnalités :
    - Acquisition de locks d'édition (avec TTL)
    - Libération de locks
    - Heartbeat pour maintenir les locks actifs
    - Récupération des infos d'éditeur
    - Nettoyage automatique des locks expirés
    """

    def __init__(self):
        self.redis = get_redis()
        self.lock_ttl = settings.EDIT_LOCK_TTL_SECONDS

    def _get_lock_key(self, resource_type: ResourceType, resource_id: int) -> str:
        """Génère la clé Redis pour un lock."""
        return f"lock:{resource_type.value}:{resource_id}"

    def _get_user_locks_key(self, user_id: int) -> str:
        """Génère la clé Redis pour les locks d'un utilisateur."""
        return f"user_locks:{user_id}"

    def acquire_lock(
            self,
            resource_type: ResourceType,
            resource_id: int,
            user_id: int,
            user_name: str,
            user_email: str
    ) -> tuple[bool, Optional[LockInfo]]:
        """
        Tente d'acquérir un lock d'édition sur une ressource.

        Args:
            resource_type: Type de ressource (PATIENT, AGGIR_EVALUATION, etc.)
            resource_id: ID de la ressource
            user_id: ID de l'utilisateur
            user_name: Nom complet de l'utilisateur
            user_email: Email de l'utilisateur

        Returns:
            Tuple (success, lock_info):
            - success: True si le lock est acquis
            - lock_info: Informations sur le lock (existant si échec, nouveau si succès)

        Example:
            success, info = session_mgr.acquire_lock(
                ResourceType.PATIENT,
                patient_id=42,
                user_id=123,
                user_name="Dr Jean Dupont",
                user_email="jean.dupont@example.com"
            )

            if not success:
                print(f"Dossier verrouillé par {info.user_name}")
        """
        lock_key = self._get_lock_key(resource_type, resource_id)

        # Vérifier si un lock existe déjà
        existing_lock_data = self.redis.get(lock_key)

        if existing_lock_data:
            lock_info = LockInfo.from_dict(json.loads(existing_lock_data))

            # Si c'est le même utilisateur, renouveler le lock
            if lock_info.user_id == user_id:
                # Renouveler le TTL
                self.redis.expire(lock_key, self.lock_ttl)

                # Mettre à jour l'expiration
                lock_info.expires_at = datetime.utcnow() + timedelta(seconds=self.lock_ttl)
                self.redis.set(lock_key, json.dumps(lock_info.to_dict()), ex=self.lock_ttl)

                return True, lock_info

            # Lock déjà pris par un autre utilisateur
            # Vérifier si le lock a expiré (double sécurité)
            if lock_info.is_expired():
                # Lock expiré, on peut le réacquérir
                # (Normalement Redis devrait l'avoir supprimé, mais sécurité)
                pass
            else:
                # Lock actif par un autre utilisateur
                return False, lock_info

        # Acquérir le lock
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.lock_ttl)

        lock_info = LockInfo(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            started_at=now,
            expires_at=expires_at
        )

        # Stocker dans Redis avec TTL
        self.redis.setex(
            lock_key,
            self.lock_ttl,
            json.dumps(lock_info.to_dict())
        )

        # Ajouter à la liste des locks de l'utilisateur (pour nettoyage)
        user_locks_key = self._get_user_locks_key(user_id)
        lock_reference = f"{resource_type.value}:{resource_id}"
        self.redis.sadd(user_locks_key, lock_reference)
        # TTL sur la liste aussi (nettoyage automatique)
        self.redis.expire(user_locks_key, self.lock_ttl * 2)

        return True, lock_info

    def release_lock(
            self,
            resource_type: ResourceType,
            resource_id: int,
            user_id: int
    ) -> bool:
        """
        Libère un lock d'édition.

        Args:
            resource_type: Type de ressource
            resource_id: ID de la ressource
            user_id: ID de l'utilisateur (seul le propriétaire peut libérer)

        Returns:
            True si le lock a été libéré, False sinon
        """
        lock_key = self._get_lock_key(resource_type, resource_id)

        # Vérifier que c'est bien le propriétaire
        existing_lock_data = self.redis.get(lock_key)

        if not existing_lock_data:
            # Pas de lock existant
            return False

        lock_info = LockInfo.from_dict(json.loads(existing_lock_data))

        if lock_info.user_id != user_id:
            # Pas le propriétaire du lock
            return False

        # Supprimer le lock
        self.redis.delete(lock_key)

        # Retirer de la liste des locks de l'utilisateur
        user_locks_key = self._get_user_locks_key(user_id)
        lock_reference = f"{resource_type.value}:{resource_id}"
        self.redis.srem(user_locks_key, lock_reference)

        return True

    def keep_alive(
            self,
            resource_type: ResourceType,
            resource_id: int,
            user_id: int
    ) -> tuple[bool, Optional[int]]:
        """
        Renouvelle le TTL d'un lock (heartbeat).

        À appeler périodiquement depuis le frontend pour maintenir le lock actif.

        Args:
            resource_type: Type de ressource
            resource_id: ID de la ressource
            user_id: ID de l'utilisateur

        Returns:
            Tuple (success, time_remaining):
            - success: True si le lock a été renouvelé
            - time_remaining: Secondes restantes avant expiration (si succès)
        """
        lock_key = self._get_lock_key(resource_type, resource_id)

        existing_lock_data = self.redis.get(lock_key)

        if not existing_lock_data:
            # Lock n'existe plus (expiré ou libéré)
            return False, None

        lock_info = LockInfo.from_dict(json.loads(existing_lock_data))

        if lock_info.user_id != user_id:
            # Pas le propriétaire
            return False, None

        # Renouveler le TTL
        self.redis.expire(lock_key, self.lock_ttl)

        # Mettre à jour l'expiration dans les données
        lock_info.expires_at = datetime.utcnow() + timedelta(seconds=self.lock_ttl)
        self.redis.set(lock_key, json.dumps(lock_info.to_dict()), ex=self.lock_ttl)

        return True, self.lock_ttl

    def get_lock_info(
            self,
            resource_type: ResourceType,
            resource_id: int
    ) -> Optional[LockInfo]:
        """
        Récupère les informations d'un lock existant.

        Args:
            resource_type: Type de ressource
            resource_id: ID de la ressource

        Returns:
            LockInfo si un lock existe, None sinon
        """
        lock_key = self._get_lock_key(resource_type, resource_id)
        lock_data = self.redis.get(lock_key)

        if not lock_data:
            return None

        return LockInfo.from_dict(json.loads(lock_data))

    def is_locked(
            self,
            resource_type: ResourceType,
            resource_id: int
    ) -> bool:
        """Vérifie si une ressource est actuellement verrouillée."""
        lock_key = self._get_lock_key(resource_type, resource_id)
        return self.redis.exists(lock_key) > 0

    def is_locked_by_user(
            self,
            resource_type: ResourceType,
            resource_id: int,
            user_id: int
    ) -> bool:
        """Vérifie si une ressource est verrouillée par un utilisateur spécifique."""
        lock_info = self.get_lock_info(resource_type, resource_id)
        return lock_info is not None and lock_info.user_id == user_id

    def get_user_locks(self, user_id: int) -> List[str]:
        """
        Récupère la liste des locks détenus par un utilisateur.

        Returns:
            Liste de références de locks (ex: ["patient:42", "aggir_evaluation:17"])
        """
        user_locks_key = self._get_user_locks_key(user_id)
        locks = self.redis.smembers(user_locks_key)
        return list(locks) if locks else []

    def release_all_user_locks(self, user_id: int) -> int:
        """
        Libère tous les locks d'un utilisateur.

        Utile lors de la déconnexion ou en cas de problème.

        Returns:
            Nombre de locks libérés
        """
        locks = self.get_user_locks(user_id)
        count = 0

        for lock_ref in locks:
            try:
                resource_type_str, resource_id_str = lock_ref.split(":")
                resource_type = ResourceType(resource_type_str)
                resource_id = int(resource_id_str)

                if self.release_lock(resource_type, resource_id, user_id):
                    count += 1
            except (ValueError, KeyError):
                # Lock invalide, ignorer
                continue

        return count

    def force_release_lock(
            self,
            resource_type: ResourceType,
            resource_id: int
    ) -> bool:
        """
        Force la libération d'un lock (admin uniquement).

        À utiliser avec précaution, peut causer des pertes de données
        si l'utilisateur est en train d'éditer.

        Returns:
            True si un lock a été supprimé
        """
        lock_key = self._get_lock_key(resource_type, resource_id)

        # Récupérer l'info du lock pour nettoyer la liste utilisateur
        lock_info = self.get_lock_info(resource_type, resource_id)

        if lock_info:
            user_locks_key = self._get_user_locks_key(lock_info.user_id)
            lock_reference = f"{resource_type.value}:{resource_id}"
            self.redis.srem(user_locks_key, lock_reference)

        # Supprimer le lock
        return self.redis.delete(lock_key) > 0


# Instance singleton
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Retourne l'instance singleton du gestionnaire de sessions."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager