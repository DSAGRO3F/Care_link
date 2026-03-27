"""
Calculateurs de tests cliniques gériatriques.

Chaque calculateur reçoit les données brutes d'un bloc santé (questionReponse[])
et retourne une liste d'entrées test[] au format :
    [{"nom": str, "resultat": str}, ...]

Architecture identique à app/services/aggir/calculator.py :
- Fonctions pures, sans accès DB
- Appelées depuis le endpoint PATCH /evaluations/{id} à la soumission
- Les résultats remplacent le contenu de sante.blocs[x].test[]

Référentiel :
- GAI-SF : Pachana et al. 2007
- Mini-GDS : Clément & Nassif, L'Encéphale 1997
- ICOPE : OMS 2019
- Mini-cog : Borson 2000
- MNA-SF : Rubenstein 2001, Kaiser 2009
- Norton : Norton 1962 (adaptation AGGIR)
- SPPB : Guralnik et al. 1994
- IMC : Seuils gériatriques HAS (≥ 65 ans)
"""

from datetime import date


# ─── Helpers ────────────────────────────────────────────────────────────────


def _today_str() -> str:
    """Date du jour au format DD/MM/YYYY (format JSON CareLink)."""
    return date.today().strftime("%d/%m/%Y")


def _get_test_date(question_reponse: list[dict], date_question: str) -> str:
    """
    Lit la date d'administration du test depuis questionReponse[].
    Le professionnel saisit cette date dans le wizard (champs split JJ/MM/AAAA
    pré-remplis mois+année courants, sérialisés en DD/MM/YYYY).
    Fallback sur _today_str() si le champ est absent ou vide.
    """
    val = _get_response(question_reponse, date_question)
    if val and val.strip():
        return val.strip()
    return _today_str()


def _get_response(question_reponse: list[dict], question_substr: str) -> str | None:
    """
    Retrouve la réponse d'une question par sous-chaîne du libellé.
    Retourne None si non trouvée ou vide.
    """
    for qr in question_reponse:
        if question_substr.lower() in qr.get("question", "").lower():
            val = qr.get("reponse", "").strip()
            return val if val else None
    return None


def _get_all_responses(question_reponse: list[dict], question_substr: str) -> list[str]:
    """
    Retrouve toutes les réponses d'une question (pour les questions dupliquées).
    """
    results = []
    for qr in question_reponse:
        if question_substr.lower() in qr.get("question", "").lower():
            val = qr.get("reponse", "").strip()
            if val:
                results.append(val)
    return results


def _is_oui(val: str | None) -> bool:
    """Teste si la réponse est OUI (insensible à la casse)."""
    return val is not None and val.strip().upper() == "OUI"


def _is_non(val: str | None) -> bool:
    """Teste si la réponse est NON (insensible à la casse)."""
    return val is not None and val.strip().upper() == "NON"


def _safe_float(val: str | None) -> float | None:
    """Conversion sécurisée vers float."""
    if val is None:
        return None
    try:
        # Gère les formats "12:62" (mm:ss) → secondes décimales
        if ":" in val:
            parts = val.split(":")
            return float(parts[0]) + float(parts[1]) / 100
        return float(val.replace(",", "."))
    except (ValueError, IndexError):
        return None


# ─── GAI-SF (Geriatric Anxiety Inventory - Short Form) ─────────────────────

# Questions officielles GAI-SF (5 items, OUI/NON)
_GAI_SF_QUESTIONS = [
    "inquiétude",  # "Le patient vit-il beaucoup dans l'inquiétude ?"
    "un rien le",  # "Un rien le dérange ?"
    "nature inquiète",  # "Le patient se considère-t-il comme étant de nature inquiète ?"
    "souvent nerveux",  # "Le patient se sent-il souvent nerveux ?"
    "propres pensées",  # "Lui arrive-t-il souvent que ses propres pensées suscitent..."
]


