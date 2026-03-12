# Rapport d’implémentation — Agent Hex V2

## 1. Objectif de cette V2

La V1 utilisait déjà une recherche **alpha-bêta** avec une profondeur fixe de 2 et une heuristique de type **plus court chemin pondéré** inspirée de Dijkstra.

L’objectif de la V2 est de conserver cette base, mais d’ajouter quatre améliorations majeures :

1. **Iterative deepening** pour mieux exploiter le budget temps.
2. **Transposition table** pour éviter de recalculer des sous-arbres identiques.
3. **Move ordering fort** pour maximiser l’efficacité de l’élagage alpha-bêta.
4. **Heuristique plus riche**, combinant une version améliorée du signal de connexion de type two-distance avec des motifs de **bridge/save-bridge**.

Cette direction est cohérente avec le projet Hex du cours : le jeu est joué sur un plateau **14x14**, le budget est de **15 minutes pour toute la partie**, Python est imposé, le multithreading et le GPU sont interdits, et le rapport doit justifier les choix algorithmiques de manière claire.

---

## 2. Point de départ : V1

La V1 fournie dans `my_player_v1.py` repose sur :

- `compute_action()`
- `alpha_beta(state, depth, alpha, beta, maximizing_player)`
- `heuristic(state)`
- `_get_shortest_path_distance(state, piece_type)`

Le cœur de la V1 est donc :

- une **recherche adversarielle**,
- une **profondeur fixe**,
- une **heuristique de connectivité simple**.

Cette structure est saine, mais limitée :

- profondeur rigide,
- pas de gestion fine du temps,
- aucun réemploi de positions déjà vues,
- ordre des coups arbitraire,
- heuristique trop globale et pas assez spécifique à Hex.

---

## 3. Principes de conception

### 3.1. Pourquoi conserver alpha-bêta ?

Le module 2 du cours présente explicitement **minimax + alpha-bêta + heuristique** comme base standard pour les jeux compétitifs. Il précise aussi que plusieurs améliorations sont possibles sans changer complètement de paradigme :

- éviter le calcul inutile,
- réduire la profondeur,
- ne considérer d’abord que les actions prometteuses,
- ajouter mémoire et connaissance experte.

C’est exactement la philosophie retenue ici.

### 3.2. Pourquoi ne pas passer immédiatement à MCTS ?

Le cours mentionne MCTS comme alternative, mais indique aussi qu’un agent minimax reste pertinent lorsque l’on dispose d’une **bonne heuristique** et que l’on veut injecter de la **connaissance spécifique au jeu**. Pour une V2, il est donc plus rentable d’améliorer fortement l’agent alpha-bêta existant que de repartir sur une nouvelle architecture.

### 3.3. Pourquoi des motifs spécifiques à Hex ?

La littérature sur Hex montre que les meilleurs agents historiques ne se contentent pas d’une recherche brute. Ils intègrent des notions structurelles du jeu :

- **bridges**,
- **save-bridges**,
- **virtual connections**,
- **inferior cells**,
- **évaluations de connexion robustes**.

Dans cette V2, on se limite volontairement aux briques les plus rentables et les plus faciles à justifier :

- une **approximation two-distance améliorée**,
- les motifs **bridge** et **save-bridge**.

---

## 4. Architecture générale de la V2

Le fichier `my_player_v2.py` est organisé autour de 5 blocs.

### 4.1. Entrée principale

- `compute_action(...)`

Responsabilités :

- générer les actions légales,
- calculer un budget temps local,
- lancer l’iterative deepening,
- mémoriser la meilleure action complètement évaluée,
- revenir proprement à la meilleure action connue en cas de timeout.

### 4.2. Recherche

- `_alpha_beta_root(...)`
- `_alpha_beta(...)`
- `_check_timeout()`

Responsabilités :

- exploration alpha-bêta,
- intégration de la table de transposition,
- gestion des bornes exactes / upper / lower,
- arrêt immédiat sur dépassement du budget temps.

### 4.3. Heuristique

- `heuristic(...)`
- `_two_best_connection_costs(...)`
- `_influence_score(...)`

Responsabilités :

- mesurer la qualité positionnelle d’un état non terminal,
- tenir compte de la force de connexion globale,
- tenir compte d’une redondance minimale des chemins,
- intégrer un signal structurel léger.

