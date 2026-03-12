# Rapport global d’implémentation — Agent Hex V1 à V4

## 1. Contexte et objectif du projet

Le projet consiste à construire un agent Hex compétitif sur un plateau 14x14, en Python, sous contrainte de temps globale. Le cadre du cours valorise une progression incrémentale : partir d’un agent simple, puis ajouter des améliorations mesurées et justifiées.

Dans cette optique, l’évolution V1 → V4 a permis d’identifier une leçon centrale : **dans ce projet, la qualité d’un agent dépend autant de la force théorique de ses idées que de leur rentabilité en temps de calcul**.

Autrement dit, une heuristique un peu moins sophistiquée mais très rapide peut être meilleure en pratique qu’un système riche en concepts mais trop coûteux.

---

## 2. Philosophie générale de développement

La progression a suivi quatre étapes :

- **V1** : poser une base solide de recherche adversarielle.
- **V2** : enrichir cette base avec des optimisations classiques de moteur de jeu.
- **V3** : tester des idées plus structurelles et tactiques propres à Hex.
- **V4** : revenir à une architecture compacte et rapide, recentrée sur ce qui produit réellement des gains dans le cadre du projet.

Cette trajectoire est cohérente avec :
- le **module 1**, qui met l’accent sur la modélisation et la construction d’heuristiques ;
- le **module 2**, consacré à minimax, alpha-bêta et aux améliorations de recherche adversarielle ;
- le **module 4**, qui met en avant la réduction de l’espace de recherche.

---

## 3. Version 1 — Fondation simple et correcte

### 3.1 Idée principale

La V1 repose sur deux composants :

1. **Minimax avec élagage alpha-bêta**
2. **Heuristique de connectivité par Dijkstra**

L’heuristique considère que :
- une case alliée coûte 0 ;
- une case vide coûte 1 ;
- une case ennemie est bloquante.

L’évaluation compare ensuite :

**Score = Distance adversaire − Distance moi**

Cette idée est très naturelle pour Hex, car le but du jeu n’est pas de capturer des pièces mais de **former une connexion**.

### 3.2 Justification théorique

- **[module 1]** : le plateau est modélisé comme un problème de recherche sur graphe.
- **[module 2]** : l’arbre de jeu est exploré avec minimax et alpha-bêta, ce qui permet d’éviter une recherche exhaustive impossible.

### 3.3 Forces

- Très simple à comprendre et à justifier.
- Coût d’évaluation relativement modéré.
- Bonne base pour ajouter des améliorations.

### 3.4 Limites

- Profondeur fixe trop faible.
- Pas de gestion fine du temps.
- Heuristique encore trop naïve pour capturer certaines structures locales de Hex.

---

## 4. Version 2 — Enrichissement classique du moteur

### 4.1 Objectif

La V2 visait à rendre l’agent plus fort sans changer de paradigme. L’idée était d’ajouter les briques classiques d’un moteur de recherche adversarielle plus sérieux.

### 4.2 Ajouts principaux

#### 4.2.1 Iterative deepening

Au lieu d’une profondeur fixe, la recherche est lancée à profondeur 1, puis 2, puis 3, etc., tant que le temps le permet.

**Pourquoi ?**
- Garantir qu’un coup complet est toujours disponible.
- Mieux exploiter un budget temps variable.
- Favoriser la profondeur réelle atteinte en pratique.

**Source principale** : **[module 2]**

#### 4.2.2 Transposition table

Une table de transposition a été ajoutée pour mémoriser des états déjà vus.

**Pourquoi ?**
- Éviter de recalculer inutilement certaines positions.
- Réutiliser une partie du travail déjà fait.

**Source principale** : **[module 2]**

#### 4.2.3 Move ordering fort

Les coups étaient triés pour essayer de visiter d’abord les plus prometteurs.

**Pourquoi ?**
- Un bon ordre augmente fortement l’efficacité de l’élagage alpha-bêta.

**Source principale** : **[module 2]**

#### 4.2.4 Two-distance améliorée

L’évaluation a été enrichie pour ne pas seulement regarder un unique meilleur chemin de connexion, mais aussi une certaine forme de redondance.

**Pourquoi ?**
- En Hex, un seul chemin court peut être fragile.
- Une connectivité plus robuste est souvent plus informative.

**Source principale** : **[module 1]**, **[module 2]**, et littérature sur Queenbee.

#### 4.2.5 Bridges / save-bridges

Des motifs locaux comme les bridges et les coups de sauvegarde de bridge ont été ajoutés à l’évaluation et au tri des coups.

**Pourquoi ?**
- Les bridges sont des structures centrales du jeu Hex.
- Ils améliorent la robustesse de la connexion.

**Source principale** : littérature Hex (Queenbee / MoHex / virtual connections)

### 4.3 Ce que la V2 a apporté

- meilleure gestion du temps ;
- arbre mieux élagué ;
- meilleure prise en compte de motifs spécifiques à Hex.

### 4.4 Limites constatées

En pratique, cette V2 a aussi révélé un problème : **chaque ajout a un coût**.

