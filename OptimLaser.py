#!/usr/bin/env/python
'''
Codé par Frank SAURET janvier 2023 - mai 2024
 
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
# - Suppression des traits supperposés

# Todo
# - Optimisation du déplacement

# Versions
#  0.1 Janvier 2023
#  0.2 juin 2024

__version__ = "0.2"

#from math import *
import os
import sys
import subprocess
import inkex
import inkex.base
from inkex.elements import ShapeElement
import re
#from simplepath import *
from lxml import etree
#import simplestyle
import xml.etree.ElementTree as ET
from ungroup_deep import *
#import copy
#import numpy
from inkex.transforms import Transform
#from xml.etree import ElementTree
from inkex import bezier, PathElement, CubicSuperPath, Transform
import numpy as np
from tkinter import messagebox
from inkex.paths import Path, Move
import math
import platform
from datetime import datetime
import warnings
from inkex.bezier import cspsubdiv






class OptimLaser(inkex.Effect,inkex.EffectExtension):
    
    def __init__(self):
        self.seen_elems = []
        self.numeroChemin = 1
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
    
    def path_to_csp(self, path):
        # Convertir l'élément en un élément de chemin
        path_element = Path(path)
        # Convertir l'élément de chemin en un SuperPath
        superpath = path_element.to_superpath()
        # Convertir le SuperPath en un CubicSuperPath
        cubicsuperpath = cspsubdiv(superpath, 0.1)
        return cubicsuperpath   

    def replace_with_subpaths(self, element):
        # Thank's to Kaalleen on inkscape forum
        # get info about the position in the svg document
        # M x y : Move To :  déplace vers un point donné de coordonnées(x,y)
        # Z ferme le chemin
        # A rx ry x-axis-rotation large-arc-flag sweep-flag x y : Arc Eliptique : Cercle ou ellipse - 
        # C x1 y1, x2 y2, x y: Curve To : Courbe de Bézier cubique
        # L x y : Line TO : dessine une ligne droite vers un point donné de coordonnées(x,y)
        
        parent = element.getparent()
        index = parent.index(element)
               
        # Supprimer le remplissage, les nouveaux éléments sont des traits.
        # Le noir étant a priori destiné à la gravure, les éléments dont le remplissage est gris garderont leur remplissage.
        style = element.style
        fill_color = inkex.Color(style('fill', None))
        r, v, b = fill_color.to_rgb()
        if r != v or r != b or v != b:
            if not style('stroke', None):
                style['stroke'] = style('fill', None)
            style['fill'] = 'none'

        # Supprime les translates
        if isinstance(element, PathElement) and 'transform' in element.attrib:
            path = element.path
            transform = inkex.Transform(element.get('transform'))
            path = path.transform(transform)
            del element.attrib['transform']
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
                    segmentPrev = segment
                else:    # si Z ferme la forme par une ligne droite
                    debut=(round(segmentPrev.x, 6), round(segmentPrev.y, 6))
                    fin = (round(Premier.x, 6), round(Premier.y, 6))
                    if debut != fin:
                        if fin[1]<debut[1] :
                            debut, fin=fin, debut
                        segment_path = inkex.Path([inkex.paths.Move(*fin), inkex.paths.Line(*debut)])
                # Crée puis insère le nouveau chemin        
                new_element = inkex.PathElement(id="chemin"+str(self.numeroChemin),
                                                d=str(segment_path),
                                                style=str(style),
                                                transform=str(element.transform))
                self.numeroChemin += 1
                parent.insert(index, new_element) 
                self.document.getroot().append(new_element)
                self.svg.selection.add(new_element)
                       
            # supprime l'elément original
            parent.remove(element)
            # met à jour la sélection
            self.svg.selection.pop(element.get('id'))
                            
    def remove_duplicates(self):
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
        path = d.split()
        return float(path[1]), float(path[2]), float(path[-2]), float(path[-1])
    
    def order_paths(self):
        # Créez une liste de tous les chemins
        paths = [(element.get('d'), element.get('style'), *self.get_first_and_last_point(element.get('d'))) for element in self.svg.selection.filter(inkex.PathElement) if element.get('d') is not None]

        # Calculez la distance de chaque point de départ à (0,0)
        distances = [np.sqrt(path[2]**2 + path[3]**2) for path in paths]

        # Trouvez l'index du chemin le plus proche de (0,0)
        start_index = np.argmin(distances)

        # Choisissez ce point comme point de départ et retirez-le de la liste des chemins
        start_point = paths[start_index][4:6]
        ordered_paths = [paths.pop(start_index)]

        while paths:
            # Trouvez le chemin le plus proche, en considérant à la fois le premier et le dernier point
            distances = [min(np.sqrt((start_point[0] - path[2])**2 + (start_point[1] - path[3])**2), np.sqrt((start_point[0] - path[4])**2 + (start_point[1] - path[5])**2)) for path in paths]
            nearest_path_index = np.argmin(distances)
            nearest_path = paths.pop(nearest_path_index)
            # Faites du dernier point du chemin le plus proche votre nouveau point de départ
            start_point = nearest_path[4:6]
            # Ajoutez le chemin le plus proche à la liste des chemins ordonnés
            ordered_paths.append(nearest_path)

        # supression des éléments de la sélection et du document
        for element in list(self.svg.selection):
            if element.get('d') is not None:
                parent = element.getparent()
                parent.remove(element)
                self.svg.selection.pop(element.get('id'))

        # Ajoutez les chemins triés à la sélection et au document
        NumChemin=1
        for path in ordered_paths:  
            new_element = inkex.PathElement(id="chemin"+str(NumChemin),
                                            d=path[0],
                                            style=path[1])
            self.document.getroot().append(new_element)
            self.svg.selection.add(new_element)
            NumChemin+=1
        
    def kill_other_inkscape_running(self):
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
            messagebox.showwarning('Attention !', 'Vous devez ouvrir un fichier avant de lancer l\'extension.')
            return
        
        # % Sélectionne tout si demandé
        if self.options.ToutSelectionner or (not self.svg.selected) :
            for element in self.svg.descendants():
                if not isinstance(element, inkex.Group) and not isinstance(element, inkex.TextElement): # pas les groupes pour éviter une redondance
                    self.svg.selection.add(element)
            
        # % Découpage en chemins simples
        for element in self.svg.selection.filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon):
            self.replace_with_subpaths(element)
        
        # % Suppression des doublons
        self.remove_duplicates()   
        
        # % Optimisation du parcours
        self.order_paths()
                    
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

            



# =================================
if __name__ == '__main__':
    e = OptimLaser()
    e.run()
