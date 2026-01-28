"""
Initialisation de la base de données CareLink v4.1 (Multi-tenant)
Crée les tables, tenant par défaut, professions, rôles système, pays/entité et compte admin.
"""

import logging
import sys
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.base_class import Base
from app.database.session import engine, db_session, check_database_connection
# =============================================================================
# IMPORTS DES MODÈLES (via le module centralisé)
# =============================================================================
from app.models import (
    # Référence
    Country,
    # Organisation
    Entity,
    # Utilisateurs
    User,
    Role,
    INITIAL_ROLES,
    Profession,
    INITIAL_PROFESSIONS,
    UserRole,
    UserEntity,
    Permission,  # AJOUT v4.3
    RolePermission,  # AJOUT v4.3
    # Tenant (nouveau v4.1)
    Tenant,
    TenantStatus,
    TenantType,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
    # Enums
    EntityType,
    ContractType,
    RoleName,
    PermissionCategory,  # AJOUT v4.3
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# 1. CRÉATION DES TABLES
# =============================================================================

def create_all_tables() -> bool:
    """
    Crée toutes les tables de la base de données.

    Utilise les métadonnées de Base qui contiennent tous les modèles
    importés via app/database/base_class.py

    Returns:
        True si succès, False sinon
    """
    try:
        logger.info("📦 Création des tables...")
        Base.metadata.create_all(bind=engine)

        # Lister les tables créées
        table_names = list(Base.metadata.tables.keys())
        logger.info(f"✅ {len(table_names)} tables créées : {', '.join(sorted(table_names))}")

        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables : {e}")
        return False


def drop_all_tables() -> bool:
    """
    Supprime toutes les tables de la base de données.

    ⚠️ ATTENTION : Cette action est irréversible !
    Utilisé principalement pour les tests ou le reset complet.

    Returns:
        True si succès, False sinon
    """
    try:
        logger.warning("❗️❗️❗️️ Suppression de toutes les tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ Toutes les tables ont été supprimées")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression des tables : {e}")
        return False


# =============================================================================
# 2. INITIALISATION DES PROFESSIONS
# =============================================================================

def init_professions(db: Session) -> list[Profession]:
    """
    Crée les professions de santé réglementées.

    Les 17 professions prédéfinies (INITIAL_PROFESSIONS) :
    - Médicales : Médecin, Pharmacien, Chirurgien-dentiste, Sage-femme
    - Paramédicales : Infirmier, Kinésithérapeute, Aide-soignant, etc.
    - Administratives : Administratif, Coordinateur

    Args:
        db: Session SQLAlchemy

    Returns:
        Liste des professions créées/existantes
    """
    logger.info("🏥 Initialisation des professions...")

    professions = []
    created_count = 0

    for prof_data in INITIAL_PROFESSIONS:
        # Vérifier si la profession existe déjà
        existing = db.query(Profession).filter(
            Profession.name == prof_data["name"]
        ).first()

        if existing:
            professions.append(existing)
            logger.debug(f"   ℹ️ {prof_data['name']} existe déjà")
        else:
            # Créer la profession
            profession = Profession(
                name=prof_data["name"],
                code=prof_data.get("code"),
                category=prof_data.get("category"),
                requires_rpps=prof_data.get("requires_rpps", True)
            )
            db.add(profession)
            professions.append(profession)
            created_count += 1
            logger.info(f"   ✅ {prof_data['name']} créée")

    db.flush()
    logger.info(f"✅ {len(professions)} professions ({created_count} nouvelles)")

    return professions


# =============================================================================
# 3. INITIALISATION DES RÔLES
# =============================================================================

def init_roles(db: Session) -> list[Role]:
    """
    Crée ou met à jour les rôles système (v4.3 avec Permission/RolePermission).

    Les 8 rôles prédéfinis (INITIAL_ROLES) :
    - ADMIN : Tous les droits
    - COORDINATEUR : Gestion équipe et accès
    - MEDECIN_TRAITANT : Accès complet patients + validation
    - MEDECIN_SPECIALISTE : Consultation
    - INFIRMIERE : Soins + évaluations
    - AIDE_SOIGNANTE : Consultation + mesures vitales
    - KINESITHERAPEUTE : Consultation
    - INTERVENANT : Lecture seule

    Args:
        db: Session SQLAlchemy

    Returns:
        Liste des rôles créés/mis à jour
    """
    logger.info("🎭 Initialisation des rôles système (v4.3)...")

    # Cache des permissions pour éviter les requêtes répétées
    permission_cache = {}

    def get_or_create_permission(perm_code: str) -> Permission:
        """Récupère ou crée une permission."""
        if perm_code in permission_cache:
            return permission_cache[perm_code]

        # Chercher la permission existante
        perm = db.query(Permission).filter(Permission.code == perm_code).first()
        if not perm:
            # Déterminer la catégorie selon le préfixe
            if perm_code.startswith("PATIENT"):
                cat = PermissionCategory.PATIENT
            elif perm_code.startswith("EVALUATION"):
                cat = PermissionCategory.PATIENT
            elif perm_code.startswith("VITALS"):
                cat = PermissionCategory.PATIENT
            elif perm_code.startswith("USER"):
                cat = PermissionCategory.USER
            elif perm_code.startswith("ENTITY"):
                cat = PermissionCategory.ORGANIZATION
            elif perm_code.startswith("CAREPLAN"):
                cat = PermissionCategory.CAREPLAN
            elif perm_code.startswith("COORDINATION"):
                cat = PermissionCategory.COORDINATION
            elif perm_code.startswith("ADMIN"):
                cat = PermissionCategory.ADMIN
            else:
                cat = PermissionCategory.SYSTEM

            perm = Permission(
                code=perm_code,
                name=perm_code.replace("_", " ").title(),
                description=f"Permission {perm_code}",
                category=cat
            )
            db.add(perm)
            db.flush()
            logger.debug(f"      📝 Permission créée: {perm_code}")

        permission_cache[perm_code] = perm
        return perm

    roles = []
    created_count = 0

    for role_data in INITIAL_ROLES:
        # Vérifier si le rôle existe déjà
        existing = db.query(Role).filter(
            Role.name == role_data["name"]
        ).first()

        if existing:
            # Rôle existe - mettre à jour les permissions via RolePermission
            existing_perm_codes = {rp.permission.code for rp in existing.role_permissions}
            new_perm_codes = set(role_data.get("permissions", []))

            # Ajouter les permissions manquantes
            for perm_code in new_perm_codes - existing_perm_codes:
                perm = get_or_create_permission(perm_code)
                role_perm = RolePermission(role_id=existing.id, permission_id=perm.id)
                db.add(role_perm)
                logger.debug(f"      ➕ {perm_code} ajouté à {role_data['name']}")

            if new_perm_codes - existing_perm_codes:
                logger.info(f"   🔄 {role_data['name']} - permissions mises à jour")
            roles.append(existing)
        else:
            # Créer le rôle (sans permissions directes en v4.3)
            role = Role(
                name=role_data["name"],
                description=role_data.get("description"),
                is_system_role=role_data.get("is_system_role", True)
            )
            db.add(role)
            db.flush()  # Pour obtenir l'ID

            # Créer les associations RolePermission
            perm_codes = role_data.get("permissions", [])
            for perm_code in perm_codes:
                perm = get_or_create_permission(perm_code)
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.add(role_perm)

            roles.append(role)
            created_count += 1
            logger.info(f"   ✅ {role_data['name']} - {len(perm_codes)} permissions")

    db.flush()
    logger.info(f"✅ {len(roles)} rôles système ({created_count} nouveaux)")

    return roles


# =============================================================================
# 4. INITIALISATION DU PAYS PAR DÉFAUT
# =============================================================================

def init_default_country(db: Session) -> Country:
    """
    Crée le pays par défaut (France).

    Args:
        db: Session SQLAlchemy

    Returns:
        Country créé ou existant
    """
    logger.info("🌍 Initialisation du pays par défaut...")

    # Vérifier si France existe déjà
    france = db.query(Country).filter(
        Country.country_code == "FR"
    ).first()

    if france:
        logger.info("   ℹ️ France existe déjà")
    else:
        france = Country(
            name="France",
            country_code="FR",
            status="active"
        )
        db.add(france)
        db.flush()
        logger.info("   ✅ France créé")

    return france


# =============================================================================
# 5. INITIALISATION DU TENANT PAR DÉFAUT (NOUVEAU v4.1)
# =============================================================================

def init_default_tenant(db: Session, country: Country) -> Tenant:
    """
    Crée le tenant par défaut (GCSMS CareLink).

    Le tenant représente le client/locataire de la plateforme.
    Il peut être un GCSMS (groupement) ou une structure indépendante.

    Args:
        db: Session SQLAlchemy
        country: Pays de rattachement

    Returns:
        Tenant créé ou existant
    """
    logger.info("🏛️ Initialisation du tenant par défaut...")

    # Vérifier si le tenant par défaut existe déjà
    tenant = db.query(Tenant).filter(
        Tenant.code == "CARELINK-DEFAULT"
    ).first()

    if tenant:
        logger.info("   ℹ️ Tenant CARELINK-DEFAULT existe déjà")
    else:
        tenant = Tenant(
            code="CARELINK-DEFAULT",
            name="CareLink Demo",
            legal_name="CareLink SAS (Demo)",
            tenant_type=TenantType.GCSMS,
            status=TenantStatus.ACTIVE,
            contact_email="contact@carelink.fr",
            contact_phone="0148000000",
            address_line1="1 rue de la Santé",
            postal_code="75013",
            city="Paris",
            country_id=country.id,
            encryption_key_id="default-dev-key-DO-NOT-USE-IN-PROD",
            timezone="Europe/Paris",
            locale="fr_FR",
            max_patients=1000,
            max_users=100,
            max_storage_gb=50,
            settings={
                "features": {
                    "aggir_evaluation": True,
                    "document_generation": True,
                    "device_integration": False
                },
                "notifications": {
                    "email": True,
                    "sms": False
                }
            },
            activated_at=datetime.now()
        )
        db.add(tenant)
        db.flush()
        logger.info("   ✅ Tenant CARELINK-DEFAULT créé")

    return tenant


def init_default_subscription(db: Session, tenant: Tenant) -> Subscription:
    """
    Crée l'abonnement par défaut pour le tenant.

    Args:
        db: Session SQLAlchemy
        tenant: Tenant propriétaire

    Returns:
        Subscription créée ou existante
    """
    logger.info("💳 Initialisation de l'abonnement par défaut...")

    # Vérifier si un abonnement actif existe déjà
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()

    if subscription:
        logger.info("   ℹ️ Abonnement actif existe déjà")
    else:
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_code=SubscriptionPlan.L,
            plan_name="Plan Large - Demo",
            status=SubscriptionStatus.ACTIVE,
            started_at=date.today(),
            base_price_cents=0,  # Gratuit pour la démo
            price_per_extra_patient_cents=0,
            currency="EUR",
            billing_cycle=BillingCycle.MONTHLY,
            included_patients=1000,
            included_users=100,
            included_storage_gb=50,
            notes="Abonnement de démonstration - usage interne uniquement"
        )
        db.add(subscription)
        db.flush()
        logger.info("   ✅ Abonnement Plan L (Demo) créé")

    return subscription