Quand trop de logique est intégrée dans :
- l’évaluation,
- le tri des coups,
- la mémoire,

on peut perdre ce qui compte le plus sur ce projet : **la profondeur atteinte sous contrainte de temps**.

---

## 5. Version 3 — Sélection tactique et réduction de l’espace de recherche

### 5.1 Objectif

La V3 cherchait à rendre l’agent plus sélectif et plus tactique.

### 5.2 Ajouts principaux

#### 5.2.1 Mustplay region

Approximation d’une région critique du plateau dans laquelle il faut probablement jouer pour répondre à une menace adverse.

**Idée** : si seuls quelques coups sont vraiment pertinents, on peut réduire le domaine des actions candidates.

**Source principale** : **[module 4]** + littérature sur virtual connections.

#### 5.2.2 Dead cells / captured cells / coups inférieurs simples

Ajout d’heuristiques pour repérer des cases peu utiles ou des coups localement dominés.

**Pourquoi ?**
- Réduire le bruit de recherche.
- Éviter de gaspiller du temps sur des coups peu prometteurs.

**Source principale** : **[module 4]** + littérature sur inferior cells.

#### 5.2.3 Quiescence search et tactical extensions

L’idée était de prolonger légèrement la recherche dans les positions tactiquement instables, au lieu de couper brutalement à profondeur 0.

**Pourquoi ?**
- Réduire l’effet d’horizon.
- Éviter certaines évaluations trompeuses.

**Source principale** : **[module 2]** et littérature générale sur les moteurs de jeu.

### 5.3 Ce que la V3 a montré

Conceptuellement, la V3 allait dans une direction défendable :
- moins de coups inutiles ;
- meilleure attention aux séquences tactiques ;
- meilleure exploitation des idées du module 4.

### 5.4 Problème pratique observé

Cependant, cette version a confirmé un point crucial :

> une amélioration théoriquement bonne peut devenir mauvaise si son coût dépasse son gain.

Dans ce projet, plusieurs idées de V3 étaient trop coûteuses ou trop fragiles pour garantir un gain réel en parties.

---

## 6. Retour critique après confrontation expérimentale

Le tournant est venu du constat suivant : un agent beaucoup plus court, centré sur :
- iterative deepening,
- alpha-bêta,
- Dijkstra rapide,
- bridges,

pouvait battre régulièrement une version beaucoup plus grosse et plus riche conceptuellement.

Cela a conduit à une révision de la stratégie globale.

### Leçon principale

La bonne question n’est pas :

> “Quels concepts puis-je ajouter ?”

mais plutôt :

> “Quels concepts améliorent réellement la force **par milliseconde** ?”

Cette observation est très cohérente avec les moteurs de jeu classiques : un bon moteur n’est pas seulement un moteur intelligent, c’est un moteur qui dépense son temps de calcul de façon rentable.

---

## 7. Version 4 — Recentrage sur la vitesse et la profondeur

### 7.1 Objectif général

La V4 a été conçue comme une réponse directe aux limites des V2/V3.

Le principe directeur est simple :

> **retirer tout ce qui n’apporte pas un gain clair, et concentrer la puissance dans un noyau très rapide.**

La V4 n’essaie donc pas d’être la version la plus riche en concepts. Elle cherche à être la version la plus **efficace** dans le cadre réel du tournoi.

### 7.2 Architecture de la V4

La V4 repose sur cinq blocs principaux.

#### 7.2.1 Iterative deepening [module 2]

La recherche est lancée profondeur par profondeur, avec une deadline stricte.

**Intérêt** :
- garantit une réponse valide ;
- permet de s’arrêter proprement ;
- exploite au mieux le temps disponible.

#### 7.2.2 Alpha-bêta léger [module 2]

Le moteur récursif a été gardé volontairement compact.

**Choix de conception** :
- pas de logique annexe coûteuse dans la boucle principale ;
- vérification du temps simple ;
- structure claire max/min.

L’objectif n’est pas d’avoir l’alpha-bêta le plus sophistiqué, mais un alpha-bêta **très peu coûteux**.

#### 7.2.3 Move ordering compact [module 2]

Le tri des coups reste présent, mais il a été rendu beaucoup plus léger.

Les critères utilisés sont essentiellement :
- centralité ;
- progression sur l’axe de victoire ;
- voisinage allié / ennemi ;
- création, sauvegarde ou blocage de bridges ;
- petit bonus racine basé sur l’effet immédiat sur la distance.

**Idée clé** :
le tri doit aider alpha-bêta **sans coûter trop cher**.

#### 7.2.4 Heuristique recentrée sur la connectivité [module 1]

L’heuristique de la V4 remet le calcul de distance au centre de l’évaluation.

Le signal principal reste :

**distance adverse − distance propre**

mais cette distance est calculée par une version enrichie de Dijkstra.

#### 7.2.5 Dijkstra + bridges + edge templates [module 1] + [source internet]

C’est ici que se trouve la majorité de “l’intelligence utile” de la V4.

