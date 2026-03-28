#!/usr/bin/env python3
"""
Script de bootstrap - Crée le premier tenant et administrateur CareLink.

À exécuter UNE SEULE FOIS lors du déploiement initial.

Usage:
    cd backend
    python scripts/seed_first_admin.py

    # Ou avec des paramètres personnalisés :
    python scripts/seed_first_admin.py \
        --email admin@monssiad.fr \
        --password "MonMotDePasse123!" \
        --first-name Jean \
        --last-name Dupont \
        --tenant-name "SSIAD de Paris" \
        --tenant-code "SSIAD-PARIS-01"
"""

import argparse
import secrets
import sys
from pathlib import Path


# Ajouter le répertoire backend au path pour les imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from app.core.security.hashing import hash_password
from app.database.session import SessionLocal
from app.models.enums import TenantStatus, TenantType
from app.models.tenants.tenant import Tenant
from app.models.user.user import User


def get_or_create_tenant(
    db: Session, code: str, name: str, tenant_type: TenantType, contact_email: str
) -> Tenant:
    """
    Récupère ou crée le premier tenant.

    Returns:
        Tenant: Le tenant existant ou nouvellement créé
    """
    # Vérifier si un tenant existe déjà
    existing = db.query(Tenant).first()

    if existing:
        print("✅ Tenant existant trouvé :")
        print(f"   - ID: {existing.id}")
        print(f"   - Code: {existing.code}")
        print(f"   - Nom: {existing.name}")
        return existing

    # Générer une clé de chiffrement placeholder pour le dev
    # En production, cette clé serait gérée par un vault (AWS KMS, HashiCorp, etc.)
    encryption_key_id = f"dev-key-{secrets.token_hex(8)}"

    # Créer le premier tenant
    tenant = Tenant(
        code=code,
        name=name,
        tenant_type=tenant_type,
        status=TenantStatus.ACTIVE,
        contact_email=contact_email,
        encryption_key_id=encryption_key_id,
        timezone="Europe/Paris",
        locale="fr_FR",
        max_storage_gb=50,
        settings={},
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    print("✅ Tenant créé :")
    print(f"   - ID: {tenant.id}")
    print(f"   - Code: {tenant.code}")
    print(f"   - Nom: {tenant.name}")
    print(f"   - Type: {tenant.tenant_type.value}")
    print(f"   - Encryption Key ID: {encryption_key_id}")

    return tenant


def create_first_admin(
    db: Session, email: str, password: str, first_name: str, last_name: str, tenant_id: int
) -> User | None:
    """
    Crée le premier administrateur.

    Returns:
        User | None: L'utilisateur créé ou None si un admin existe déjà
    """
    # Vérifier si un admin existe déjà
    existing_admin = db.query(User).filter(User.is_admin == True)  # noqa: E712
    if existing_admin:
        print(f"⚠️  Un administrateur existe déjà : {existing_admin.email}")
        return None

    # Vérifier si l'email est déjà utilisé
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        print(f"⚠️  L'email {email} est déjà utilisé")
        return None

    # Créer l'admin
    admin = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        password_hash=hash_password(password),
        is_admin=True,
        is_active=True,
        tenant_id=tenant_id,
        rpps=None,  # Pas de RPPS pour un admin non-soignant
        profession_id=None,  # Pas de profession réglementée
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    print("✅ Administrateur créé :")
    print(f"   - ID: {admin.id}")
    print(f"   - Email: {admin.email}")
    print(f"   - Nom: {admin.full_name}")
    print(f"   - Tenant ID: {admin.tenant_id}")
    print(f"   - is_admin: {admin.is_admin}")

    return admin


def main():
    parser = argparse.ArgumentParser(
        description="Crée le premier tenant et administrateur CareLink"
    )

    # Paramètres Admin
    parser.add_argument(
        "--email",
        default="olivier.debeyssac@gmail.com",
        help="Email de l'administrateur (défaut: olivier.debeyssac@gmail.com)",
    )
    parser.add_argument("--password", default="Fer458it", help="Mot de passe (défaut: Fer458it)")
    parser.add_argument("--first-name", default="Olivier", help="Prénom (défaut: Olivier)")
    parser.add_argument("--last-name", default="de Beyssac", help="Nom (défaut: de Beyssac)")

    # Paramètres Tenant
    parser.add_argument(
        "--tenant-code",
        default="CARELINK-DEMO-01",
        help="Code unique du tenant (défaut: CARELINK-DEMO-01)",
    )
    parser.add_argument(
        "--tenant-name", default="CareLink Demo", help="Nom du tenant (défaut: CareLink Demo)"
    )
    parser.add_argument(
        "--tenant-type",
        default="SSIAD",
        choices=["GCSMS", "SSIAD", "SAAD", "SPASAD", "EHPAD", "DAC", "CPTS", "OTHER"],
        help="Type de tenant (défaut: SSIAD)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🏥 CareLink - Bootstrap du premier tenant et administrateur")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Étape 1: Tenant
        print("\n📦 Étape 1/2 : Vérification/création du tenant...")
        tenant = get_or_create_tenant(
            db=db,
            code=args.tenant_code,
            name=args.tenant_name,
            tenant_type=TenantType(args.tenant_type),
            contact_email=args.email,  # Même email que l'admin par défaut
        )

        # Étape 2: Admin
        print("\n👤 Étape 2/2 : Création de l'administrateur...")
        admin = create_first_admin(
            db=db,
            email=args.email,
            password=args.password,
            first_name=args.first_name,
            last_name=args.last_name,
            tenant_id=tenant.id,
        )

        if admin:
            print("\n" + "=" * 60)
            print("🎉 Bootstrap terminé avec succès !")
            print("=" * 60)
            print("\n📧 Connectez-vous avec :")
            print("   URL: http://localhost:3000/login")
            print(f"   Email: {args.email}")
            print(f"   Mot de passe: {args.password}")
            print("\n⚠️  IMPORTANT: Changez ce mot de passe après la première connexion !")
        else:
            print("\n⚠️  Admin non créé (existe peut-être déjà)")
            print("    Vous pouvez utiliser l'admin existant pour vous connecter.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
