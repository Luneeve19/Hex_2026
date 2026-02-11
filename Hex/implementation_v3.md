# Rapport d'Implémentation - Version 3 : Théorie des Circuits Électriques

La version 3 représente l'aboutissement technique de l'agent en remplaçant la recherche de chemin discret par une analyse de flux continu basée sur la physique.

## 1. Heuristique : Résistance Équivalente (Electrical Network)
Cette approche, inspirée des travaux de Vadim Anshelevich, modélise le plateau de Hex comme un réseau de résistances électriques.

### L'analogie physique
Chaque état du plateau est converti en un circuit :
*   **Conducteurs (0.01 Ω)** : Nos propres pierres. Le courant circule presque sans perte.
*   **Résistances (1.0 Ω)** : Les cases vides. Elles représentent le "coût" de l'effort pour établir une connexion.
*   **Isolants (1,000,000 Ω)** : Les pierres adverses. Elles bloquent presque totalement le passage du courant.

### Pourquoi c'est supérieur à Dijkstra ?
Alors que Dijkstra ne voit qu'un seul chemin (le plus court), la théorie des circuits évalue la **qualité globale** de la position :
1.  **Largeur du chemin** : Deux chemins parallèles réduisent la résistance totale (loi d'Ohm : $1/R_{eq} = 1/R_1 + 1/R_2$). L'IA préférera donc une position offrant plusieurs options de victoire.
2.  **Robustesse** : Une position avec un "goulot d'étranglement" aura une résistance plus élevée qu'une position aérée, même si la longueur du chemin le plus court est la même.
3.  **Anticipation des blocages** : Si l'adversaire bloque une branche, le courant se redistribue. L'impact sur la résistance totale est immédiat et précis.

## 2. Implémentation Mathématique (Numpy)
L'évaluation d'un plateau nécessite la résolution d'un système d'équations linéaires :
*   **Matrice Laplacienne** : Nous construisons une matrice $L$ de taille $(N+2) 	imes (N+2)$ (où $N=196$ cases + Source + Sink).
*   **Loi des Nœuds de Kirchhoff** : Le système est résolu à l'aide de `numpy.linalg.solve` pour trouver les potentiels électriques à chaque nœud.
*   **Calcul final** : La résistance équivalente $R_{eq}$ est dérivée du potentiel à la Source pour un courant injecté de 1 Ampère.

## 3. Formule de Score : $Score = R_{adv} / R_{moi}$
L'objectif de l'agent est de minimiser sa propre résistance vers ses bords cibles tout en maximisant celle de l'adversaire. Le ratio offre une sensibilité fine pour comparer l'avancement respectif des deux joueurs.

## 4. Compromis Performance / Profondeur
Le calcul matriciel est plus lourd que le Dijkstra de la V2. 
*   **Optimisation** : Utilisation des capacités de calcul vectoriel de `numpy`.
*   **Stratégie** : En raison du coût de résolution des matrices (environ 196x196), cette version est optimisée pour une profondeur de recherche plus faible (Depth 1 ou 2), compensée par une "intelligence" d'évaluation par nœud bien plus profonde.

## 5. Conclusion sur la V3
Cette version transforme l'agent en un stratège capable d'évaluer la "pression" exercée sur l'ensemble du plateau. C'est l'approche la plus proche des moteurs de Hex professionnels avant l'ère du Deep Learning.
