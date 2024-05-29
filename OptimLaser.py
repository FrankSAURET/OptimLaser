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
#  0.2 mai 2024

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


class OptimLaser(inkex.Effect,inkex.EffectExtension):
    
    def __init__(self):
        self.seen_elems = []
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
        # self.arg_parser.add_argument("-i","--interp",
        #     type=inkex.Boolean, 
        #     dest="interp",
        #     default=False)
    

        Trouve = 0
        # Récupération de tous les chemins
        elems = self.svg.xpath('//svg:path')
        # Création d'une liste pour stocker les chemins déjà vus
        seen_elems = []
        keep_elems = []
        # Boucle sur tous les chemins
        somme=0
        for elem in elems:
            #inkex.utils.debug(f"elems final: {type(elem)}")
            # Récupération des données du chemin
            elem_data = elem.path.to_non_shorthand()
            # Création d'une clé pour stocker le chemin dans le dictionnaire
            elem_key = str(elem.path)
            # Si le chemin a déjà été vu, on le supprime
            if not elem_key in seen_elems:
                somme+=1
                seen_elems.append(elem_key)
                keep_elems.append(elem)

        elems=keep_elems    
        for elem in elems:       
            elem_key = str(elem.path) 
            #inkex.utils.debug(f"elems final: {elem_key}")
    
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
               
        # get style and remove fill, the new elements are strokes
        style = element.style
        if not style('stroke', None):
            style['stroke'] = style('fill', None)
        style['fill'] = 'none'

        # path
        path = element.path.to_non_shorthand()

        if len(path)>0:
            """
            # Supprimer les lignes de longueur nulle POURQUOI ???
            new_path = [path[0]] # récupération du move to initiale
            for i in range(1, len(path)): # parcours tous les éléments (lettres) du path
                segment = path[i]
                segmentPrev = path[i-1]
                if not isinstance(segmentPrev, inkex.paths.ZoneClose) and not isinstance(segment, inkex.paths.ZoneClose):
                    segment1 = segment.end_point(None, None)
                    segmentPrev1 = segmentPrev.end_point(None, None)
                    Fin = (segment1.x, segment1.y)
                    Debut = (segmentPrev1.x, segmentPrev1.y)
                if segment.letter == 'L':
                    if Fin != Debut:
                        new_path.append(segment)
                else:
                    new_path.append(segment)
            path = inkex.Path(new_path)
            """
            # Générer les nouveaux éléments à partir du chemin complet
            inkex.utils.debug(f"path : {path}")##########
            segments = iter(path)
            segment = next(segments)
            start = segment
            segment = next(segments) # Sauter le premier M
            end = []
            end.append(segment)
            while segment.letter != 'Z' and len(end) > 0:
                start = start.end_point(None, None)
                start = inkex.paths.Move(start.x, start.y)
                segment_path = inkex.Path([start] + end)
                new_element = inkex.PathElement(d=str(segment_path),
                                                style=str(style),
                                                transform=str(element.transform))
                parent.insert(index, new_element)
            # end = []
            # try:
            #     segment = next(segments)
            #     Premier = segment
            #     start = segment
            #     segmentPrev = segment
            #     segment = next(segments)  # Sauter le premier M
            #     inkex.utils.debug(f"segment : {segment}")##########

            #     while segment.letter != 'Z':
            #         end = []
            #         end.append(segment)
            #         inkex.utils.debug(f"end : {end}")
            #         segmentPrev = segment
            #         segment = next(segments)
            #         inkex.utils.debug(f"segmentPrev : {segmentPrev}")##########
            #         inkex.utils.debug(f"segment : {segment}")##########
            #         if len(end) > 0:    # Si il y a des segments à ajouter les dessinner
            #             start = start.end_point(None, None)
            #             start = inkex.paths.Move(start.x, start.y)
            #             segment_path = inkex.Path([start] + end)
            #             new_element = inkex.PathElement(d=str(segment_path),
            #                                             style=str(style),
            #                                             transform=str(element.transform))
                    
            #         self.remove_duplicates(new_element,segment_path,element)
            #         # inkex.utils.debug(f"Element 1 : {element.path.to_non_shorthand()}")  
                       
            #         start = segmentPrev  # Le nouveau segment de départ est le dernier segment de la série précédente
            #     # Fermer la forme si elle ne l'était pas
            #     if start.letter != 'C':
            #         debut = (start.x, start.y)
            #     else:
            #         debut = (start.x4, start.y4)
            #     fin = (Premier.x, Premier.y)
            #     if debut != fin:
            #         start = start.end_point(None, None)
            #         start = inkex.paths.Move(start.x, start.y)
            #         end = []
            #         Premier = inkex.paths.Line(Premier.x, Premier.y)
            #         end.append(Premier)
            #         segment_path = inkex.Path([start] + end)
            #         new_element = inkex.PathElement(d=str(segment_path),
            #                                         style=str(style),
            #                                         transform=str(element.transform))
                    
            #     self.remove_duplicates(new_element,segment_path,element) 
            #     # inkex.utils.debug(f"Element 2 : {element.path.to_non_shorthand()}")         

            # except StopIteration:  # Si la forme n'est pas fermée par un Z
            #     pass
            #     #inkex.utils.debug("=================== Stop itération ===================")  # **********************
            #     start = start.end_point(None, None)
            #     start = inkex.paths.Move(start.x, start.y)
            #     segment_path = inkex.Path([start] + end)
            #     new_element = inkex.PathElement(d=str(segment_path),
            #                                     style=str(style),
            #                                     transform=str(element.transform))
                
                # self.remove_duplicates(new_element,segment_path,element)
                # inkex.utils.debug(f"Element 3 : {element.path.to_non_shorthand()}")    
                    
            # remove the original element
            parent.remove(element)
                            
    def remove_duplicates(self):
        tolerance=self.options.tolerance
        
        coords=[]#one segmentx8 subarray for each path and subpath (paths and subpaths treated equally)
        pathNo=[]
        subPathNo=[]
        cPathNo=[]#counting alle paths and subpaths equally
        removeSegmentPath=[]
        removeSegmentSubPath=[]
        removeSegment_cPath=[]
        removeSegment=[]
        matchSegmentPath=[]
        matchSegmentSubPath=[]
        matchSegment_cPath=[]
        matchSegment=[]
        matchSegmentRev=[]
        
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
 
        if nFailed > 0:
            messagebox.showwarning('Attention', str(nFailed) + ' éléments sélectionnés n\'avaient pas de chemin. Les groupes, les éléments de forme et le texte seront ignorés.')
        if nInkEffect > 0:
            messagebox.showwarning('Attention', str(nInkEffect) + ' éléments sélectionnés ont un effet de chemin Inkscape appliqué. Ces éléments seront ignorés pour éviter des résultats confus. Appliquez Chemins->Objet vers chemin (Shift+Ctrl+C) et réessayez.')        
            
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
                            matchThisRev=False
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
                                            matchThisRev=True
                                            finalK=k
                                            lesstolc=lessTol[c]
                                        c+=1
                            
                            if matchThis:
                                coords[finalK][lesstolc,:]=-1000
                                removeSegmentPath.append(pathNo[finalK])
                                removeSegmentSubPath.append(subPathNo[finalK])
                                removeSegment_cPath.append(cPathNo[finalK])
                                removeSegment.append(lesstolc)
                                matchSegmentPath.append(pathNo[i])
                                matchSegmentSubPath.append(subPathNo[i])
                                matchSegment_cPath.append(cPathNo[i])
                                matchSegment.append(j)
                                matchSegmentRev.append(matchThisRev)        
                                        
                    k+=1
                j+=1
            i+=1
                
        #(interpolate remaining and) remove segments with a match
        if len(removeSegmentPath) > 0:          
            removeSegmentPath=np.array(removeSegmentPath)
            removeSegmentSubPath=np.array(removeSegmentSubPath)
            removeSegment_cPath=np.array(removeSegment_cPath)
            removeSegment=np.array(removeSegment)
            matchSegmentPath=np.array(matchSegmentPath)
            matchSegment_cPath=np.array(matchSegment_cPath)
            matchSegmentSubPath=np.array(matchSegmentSubPath)
            matchSegment=np.array(matchSegment)
            matchSegmentRev=np.array(matchSegmentRev)

            # #first interpolate remaining segment
            # if self.options.interp:
            #     idx=np.argsort(matchSegmentPath)
            #     matchSegmentPath=matchSegmentPath[idx]
            #     matchSegment_cPath=matchSegment_cPath[idx]
            #     matchSegmentSubPath=matchSegmentSubPath[idx]
            #     matchSegment=matchSegment[idx]
            #     matchSegmentRev=matchSegmentRev[idx]
            #     remSegmentPath=removeSegmentPath[idx]
            #     remSegment_cPath=removeSegment_cPath[idx]
            #     remSegment=removeSegment[idx]
                
            #     i=0
            #     for id, elem in self.svg.selection.id_dict().items():#each path         
            #         if not id in idsNotPath:
            #             if i in matchSegmentPath:           
            #                 idxi=np.argwhere(matchSegmentPath==i)
            #                 idxi=idxi.reshape(-1)
            #                 icMatch=matchSegment_cPath[idxi]
            #                 iSegMatch=matchSegment[idxi]
            #                 iSegMatchRev=matchSegmentRev[idxi]
            #                 iSubMatch=matchSegmentSubPath[idxi]
            #                 iSegRem=remSegment[idxi]
            #                 icRem=remSegment_cPath[idxi]
            #                 iPathRem=remSegmentPath[idxi]
            #                 new=[]
            #                 j=0
            #                 for sub in elem.path.to_superpath():#each subpath 
            #                     idxj=np.argwhere(iSubMatch==j)
            #                     idxj=idxj.reshape(-1)
            #                     this_cMatch=icMatch[idxj]
            #                     thisSegMatch=iSegMatch[idxj]
            #                     thisSegMatchRev=iSegMatchRev[idxj]                            
            #                     thisSegRem=iSegRem[idxj].reshape(-1)
            #                     this_cRem=icRem[idxj]
            #                     thisPathRem=iPathRem[idxj] 
            #                     k=0
            #                     while k<len(thisSegMatch):
                               
            #                         if thisSegMatchRev[k]==False:
            #                             x1interp=0.5*(sub[thisSegMatch[k]][1][0]+origCoords[this_cRem[k]][thisSegRem[k],0])
            #                             y1interp=0.5*(sub[thisSegMatch[k]][1][1]+origCoords[this_cRem[k]][thisSegRem[k],1])
            #                             cx1interp=0.5*(sub[thisSegMatch[k]][2][0]+origCoords[this_cRem[k]][thisSegRem[k],2])
            #                             cy1interp=0.5*(sub[thisSegMatch[k]][2][1]+origCoords[this_cRem[k]][thisSegRem[k],3])
            #                             x2interp=0.5*(sub[thisSegMatch[k]+1][1][0]+origCoords[this_cRem[k]][thisSegRem[k],6])
            #                             y2interp=0.5*(sub[thisSegMatch[k]+1][1][1]+origCoords[this_cRem[k]][thisSegRem[k],7])
            #                             cx2interp=0.5*(sub[thisSegMatch[k]+1][0][0]+origCoords[this_cRem[k]][thisSegRem[k],4])
            #                             cy2interp=0.5*(sub[thisSegMatch[k]+1][0][1]+origCoords[this_cRem[k]][thisSegRem[k],5])
            #                         else:
            #                             x1interp=0.5*(sub[thisSegMatch[k]][1][0]+origCoords[this_cRem[k]][thisSegRem[k],6])
            #                             y1interp=0.5*(sub[thisSegMatch[k]][1][1]+origCoords[this_cRem[k]][thisSegRem[k],7])
            #                             cx1interp=0.5*(sub[thisSegMatch[k]][2][0]+origCoords[this_cRem[k]][thisSegRem[k],4])
            #                             cy1interp=0.5*(sub[thisSegMatch[k]][2][1]+origCoords[this_cRem[k]][thisSegRem[k],5])
            #                             x2interp=0.5*(sub[thisSegMatch[k]+1][1][0]+origCoords[this_cRem[k]][thisSegRem[k],0])
            #                             y2interp=0.5*(sub[thisSegMatch[k]+1][1][1]+origCoords[this_cRem[k]][thisSegRem[k],1])
            #                             cx2interp=0.5*(sub[thisSegMatch[k]+1][0][0]+origCoords[this_cRem[k]][thisSegRem[k],2])
            #                             cy2interp=0.5*(sub[thisSegMatch[k]+1][0][1]+origCoords[this_cRem[k]][thisSegRem[k],3])
                                    
            #                         sub[thisSegMatch[k]][1]=[x1interp,y1interp]
            #                         sub[thisSegMatch[k]][2]=[cx1interp,cy1interp]
            #                         sub[thisSegMatch[k]+1][1]=[x2interp,y2interp]
            #                         sub[thisSegMatch[k]+1][0]=[cx2interp,cy2interp]
                                                                      
            #                         if thisSegMatch[k]==0:
            #                             sub[thisSegMatch[k]][0]=[x1interp,y1interp]
            #                         if thisSegMatch[k]+1==len(sub)-1:
            #                             sub[thisSegMatch[k]+1][2]=[x2interp,y2interp]
            #                         k+=1

            #                     new.append(sub)
            #                     j+=1
                                
            #                 elem.path = CubicSuperPath(new).to_path(curves_only=True)
                            
            #             i+=1
            
            # #remove
            i=0
            for id, elem in self.svg.selection.id_dict().items():#each path 
                if not id in idsNotPath:
                    idx=np.argwhere(removeSegmentPath==i)              
                    if len(idx) > 0:
                        idx=idx.reshape(1,-1)
                        idx=idx[0]
                        new=[]
                        j=0
                        for sub in elem.path.to_superpath():#each subpath                       
                            thisSegRem=removeSegment[idx]
                            keepLast=False if len(sub)-2 in thisSegRem else True
                            keepNext2Last=False if len(sub)-3 in thisSegRem else True
                            thisSubPath=removeSegmentSubPath[idx]
                            idx2=np.argwhere(removeSegmentSubPath[idx]==j)                      
                            if len(idx2) > 0:
                                idx2=idx2.reshape(1,-1)
                                idx2=idx2[0]
                                thisSegRem=thisSegRem[idx2]
                                if len(thisSegRem) < len(sub)-1:#if any segment to be kept
                                    #find first segment
                                    k=0
                                    if 0 in thisSegRem:#remove first segment
                                        proceed=True
                                        while proceed:
                                            if k+1 in thisSegRem:
                                                k+=1
                                            else:
                                                proceed=False
                                        k+=1    
                                        new.append([sub[k]])
                                        if sub[k+1]!=new[-1][-1]:#avoid duplicated nodes
                                            new[-1].append(sub[k+1])
                                            new[-1][-1][0]=new[-1][-1][1]                                      
                                    else:
                                        new.append([sub[0]])
                                        if sub[1]!=new[-1][-1]:#avoid duplicated nodes
                                            new[-1].append(sub[1])
                                        k+=1
                                   
                                    #rest of segments
                                    while k<len(sub)-1:
                                        if k in thisSegRem:
                                            new[-1][-1][-1]=new[-1][-1][1]#stop subpath
                                            cut=True
                                            while cut:                                           
                                                if k+1 in thisSegRem:
                                                    k+=1
                                                else:
                                                    cut=False
                                            k+=1
                                            if k<len(sub)-1:
                                                #start new subpath, start by checking that last sub did contain more than one element
                                                if len(new[-1])==1: new.pop()
                                                new.append([sub[k]])#start new subpath
                                                new[-1][-1][0]=new[-1][-1][1]
                                                if sub[k+1]!=new[-1][-1]:#avoid duplicated nodes
                                                    new[-1].append(sub[k+1])
                                                k+=1
                                        else:
                                            if sub[k+1]!=new[-1][-1]:#avoid duplicated nodes
                                                new[-1].append(sub[k+1])
                                            k+=1
                                    if keepLast:
                                        if sub[-1]!=new[-1][-1]:#avoid duplicated nodes
                                            new[-1].append(sub[-1])

                                if len(new) > 0:
                                    if len(new[-1])==1: new.pop()   
                            else:
                                new.append(sub)#add as is
                             
                            j+=1
                                                                    
                        elem.path = CubicSuperPath(new).to_path(curves_only=True)
                    i+=1

    # --------------------------------------------
    def effect(self):
        # % Force la sauvegarde du fichier mais attention  il reste affiché comme si pas sauvé (impossible de faire un enregistre sous)
        current_file_name = self.document_path()
        # inkex.utils.debug("---------- Nom de fichier actuel : "+current_file_name)
        with open(current_file_name, 'wb') as output_file:
            self.save(output_file)       
        
        # % Sélectionne tout si demandé
        if self.options.ToutSelectionner or (not self.svg.selected) :
            # Sélectionner tous les éléments
            for layer in self.svg.getchildren():
                for element in layer.getchildren():
                    self.svg.selection.add(element)
        
        # # % Découpage en path simples
        # for element in self.svg.selection.filter(inkex.Group, inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
        #     # groups: iterate through descendants
        #     if isinstance(element, inkex.Group):
        #         for shape_element in element.descendants().filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
        #             self.replace_with_subpaths(shape_element)
        #     else:
        #         self.replace_with_subpaths(element)                              
        
        # # % Conversion en chemin
        # for element_id in self.svg.selection:
        #     element = self.svg.selection[element_id]
        #     if isinstance(element, ShapeElement):
        #         path = inkex.PathElement()
        #         path.set('d', str(inkex.paths.CubicSuperPath(element.get_path())))
        #         element.getparent().replace(element, path)
        
        # % Suppression des doublons
        self.remove_duplicates()   
            
        # % Sauvegarde du fichier modifié et ouverture dans une nouvelle occurence d'inkscape si demandé
        if self.options.SauvegarderSousDecoupe:
            # Sauvegarde du fichier modifié 
            current_file_name = self.document_path()
            base_name, extension = os.path.splitext(current_file_name)
            new_file_name = base_name + " - decoupe" + extension
            with open(new_file_name, 'wb') as output_file:
                self.save(output_file)
            # ouvre le fichier modifié dans une nouvelle occurence d'inkscape
            subprocess.Popen(["inkscape", new_file_name])



# =================================
if __name__ == '__main__':
    e = OptimLaser()
    e.run()
