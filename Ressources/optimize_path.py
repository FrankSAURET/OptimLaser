"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
optimize_path.py(Ɔ) 2023
Description : Optimisation de la découpe laser
Créé le :  jeudi 19 janvier 2023, 10:14:34 
Dernière modification : jeudi 19 janvier 2023, 10:15:06"""


def optimize_path(points):
  # trier les points par ordre de distance croissante à l'origine (0,0)
  points.sort(key=lambda p: p[0]**2 + p[1]**2)

  # initialiser le chemin optimisé avec le premier point
  optimized_path = [points[0]]

  # itérer sur les points restants
  for i in range(1, len(points)):
    # récupérer le dernier point du chemin optimisé
    last_point = optimized_path[-1]

    # trouver le point le plus proche parmi les points restants
    closest_point = min(points[i:], key=lambda p: ((p[0]-last_point[0])**2 + (p[1]-last_point[1])**2))

    # ajouter le point le plus proche au chemin optimisé
    optimized_path.append(closest_point)

  # retourner le chemin optimisé
  return optimized_path