# =============================================================================
# 6. INITIALISATION DE L'ENTITÉ PAR DÉFAUT
# =============================================================================

def init_default_entity(db: Session, country: Country, tenant: Tenant) -> Entity:
    """
    Crée l'entité de soins par défaut (SSIAD exemple).

    Args:
        db: Session SQLAlchemy
        country: Pays de rattachement
        tenant: Tenant propriétaire

    Returns:
        Entity créée ou existante
    """
    logger.info("🏢 Initialisation de l'entité par défaut...")

    # Vérifier si l'entité exemple existe déjà
    entity = db.query(Entity).filter(
        Entity.name == "SSIAD CareLink Paris"
    ).first()

    if entity:
        logger.info("   ℹ️ SSIAD CareLink Paris existe déjà")
        # Mettre à jour le tenant_id si nécessaire
        if entity.tenant_id != tenant.id:
            entity.tenant_id = tenant.id
            logger.info("   🔄 tenant_id mis à jour")
    else:
        entity = Entity(
            name="SSIAD CareLink Paris",
            short_name="SSIAD Paris",
            entity_type=EntityType.SSIAD,
            country_id=country.id,
            tenant_id=tenant.id,  # NOUVEAU: Rattachement au tenant
            siret="12345678901234",
            siren="123456789",
            finess_et="750000001",
            address="1 rue de la Santé",
            postal_code="75013",
            city="Paris",
            phone="0148000001",
            email="contact@carelink-paris.fr",
            latitude=48.8356,
            longitude=2.3539,
            default_intervention_radius_km=15,
            status="active"
        )
        db.add(entity)
        db.flush()
        logger.info("   ✅ SSIAD CareLink Paris créé")

    return entity


