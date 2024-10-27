#!/usr/bin/env/python
'''
Codé par Frank SAURET et Copilot janvier 2023 - juin 2024

La fonction remove duplicate utilise maintenant le travail de Ellen Wasbø :
    https://gitlab.com/EllenWasbo/inkscape-extension-removeduplicatelines

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This    program    is    distributed in the    hope    that    it    will    be    useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
'''

# Optimisation avant découpe laser
# - Décomposition en éléments simples
# - Suppression des traits supperposés
# - Ordonnancement des chemins pour optimiser le déplacement de la tête de découpe laser
# - sauvegarde avant et aprés dans 2 fichiers séparés

# Todo
# - Revoir l'optimisation du déplacement avec un algo plus performant
# - Optimiser le code en globalisant les actions
# - Revoir la gestion du kill des processus inkscape essayer de ne fermer que l'instance du fichier de découpe ou faire un enregistrer sous si l'api l'implémente

# Versions
#  0.1 Janvier 2023
#  0.2 juin 2024
#  0.2.2 octobre 2024
# 2024.1 novembre 2024 juste le versionnage

__version__ = "2024.1"

import os
import subprocess
import inkex
import inkex.base
import re
import xml.etree.ElementTree as ET
# from ungroup_deep import *
from inkex.transforms import Transform
from inkex import PathElement, CubicSuperPath, Transform
import numpy as np
from tkinter import messagebox
import platform
from datetime import datetime
import warnings
import copy
from lxml import etree


