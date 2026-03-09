# Rapport d'Implémentation - Version 5 : Champs d'Influence et Centralité

La Version 5 s'éloigne des calculs purement "pathfinding" pour intégrer des concepts de contrôle spatial et de topologie réseau.

## 1. Concept : Champ de Potentiel (Influence Maps)
Cette heuristique s'inspire de la physique (champs gravitationnels ou électrostatiques). L'idée est que chaque pierre posée sur le plateau ne contrôle pas uniquement sa propre case, mais exerce une "influence" sur les cases environnantes.

### Implémentation
Nous générons une matrice `numpy` 14x14 initialisée à zéro. Pour chaque pierre présente sur le plateau :
*   **Centre (La pierre)** : Valeur ±10 (Positif pour nous, négatif pour l'adversaire).
*   **Cercle 1 (Voisins directs)** : Valeur ±5.
*   **Cercle 2 (Voisins de voisins)** : Valeur ±2.

### Intérêt Stratégique
Le score d'influence est la somme de toute la matrice. Cela encourage l'IA à :
1.  **Grouper ses pierres** : Les champs se superposent, créant des zones de fort contrôle local difficile à pénétrer pour l'adversaire.
2.  **Maximiser l'impact** : Placer une pierre au centre du plateau touche plus de voisins (et donc génère plus de points) qu'une pierre sur un bord.
3.  **Créer des barrières** : Une ligne de pierres crée un "mur" de potentiel positif que l'adversaire (qui cherche à minimiser ce score ou créer son propre chemin) aura du mal à traverser virtuellement.

## 2. Intégration dans l'Heuristique Globale
L'influence seule ne suffit pas à gagner (elle peut encourager à faire des "pâtés" inutiles). Nous la combinons donc avec l'heuristique de distance de la V2.

**Formule finale :**
$$Score = (D_{adv} - D_{moi}) 	imes 100 + (Score_{Influence} 	imes 0.1)$$

*   Le facteur **100** sur la distance garantit que la **connexion** reste la priorité absolue (on ne sacrifie pas la victoire pour du territoire).
*   L'influence sert de "Tie-Breaker" (départage) pour choisir entre deux coups qui réduisent la distance de la même manière, privilégiant celui qui contrôle le plus d'espace.

## 3. Centralité (Intermédiarité)
Bien que non explicitement calculée par une mesure de "Betweenness Centrality" lourde (coûteuse en temps), l'influence map agit comme une approximation. Les cases centrales ou les goulots d'étranglement naturels accumulent plus d'influence car elles sont à la croisée de multiples voisinages.

## 4. Conclusion sur la V5
C'est un agent "complet" qui possède à la fois un objectif clair (le chemin) et une compréhension positionnelle (le territoire). Il est particulièrement robuste dans les phases de milieu de partie où les chemins ne sont pas encore clairement définis.
