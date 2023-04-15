"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
TraitSupp.py(Ɔ) 2023
Description : supprime les traits superposés dans un fichier SVG
Créé le :  jeudi 19 janvier 2023, 10:36:58 
Dernière modification : jeudi 19 janvier 2023, 10:38:13"""

import inkex
import simplestyle


class RemoveOverlappingLines(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        # Récupération de toutes les lignes
        lines = self.document.xpath('//svg:line', namespaces=inkex.NSS)

        # Création d'un dictionnaire pour stocker les lignes déjà vues
        seen_lines = {}

        # Boucle sur toutes les lignes
        for line in lines:
            # Récupération des coordonnées de départ et d'arrivée de la ligne
            x1 = float(line.get('x1'))
            y1 = float(line.get('y1'))
            x2 = float(line.get('x2'))
            y2 = float(line.get('y2'))

            # Création d'une clé pour stocker la ligne dans le dictionnaire
            line_key = str((x1, y1, x2, y2))

            # Si la ligne a déjà été vue, on la supprime
            if line_key in seen_lines:
                line.getparent().remove(line)
            else:
                # Sinon, on l'ajoute au dictionnaire des lignes déjà vues
                seen_lines[line_key] = True
