"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
SuppTraitsPaths.py(Ɔ) 2023
Description : supprimer les chemins superposés
Créé le :  jeudi 19 janvier 2023, 10:39:09 
Dernière modification : jeudi 19 janvier 2023, 10:39:37"""

# ne vérifie pas si les chemins sont vraiment superposés, mais seulement si leur "d" est identique

import inkex
import simplestyle


class RemoveOverlappingPaths(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        # Récupération de tous les chemins
        paths = self.document.xpath('//svg:path', namespaces=inkex.NSS)

        # Création d'un dictionnaire pour stocker les chemins déjà vus
        seen_paths = {}

        # Boucle sur tous les chemins
        for path in paths:
            # Récupération des données du chemin
            path_data = path.get('d')

            # Création d'une clé pour stocker le chemin dans le dictionnaire
            path_key = path_data

            # Si le chemin a déjà été vu, on le supprime
            if path_key in seen_paths:
                path.getparent().remove(path)
            else:
                # Sinon, on l'ajoute au dictionnaire des chemins déjà vus
                seen_paths[path_key] = True
