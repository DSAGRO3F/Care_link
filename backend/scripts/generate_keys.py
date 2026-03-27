"""
Génère les clés cryptographiques nécessaires pour l'application.

Usage:
    python scripts/generate_keys.py

Génère:
    1. Paire de clés ES256 (ECDSA P-256) pour JWT
    2. Clé AES-256 pour chiffrement des données patients
"""

import base64
import os
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_es256_keypair(output_dir: Path):
    """Génère une paire de clés ECDSA P-256 (ES256)."""
    print("🔐 Génération de la paire de clés ES256 (ECDSA P-256)...")

    # Générer la clé privée
    private_key = ec.generate_private_key(
        ec.SECP256R1(),  # Courbe P-256
        default_backend(),
    )

    # Sauvegarder la clé privée au format PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    private_key_path = output_dir / "jwt_private_key.pem"
    private_key_path.write_bytes(private_pem)
    print(f"✅ Clé privée JWT: {private_key_path}")

    # Générer et sauvegarder la clé publique
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    public_key_path = output_dir / "jwt_public_key.pem"
    public_key_path.write_bytes(public_pem)
    print(f"✅ Clé publique JWT: {public_key_path}")


def generate_aes256_key():
    """Génère une clé AES-256 pour le chiffrement des données."""
    print("\n🔐 Génération de la clé AES-256 pour chiffrement des données...")

    # Générer 32 bytes aléatoires (256 bits)
    key = os.urandom(32)

    # Encoder en base64 pour faciliter le stockage dans .env
    key_b64 = base64.b64encode(key).decode("utf-8")

    print("✅ Clé AES-256 (à ajouter dans .env):")
    print(f"\nENCRYPTION_KEY={key_b64}\n")

    return key_b64


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("Génération des clés cryptographiques pour CareLink")
    print("=" * 60)

    # Créer le répertoire keys/ s'il n'existe pas
    keys_dir = Path("keys")
    keys_dir.mkdir(exist_ok=True)

    # Générer les clés ES256 pour JWT
    generate_es256_keypair(keys_dir)

    # Générer la clé AES-256
    aes_key = generate_aes256_key()

    print("=" * 60)
    print("⚠️  IMPORTANT - Sécurité")
    print("=" * 60)
    print("1. Ajoutez la clé AES-256 dans votre fichier .env")
    print("2. NE COMMITEZ JAMAIS le dossier keys/ dans git")
    print("3. Ajoutez 'keys/' dans votre .gitignore")
    print("4. En production, utilisez un gestionnaire de secrets")
    print("   (AWS Secrets Manager, Azure Key Vault, etc.)")
    print("5. Les clés doivent être différentes par environnement")
    print("=" * 60)

    # Créer/mettre à jour .gitignore
    gitignore_path = Path(".gitignore")
    gitignore_content = gitignore_path.read_text() if gitignore_path.exists() else ""

    if "keys/" not in gitignore_content:
        with gitignore_path.open("a") as f:
            f.write("\n# Clés cryptographiques (ne JAMAIS commiter)\nkeys/\n")
        print("✅ Ajouté 'keys/' au .gitignore")


if __name__ == "__main__":
    main()