### 4.4. Move ordering

- `_order_actions(...)`
- `_adjacency_bonus(...)`
- `_goal_progress_bonus(...)`
- `_center_bonus(...)`

Responsabilités :

- trier les coups dans un ordre plus favorable au pruning,
- remonter le meilleur coup TT,
- prioriser les coups tactiques ou structurels.

### 4.5. Connaissance Hex spécifique

- `_count_bridges(...)`
- `_count_threatened_bridges(...)`
- `_local_bridge_creation_bonus(...)`
- `_local_savebridge_bonus(...)`
- `_local_block_bridge_bonus(...)`

Responsabilités :

- détecter les motifs locaux stables de Hex,
- favoriser les coups qui créent ou sauvent une connexion virtuelle élémentaire,
- pénaliser indirectement les positions où l’adversaire possède ce type de structure.

---

## 5. Détail des améliorations

## 5.1. Iterative deepening

### Quoi ?

Au lieu de lancer directement une recherche à profondeur fixe, on explore successivement :

- profondeur 1,
- profondeur 2,
- profondeur 3,
- etc.

jusqu’à manquer de temps.

### Pourquoi ?

Dans le projet, le temps est alloué sur toute la partie. Une profondeur fixe est fragile :

- trop faible → l’agent rate des tactiques,
- trop élevée → timeout ou réponse trop tardive.

L’iterative deepening donne toujours une **meilleure action complète disponible**.

### Comment ?

`compute_action()` :

- estime un temps pour le coup courant via `_allocate_time(...)`,
- initialise `self.search_deadline`,
- lance une boucle `for depth in range(1, max_depth + 1)`,
- conserve la dernière action entièrement résolue.

### Source

- **Projet Hex** : budget total de 15 minutes, pas de GPU, pas de multithreading.
- **Module 2** : minimax + alpha-bêta + heuristique comme base pratique.
- **Module 3** : idée générale d’exploiter entièrement un budget temps et de conserver la meilleure solution trouvée jusqu’ici.

---

## 5.2. Transposition table

### Quoi ?

Une **transposition** est un même état qui peut être atteint par plusieurs séquences de coups différentes.

Hex est particulièrement propice à cela : si deux coups indépendants sont joués dans un ordre différent, on peut obtenir le même plateau final.

### Pourquoi ?

Sans mémoire, l’algorithme recalcule plusieurs fois des sous-arbres identiques.

Avec une table de transposition, on stocke :

- la profondeur d’évaluation,
- la valeur estimée,
- le type de borne (`EXACT`, `LOWER`, `UPPER`),
- le meilleur coup associé.

### Comment ?

- La clé d’état est construite dans `_state_key(...)`.
- L’entrée TT est utilisée au début de `_alpha_beta(...)`.
- Si la profondeur stockée est suffisante, on peut :
  - retourner directement la valeur exacte,
  - raffiner `alpha` ou `beta`,
  - voire couper immédiatement la branche.
- En sortie, on réinsère le résultat avec son flag.

### Source

- **Module 2** : le chapitre sur les chemins redondants et les tables de transposition insiste sur le fait que des états identiques réapparaissent dans l’arbre et que ne pas les mémoriser coûte très cher.
- En pratique, cette idée est aussi omniprésente dans les moteurs classiques de recherche adversarielle.

---

## 5.3. Move ordering fort

### Quoi ?

Alpha-bêta est exact, mais sa vitesse dépend énormément de l’ordre d’exploration des actions.

### Pourquoi ?

Si l’on examine d’abord les coups les plus prometteurs pour le joueur courant :

- on obtient plus vite de bonnes bornes,
- on coupe plus tôt les branches inutiles,
- on peut atteindre une profondeur effective plus grande.

### Comment ?

La fonction `_order_actions(...)` attribue un score local à chaque action à partir de :

1. **coup terminal immédiat**,
2. **coup TT**,
3. **création de bridge**,
4. **save-bridge**,
5. **blocage d’un bridge adverse**,
6. **adjacence locale**,
7. **progression vers l’objectif**,
8. **centralité**.

Ensuite :

- aux nœuds MAX, on trie décroissant,
- aux nœuds MIN, on trie croissant.

### Source

