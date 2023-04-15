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

### Todo
#  

### Versions
#  0.1 Janvier 2023 

__version__ = "0.1"

#from math import *
import os
import sys
import inkex
from simplepath import *
from lxml import etree

class OptimLaser(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)

    ###--------------------------------------------
    ### The    main function    called    by    the    inkscape    UI
    def effect(self):
        self.document.save()
        # Récupération du nom de fichier et de son extension
        file_path = sys.argv[-1]
        base_file, file_extension = os.path.splitext(file_path)
        file_name = os.path.basename(base_file)

        # Création du nouveau nom de fichier
        new_file_name = base_file + "- Decoupe" + file_extension

        # Enregistrement de la nouvelle version du fichier
        self.document.saveas(new_file_name)
        print(f"File saved as {new_file_name}")

###
if __name__ == '__main__':
    e = OptimLaser()
    e.run()