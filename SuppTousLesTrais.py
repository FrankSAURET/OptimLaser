"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
SuppTousLesTrais.py(Ɔ) 2023
Description : supprimer absolument tous les traits superposés d'un dessin SVG
Créé le :  jeudi 19 janvier 2023, 10:40:56 
Dernière modification : jeudi 19 janvier 2023, 10:41:31"""

import inkex
import simplestyle


class RemoveOverlapping(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        # Récupération de tous les éléments de type trait
        elements = self.document.xpath('//svg:line | //svg:path | //svg:polyline | //svg:polygon', namespaces=inkex.NSS)

        # Création d'un dictionnaire pour stocker les éléments déjà vus
        seen_elements = {}

        # Boucle sur tous les éléments
        for element in elements:
            # Récupération des données de l'élément
            element_data = element.get('d') if element.tag.endswith("path") else (element.get('points') if element.tag.endswith(
                "poly") else (element.get('x1'), element.get('y1'), element.get('x2'), element.get('y2')))

            # Création d'une clé pour stocker l'élément dans le dictionnaire
            element_key = str(element_data)

            # Si l'élément a déjà été vu, on le supprime
            if element_key in seen_elements:
                element.getparent().remove(element)
            else:
                # Sinon, on l'ajoute au dictionnaire des éléments déjà vus
                seen_elements[element_key] = True