- **Module 2** : il est dit explicitement que l’efficacité de l’alpha-bêta dépend fortement de l’ordre dans lequel les actions sont étendues, et que l’ordre idéal peut presque doubler la profondeur effective.
- **Littérature Hex** : les programmes forts exploitent massivement la connaissance du domaine pour guider la recherche.

---

## 5.4. Heuristique two-distance améliorée

### Quoi ?

La V1 utilisait seulement une distance de plus court chemin pondéré :

- pierre alliée = coût 0,
- case vide = coût 1,
- pierre adverse = obstacle.

La V2 passe à une mesure plus robuste inspirée des approches **two-distance / Queenbee** :

- on ne garde pas uniquement le meilleur coût de connexion,
- on récupère aussi une **seconde meilleure connexion**,
- on les combine dans un score unique.

### Pourquoi ?

Dans Hex, une position n’est pas forte seulement parce qu’elle possède un chemin “le plus court”.
Elle est forte aussi quand elle possède une **redondance** :

- plusieurs connexions plausibles,
- une structure moins fragile,
- une meilleure résilience face à un blocage.

### Comment ?

La fonction `_two_best_connection_costs(...)` utilise une variante de Dijkstra qui garde, pour chaque cellule :

- `dist1[cell]` = meilleur coût connu,
- `dist2[cell]` = deuxième meilleur coût connu.

Ensuite :

- on récupère les deux meilleurs coûts vers le bord cible,
- on définit un agrégat du type `2 * primary + secondary`.

L’évaluation finale compare ensuite :

- le coût agrégé du joueur,
- le coût agrégé de l’adversaire.

### Important

Ce n’est **pas** une implémentation complète des virtual connections ni du moteur Queenbee historique dans toute sa généralité. C’est une **approximation pratique, calculable rapidement**, conçue pour rester compatible avec alpha-bêta sur un plateau 14x14.

### Source

- **Module 1** : l’heuristique doit être informative mais aussi rapide à calculer ; une heuristique plus lente n’est pas toujours préférable.
- **Jack van Rijswijck, *Computer Hex*** : Queenbee popularise une évaluation de connexion plus riche que le simple plus court chemin.
- **Search and Evaluation in Hex** : les évaluations par connectivité, résistance et distance sont des briques centrales des agents Hex classiques.

---

## 5.5. Bridges et save-bridges

### Quoi ?

Dans Hex, un **bridge** est une structure locale très importante : deux pierres alliées non adjacentes peuvent former une connexion virtuelle solide via deux cellules intermédiaires.

Si l’adversaire en occupe une, l’autre peut souvent servir de **save-bridge**.

### Pourquoi ?

Ces motifs sont extrêmement rentables :

- très locaux,
- très fréquents,
- très informatifs,
- peu coûteux à reconnaître.

Ils capturent une vraie connaissance experte du jeu, absente d’une simple distance géométrique.

### Comment ?

La V2 détecte les 6 offsets standards des deux-bridges sur une grille hexagonale.

Fonctions utilisées :

- `_count_bridges(...)` : nombre de bridges stables,
- `_count_threatened_bridges(...)` : bridges attaqués mais sauvables,
- `_local_bridge_creation_bonus(...)` : bonus si le coup crée un bridge,
- `_local_savebridge_bonus(...)` : bonus si le coup sauve un bridge attaqué,
- `_local_block_bridge_bonus(...)` : bonus si le coup casse une structure de bridge adverse.

### Source

- La littérature Hex décrit depuis longtemps les **virtual connections** et notamment les **two-bridges** comme briques fondamentales.
- MoHex 2.0 mentionne explicitement le motif `savebridge` dans sa politique de simulation.
- Les approches de type Hexy/H-search reposent aussi fortement sur ces structures locales.

---

## 5.6. Fonction d’évaluation finale

La V2 combine quatre composantes :

1. **connexion two-distance améliorée**,
2. **bridges**,
3. **bridges menacés / save-bridges**,
4. **influence locale légère**.

Forme générale :

```text
Eval(state) =
    12 * (OppMetric - MyMetric)
  +  9 * (MyBridges - OppBridges)
  + 14 * (MyThreatenedBridges - OppThreatenedBridges)
  + 1.5 * (MyInfluence - OppInfluence)
```

avec :

```text
Metric(player) = 2 * PrimaryConnectionCost + SecondaryConnectionCost
```

### Pourquoi cette combinaison ?

