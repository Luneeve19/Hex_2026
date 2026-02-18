# Rapport d'Implémentation - Version 10 : Maîtrise des Bords (Edge Templates)

La Version 5 franchit un cap dans l'intelligence positionnelle de l'agent. En plus de calculer le chemin le plus court, l'agent comprend désormais quand une connexion est **mathématiquement inévitable**, lui permettant d'économiser des coups précieux.

## 1. Concept Stratégique : L'Économie de Coups (Tempo)

Dans Hex, jouer un coup pour sécuriser une connexion qui est déjà imprenable est une erreur stratégique majeure (perte de tempo).

- **Problème V4** : Le Dijkstra standard voyait une pierre proche du bord (mais pas touchante) comme étant à "Distance 1". L'agent avait tendance à gaspiller un coup pour la coller au bord.
- **Solution V5** : L'agent reconnaît désormais les "Modèles de Bords" (Edge Templates). Si la connexion est garantie, il considère la distance comme nulle et utilise son coup ailleurs pour attaquer.

## 2. Implémentation : Détection de Motifs

Nous avons enrichi l'algorithme de Dijkstra avec une règle de sortie anticipée basée sur la topologie du plateau.

### Le Modèle "II" (Template II)

C'est le motif le plus courant et le plus utile en fin de partie.

- **Configuration** : Une pierre alliée se trouve sur l'avant-dernière ligne (ou colonne).
- **Condition** : Les deux cases adjacentes menant au bord final sont vides (ou contrôlées).
- **Logique** : Si l'adversaire joue dans l'une des cases, nous jouons immédiatement dans l'autre. La connexion au bord est donc **inconditionnelle**.
- **Résultat Heuristique** : `Distance = 0`. L'algorithme considère le bord comme _déjà atteint_.

## 3. Intégration Technique

La détection se fait en temps constant $O(1)$ à l'intérieur de la boucle de propagation du Dijkstra.

- **Pas de surcoût** : Contrairement à une analyse de pattern séparée qui scannerait tout le plateau, cette vérification n'est faite que lorsque le front de recherche (Dijkstra) approche naturellement du bord.
- **Robutesse** : Le code vérifie non seulement que les cases sont vides, mais aussi qu'elles n'appartiennent pas à l'adversaire, garantissant que le "template" n'est pas brisé.

## 4. Conclusion sur la V10

Avec cette amélioration, l'agent ne se contente plus de chercher un chemin : il optimise ses ressources. Il sait ignorer les batailles déjà gagnées sur les bords pour concentrer toute sa profondeur de calcul (Alpha-Beta) sur le centre et les zones de conflit actif. C'est un comportement typique des joueurs de niveau expert.