class OptimLaser(inkex.Effect,inkex.EffectExtension):

    def __init__(self):
        self.ListeDeGris=[]
        self.numeroChemin=0
        inkex.Effect.__init__(self)
        self.arg_parser.add_argument("--tab",
            type=str,
            dest="tab",
            default="options",
            help="The selected UI-tab when OK was pressed")
        self.arg_parser.add_argument("-S","--SauvegarderSousDecoupe",
            type=inkex.Boolean,
            dest="SauvegarderSousDecoupe",
            default=True,
            help="Sauvegarder fichier avec « - Decoupe » au bout de son nom.")
        self.arg_parser.add_argument("-T","--ToutSelectionner",
            type=inkex.Boolean,
            dest="ToutSelectionner",
            default=True,
            help="Applique les modifications à tout le document. Si non coché ne les applique qu'à la sélection.")
        self.arg_parser.add_argument("-t","--tolerance",
            type=float,
            dest="tolerance",
            default="0.001")
        self.arg_parser.add_argument("-x","--selfPath",
            type=inkex.Boolean,
            dest="selfPath",
            default=False)

    def is_line(self, start, control1, control2, end ):
        """Vérifie si la courbe de Bézier est une ligne droite

        Args:
            start (tuple[float, float]): Début de la courbe de Bézier
            control1 (tuple[float, float]): Premier point de contrôle
            control2 (tuple[float, float]): second point de contrôle
            end (tuple[float, float]): fin

        Returns:
            bool: true if this is a line
        """
        vector_se = (end[0] - start[0], end[1] - start[1])
        vector_sc1 = (control1[0] - start[0], control1[1] - start[1])
        vector_sc2 = (control2[0] - start[0], control2[1] - start[1])
        cross_product1 = vector_se[0] * vector_sc1[1] - vector_se[1] * vector_sc1[0]
        cross_product2 = vector_se[0] * vector_sc2[1] - vector_se[1] * vector_sc2[0]
        return abs(cross_product1) < 0.01 and abs(cross_product2) < 0.01

    def find_layer(self, element):
        """Retourne le calque parent d'un élément
        """
        while element is not None:
            if isinstance(element, etree._Element):
                if element.tag == inkex.addNS('g', 'svg') and element.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    # return element.get(inkex.addNS('label', 'inkscape')) // pour son nom
                    return element
            element = element.getparent()
        return None
    
    def ungroup_and_apply_transform_to_children(self):
        """Applique la transformation d'un groupe à chacun de ses éléments enfants en conservant les transformations eventuelles."""
        listChild=[]
        for element in self.svg.selection.filter(inkex.Group):
            if 'layer' not in element.get('id', ''):
                parent = element.getparent()
                transform = element.transform
                for child in element.getchildren():
                    id_child = child.get('id')
                    if not isinstance(child, inkex.PathElement):
                        child = child.to_path_element()
                        child.set('id', id_child)
                    path = child.path
                    path = path.transform(transform)
                    child.path = path
                    child.attrib.pop('transform', None) 
                    parent.append(child)
                    self.svg.selection.pop(child.get('id'))
                    listChild.append(child)
                self.svg.selection.pop(element.get('id'))
                parent.remove(element)    
        #Ici il y a un bug dans la fonction svg.selection.add qui fait que quelques fois le compteur ne s'incrémente pas et donc ça écrit l'élément suivant sur le précédent                
        liste_selectionP = []
        for element in self.svg.selection.values():
            liste_selectionP.append(element)
        liste_selectionP.extend(listChild)  
        self.svg.selection.clear()
        # Ajouter les éléments de liste_selection dans svg.selection
        for elem in liste_selectionP:
            self.svg.selection[elem.get('id')] = elem                                        

    def replace_with_subpaths(self):
        """Découpe tous les chemin en petits chemins composés uniquement d'un commande Move et d'une commande de tracé (absolu)

        Args:
            element (inkex.elements): un chemin composé de M, L, A, C ou Z.
        """
        # M x y : Move To :  déplace vers un point donné de coordonnées(x,y)
        # Z ferme le chemin
        # A rx ry x-axis-rotation large-arc-flag sweep-flag x y : Arc Eliptique : Cercle ou ellipse -
        # C x1 y1, x2 y2, x y: Curve To : Courbe de Bézier cubique
        # L x y : Line TO : dessine une ligne droite vers un point donné de coordonnées(x,y)
        self.numeroChemin = len(self.svg.selection)
        listElem=[]
        
        for element in self.svg.selection.filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon):
            parent = element.getparent()
            couche = self.find_layer(element)
            # Supprimer le remplissage, les nouveaux éléments sont des traits.
            # Le gris étant a priori destiné à la gravure, les éléments dont le remplissage est gris ou noir seront remis après les modifications.
            style = element.style
            fill_value = style.get('fill', None)
            if fill_value and fill_value.lower() != 'none':
                fill_color = inkex.Color(style('fill', None))
                r, v, b = fill_color.to_rgb()
                if (r == v and r == b and v == b) :
                    self.ListeDeGris.append(copy.deepcopy(element))
                style['fill'] = 'none'
            
            # Supprime les translates
            if isinstance(element, inkex.PathElement) and 'transform' in element.attrib:
                path = element.path
                transform = inkex.Transform(element.get('transform'))
                path = path.transform(transform)
                element.attrib.pop('transform', None) 
                element.path = path
            path = element.path.to_non_shorthand()
            
            if len(path)>0:
                # Générer les nouveaux éléments à partir du chemin complet
                segments = iter(path)
                segmentPrev = next(segments)
                Premier = segmentPrev
                for segment in segments:
                    if segment.letter != 'Z' : # si pas Z crée le chemin
                        debut=segmentPrev.end_point(None, None)
                        fin=segment.end_point(None, None)
                        segment_path = inkex.Path([inkex.paths.Move(*debut)] + [segment])
                        # Si Curve=ligne change le C en L
                        if segment.letter=='C' :
                            if self.is_line(debut, (segment.x2,segment.y2), (segment.x3,segment.y3), fin):
                                segment_path = inkex.Path([inkex.paths.Move(*debut)] + [inkex.paths.Line(*fin)])
                        segmentPrev = segment
                    else:    # si Z ferme la forme par une ligne droite
                        if segmentPrev.letter!='C':
                            debut=(round(segmentPrev.x, 6), round(segmentPrev.y, 6))
                        else:
                            debut=(round(segmentPrev.x4, 6), round(segmentPrev.y4, 6))    
                        fin = (round(Premier.x, 6), round(Premier.y, 6))
                        segment_path = inkex.Path([inkex.paths.Move(*debut)] + [inkex.paths.Line(*fin)])
                    if debut!=fin:
                        self.numeroChemin += 1
                        # Crée puis insère le nouveau chemin
                        new_element = inkex.PathElement(id="chemin"+str(self.numeroChemin),
                                                        d=str(segment_path),
                                                        style=str(style),
                                                        transform=str(element.transform))
                        # Ajouter le nouvel élément à la couche parente
                        if couche is not None:
                            couche.append(new_element)
                        else:
                            # Si aucune couche n'est trouvée, ajouter à la racine du document
                            self.document.getroot().append(new_element)
                        # self.svg.selection.add(new_element) // Voir ci dessous
                        listElem.append(new_element)
                # supprime l'elément original du document
                parent.remove(element)
                # supprime l'elément original de la sélection
                self.svg.selection.pop(element.get('id'))
        
        #Ici il y a un bug dans la fonction svg.selection.add qui fait que quelques fois le compteur ne s'incrémente pas et donc ça écrit l'élément suivant sur le précédent
        liste_selection = []
        for element in self.svg.selection.values():
            liste_selection.append(element)
        liste_selection.extend(listElem)  
        self.svg.selection.clear()
        # Ajouter les éléments de liste_selection dans svg.selection
        for elem in liste_selection:
            self.svg.selection[elem.get('id')] = elem

    def remove_duplicates(self):
        """ supprime les lignes qui passe les unes sur les autres
        """
        tolerance=self.options.tolerance

        coords=[]#one segmentx8 subarray for each path and subpath (paths and subpaths treated equally)
        pathNo=[]
        subPathNo=[]
        cPathNo=[]#counting alle paths and subpaths equally
        removeSegmentPath=[]

        nFailed=0
        nInkEffect=0
        p=0
        c=0
        idsNotPath=[]
        for id, elem in self.svg.selection.id_dict().items():
            thisIsPath=True
            if elem.get('d')==None: # lit le chemin
                thisIsPath=False
                nFailed+=1
                idsNotPath.append(id)
            if elem.get('inkscape:path-effect') != None: # si pas d'effet de chemin
                thisIsPath=False
                nInkEffect+=1
                idsNotPath.append(id)

            if thisIsPath:
                #apply transformation matrix if present
                csp = CubicSuperPath(elem.get('d'))
                elem.path=elem.path.to_absolute()
                transformMat = Transform(elem.get('transform'))
                cpsTransf=csp.transform(transformMat)
                elem.path = cpsTransf.to_path(curves_only=True)
                pp=elem.path
                s=0
                #create matrix with segment coordinates p1x p1y c1x c1y c2x c2y p2x p2y
                for sub in pp.to_superpath():
                    coordsThis=np.zeros((len(sub)-1,8))

                    i=0
                    while i <= len(sub) - 2:
                        coordsThis[i][0]=sub[i][1][0]
                        coordsThis[i][1]=sub[i][1][1]
                        coordsThis[i][2]=sub[i][2][0]
                        coordsThis[i][3]=sub[i][2][1]
                        coordsThis[i][4]=sub[i+1][0][0]
                        coordsThis[i][5]=sub[i+1][0][1]
                        coordsThis[i][6]=sub[i+1][1][0]
                        coordsThis[i][7]=sub[i+1][1][1]

                        i+=1

                    coords.append(coordsThis)
                    pathNo.append(p)
                    subPathNo.append(s)
                    cPathNo.append(c)
                    c+=1
                    s+=1
                p+=1

        origCoords=[]
        for item in coords: origCoords.append(np.copy(item))#make a real copy (not a reference that changes with the original
        #search for overlapping or close segments
        #for each segment find if difference of any x or y is less than tolerance - if so - calculate 2d-distance and find if all 4 less than tolerance
        #repeat with reversed segment
        #if match found set match coordinates to -1000 to mark this to be removed and being ignored later on
        i=0
        while i <= len(coords)-1:#each path or subpath
            j=0
            while j<=len(coords[i][:,0])-1:#each segment j of path i
                k=0
                while k<=len(coords)-1:#search all other subpaths
                    evalPath=True
                    if k == i and self.options.selfPath == False:#do not test path against itself
                        evalPath=False
                    if evalPath:
                        segmentCoords=np.array(coords[i][j,:])
                        if segmentCoords[0] != -1000 and segmentCoords[1] != -1000:
                            searchCoords=np.array(coords[k])
                            if k==i:
                                searchCoords[j,:]=-2000#avoid comparing segment with itself
                            subtr=np.abs(searchCoords-segmentCoords)
                            maxval=subtr.max(1)
                            lessTol=np.argwhere(maxval<tolerance)
                            matchThis=False
                            finalK=0
                            lesstolc=0
                            if len(lessTol) > 0:#proceed to calculate 2d distance where both x and y distance is less than tolerance
                                c=0
                                while c < len(lessTol):
                                    dists=np.zeros(4)
                                    dists[0]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][0],2),np.power(subtr[lessTol[c,0]][1],2)))
                                    dists[1]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][2],2),np.power(subtr[lessTol[c,0]][3],2)))
                                    dists[2]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][4],2),np.power(subtr[lessTol[c,0]][5],2)))
                                    dists[3]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][6],2),np.power(subtr[lessTol[c,0]][7],2)))
                                    if dists.max() < tolerance:
                                        matchThis=True
                                        finalK=k
                                        lesstolc=lessTol[c]
                                    c+=1
                            if matchThis == False:#try reversed
                                segmentCoordsRev=[segmentCoords[6], segmentCoords[7],segmentCoords[4],segmentCoords[5],segmentCoords[2],segmentCoords[3],segmentCoords[0],segmentCoords[1]]
                                subtr=np.abs(searchCoords-segmentCoordsRev)
                                maxval=subtr.max(1)
                                lessTol=np.argwhere(maxval<tolerance)
                                if len(lessTol) > 0:#proceed to calculate 2d distance where both x and y distance is less than tolerance
                                    c=0
                                    while c < len(lessTol):
                                        dists=np.zeros(4)
                                        dists[0]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][0],2),np.power(subtr[lessTol[c,0]][1],2)))
                                        dists[1]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][2],2),np.power(subtr[lessTol[c,0]][3],2)))
                                        dists[2]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][4],2),np.power(subtr[lessTol[c,0]][5],2)))
                                        dists[3]=np.sqrt(np.add(np.power(subtr[lessTol[c,0]][6],2),np.power(subtr[lessTol[c,0]][7],2)))
                                        if dists.max() < tolerance:
                                            matchThis=True
                                            finalK=k
                                            lesstolc=lessTol[c]
                                        c+=1

                            if matchThis:
                                coords[finalK][lesstolc,:]=-1000
                                removeSegmentPath.append(pathNo[finalK])
                    k+=1
                j+=1
            i+=1

        # % Remove segments with a match
        if len(removeSegmentPath) > 0:
            removeSegmentPath=np.array(removeSegmentPath)
            i=0
            for id, elem in self.svg.selection.id_dict().items():#each path
                if not id in idsNotPath:
                    idx=np.argwhere(removeSegmentPath==i)
                    if len(idx) > 0:
                        # s'il a matché ça le supprime du dessin et de la selection
                        parent = elem.getparent()
                        parent.remove(elem)
                        self.svg.selection.pop(elem.get('id'))
                    i+=1

    def get_first_and_last_point(self, d):
        """Retourne les premier et dernier point d'un segment

        Args:
            d (string): chemin

        Returns:
            tupel(float, float, float, float): x, y du premier point et x, y du dernier point
        """
        path = d.split()
        return float(path[1]), float(path[2]), float(path[-2]), float(path[-1])

    def order_paths(self):
        """Trie les chemins pour optimiser le déplacement de la tête de découpe laser
        """
        # Créer une liste de tous les chemins
        paths = [
            (
                element.get('d'), 
                element.get('style'), 
                *self.get_first_and_last_point(element.get('d')), 
                self.find_layer(element)
            ) 
            for element in self.svg.selection.filter(inkex.PathElement) 
            if element.get('d') is not None]
            # element.get('d'),          # path[0]
            # element.get('style'),      # path[1]
            # first_point_x,             # path[2]
            # first_point_y,             # path[3]
            # last_point_x,              # path[4]
            # last_point_y,              # path[5]
            # self.find_layer(element)   # path[6]
 
        # Calculer la distance de chaque point de départ à (0,0)
        distances = [np.sqrt(path[2]**2 + path[3]**2) for path in paths]

        # Trouver l'index du chemin le plus proche de (0,0)
        start_index = np.argmin(distances)

        # Choisir ce point comme point de départ et le retirer de la liste des chemins
        start_point = paths[start_index][4:6]
        ordered_paths = [paths.pop(start_index)]

        while paths:
            # Trouver le chemin le plus proche
            distances_to_start = [np.sqrt((start_point[0] - path[2])**2 + (start_point[1] - path[3])**2) for path in paths]
            distances_to_end = [np.sqrt((start_point[0] - path[4])**2 + (start_point[1] - path[5])**2) for path in paths]
            nearest_path_index_start = np.argmin(distances_to_start)
            nearest_path_index_end = np.argmin(distances_to_end)
            if distances_to_end[nearest_path_index_end] < distances_to_start[nearest_path_index_start]:
                nearest_path_index = nearest_path_index_end
                # Inverser le chemin si le point le plus proche est le dernier point du chemin
                paths[nearest_path_index] = (paths[nearest_path_index][0], paths[nearest_path_index][1], paths[nearest_path_index][4], paths[nearest_path_index][5], paths[nearest_path_index][2], paths[nearest_path_index][3],paths[nearest_path_index][6])
            else:
                nearest_path_index = nearest_path_index_start
            nearest_path = paths.pop(nearest_path_index)
            # Faire du dernier point du chemin le plus proche votre nouveau point de départ
            start_point = nearest_path[4:6]
            # Ajouter le chemin le plus proche à la liste des chemins ordonnés
            ordered_paths.append(nearest_path)

        # supression des éléments de la sélection et du document
        for element in list(self.svg.selection):
            if element.get('d') is not None:
                parent = element.getparent()
                parent.remove(element)
                self.svg.selection.pop(element.get('id'))

        # Ajouter les chemins triés à la sélection et au document
        NumChemin=1
        for path in ordered_paths:
            new_element = inkex.PathElement(id="chemin"+str(NumChemin),
                                            d=path[0],
                                            style=path[1])
            # Ajouter le nouvel élément à la couche parente
            if path[6] is not None:
                path[6].append(new_element)
            else:
                # Si aucune couche n'est trouvée, ajouter à la racine du document
                self.document.getroot().append(new_element)
            self.svg.selection.add(new_element)
            NumChemin+=1

    def kill_other_inkscape_running(self):
        """ Ferme toutes les autres instances d'inkscape
        """
        if platform.system() == 'Windows':
            result = subprocess.run(['wmic', 'process', 'where', "name='inkscape.exe'", 'get', 'CreationDate,ProcessId'], text=True, capture_output=True)
            lines = result.stdout.strip().split('\n')[1:]  # Ignore the header line
            #Parse the process IDs and creation dates
            processes = []
            for line in lines:
                if line!="":
                    parts = line.split()
                    pid = parts[1]
                    creation_date_str = re.sub(r'\+\d+$', '', parts[0]) # Supprime le decalage horaire
                    creation_date = datetime.strptime(creation_date_str, '%Y%m%d%H%M%S.%f')  # Convert the creation date to a datetime object
                    processes.append((pid, creation_date))
            # Trier les processus par date de création
            processes.sort(key=lambda x: x[1])
            # Si plus d'un processus est en cours d'exécution
            if len(processes) > 1:
                # Tuer tous les processus sauf le premier
                for process in processes[1:]:
                    subprocess.run(['taskkill', '/PID', process[0]])

    def add_points_to_overlapping_paths(self):
        """Décompose les lignes qui se chevauchent
        """
        # Extrait les 2 coordonnées des chemins avec L
        coords = [[(command[1][0], command[1][1]) for command in element.path.to_arrays() if len(command[1]) >= 2] for element in self.svg.selection.filter(inkex.PathElement) if 'L' in element.get('d').upper()]

        paths=[]
        for element in self.svg.selection.filter(inkex.PathElement):
            if isinstance(element, inkex.PathElement) and 'L' in element.get('d').upper():
                paths.append(element)
        
        for i in range(len(coords) - 1):
            for j in range(i + 1, len(coords)):
                coord1, coord2 = coords[i], coords[j]
                idi=paths[i].get('id')
                idj=paths[j].get('id')
                # Arrondir les coordonnées des chemins à 3 chiffres après la virgule
                coord1 = [(round(x, 3), round(y, 3)) for x, y in coord1]
                coord2 = [(round(x, 3), round(y, 3)) for x, y in coord2]
                # Vérifier que path1 et path2 ne sont pas None, contiennent au moins deux points et qu'aucun point n'est none
                if not coord1 or not coord2 or len(coord1) < 2 or len(coord2) < 2 or any(point is None for point in coord1) or any(point is None for point in coord2):
                    continue
                # Calcules les pentes des chemins (y=ax+b)
                a1 = (coord1[1][1] - coord1[0][1]) / (coord1[1][0] - coord1[0][0]) if coord1[1][0] != coord1[0][0] else float('inf')
                a2 = (coord2[1][1] - coord2[0][1]) / (coord2[1][0] - coord2[0][0]) if coord2[1][0] != coord2[0][0] else float('inf')
                # si les pentes ne sont pas égales, les chemins ne sont pas colinéaires
                if abs(a1 - a2) > 0.001:
                    continue
                # ignorer les chemins qui se touchent par au moins 1 point (identiques ou qui se suivent)
                if coord1[0] == coord2[0] or coord1[0] == coord2[-1] or coord1[-1] == coord2[0] or coord1[-1] == coord2[-1]:
                    continue
                # Ajouter les points si les chemins se chevauchent
                if self.is_point_on_path_segment(coord1[0], coord2, a2):
                    segment_path1 = inkex.Path([inkex.paths.Move(*coord2[0])] + [inkex.paths.Line(*coord1[0])])
                    segment_path2 = inkex.Path([inkex.paths.Move(*coord1[0])] + [inkex.paths.Line(*coord2[-1])])
                    self.numeroChemin+=1
                    id2="chemin"+str(self.numeroChemin)
                    new_element2 = inkex.PathElement(id=id2, d=str(segment_path2), style=str(paths[j].get('style')), transform=str(paths[j].transform))
                    
                    elsel=self.svg.getElementById(paths[j].get('id'))
                    elsel.set('d', str(segment_path1))
                    self.document.getroot().append(new_element2)
                    self.svg.selection.add(new_element2)
                    
                if self.is_point_on_path_segment(coord1[-1], coord2, a2):
                    segment_path1 = inkex.Path([inkex.paths.Move(*coord1[-1])] + [inkex.paths.Line(*coord2[0])])
                    segment_path2 = inkex.Path([inkex.paths.Move(*coord2[-1])] + [inkex.paths.Line(*coord1[-1])])
                    self.numeroChemin+=1
                    id2="chemin"+str(self.numeroChemin)
                    new_element2 = inkex.PathElement(id=id2, d=str(segment_path2), style=str(paths[j].get('style')), transform=str(paths[j].transform))
         
                    elsel=self.svg.getElementById(paths[j].get('id'))
                    elsel.set('d', str(segment_path1))  
                    self.document.getroot().append(new_element2)
                    self.svg.selection.add(new_element2)       
                    
                if self.is_point_on_path_segment(coord2[-1], coord1, a2):    
                    segment_path1 = inkex.Path([inkex.paths.Move(*coord1[0])] + [inkex.paths.Line(*coord2[-1])])
                    segment_path2 = inkex.Path([inkex.paths.Move(*coord2[-1])] + [inkex.paths.Line(*coord1[-1])])
                    self.numeroChemin+=1
                    id2="chemin"+str(self.numeroChemin)
                    new_element2 = inkex.PathElement(id=id2, d=str(segment_path2), style=str(paths[i].get('style')), transform=str(paths[i].transform))
                    
                    elsel=self.svg.getElementById(paths[i].get('id'))
                    elsel.set('d', str(segment_path1))
                    self.document.getroot().append(new_element2)
                    self.svg.selection.add(new_element2)                   
                    
                if self.is_point_on_path_segment(coord2[0], coord1, a2):
                    segment_path1 = inkex.Path([inkex.paths.Move(*coord1[0])] + [inkex.paths.Line(*coord2[0])])
                    segment_path2 = inkex.Path([inkex.paths.Move(*coord2[0])] + [inkex.paths.Line(*coord1[-1])])
                    self.numeroChemin+=1
                    id2="chemin"+str(self.numeroChemin)
                    new_element2 = inkex.PathElement(id=id2, d=str(segment_path2), style=str(paths[i].get('style')), transform=str(paths[i].transform))
                                        
                    elsel=self.svg.getElementById(paths[i].get('id'))
                    elsel.set('d', str(segment_path1))
                    self.document.getroot().append(new_element2)
                    self.svg.selection.add(new_element2)     
        pass
    
    def is_point_on_path_segment(self,point, path_segment, a):
        """Vérifie si point se trouve sur path_segment

        Args:
            point (tuple(float, float)): coordonnées du point
            path_segment (tuple(float, float, float, float)): Coordonnées des points de début et fin du segment
            a (float): pente du segment

        Returns:
            bool: true si point est sur le segment
        """
        # pour une droite d'équation y=ax+b
        y=path_segment[0][1]
        x=path_segment[0][0]
        x1=point[0]
        y1=point[1]
        if a != float('inf'): # si droite verticale
            b = y - a * x
            # Vérifier si le point satisfait l'équation de la droite avec une tolérance
            y_attendu = a * x1 + b
            if abs(y_attendu - y1) < 0.001:
                # Vérifier si le point est entre les deux points extrêmes de path_segment
                if min(path_segment[0][0], path_segment[1][0]) <= point[0] <= max(path_segment[0][0], path_segment[1][0]) and \
                min(path_segment[0][1], path_segment[1][1]) <= point[1] <= max(path_segment[0][1], path_segment[1][1]):
                    return True
        else:
            # Cas spécial où la droite est verticale
            if point[0] == path_segment[0][0]:
                if min(path_segment[0][1], path_segment[1][1]) <= point[1] <= max(path_segment[0][1], path_segment[1][1]):
                    return True
        return False
    
    # --------------------------------------------
    def effect(self):
        # Attention : les messages d'erreur ne seront plus affichés
            # sys.stdout = open(os.devnull, 'w')
            # sys.stderr = open(os.devnull, 'w')
        # % Force la sauvegarde du fichier mais attention  il reste affiché comme si pas sauvé (impossible de faire un enregistrer sous)
        try:
            current_file_name = self.document_path()
            with open(current_file_name, 'wb') as output_file:
                self.save(output_file)
        except Exception as e:
            messagebox.showwarning('Attention !', 'Vous devez enregistrer le fichier puis relancer l\'extension.')
            return

        # % Sélectionne tout si demandé
        if self.options.ToutSelectionner or (not self.svg.selected) :
            for element in self.svg.descendants():
                # if not isinstance(element, inkex.Group) and not isinstance(element, inkex.TextElement): # pas les groupes pour éviter une redondance
                if not isinstance(element, inkex.TextElement):     
                    self.svg.selection.add(element)
        
        # % Applique la transformation d'un groupe à chacun de ses éléments enfants.
        self.ungroup_and_apply_transform_to_children()
       
        # % Découpage en chemins simples
        self.replace_with_subpaths()

        # % Ajoute des points en cas de colinéarité
        self.add_points_to_overlapping_paths()

        # % Suppression des doublons
        self.remove_duplicates()
            
        # % Optimisation du parcours
        self.order_paths()
        
        # % Remets les éléments gris
        for element in list(self.ListeDeGris):
            couche = self.find_layer(element)
            style = element.style
            style['stroke']=None
            # Ajouter le nouvel élément à la couche parente
            if couche is not None:
                couche.append(element)
            else:
                # Si aucune couche n'est trouvée, ajouter à la racine du document
                self.document.getroot().append(element)
                
        # % Sauvegarde du fichier modifié et ouverture dans une nouvelle occurence d'inkscape si demandé
        if self.options.SauvegarderSousDecoupe:
            # Sauvegarde du fichier modifié
            current_file_name = self.document_path()
            base_name, extension = os.path.splitext(current_file_name)
            new_file_name = base_name + " - decoupe" + extension
            with open(new_file_name, 'wb') as output_file:
                self.save(output_file)
            self.document = inkex.load_svg(current_file_name)
            # ouvre le fichier modifié dans une nouvelle occurence d'inkscape
            self.kill_other_inkscape_running()
            #Lance inkscape avec new_file_name en masquant les warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                subprocess.Popen(["inkscape", new_file_name])

# ======================================================================
if __name__ == '__main__':
    OptimLaser().run()
# Pour débugger dans VSCode et en lançant InkScape    
# if __name__ == '__main__':
#     if '\\' in __file__:
#         # Dans VSCode
#         input_file = r'H:\\OneDrive\\Essai supp double dupliqué.svg'
#         output_file = input_file
#         OptimLaser().run([input_file, '--output=' + output_file])
#     else:
#         OptimLaser().run()
