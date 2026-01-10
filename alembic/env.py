"""
Alembic Environment Configuration - CareLink

Ce fichier configure Alembic pour :
1. Charger l'URL de la base depuis app/core/config.py (qui lit le .env)
2. Importer tous les modèles SQLAlchemy pour la détection automatique
3. Supporter les migrations online (base connectée) et offline (génération SQL)
"""

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config
from sqlalchemy import create_engine

from alembic import context

# === Import de la configuration CareLink ===
from app.core.config import settings

# === Import de la Base et des modèles ===
# Cet import est CRUCIAL : il charge tous les modèles pour que
# Alembic puisse détecter les tables à créer/modifier
from app.models.base import Base

# Configuration Alembic depuis alembic.ini
config = context.config

# Configuration du logging depuis alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées des modèles pour autogenerate
target_metadata = Base.metadata


# === Helpers ===

def get_url() -> str:
    """
    Retourne l'URL de la base de données depuis les settings.

    L'URL est chargée depuis le .env via Pydantic Settings.
    """
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Exécute les migrations en mode 'offline'.

    En mode offline, Alembic génère le SQL sans se connecter à la base.
    Utile pour générer des scripts SQL à exécuter manuellement.

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare les types de colonnes (pas seulement les noms)
        compare_type=True,
        # Compare les contraintes de clés étrangères
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Exécute les migrations en mode 'online'.

    En mode online, Alembic se connecte à la base et applique les migrations.
    C'est le mode normal d'utilisation.

    Usage:
        alembic upgrade head
    """
    # Créer l'engine avec l'URL des settings
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare les types de colonnes
            compare_type=True,
            # Compare les valeurs par défaut côté serveur
            compare_server_default=True,
            # Inclure les objets (comme les ENUMs) dans les migrations
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filtre les objets à inclure dans les migrations.

    Par défaut, inclut tout. Peut être personnalisé pour exclure
    certaines tables (ex: tables système, tables de cache).
    """
    # Exclure certaines tables si nécessaire
    # if type_ == "table" and name.startswith("_"):
    #     return False
    return True


# === Point d'entrée ===

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()