- la composante de connexion reste la base,
- les bridges donnent du savoir structurel,
- les save-bridges ajoutent un signal tactique,
- l’influence lisse un peu le comportement sans coûter trop cher.

---

## 6. Liens explicites avec les modules du cours

## 6.1. Module 1 — Stratégies de recherche

Apport principal dans la V2 :

- conception d’une heuristique utile,
- compromis précision / vitesse,
- importance d’une bonne modélisation.

Application concrète :

- la two-distance améliorée est une heuristique plus informative que le simple coût minimal,
- mais elle reste volontairement simple pour ne pas ralentir excessivement la recherche.

## 6.2. Module 2 — Recherche adversarielle

Apport principal dans la V2 :

- minimax / alpha-bêta,
- profondeur limitée,
- propagation des bornes,
- ordre des actions,
- mémoire via transposition table.

Application concrète :

- toute l’architecture de recherche de la V2 est un prolongement direct du module 2.

## 6.3. Module 3 — Recherche locale

Apport principal ici :

- exploitation d’un budget temps,
- amélioration incrémentale,
- logique de meilleure solution courante.

Application concrète :

- l’iterative deepening joue un rôle analogue : on affine progressivement la solution disponible tant que le temps le permet.

Remarque :

- une future V3/V4 pourrait utiliser le module 3 plus directement pour **tuner automatiquement les poids** de l’heuristique par self-play.

---

## 7. Ce que cette V2 n’implémente pas encore

Pour garder un code robuste et raisonnable en Python, plusieurs idées fortes ont été volontairement laissées pour plus tard :

- **virtual connections complètes** via H-search,
- **mustplay region**,
- **inferior cell analysis**,
- **quiescence search**,
- **ouverture / endgame tables**,
- **MCTS hybride**.

Ces éléments sont très puissants, mais ils augmentent nettement la complexité de l’implémentation.

---

## 8. Limites actuelles de la V2

### 8.1. Approximation two-distance

La version utilisée ici est une approximation pratique fondée sur les **deux meilleurs coûts de connexion**. Elle améliore déjà la robustesse de l’évaluation, mais ne modélise pas complètement les connexions virtuelles fortes.

### 8.2. Bridges purement locaux

Les motifs bridge/save-bridge détectés sont très utiles, mais ne suffisent pas à représenter toutes les structures stratégiques profondes de Hex.

### 8.3. Time management simple

L’allocation de temps est volontairement conservatrice et heuristique. Elle peut encore être raffinée selon :

- la phase de partie,
- la complexité locale,
- la variance des scores entre les meilleurs coups.

---

## 9. Bilan

La V2 transforme la V1 en un véritable agent de recherche plus compétitif :

- **V1** : alpha-bêta profondeur fixe + shortest path simple.
- **V2** : iterative deepening + alpha-bêta + TT + move ordering + two-distance améliorée + bridges/save-bridges.

Le gain attendu est double :

1. **gain calculatoire**
   - moins de recalculs,
   - plus de pruning,
   - profondeur effective meilleure ;

2. **gain positionnel**
   - meilleure lecture de la connectivité,
   - meilleure prise en compte des motifs spécifiques à Hex.

Cette V2 est donc un très bon compromis entre :

- qualité pratique,
- cohérence avec les modules du cours,
- faisabilité en Python,
- clarté de justification dans un rapport académique.

---

## 10. Sources utilisées

### Sources du projet et du cours

- `Projet_Hex_H2026.pdf`
- `M1-strategie-recherche.pdf`
- `M2-recherche-adversaire.pdf`
- `M3-recherche-locale.pdf`
- `my_player_v1.py`

### Sources externes / recherche

- Jack van Rijswijck, *Computer Hex*.
- Jack van Rijswijck, *Search and Evaluation in Hex*.
- Vadim Anshelevich, *A Hierarchical Approach to Computer Hex*.
- MoHex 2.0: *A Pattern-Based MCTS Hex Player*.
- Chao Gao, *Search and Learning Algorithms for Two-Player Games with Application to Hex*.

---

## 11. Pistes directes pour la V3

Ordre recommandé :

1. ajouter une **mustplay region** simple ;
2. ajouter une première **inferior cell analysis** légère ;
3. ajouter une **quiescence search tactique** ;
4. tuner automatiquement les poids de l’heuristique par self-play.

