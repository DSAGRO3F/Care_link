"""initial_schema

Revision ID: ea35c5fec585
Revises: 
Create Date: 2025-12-15 20:14:15.461311+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ea35c5fec585'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# =============================================================================
# HELPERS - Fonctions utilitaires pour vérifications
# =============================================================================

def column_exists(table_name: str, column_name: str) -> bool:
    """Vérifie si une colonne existe dans une table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """))
    return result.fetchone() is not None


def constraint_exists(constraint_name: str) -> bool:
    """Vérifie si une contrainte existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM pg_constraint WHERE conname = '{constraint_name}'
    """))
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    """Vérifie si un index existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}'
    """))
    return result.fetchone() is not None


def enum_exists(enum_name: str) -> bool:
    """Vérifie si un type ENUM existe."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"""
        SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
    """))
    return result.fetchone() is not None


def upgrade() -> None:
    """Upgrade schema."""

    # ==========================================================================
    # 1. ENTITIES - Modifications majeures
    # ==========================================================================

    # 1.1 Créer le type ENUM pour entity_type (si n'existe pas)
    if not enum_exists('entity_type_enum'):
        entity_type_enum = postgresql.ENUM(
            'SSIAD', 'SAAD', 'SAD', 'SPASAD', 'SAP', 'EHPAD', 'RESIDENCE_AUTONOMIE',
            'ACCUEIL_JOUR', 'FAM', 'MAS', 'SESSAD', 'IME', 'ESAT', 'GCSMS', 'DAC',
            'CPTS', 'PCPE', 'PCO', 'HOSPITAL', 'CLINIC', 'CSI', 'HALTE_REPIT',
            'FORMATION', 'OTHER',
            name='entity_type_enum'
        )
        entity_type_enum.create(op.get_bind(), checkfirst=True)

    # 1.2 Créer le type ENUM pour integration_type (si n'existe pas)
    if not enum_exists('integration_type_enum'):
        integration_type_enum = postgresql.ENUM(
            'MANAGED', 'FEDERATED', 'CONVENTION', 'FINANCIAL_CONTROL',
            name='integration_type_enum'
        )
        integration_type_enum.create(op.get_bind(), checkfirst=True)

    # 1.3 Ajouter les nouvelles colonnes (si n'existent pas)
    if not column_exists('entities', 'short_name'):
        op.add_column('entities', sa.Column('short_name', sa.String(length=50), nullable=True))

    if not column_exists('entities', 'integration_type'):
        op.add_column('entities', sa.Column('integration_type', sa.Enum(
            'MANAGED', 'FEDERATED', 'CONVENTION', 'FINANCIAL_CONTROL',
            name='integration_type_enum', create_constraint=False
        ), nullable=True))

    if not column_exists('entities', 'parent_entity_id'):
        op.add_column('entities', sa.Column('parent_entity_id', sa.Integer(), nullable=True))

    if not column_exists('entities', 'siret'):
        op.add_column('entities', sa.Column('siret', sa.String(length=14), nullable=True))

    if not column_exists('entities', 'finess_ej'):
        op.add_column('entities', sa.Column('finess_ej', sa.String(length=9), nullable=True))

    if not column_exists('entities', 'authorized_capacity'):
        op.add_column('entities', sa.Column('authorized_capacity', sa.Integer(), nullable=True))

    if not column_exists('entities', 'authorization_date'):
        op.add_column('entities', sa.Column('authorization_date', sa.Date(), nullable=True))

    if not column_exists('entities', 'authorization_reference'):
        op.add_column('entities', sa.Column('authorization_reference', sa.String(length=100), nullable=True))

    if not column_exists('entities', 'postal_code'):
        op.add_column('entities', sa.Column('postal_code', sa.String(length=10), nullable=True))

    if not column_exists('entities', 'city'):
        op.add_column('entities', sa.Column('city', sa.String(length=100), nullable=True))

    if not column_exists('entities', 'website'):
        op.add_column('entities', sa.Column('website', sa.String(length=255), nullable=True))

    # 1.4 RENOMMER finess → finess_et (si finess existe et finess_et n'existe pas)
    if column_exists('entities', 'finess') and not column_exists('entities', 'finess_et'):
        op.alter_column('entities', 'finess', new_column_name='finess_et')
    elif not column_exists('entities', 'finess_et'):
        # Si ni finess ni finess_et n'existent, créer finess_et
        op.add_column('entities', sa.Column('finess_et', sa.String(length=9), nullable=True))

    # 1.5 Convertir entity_type de VARCHAR vers ENUM (si c'est encore VARCHAR)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'entities' AND column_name = 'entity_type'
    """))
    row = result.fetchone()
    if row and row[0] == 'character varying':
        op.execute("""
            ALTER TABLE entities 
            ALTER COLUMN entity_type TYPE entity_type_enum 
            USING entity_type::entity_type_enum
        """)

    # 1.6 Supprimer les anciennes contraintes (si existent)
    if constraint_exists('entities_finess_key'):
        op.drop_constraint('entities_finess_key', 'entities', type_='unique')

    if constraint_exists('entities_siren_key'):
        op.drop_constraint('entities_siren_key', 'entities', type_='unique')

    # 1.7 Créer les nouvelles contraintes (si n'existent pas)
    if not constraint_exists('uq_entities_siret'):
        op.create_unique_constraint('uq_entities_siret', 'entities', ['siret'])

    if not constraint_exists('uq_entities_finess_et'):
        op.create_unique_constraint('uq_entities_finess_et', 'entities', ['finess_et'])

    if not constraint_exists('fk_entities_parent_entity_id'):
        op.create_foreign_key(
            'fk_entities_parent_entity_id',
            'entities', 'entities',
            ['parent_entity_id'], ['id'],
            ondelete='SET NULL'
        )

    # ==========================================================================
    # 2. COORDINATION_ENTRIES - Correction des index
    # ==========================================================================

    # 2.1 Supprimer les anciens index (si existent)
    if index_exists('idx_coordination_entries_category'):
        op.drop_index('idx_coordination_entries_category', table_name='coordination_entries')
    if index_exists('idx_coordination_entries_patient_id'):
        op.drop_index('idx_coordination_entries_patient_id', table_name='coordination_entries')
    if index_exists('idx_coordination_entries_performed_at'):
        op.drop_index('idx_coordination_entries_performed_at', table_name='coordination_entries')
    if index_exists('idx_coordination_entries_user_id'):
        op.drop_index('idx_coordination_entries_user_id', table_name='coordination_entries')

    # 2.2 Créer les nouveaux index (si n'existent pas)
    if not index_exists('ix_coordination_entries_category'):
        op.create_index('ix_coordination_entries_category', 'coordination_entries', ['category'], unique=False)
    if not index_exists('ix_coordination_entries_patient_id'):
        op.create_index('ix_coordination_entries_patient_id', 'coordination_entries', ['patient_id'], unique=False)
    if not index_exists('ix_coordination_entries_performed_at'):
        op.create_index('ix_coordination_entries_performed_at', 'coordination_entries', ['performed_at'], unique=False)
    if not index_exists('ix_coordination_entries_user_id'):
        op.create_index('ix_coordination_entries_user_id', 'coordination_entries', ['user_id'], unique=False)

    # ==========================================================================
    # 3. PATIENT_DOCUMENTS - Correction des index
    # ==========================================================================

    if index_exists('idx_patient_documents_document_type'):
        op.drop_index('idx_patient_documents_document_type', table_name='patient_documents')
    if index_exists('idx_patient_documents_generated_at'):
        op.drop_index('idx_patient_documents_generated_at', table_name='patient_documents')
    if index_exists('idx_patient_documents_patient_id'):
        op.drop_index('idx_patient_documents_patient_id', table_name='patient_documents')

    if not index_exists('ix_patient_documents_document_type'):
        op.create_index('ix_patient_documents_document_type', 'patient_documents', ['document_type'], unique=False)
    if not index_exists('ix_patient_documents_patient_id'):
        op.create_index('ix_patient_documents_patient_id', 'patient_documents', ['patient_id'], unique=False)

    # ==========================================================================
    # 4. PATIENT_EVALUATIONS - Correction mineure
    # ==========================================================================

    # Vérifier la taille actuelle de la colonne
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT character_maximum_length FROM information_schema.columns 
        WHERE table_name = 'patient_evaluations' AND column_name = 'schema_version'
    """))
    row = result.fetchone()
    if row and row[0] and row[0] < 20:
        op.alter_column('patient_evaluations', 'schema_version',
                        existing_type=sa.VARCHAR(length=10),
                        type_=sa.String(length=20),
                        existing_nullable=False)

    if index_exists('ix_patient_evaluations_evaluation_date'):
        op.drop_index('ix_patient_evaluations_evaluation_date', table_name='patient_evaluations')
    if index_exists('ix_patient_evaluations_patient_date'):
        op.drop_index('ix_patient_evaluations_patient_date', table_name='patient_evaluations')

    # ==========================================================================
    # 5. USER_ROLES - Ajout contrainte unique (si n'existe pas)
    # ==========================================================================

    if not constraint_exists('uq_user_role'):
        op.create_unique_constraint('uq_user_role', 'user_roles', ['user_id', 'role_id'])


def downgrade() -> None:
    """Downgrade schema."""

    # ==========================================================================
    # 5. USER_ROLES
    # ==========================================================================
    if constraint_exists('uq_user_role'):
        op.drop_constraint('uq_user_role', 'user_roles', type_='unique')

    # ==========================================================================
    # 4. PATIENT_EVALUATIONS
    # ==========================================================================
    if not index_exists('ix_patient_evaluations_patient_date'):
        op.create_index('ix_patient_evaluations_patient_date', 'patient_evaluations', ['patient_id', 'evaluation_date'], unique=False)
    if not index_exists('ix_patient_evaluations_evaluation_date'):
        op.create_index('ix_patient_evaluations_evaluation_date', 'patient_evaluations', ['evaluation_date'], unique=False)

    op.alter_column('patient_evaluations', 'schema_version',
                    existing_type=sa.String(length=20),
                    type_=sa.VARCHAR(length=10),
                    existing_nullable=False)

    # ==========================================================================
    # 3. PATIENT_DOCUMENTS
    # ==========================================================================
    if index_exists('ix_patient_documents_patient_id'):
        op.drop_index('ix_patient_documents_patient_id', table_name='patient_documents')
    if index_exists('ix_patient_documents_document_type'):
        op.drop_index('ix_patient_documents_document_type', table_name='patient_documents')

    if not index_exists('idx_patient_documents_patient_id'):
        op.create_index('idx_patient_documents_patient_id', 'patient_documents', ['patient_id'], unique=False)
    if not index_exists('idx_patient_documents_generated_at'):
        op.create_index('idx_patient_documents_generated_at', 'patient_documents', ['patient_id', 'generated_at'], unique=False)
    if not index_exists('idx_patient_documents_document_type'):
        op.create_index('idx_patient_documents_document_type', 'patient_documents', ['patient_id', 'document_type'], unique=False)

    # ==========================================================================
    # 2. COORDINATION_ENTRIES
    # ==========================================================================
    if index_exists('ix_coordination_entries_user_id'):
        op.drop_index('ix_coordination_entries_user_id', table_name='coordination_entries')
    if index_exists('ix_coordination_entries_performed_at'):
        op.drop_index('ix_coordination_entries_performed_at', table_name='coordination_entries')
    if index_exists('ix_coordination_entries_patient_id'):
        op.drop_index('ix_coordination_entries_patient_id', table_name='coordination_entries')
    if index_exists('ix_coordination_entries_category'):
        op.drop_index('ix_coordination_entries_category', table_name='coordination_entries')

    if not index_exists('idx_coordination_entries_user_id'):
        op.create_index('idx_coordination_entries_user_id', 'coordination_entries', ['patient_id', 'user_id'], unique=False)
    if not index_exists('idx_coordination_entries_performed_at'):
        op.create_index('idx_coordination_entries_performed_at', 'coordination_entries', ['patient_id', 'performed_at'], unique=False)
    if not index_exists('idx_coordination_entries_patient_id'):
        op.create_index('idx_coordination_entries_patient_id', 'coordination_entries', ['patient_id'], unique=False)
    if not index_exists('idx_coordination_entries_category'):
        op.create_index('idx_coordination_entries_category', 'coordination_entries', ['patient_id', 'category'], unique=False)

    # ==========================================================================
    # 1. ENTITIES
    # ==========================================================================

    # 1.1 Supprimer les nouvelles contraintes
    if constraint_exists('fk_entities_parent_entity_id'):
        op.drop_constraint('fk_entities_parent_entity_id', 'entities', type_='foreignkey')
    if constraint_exists('uq_entities_finess_et'):
        op.drop_constraint('uq_entities_finess_et', 'entities', type_='unique')
    if constraint_exists('uq_entities_siret'):
        op.drop_constraint('uq_entities_siret', 'entities', type_='unique')

    # 1.2 Recréer les anciennes contraintes
    if not constraint_exists('entities_siren_key'):
        op.create_unique_constraint('entities_siren_key', 'entities', ['siren'])
    if not constraint_exists('entities_finess_key') and column_exists('entities', 'finess'):
        op.create_unique_constraint('entities_finess_key', 'entities', ['finess'])

    # 1.3 Reconvertir entity_type vers VARCHAR
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'entities' AND column_name = 'entity_type'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':  # C'est un ENUM
        op.execute("""
            ALTER TABLE entities 
            ALTER COLUMN entity_type TYPE VARCHAR(50) 
            USING entity_type::text
        """)

    # 1.4 RENOMMER finess_et → finess
    if column_exists('entities', 'finess_et') and not column_exists('entities', 'finess'):
        op.alter_column('entities', 'finess_et', new_column_name='finess')

    # 1.5 Supprimer les nouvelles colonnes
    for col in ['website', 'city', 'postal_code', 'authorization_reference',
                'authorization_date', 'authorized_capacity', 'finess_ej',
                'siret', 'parent_entity_id', 'integration_type', 'short_name']:
        if column_exists('entities', col):
            op.drop_column('entities', col)

    # 1.6 Supprimer les types ENUM
    op.execute("DROP TYPE IF EXISTS integration_type_enum")
    op.execute("DROP TYPE IF EXISTS entity_type_enum")