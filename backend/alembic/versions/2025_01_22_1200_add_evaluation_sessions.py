"""add_evaluation_sessions

Revision ID: add_evaluation_sessions
Revises: normalize_permissions
Create Date: 2025-01-22

Cette migration ajoute le support des évaluations multi-sessions :
1. Nouvelles colonnes sur `patient_evaluations` :
   - status: Statut de l'évaluation (DRAFT, VALIDATED, etc.)
   - completion_percent: Pourcentage de complétion
   - expires_at: Date d'expiration du brouillon (J+7)
   - medical_validated_at/by: Validation médecin coordonnateur
   - department_validated_at/name/ref: Validation Conseil Départemental

2. Nouvelle table `evaluation_sessions` :
   - Stocke les sessions de saisie (une évaluation = plusieurs sessions)
   - Support du mode hors-ligne (sync_status, local_session_id)

3. Nouveaux types ENUM PostgreSQL :
   - evaluation_status
   - evaluation_session_status
   - sync_status
"""

from typing import Sequence, Union
from datetime import datetime, timezone, timedelta

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_evaluation_sessions'
down_revision: Union[str, Sequence[str], None] = 'normalize_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# =============================================================================
# HELPERS
# =============================================================================

def table_exists(table_name: str) -> bool:
    """Vérifie si une table existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM pg_tables WHERE tablename = '{table_name}'
        )
    """))
    return result.scalar()


def column_exists(table_name: str, column_name: str) -> bool:
    """Vérifie si une colonne existe dans une table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def enum_exists(enum_name: str) -> bool:
    """Vérifie si un type ENUM existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT EXISTS (
            SELECT FROM pg_type WHERE typname = '{enum_name}'
        )
    """))
    return result.scalar()


# =============================================================================
# UPGRADE
# =============================================================================

def upgrade() -> None:
    """Upgrade schema - Ajouter le support des sessions d'évaluation."""

    # =========================================================================
    # 1. CRÉER LES TYPES ENUM
    # =========================================================================

    # Enum pour le statut des évaluations
    if not enum_exists('evaluation_status'):
        evaluation_status = postgresql.ENUM(
            'DRAFT',
            'PENDING_COMPLETION',
            'COMPLETE',
            'PENDING_MEDICAL',
            'PENDING_DEPARTMENT',
            'VALIDATED',
            'EXPIRED',
            'CANCELLED',
            name='evaluation_status'
        )
        evaluation_status.create(op.get_bind())

    # Enum pour le statut des sessions
    if not enum_exists('evaluation_session_status'):
        session_status = postgresql.ENUM(
            'IN_PROGRESS',
            'COMPLETED',
            'INTERRUPTED',
            name='evaluation_session_status'
        )
        session_status.create(op.get_bind())

    # Enum pour le statut de synchronisation
    if not enum_exists('sync_status'):
        sync_status = postgresql.ENUM(
            'SYNCED',
            'PENDING',
            'CONFLICT',
            'ERROR',
            name='sync_status'
        )
        sync_status.create(op.get_bind())

    # =========================================================================
    # 2. AJOUTER LES COLONNES À patient_evaluations
    # =========================================================================

    # Statut de l'évaluation
    if not column_exists('patient_evaluations', 'status'):
        op.add_column('patient_evaluations',
                      sa.Column('status', sa.String(30), nullable=True, default='DRAFT')
                      )
        # Mettre à jour les évaluations existantes
        op.execute("""
            UPDATE patient_evaluations 
            SET status = CASE 
                WHEN validated_at IS NOT NULL THEN 'VALIDATED'
                ELSE 'DRAFT'
            END
            WHERE status IS NULL
        """)
        # Rendre non nullable après migration
        op.alter_column('patient_evaluations', 'status', nullable=False)

    # Pourcentage de complétion
    if not column_exists('patient_evaluations', 'completion_percent'):
        op.add_column('patient_evaluations',
                      sa.Column('completion_percent', sa.Integer(), nullable=True, default=0)
                      )
        # Mettre à jour : 100% si validée, 0% sinon
        op.execute("""
            UPDATE patient_evaluations 
            SET completion_percent = CASE 
                WHEN validated_at IS NOT NULL THEN 100
                ELSE 0
            END
            WHERE completion_percent IS NULL
        """)
        op.alter_column('patient_evaluations', 'completion_percent', nullable=False)

    # Date d'expiration du brouillon
    if not column_exists('patient_evaluations', 'expires_at'):
        op.add_column('patient_evaluations',
                      sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
                      )
        # Définir expiration J+7 pour les brouillons existants
        op.execute("""
            UPDATE patient_evaluations 
            SET expires_at = created_at + INTERVAL '7 days'
            WHERE status = 'DRAFT' AND expires_at IS NULL
        """)

    # Validation médecin coordonnateur
    if not column_exists('patient_evaluations', 'medical_validated_at'):
        op.add_column('patient_evaluations',
                      sa.Column('medical_validated_at', sa.DateTime(timezone=True), nullable=True)
                      )

    if not column_exists('patient_evaluations', 'medical_validated_by'):
        op.add_column('patient_evaluations',
                      sa.Column('medical_validated_by', sa.Integer(),
                                sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
                      )

    # Validation Conseil Départemental
    if not column_exists('patient_evaluations', 'department_validated_at'):
        op.add_column('patient_evaluations',
                      sa.Column('department_validated_at', sa.DateTime(timezone=True), nullable=True)
                      )

    if not column_exists('patient_evaluations', 'department_validator_name'):
        op.add_column('patient_evaluations',
                      sa.Column('department_validator_name', sa.String(200), nullable=True)
                      )

    if not column_exists('patient_evaluations', 'department_validator_reference'):
        op.add_column('patient_evaluations',
                      sa.Column('department_validator_reference', sa.String(100), nullable=True)
                      )

    # Migration des évaluations validées existantes
    # Si validated_at existe, copier vers medical_validated_at
    op.execute("""
        UPDATE patient_evaluations 
        SET medical_validated_at = validated_at,
            medical_validated_by = validated_by
        WHERE validated_at IS NOT NULL 
          AND medical_validated_at IS NULL
    """)

    # =========================================================================
    # 3. CRÉER LA TABLE evaluation_sessions
    # =========================================================================

    if not table_exists('evaluation_sessions'):
        op.create_table(
            'evaluation_sessions',

            # Clé primaire
            sa.Column('id', sa.Integer(), primary_key=True),

            # Multi-tenant
            sa.Column('tenant_id', sa.Integer(),
                      sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                      nullable=False, index=True),

            # Références
            sa.Column('evaluation_id', sa.Integer(),
                      sa.ForeignKey('patient_evaluations.id', ondelete='CASCADE'),
                      nullable=False, index=True),
            sa.Column('user_id', sa.Integer(),
                      sa.ForeignKey('users.id', ondelete='SET NULL'),
                      nullable=False, index=True),

            # Temporalité
            sa.Column('started_at', sa.DateTime(timezone=True),
                      nullable=False, default=datetime.now(timezone.utc)),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),

            # Statut
            sa.Column('status', sa.String(30), nullable=False, default='IN_PROGRESS'),

            # Mode hors-ligne
            sa.Column('sync_status', sa.String(20), nullable=False, default='SYNCED'),
            sa.Column('local_session_id', sa.String(100), nullable=True),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),

            # Métadonnées
            sa.Column('device_info', sa.String(200), nullable=True),
            sa.Column('variables_recorded', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True),
                      nullable=False, default=datetime.now(timezone.utc)),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

            # Commentaire table
            comment='Table des sessions de saisie pour les évaluations multi-jours'
        )

        # Index pour les requêtes fréquentes
        op.create_index(
            'ix_evaluation_sessions_evaluation_started',
            'evaluation_sessions',
            ['evaluation_id', 'started_at']
        )

        op.create_index(
            'ix_evaluation_sessions_sync_status',
            'evaluation_sessions',
            ['sync_status']
        )

        op.create_index(
            'ix_evaluation_sessions_local_id',
            'evaluation_sessions',
            ['local_session_id'],
            unique=False  # Pas unique car peut être NULL
        )

    # =========================================================================
    # 4. AJOUTER UN INDEX SUR patient_evaluations.status
    # =========================================================================

    op.create_index(
        'ix_patient_evaluations_status',
        'patient_evaluations',
        ['status'],
        if_not_exists=True
    )

    op.create_index(
        'ix_patient_evaluations_expires',
        'patient_evaluations',
        ['expires_at'],
        if_not_exists=True
    )


