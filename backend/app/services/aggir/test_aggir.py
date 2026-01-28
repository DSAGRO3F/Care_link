from app.services.aggir.calculator import AggirCalculator, Variable, Adverbes

# Test simple
calculator = AggirCalculator()
evaluations = {
    Variable.COMMUNICATION: Adverbes(True, True, True, True),
    Variable.COMPORTEMENT: Adverbes(True, True, True, True),
    Variable.ORIENTATION_TEMPS: Adverbes(True, True, True, True),
    Variable.ORIENTATION_ESPACE: Adverbes(True, True, True, True),
    Variable.TOILETTE_HAUT: Adverbes(True, True, True, True),
    Variable.TOILETTE_BAS: Adverbes(False, False, False, False),
    Variable.HABILLAGE_HAUT: Adverbes(True, True, True, True),
    Variable.HABILLAGE_MOYEN: Adverbes(True, True, True, True),
    Variable.HABILLAGE_BAS: Adverbes(False, False, True, True),
    Variable.SE_SERVIR: Adverbes(True, True, True, True),
    Variable.MANGER: Adverbes(True, True, True, True),
    Variable.ELIMINATION_URINAIRE: Adverbes(True, True, True, True),
    Variable.ELIMINATION_FECALE: Adverbes(True, True, True, True),
    Variable.TRANSFERTS: Adverbes(True, True, True, True),
    Variable.DEPLACEMENTS_INTERNES: Adverbes(True, True, True, True),
    Variable.DEPLACEMENTS_EXTERNES: Adverbes(True, True, True, True),
    Variable.ALERTER: Adverbes(True, True, True, True),
}

gir, details = calculator.calculer_gir(evaluations)
print(f"GIR calculé: {gir}")
print(f"Groupe: {details['groupe_final']}")