# =============================================================================
# 7. INITIALISATION DU COMPTE ADMIN
# =============================================================================

def init_default_admin(
    db: Session,
    entity: Entity,
    tenant: Tenant,
    email: str = "admin@carelink.fr",
    rpps: str = "00000000001"
) -> Optional[User]:
    """
    Crée le compte administrateur système.

    Ce compte est utilisé pour l'administration et la configuration
    initiale de l'application.

    Args:
        db: Session SQLAlchemy
        entity: Entité de rattachement
        tenant: Tenant de rattachement
        email: Email de l'admin
        rpps: Numéro RPPS fictif pour l'admin

    Returns:
        User créé ou None si déjà existant
    """
    logger.info("👤 Initialisation du compte administrateur...")

    # Vérifier si l'admin existe déjà
    existing_admin = db.query(User).filter(User.email == email).first()

    if existing_admin:
        logger.info(f"   ℹ️ Admin {email} existe déjà")
        # Mettre à jour le tenant_id si nécessaire
        if existing_admin.tenant_id != tenant.id:
            existing_admin.tenant_id = tenant.id
            logger.info("   🔄 tenant_id mis à jour")
        return existing_admin

    # Récupérer le rôle ADMIN
    admin_role = db.query(Role).filter(Role.name == RoleName.ADMIN.value).first()
    if not admin_role:
        logger.error("   ❌ Rôle ADMIN non trouvé ! Lancez d'abord init_roles()")
        return None

    # Récupérer la profession Administratif
    admin_profession = db.query(Profession).filter(
        Profession.name == "Administratif"
    ).first()
    if not admin_profession:
        logger.warning("   ⚠️ Profession 'Administratif' non trouvée, admin créé sans profession")

    # Créer l'utilisateur admin
    admin_user = User(
        email=email,
        first_name="Admin",
        last_name="CareLink",
        rpps=rpps,
        profession_id=admin_profession.id if admin_profession else None,
        tenant_id=tenant.id,  # NOUVEAU: Rattachement au tenant
        is_active=True,
        is_admin=True
    )
    db.add(admin_user)
    db.flush()  # Pour obtenir l'ID

    # Créer l'association UserRole (admin → rôle ADMIN)
    user_role = UserRole(
        user_id=admin_user.id,
        role_id=admin_role.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        assigned_by=admin_user.id  # Auto-assigné à la création
    )
    db.add(user_role)

    # Créer l'association UserEntity (admin → entité par défaut)
    user_entity = UserEntity(
        user_id=admin_user.id,
        entity_id=entity.id,
        tenant_id=tenant.id,  # MULTI-TENANT v4.3
        is_primary=True,
        contract_type=ContractType.SALARIE.value,
        start_date=date.today()
    )
    db.add(user_entity)

    db.flush()

    logger.info(f"   ✅ Admin créé : {email}")
    logger.info(f"   📧 Email : {email}")
    logger.info(f"   🏥 RPPS : {rpps}")
    logger.info(f"   🏛️ Tenant : {tenant.name}")
    logger.info(f"   🏢 Entité : {entity.name}")
    logger.info(f"   🎭 Rôle : ADMIN")

    return admin_user