# =============================================================================
# DOWNGRADE
# =============================================================================

def downgrade() -> None:
    """Downgrade schema - Retirer le support des sessions d'évaluation."""

    # =========================================================================
    # 1. SUPPRIMER LES INDEX
    # =========================================================================

    op.drop_index('ix_patient_evaluations_expires', table_name='patient_evaluations',
                  if_exists=True)
    op.drop_index('ix_patient_evaluations_status', table_name='patient_evaluations',
                  if_exists=True)

    # =========================================================================
    # 2. SUPPRIMER LA TABLE evaluation_sessions
    # =========================================================================

    if table_exists('evaluation_sessions'):
        op.drop_index('ix_evaluation_sessions_local_id',
                      table_name='evaluation_sessions', if_exists=True)
        op.drop_index('ix_evaluation_sessions_sync_status',
                      table_name='evaluation_sessions', if_exists=True)
        op.drop_index('ix_evaluation_sessions_evaluation_started',
                      table_name='evaluation_sessions', if_exists=True)
        op.drop_table('evaluation_sessions')

    # =========================================================================
    # 3. SUPPRIMER LES COLONNES DE patient_evaluations
    # =========================================================================

    columns_to_drop = [
        'department_validator_reference',
        'department_validator_name',
        'department_validated_at',
        'medical_validated_by',
        'medical_validated_at',
        'expires_at',
        'completion_percent',
        'status',
    ]

    for col in columns_to_drop:
        if column_exists('patient_evaluations', col):
            op.drop_column('patient_evaluations', col)

    # =========================================================================
    # 4. SUPPRIMER LES TYPES ENUM
    # =========================================================================

    # Note: Les ENUMs doivent être supprimés après les colonnes qui les utilisent

    if enum_exists('sync_status'):
        op.execute("DROP TYPE IF EXISTS sync_status")

    if enum_exists('evaluation_session_status'):
        op.execute("DROP TYPE IF EXISTS evaluation_session_status")

    if enum_exists('evaluation_status'):
        op.execute("DROP TYPE IF EXISTS evaluation_status")