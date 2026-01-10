"""
Mixins réutilisables pour les modèles SQLAlchemy.

Ce module définit des mixins qui ajoutent des fonctionnalités communes
à plusieurs modèles (timestamps, audit, versioning).
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    pass


class TimestampMixin:
    """
    Mixin ajoutant les colonnes created_at et updated_at.

    - created_at : auto-rempli à la création
    - updated_at : auto-mis à jour à chaque modification

    Usage:
        class MyModel(TimestampMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc),
        doc="Date et heure de création",
        info={"description": "Timestamp de création", "auto_generated": True}
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=datetime.now(timezone.utc),
        doc="Date et heure de dernière modification",
        info={"description": "Timestamp de mise à jour", "auto_generated": True}
    )


class AuditMixin:
    """
    Mixin ajoutant les colonnes created_by et updated_by.

    Permet de tracer quel utilisateur a créé/modifié un enregistrement.

    Usage:
        class MyModel(AuditMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant créé l'enregistrement",
        info={"description": "Référence vers le créateur"}
    )

    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID de l'utilisateur ayant modifié l'enregistrement",
        info={"description": "Référence vers le modificateur"}
    )


class VersionedMixin:
    """
    Mixin ajoutant une colonne de version pour le verrouillage optimiste.

    La colonne `version` doit être incrémentée manuellement ou via
    un trigger lors des modifications. Pour activer le verrouillage
    optimiste automatique de SQLAlchemy, ajoutez dans votre modèle :

        __mapper_args__ = {"version_id_col": __table__.c.version}

    Usage:
        class MyModel(VersionedMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)

    Note: Pour une implémentation complète de l'optimistic locking en
    production, utilisez les events SQLAlchemy ou configurez version_id_col
    au niveau du modèle individuel.
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Version pour verrouillage optimiste",
        info={"description": "Incrémenté à chaque modification", "auto_generated": True}
    )


class StatusMixin:
    """
    Mixin ajoutant une colonne status.

    Usage:
        class MyModel(StatusMixin, Base):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        doc="Statut de l'enregistrement",
        info={"description": "active, inactive, archived, etc.", "default": "active"}
    )