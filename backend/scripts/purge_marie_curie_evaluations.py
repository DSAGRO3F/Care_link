#!/usr/bin/env python3
"""
Purge ciblée des données de validation/évaluation FICTIVES de Marie CURIE.

Cible : tenant_id = 364, patient_id = 7 (Marie CURIE — patient de test prefill).
Objectif : repartir d'un dossier vierge pour rejouer un cycle E2E propre du
portail valideur (création éval → soumission → relais médecin/département).

Périmètre (décision D-gamma, raffinée le 03/06/2026) :
  - TOUTES les évaluations du patient 7 (brouillon du 02/06 inclus)
  - TOUS les plans d'aide fictifs du patient 7
  - Les objets dépendants (VR, échanges, notifications, sessions, services)

Analyse FK (vérifiée sur les modèles ORM, confirmée au runtime par le préflight) :
  ON DELETE CASCADE (se défont seuls) :
    validation_requests.evaluation_id / .care_plan_id
    validation_exchanges.validation_request_id
    notifications.related_evaluation_id / .related_care_plan_id
                 / .related_validation_request_id
  ON DELETE SET NULL (ne bloquent jamais) :
    patient_evaluations.superseded_by_evaluation_id (self)
    care_plans.supersedes_plan_id (self)
    care_plans.source_evaluation_id / .gir_inherited_from_evaluation_id
  ON DELETE non vu dans les modèles -> on supprime ces enfants EXPLICITEMENT :
    evaluation_sessions.evaluation_id
    care_plan_services.care_plan_id

Sécurité d'exécution :
  - Tout se passe dans UNE transaction.
  - Mode par défaut = DRY-RUN : compte + préflight, puis ROLLBACK (zéro écriture).
  - Suppression réelle : --apply, avec confirmation interactive (ou --yes).
  - SET LOCAL app.is_super_admin='true' posé par convention maison (redondant
    sous odb_admin_1 qui est superuser bypassrls, mais requis sous le rôle
    restreint 'carelink').

Usage :
  python purge_marie_curie_evaluations.py            # dry-run (recommandé d'abord)
  python purge_marie_curie_evaluations.py --apply     # supprime (confirmation requise)
  python purge_marie_curie_evaluations.py --apply --yes  # supprime sans prompt

Variable d'environnement attendue : DATABASE_URL
  ex. postgresql://odb_admin_1@localhost:5432/carelink_db
"""

# Faux positif S608 (injection SQL) : tout le SQL dynamique de ce script interpole
# exclusivement des CONSTANTES internes (noms de tables + prédicats WHERE définis
# dans STEPS), jamais d'entrée utilisateur ; les seules valeurs (tenant_id / patient_id)
# passent en paramètres liés (:tenant / :patient). Aucun vecteur d'injection.
# ruff: noqa: S608

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# load_dotenv() après les imports : ce script n'importe AUCUN module applicatif
# (app.*), donc aucune dépendance d'environnement au moment de l'import. DATABASE_URL
# n'est lue qu'à l'appel de get_engine() ; load_dotenv() doit seulement précéder cet appel.
load_dotenv()


TENANT_ID = 364
PATIENT_ID = 7

# Tables enfants supprimées explicitement (couvre les ON DELETE non garantis).
# Ordre = enfants -> parents. Chaque entrée : (label, requête DELETE/COUNT).
# Les sous-requêtes sont réévaluées à l'exécution ; l'ordre garantit que les
# ensembles eval/plan/VR existent encore quand on en a besoin.
_EVAL_IDS = "SELECT id FROM patient_evaluations WHERE patient_id = :patient AND tenant_id = :tenant"
_PLAN_IDS = "SELECT id FROM care_plans WHERE patient_id = :patient AND tenant_id = :tenant"
_VR_PRED = (
    f"tenant_id = :tenant AND (evaluation_id IN ({_EVAL_IDS}) OR care_plan_id IN ({_PLAN_IDS}))"
)

# (label, prédicat WHERE) — l'ordre EST l'ordre de suppression.
STEPS: list[tuple[str, str, str]] = [
    (
        "validation_exchanges",
        f"validation_request_id IN (SELECT id FROM validation_requests WHERE {_VR_PRED})",
        "fil d'échange des VR",
    ),
    (
        "notifications",
        f"related_evaluation_id IN ({_EVAL_IDS}) "
        f"OR related_care_plan_id IN ({_PLAN_IDS}) "
        f"OR related_validation_request_id IN (SELECT id FROM validation_requests WHERE {_VR_PRED})",
        "notifications pointant vers les objets purgés",
    ),
    (
        "validation_requests",
        _VR_PRED,
        "demandes de validation (éval + plan)",
    ),
    (
        "evaluation_sessions",
        f"evaluation_id IN ({_EVAL_IDS})",
        "sessions de saisie des évaluations",
    ),
    (
        "care_plan_services",
        f"care_plan_id IN ({_PLAN_IDS})",
        "services des plans d'aide",
    ),
    (
        "care_plans",
        "patient_id = :patient AND tenant_id = :tenant",
        "plans d'aide fictifs",
    ),
    (
        "patient_evaluations",
        "patient_id = :patient AND tenant_id = :tenant",
        "évaluations (brouillon 02/06 inclus)",
    ),
]

_CONFDELTYPE = {
    "a": "NO ACTION",
    "r": "RESTRICT",
    "c": "CASCADE",
    "n": "SET NULL",
    "d": "SET DEFAULT",
}

