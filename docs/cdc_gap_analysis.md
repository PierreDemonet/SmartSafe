# Évaluation de couverture du cahier des charges

Cette note compare rapidement le prototype actuel (`pvai diag`) avec le cahier des charges "diagnostic structurel rapide".

## Points couverts par le prototype
- Calcul simplifié de la charge de neige (zone, altitude, effet pente/monopente) et de vent (zone, hauteur, type de toit). 
- Vérification rudimentaire de la poutre (arbalétrier) et du poteau par rapport à leur résistance en flexion/traction-compression, avec verdict GO / NO GO et suggestions génériques de renforts.
- Exposition en ligne de commande via `pvai diag` pour paramétrer la géométrie de base, les charges et les sections.

## Écarts majeurs au cahier des charges
- **Couverture normatives limitées** : les vérifications Eurocode sont réduites à des capacités plastiques basiques sans interaction N/M détaillée, flambement, déversement ou vérification bois EC5.
- **Portée structurelle partielle** : seules une poutre et un poteau sont vérifiés. Les pannes, contreventements, butons et liaisons ne sont pas modélisés ni vérifiés.
- **Charges et combinaisons** : pas de gestion des combinaisons ELU/SLS complètes, des cas de vent en dépression/sous-pression, ni des effets de neige non-uniforme ou congères.
- **Paramétrage matériau/sections** : bibliothèque de profils minimale, pas de chargement depuis une table externe ou d’options bois usuelles.
- **Renforts** : les propositions sont textuelles et génériques ; aucun recalcul itératif ni pré-dimensionnement quantitatif n’est produit.
- **Livrables** : aucune génération de rapport PDF ou d’export Excel ; pas d’IHM graphique ni de schéma illustratif.
- **Qualité/fiabilité** : seulement deux tests unitaires ; aucun test bout-en-bout ni validation sur un cas de référence.

## Recommandations prioritaires
1. Étendre le calcul des charges (vent pression/succion, combinaisons Eurocode) et ajouter la prise en compte des pannes/contreventements.
2. Implémenter des vérifications EC3/EC5 plus complètes (flambement, interaction N+M, déversement, kmod/γM bois) et intégrer une bibliothèque de profils/ matériaux depuis un fichier de données.
3. Générer un rapport PDF conforme au cahier des charges (résumé GO/NO GO, tableau des taux, renforts dimensionnés) et ajouter un mode GUI/Excel pour la saisie.
4. Augmenter la couverture de tests avec un cas complet de hangar type et un scénario NO GO + renfort proposé.
