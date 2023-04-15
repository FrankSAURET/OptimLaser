#!/usr/bin/env/python
'''
Codé par Frank SAURET janvier 2023

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
# - Optimisation du déplacement

# Todo
#

# Versions
#  0.1 Janvier 2023

__version__ = "0.1"

#from math import *
import os
import sys
import inkex
from simplepath import *
from lxml import etree
import simplestyle
import cubicsuperpath
import xml.etree.ElementTree as ET
from ungroup_deep import *
import copy
import numpy

class OptimLaser(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    def recursively_ungroup(self, node):
        if node.tag == inkex.addNS("g", "svg"):
            #tagname=node._base.BaseElement.tag_name()
            #inkex.utils.debug("======== tagname : "+str(tagname))
            for child in node:
                self.recursively_ungroup(child)
            parent = node.getparent()
            parent2 = node.ancestors(None, (1))
            inkex.utils.debug("======== parent : "+str(parent))
            inkex.utils.debug("======== parent2 : "+str(parent2))
            if parent is not None:
                index = parent.index(node)
                parent[index:index + 1] = node

    def remove_duplicates(self):
        Trouve = 0
        # Récupération de tous les chemins
        elems = self.svg.xpath('//svg:path')
        #inkex.utils.debug("======== elems : "+str(elems))

        # Création d'un dictionnaire pour stocker les chemins déjà vus
        seen_elems = {}

        # Boucle sur tous les chemins
        for elem in elems:
            # Récupération des données du chemin
            #elem_data = elem.path
            #inkex.utils.debug("======== elem_data : "+str(elem_data))
            # Création d'une clé pour stocker le chemin dans le dictionnaire

            elem_key = str(elem.path)
            #inkex.utils.debug("======== absolu : "+str(elem.path.to_absolute()))
            inkex.utils.debug("======== original : "+str(elem.path))
            #inkex.utils.debug("======== relatif : "+str(elem.path.to_relative()))
            #inkex.utils.debug("======== elem_key : "+elem_key)
            # Si le chemin a déjà été vu, on le supprime
            if elem_key in seen_elems:
                #inkex.utils.debug("======== Trouvé : "+elem_key)
                Trouve += 1
                #elem.delete()
                #elem.style['stroke-width'] = 2.0
            else:
                # Sinon, on l'ajoute au dictionnaire des chemins déjà vus
                seen_elems[elem_key] = True
        inkex.utils.debug("======== Trouvé : "+str(Trouve))
    # --------------------------------------------
    def effect(self):
        # Remplace tous les objets par des path
        for elem in self.svg.xpath('//svg:circle | //svg:ellipse | //svg:line | //svg:polygon | //svg:polyline | //svg:rect | //svg:use'):
            elem.replace_with(inkex.elements._base.ShapeElement.to_path_element(elem))

        # NbPath=0
        # for node in self.svg.xpath('//svg:path'):
        #     NbPath+=1
        #     minx, miny = node.bounding_box().minimum
        #     inkex.utils.debug("======== bounding box min avant: "+str(node.bounding_box().minimum))
        #     node.path.translate(-minx, -miny)
        #     node.path.to_relative()
        #     inkex.utils.debug("======== bounding box min aprés : "+str(node.bounding_box().minimum))
        # inkex.utils.debug("======== NbPath : "+str(NbPath))
        # for elem in self.svg.xpath('//svg:path'):
        #     minx, miny= elem.bounding_box().minimum
        #     elem.path.translate(-minx, -miny)
            
        # Dégroupage général
        # node_list = self.document.getroot().xpath("//svg:g", namespaces=inkex.NSS)
        # self.recursively_ungroup(node_list)
        for node in self.svg.xpath('//svg:g'):
            self.recursively_ungroup(node)
            #_want_ungroup=UngroupDeep._want_ungroup(self, elem, 0, None)
            #UngroupDeep._deep_ungroup(UngroupDeep,elem)
        # Explosion en chemin simples

        # Supprime les doublons
        #remove_duplicates(self)
    # --------------------------------------------


# =================================
if __name__ == '__main__':
    e = OptimLaser()
    e.run()
