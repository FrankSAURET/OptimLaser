"""
Module de suppression des doublons - Détection et fusion de segments superposés

Gère la détection avancée des doublons pour tous les types de géométries :
lignes, arcs, et courbes de Bézier, y compris les chevauchements partiels.
"""

import math
from typing import List, Set, Dict, Tuple, Optional
from dataclasses import dataclass
try:
    from .geometry import Point, Segment, Arc, BezierCurve, Vector
except ImportError:
    from geometry import Point, Segment, Arc, BezierCurve, Vector

__all__ = ['DuplicateRemover', 'OverlapInfo']



@dataclass
class OverlapInfo:
    """
    Informations sur le chevauchement entre deux segments.
    
    Attributes:
        segment1_id (str): ID du premier segment
        segment2_id (str): ID du deuxième segment
        overlap_ratio (float): Ratio de chevauchement (0.0 à 1.0)
        merge_point1 (Point): Premier point de fusion
        merge_point2 (Point): Deuxième point de fusion
    """
    segment1_id: str
    segment2_id: str
    overlap_ratio: float
    merge_point1: Point
    merge_point2: Point


class DuplicateRemover:
    """
    Détecteur et fusionneur de doublons géométriques.
    
    Gère la détection de segments superposés, y compris :
    - Doublons exacts
    - Chevauchements partiels
    - Segments parallèles proches (selon tolérance)
    - Courbes similaires (arcs, Bézier)
    """
    
    def __init__(self, tolerance: float = 0.1, enable_partial_overlap: bool = True,
                 overlap_threshold: float = 0.7):
        """
        Initialise le détecteur de doublons.
        
        Args:
            tolerance: Tolérance spatiale en unités document
            enable_partial_overlap: Activer la détection de chevauchements partiels
            overlap_threshold: Ratio minimum de chevauchement pour considérer comme doublons
        """
        self.tolerance = tolerance
        self.enable_partial_overlap = enable_partial_overlap
        self.overlap_threshold = overlap_threshold
    
    def find_duplicate_line_segments(self, segments: List[Dict]) -> List[OverlapInfo]:
        """
        Trouve les segments de droite superposés.
        
        Args:
            segments: Liste de dictionnaires avec clés 'id', 'start', 'end', 'color'
            
        Returns:
            Liste des chevauchements détectés
        """
        overlaps = []
        
        # Grouper par couleur
        by_color = {}
        for seg in segments:
            color = seg.get('color', '#000000')
            if color not in by_color:
                by_color[color] = []
            by_color[color].append(seg)
        
        # Analyser chaque couleur
        for color, color_segs in by_color.items():
            # Grouper par orientation
            horizontal = [s for s in color_segs if abs(s['start'].y - s['end'].y) < self.tolerance]
            vertical = [s for s in color_segs if abs(s['start'].x - s['end'].x) < self.tolerance]
            diagonal = [s for s in color_segs if s not in horizontal and s not in vertical]
            
            # Analyser chaque groupe
            for group in [horizontal, vertical, diagonal]:
                overlaps.extend(self._find_overlapping_lines_in_group(group))
        
        return overlaps
    
    def _find_overlapping_lines_in_group(self, segments: List[Dict]) -> List[OverlapInfo]:
        """
        Trouve les chevauchements dans un groupe de lignes orientées similairement.
        
        Args:
            segments: Segments alignés
            
        Returns:
            Liste des chevauchements
        """
        overlaps = []
        
        for i, seg1 in enumerate(segments):
            for j, seg2 in enumerate(segments):
                if i >= j:
                    continue
                
                seg_obj1 = Segment(seg1['start'], seg1['end'])
                seg_obj2 = Segment(seg2['start'], seg2['end'])
                
                # Vérifier la colinéarité
                if not seg_obj1.is_collinear_with(seg_obj2, self.tolerance):
                    continue
                
                # Vérifier le chevauchement
                if not seg_obj1.overlaps_with(seg_obj2, self.tolerance):
                    continue
                
                # Calculer le ratio de chevauchement
                overlap_ratio = self._calculate_overlap_ratio(seg1, seg2)
                
                if overlap_ratio >= self.overlap_threshold:
                    # Déterminer les points de fusion
                    merge_start, merge_end = self._get_merge_points(seg1, seg2)
                    
                    overlaps.append(OverlapInfo(
                        segment1_id=seg1['id'],
                        segment2_id=seg2['id'],
                        overlap_ratio=overlap_ratio,
                        merge_point1=merge_start,
                        merge_point2=merge_end
                    ))
        
        return overlaps
    
    def _calculate_overlap_ratio(self, seg1: Dict, seg2: Dict) -> float:
        """
        Calcule le ratio de chevauchement entre deux segments colinéaires.
        
        Args:
            seg1: Premier segment
            seg2: Deuxième segment
            
        Returns:
            Ratio entre 0 et 1
        """
        seg_obj1 = Segment(seg1['start'], seg1['end'])
        seg_obj2 = Segment(seg2['start'], seg2['end'])
        
        len1 = seg_obj1.length
        len2 = seg_obj2.length
        
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Projeter tous les points sur la droite du premier segment
        seg_vec = Vector(seg1['end'].x - seg1['start'].x,
                        seg1['end'].y - seg1['start'].y)
        seg_vec = seg_vec.normalize()
        
        def project(p: Point) -> float:
            vec = Vector(p.x - seg1['start'].x, p.y - seg1['start'].y)
            return vec.dot_product(seg_vec)
        
        p1_start, p1_end = project(seg1['start']), project(seg1['end'])
        p2_start, p2_end = project(seg2['start']), project(seg2['end'])
        
        # Normaliser les projections
        if p1_start > p1_end:
            p1_start, p1_end = p1_end, p1_start
        if p2_start > p2_end:
            p2_start, p2_end = p2_end, p2_start
        
        # Calculer le chevauchement
        overlap_start = max(p1_start, p2_start)
        overlap_end = min(p1_end, p2_end)
        overlap_len = max(0, overlap_end - overlap_start)
        
        # Ratio par rapport au segment le plus court
        min_len = min(len1, len2)
        return overlap_len / min_len if min_len > 0 else 0.0
    
    def _get_merge_points(self, seg1: Dict, seg2: Dict) -> Tuple[Point, Point]:
        """
        Détermine les points extrêmes pour la fusion de deux segments.
        
        Args:
            seg1: Premier segment
            seg2: Deuxième segment
            
        Returns:
            Tuple (point_début, point_fin) du segment fusionné
        """
        seg_vec = Vector(seg1['end'].x - seg1['start'].x,
                        seg1['end'].y - seg1['start'].y)
        seg_vec = seg_vec.normalize()
        
        def project(p: Point) -> float:
            vec = Vector(p.x - seg1['start'].x, p.y - seg1['start'].y)
            return vec.dot_product(seg_vec)
        
        points = [
            (project(seg1['start']), seg1['start']),
            (project(seg1['end']), seg1['end']),
            (project(seg2['start']), seg2['start']),
            (project(seg2['end']), seg2['end']),
        ]
        
        points.sort(key=lambda x: x[0])
        
        return points[0][1], points[-1][1]
    
    def find_duplicate_arcs(self, arcs: List[Dict]) -> List[OverlapInfo]:
        """
        Trouve les arcs superposés.
        
        Args:
            arcs: Liste de dictionnaires avec clés 'id', 'start', 'end', 'arc_obj', 'color'
            
        Returns:
            Liste des chevauchements détectés
        """
        overlaps = []
        
        for i, arc1 in enumerate(arcs):
            for j, arc2 in enumerate(arcs):
                if i >= j:
                    continue
                
                if arc1.get('color') != arc2.get('color'):
                    continue
                
                arc_obj1: Arc = arc1.get('arc_obj')
                arc_obj2: Arc = arc2.get('arc_obj')
                
                if arc_obj1 and arc_obj2 and arc_obj1.is_similar_to(arc_obj2, self.tolerance):
                    overlaps.append(OverlapInfo(
                        segment1_id=arc1['id'],
                        segment2_id=arc2['id'],
                        overlap_ratio=1.0,
                        merge_point1=arc1['start'],
                        merge_point2=arc1['end']
                    ))
        
        return overlaps
    
    def find_duplicate_bezier_curves(self, curves: List[Dict]) -> List[OverlapInfo]:
        """
        Trouve les courbes de Bézier superposées.
        Calcule le ratio de chevauchement réel.
        
        Args:
            curves: Liste de dictionnaires avec clés 'id', 'curve_obj', 'color'
            
        Returns:
            Liste des chevauchements détectés
        """
        overlaps = []
        
        for i, curve1 in enumerate(curves):
            for j, curve2 in enumerate(curves):
                if i >= j:
                    continue
                
                if curve1.get('color') != curve2.get('color'):
                    continue
                
                bezier1: BezierCurve = curve1.get('curve_obj')
                bezier2: BezierCurve = curve2.get('curve_obj')
                
                if not bezier1 or not bezier2:
                    continue
                
                # Calculer le ratio de chevauchement
                overlap_ratio = self._calculate_bezier_overlap(bezier1, bezier2)
                
                # Si chevauchement détecté (>0)
                if overlap_ratio > 0:
                    overlaps.append(OverlapInfo(
                        segment1_id=curve1['id'],
                        segment2_id=curve2['id'],
                        overlap_ratio=overlap_ratio,
                        merge_point1=bezier1.start,
                        merge_point2=bezier1.end
                    ))
        
        return overlaps
    
    def _calculate_bezier_overlap(self, bezier1: BezierCurve, bezier2: BezierCurve) -> float:
        """
        Calcule le ratio de chevauchement entre deux courbes de Bézier.
        Compare les points de la courbe.
        
        Args:
            bezier1: Première courbe
            bezier2: Deuxième courbe
            
        Returns:
            Ratio de chevauchement (0.0 à 1.0)
        """
        try:
            # Échantillonner les deux courbes et comparer les points
            samples = 50  # Beaucoup de points pour meilleure précision
            matching_points = 0
            
            for i in range(samples + 1):
                t = i / samples
                
                # Obtenir les points sur les deux courbes
                p1 = bezier1.get_point_at(t)
                p2 = bezier2.get_point_at(t)
                
                # Distance entre les points - tolérance TRÈS grande pour debugging
                dist = p1.distance_to(p2)
                
                # Si les points sont proches, compter comme match
                # Tolérance très grande pour permettre les duplicatas avec petites variations
                distance_threshold = max(5.0, self.tolerance * 500)
                if dist < distance_threshold:
                    matching_points += 1
            
            # Calculer le ratio
            overlap_ratio = matching_points / (samples + 1)
            
            # Si au moins 90% des points correspondent, c'est un chevauchement complet
            if overlap_ratio >= 0.90:
                return 1.0
            
            # Si au moins 10%, c'est un chevauchement partiel (très permissif)
            elif overlap_ratio >= 0.1:
                return overlap_ratio
            
            return 0.0
        except Exception as e:
            return 0.0
    
    def find_all_duplicates(self, lines: List[Dict] = None,
                           arcs: List[Dict] = None,
                           curves: List[Dict] = None) -> Dict[str, List[OverlapInfo]]:
        """
        Trouve tous les doublons dans un ensemble de segments.
        
        Args:
            lines: Liste de segments de droite
            arcs: Liste d'arcs
            curves: Liste de courbes de Bézier
            
        Returns:
            Dictionnaire {'lines': [...], 'arcs': [...], 'curves': [...]}
        """
        result = {
            'lines': self.find_duplicate_line_segments(lines or []),
            'arcs': self.find_duplicate_arcs(arcs or []),
            'curves': self.find_duplicate_bezier_curves(curves or [])
        }
        return result
