# Rapport d'Implémentation - Version 6 : Mode Panique et Défense des Bords

La Version 6 est une version spécialisée de la V4 conçue pour corriger une faiblesse commune des IA : l'incapacité à voir l'urgence d'un blocage sur la ligne d'arrivée.

## 1. Le Problème : La Cécité de Bordure
Dans les versions précédentes, l'IA pouvait parfois ignorer une pierre adverse située à 1 case du bord si son propre chemin semblait plus "court" en termes de Dijkstra pur. Cependant, au Hex, une pierre sur l'avant-dernière rangée est une menace mortelle immédiate.

## 2. Solution : Le "Panic Mode" (Défense de Bordure)
Nous avons ajouté un module de détection de proximité qui surveille les bords cibles de l'adversaire.

### Logique de Détection
L'IA analyse la position de chaque pierre adverse par rapport à ses objectifs :
*   **Pour le joueur Rouge** : Proximité avec la ligne 0 (Haut) et la ligne 13 (Bas).
*   **Pour le joueur Bleu** : Proximité avec la colonne 0 (Gauche) et la colonne 13 (Droite).

### Application du Bonus/Pénalité
Dès qu'une pierre adverse entre dans la "Zone de Risque" (distance ≤ 1 case du bord) :
*   Une pénalité massive est appliquée au score de l'état.
*   **Impact** : Dans l'arbre Alpha-Béta, cela rend les branches où l'adversaire approche du bord extrêmement indésirables. L'IA choisira donc en priorité les branches (actions) qui placent une pierre bloquante entre l'adversaire et le bord.

## 3. Architecture Héritée
La V6 conserve les piliers de la V4 pour rester compétitive globalement :
*   **Alpha-Béta** : Recherche récursive.
*   **Dijkstra + Bridges** : Évaluation de la connectivité globale.
*   **Criticality Ordering** : Tri des coups pour optimiser la vitesse de recherche.

## 4. Impact Stratégique : Le "Mur"
En pratique, cette version se comporte comme un défenseur acharné. Dès que l'adversaire tente une percée latérale, l'IA "décroche" de son propre chemin pour aller construire un mur de protection sur le bord menacé. C'est une stratégie de "sécurité d'abord" qui empêche les défaites par surprise sur les bords du plateau.

## 5. Conclusion sur la V6
La V6 est l'agent le plus "prudent". Elle sacrifie un peu d'agressivité pour une robustesse défensive accrue, ce qui est souvent la clé pour gagner des tournois contre des humains ou d'autres IA qui jouent de manière très directe.
