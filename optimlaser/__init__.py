"""
OptimLaser - Extension Inkscape pour optimisation de découpe laser

Package principal contenant les modules de géométrie, optimisation et interface.
Version 2026.1 - Refactorisation complète avec architecture modulaire.
"""

__version__ = "2026.1"
__author__ = "Frank SAURET & GitHub Copilot"
__license__ = "GPLv2"

# Imports pour accès facile aux modules principaux
try:
    from .geometry import Point, Vector, Segment, Arc, BezierCurve
    from .duplicate_remover import DuplicateRemover
except ImportError:
    # Fallback pour les imports directs
    from geometry import Point, Vector, Segment, Arc, BezierCurve
    from duplicate_remover import DuplicateRemover

__all__ = [
    'Point', 'Vector', 'Segment', 'Arc', 'BezierCurve',
    'DuplicateRemover'
]
