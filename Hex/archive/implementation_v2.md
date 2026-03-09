# Rapport d'Implémentation - Version 2 : Connexions Virtuelles et Optimisation

La version 2 améliore la perception stratégique de l'agent en intégrant des concepts avancés de la théorie du jeu de Hex : les **Connexions Virtuelles**.

## 1. Amélioration de l'Heuristique : Virtual Connections (Bridges)
La plus grande faiblesse de la V1 était de ne considérer que les cases adjacentes. Au Hex, deux pierres peuvent être "connectées" même sans se toucher.

### Le concept du "Pont" (Bridge)
Un pont est une structure où deux pierres sont séparées par deux cases vides adjacentes communes. 
*   **Propriété** : Si l'adversaire joue dans l'une des cases vides, nous jouons dans l'autre pour maintenir la connexion. La distance réelle entre ces deux pierres est donc de **0** (ou virtuellement connectée).

### Implémentation dans Dijkstra
Nous avons modifié le voisinage exploré par l'algorithme de Dijkstra. En plus des 6 voisins directs, l'algorithme vérifie désormais 6 **offsets de ponts** :
*   Offsets : `(-1, 2), (1, 1), (2, -1), (1, -2), (-1, -1), (-2, 1)`.
*   **Condition de validité** : Un pont n'est ajouté comme arête de poids 0 (ou 1 si on vise une case vide) que si les **deux cases intermédiaires** sont vides.

## 2. Impact Stratégique
Cette modification change radicalement le comportement de l'IA :
1.  **Jeu plus aéré** : L'IA ne joue plus seulement "collé" à ses propres pièces, mais crée des réseaux de ponts plus difficiles à intercepter.
2.  **Défense anticipative** : L'IA identifie les ponts de l'adversaire et tente de les "briser" en s'insérant dans les cases critiques.
3.  **Évaluation plus juste** : Le score $D_{adv} - D_{moi}$ reflète maintenant la réalité du jeu de haut niveau, où les connexions virtuelles sont la norme.

## 3. Gestion du Temps et Profondeur
*   **Profondeur** : Toujours fixée à 2 pour compenser le surcoût calculatoire de la vérification des ponts dans Dijkstra.
*   **Optimisation** : L'utilisation de `bridge_data` pré-calculé pour éviter les calculs redondants à chaque nœud de l'arbre Minimax.

## 4. Conclusion sur la V2
L'agent passe d'un joueur "naïf" (basé sur le plus court chemin physique) à un joueur "stratégique" capable de manipuler les structures fondamentales du Hex. C'est cette version qui permet de rivaliser avec des agents plus avancés.
