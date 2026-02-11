# Rapport d'Implémentation - Version 1 : Fondations et Algorithmes de Base

Cette version pose les bases de l'intelligence de l'agent Hex en se concentrant sur une recherche robuste et une évaluation spatiale du plateau.

## 1. Algorithme de Recherche : Minimax avec Élagage Alpha-Béta
L'algorithme principal utilisé est le **Minimax**, optimisé par l'**élagage Alpha-Béta**. 

*   **Objectif** : Réduire le nombre de nœuds explorés dans l'arbre de recherche en "coupant" les branches qui ne peuvent pas influencer la décision finale (car elles mènent à des états moins bons que ceux déjà trouvés).
*   **Profondeur** : Fixée à 2 pour cette version, afin de garantir des temps de réponse rapides sur un plateau de 14x14 (soit ~196 actions possibles par tour).

## 2. Heuristique : Stratégie "Two-Distance" (Dijkstra)
Le cœur de l'intelligence réside dans la fonction d'évaluation. Contrairement aux échecs, le nombre de pièces à Hex n'est pas un bon indicateur. L'importance réside dans la **connectivité**.

### Le Concept
L'heuristique utilise l'algorithme de **Dijkstra** pour modéliser le plateau comme un graphe de coûts :
*   **Poids 0** : Case occupée par l'un de nos pions (déjà connecté).
*   **Poids 1** : Case vide (coût d'un coup pour l'occuper).
*   **Poids Infini** : Case occupée par l'adversaire (chemin bloqué).

### La Formule : $Score = D_{adv} - D_{moi}$
*   $D_{moi}$ : Distance la plus courte (en nombre de pierres à ajouter) pour relier nos deux bords.
*   $D_{adv}$ : Distance la plus courte pour que l'adversaire relie ses bords.
*   **Interprétation** : Un score positif élevé signifie que l'adversaire est loin de gagner tandis que nous sommes proches de la victoire. Cela pousse l'IA à la fois à construire son chemin et à bloquer activement celui de l'adversaire.

## 3. Gestion du Temps
Dans cette phase initiale, la gestion du temps est simpliste avec une profondeur fixe. L'agent garantit une réponse en calculant les distances Dijkstra de manière efficace grâce à une file de priorité (`heapq`).

## 4. Résumé Technique
*   **Modélisation** : Graphe hexagonal 14x14.
*   **Calcul de distance** : Dijkstra unilatéral (Haut -> Bas pour Rouge, Gauche -> Droite pour Bleu).
*   **Complexité** : Alpha-Béta permet de gérer l'explosion combinatoire initiale.
