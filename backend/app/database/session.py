"""
Configuration de la session SQLAlchemy - Connexion PostgreSQL
Fournit l'engine, la factory de sessions, et la dependency FastAPI
"""

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# Logger pour debugging des connexions
logger = logging.getLogger(__name__)


# === 1. ENGINE (Connexion PostgreSQL) ===
#
# L'engine est le point d'entrée vers la base de données.
# Il gère un "pool" de connexions réutilisables pour les performances.

engine = create_engine(
    settings.DATABASE_URL,
    # === Pool de connexions ===
    poolclass=QueuePool,  # Type de pool (file d'attente)
    pool_size=5,  # Nombre de connexions permanentes
    max_overflow=10,  # Connexions supplémentaires si besoin (temporaires)
    pool_timeout=30,  # Timeout pour obtenir une connexion (secondes)
    pool_recycle=1800,  # Recycler les connexions après 30 min (évite déconnexions)
    pool_pre_ping=True,  # Vérifier que la connexion est vivante avant utilisation
    # === Options de connexion ===
    echo=settings.ENVIRONMENT == "development",  # Log SQL en dev uniquement
    echo_pool=False,  # Ne pas logger les événements du pool
    # === Paramètres PostgreSQL ===
    connect_args={
        "application_name": "carelink",  # Identifie l'app dans pg_stat_activity
        "options": "-c timezone=UTC",  # Forcer timezone UTC
    },
)


# === 2. SESSION LOCAL (Factory de sessions) ===
#
# SessionLocal est une "factory" qui crée des sessions à la demande.
# Chaque session = une transaction avec la base de données.

SessionLocal = sessionmaker(
    bind=engine,  # Connecté à notre engine
    autocommit=False,  # Pas de commit automatique (on contrôle explicitement)
    autoflush=False,  # Pas de flush automatique (meilleur contrôle)
    expire_on_commit=False,  # Garder les objets accessibles après commit
)


# === 3. FONCTIONS UTILITAIRES ===


def get_db_session() -> Session:
    """
    Crée une session de base de données (usage hors FastAPI).

    ⚠️ IMPORTANT : Vous devez fermer la session manuellement !

    Usage:
        db = get_db_session()
        try:
            # ... opérations
            db.commit()
        finally:
            db.close()

    Pour un context manager automatique, utilisez plutôt db_session().

    Returns:
        Nouvelle session SQLAlchemy
    """
    return SessionLocal()


class db_session:
    """
    Context manager pour utiliser une session hors FastAPI.

    Gère automatiquement le commit/rollback et la fermeture.

    Usage:
        with db_session() as db:
            user = db.query(User).first()
            user.last_login = datetime.utcnow()
            # Commit automatique si pas d'erreur

        # Rollback automatique si erreur
        with db_session() as db:
            db.add(user)
            raise Exception("Oops")  # → Rollback automatique
    """

    def __init__(self, commit_on_exit: bool = True):
        """
        Args:
            commit_on_exit: Si True, commit automatiquement à la sortie (si pas d'erreur)
        """
        self.db: Session | None = None
        self.commit_on_exit = commit_on_exit

    def __enter__(self) -> Session:
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None and self.commit_on_exit:
                # Pas d'exception → commit
                self.db.commit()
            else:
                # Exception levée → rollback
                self.db.rollback()
        finally:
            self.db.close()

        # Ne pas supprimer l'exception (la propager)
        return False


# === 4. VÉRIFICATION DE CONNEXION ===


def check_database_connection() -> bool:
    """
    Vérifie que la connexion à la base de données fonctionne.

    Utile pour les health checks et le démarrage de l'application.

    Returns:
        True si la connexion est OK, False sinon

    Example:
        >>> from app.database.session import check_database_connection
        >>> if check_database_connection():
        ...     print("✅ Base de données connectée")
        ... else:
        ...     print("❌ Impossible de se connecter à la base")
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données : {e}")
        return False


def get_database_info() -> dict:
    """
    Retourne des informations sur la connexion à la base de données.

    Utile pour le debugging et les endpoints d'administration.

    Returns:
        Dictionnaire avec les infos de connexion

    Example:
        >>> from app.database.session import get_database_info
        >>> info = get_database_info()
        >>> print(info)
        {
            'database': 'carelink_db',
            'host': 'localhost',
            'port': 5432,
            'connected': True,
            'pool_status': 'Pool size: 5  Connections in pool: 3 ...'
        }
    """
    url = engine.url

    return {
        "database": url.database,
        "host": url.host,
        "port": url.port or 5432,
        "connected": check_database_connection(),
        "pool_status": engine.pool.status(),  # Retourne un string avec toutes les infos
    }


# === 5. EVENT LISTENERS (Optionnel - Debugging) ===

if settings.ENVIRONMENT == "development":

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        """Log quand une nouvelle connexion est créée"""
        logger.debug("🔌 Nouvelle connexion PostgreSQL créée")

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Log quand une connexion est empruntée du pool"""
        logger.debug("📤 Connexion empruntée du pool")

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        """Log quand une connexion est rendue au pool"""
        logger.debug("📥 Connexion rendue au pool")