# =============================================================================
# 8. FONCTION D'INITIALISATION COMPLÈTE
# =============================================================================

def init_database(
    drop_existing: bool = False,
    admin_email: str = "admin@carelink.fr",
    admin_rpps: str = "00000000001"
) -> bool:
    """
    Initialise complètement la base de données CareLink.

    Étapes :
    1. Vérifie la connexion à PostgreSQL
    2. (Optionnel) Supprime les tables existantes
    3. Crée toutes les tables
    4. Crée les professions de santé
    5. Crée les rôles système
    6. Crée le pays par défaut (France)
    7. Crée le tenant par défaut (NOUVEAU v4.1)
    8. Crée l'abonnement par défaut (NOUVEAU v4.1)
    9. Crée l'entité par défaut (SSIAD exemple)
    10. Crée le compte administrateur

    Args:
        drop_existing: Si True, supprime les tables existantes avant création
        admin_email: Email du compte admin
        admin_rpps: RPPS du compte admin

    Returns:
        True si initialisation réussie, False sinon

    Example:
        >>> from app.database.init_db import init_database
        >>> init_database()
        True
    """
    logger.info("=" * 60)
    logger.info("🚀 INITIALISATION DE LA BASE DE DONNÉES CARELINK v4.1")
    logger.info("   (Architecture Multi-Tenant)")
    logger.info("=" * 60)

    # 1. Vérifier la connexion
    logger.info("\n📡 Vérification de la connexion PostgreSQL...")
    if not check_database_connection():
        logger.error("❌ Impossible de se connecter à PostgreSQL")
        logger.error("   Vérifiez que PostgreSQL est démarré et que DATABASE_URL est correct")
        return False
    logger.info("✅ Connexion PostgreSQL OK\n")

    # 2. Suppression des tables (si demandé)
    if drop_existing:
        logger.warning("⚠️ Mode DROP_EXISTING activé")
        if not drop_all_tables():
            return False
        logger.info("")

    # 3. Création des tables
    if not create_all_tables():
        return False
    logger.info("")

    # 4-10. Initialisation des données avec une session
    try:
        with db_session() as db:
            # 4. Professions
            professions = init_professions(db)
            if not professions:
                logger.error("❌ Échec de l'initialisation des professions")
                return False
            logger.info("")

            # 5. Rôles
            roles = init_roles(db)
            if not roles:
                logger.error("❌ Échec de l'initialisation des rôles")
                return False
            logger.info("")

            # 6. Pays
            country = init_default_country(db)
            logger.info("")

            # 7. Tenant (NOUVEAU v4.1)
            tenant = init_default_tenant(db, country)
            logger.info("")

            # 8. Abonnement (NOUVEAU v4.1)
            subscription = init_default_subscription(db, tenant)
            logger.info("")

            # 9. Entité
            entity = init_default_entity(db, country, tenant)
            logger.info("")

            # 10. Admin
            init_default_admin(
                db=db,
                entity=entity,
                tenant=tenant,
                email=admin_email,
                rpps=admin_rpps
            )

            # Commit final
            db.commit()

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation des données : {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ INITIALISATION TERMINÉE AVEC SUCCÈS")
    logger.info("=" * 60)
    logger.info(f"""
📋 Résumé :
   - Tables créées : {len(Base.metadata.tables)}
   - Professions : {len(INITIAL_PROFESSIONS)}
   - Rôles système : {len(INITIAL_ROLES)}
   - Pays : France
   - Tenant : CareLink Demo (CARELINK-DEFAULT)
   - Abonnement : Plan L (Demo)
   - Entité : SSIAD CareLink Paris
   - Admin : {admin_email}

📊 Tables créées (24 tables) :
   
   🏛️ MODULE TENANT (nouveau v4.1)
   - tenants            : Clients/locataires de la plateforme
   - subscriptions      : Abonnements et facturation
   - subscription_usage : Suivi de consommation mensuelle
   
   🌍 MODULE REFERENCE
   - countries          : Pays
   
   🏢 MODULE ORGANIZATION
   - entities           : Entités de soins (SSIAD, EHPAD...)
   
   👥 MODULE USER
   - professions        : Professions réglementées
   - roles              : Rôles fonctionnels
   - users              : Utilisateurs/Professionnels
   - user_roles         : Association User ↔ Role
   - user_entities      : Association User ↔ Entity
   - user_availabilities: Disponibilités des professionnels
   
   🏥 MODULE PATIENT
   - patients           : Dossiers patients (chiffrés)
   - patient_access     : Traçabilité RGPD
   - patient_evaluations: Évaluations (JSON Schema / AGGIR)
   - patient_thresholds : Seuils de constantes
   - patient_vitals     : Mesures de constantes
   - patient_devices    : Devices connectés
   - patient_documents  : Documents générés (PPA, PPCS...)
   
   📚 MODULE CATALOG
   - service_templates  : Catalogue national des prestations
   - entity_services    : Services activés par entité
   
   📋 MODULE CAREPLAN
   - care_plans         : Plans d'aide patients
   - care_plan_services : Services des plans d'aide
   
   📅 MODULE COORDINATION
   - coordination_entries    : Carnet de coordination
   - scheduled_interventions : Planning des interventions

🚀 Prochaine étape :
   uvicorn app.main:app --reload
""")

    return True


# =============================================================================
# 9. POINT D'ENTRÉE CLI
# =============================================================================

def main():
    """
    Point d'entrée pour exécution en ligne de commande.

    Usage:
        python -m app.database.init_db
        python -m app.database.init_db --drop
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialise la base de données CareLink v4.1 (Multi-tenant)"
    )
    parser.add_argument(
        '--drop',
        action='store_true',
        help="Supprime les tables existantes avant création (ATTENTION !)"
    )
    parser.add_argument(
        '--admin-email',
        default="admin@carelink.fr",
        help="Email du compte administrateur (défaut: admin@carelink.fr)"
    )
    parser.add_argument(
        '--admin-rpps',
        default="00000000001",
        help="RPPS du compte administrateur (défaut: 00000000001)"
    )

    args = parser.parse_args()

    # Confirmation si --drop
    if args.drop:
        print("\n⚠️  ATTENTION : Vous allez SUPPRIMER toutes les tables existantes !")
        print("   Toutes les données seront perdues.\n")
        response = input("Êtes-vous sûr ? (oui/non) : ")
        if response.lower() != 'oui':
            print("Annulé.")
            sys.exit(0)

    # Lancer l'initialisation
    success = init_database(
        drop_existing=args.drop,
        admin_email=args.admin_email,
        admin_rpps=args.admin_rpps
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()