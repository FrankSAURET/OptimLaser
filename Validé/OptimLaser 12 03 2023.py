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
from inkex.transforms import Transform
from xml.etree import ElementTree


class OptimLaser(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
    # region ungroup_deep
    # This part is fully copied from "ungroup_deep.py" which comes with inkscape. The author's license therefore applies
    @staticmethod
    def _merge_style(node, style):
        """Propagate style and transform to remove inheritance
        Originally from
        https://github.com/nikitakit/svg2sif/blob/master/synfig_prepare.py#L370
        """

        # Compose the style attribs
        this_style = node.style
        remaining_style = {}  # Style attributes that are not propagated

        # Filters should remain on the top ancestor
        non_propagated = ["filter"]
        for key in non_propagated:
            if key in this_style.keys():
                remaining_style[key] = this_style[key]
                del this_style[key]

        # Create a copy of the parent style, and merge this style into it
        parent_style_copy = style.copy()
        parent_style_copy.update(this_style)
        this_style = parent_style_copy

        # Merge in any attributes outside of the style
        style_attribs = ["fill", "stroke"]
        for attrib in style_attribs:
            if node.get(attrib):
                this_style[attrib] = node.get(attrib)
                del node.attrib[attrib]

        if isinstance(node, (SvgDocumentElement, Anchor, Group, Switch)):
            # Leave only non-propagating style attributes
            if not remaining_style:
                if "style" in node.keys():
                    del node.attrib["style"]
            else:
                node.style = remaining_style

        else:
            # This element is not a container

            # Merge remaining_style into this_style
            this_style.update(remaining_style)

            # Set the element's style attribs
            node.style = this_style

    def _merge_clippath(self, node, clippathurl):
        if clippathurl and clippathurl != "none":
            node_transform = node.transform
            if node_transform:
                # Clip-paths on nodes with a transform have the transform
                # applied to the clipPath as well, which we don't want.  So, we
                # create new clipPath element with references to all existing
                # clippath subelements, but with the inverse transform applied
                new_clippath = self.svg.defs.add(
                    ClipPath(clipPathUnits="userSpaceOnUse")
                )
                new_clippath.set_random_id("clipPath")
                clippath = self.svg.getElementById(clippathurl[5:-1])
                for child in clippath.iterchildren():
                    new_clippath.add(Use.new(child, 0, 0))

                # Set the clippathurl to be the one with the inverse transform
                clippathurl = "url(#" + new_clippath.get("id") + ")"

            # Reference the parent clip-path to keep clipping intersection
            # Find end of clip-path chain and add reference there
            node_clippathurl = node.get("clip-path")
            while node_clippathurl:
                node = self.svg.getElementById(node_clippathurl[5:-1])
                node_clippathurl = node.get("clip-path")
            node.set("clip-path", clippathurl)
    
    # Flatten a group into same z-order as parent, propagating attribs
    def _ungroup(self, node):
        node_parent = node.getparent()
        node_index = list(node_parent).index(node)
        node_style = node.style

        node_transform = node.transform
        node_clippathurl = node.get("clip-path")
        for child in reversed(list(node)):
            if not isinstance(child, inkex.BaseElement):
                continue
            child.transform = node_transform @ child.transform

            if node.get("style") is not None:
                self._merge_style(child, node_style)
            self._merge_clippath(child, node_clippathurl)
            node_parent.insert(node_index, child)
        node_parent.remove(node)
        
    # Put all ungrouping restrictions here
    def _want_ungroup(self, node, depth, height):
        if (
            isinstance(node, Group)
            and node.getparent() is not None
            and height > 0
            and 0 <= depth <= 65535
        ):
            return True
        return False
    
    def _deep_ungroup(self, node):
        # using iteration instead of recursion to avoid hitting Python
        # max recursion depth limits, which is a problem in converted PDFs

        # Seed the queue (stack) with initial node
        q = [{"node": node, "depth": 0, "prev": {"height": None}, "height": None}]

        while q:
            current = q[-1]
            node = current["node"]
            depth = current["depth"]
            height = current["height"]

            # Recursion path
            if height is None:
                    # Don't enter non-graphical portions of the document
                    if isinstance(node, (NamedView, Defs, Metadata, ForeignObject)):
                        q.pop()

                    # Base case: Leaf node
                    if not isinstance(node, Group) or not list(node):
                        current["height"] = 0

                    # Recursive case: Group element with children
                    else:
                        depth += 1
                        for child in node.iterchildren():
                            q.append(
                                {
                                    "node": child,
                                    "prev": current,
                                    "depth": depth,
                                    "height": None,
                                }
                            )

            # Return path
            else:
                # Ungroup if desired
                if self._want_ungroup(node, depth, height):
                    self._ungroup(node)

                # Propagate (max) height up the call chain
                height += 1
                previous = current["prev"]
                prev_height = previous["height"]
                if prev_height is None or prev_height < height:
                    previous["height"] = height

                # Only process each node once
                q.pop()
    # End of the part copied from "ungroup_deep.py". The author's license therefore applies
    # endregion ungroup_deep

    def replace_with_subpaths(self, element):
        # Thank's to Kaalleen on inkscape forum
        # get info about the position in the svg document
        parent = element.getparent()
        index = parent.index(element)

        # get style and remove fill, the new elements are strokes
        style = element.style
        if not style('stroke', None):
            style['stroke'] = style('fill', None)
        style['fill'] = 'none'
        style['stroke-width'] = '0.1'  # Toutes les ligne en 0.1mm

        # path
        path = element.path.to_non_shorthand()
        # Supprimer les lignes de longueur nulle
        new_path = [path[0]]
        for i in range(1, len(path)):
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

        # generate new elements from sub paths
        segments = iter(path)
        end = []
        try:
            segment = next(segments)
            Premier = segment
            start = segment
            segmentPrev = segment
            segment = next(segments)  # Sauter le premier M

            while segment.letter != 'Z':
                end = []
                # Si ce sont des arcs les garder dans un même chemin
                if segment.letter != 'A':
                    end.append(segment)
                    segmentPrev = segment
                    segment = next(segments)
                else:
                    while segment.letter == 'A':
                        end.append(segment)
                        segmentPrev = segment
                        segment = next(segments)
                if len(end) > 0:    # Si il y a des segments à ajouter les dessinner
                    start = start.end_point(None, None)
                    start = inkex.paths.Move(start.x, start.y)
                    segment_path = inkex.Path([start] + end)
                    new_element = inkex.PathElement(d=str(segment_path),
                                                    style=str(style),
                                                    transform=str(element.transform))
                    parent.insert(index, new_element)
                start = segmentPrev  # Le nouveau segment de départ est le dernier segment de la série précédente
            # Fermer la forme si elle ne l'était pas
            if start.letter != 'C':
                debut = (start.x, start.y)
            else:
                debut = (start.x4, start.y4)
            fin = (Premier.x, Premier.y)
            if debut != fin:
                start = start.end_point(None, None)
                start = inkex.paths.Move(start.x, start.y)
                end = []
                Premier = inkex.paths.Line(Premier.x, Premier.y)
                end.append(Premier)
                segment_path = inkex.Path([start] + end)
                new_element = inkex.PathElement(d=str(segment_path),
                                                style=str(style),
                                                transform=str(element.transform))
                parent.insert(index, new_element)

        except StopIteration:  # Si la forme n'est pas fermée par un Z
            pass
            #inkex.utils.debug("=================== Stop itération ===================")  # **********************
            start = start.end_point(None, None)
            start = inkex.paths.Move(start.x, start.y)
            segment_path = inkex.Path([start] + end)
            new_element = inkex.PathElement(d=str(segment_path),
                                            style=str(style),
                                            transform=str(element.transform))
            parent.insert(index, new_element)
        # remove the original element
        parent.remove(element)

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
        # % Remplace tous les objets par des path
        # for element in self.svg.xpath('//svg:circle | //svg:ellipse | //svg:line | //svg:polygon | //svg:polyline | //svg:rect | //svg:use'):
        #     element.replace_with(inkex.elements._base.ShapeElement.to_path_element(element))
        #     inkex.utils.debug("Remplace tous les objets par des path")  # **********************
        
        # # Dégroupage général
        # for node in self.document.getroot():
        #     self._deep_ungroup(node)
        #     inkex.utils.debug("Dégroupage général")  # **********************
        
        # % Découpage en path simples
        # Sélectionner tous les éléments
        for layer in self.svg.getchildren():
            for element in layer.getchildren():
                self.svg.selection.add(element)

        for element in self.svg.selection.filter(inkex.Group, inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
            # groups: iterate through descendants
            if isinstance(element, inkex.Group):
                for shape_element in element.descendants().filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
                    self.replace_with_subpaths(shape_element)
            else:
                self.replace_with_subpaths(element)
        




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
            
        
        
        # Découpage du path en sous path
        # for element in self.svg.xpath('//svg:g | //svg:path'):
        #     if isinstance(element, inkex.Group):
        #         for shape_element in element.descendants().filter(inkex.PathElement, inkex.Circle, inkex.Ellipse, inkex.Rectangle):
        #             self.replace_with_subpaths(shape_element)
        #     else:
        #         self.replace_with_subpaths(element)
        
       
        # Explosion en chemin simples

        # Supprime les doublons
        #remove_duplicates(self)
    # --------------------------------------------


# =================================
if __name__ == '__main__':
    e = OptimLaser()
    e.run()
