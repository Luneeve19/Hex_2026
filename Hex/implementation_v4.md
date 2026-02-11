# Rapport d'Implémentation - Version 4 : Criticalité et Tri des Coups (Move Ordering)

La version 4 optimise l'efficacité de l'algorithme Alpha-Béta en introduisant une intelligence de tri avant l'exploration de l'arbre.

## 1. Le Problème : L'Explosion Combinatoire
Sur un plateau 14x14, le nombre de coups possibles est immense (~196 au début). L'élagage Alpha-Béta est très sensible à l'ordre dans lequel les coups sont explorés. Si le meilleur coup est examiné en dernier, aucun élagage ne se produit.

## 2. Solution : Move Ordering par "Criticalité"
L'agent identifie les cases les plus importantes du plateau avant de lancer la recherche récursive.

### Définition de la Criticalité
Une case est jugée **critique** si elle se trouve à l'intersection des flux de deux joueurs. C'est ce qu'on appelle un "Point de Selle" (Saddle Point).
*   **Calcul** : Pour chaque case vide $(r, c)$, on calcule :
    *   $Dist_{R} = Dist(Haut, (r,c)) + Dist((r,c), Bas)$
    *   $Dist_{B} = Dist(Gauche, (r,c)) + Dist((r,c), Droite)$
*   **Score de Criticalité** : $-(Dist_{R} + Dist_{B})$. Plus cette somme est petite, plus la case est proche des chemins les plus courts des deux joueurs.

## 3. Implémentation : Dijkstra Quadridirectionnel
Pour obtenir ces scores, l'agent effectue 4 recherches Dijkstra par niveau (ou au moins à la racine) :
1.  Depuis le bord Haut vers toutes les cases.
2.  Depuis le bord Bas vers toutes les cases.
3.  Depuis le bord Gauche vers toutes les cases.
4.  Depuis le bord Droite vers toutes les cases.

## 4. Impact sur la Performance
*   **Élagage Massif** : En explorant les cases critiques en priorité, l'agent trouve rapidement des "réfutations" (bons coups adverses) qui permettent de couper des pans entiers de l'arbre de recherche.
*   **Profondeur accrue** : Cette efficacité permet d'envisager des recherches plus profondes (Depth 3 ou plus) tout en restant dans les limites de temps.
*   **Style de jeu** : L'IA devient extrêmement agressive sur les points de tension du plateau, bloquant l'adversaire pile au moment où il s'apprête à faire une jonction.

## 5. Conclusion sur la V4
La V4 ne change pas l'évaluation finale du plateau, mais elle change la **vitesse** à laquelle l'IA trouve la meilleure décision. C'est l'optimisation algorithmique indispensable pour passer d'un niveau amateur à un niveau compétitif sur de grands plateaux.
