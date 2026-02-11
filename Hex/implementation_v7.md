# Rapport d'Implémentation - Version 7 : Priorité au Centre et Blocage Stratégique

La Version 7 affine le comportement de l'agent en combinant une occupation centrale forte avec des techniques de blocage avancées issues de la théorie du Hex professionnel.

## 1. Domination Centrale (Ouverture)
L'IA valorise le centre du plateau durant les 20 premiers coups. Une pierre centrale offre une flexibilité maximale, permettant de bifurquer vers n'importe quel bord en fonction des réponses adverses.

## 2. Blocage Stratégique : Le "Classic Block"
La grande amélioration de cette version est la gestion de la distance de blocage.

### Le Problème du Blocage Adjacent
Un débutant a tendance à jouer juste à côté de la pierre de tête adverse pour la bloquer. Au Hex, c'est inefficace car l'adversaire peut simplement "couler" autour de la pièce (flow around) en utilisant des connexions en pont ou des décalages.

### La Solution : Bloquer à Distance
L'IA de la V7 utilise une heuristique de "distance de sécurité" :
*   **Pénalité pour le Blocage Adjacent (Distance 1)** : L'IA évite de coller ses pièces à celles de l'adversaire si une meilleure option existe, car cela ne freine pas sa progression.
*   **Bonus pour le "Classic Block" (Distance 2 ou 3)** : L'IA préfère placer une pierre à une ou deux cases de distance sur le chemin probable de l'adversaire. 
    *   **Avantage** : Cela crée une zone d'influence que l'adversaire ne peut pas contourner facilement sans rencontrer une autre pièce défensive. Cela donne à l'IA un temps d'avance pour consolider son mur.

## 3. Panic Mode et Défense des Bords
Hérité de la V6, le mode panique s'active dès qu'une pierre adverse approche des bords cibles. L'IA combine alors le blocage à distance avec une obstruction directe et massive pour empêcher la connexion finale.

## 4. Move Ordering et Efficacité
Le tri des coups intègre désormais ces biais : les cases centrales et les positions de "blocage classique" sont explorées en premier dans l'arbre Alpha-Béta, garantissant une recherche de haute qualité même à faible profondeur.

## 5. Conclusion sur la V7
L'agent V7 ne se contente plus de chercher le chemin le plus court ; il joue avec une conscience tactique du positionnement adverse. Il sait quand il est temps de contester le centre, quand il faut reculer pour mieux bloquer, et quand il faut construire un mur infranchissable sur ses propres bordures.
