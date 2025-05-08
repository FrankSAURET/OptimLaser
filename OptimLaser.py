#!/usr/bin/env/python
'''
Codé par Frank SAURET et Copilot janvier 2023 - mai 2025

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
'''

# Optimisation avant découpe laser
# - Décomposition en éléments simples
# - Suppression des traits superposés (sauf les courbes de bezier)
# - Classement des chemins pour optimiser le déplacement de la tête de découpe laser
# - sauvegarde avant et aprés dans 2 fichiers séparés
# - Ajout d'un fichier ini qui contient une liste des couleurs de la découpeuse laser
# - Suppression (possible) des traits non découpables (de couleurs non gérés pas la découpe laser)

# Todo
# - Revoir la gestion du kill des processus inkscape essayer de ne fermer que l'instance du fichier de découpe ou faire un enregistrer sous si l'api l'implémente

# Versions
#  0.1 Janvier 2023
#  0.2 juin 2024
#  0.2.2 octobre 2024
# 2024.1 novembre 2024 juste le versionnage
# 2025.1 23 Février 2025 Correction d'un bug
# 2025.2 Avril 2025 Correction de bugs Réécriture de la fonction de détection de chevauchement réécriture de la fonction d'optimisation de l'ordre de découpe.
# 2025.3 Mai 2025 Correction de traitement des chemins complexes. Suppression de la gestion des chevauchement pour les courbes de beziers qui ne marchait pas vraiment bien. Réécriture de la gestion des ellipses et arcs. Optimisation du traitement.

__version__ = "2025.3"

import os
import subprocess
import inkex
import re
import math
from tkinter import messagebox
import platform
from datetime import datetime
import warnings
import copy
from lxml import etree

