"""B40-J3 — Fil d'échange (validation_exchanges) + chaînage VR (previous_vr_id)

Revision ID: b40j3aaa2026
Revises: b40j1aaa2026
Create Date: 2026-06-02

Crée :
- 2 types ENUM PG : exchange_action_type_enum, exchange_visibility_enum
- table validation_exchanges (fil d'échange, rattachée à validation_requests — Option A)
- colonne validation_requests.previous_vr_id (SELF-FK, chaînage explicite du relais)

NB : les policies RLS de validation_exchanges sont ajoutées au script séparé
backend/scripts/rls_policies.sql (patron tenant standard, calqué validation_requests),
conformément à la pratique projet (RLS hors Alembic).

Référence : cadrage_ValidationExchange.md.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b40j3aaa2026"
down_revision: str | None = "b40j1aaa2026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# === ENUM PG (create_type=False — création explicite via .create(), comme B40-J1) ===

exchange_action_type_enum = postgresql.ENUM(
    "SUBMIT",
    "COMMENT",
    "RESUBMIT",
    "VALIDATE",
    "REQUEST_INFO",
    "INVALIDATE",
    "TRANSMIT",
    name="exchange_action_type_enum",
    create_type=False,
)

exchange_visibility_enum = postgresql.ENUM(
    "INTERNAL_ONLY",
    "SHARED_EXTERNAL",
    name="exchange_visibility_enum",
    create_type=False,
)


def upgrade() -> None:
    """Création du fil d'échange + chaînage explicite des VR (B40-J3)."""

    # Bypass RLS pour les opérations de migration sur tables sous policy
    op.execute("SET LOCAL app.is_super_admin = 'true'")

    bind = op.get_bind()

    # =========================================================================
    # ÉTAPE 1 — Création des 2 nouveaux ENUM PostgreSQL
    # =========================================================================

    exchange_action_type_enum.create(bind, checkfirst=True)
    exchange_visibility_enum.create(bind, checkfirst=True)

    # =========================================================================
    # ÉTAPE 2 — Chaînage explicite : validation_requests.previous_vr_id (SELF-FK)
    # =========================================================================

    op.add_column(
        "validation_requests",
        sa.Column(
            "previous_vr_id",
            sa.Integer(),
            sa.ForeignKey("validation_requests.id", ondelete="SET NULL"),
            nullable=True,
            comment="VR précédente dans la chaîne (interne→médical→financement)",
        ),
    )
    op.create_index(
        "ix_validation_requests_previous_vr",
        "validation_requests",
        ["previous_vr_id"],
    )

    # =========================================================================
    # ÉTAPE 3 — Création de la table validation_exchanges
    # =========================================================================

    op.create_table(
        "validation_exchanges",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            comment="Tenant propriétaire de cet enregistrement",
        ),
        sa.Column(
            "validation_request_id",
            sa.Integer(),
            sa.ForeignKey("validation_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Auteur
        sa.Column(
            "author_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("author_role", sa.String(length=50), nullable=False),
        # Nature de l'entrée
        sa.Column("action_type", exchange_action_type_enum, nullable=False),
        sa.Column(
            "visibility",
            exchange_visibility_enum,
            nullable=False,
            server_default="SHARED_EXTERNAL",
        ),
        # Contenu
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "attachments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        # TimestampMixin (created_at non-null server_default now ; updated_at nullable
        # sans server_default — pattern projet TimestampMixin, cf. B40-J1)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Entrées du fil d'échange de validation (Phase 4 bis B40-J3)",
    )

    # Indexes validation_exchanges
    op.create_index(
        "ix_validation_exchanges_vr_created",
        "validation_exchanges",
        ["validation_request_id", "created_at"],
    )
    op.create_index(
        "ix_validation_exchanges_tenant_id",
        "validation_exchanges",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Suppression symétrique (ordre inverse) du fil d'échange + chaînage VR."""

    op.execute("SET LOCAL app.is_super_admin = 'true'")

    bind = op.get_bind()

    # =========================================================================
    # ÉTAPE 3 inv — Suppression validation_exchanges
    # =========================================================================

    op.drop_index(
        "ix_validation_exchanges_tenant_id",
        table_name="validation_exchanges",
    )
    op.drop_index(
        "ix_validation_exchanges_vr_created",
        table_name="validation_exchanges",
    )
    op.drop_table("validation_exchanges")

    # =========================================================================
    # ÉTAPE 2 inv — Suppression previous_vr_id sur validation_requests
    # =========================================================================

    op.drop_index(
        "ix_validation_requests_previous_vr",
        table_name="validation_requests",
    )
    op.drop_column("validation_requests", "previous_vr_id")

    # =========================================================================
    # ÉTAPE 1 inv — Suppression des 2 ENUM
    # =========================================================================

    exchange_visibility_enum.drop(bind, checkfirst=True)
    exchange_action_type_enum.drop(bind, checkfirst=True)