# Tables qu'on supprime explicitement -> une FK entrante vers nos parents qui
# pointe vers l'une d'elles est "couverte". Toute autre table avec NO ACTION /
# RESTRICT déclenche un avertissement (FK oubliée).
_HANDLED_CHILDREN = {label for label, _, _ in STEPS}


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("ERREUR : variable d'environnement DATABASE_URL absente.")
    return create_engine(url, future=True)


def preflight(conn) -> None:
    """Affiche les FK entrantes réelles vers les 3 tables parentes + alerte si
    une FX bloquante (NO ACTION/RESTRICT) pointe vers une table non gérée."""
    print("\n--- PRÉFLIGHT : FK entrantes (source de vérité = pg_constraint) ---")
    rows = conn.execute(
        text(
            """
            SELECT conrelid::regclass::text AS child_table,
                   a.attname               AS child_column,
                   confrelid::regclass::text AS parent_table,
                   c.confdeltype           AS on_delete
            FROM pg_constraint c
            JOIN pg_attribute a
              ON a.attnum = ANY (c.conkey) AND a.attrelid = c.conrelid
            WHERE c.contype = 'f'
              AND c.confrelid IN (
                  'patient_evaluations'::regclass,
                  'care_plans'::regclass,
                  'validation_requests'::regclass
              )
            ORDER BY parent_table, child_table, child_column
            """
        )
    ).fetchall()

    warnings: list[str] = []
    for child_table, child_col, parent_table, deltype in rows:
        on_delete = _CONFDELTYPE.get(deltype, deltype)
        # nom non-qualifié pour comparaison avec _HANDLED_CHILDREN
        child_simple = child_table.split(".")[-1]
        print(f"  {parent_table:<22} <- {child_table}.{child_col:<28} [{on_delete}]")
        if on_delete in ("NO ACTION", "RESTRICT") and child_simple not in _HANDLED_CHILDREN:
            warnings.append(
                f"FK bloquante non gérée : {child_table}.{child_col} "
                f"({on_delete}) -> {parent_table}"
            )

    # Tables enfants explicites : existent-elles ?
    for tbl in ("evaluation_sessions", "care_plan_services"):
        exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{tbl}"}).scalar()
        if exists is None:
            warnings.append(f"Table attendue introuvable : {tbl}")

    if warnings:
        print("\n  ⚠️  AVERTISSEMENTS :")
        for w in warnings:
            print(f"     - {w}")
    else:
        print("\n  ✓ Toutes les FK entrantes sont en CASCADE/SET NULL ou gérées explicitement.")


def count_targets(conn) -> list[tuple[str, int]]:
    """Compte les lignes qui seront supprimées, dans l'ordre des étapes."""
    params = {"tenant": TENANT_ID, "patient": PATIENT_ID}
    counts: list[tuple[str, int]] = []
    for table, where, _desc in STEPS:
        n = conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), params).scalar_one()
        counts.append((table, int(n)))
    return counts


def print_counts(title: str, counts: list[tuple[str, int]]) -> int:
    print(f"\n--- {title} (tenant {TENANT_ID}, patient {PATIENT_ID}) ---")
    total = 0
    desc_by_table = {t: d for t, _, d in STEPS}
    for table, n in counts:
        total += n
        print(f"  {n:>6}  {table:<22} {desc_by_table.get(table, '')}")
    print(f"  {'-' * 6}")
    print(f"  {total:>6}  TOTAL lignes ciblées")
    return total


def do_deletes(conn) -> list[tuple[str, int]]:
    params = {"tenant": TENANT_ID, "patient": PATIENT_ID}
    result: list[tuple[str, int]] = []
    for table, where, _desc in STEPS:
        res = conn.execute(text(f"DELETE FROM {table} WHERE {where}"), params)
        result.append((table, res.rowcount or 0))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Exécute réellement la suppression (sinon : dry-run + rollback).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Saute la confirmation interactive (à utiliser avec --apply).",
    )
    args = parser.parse_args()

    engine = get_engine()
    with engine.connect() as conn:
        trans = conn.begin()
        # Convention maison : contexte super-admin (redondant sous odb_admin_1).
        conn.execute(text("SET LOCAL app.is_super_admin = 'true'"))
        conn.execute(text(f"SET LOCAL app.current_tenant_id = '{TENANT_ID}'"))

        preflight(conn)
        counts = count_targets(conn)
        total = print_counts("INVENTAIRE AVANT SUPPRESSION", counts)

        if total == 0:
            print("\n✓ Rien à purger — le dossier est déjà vierge.")
            trans.rollback()
            return

        if not args.apply:
            print(
                "\n[DRY-RUN] Aucune écriture effectuée (rollback). "
                "Relancez avec --apply pour supprimer."
            )
            trans.rollback()
            return

        if not args.yes:
            print(
                f"\n⚠️  Suppression IRRÉVERSIBLE de {total} lignes "
                f"(patient {PATIENT_ID}, tenant {TENANT_ID})."
            )
            answer = input("    Tapez exactement PURGE pour confirmer : ").strip()
            if answer != "PURGE":
                print("    Annulé (rollback).")
                trans.rollback()
                return

        deleted = do_deletes(conn)
        print_counts("LIGNES SUPPRIMÉES", deleted)

        # Vérification post-suppression dans la même transaction.
        residual = count_targets(conn)
        residual_total = sum(n for _, n in residual)
        if residual_total != 0:
            print(f"\n✗ ANOMALIE : {residual_total} lignes résiduelles — ROLLBACK.")
            print_counts("RÉSIDU", residual)
            trans.rollback()
            sys.exit(1)

        trans.commit()
        print("\n✓ Purge committée. Dossier Marie CURIE vierge pour l'E2E.")


if __name__ == "__main__":
    main()
