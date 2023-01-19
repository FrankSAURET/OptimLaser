"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
ConvertitEnPath.py(Ɔ) 2023
Description : modifier tous les élément dessinnés en path simple
Créé le :  jeudi 19 janvier 2023, 10:42:28 
Dernière modification : jeudi 19 janvier 2023, 10:48:47"""

import inkex
import simplestyle


def convert_to_path(file_path):
    # Chargement du fichier SVG
    svg = inkex.etree.parse(file_path).getroot()

    # Récupération de tous les éléments
    elements = svg.xpath(
        "//*[name()='svg:line' or name()='svg:rect' or name()='svg:circle' or name()='svg:ellipse' or name()='svg:polyline' or name()='svg:polygon']")

    # Boucle sur tous les éléments
    for element in elements:
        parent = element.getparent()
        if element.tag.endswith("line"):
            x1 = float(element.get("x1"))
            y1 = float(element.get("y1"))
            x2 = float(element.get("x2"))
            y2 = float(element.get("y2"))
            path_data = f"M {x1} {y1} L {x2} {y2}"
        elif element.tag.endswith("rect"):
            x = float(element.get("x"))
            y = float(element.get("y"))
            width = float(element.get("width"))
            height = float(element.get("height"))
            path_data = f"M {x} {y} h {width} v {height} h -{width} Z"
        elif element.tag.endswith("circle"):
            cx = float(element.get("cx"))
            cy = float(element.get("cy"))
            r = float(element.get("r"))
            path_data = f"M {cx - r} {cy} a {r} {r} 0 1 0 {r*2} 0 a {r} {r} 0 1 0 -{r*2} 0"
        
        elif element.tag.endswith("ellipse"):
            cx = float(element.get("cx"))
            cy = float(element.get("cy"))
            rx = float(element.get("rx"))
            ry = float(element.get("ry"))
            path_data = f"M {cx - rx} {cy} a {rx} {ry} 0 1 0 {rx*2} 0 a {rx} {ry} 0 1 0 -{rx*2} 0"
        elif element.tag.endswith("polyline") or element.tag.endswith("polygon"):
            points = element.get("points")
            path_data = f"M {points.replace(' ', ' L ')}"
            if element.tag.endswith("polygon"):
                path_data += " Z"
        else:
            continue
        new_path = inkex.etree.Element(inkex.addNS("path", "svg"))
        new_path.set("d", path_data)
        style = simplestyle.formatStyle(element.attrib)
        if style:
            new_path.set("style", style)
        parent.replace(element, new_path)



