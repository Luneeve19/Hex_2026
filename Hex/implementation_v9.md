# Rapport d'Implémentation - Version 9: Profondeur & Connexions Virtuelles

La version 4 marque un tournant stratégique en abandonnant la complexité des règles manuelles ("Panic Mode", "Blocking") au profit d'une puissance de calcul brute et d'une vision tactique épurée.

## 1. Philosophie : "La Profondeur bat la Complexité"

L'analyse des versions précédentes a montré que les heuristiques lourdes (O(N) ou O(N²) par nœud) ralentissaient l'agent, le limitant à une profondeur de recherche faible.

- **Constat** : Un agent à profondeur 2 avec des règles intelligentes joue moins bien qu'un agent à profondeur 4 avec une évaluation simple.
- **Solution** : Suppression de la majorité du code "métier" pour débloquer les niveaux 3 et 4 de l'arbre de recherche, permettant à l'algorithme Minimax de pleinement anticiper les coups adverses.

## 2. Heuristique : Dijkstra Bidirectionnel avec Ponts

L'évaluation du plateau repose désormais uniquement sur la notion de "Distance Restante", modifiée par la topologie spécifique du Hex.

### L'algorithme de base

Nous utilisons une variation de l'algorithme de Dijkstra (Breadth-First Search pondéré) pour trouver le plus court chemin dans le graphe du plateau :

- **Coût 0** : Traverser une pierre de notre couleur.
- **Coût 1** : Traverser une case vide (nécessite de poser une pierre).
- **Coût $\infty$** : Traverser une pierre adverse (obstacle infranchissable).

### L'innovation : Les Ponts (Bridges)

Le Dijkstra classique échoue souvent à Hex car il ne voit pas les connexions virtuelles. Nous avons intégré la détection des ponts directement dans le graphe de recherche.

- **Définition** : Deux cases séparées par un motif spécifique (ex: sauter une ligne et décaler) sont connectées virtuellement tant que les deux cases intermédiaires sont vides.
- **Implémentation** : Le graphe ajoute dynamiquement des arêtes de poids nul entre ces cases. L'agent "sait" qu'il est connecté même s'il y a du vide, rendant son évaluation de distance extrêmement précise sans nécessiter de règles de blocage manuelles.

## 3. Gestion Temporelle : Iterative Deepening

Pour respecter la contrainte stricte des 15 minutes sans sacrifier la qualité en début de partie, nous utilisons l'approfondissement itératif (Iterative Deepening).

- **Mécanisme** : L'agent lance une recherche à profondeur 1, puis 2, puis 3, etc.
- **Sécurité** : Avant chaque nouvelle profondeur, le temps restant est vérifié. Si le chrono approche la limite allouée au coup (calculée dynamiquement à 5% du temps global restant), l'agent s'arrête et renvoie le meilleur coup de la profondeur précédente complétée.

## 4. Optimisation : Tri des Coups (Move Ordering)

Pour maximiser l'efficacité de l'élagage Alpha-Beta, l'ordre d'exploration des nœuds est critique.

- **Biais Central** : Une carte de chaleur pré-calculée (O(1)) favorise l'exploration des coups au centre du plateau en premier.
- **Gain** : Cela permet à l'Alpha-Beta de trouver rapidement de bons coups et de "couper" (prune) les branches inintéressantes beaucoup plus tôt, accélérant la recherche globale d'un facteur significatif.

## 5. Conclusion sur la V4

Cette version est un "moteur de course". Elle ne s'encombre pas de stratégies défensives codées en dur ("si ennemi proche, alors panique"). Elle laisse la profondeur de l'arbre de recherche découvrir ces vérités tactiques par elle-même, résultant en un jeu plus fluide, plus rapide et mathématiquement plus robuste.
