# Rapport d'Optimisation : Agent Hex "Turbo"

Ce document détaille les changements techniques effectués pour passer d'une version "Stratégique mais Lente" à une version "Compétitive et Rapide".

## 1. Accélération de la Recherche (x10 à x100)

### Avant (Lent)

- **Move Ordering lourd :** Calculait 4 fois Dijkstra complet (`_get_criticality_map`) _avant_ chaque coup à la racine pour savoir quel coup explorer en premier.
- **Profondeur fixe :** `depth=2` constant. Risque de timeout ou de jouer trop vite.

### Après (Rapide)

- **Move Ordering statique :** Utilisation d'une "Carte de Chaleur" du centre pré-calculée (`self.center_weights`).
  - _Gain :_ O(1) au lieu de O(N²) pour trier les coups.
- **Iterative Deepening :** L'agent commence à profondeur 1, puis 2, puis 3... jusqu'à ce que le chrono dise "Stop".
  - _Gain :_ Gestion parfaite du temps (15 min) et garantie de toujours avoir un coup à jouer.

## 2. Optimisation de l'Heuristique (Dijkstra)

### Avant

- **Boucles redondantes :** Parcours inefficaces des voisins.
- **Calculs répétés :** Recalculait des distances sans mémorisation efficace.

### Après

- **Dijkstra Vectorisé (Logic) :** Utilisation de `heapq` avec sortie anticipée (`Early Exit`). Dès qu'on trouve le chemin le plus court, on arrête de calculer le reste du plateau.
- **Ponts Intégrés :** La logique des "Ponts" (connexions virtuelles) est intégrée directement dans le coût du chemin (coût 0 pour traverser un pont) au lieu d'être une surcouche.

## 3. Gestion Mémoire

- **Nettoyage :** Suppression des dictionnaires de "Criticality" stockés inutilement.
- **Sécurité JSON :** Le code est propre pour ne pas faire crasher les logs d'Abyss (pas d'objets complexes stockés dans `self`).

---

## 4. Bilan des Fonctionnalités (Ce qui a été gardé vs modifié)

| Fonctionnalité Originale     | État dans la version Optimisée | Explication Technique                                                                                                                                                                                      |
| :--------------------------- | :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dijkstra (Shortest Path)** | ✅ **Amélioré**                | Plus rapide, intègre maintenant les ponts nativement.                                                                                                                                                      |
| **Détection des Ponts**      | ✅ **Conservée**               | Intégrée dans le cœur du Dijkstra pour une vision plus juste de la distance.                                                                                                                               |
| **Center Priority**          | 🔄 **Déplacée**                | Ne fait plus partie de l'évaluation finale (feuilles), mais sert à **trier les coups** pour l'élagage Alpha-Beta. C'est plus efficace ainsi.                                                               |
| **Panic Defense**            | ❌ **Supprimée**               | **Raison :** C'était une boucle lente O(N) à chaque feuille. Avec une recherche plus profonde (grâce à la vitesse gagnée), l'agent "voit" naturellement le danger sans avoir besoin de cette règle "dure". |
| **Advanced Blocking**        | ❌ **Supprimée**               | **Raison :** Même chose. C'était une heuristique coûteuse. Un Alpha-Beta à profondeur 3 ou 4 trouvera naturellement ces coups de blocage car ils minimisent le score adverse.                              |