def compute_gai_sf(
    question_reponse: list[dict],
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    GAI-SF : 5 items OUI/NON, score /5, seuil ≥ 3 = anxiété significative.
    Pachana et al. 2007.
    """
    score = 0
    answered = 0

    for q_substr in _GAI_SF_QUESTIONS:
        resp = _get_response(question_reponse, q_substr)
        if resp is not None:
            answered += 1
            if _is_oui(resp):
                score += 1

    if answered == 0:
        return []

    test_date = _get_test_date(question_reponse, "Date du test GAI-SF")

    if score >= 3:
        interpretation = (
            f"{patient_display_name} présente des signes d'anxiété significative. "
            "Une attention particulière aux symptômes liés à l'anxiété et au stress "
            "est recommandée afin de proposer un suivi adapté"
        )
        resultat = "Le test fait état d'une anxiété"
    else:
        interpretation = (
            f"{patient_display_name} ne présente pas de signes d'anxiété significative "
            "selon le test GAI-SF. Aucune action spécifique n'est requise à ce stade"
        )
        resultat = "Le test ne fait pas état d'une anxiété significative"

    return [
        {"nom": "TEST GAI (Geriatric Anxiety Inventory)", "resultat": resultat},
        {"nom": "Interprétation du test GAI-SF", "resultat": interpretation},
        {"nom": "TEST GAI (Geriatric Anxiety Inventory)", "resultat": test_date},
    ]


# ─── Mini-GDS (Gériatric Depressive Syndrome) ──────────────────────────────

# Questions officielles Mini-GDS (4 items)
# Index = position dans questionReponse[] du bloc Dépression
# Q1 "découragé et triste" → OUI = 1 point
# Q2 "heureux la plupart du temps" → NON = 1 point (question inversée)
# Q3 "vie est vide" → OUI = 1 point
# Q4 "situation est désespérée" → OUI = 1 point

_MINI_GDS_ITEMS = [
    {"substr": "découragé et triste", "invert": False},
    {"substr": "heureux la plupart", "invert": True},
    {"substr": "vie est vide", "invert": False},
    {"substr": "situation est désespérée", "invert": False},
]


def compute_mini_gds(
    question_reponse: list[dict],
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    Mini-GDS : 4 items, score /4, seuil ≥ 1 = forte probabilité de dépression.
    Clément & Nassif, L'Encéphale 1997.

    La Q5 ("Cela l'empêche-t-il de s'engager...") est conservée dans
    questionReponse[] pour sa valeur clinique mais n'entre PAS dans le score.
    """
    score = 0
    answered = 0
    details: list[str] = []

    for item in _MINI_GDS_ITEMS:
        resp = _get_response(question_reponse, item["substr"])
        if resp is None:
            continue

        answered += 1
        point = 0

        if item["invert"]:
            # Question inversée : NON = 1 point
            if _is_non(resp):
                point = 1
                details.append(
                    f"{patient_display_name} indique ne pas être heureux(se) la plupart du temps."
                )
        else:
            if _is_oui(resp):
                point = 1

        score += point

    if answered == 0:
        return []

    test_date = _get_test_date(question_reponse, "Date du test Mini-GDS")

    # --- ICOPE Dépression (basé sur Q3 vie vide + Q4 désespérée) ---
    q_vide = _get_response(question_reponse, "vie est vide")
    q_desespere = _get_response(question_reponse, "situation est désespérée")

    icope_alerte = _is_oui(q_vide) or _is_oui(q_desespere)
    if icope_alerte:
        icope_resultat = (
            "Les signes de dépression du programme ICOPE sont positifs, "
            "une évaluation complète est recommandée"
        )
    else:
        icope_resultat = "Pas de signe de dépression détecté par le dépistage ICOPE"

    # --- Mini-GDS ---
    detail_str = " ".join(details) if details else ""
    mini_gds_resultat = f"{patient_display_name} a un test mini-GDS de {score}/4."
    if detail_str:
        mini_gds_resultat += f" {detail_str}"

    return [
        {"nom": "Dépistage des symptômes dépressifs ICOPE", "resultat": icope_resultat},
        {"nom": "Dépistage des symptômes dépressifs ICOPE", "resultat": test_date},
        {"nom": "Mini GDS (Gériatric Depressive Syndrome)", "resultat": mini_gds_resultat},
        {"nom": "Mini GDS (Gériatric Depressive Syndrome)", "resultat": test_date},
    ]


# ─── ICOPE Cognition + Mini-cog ────────────────────────────────────────────


def compute_cognition(
    question_reponse: list[dict],
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    Deux tests combinés dans le bloc Cognition :

    1. ICOPE step 1 Cognition (OMS 2019) :
       - 2 questions screening (mémoire/orientation + aggravation 4 mois)
       - Encodage 3 mots (rappel immédiat)
       - Test horloge 11h10
       - Rappel différé 3 mots
       - Alerte si rappel différé < 3 mots OU horloge non réussie

    2. Mini-cog (Borson 2000) :
       - Score /5 = rappel différé (0-3 pts) + horloge (0 ou 2 pts)
       - Seuil ≤ 2 = troubles significatifs
    """
    test_date = _get_test_date(question_reponse, "Date des tests cognitifs")
    results: list[dict] = []

    # --- Données brutes ---
    horloge_resp = _get_response(question_reponse, "horloge")
    rappel_resp = _get_response(question_reponse, "redonner les 3 mots")

    # --- Score horloge (0 ou 2 points Mini-cog) ---
    horloge_ok = False
    if horloge_resp is not None:
        horloge_ok = "réussi" in horloge_resp.lower() and "non" not in horloge_resp.lower()
    horloge_score = 2 if horloge_ok else 0

    # --- Score rappel différé (0 à 3 points Mini-cog) ---
    rappel_score = 0
    if rappel_resp is not None:
        # Compter les mots rappelés parmi la liste
        # Le rappel peut être "Village" ou "DRAPEAU, FLEUR" etc.
        mots = [m.strip() for m in rappel_resp.replace(",", " ").split() if m.strip()]
        rappel_score = min(len(mots), 3)

    # --- Mini-cog total ---
    mini_cog_score = horloge_score + rappel_score  # /5

    if mini_cog_score <= 2:
        mini_cog_interp = (
            f"{patient_display_name} a eu un test mini-cog de {mini_cog_score}/5. "
            "La mémoire et les capacités de réflexion semblent significativement "
            "perturbées et nécessitent d'être complétées par une exploration spécialisée."
        )
    elif mini_cog_score <= 3:
        mini_cog_interp = (
            f"{patient_display_name} a eu un test mini-cog de {mini_cog_score}/5. "
            "Des difficultés cognitives modérées sont détectées. "
            "Un suivi et une évaluation complémentaire sont recommandés."
        )
    else:
        mini_cog_interp = (
            f"{patient_display_name} a eu un test mini-cog de {mini_cog_score}/5. "
            "Les capacités cognitives ne présentent pas de perturbation significative."
        )

    # --- ICOPE Cognition ---
    # Alerte si rappel < 3 OU horloge non réussie
    icope_alerte = (rappel_score < 3) or (not horloge_ok)

    if icope_alerte:
        icope_resultat = "Les tests de mémorisation du programme ICOPE sont perturbés"
        icope_reco = " une évaluation complète de ce domaine est recommandée"
    else:
        icope_resultat = (
            "Les tests de mémorisation du programme ICOPE ne montrent pas "
            "de perturbation significative"
        )
        icope_reco = " pas d'action spécifique requise"

    results.extend(
        [
            {"nom": "Dépistage cognitif ICOPE", "resultat": test_date},
            {"nom": "Dépistage cognitif ICOPE", "resultat": icope_resultat},
            {"nom": "Dépistage cognitif ICOPE", "resultat": icope_reco},
            {"nom": "Mini-cog", "resultat": mini_cog_interp},
        ]
    )

    return results


# ─── IMC (Indice de Masse Corporelle) ──────────────────────────────────────


def compute_imc(
    question_reponse: list[dict],
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    IMC = poids (kg) / taille (m)²
    Seuils gériatriques HAS (≥ 65 ans) :
    - < 21 : Risque de dénutrition
    - 21–27 : Normal
    - > 27 : Surpoids / Obésité
    """
    taille_str = _get_response(question_reponse, "taille (en cm)")
    poids_str = _get_response(question_reponse, "poids (en kg)")

    taille = _safe_float(taille_str)
    poids = _safe_float(poids_str)

    if taille is None or poids is None or taille <= 0:
        return []

    taille_m = taille / 100
    imc = poids / (taille_m**2)
    imc_round = round(imc, 1)

    test_date = _get_test_date(question_reponse, "Date des tests nutritionnels")

    # Seuils gériatriques HAS
    if imc < 21:
        interpretation = f"{patient_display_name} est en situation de risque de dénutrition"
    elif imc <= 27:
        interpretation = f"{patient_display_name} a un IMC normal"
    else:
        interpretation = f"{patient_display_name} est en Surpoids"

    return [
        {"nom": "IMC", "resultat": str(imc_round)},
        {"nom": "Interprétation IMC", "resultat": interpretation},
        {"nom": "Interprétation IMC", "resultat": test_date},
    ]


# ─── ICOPE Nutrition ────────────────────────────────────────────────────────


def compute_icope_nutrition(
    question_reponse: list[dict],
) -> list[dict]:
    """
    ICOPE step 1 Nutrition (OMS 2019) :
    - Baisse des apports alimentaires (3 mois)
    - Perte de poids (3 mois)
    Alerte si l'un des deux est positif.
    """
    baisse = _get_response(question_reponse, "baisse des prises alimentaires")
    perte = _get_response(question_reponse, "perte récente de poids")

    if baisse is None and perte is None:
        return []

    test_date = _get_test_date(question_reponse, "Date des tests nutritionnels")
    alerts: list[str] = []

    if baisse and baisse.upper() != "NON" and baisse.lower() != "pas de baisse":
        alerts.append(baisse)
    if perte and perte.upper() != "NON" and perte.lower() != "ne sait pas":
        alerts.append(perte)

    perte_display = perte if perte else "Non renseigné"
    baisse_display = baisse if baisse else "Non renseigné"

    if alerts:
        resultat = (
            f"{baisse_display} - {perte_display} | ICOPE NUTRITION légèrement perturbé à surveiller"
        )
    else:
        resultat = f"{baisse_display} - {perte_display} | ICOPE NUTRITION normal"

    return [
        {"nom": "ICOPE NUTRITION", "resultat": resultat},
        {"nom": "ICOPE NUTRITION", "resultat": test_date},
    ]


# ─── MNA-SF (Mini Nutritional Assessment - Short Form) ─────────────────────


def compute_mna_sf(
    question_reponse: list[dict],
    aggir_variables: list[dict],
    depression_score: int | None = None,
    cognition_mini_cog_score: int | None = None,
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    MNA-SF : 6 items, score /14, seuils :
    - ≥ 12 : État nutritionnel normal
    - 8–11 : Risque de malnutrition
    - ≤ 7 : État de dénutrition avérée

    Items :
    A. Baisse des apports alimentaires (0-2 pts)
    B. Perte de poids (0-3 pts)
    C. Mobilité — calculé depuis AGGIR (Transferts + Déplacements)
    D. Maladie aiguë / stress psychologique (0-2 pts)
    E. Problèmes neuropsychologiques — calculé depuis blocs Dépression + Cognition
    F. IMC (0-3 pts) — calculé depuis Taille + Poids du même bloc
    """

    # --- Item A : Baisse des apports (0-2) ---
    baisse = _get_response(question_reponse, "baisse des prises alimentaires")
    if baisse is None:
        score_a = 0
    elif "sévère" in baisse.lower() or "forte" in baisse.lower():
        score_a = 0  # Sévère diminution
    elif "légère" in baisse.lower() or "modérée" in baisse.lower():
        score_a = 1  # Légère diminution
    elif baisse.upper() == "NON" or "pas de" in baisse.lower():
        score_a = 2  # Pas de diminution
    else:
        score_a = 1  # Par défaut si texte ambigu → légère

    # --- Item B : Perte de poids (0-3) ---
    perte = _get_response(question_reponse, "perte récente de poids")
    if perte is None:
        score_b = 0
    elif "ne sait pas" in perte.lower():
        score_b = 1  # Ne sait pas
    elif perte.upper() == "NON" or "pas de perte" in perte.lower():
        score_b = 3  # Pas de perte
    elif "1 à 3" in perte.lower() or "1 et 3" in perte.lower():
        score_b = 2  # Perte entre 1 et 3 kg
    else:
        score_b = 0  # Perte > 3 kg ou non précisé

    # --- Item C : Mobilité (0-2) — depuis AGGIR ---
    score_c = _compute_mna_mobilite(aggir_variables)

    # --- Item D : Maladie aiguë / stress psychologique (0-2) ---
    maladie = _get_response(question_reponse, "maladie aigüe")
    if maladie is None:
        # Essayer variante orthographique
        maladie = _get_response(question_reponse, "maladie aigue")
    score_d = 0 if _is_oui(maladie) else 2

    # --- Item E : Problèmes neuropsychologiques (0-2) — depuis blocs croisés ---
    score_e = _compute_mna_neuropsy(depression_score, cognition_mini_cog_score)

    # --- Item F : IMC (0-3) ---
    taille = _safe_float(_get_response(question_reponse, "taille (en cm)"))
    poids = _safe_float(_get_response(question_reponse, "poids (en kg)"))

    if taille and poids and taille > 0:
        imc = poids / ((taille / 100) ** 2)
        if imc < 19:
            score_f = 0
        elif imc < 21:
            score_f = 1
        elif imc < 23:
            score_f = 2
        else:
            score_f = 3
    else:
        score_f = 0

    # --- Total ---
    total = score_a + score_b + score_c + score_d + score_e + score_f
    test_date = _get_test_date(question_reponse, "Date des tests nutritionnels")

    if total >= 12:
        etat = "État nutritionnel normal"
        reco = " pas d'action spécifique requise"
    elif total >= 8:
        etat = "Risque de malnutrition"
        reco = " suivi nutritionnel recommandé"
    else:
        etat = "Etat de dénutrition avérée"
        reco = " suivi médical fortement recommandé"

    return [
        {"nom": "Test de dépistage du MNA", "resultat": etat},
        {"nom": "Test de dépistage du MNA", "resultat": reco},
        {"nom": "Test de dépistage du MNA", "resultat": test_date},
    ]


def _compute_mna_mobilite(aggir_variables: list[dict]) -> int:
    """
    Item C du MNA-SF : mobilité.
    Calculé depuis AGGIR (Transferts + Déplacements intérieurs).
    - 0 = alité/fauteuil (Transferts C OU Déplacements intérieurs C)
    - 1 = se lève mais ne sort pas (Transferts A/B ET Déplacements intérieurs A/B
           ET Déplacements extérieurs C)
    - 2 = sort du domicile (Déplacements extérieurs A/B)
    """
    transferts = _get_aggir_result(aggir_variables, "Transferts")
    dep_int = _get_aggir_result(aggir_variables, "Déplacements intérieurs")
    dep_ext = _get_aggir_result(aggir_variables, "Déplacements extérieurs")

    if transferts == "C" or dep_int == "C":
        return 0  # Alité ou fauteuil
    if dep_ext in ("A", "B"):
        return 2  # Sort du domicile
    return 1  # Se lève mais ne sort pas


def _compute_mna_neuropsy(
    depression_score: int | None,
    mini_cog_score: int | None,
) -> int:
    """
    Item E du MNA-SF : problèmes neuropsychologiques.
    Calculé depuis les résultats des blocs Dépression + Cognition.
    - 0 = démence ou dépression sévère (mini_cog ≤ 2 ET mini_gds ≥ 1)
    - 1 = démence légère (mini_cog ≤ 2 OU mini_gds ≥ 1)
    - 2 = pas de problème
    """
    has_depression = depression_score is not None and depression_score >= 1
    has_cognition = mini_cog_score is not None and mini_cog_score <= 2

    if has_depression and has_cognition:
        return 0
    if has_depression or has_cognition:
        return 1
    return 2


# ─── Norton (risque d'escarre) ──────────────────────────────────────────────


def compute_norton(
    aggir_variables: list[dict],
    nutrition_question_reponse: list[dict] | None = None,
    peau_question_reponse: list[dict] | None = None,
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    Échelle de Norton : 5 critères, score /20, seuil ≤ 14 = risque.
    100% calculé depuis les variables AGGIR + état nutritionnel.

    Critères (1-4 chacun) :
    1. Condition physique générale → depuis état nutritionnel (IMC/MNA)
    2. État mental → depuis Orientation + Cohérence AGGIR
    3. Activité → depuis Déplacements intérieurs + extérieurs AGGIR
    4. Mobilité → depuis Transferts AGGIR
    5. Incontinence → depuis Élimination AGGIR
    """
    test_date = _get_test_date(peau_question_reponse or [], "Date de l'évaluation Norton")

    # 1. Condition physique (1-4)
    score_physique = _norton_condition_physique(nutrition_question_reponse)

    # 2. État mental (1-4)
    orientation = _get_aggir_result(aggir_variables, "Orientation")
    coherence = _get_aggir_result(aggir_variables, "Cohérence")
    score_mental = _norton_from_two_vars(orientation, coherence)

    # 3. Activité (1-4)
    dep_int = _get_aggir_result(aggir_variables, "Déplacements intérieurs")
    dep_ext = _get_aggir_result(aggir_variables, "Déplacements extérieurs")
    score_activite = _norton_from_two_vars(dep_int, dep_ext)

    # 4. Mobilité (1-4)
    transferts = _get_aggir_result(aggir_variables, "Transferts")
    score_mobilite = _norton_from_single_var(transferts)

    # 5. Incontinence (1-4)
    elimination = _get_aggir_result(aggir_variables, "Élimination")
    score_incontinence = _norton_from_single_var(elimination)

    total = score_physique + score_mental + score_activite + score_mobilite + score_incontinence

    if total <= 10:
        interpretation = f"{patient_display_name} présente un risque élevé d'escarre"
    elif total <= 14:
        interpretation = f"{patient_display_name} présente un risque modéré d'escarre"
    else:
        interpretation = f"{patient_display_name} ne présente pas de risque d'escarre significatif"

    return [
        {
            "nom": "Evaluation du risque d'escarre selon l'échelle de Norton "
            "(Basé sur l'évaluation AGGIR)",
            "resultat": interpretation,
        },
        {
            "nom": "Evaluation du risque d'escarre selon l'échelle de Norton "
            "(Basé sur l'évaluation AGGIR)",
            "resultat": test_date,
        },
    ]


def _norton_condition_physique(
    nutrition_qr: list[dict] | None,
) -> int:
    """Score Norton condition physique depuis données nutrition."""
    if nutrition_qr is None:
        return 2  # Moyen par défaut

    taille = _safe_float(_get_response(nutrition_qr, "taille (en cm)"))
    poids = _safe_float(_get_response(nutrition_qr, "poids (en kg)"))

    if taille and poids and taille > 0:
        imc = poids / ((taille / 100) ** 2)
        if imc < 18:
            return 1  # Très mauvais
        if imc < 21:
            return 2  # Moyen
        if imc <= 27:
            return 3  # Bon
        return 3  # Surpoids = pas un risque d'escarre

    return 2  # Par défaut


def _norton_from_two_vars(
    var1: str | None,
    var2: str | None,
) -> int:
    """Score Norton (1-4) depuis deux variables AGGIR combinées."""
    scores = {"A": 4, "B": 2, "C": 1}
    s1 = scores.get(var1, 2)
    s2 = scores.get(var2, 2)
    avg = (s1 + s2) / 2
    return max(1, min(4, round(avg)))


def _norton_from_single_var(var_result: str | None) -> int:
    """Score Norton (1-4) depuis une variable AGGIR."""
    mapping = {"A": 4, "B": 3, "C": 1}
    return mapping.get(var_result, 2)


# ─── SPPB (Short Physical Performance Battery) ─────────────────────────────


def compute_sppb(
    question_reponse: list[dict],
) -> list[dict]:
    """
    SPPB : 3 sous-tests chronométrés, score total /12.
    Les durées sont saisies manuellement par le professionnel.

    1. Lever de chaise (5 fois) : score /4
    2. Équilibre statique : score /4
    3. Marche 4 mètres : score /4

    Interprétation :
    - 0–3 : Limitation sévère
    - 4–6 : Limitation modérée
    - 7–9 : Limitation légère
    - 10–12 : Performance normale
    """
    test_date_chaise = _get_test_date(question_reponse, "Date du test lever de chaise")
    test_date_equilibre = _get_test_date(question_reponse, "Date du test d'équilibre")
    test_date_marche = _get_test_date(question_reponse, "Date du test de marche")
    results: list[dict] = []

    # --- Lever de chaise ---
    duree_chaise_str = _get_response(question_reponse, "durée lever de chaise")
    duree_chaise = _safe_float(duree_chaise_str)
    score_chaise = _sppb_score_chaise(duree_chaise)

    if duree_chaise is not None:
        chaise_interp = _sppb_interp_chaise(score_chaise)
        results.append(
            {
                "nom": "Test du lever de chaise",
                "resultat": (
                    f"Le test du lever de chaise a été réalisé en "
                    f"{duree_chaise_str} secondes soit {score_chaise} points / 4 : "
                    f"{chaise_interp}"
                ),
            }
        )

    # --- Équilibre ---
    duree_equilibre_str = _get_response(question_reponse, "durée équilibre")
    duree_equilibre = _safe_float(duree_equilibre_str)
    score_equilibre = _sppb_score_equilibre(duree_equilibre)

    if duree_equilibre is not None:
        equilibre_interp = _sppb_interp_equilibre(score_equilibre)
        results.append(
            {
                "nom": "Test d'équilibre",
                "resultat": (
                    f"Le test de l'équilibre a été réalisé en "
                    f"{duree_equilibre_str} secondes soit {score_equilibre} points / 4 : "
                    f"{equilibre_interp}"
                ),
            }
        )

    # --- Marche 4m ---
    duree_marche_str = _get_response(question_reponse, "durée marche")
    duree_marche = _safe_float(duree_marche_str)
    score_marche = _sppb_score_marche(duree_marche)

    if duree_marche is not None:
        marche_interp = _sppb_interp_marche(score_marche)
        results.append(
            {
                "nom": "Test de la vitesse de marche sur 4 mètres",
                "resultat": (
                    f"Le test de la marche a été réalisé en "
                    f"{duree_marche_str} secondes soit {score_marche} points / 4 : "
                    f"{marche_interp}"
                ),
            }
        )

    # Dates
    if duree_chaise is not None:
        results.append({"nom": "Test du lever de chaise", "resultat": test_date_chaise})
    if duree_equilibre is not None:
        results.append({"nom": "Test d'équilibre", "resultat": test_date_equilibre})
    if duree_marche is not None:
        results.append(
            {
                "nom": "Test de la vitesse de marche sur 4 mètres",
                "resultat": test_date_marche,
            }
        )

    return results


def _sppb_score_chaise(duree: float | None) -> int:
    """Score lever de chaise 5× (Guralnik et al.)."""
    if duree is None or duree <= 0:
        return 0
    if duree <= 11.19:
        return 4
    if duree <= 13.69:
        return 3
    if duree <= 16.69:
        return 2
    if duree <= 60:
        return 1
    return 0


def _sppb_score_equilibre(duree: float | None) -> int:
    """Score équilibre statique (pieds joints, semi-tandem, tandem)."""
    if duree is None or duree <= 0:
        return 0
    if duree >= 30:
        return 4
    if duree >= 20:
        return 3
    if duree >= 10:
        return 2
    if duree >= 3:
        return 1
    return 0


def _sppb_score_marche(duree: float | None) -> int:
    """Score marche 4 mètres."""
    if duree is None or duree <= 0:
        return 0
    if duree <= 4.82:
        return 4
    if duree <= 6.20:
        return 3
    if duree <= 8.70:
        return 2
    if duree < 60:
        return 1
    return 0


def _sppb_interp_chaise(score: int) -> str:
    interps = {
        4: "Mobilité excellente",
        3: "Mobilité correcte",
        2: "Mobilité ralentie",
        1: "Mobilité très ralentie",
        0: "Test non réalisé ou impossible",
    }
    return interps.get(score, "Non évalué")


def _sppb_interp_equilibre(score: int) -> str:
    interps = {
        4: "Equilibre normal",
        3: "Equilibre correct",
        2: "Equilibre perturbé",
        1: "Test d'équilibre très perturbée",
        0: "Test non réalisé ou impossible",
    }
    return interps.get(score, "Non évalué")


def _sppb_interp_marche(score: int) -> str:
    interps = {
        4: "Vitesse de marche normale",
        3: "Mobilité correcte",
        2: "Mobilité ralentie",
        1: "Mobilité très ralentie ou impossible",
        0: "Test non réalisé ou impossible",
    }
    return interps.get(score, "Non évalué")


# ─── ICOPE Sensoriel ───────────────────────────────────────────────────────


def compute_icope_sensoriel(
    question_reponse: list[dict],
) -> list[dict]:
    """
    ICOPE step 1 Sensoriel (OMS 2019) :
    - Vision : problèmes oculaires signalés
    - Audition : test de chuchotement OD/OG
    """
    test_date_vision = _get_test_date(question_reponse, "Date du test de vision")
    test_date_audition = _get_test_date(question_reponse, "Date du test d'audition")
    results: list[dict] = []

    # --- Vision ---
    vision = _get_response(question_reponse, "problèmes oculaires")
    if vision is not None:
        if _is_oui(vision):
            results.append(
                {
                    "nom": "Icope déficience visuelle",
                    "resultat": "Une évaluation complète de la vue est recommandée",
                }
            )
        else:
            results.append(
                {
                    "nom": "Icope déficience visuelle",
                    "resultat": "Pas de déficience visuelle détectée",
                }
            )
        results.append({"nom": "Icope déficience visuelle", "resultat": test_date_vision})

    # --- Audition ---
    od = _get_response(question_reponse, "oreille droite")
    og = _get_response(question_reponse, "oreille gauche")

    if od is not None or og is not None:
        echec_od = od is not None and "incorrect" in od.lower()
        echec_og = og is not None and "incorrect" in og.lower()

        if echec_od or echec_og:
            results.append(
                {
                    "nom": "Icope audition",
                    "resultat": "Une évaluation complète de l'ouie est recommandée",
                }
            )
        else:
            results.append(
                {
                    "nom": "Icope audition",
                    "resultat": "Pas de déficience auditive détectée",
                }
            )
        results.append({"nom": "Icope audition", "resultat": test_date_audition})

    return results


# ─── Helper AGGIR ───────────────────────────────────────────────────────────


def _get_aggir_result(
    aggir_variables: list[dict],
    variable_name: str,
) -> str | None:
    """
    Retrouve le Resultat (A/B/C) d'une variable AGGIR par son nom.
    Gère les variables avec et sans sous-variables.
    """
    for var in aggir_variables:
        if var.get("Nom") == variable_name:
            return var.get("Resultat")
    return None


# ─── Orchestrateur principal ────────────────────────────────────────────────


def compute_all_sante_tests(
    sante_blocs: list[dict],
    aggir_variables: list[dict],
    patient_display_name: str = "Le patient",
) -> list[dict]:
    """
    Orchestre le calcul de tous les tests cliniques pour une évaluation.

    Parcourt les blocs santé, appelle le calculateur approprié pour chaque bloc,
    et injecte les résultats dans test[].

    Paramètres :
        sante_blocs: liste des blocs sante (evaluation_data.sante.blocs)
        aggir_variables: liste des variables AGGIR (evaluation_data.aggir.AggirVariable)
        patient_display_name: nom affiché dans les interprétations

    Retourne :
        La liste sante_blocs mise à jour avec les test[] calculés.
    """
    # --- Index des blocs par nom ---
    bloc_by_name: dict[str, dict] = {}
    for bloc in sante_blocs:
        nom = bloc.get("nom", "")
        bloc_by_name[nom] = bloc

    # --- Calculer Mini-GDS d'abord (nécessaire pour MNA-SF item E) ---
    depression_score: int | None = None
    depression_bloc = bloc_by_name.get("Dépression")
    if depression_bloc:
        qr = depression_bloc.get("questionReponse", [])
        # Calculer le score brut pour le croiser avec MNA
        score = 0
        for item in _MINI_GDS_ITEMS:
            resp = _get_response(qr, item["substr"])
            if resp is None:
                continue
            if item["invert"]:
                if _is_non(resp):
                    score += 1
            else:
                if _is_oui(resp):
                    score += 1
        depression_score = score

        # Calculer les résultats complets
        depression_bloc["test"] = compute_mini_gds(qr, patient_display_name)

    # --- Calculer Cognition (nécessaire pour MNA-SF item E) ---
    mini_cog_score: int | None = None
    cognition_bloc = bloc_by_name.get("Cognition")
    if cognition_bloc:
        qr = cognition_bloc.get("questionReponse", [])

        # Calculer le score mini-cog brut pour le croiser avec MNA
        horloge_resp = _get_response(qr, "horloge")
        horloge_ok = (
            horloge_resp is not None
            and "réussi" in horloge_resp.lower()
            and "non" not in horloge_resp.lower()
        )
        rappel_resp = _get_response(qr, "redonner les 3 mots")
        rappel_count = 0
        if rappel_resp:
            mots = [m.strip() for m in rappel_resp.replace(",", " ").split() if m.strip()]
            rappel_count = min(len(mots), 3)
        mini_cog_score = (2 if horloge_ok else 0) + rappel_count

        cognition_bloc["test"] = compute_cognition(qr, patient_display_name)

    # --- Anxiété (GAI-SF) ---
    anxiete_bloc = bloc_by_name.get("Anxiété")
    if anxiete_bloc:
        qr = anxiete_bloc.get("questionReponse", [])
        anxiete_bloc["test"] = compute_gai_sf(qr, patient_display_name)

    # --- Nutrition (IMC + ICOPE Nutrition + MNA-SF) ---
    nutrition_bloc = bloc_by_name.get("Nutrition")
    if nutrition_bloc:
        qr = nutrition_bloc.get("questionReponse", [])
        tests: list[dict] = []

        # IMC
        tests.extend(compute_imc(qr, patient_display_name))

        # ICOPE Nutrition
        tests.extend(compute_icope_nutrition(qr))

        # MNA-SF (avec données croisées)
        tests.extend(
            compute_mna_sf(
                qr,
                aggir_variables,
                depression_score=depression_score,
                cognition_mini_cog_score=mini_cog_score,
                patient_display_name=patient_display_name,
            )
        )

        nutrition_bloc["test"] = tests

    # --- Mobilité (SPPB) ---
    mobilite_bloc = bloc_by_name.get("Mobilité")
    if mobilite_bloc:
        qr = mobilite_bloc.get("questionReponse", [])
        mobilite_bloc["test"] = compute_sppb(qr)

    # --- Sensoriel (ICOPE) ---
    sensoriel_bloc = bloc_by_name.get("Sensoriel")
    if sensoriel_bloc:
        qr = sensoriel_bloc.get("questionReponse", [])
        sensoriel_bloc["test"] = compute_icope_sensoriel(qr)

    # --- Peau (Norton) ---
    peau_bloc = bloc_by_name.get("Peau")
    if peau_bloc:
        nutrition_qr = nutrition_bloc.get("questionReponse", []) if nutrition_bloc else None
        peau_bloc["test"] = compute_norton(
            aggir_variables,
            nutrition_question_reponse=nutrition_qr,
            peau_question_reponse=peau_bloc.get("questionReponse", []),
            patient_display_name=patient_display_name,
        )

    return sante_blocs
