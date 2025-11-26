# Cahier des charges – Outil de diagnostic structurel rapide pour hangars agricoles en France

## Contexte et objectifs

De nombreux hangars agricoles construits avant les années 2000 ne sont pas dimensionnés pour des charges additionnelles importantes (nouvelle couverture bac acier, panneaux photovoltaïques). Avec le temps, les structures peuvent montrer des signes de fatigue (déformations, corrosion, fissures) nécessitant un diagnostic. L’outil visé doit permettre d’évaluer rapidement la capacité portante vis-à-vis de charges supplémentaires et de décider si des renforts sont requis selon les Eurocodes.

## En bref : ce que fait l’outil
- Vous saisissez la géométrie du hangar (dimensions, pente, matériaux), l’emplacement climatique (zone neige/vent, altitude) et la surcharge envisagée (nouvelle couverture, panneaux PV, etc.).
- Le programme calcule automatiquement les charges réglementaires, estime les efforts dans le portique 2D, vérifie chaque élément selon l’Eurocode approprié (acier EC3 ou bois EC5) et affiche un verdict « GO / NO GO ».
- En cas de NO GO, il propose des renforts simples et réalistes pour ce type de hangar (pannes supplémentaires, bracons, poteaux/butons, doublage de profilés) et produit un rapport PDF structuré avec hypothèses, résultats et recommandations.

### Objectifs principaux
- Configurer la géométrie et la structure (dimensions, type de portique, matériaux) ainsi que les charges (neige, vent, surcharge utilisateur).
- Vérifier la capacité à supporter une surcharge additionnelle (ex. remplacement d’une couverture fibrociment par bac acier + panneaux PV) en respectant Eurocode 1 (actions), Eurocode 3 (acier) et Eurocode 5 (bois).
- Conclure automatiquement par un indicateur « GO / NO GO ».
- Proposer des renforts typiques (pannes, bracons, butons, poteaux supplémentaires) dimensionnés de façon préliminaire en cas de NO GO.
- Générer un rapport PDF clair (hypothèses, résultats, conclusion GO/NO GO, recommandations de renforcement).

## Périmètre et hypothèses clés
- **Structures visées** : portiques rigides acier S275 ou bois lamellé (hors treillis complexes).
- **Géométrie type** : nef rectangulaire simple (~18 m de long pour 3 travées de 6 m), portée 10–20 m, toiture mono ou bipente 10–15°, un portique contreventé longitudinalement.
- **Climat** : zones neige A–E et vent 1–2 (option 3), altitude par défaut 200 m (majoration neige +5 %/100 m au-delà de 200 m).
- **Matériaux/sections** : acier S275 pour portiques principaux, S390GD pour pannes secondaires, bois GL24 si charpente bois. Poids propres calculés à partir des sections.
- **Charges** : surcharges permanentes additionnelles saisies en kN/m² ou via options prédéfinies (ex. bac acier + PV ~0,20 kN/m²), combinaisons ELU Eurocode avec coefficients partiels par défaut (γF = 1,5 sur variables, γM = 1,0 sur acier).
- **Fondations** : hors périmètre (supposées suffisantes).
- **Modélisation** : approche 2D sécuritaire (portique bi-articulé par défaut), effets 3D et séisme exclus.

## Fonctionnalités détaillées
### Configuration et calcul des charges
- Paramétrage interactif des dimensions, type de toiture (mono/double pente), inclinaison, matériaux et sections (poteaux/poutres/pannes), espacements, zones climatiques, surcharge additionnelle.
- Calcul en continu ou sur demande des charges climatiques (neige, vent) et permanentes, affichage des valeurs retenues (kN/m²).

### Diagnostic GO / NO GO
- Analyse des sollicitations internes du portique 2D (N, M, V) sous charges combinées.
- Vérifications Eurocode appropriées (acier EC3, bois EC5) avec taux d’utilisation % par élément.
- Verdict GO si tous les éléments ≤ 100 % (ou seuil ajustable), NO GO sinon, avec tableau récapitulatif coloré dans l’IHM.

### Renforcement en cas de NO GO
- Propositions automatiques parmi : ajout/doublage de pannes, ajout de bracons, butons de stabilité, contreventements/tirants, doublage de profilés porteurs, ajout de poteaux intermédiaires.
- Pré-dimensionnement sommaire des renforts (sections, positionnement) et options cohérentes numérotées si plusieurs solutions.

### Rapport PDF
- Génération via FPDF/ReportLab : page de titre, données d’entrée, hypothèses, tableau des résultats (taux d’utilisation), conclusion GO/NO GO, recommandations de renfort, annexes (formules, schémas de charges et géométrie).

### Interface utilisateur
- GUI Python (Tkinter/PyQt/Streamlit) ou import/export Excel (pandas/openpyxl).
- Formulaires structurés par thème, bouton « Calculer/Diagnostiquer » et « Générer le rapport PDF ».
- Visualisation schématique 2D du portique paramétré avec annotations et renforts proposés, validations d’entrée et messages d’erreur clairs.

## Architecture logicielle
Modules prévus :
- **Interface (IHM)** : saisie, affichage résultats, schéma.
- **Lecture/écriture Excel** (optionnel).
- **Calcul des charges** : neige, vent, poids propres, surcharge utilisateur.
- **Analyse structurale** : modèle portique 2D, efforts internes et réactions.
- **Vérification Eurocode** : résistances et taux d’utilisation, verdict global.
- **Renforcement** : choix des solutions et dimensionnement préliminaire.
- **Rapport PDF** : composition et export du rapport.
- **Utilitaires** : conversions, géométrie, interpolation (altitude), gestion d’erreurs/logs.

## Principales fonctions cibles
- `calculer_charge_neige(zone, alt, pente, type_toit) → kN/m²`.
- `calculer_charge_vent(zone, hauteur, largeur, longueur, type_toit) → pressions kN/m²`.
- `resoudre_portique_2D(geom, charges) → efforts N/M/V`.
- `verifier_section_acier(profil, efforts, materiau) → taux %` (équivalent bois pour EC5).
- `determiner_renforts(resultats, config) → liste de recommandations`.
- `generer_pdf(rapport_data, fichier_sortie)`.

## Entrées utilisateur principales
- Longueur totale, portée, hauteur des poteaux.
- Type/pente de toiture (mono ou double pente), matériaux (acier S275, bois GL24…) et sections des poteaux/poutres.
- Type et entraxe des pannes (ex. Z200 S390GD).
- Zones neige/vent, altitude, catégorie d’exposition (option).
- Surcharge additionnelle (valeur ou option prédéfinie), coefficients de sécurité et options avancées.

## Sorties attendues
- Verdict GO/NO GO et tableau des taux d’utilisation par élément.
- Liste synthétique des renforts proposés.
- Rapport PDF complet exportable.
- Schéma visuel du portique avec renforts éventuels.
- Journaux internes pour débogage (optionnel).

## Technologies et bonnes pratiques
- Python 3.x avec NumPy, SciPy (option), pandas/openpyxl (Excel), matplotlib (schémas), tkinter/PyQt/Streamlit (GUI), FPDF/ReportLab (PDF).
- Code modulaire et documenté (PEP 8), paramètres normatifs centralisés (JSON/CSV), bibliothèque de profils standard intégrée, tests unitaires de base, architecture prête pour évolutions (déformations SLS, congères, dimensionnement optimisé des renforts).
- Livraison possible en script Python ou exécutable packagé (PyInstaller) pour usage terrain.
