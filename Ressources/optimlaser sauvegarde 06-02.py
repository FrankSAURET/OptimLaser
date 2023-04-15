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
from inkex import bezier, PathElement, CubicSuperPath


def convert_to_path(self, elem):
    """Convertit un élément  path

    Args:
        elem (inkex.elements._svg.SvgDocumentElement): élément à convertir
    """
    inkex.utils.debug("************************************************************")
    inkex.utils.debug("======== tag : "+str(elem.tag))

    # if elem.tag == inkex.addNS('path', 'svg'):
    #     return
    # ******* exemple sortie debug print ***** A virer *****
    inkex.utils.debug("======== type elem : "+str(type(elem)))
    inkex.utils.debug("======== elem : "+str(elem))

    #inkex.errormsg(_("This extension requires two selected paths."))
    # style = simplestyle.parseStyle(elem.attrib.get('style', ''))
    # if 'fill' in style:
    #     del style['fill']
    # if 'stroke' in style:
    #     style['fill'] = style['stroke']
    #     del style['stroke']
    # elem.attrib['style'] = simplestyle.formatStyle(style)
    #path_d = inkex.elements._base.ShapeElement.to_path_element(elem).path
    path_d = inkex.elements._base.ShapeElement.to_path_element(elem)
    inkex.utils.debug("======== path : "+str(path_d))

    self.svg.get_current_layer().append(path_d)
    inkex.utils.debug("======== elem2 : "+str(elem))
    # elem.clear()
    # elem.attrib['d'] = path_d

    # elem.tag = inkex.addNS('path', 'svg')


# def csp_subpath_ccw(subpath):
#     # Remove all zero length segments
#     #
#     s = 0
#     if (P(subpath[-1][1]) - P(subpath[0][1])).l2() > 1e-10:
#         subpath[-1][2] = subpath[-1][1]
#         subpath[0][0] = subpath[0][1]
#         subpath += [[subpath[0][1], subpath[0][1], subpath[0][1]]]
#     pl = subpath[-1][2]
#     for sp1 in subpath:
#         for p in sp1:
#             s += (p[0] - pl[0]) * (p[1] + pl[1])
#             pl = p
#     return s < 0


class OptimLaser(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)

    # --------------------------------------------
    def effect(self):
        drawable_elements = self.svg.xpath('//svg:circle | //svg:ellipse | //svg:line | '
                                           '//svg:polygon | //svg:polyline | //svg:rect | //svg:use')
        #for node in self.svg.selection.filter(inkex.Circle, inkex.Ellipse, inkex.Line, inkex.Polygon, inkex.Polyline, inkex.Rectangle, inkex.Use):

        #for node in  self.svg.xpath('//svg:path'):
        #for node in self.svg.selection.filter(inkex.PathElement):
        #for node in self.svg.selection.filter(inkex.Path):
        #for node in drawable_elements:
        #self.document.getroot().xpath('//*[not(self::svg:path)]', namespaces=inkex.NSS):
        #for node in self.svg.xpath('//*[not(svg:path)]'):
        for node in self.svg.xpath('//svg:circle | //svg:ellipse | //svg:line | //svg:polygon | //svg:polyline | //svg:rect | //svg:use'):
            convert_to_path(self, node)

    # --------------------------------------------


# =================================
if __name__ == '__main__':
    e = OptimLaser()
    e.run()