Le Dijkstra de la V4 intègre :
- les transitions classiques sur voisins hexagonaux ;
- les **bridges** comme connexions virtuelles rapides ;
- des **templates de bord** pour reconnaître certaines connexions quasi garanties près du bord d’arrivée.

L’idée est de rendre la distance plus fidèle au vrai potentiel de connexion du joueur, **sans multiplier les modules séparés**.

### 7.3 Pourquoi cette V4 est meilleure stratégiquement

La V4 applique une philosophie plus rigoureuse :

- la **distance** reste le signal principal ;
- les motifs Hex servent surtout à améliorer cette distance ;
- les bonus secondaires restent faibles ;
- la boucle de recherche reste rapide.

Cela permet généralement de :
- monter plus profond ;
- obtenir un comportement plus stable ;
- limiter les erreurs dues à des heuristiques secondaires trop agressives.

---

## 8. Justification par les modules

### 8.1 Module 1 — Stratégies de recherche et heuristiques

Le module 1 justifie :
- la modélisation du plateau comme problème de recherche ;
- l’utilisation d’une heuristique de coût ;
- l’importance de construire une heuristique non triviale mais utile.

La V1 puis la V4 s’appuient fortement sur ce module à travers le calcul de connectivité par Dijkstra.

### 8.2 Module 2 — Recherche adversarielle

Le module 2 justifie :
- minimax ;
- alpha-bêta ;
- iterative deepening ;
- l’importance de l’ordre des coups ;
- l’intérêt possible des tables de transposition.

La V2 et la V4 s’inscrivent directement dans ce cadre, avec une préférence finale pour une version plus légère et plus rentable.

### 8.3 Module 4 — Réduction de l’espace de recherche

Le module 4 justifie les tentatives de V3 visant à réduire l’espace de recherche par sélection des coups candidats.

Même si la V4 ne reprend pas toutes ces idées, cette étape a été utile pour comprendre que :
- certaines réductions sont intéressantes ;
- mais leur coût doit être strictement contrôlé.

---

## 9. Justification par les sources externes

### 9.1 Queenbee et la two-distance

Les travaux autour de Queenbee montrent que la notion de **two-distance** est une manière naturelle de mesurer la connectivité dans Hex, plus riche qu’une simple distance de graphe.

Cela a inspiré les enrichissements de V2, même si la V4 revient à une version plus compacte de cette logique.

### 9.2 MoHex / virtual connections / bridges

La littérature sur Hex montre aussi que les **bridges** et plus généralement les **virtual connections** sont centraux pour bien jouer à Hex.

Cela justifie la décision de conserver les bridges dans la V4, mais de les intégrer directement à la métrique de distance au lieu d’en faire un module lourd séparé.

### 9.3 Quiescence search dans les moteurs de jeu

La quiescence search est une idée standard pour éviter l’effet d’horizon. Elle a motivé certaines expérimentations de V3.

Cependant, dans le cadre spécifique de ce projet et avec l’architecture Python choisie, son coût n’a pas semblé suffisamment rentable pour la conserver au cœur de la V4.

---

## 10. Comparaison synthétique des versions

### V1
- **Force** : simple, propre, bonne base.
- **Faiblesse** : profondeur limitée, peu de gestion du temps.

### V2
- **Force** : moteur plus sérieux, plus complet, meilleure intégration des idées du module 2.
- **Faiblesse** : risque de surcharge computationnelle.

### V3
- **Force** : tentative intéressante de réduction sélective de l’espace de recherche.
- **Faiblesse** : coût élevé, sensibilité au calibrage, gain pratique incertain.

### V4
- **Force** : très bon rapport force / coût ; profondeur plus stable ; architecture compacte.
- **Faiblesse** : moins ambitieuse théoriquement que V2/V3 ; certaines idées avancées sont volontairement laissées de côté.

---

## 11. Conclusion générale

L’évolution V1 → V4 montre qu’un bon agent Hex ne se construit pas seulement en accumulant des idées puissantes. Il faut aussi que ces idées soient **compatibles avec le budget temps réel du projet**.

La conclusion principale est donc la suivante :

> la meilleure version n’est pas forcément celle qui contient le plus de concepts, mais celle qui transforme le mieux chaque milliseconde de calcul en qualité de décision.

Dans cette perspective, la V4 constitue la version la plus cohérente à ce stade :
- elle garde les fondations théoriques solides de V1 ;
- elle conserve les apports vraiment rentables de V2 ;
- elle tient compte des leçons apprises avec V3 ;
- et elle recentre l’agent sur une recherche rapide, stable et spécifiquement adaptée à Hex.

---

## 12. Références mobilisées

### Sources du cours
- **[module 1]** M1-strategie-recherche.pdf
- **[module 2]** M2-recherche-adversaire.pdf
- **[module 4]** M4-programmation-par-contraintes.pdf
- Sujet du projet Hex H2026

### Sources externes
- Jack van Rijswijck, *Computer Hex* (Queenbee / two-distance)
- MoHex 2.0, articles sur les virtual connections et bridges
- Chessprogramming Wiki, *Quiescence Search*
