"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
suppPartieSupperpose.py(Ɔ) 2023
Description : supprimer la partie ou des traits se superposent.
Créé le :  jeudi 19 janvier 2023, 10:43:40 
Dernière modification : jeudi 19 janvier 2023, 10:44:48"""

import inkex
import simplestyle


class RemoveOverlap(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def effect(self):
        # Récupération de tous les éléments de type trait
        lines = self.document.xpath('//svg:line', namespaces=inkex.NSS)
        if len(lines) < 2:
            inkex.errormsg("You need at least two lines to use this effect")
            return
        for i in range(len(lines)):
            x1 = float(lines[i].get("x1"))
            y1 = float(lines[i].get("y1"))
            x2 = float(lines[i].get("x2"))
            y2 = float(lines[i].get("y2"))
            for j in range(i+1, len(lines)):
                x3 = float(lines[j].get("x1"))
                y3 = float(lines[j].get("y1"))
                x4 = float(lines[j].get("x2"))
                y4 = float(lines[j].get("y2"))
                #calcul de l'intersection
                x, y = self.lines_intersection(x1, y1, x2, y2, x3, y3, x4, y4)
                if x and y:
                    #calcul de la distance entre les deux points d'intersection
                    dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
                    dist2 = ((x4 - x3)**2 + (y4 - y3)**2)**0.5
                    #suppression de la partie superposée
                    if dist < dist2:
                        lines[i].getparent().remove(lines[i])
                    else:
                        lines[j].getparent().remove(lines[j])

    def lines_intersection(self, x1, y1, x2, y2, x3, y3, x4, y4):
        #calcul des coefficients pour les équations des droites
        a1 = y2 - y1
        b1 = x1 - x2
        c1 = a1 * x1 + b1 * y1
        a2 = y4 - y3
        b2 = x3 - x4
        c2 = a2 * x3 + b2 * y3
        determinant = a1 * b2 - a2 * b1
        if determinant == 0:
            return None, None
        else:
            x = (b2 * c1 - b1 * c2) / determinant
            y = (a1 * c2 - a2 * c1) / determinant
            return x, y
