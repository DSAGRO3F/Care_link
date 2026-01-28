# Calculateur AGGIR - Documentation

## Vue d'ensemble

Ce module Python implémente l'algorithme officiel de calcul du GIR (Groupe Iso-Ressources) pour l'évaluation de la dépendance des personnes âgées en France, basé sur la grille AGGIR (Autonomie Gérontologique Groupes Iso-Ressources).

### Références légales
- Décret n°97-427 du 28 avril 1997
- Journal Officiel du 30 avril 1997 (pages 6530-6538)
- Code de l'action sociale et des familles, annexe 2.2 de l'article R232-3

## Qu'est-ce que la grille AGGIR ?

La grille AGGIR est l'outil national d'évaluation de la perte d'autonomie des personnes âgées. Elle permet de :
- Déterminer l'éligibilité à l'APA (Allocation Personnalisée d'Autonomie)
- Classer les personnes selon 6 niveaux de dépendance (GIR 1 à 6)
- Établir des plans d'aide personnalisés

### Les 6 GIR

- **GIR 1** : Dépendance totale (confinement au lit/fauteuil, fonctions mentales gravement altérées)
- **GIR 2** : Dépendance sévère (confinement avec fonctions mentales partiellement préservées OU déambulation avec troubles mentaux)
- **GIR 3** : Dépendance importante (autonomie mentale préservée mais besoin d'aide multiple fois par jour)
- **GIR 4** : Dépendance modérée (besoin d'aide pour transferts OU activités corporelles)
- **GIR 5** : Dépendance légère (aide ponctuelle pour toilette et activités domestiques)
- **GIR 6** : Autonome pour tous les actes essentiels

**Note** : Seuls les GIR 1 à 4 ouvrent droit à l'APA.

## Structure du code

### Classes principales

#### 1. `Variable` (Enum)
Énumère toutes les variables discriminantes de la grille AGGIR :
- Variables simples : Transferts, Déplacements (internes/externes), Alerter
- Variables composées : Cohérence, Orientation, Toilette, Habillage, Alimentation, Élimination

#### 2. `Adverbes` (Dataclass)
Représente l'évaluation des 4 critères pour chaque variable :
- `spontanement` : Sans incitation/stimulation
- `totalement` : Pour l'ensemble des actes
- `correctement` : Selon les usages et sans danger
- `habituellement` : Régulièrement dans le temps

#### 3. `AggiralgorithmTable`
Contient toutes les tables de coefficients de l'algorithme :
- 8 groupes de calcul (A à H)
- Coefficients pour chaque variable selon son résultat (A, B ou C)
- Seuils de détermination du GIR

#### 4. `AggorithmeAGGIR`
Implémente l'algorithme de calcul :
- Conversion des adverbes en lettres
- Combinaison des sous-variables
- Calcul des scores par groupe
- Détermination du GIR final

## Guide d'utilisation

### Installation

Aucune dépendance externe nécessaire. Le code utilise uniquement la bibliothèque standard Python 3.7+.

```python
# Copier le fichier aggir_calculator.py dans votre projet
from aggir_calculator import AggorithmeAGGIR, Variable, Adverbes
```

### Utilisation basique

```python
# 1. Créer une instance du calculateur
calculateur = AggorithmeAGGIR()

# 2. Préparer les évaluations
evaluations = {
    # Pour chaque variable, évaluer les 4 adverbes
    Variable.COMMUNICATION: Adverbes(
        spontanement=True,
        totalement=True,
        correctement=True,
        habituellement=True
    ),
    Variable.COMPORTEMENT: Adverbes(
        spontanement=True,
        totalement=True,
        correctement=False,  # Quelques troubles du comportement
        habituellement=True
    ),
    # ... (continuer pour toutes les variables)
}

# 3. Calculer le GIR
gir, details = calculateur.calculer_gir(evaluations)

print(f"GIR: {gir}")
print(f"Détails: {details}")
```

### Variables à évaluer

Pour un calcul complet, vous devez évaluer :

**Variables composées (avec sous-variables) :**
1. **Cohérence**
   - `Variable.COMMUNICATION`
   - `Variable.COMPORTEMENT`

2. **Orientation**
   - `Variable.ORIENTATION_TEMPS`
   - `Variable.ORIENTATION_ESPACE`

3. **Toilette**
   - `Variable.TOILETTE_HAUT` (visage, tronc, bras, mains)
   - `Variable.TOILETTE_BAS` (régions intimes, jambes, pieds)

4. **Habillage**
   - `Variable.HABILLAGE_HAUT` (vêtements tête/bras)
   - `Variable.HABILLAGE_MOYEN` (boutons, fermetures)
   - `Variable.HABILLAGE_BAS` (vêtements bas du corps, chaussures)

5. **Alimentation**
   - `Variable.SE_SERVIR` (couper, ouvrir, remplir)
   - `Variable.MANGER` (porter à la bouche, avaler)

6. **Élimination**
   - `Variable.ELIMINATION_URINAIRE`
   - `Variable.ELIMINATION_FECALE`

**Variables simples :**
- `Variable.TRANSFERTS` (se lever, se coucher, s'asseoir)
- `Variable.DEPLACEMENTS_INTERNES` (se déplacer dans le lieu de vie)
- `Variable.DEPLACEMENTS_EXTERNES` (sortir du lieu de vie)
- `Variable.ALERTER` (utiliser téléphone, alarme, sonnette)

### Règles d'évaluation

Pour chaque variable, évaluer les 4 adverbes :

**Spontanément** : La personne fait-elle sans qu'on lui dise, sans stimulation ?
- ✅ Oui → `True`
- ❌ Non → `False`

**Totalement** : La personne fait-elle l'ensemble des actes nécessaires ?
- ✅ Oui → `True`
- ❌ Non → `False`

**Correctement** : La personne fait-elle selon les usages, sans danger ?
- ✅ Oui → `True`
- ❌ Non → `False`

**Habituellement** : La personne fait-elle régulièrement, à chaque fois que nécessaire ?
- ✅ Oui → `True`
- ❌ Non → `False`

### Interprétation des résultats

La méthode `calculer_gir()` retourne un tuple `(gir, details)` :

```python
gir, details = calculateur.calculer_gir(evaluations)

# gir : int (1 à 6)
print(f"GIR: {gir}")

# details : dict avec :
print(details['lettres_sous_variables'])    # Lettres A/B/C pour chaque sous-variable
print(details['lettres_principales'])        # Lettres A/B/C pour variables principales
print(details['scores_par_groupe'])          # Scores calculés pour groupes A-H
print(details['groupe_final'])               # Groupe ayant déterminé le GIR
print(details['score_final'])                # Score du groupe final
```

## Exemples pratiques

### Exemple 1 : Personne très dépendante (GIR 1-2)

```python
evaluations_dependante = {}

# Toutes les variables en C (ne fait pas)
for var in [Variable.COMMUNICATION, Variable.COMPORTEMENT, 
            Variable.ORIENTATION_TEMPS, Variable.ORIENTATION_ESPACE,
            Variable.TOILETTE_HAUT, Variable.TOILETTE_BAS,
            # ... etc
           ]:
    evaluations_dependante[var] = Adverbes(
        spontanement=False,
        totalement=False,
        correctement=False,
        habituellement=False
    )

gir, _ = calculateur.calculer_gir(evaluations_dependante)
# Résultat attendu : GIR 1 ou 2
```

### Exemple 2 : Personne autonome (GIR 6)

```python
evaluations_autonome = {}

# Toutes les variables en A (fait seul)
for var in [Variable.COMMUNICATION, Variable.COMPORTEMENT, 
            Variable.ORIENTATION_TEMPS, Variable.ORIENTATION_ESPACE,
            # ... etc
           ]:
    evaluations_autonome[var] = Adverbes(
        spontanement=True,
        totalement=True,
        correctement=True,
        habituellement=True
    )

gir, _ = calculateur.calculer_gir(evaluations_autonome)
# Résultat attendu : GIR 6
```

### Exemple 3 : Personne avec troubles cognitifs légers (GIR 4)

```python
evaluations_troubles_legers = {
    # Cohérence légèrement altérée
    Variable.COMMUNICATION: Adverbes(True, True, False, True),  # B
    Variable.COMPORTEMENT: Adverbes(True, True, True, True),     # A
    
    # Orientation partiellement préservée
    Variable.ORIENTATION_TEMPS: Adverbes(True, False, True, True),  # B
    Variable.ORIENTATION_ESPACE: Adverbes(True, True, True, True),   # A
    
    # Autonomie corporelle préservée
    Variable.TOILETTE_HAUT: Adverbes(True, True, True, True),  # A
    Variable.TOILETTE_BAS: Adverbes(True, True, True, True),   # A
    Variable.HABILLAGE_HAUT: Adverbes(True, True, True, True),  # A
    Variable.HABILLAGE_MOYEN: Adverbes(True, True, True, True), # A
    Variable.HABILLAGE_BAS: Adverbes(True, True, True, True),   # A
    Variable.SE_SERVIR: Adverbes(True, True, True, True),       # A
    Variable.MANGER: Adverbes(True, True, True, True),          # A
    Variable.ELIMINATION_URINAIRE: Adverbes(True, True, True, True), # A
    Variable.ELIMINATION_FECALE: Adverbes(True, True, True, True),   # A
    Variable.TRANSFERTS: Adverbes(True, True, True, True),      # A
    Variable.DEPLACEMENTS_INTERNES: Adverbes(True, True, True, True), # A
    Variable.DEPLACEMENTS_EXTERNES: Adverbes(True, True, True, True), # A
    Variable.ALERTER: Adverbes(True, True, True, True),         # A
}

gir, details = calculateur.calculer_gir(evaluations_troubles_legers)
# Résultat attendu : GIR 4
```

## Intégration dans une application FastAPI

### Modèle Pydantic

```python
from pydantic import BaseModel
from typing import Dict
from aggir_calculator import Variable, Adverbes

class AdverbesModel(BaseModel):
    spontanement: bool
    totalement: bool
    correctement: bool
    habituellement: bool
    
    def to_adverbes(self) -> Adverbes:
        return Adverbes(
            spontanement=self.spontanement,
            totalement=self.totalement,
            correctement=self.correctement,
            habituellement=self.habituellement
        )

class EvaluationAGGIR(BaseModel):
    # Cohérence
    communication: AdverbesModel
    comportement: AdverbesModel
    
    # Orientation
    orientation_temps: AdverbesModel
    orientation_espace: AdverbesModel
    
    # ... (continuer pour toutes les variables)
    
class ResultatGIR(BaseModel):
    gir: int
    groupe_final: str
    score_final: int
    lettres_principales: Dict[str, str]
    eligible_apa: bool  # True si GIR 1-4
```

### Route FastAPI

```python
from fastapi import FastAPI
from aggir_calculator import AggorithmeAGGIR, Variable

app = FastAPI()
calculateur = AggorithmeAGGIR()

@app.post("/calculer-gir", response_model=ResultatGIR)
async def calculer_gir_endpoint(evaluation: EvaluationAGGIR):
    # Convertir le modèle Pydantic en dictionnaire pour le calculateur
    evaluations = {
        Variable.COMMUNICATION: evaluation.communication.to_adverbes(),
        Variable.COMPORTEMENT: evaluation.comportement.to_adverbes(),
        Variable.ORIENTATION_TEMPS: evaluation.orientation_temps.to_adverbes(),
        Variable.ORIENTATION_ESPACE: evaluation.orientation_espace.to_adverbes(),
        # ... (continuer pour toutes les variables)
    }
    
    # Calculer le GIR
    gir, details = calculateur.calculer_gir(evaluations)
    
    # Formater la réponse
    return ResultatGIR(
        gir=gir,
        groupe_final=details['groupe_final'],
        score_final=details['score_final'],
        lettres_principales={
            var.name: lettre 
            for var, lettre in details['lettres_principales'].items()
        },
        eligible_apa=(gir <= 4)
    )
```

## Points d'attention

### 1. Aides techniques
Les aides techniques (lunettes, prothèses auditives, fauteuil roulant, etc.) sont considérées comme faisant partie de la personne. Si une personne utilise un fauteuil roulant et se déplace parfaitement avec, elle est autonome pour les déplacements.

### 2. Évaluation "fait seul"
L'observation porte uniquement sur ce que fait la personne **seule**, en excluant ce que font les aidants et les soignants.

### 3. Différence C vs B
- **C** : La personne ne fait **jamais** l'activité seule, même partiellement → Il faut tout faire à sa place
- **B** : La personne fait partiellement, ou non spontanément, ou non habituellement, ou non correctement

### 4. Variables illustratives
Les 7 variables illustratives (gestion, cuisine, ménage, transports, achats, suivi du traitement, activités de temps libre) ne sont **pas** utilisées pour le calcul du GIR. Elles servent uniquement à compléter l'évaluation pour le plan d'aide.

## Tests et validation

Pour valider l'implémentation, vous pouvez :

1. **Cas limites** : Tester avec tous A (→ GIR 6) et tous C (→ GIR 1)
2. **Cas intermédiaires** : Tester des combinaisons connues
3. **Comparaison** : Comparer avec des calculateurs officiels (CNSA, logiciels agréés)

## Licence et avertissements

**Important** : 
- Cet algorithme est protégé et appartient au Syndicat national de gérontologie clinique
- Cette implémentation est fournie à titre éducatif et informatif
- Pour une utilisation officielle (APA, EHPAD), utilisez les logiciels agréés par les autorités
- Consultez toujours un professionnel de santé qualifié pour une évaluation officielle

## Support et contributions

Ce code est une adaptation Python de l'algorithme officiel documenté dans :
- Le décret n°97-427 du 28 avril 1997
- L'article de SQL Pro : https://blog.developpez.com/sqlpro/p9425/

Pour toute question sur l'algorithme officiel, référez-vous aux sources légales et aux organismes compétents (CNSA, ARS).