class OptimLaser(inkex.EffectExtension):
    def __init__(self):
        self.ListeDeGris = []
        self.numeroChemin = 0
        self._distance_cache = {}
        inkex.Effect.__init__(self)
        self.arg_parser.add_argument("--tab",
            type=str,
            dest="tab",
            default="options")
        self.arg_parser.add_argument("-S","--SauvegarderSousDecoupe",
            type=inkex.Boolean,
            dest="SauvegarderSousDecoupe",
            default=True)
        self.arg_parser.add_argument("--SupprimerCouleursNonGerees",
            type=inkex.Boolean,
            dest="SupprimerCouleursNonGerees",
            default=True)
        self.arg_parser.add_argument("-t","--tolerance",
            type=float,
            dest="tolerance",
            default="0.15")

    
    def get_path_envelope(self, path, tolerance=0.0):
        """Crée une enveloppe autour d'un chemin simple (M + A/Q/C/L) avec une tolérance donnée
        
        Args:
            path: Le chemin inkex.Path à envelopper
            tolerance: Épaisseur de l'enveloppe (valeur par défaut: 0)
            
        Returns:
            Un chemin inkex.Path représentant l'enveloppe du chemin original
        """
        if not isinstance(path, inkex.Path) or len(path) < 2:
            return path  # Retourne le chemin original si invalide
        
        # Extraire la commande M (déplacement initial) et la commande de dessin
        move_cmd = path[0]
        draw_cmd = path[1]
        
        if move_cmd.letter != 'M':
            return path  # Retourne le chemin original si format inattendu
        
        # Point de départ
        start_x, start_y = move_cmd.x, move_cmd.y
        
        # Nouvelle enveloppe (chemin fermé)
        envelope = inkex.Path()
        
        # Vecteurs normaux pour créer l'enveloppe
        if draw_cmd.letter == 'L':  # Ligne
            end_x, end_y = draw_cmd.x, draw_cmd.y
            
            # Vecteur de direction
            dx = end_x - start_x
            dy = end_y - start_y
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0:
                # Vecteur normal (perpendiculaire)
                nx = -dy / length * tolerance
                ny = dx / length * tolerance
                
                # Points de l'enveloppe (rectangle)
                p1 = (start_x + nx, start_y + ny)
                p2 = (end_x + nx, end_y + ny)
                p3 = (end_x - nx, end_y - ny)
                p4 = (start_x - nx, start_y - ny)
                
                # Création du chemin de l'enveloppe
                envelope.append(inkex.paths.Move(*p1))
                envelope.append(inkex.paths.Line(*p2))
                envelope.append(inkex.paths.Line(*p3))
                envelope.append(inkex.paths.Line(*p4))
                envelope.append(inkex.paths.ZoneClose())
            else:
                # Point unique, créer un cercle
                envelope.append(inkex.paths.Move(start_x + tolerance, start_y))
                envelope.append(inkex.paths.Arc(tolerance, tolerance, 0, 0, 1, start_x - tolerance, start_y))
                envelope.append(inkex.paths.Arc(tolerance, tolerance, 0, 0, 1, start_x + tolerance, start_y))
                envelope.append(inkex.paths.ZoneClose())
            
        elif draw_cmd.letter == 'A':  # Arc
            # Créer une version épaissie de l'arc
            rx, ry = draw_cmd.rx, draw_cmd.ry
            x_axis_rotation = draw_cmd.x_axis_rotation  # Correction: utiliser x_axis_rotation au lieu de rotation
            large_arc = draw_cmd.large_arc
            sweep = draw_cmd.sweep
            end_x, end_y = draw_cmd.x, draw_cmd.y
            
            # Arc extérieur (plus grand rayon)
            outer_rx = rx + tolerance
            outer_ry = ry + tolerance
            
            # Arc intérieur (plus petit rayon)
            inner_rx = max(0.1, rx - tolerance)  # Éviter les rayons négatifs
            inner_ry = max(0.1, ry - tolerance)  # Éviter les rayons négatifs
            
            # Créer l'enveloppe avec les deux arcs
            envelope.append(inkex.paths.Move(start_x, start_y))
            envelope.append(inkex.paths.Arc(outer_rx, outer_ry, x_axis_rotation, large_arc, sweep, end_x, end_y))
            envelope.append(inkex.paths.Arc(inner_rx, inner_ry, x_axis_rotation, large_arc, 1-sweep, start_x, start_y))
            envelope.append(inkex.paths.ZoneClose())
            
        elif draw_cmd.letter == 'C':  # Courbe cubique de Bézier
            # Pour les courbes de Bézier, nous échantillonnons des points
            # et créons une série de segments pour approximer l'enveloppe
            end_x, end_y = draw_cmd.x2, draw_cmd.y2  # Point final
            
            # Accéder directement aux attributs de contrôle pour les courbes cubiques
            if hasattr(draw_cmd, 'x1') and hasattr(draw_cmd, 'y1') and hasattr(draw_cmd, 'x2') and hasattr(draw_cmd, 'y2'):
                control1_x, control1_y = draw_cmd.x1, draw_cmd.y1  # Premier point de contrôle
                control2_x, control2_y = draw_cmd.x2, draw_cmd.y2  # Second point de contrôle
            else:
                # Fallback si les attributs standard ne sont pas disponibles
                control1_x, control1_y = (start_x * 2 + end_x) / 3, (start_y * 2 + end_y) / 3
                control2_x, control2_y = (start_x + end_x * 2) / 3, (start_y + end_y * 2) / 3
            
            # Échantillonnage de points le long de la courbe
            points = []
            steps = 20  # Plus de points pour une meilleure précision
            
            for i in range(steps + 1):
                t = i / steps
                mt = 1 - t
                
                # Formule paramétrique pour une courbe de Bézier cubique
                x = mt**3 * start_x + 3 * mt**2 * t * control1_x + 3 * mt * t**2 * control2_x + t**3 * end_x
                y = mt**3 * start_y + 3 * mt**2 * t * control1_y + 3 * mt * t**2 * control2_y + t**3 * end_y
                
                # Calcul de la dérivée pour obtenir la tangente
                tx = -3 * mt**2 * start_x + 3 * (1 - 4*t + 3*t**2) * control1_x + 3 * (2*t - 3*t**2) * control2_x + 3 * t**2 * end_x
                ty = -3 * mt**2 * start_y + 3 * (1 - 4*t + 3*t**2) * control1_y + 3 * (2*t - 3*t**2) * control2_y + 3 * t**2 * end_y
                
                # Normalisation de la tangente
                len_t = math.sqrt(tx**2 + ty**2)
                if len_t > 0:
                    nx = -ty / len_t * tolerance
                    ny = tx / len_t * tolerance
                    
                    # Points extérieur et intérieur
                    points.append(((x + nx, y + ny), (x - nx, y - ny)))
            
            # Créer le chemin de l'enveloppe
            if points:
                # Contour extérieur (aller)
                envelope.append(inkex.paths.Move(*points[0][0]))
                
                for i in range(1, len(points)):
                    envelope.append(inkex.paths.Line(*points[i][0]))
                
                # Contour intérieur (retour)
                for i in range(len(points)-1, -1, -1):
                    envelope.append(inkex.paths.Line(*points[i][1]))
                    
                envelope.append(inkex.paths.ZoneClose())
            
        elif draw_cmd.letter == 'Q':  # Courbe quadratique de Bézier
            # Similaire à la courbe cubique, mais avec un seul point de contrôle
            end_x, end_y = draw_cmd.x, draw_cmd.y  # Point final
            
            # Accéder directement aux attributs de contrôle pour les courbes quadratiques
            if hasattr(draw_cmd, 'x1') and hasattr(draw_cmd, 'y1'):
                control_x, control_y = draw_cmd.x1, draw_cmd.y1  # Point de contrôle
            else:
                # Fallback si les attributs standard ne sont pas disponibles
                control_x, control_y = (start_x + end_x) / 2, (start_y + end_y) / 2
            
            # Échantillonnage de points le long de la courbe
            points = []
            steps = 20  # Plus de points pour une meilleure précision
            
            for i in range(steps + 1):
                t = i / steps
                mt = 1 - t
                
                # Formule paramétrique pour une courbe de Bézier quadratique
                x = mt**2 * start_x + 2 * mt * t * control_x + t**2 * end_x
                y = mt**2 * start_y + 2 * mt * t * control_y + t**2 * end_y
                
                # Calcul de la dérivée pour obtenir la tangente
                tx = -2 * mt * start_x + 2 * (1 - 2*t) * control_x + 2 * t * end_x
                ty = -2 * mt * start_y + 2 * (1 - 2*t) * control_y + 2 * t * end_y
                
                # Normalisation de la tangente
                len_t = math.sqrt(tx**2 + ty**2)
                if len_t > 0:
                    nx = -ty / len_t * tolerance
                    ny = tx / len_t * tolerance
                    
                    # Points extérieur et intérieur
                    points.append(((x + nx, y + ny), (x - nx, y - ny)))
            
            # Créer le chemin de l'enveloppe
            if points:
                # Contour extérieur (aller)
                envelope.append(inkex.paths.Move(*points[0][0]))
                
                for i in range(1, len(points)):
                    envelope.append(inkex.paths.Line(*points[i][0]))
                
                # Contour intérieur (retour)
                for i in range(len(points)-1, -1, -1):
                    envelope.append(inkex.paths.Line(*points[i][1]))
                    
                envelope.append(inkex.paths.ZoneClose())
        
        return envelope
    
    def find_layer(self, element):
        while element is not None:
            if isinstance(element, etree._Element):
                if element.tag == inkex.addNS('g', 'svg') and element.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    return element
            element = element.getparent()
        return None

    def custom_to_path_element(self, element):
        """
        Convertit un élément en chemin (path). 
        Pour les ellipses, découpe systématiquement en 4 arcs de 90°.
        Pour les autres formes, utilise la méthode to_path_element() standard d'inkex.
        
        Args:
            element: L'élément à convertir en chemin
        
        Returns:
            Un élément de type PathElement
        """
        # Si l'élément est une ellipse, la découper en 4 arcs
        if isinstance(element, inkex.Ellipse):
            # Récupérer les propriétés de l'ellipse
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            rx = float(element.get('rx', 0))
            ry = float(element.get('ry', 0))
            
            # Créer un nouveau chemin avec 4 arcs de 90°
            path = inkex.Path()
            
            # Points cardinaux de l'ellipse (Est, Nord, Ouest, Sud)
            east = (cx + rx, cy)
            north = (cx, cy - ry)
            west = (cx - rx, cy)
            south = (cx, cy + ry)
            
            # Créer les 4 arcs de 90°
            path.append(inkex.paths.Move(*east))  # Partir du point Est
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *north))  # Arc Est -> Nord
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *west))   # Arc Nord -> Ouest
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *south))  # Arc Ouest -> Sud
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *east))   # Arc Sud -> Est
            
            # Créer le nouvel élément de chemin
            path_element = inkex.PathElement()
            path_element.path = path
            
            # Copier le style et les autres attributs de l'ellipse originale
            path_element.style = element.style
            
            # Copier les transformations
            if 'transform' in element.attrib:
                path_element.set('transform', element.get('transform'))
                
            # Copier l'ID ou en créer un nouveau
            path_element.set('id', element.get('id', 'path-' + str(id(path_element))))
            
            return path_element
        else:
            # Pour tous les autres types d'éléments, utiliser la méthode standard
            return element.to_path_element()

    def ungroup_and_apply_transform_to_children(self):
        """Décompose les groupes et applique la transformation à leurs enfants"""
        Nouvelle_selection = []
        elements_to_process = [elem for elem in self.svg.descendants()
                            if not isinstance(elem, inkex.TextElement)]

        def recursive_ungroup(element):
            """Décompose les groupes et applique la transformation à leurs enfants"""
            children_to_process = []
            for child in element.getchildren():
                if isinstance(child, inkex.Group):
                    for grandchild in child.getchildren():
                        if hasattr(grandchild, 'to_path_element'):
                            grandchild = self.custom_to_path_element(grandchild)
                            grandchild.path = grandchild.path.transform(grandchild.transform)
                            grandchild.path = grandchild.path.transform(child.transform)
                            grandchild.attrib.pop('transform', None)
                            parent_style = inkex.Style(child.attrib.get('style', ''))
                            child_style = inkex.Style(grandchild.attrib.get('style', ''))
                            for key, value in parent_style.items():
                                if key not in child_style or child_style[key] is None:
                                    child_style[key] = value
                            grandchild.attrib['style'] = str(child_style)
                        element.append(grandchild)
                        children_to_process.append(grandchild)
                    element.remove(child)
                else:
                    if hasattr(child, 'to_path_element'):
                        child = self.custom_to_path_element(child)
                        parent_style = inkex.Style(element.attrib.get('style', ''))
                        child_style = inkex.Style(child.attrib.get('style', ''))
                        for key, value in parent_style.items():
                            if key not in child_style or child_style[key] is None:
                                child_style[key] = value
                        child.attrib['style'] = str(child_style)
                        children_to_process.append(child)
                        Nouvelle_selection.append(child)
            return children_to_process

        while elements_to_process:
            current_element = elements_to_process.pop()
            if isinstance(current_element, inkex.Group):
                elements_to_process.extend(recursive_ungroup(current_element))

        for element in self.svg.descendants():
            if isinstance(element, (inkex.Circle, inkex.Ellipse, inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon)):
                if hasattr(element, 'to_path_element'):
                    parent = element.getparent()
                    new_path = self.custom_to_path_element(element)
                    if 'transform' in element.attrib:
                        transform = inkex.Transform(element.get('transform'))
                        new_path.path = new_path.path.transform(transform)
                        new_path.attrib.pop('transform', None)
                    if parent is not None:
                        parent.replace(element, new_path)
                        Nouvelle_selection.append(new_path)

    def replace_with_subpaths(self):
        """Remplace les chemins complexes par des segments simples"""
        self.numeroChemin = 0

        for element in self.svg.descendants():
            if (isinstance(element, (inkex.PathElement, inkex.Circle, inkex.Ellipse,
                                inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon))
                and not any('font' in str(value).lower() for value in element.style.values())):
                parent = element.getparent()
                couche = self.find_layer(element)
                style = element.style
                fill_value = style.get('fill', None)
                if fill_value and fill_value.lower() != 'none':
                    fill_color = inkex.Color(style('fill', None))
                    r, v, b = fill_color.to_rgb()
                    if (r == v and r == b and v == b):
                        self.ListeDeGris.append(copy.deepcopy(element))
                    style['fill'] = 'none'

                if isinstance(element, inkex.PathElement) and 'transform' in element.attrib:
                    path = element.path
                    transform = inkex.Transform(element.get('transform'))
                    path = path.transform(transform)
                    element.attrib.pop('transform', None)
                    element.path = path

                path = element.path.to_non_shorthand()

                if len(path) > 0:
                    segments = iter(path)
                    segmentPrev = next(segments)
                    Premier = segmentPrev
                    for segment in segments:
                        if segment.letter != 'Z':
                            debut = segmentPrev.end_point(None, None)
                            fin = segment.end_point(None, None)
                            segment_path = inkex.Path([inkex.paths.Move(*debut)] + [segment])
                            segmentPrev = segment
                        else:
                            if segmentPrev.letter=='C':
                                debut = (round(segmentPrev.x4, 6), round(segmentPrev.y4, 6))
                            elif segmentPrev.letter=='Q':
                                debut = (round(segmentPrev.x3, 6), round(segmentPrev.y3, 6))
                            else:
                                debut = (round(segmentPrev.x, 6), round(segmentPrev.y, 6))
                            fin = (round(Premier.x, 6), round(Premier.y, 6))
                            segment_path = inkex.Path([inkex.paths.Move(*debut)] + [inkex.paths.Line(*fin)])

                        if debut != fin:
                            self.numeroChemin += 1
                            new_element = inkex.PathElement(
                                id=f"chemin{self.numeroChemin}",
                                d=str(segment_path),
                                style=str(style),
                                transform=str(element.transform)
                            )

                            path_commands = [cmd.letter for cmd in new_element.path]
                            if not all(cmd == 'M' for cmd in path_commands):
                                if couche is not None:
                                    couche.append(new_element)
                                else:
                                    self.document.getroot().append(new_element)

                    parent.remove(element)

    def get_path_endpoints(self, element):
        """Retourne les points de début et fin d'un chemin selon son type"""
        if not isinstance(element, inkex.PathElement):
            return None, None

        path = list(element.path)
        if not path:
            return None, None

        # Point de début (toujours la commande M)
        start = (float(path[0].x), float(path[0].y))

        # Point de fin selon le type de la dernière commande
        last_cmd = path[-1]
        end = None

        if last_cmd.letter == 'L':  # Ligne
            end = (float(last_cmd.x), float(last_cmd.y))

        elif last_cmd.letter == 'A':  # Arc
            end = (float(last_cmd.x), float(last_cmd.y))

        elif last_cmd.letter == 'C':  # Courbe cubique de Bézier
            end = (float(last_cmd.x3), float(last_cmd.y3))

        elif last_cmd.letter == 'Q':  # Courbe quadratique de Bézier
            end = (float(last_cmd.x2), float(last_cmd.y2))

        elif last_cmd.letter == 'Z':  # Si le chemin est fermé
            end = start

        return start, end

    def order_paths(self):
        """Trie les chemins pour optimiser le déplacement de la tête de découpe laser.
        Les chemins sont triés par couleur selon l'ordre défini dans OptimLaser.ini."""
        import numpy as np
        from collections import defaultdict

        # Lecture de l'ordre des couleurs depuis le fichier INI
        ini_path = os.path.join(os.path.dirname(__file__), 'OptimLaser.ini')

        default_color_order = ['000000', 'ff0000', '0000ff', '336699', '00ffff', '00ff00', '009933', '006633', '999933', '996633', '663300', '660066', '9900cc', 'ff00ff', 'ff6600', 'ffff00']
        color_order = []
        try:
            with open(ini_path, 'r') as ini_file:
                for line in ini_file:
                    if line.strip().startswith('order'):
                        color_order = line.split('=')[1].strip().split(',')
                        color_order = [color.strip().lower() for color in color_order]
                        break
        except:
            color_order = default_color_order

        # Dictionnaire pour accélérer la recherche d'index
        color_rank_dict = {color: i for i, color in enumerate(color_order)}

        # Collecte tous les chemins avec leurs informations en une seule passe
        paths_by_color = defaultdict(list)
        elements_to_remove = []

        for element in self.svg.descendants():
            if isinstance(element, inkex.PathElement) and element.get('d') is not None:
                stroke_color = element.style.get('stroke', '#000000').lower()
                if stroke_color.startswith('#'):
                    stroke_color = stroke_color[1:]

                # Vérifier si la couleur est gérée
                if stroke_color not in color_order and self.options.SupprimerCouleursNonGerees:
                    continue

                start, end = self.get_path_endpoints(element)

                # Ignorer les chemins sans points de début ou de fin valides
                if start is None or end is None:
                    continue

                # Structure de données optimisée pour chaque chemin
                path_data = {
                    'element': element,
                    'id': element.get('id'),
                    'start': start,
                    'end': end,
                    'color': stroke_color,
                    'color_rank': color_rank_dict.get(stroke_color, len(color_order)),
                    'parent': element.getparent()
                }

                # Regrouper directement par couleur pour éviter un tri ultérieur
                paths_by_color[stroke_color].append(path_data)
                elements_to_remove.append((element, element.getparent()))

        # Si aucun chemin n'est trouvé, on termine
        if not paths_by_color:
            return

        # Supprimer les éléments en une seule passe pour éviter de modifier la structure pendant l'itération
        for element, parent in elements_to_remove:
            if parent is not None:
                parent.remove(element)

        # Fonction optimisée pour trouver le chemin le plus proche avec vectorisation complète
        def nearest_neighbor_tsp_optimized(paths, start_point=(0, 0)):
            """Algorithme du plus proche voisin optimisé avec numpy"""
            if not paths:
                return []

            # Pré-calcul des points de début et de fin pour éviter les accès répétés
            n = len(paths)
            starts = np.array([p['start'] for p in paths])
            ends = np.array([p['end'] for p in paths])

            # Utilisation d'un tableau d'indices pour un accès rapide
            remaining = np.ones(n, dtype=bool)  # Tableau booléen pour les chemins restants
            route = []
            current_point = np.array(start_point)

            for _ in range(n):
                if not np.any(remaining):
                    break

                # Calcul vectorisé des distances (uniquement pour les chemins restants)
                remaining_idx = np.where(remaining)[0]

                # Calcul plus efficace des distances euclidiennes
                start_diff = starts[remaining_idx] - current_point
                end_diff = ends[remaining_idx] - current_point

                # Calcul des distances au carré (évite la racine carrée pour la comparaison)
                start_distances_sq = np.sum(start_diff * start_diff, axis=1)
                end_distances_sq = np.sum(end_diff * end_diff, axis=1)

                # Trouver l'index du chemin le plus proche
                min_start_idx = np.argmin(start_distances_sq)
                min_end_idx = np.argmin(end_distances_sq)

                if start_distances_sq[min_start_idx] <= end_distances_sq[min_end_idx]:
                    # Le point de départ est plus proche
                    nearest_idx = remaining_idx[min_start_idx]
                    invert = False
                    current_point = ends[nearest_idx]
                else:
                    # Le point de fin est plus proche
                    nearest_idx = remaining_idx[min_end_idx]
                    invert = True
                    current_point = starts[nearest_idx]

                # Marquer ce chemin comme visité
                remaining[nearest_idx] = False
                route.append((paths[nearest_idx], invert))

            return route

        # Optimiser l'ordre de découpe pour chaque couleur
        final_ordered_paths = []
        current_point = (0, 0)  # Point de départ de la tête de découpe

        # Traiter les couleurs dans l'ordre défini
        for color in color_order:
            if color in paths_by_color:
                color_paths = paths_by_color[color]
                ordered_paths_with_invert = nearest_neighbor_tsp_optimized(color_paths, current_point)

                if ordered_paths_with_invert:
                    last_path, inverted = ordered_paths_with_invert[-1]
                    current_point = last_path['start'] if inverted else last_path['end']

                final_ordered_paths.extend([p for p, _ in ordered_paths_with_invert])

        # Ajouter les chemins d'autres couleurs à la fin si l'option de suppression n'est pas activée
        if not self.options.SupprimerCouleursNonGerees:
            for color in paths_by_color:
                if color not in color_order:
                    color_paths = paths_by_color[color]
                    ordered_paths_with_invert = nearest_neighbor_tsp_optimized(color_paths, current_point)

                    if ordered_paths_with_invert:
                        last_path, inverted = ordered_paths_with_invert[-1]
                        current_point = last_path['start'] if inverted else last_path['end']

                    final_ordered_paths.extend([p for p, _ in ordered_paths_with_invert])

        # Réinsérer les chemins dans le document dans l'ordre optimisé
        for i, path_data in enumerate(final_ordered_paths, start=1):
            parent = path_data['parent']
            element = path_data['element']
            element.set('id', f"chemin{i}")
            parent.append(element)

    def adjust_overlapping_segments(self):
        """Identifie et ajuste les chemins qui se chevauchent (lignes, arcs et courbes de Bézier)"""
        path_elements = []
        for element in self.svg.descendants():
            if not isinstance(element, inkex.PathElement):
                continue
            path = list(element.path)
            if len(path) < 2 or path[0].letter != 'M':
                continue
            start_point = (float(path[0].x), float(path[0].y))
            end_point = None
            path_type = None
            
            if len(path) > 1:
                second_cmd = path[1]
                path_type = second_cmd.letter
                
                if path_type == 'L':
                    end_point = (float(second_cmd.x), float(second_cmd.y))
                elif path_type == 'A':
                    end_point = (float(second_cmd.x), float(second_cmd.y))
                elif path_type == 'C':
                    end_point = (float(second_cmd.x3), float(second_cmd.y3))
                elif path_type == 'Q':
                    end_point = (float(second_cmd.x2), float(second_cmd.y2))
                elif path_type == 'Z':
                    end_point = start_point
            
            # Vérification de la validité des points
            if (not isinstance(start_point, tuple) or not isinstance(end_point, tuple) or
                len(start_point) != 2 or len(end_point) != 2 or
                not all(isinstance(v, float) for v in start_point+end_point)):
                continue
            
            # Créer une enveloppe pour ce chemin
            if path_type in ['L', 'A', 'C', 'Q']:
                envelope = self.get_path_envelope(element.path,self.options.tolerance)
                
                length = math.dist(start_point, end_point)
                if length > 0:
                    vector = ((end_point[0] - start_point[0])/length, (end_point[1] - start_point[1])/length)
                else:
                    vector = (0, 0)
                
                is_horizontal = abs(vector[1]) < 0.01
                is_vertical = abs(vector[0]) < 0.01
                
                path_elements.append({
                    'element': element,
                    'id': element.get('id'),
                    'start': start_point,
                    'end': end_point,
                    'style': element.style,
                    'length': length,
                    'vector': vector,
                    'color': element.style.get('stroke', '#000000').lower(),
                    'path_type': path_type,
                    'is_horizontal': is_horizontal,
                    'is_vertical': is_vertical,
                    'orig_path': element.path,
                    'envelope': envelope
                })
        
        paths_by_color = {}
        for path in path_elements:
            color = path['color']
            if color not in paths_by_color:
                paths_by_color[color] = []
            paths_by_color[color].append(path)
        
        to_remove = set()
        for color, paths in paths_by_color.items():
            # Séparer les chemins par type
            straight_paths = [p for p in paths if p['path_type'] == 'L']
            arc_paths = [p for p in paths if p['path_type'] == 'A']
            cubic_bezier_paths = [p for p in paths if p['path_type'] == 'C']
            quadratic_bezier_paths = [p for p in paths if p['path_type'] == 'Q']
            
            # Traiter les chemins droits 
            if straight_paths:
                self._find_overlapping_straight_segments(straight_paths, to_remove)
            
            # Traiter les chemins courbes
            curve_paths = arc_paths + cubic_bezier_paths + quadratic_bezier_paths
            if curve_paths:
                self._find_overlapping_curve_segments(curve_paths, to_remove)
        
        count_removed = 0
        for element in list(self.svg.descendants()):
            if isinstance(element, inkex.PathElement) and element.get('id') in to_remove:
                parent = element.getparent()
                if parent is not None:
                    parent.remove(element)
                    count_removed += 1
        
        return count_removed > 0

    def _find_overlapping_straight_segments(self, segments, to_remove):
        """Trouve les segments droits qui se chevauchent"""
        tolerance = self.options.tolerance
        
        # Organiser les segments par orientation (horizontaux, verticaux, diagonaux)
        horizontal_segments = [s for s in segments if s['is_horizontal']]
        vertical_segments = [s for s in segments if s['is_vertical']]
        diagonal_segments = [s for s in segments if not s['is_horizontal'] and not s['is_vertical']]
        
        # Traiter chaque groupe séparément pour éviter de comparer des segments d'orientation différente
        for segment_group in [horizontal_segments, vertical_segments, diagonal_segments]:
            # Construire un graphe d'adjacence des segments qui se chevauchent
            overlap_graph = {}
            
            # Remplir le graphe
            for i in range(len(segment_group)):
                path1 = segment_group[i]
                if path1['id'] not in overlap_graph:
                    overlap_graph[path1['id']] = {'path': path1, 'overlaps': set()}
                
                for j in range(i + 1, len(segment_group)):
                    path2 = segment_group[j]
                    
                    # Si les segments ont la même orientation (vecteurs colinéaires)
                    dot_product = abs(path1['vector'][0]*path2['vector'][0] + path1['vector'][1]*path2['vector'][1])
                    if dot_product > 0.99:  # Presque parallèles
                        # Calculer la distance entre les segments
                        dist1 = self.point_to_segment_distance(path1['start'], path2['start'], path2['end'])
                        dist2 = self.point_to_segment_distance(path1['end'], path2['start'], path2['end'])
                        dist3 = self.point_to_segment_distance(path2['start'], path1['start'], path1['end'])
                        dist4 = self.point_to_segment_distance(path2['end'], path1['start'], path1['end'])
                        
                        # Si les segments sont suffisamment proches
                        if dist1 <= tolerance or dist2 <= tolerance or dist3 <= tolerance or dist4 <= tolerance:
                            # Vérifier si les segments se chevauchent
                            # Projeter les points sur la ligne de référence (utiliser le premier segment)
                            ref_vector = path1['vector']
                            ref_point = path1['start']
                            
                            # Fonction pour projeter un point sur la ligne de référence
                            def project_point(point):
                                vec = (point[0] - ref_point[0], point[1] - ref_point[1])
                                projection = vec[0] * ref_vector[0] + vec[1] * ref_vector[1]
                                return projection
                            
                            # Projeter les points de début et de fin des deux segments
                            p1_start_proj = project_point(path1['start'])
                            p1_end_proj = project_point(path1['end'])
                            p2_start_proj = project_point(path2['start'])
                            p2_end_proj = project_point(path2['end'])
                            
                            # S'assurer que les projections sont ordonnées (début < fin)
                            if p1_start_proj > p1_end_proj:
                                p1_start_proj, p1_end_proj = p1_end_proj, p1_start_proj
                            if p2_start_proj > p2_end_proj:
                                p2_start_proj, p2_end_proj = p2_end_proj, p2_start_proj
                            
                            # Vérifier si les segments se chevauchent sur l'axe de projection
                            overlap_start = max(p1_start_proj, p2_start_proj)
                            overlap_end = min(p1_end_proj, p2_end_proj)
                            
                            if overlap_start <= overlap_end:  # Les segments se chevauchent
                                # Ajouter au graphe d'adjacence
                                if path2['id'] not in overlap_graph:
                                    overlap_graph[path2['id']] = {'path': path2, 'overlaps': set()}
                                overlap_graph[path1['id']]['overlaps'].add(path2['id'])
                                overlap_graph[path2['id']]['overlaps'].add(path1['id'])
            
            # Traiter les groupes de segments qui se chevauchent
            self._process_overlapping_groups(overlap_graph, to_remove)

    def _process_overlapping_groups(self, overlap_graph, to_remove):
        """Traite les groupes de chemins qui se chevauchent"""
        # Parcourir les groupes de chemins qui se chevauchent
        processed = set()
        for path_id in overlap_graph:
            if path_id in processed or len(overlap_graph[path_id]['overlaps']) == 0:
                continue
            
            # Identifier le groupe complet avec BFS
            group = []
            queue = [path_id]
            group_processed = set([path_id])
            
            while queue:
                current_id = queue.pop(0)
                group.append(current_id)
                
                for overlapping_id in overlap_graph[current_id]['overlaps']:
                    if overlapping_id not in group_processed:
                        queue.append(overlapping_id)
                        group_processed.add(overlapping_id)
            
            # Traiter ce groupe de chemins qui se chevauchent
            if len(group) > 1:
                # Collecter tous les points de début et fin
                all_points = []
                first_path = None
                path_type = None
                
                for overlap_id in group:
                    path_data = overlap_graph[overlap_id]['path']
                    all_points.append((path_data['start'], path_data['end']))
                    
                    if first_path is None:
                        first_path = path_data
                        path_type = path_data.get('path_type', 'L')
                
                if first_path:
                    # Utiliser le premier chemin comme référence
                    ref_vector = first_path['vector']
                    ref_point = first_path['start']
                    
                    # Projeter tous les points sur la ligne de référence
                    projections = []
                    
                    for start, end in all_points:
                        # Projeter le point de début
                        vec_start = (start[0] - ref_point[0], start[1] - ref_point[1])
                        proj_start = vec_start[0] * ref_vector[0] + vec_start[1] * ref_vector[1]
                        projections.append((proj_start, start))
                        
                        # Projeter le point de fin
                        vec_end = (end[0] - ref_point[0], end[1] - ref_point[1])
                        proj_end = vec_end[0] * ref_vector[0] + vec_end[1] * ref_vector[1]
                        projections.append((proj_end, end))
                    
                    # Trouver les projections minimale et maximale
                    min_proj = min(projections, key=lambda p: p[0])
                    max_proj = max(projections, key=lambda p: p[0])
                    
                    # Récupérer les points extrêmes
                    extreme_start = min_proj[1]
                    extreme_end = max_proj[1]
                    
                    # Créer un nouveau chemin selon le type
                    new_path = None
                    
                    if path_type == 'L':
                        # Créer un segment de droite
                        new_path = inkex.Path([inkex.paths.Move(*extreme_start), inkex.paths.Line(*extreme_end)])
                    
                    else:
                        # Fallback : garder le chemin original
                        new_path = first_path['orig_path']
                    
                    # Créer un nouvel élément de chemin
                    new_element = inkex.PathElement(
                        id=f"chemin_fusionne_{path_id}",
                        d=str(new_path),
                        style=str(first_path['style'])
                    )
                    
                    # Ajouter le nouveau chemin au document
                    parent = first_path['element'].getparent()
                    if parent is not None:
                        parent.append(new_element)
                    
                    # Marquer tous les chemins originaux pour suppression
                    for overlap_id in group:
                        to_remove.add(overlap_id)
            
            # Marquer tous les chemins de ce groupe comme traités
            processed.update(group)

    def _find_overlapping_curve_segments(self, segments, to_remove):
        """Trouve les segments courbes (arcs et Bézier) qui se chevauchent en utilisant leurs enveloppes"""
        tolerance = self.options.tolerance
        
        # Regrouper les chemins par type pour un traitement plus efficace
        paths_by_type = {}
        for path in segments:
            path_type = path['path_type']
            if path_type not in paths_by_type:
                paths_by_type[path_type] = []
            paths_by_type[path_type].append(path)
        
        # Traiter chaque type de chemin séparément
        for path_type, paths in paths_by_type.items():
            # Construire un graphe d'adjacence des segments qui se chevauchent
            overlap_graph = {}
            
            # Pour chaque paire de chemins du même type
            for i in range(len(paths)):
                path1 = paths[i]
                if path1['id'] not in overlap_graph:
                    overlap_graph[path1['id']] = {'path': path1, 'overlaps': set()}
                
                for j in range(i + 1, len(paths)):
                    path2 = paths[j]
                    
                    # Vérifier si les enveloppes se chevauchent
                    # Pour simplifier, nous vérifions si les points d'extrémité sont suffisamment proches
                    # et si les chemins ont une forme similaire
                    
                    # Vérifier si les points de début et fin sont proches
                    dist_start_start = math.dist(path1['start'], path2['start'])
                    dist_start_end = math.dist(path1['start'], path2['end'])
                    dist_end_start = math.dist(path1['end'], path2['start'])
                    dist_end_end = math.dist(path1['end'], path2['end'])
                    
                    # Deux chemins sont candidats au chevauchement si leurs extrémités sont proches
                    endpoints_close = (
                        (dist_start_start <= tolerance and dist_end_end <= tolerance) or
                        (dist_start_end <= tolerance and dist_end_start <= tolerance)
                    )
                    
                    if endpoints_close:
                        # Pour les arcs: vérifier aussi les rayons et rotation
                        if path_type == 'A':
                            cmd1 = list(path1['orig_path'])[1]
                            cmd2 = list(path2['orig_path'])[1]
                            
                            # Calculer la différence relative entre les rayons
                            rx_diff = abs(cmd1.rx - cmd2.rx) / max(cmd1.rx, cmd2.rx, 0.001)
                            ry_diff = abs(cmd1.ry - cmd2.ry) / max(cmd1.ry, cmd2.ry, 0.001)
                            rot_diff = abs(cmd1.x_axis_rotation - cmd2.x_axis_rotation) % 360  # Correction: x_axis_rotation
                            rot_diff = min(rot_diff, 360 - rot_diff) / 180.0  # Normaliser entre 0 et 1
                            
                            # Si les différences sont faibles, considérer les arcs comme similaires
                            arcs_similar = (rx_diff < 0.1 and ry_diff < 0.1 and rot_diff < 0.1)
                            
                            if arcs_similar:
                                # Ajouter au graphe d'adjacence
                                if path2['id'] not in overlap_graph:
                                    overlap_graph[path2['id']] = {'path': path2, 'overlaps': set()}
                                overlap_graph[path1['id']]['overlaps'].add(path2['id'])
                                overlap_graph[path2['id']]['overlaps'].add(path1['id'])
                        
                        # Pour les courbes de Bézier: comparer les points de contrôle
                        elif path_type in ['C', 'Q']:
                            cmd1 = list(path1['orig_path'])[1]
                            cmd2 = list(path2['orig_path'])[1]
                            
                            control_points_similar = False
                            
                            if path_type == 'C':
                                # Calculer les distances entre points de contrôle (directs ou inversés)
                                dist_ctrl1 = math.dist((cmd1.x2, cmd1.y2), (cmd2.x2, cmd2.y2))
                                dist_ctrl2 = math.dist((cmd1.x3, cmd1.y3), (cmd2.x3, cmd2.y3))
                                dist_ctrl_inv1 = math.dist((cmd1.x2, cmd1.y2), (cmd2.x3, cmd2.y3))
                                dist_ctrl_inv2 = math.dist((cmd1.x3, cmd1.y3), (cmd2.x2, cmd2.y2))
                                
                                # Vérifier si les points de contrôle sont similaires (directement ou inversés)
                                control_points_similar = (
                                    (dist_ctrl1 <= tolerance * 2 and dist_ctrl2 <= tolerance * 2) or
                                    (dist_ctrl_inv1 <= tolerance * 2 and dist_ctrl_inv2 <= tolerance * 2)
                                )
                                
                            elif path_type == 'Q':
                                # Pour les courbes quadratiques, il n'y a qu'un seul point de contrôle
                                dist_ctrl = math.dist((cmd1.x1, cmd1.y1), (cmd2.x1, cmd2.y1))
                                control_points_similar = (dist_ctrl <= tolerance * 2)
                            
                            if control_points_similar:
                                # Ajouter au graphe d'adjacence
                                if path2['id'] not in overlap_graph:
                                    overlap_graph[path2['id']] = {'path': path2, 'overlaps': set()}
                                overlap_graph[path1['id']]['overlaps'].add(path2['id'])
                                overlap_graph[path2['id']]['overlaps'].add(path1['id'])
            
            # Traiter les groupes de segments qui se chevauchent
            self._process_overlapping_groups(overlap_graph, to_remove)

    def point_to_segment_distance(self, point, segment_start, segment_end):
        """Calcule la distance minimale d'un point à un segment"""
        try:
            # Clé de cache unique pour cette opération
            cache_key = (point, segment_start, segment_end)

            # Vérifier si le résultat est déjà dans le cache
            if cache_key in self._distance_cache:
                return self._distance_cache[cache_key]

            px, py = point
            ax, ay = segment_start
            bx, by = segment_end

            segment_vector = (bx - ax, by - ay)
            point_vector = (px - ax, py - ay)

            segment_length_sq = segment_vector[0]**2 + segment_vector[1]**2

            if segment_length_sq == 0:
                result = math.dist(point, segment_start)
                self._distance_cache[cache_key] = result
                return result

            t = max(0, min(1, (point_vector[0] * segment_vector[0] +
                             point_vector[1] * segment_vector[1]) / segment_length_sq))

            projection_x = ax + t * segment_vector[0]
            projection_y = ay + t * segment_vector[1]

            result = math.dist(point, (projection_x, projection_y))

            # Stocker le résultat dans le cache
            self._distance_cache[cache_key] = result

            return result
        except Exception as e:
            inkex.utils.debug(f"Erreur dans point_to_segment_distance: {str(e)}")
            return float('inf')

    def kill_other_inkscape_running(self):
        """Ferme toutes les autres instances d'inkscape"""
        if platform.system() == 'Windows':
            result = subprocess.run(['wmic', 'process', 'where', "name='inkscape.exe'", 'get', 'CreationDate,ProcessId'], text=True, capture_output=True)
            lines = result.stdout.strip().split('\n')[1:]
            processes = []
            for line in lines:
                if line != "":
                    parts = line.split()
                    pid = parts[1]
                    creation_date_str = re.sub(r'\+\d+$', '', parts[0])
                    creation_date = datetime.strptime(creation_date_str, '%Y%m%d%H%M%S.%f')
                    processes.append((pid, creation_date))
            processes.sort(key=lambda x: x[1])
            if len(processes) > 1:
                for process in processes[1:]:
                    subprocess.run(['taskkill', '/PID', process[0]])

    def remove_unmanaged_colors(self):
        """Supprime les éléments dont la couleur de trait n'est pas gérée par la découpeuse laser"""
        if not self.options.SupprimerCouleursNonGerees:
            return

        # Lecture de l'ordre des couleurs depuis le fichier INI
        ini_path = os.path.join(os.path.dirname(__file__), 'OptimLaser.ini')
        color_order = []
        try:
            with open(ini_path, 'r') as ini_file:
                for line in ini_file:
                    if line.strip().startswith('order'):
                        color_order = line.split('=')[1].strip().split(',')
                        color_order = [color.strip().lower() for color in color_order]
                        break
        except:
            return

        # Suppression des éléments avec couleur de trait non gérée
        for element in list(self.svg.descendants()):
            if hasattr(element, 'style') and 'stroke' in element.style:
                stroke_color = element.style.get('stroke', '#000000').lower()
                if stroke_color.startswith('#'):
                    stroke_color = stroke_color[1:]

                if stroke_color not in color_order:
                    parent = element.getparent()
                    if parent is not None:
                        parent.remove(element)

    def effect(self):
        try:
            current_file_name = self.document_path()
            with open(current_file_name, 'wb') as output_file:
                self.save(output_file)
        except Exception as e:
            messagebox.showwarning(_('Attention !'), _('Vous devez enregistrer le fichier puis relancer l\'extension.'))
            return

        # % Appliquer la transformation d'un groupe à chacun de ses éléments enfants
        self.ungroup_and_apply_transform_to_children()

        # % Supprimer tout ce qui a des lignes qui ne sont pas dans les couleurs gérées
        self.remove_unmanaged_colors()

        # % Découpage en chemins simples
        self.replace_with_subpaths()

        # % Ajuster les segments qui se chevauchent
        self.adjust_overlapping_segments()

        # % Optimisation du parcours
        self.order_paths()

        # % Remettre les éléments gris
        for element in list(self.ListeDeGris):
            couche = self.find_layer(element)
            style = element.style
            style['stroke'] = None
            if couche is not None:
                couche.append(element)
            else:
                self.document.getroot().append(element)

        # % Sauvegarde du fichier modifié et ouverture dans une nouvelle occurrence d'inkscape si demandé
        if self.options.SauvegarderSousDecoupe:
            current_file_name = self.document_path()
            base_name, extension = os.path.splitext(current_file_name)
            new_file_name = base_name + _(" - decoupe") + extension
            with open(new_file_name, 'wb') as output_file:
                self.save(output_file)
            self.document = inkex.load_svg(current_file_name)
            self.kill_other_inkscape_running()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                subprocess.Popen(["inkscape", new_file_name])


# ======================================================================
if __name__ == '__main__':
    OptimLaser().run()

# # Pour débugger dans VSCode et en lançant InkScape
# input_file = os.path.join(os.path.dirname(__file__), 'Test.svg')
# if __name__ == '__main__':
#     if '\\' in __file__ and os.path.exists(input_file):
#         # Dans VSCode
#         output_file = input_file
#         OptimLaser().run([input_file, '--output=' + output_file])
#     else:
#         OptimLaser().run()
