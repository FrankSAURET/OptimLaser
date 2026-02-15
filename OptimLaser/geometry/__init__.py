"""
Module de géométrie - Primitives géométriques et opérations

Contient les classes de base pour représenter et manipuler les primitives
géométriques : points, vecteurs, segments, arcs et courbes de Bézier.
"""

import math
from typing import Optional, List
from dataclasses import dataclass

__all__ = ['Point', 'Vector', 'Segment', 'Arc', 'BezierCurve']


@dataclass
class Point:
    """
    Représente un point 2D avec coordonnées flottantes.
    
    Attributes:
        x (float): Coordonnée X
        y (float): Coordonnée Y
    """
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        """
        Calcule la distance euclidienne vers un autre point.
        
        Args:
            other: Le point cible
            
        Returns:
            La distance euclidienne
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def __hash__(self):
        return hash((round(self.x, 9), round(self.y, 9)))
    
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9
    
    def __repr__(self):
        return f"Point({self.x:.3f}, {self.y:.3f})"
    
    def __iter__(self):
        """Permet de déplier le point en tuple : x, y = point"""
        return iter((self.x, self.y))


@dataclass
class Vector:
    """
    Représente un vecteur 2D.
    
    Attributes:
        x (float): Composante X
        y (float): Composante Y
    """
    x: float
    y: float
    
    @property
    def magnitude(self) -> float:
        """Retourne la norme du vecteur"""
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalize(self) -> 'Vector':
        """Retourne un vecteur normalisé (norme = 1)"""
        mag = self.magnitude
        if mag == 0:
            return Vector(0, 0)
        return Vector(self.x / mag, self.y / mag)
    
    def dot_product(self, other: 'Vector') -> float:
        """Calcule le produit scalaire avec un autre vecteur"""
        return self.x * other.x + self.y * other.y
    
    def cross_product(self, other: 'Vector') -> float:
        """Calcule le produit vectoriel (composante Z en 2D)"""
        return self.x * other.y - self.y * other.x
    
    def perpendicular(self) -> 'Vector':
        """Retourne un vecteur perpendiculaire (90° dans le sens trigonométrique)"""
        return Vector(-self.y, self.x)
    
    def __repr__(self):
        return f"Vector({self.x:.3f}, {self.y:.3f})"


class Segment:
    """
    Représente un segment de droite 2D.
    
    Attributes:
        start (Point): Point de départ
        end (Point): Point d'arrivée
    """
    
    def __init__(self, start: Point, end: Point):
        """
        Initialise un segment.
        
        Args:
            start: Point de départ
            end: Point d'arrivée
        """
        self.start = start
        self.end = end
    
    @property
    def length(self) -> float:
        """Retourne la longueur du segment"""
        return self.start.distance_to(self.end)
    
    @property
    def direction(self) -> Vector:
        """Retourne le vecteur direction normalisé"""
        vec = Vector(self.end.x - self.start.x, self.end.y - self.start.y)
        return vec.normalize()
    
    def get_point_at(self, t: float) -> Point:
        """
        Retourne le point à paramètre t ∈ [0, 1].
        t=0 → point de départ, t=1 → point d'arrivée
        
        Args:
            t: Paramètre entre 0 et 1
            
        Returns:
            Le point à cette position
        """
        return Point(
            self.start.x + t * (self.end.x - self.start.x),
            self.start.y + t * (self.end.y - self.start.y)
        )
    
    def point_to_segment_distance(self, point: Point) -> float:
        """
        Calcule la distance d'un point au segment (projection).
        
        Args:
            point: Le point à tester
            
        Returns:
            La distance minimale
        """
        seg_len_sq = self.length ** 2
        if seg_len_sq == 0:
            return point.distance_to(self.start)
        
        # Projection du point sur la ligne infinie du segment
        vec_to_point = Vector(point.x - self.start.x, point.y - self.start.y)
        seg_vec = Vector(self.end.x - self.start.x, self.end.y - self.start.y)
        
        t = max(0, min(1, vec_to_point.dot_product(seg_vec) / seg_len_sq))
        closest = self.get_point_at(t)
        return point.distance_to(closest)
    
    def distance_to_segment(self, other: 'Segment') -> float:
        """
        Calcule la distance minimale entre deux segments.
        
        Args:
            other: L'autre segment
            
        Returns:
            La distance minimale
        """
        # Distances entre chaque paire d'extrémités
        dists = [
            self.start.distance_to(other.start),
            self.start.distance_to(other.end),
            self.end.distance_to(other.start),
            self.end.distance_to(other.end),
            self.point_to_segment_distance(other.start),
            self.point_to_segment_distance(other.end),
            other.point_to_segment_distance(self.start),
            other.point_to_segment_distance(self.end),
        ]
        return min(dists)
    
    def is_collinear_with(self, other: 'Segment', tolerance: float = 0.01) -> bool:
        """
        Vérifie si deux segments sont colinéaires (sur la même droite).
        
        Args:
            other: L'autre segment
            tolerance: Tolérance pour la distance perpendiculaire
            
        Returns:
            True si les segments sont colinéaires
        """
        # Calculer la distance perpendiculaire entre les deux droites
        # Un segment est colinéaire si ses extrémités sont proches de la droite de l'autre
        dist_start_to_line = self.point_to_segment_distance(other.start)
        dist_end_to_line = self.point_to_segment_distance(other.end)
        
        # ET vérifier aussi dans l'autre sens
        dist_other_start = other.point_to_segment_distance(self.start)
        dist_other_end = other.point_to_segment_distance(self.end)
        
        # Si les extrémités sont proches de la ligne (considérée infinie),
        # alors les segments sont colinéaires
        return ((dist_start_to_line < tolerance or dist_end_to_line < tolerance) and
                (dist_other_start < tolerance or dist_other_end < tolerance))
    
    def overlaps_with(self, other: 'Segment', tolerance: float = 0.01) -> bool:
        """
        Vérifie si deux segments se chevauchent.
        
        Args:
            other: L'autre segment
            tolerance: Tolérance spatiale
            
        Returns:
            True si les segments se chevauchent
        """
        if not self.is_collinear_with(other, tolerance):
            return False
        
        # Projeter tous les points sur la droite du premier segment
        seg_vec = Vector(self.end.x - self.start.x, self.end.y - self.start.y)
        seg_len = self.length
        
        if seg_len == 0:
            return self.start.distance_to(other.start) < tolerance
        
        seg_vec_norm = seg_vec.normalize()
        
        def project(p: Point) -> float:
            vec = Vector(p.x - self.start.x, p.y - self.start.y)
            return vec.dot_product(seg_vec_norm)
        
        # Projections
        p1_start = project(self.start)
        p1_end = project(self.end)
        p2_start = project(other.start)
        p2_end = project(other.end)
        
        # Ordonner les projections
        p1_min, p1_max = min(p1_start, p1_end), max(p1_start, p1_end)
        p2_min, p2_max = min(p2_start, p2_end), max(p2_start, p2_end)
        
        # Vérifier le chevauchement
        overlap_start = max(p1_min, p2_min)
        overlap_end = min(p1_max, p2_max)
        
        return overlap_start <= overlap_end + tolerance
    
    def __repr__(self):
        return f"Segment({self.start} → {self.end})"


class Arc:
    """
    Représente un arc elliptique (SVG spec).
    
    Attributes:
        start (Point): Point de départ
        end (Point): Point d'arrivée
        rx (float): Rayon X de l'ellipse
        ry (float): Rayon Y de l'ellipse
        x_axis_rotation (float): Rotation de l'axe X en degrés
        large_arc (bool): Flag "large arc"
        sweep (bool): Flag "sweep"
    """
    
    def __init__(self, start: Point, end: Point, rx: float, ry: float,
                 x_axis_rotation: float = 0, large_arc: bool = False,
                 sweep: bool = False):
        """
        Initialise un arc.
        
        Args:
            start: Point de départ
            end: Point d'arrivée
            rx: Rayon X de l'ellipse
            ry: Rayon Y de l'ellipse
            x_axis_rotation: Rotation de l'axe X (défaut: 0°)
            large_arc: Flag "large arc" (défaut: False)
            sweep: Flag "sweep" (défaut: False)
        """
        self.start = start
        self.end = end
        self.rx = max(0.001, rx)  # Éviter les rayons nuls
        self.ry = max(0.001, ry)
        self.x_axis_rotation = x_axis_rotation
        self.large_arc = large_arc
        self.sweep = sweep
    
    def is_similar_to(self, other: 'Arc', tolerance: float = 0.01) -> bool:
        """
        Vérifie si deux arcs sont similaires (mêmes extrémités et propriétés proches).
        
        Args:
            other: L'autre arc
            tolerance: Tolérance relative pour les rayons
            
        Returns:
            True si les arcs sont similaires
        """
        # Vérifier les extrémités
        start_dist = self.start.distance_to(other.start)
        end_dist = self.end.distance_to(other.end)
        
        if start_dist > tolerance * 10 or end_dist > tolerance * 10:
            return False
        
        # Vérifier les rayons (tolérance relative)
        rx_diff = abs(self.rx - other.rx) / max(self.rx, other.rx, 0.001)
        ry_diff = abs(self.ry - other.ry) / max(self.ry, other.ry, 0.001)
        
        # Vérifier la rotation
        rot_diff = abs(self.x_axis_rotation - other.x_axis_rotation) % 360
        rot_diff = min(rot_diff, 360 - rot_diff)
        
        # Vérifier les flags
        flags_same = (self.large_arc == other.large_arc and
                     self.sweep == other.sweep)
        
        return (rx_diff < tolerance and ry_diff < tolerance and
                rot_diff < 5.0 and flags_same)
    
    def __repr__(self):
        return f"Arc({self.start} → {self.end}, rx={self.rx:.1f}, ry={self.ry:.1f})"


class BezierCurve:
    """
    Représente une courbe de Bézier (cubique ou quadratique).
    
    Attributes:
        start (Point): Point de départ
        end (Point): Point d'arrivée
        control1 (Point): Premier point de contrôle
        control2 (Optional[Point]): Deuxième point de contrôle (pour courbes cubiques)
    """
    
    def __init__(self, start: Point, end: Point, control1: Point,
                 control2: Optional[Point] = None):
        """
        Initialise une courbe de Bézier.
        
        Args:
            start: Point de départ
            end: Point d'arrivée
            control1: Premier point de contrôle
            control2: Deuxième point de contrôle (None pour quadratique)
        """
        self.start = start
        self.end = end
        self.control1 = control1
        self.control2 = control2
        self.is_quadratic = control2 is None
    
    def get_point_at(self, t: float) -> Point:
        """
        Retourne le point à paramètre t ∈ [0, 1].
        
        Args:
            t: Paramètre entre 0 et 1
            
        Returns:
            Le point sur la courbe
        """
        mt = 1 - t
        
        if self.is_quadratic:
            # Courbe quadratique : B(t) = (1-t)² P0 + 2(1-t)t P1 + t² P2
            mt2 = mt * mt
            t2 = t * t
            tmt = 2 * t * mt
            
            x = mt2 * self.start.x + tmt * self.control1.x + t2 * self.end.x
            y = mt2 * self.start.y + tmt * self.control1.y + t2 * self.end.y
        else:
            # Courbe cubique : B(t) = (1-t)³ P0 + 3(1-t)²t P1 + 3(1-t)t² P2 + t³ P3
            mt3 = mt * mt * mt
            t3 = t * t * t
            mt2 = mt * mt
            t2 = t * t
            
            x = (mt3 * self.start.x +
                 3 * mt2 * t * self.control1.x +
                 3 * mt * t2 * self.control2.x +
                 t3 * self.end.x)
            y = (mt3 * self.start.y +
                 3 * mt2 * t * self.control1.y +
                 3 * mt * t2 * self.control2.y +
                 t3 * self.end.y)
        
        return Point(x, y)
    
    def get_tangent_at(self, t: float) -> Vector:
        """
        Retourne le vecteur tangent à paramètre t.
        
        Args:
            t: Paramètre entre 0 et 1
            
        Returns:
            Le vecteur tangent
        """
        mt = 1 - t
        
        if self.is_quadratic:
            # Dérivée : B'(t) = 2(1-t)(P1 - P0) + 2t(P2 - P1)
            tx = (2 * mt * (self.control1.x - self.start.x) +
                  2 * t * (self.end.x - self.control1.x))
            ty = (2 * mt * (self.control1.y - self.start.y) +
                  2 * t * (self.end.y - self.control1.y))
        else:
            # Dérivée cubique
            mt2 = mt * mt
            t2 = t * t
            
            tx = (3 * mt2 * (self.control1.x - self.start.x) +
                  6 * mt * t * (self.control2.x - self.control1.x) +
                  3 * t2 * (self.end.x - self.control2.x))
            ty = (3 * mt2 * (self.control1.y - self.start.y) +
                  6 * mt * t * (self.control2.y - self.control1.y) +
                  3 * t2 * (self.end.y - self.control2.y))
        
        return Vector(tx, ty).normalize()
    
    def sample_points(self, num_samples: int = 20) -> List[Point]:
        """
        Échantillonne la courbe en points régulièrement espacés.
        
        Args:
            num_samples: Nombre de points à générer
            
        Returns:
            Liste des points échantillonnés
        """
        return [self.get_point_at(i / (num_samples - 1))
                for i in range(num_samples)]
    
    def is_similar_to(self, other: 'BezierCurve', tolerance: float = 0.01) -> bool:
        """
        Vérifie si deux courbes de Bézier sont similaires.
        
        Args:
            other: L'autre courbe
            tolerance: Tolérance pour la distance aux points de contrôle
            
        Returns:
            True si les courbes sont similaires
        """
        # Vérifier les extrémités
        start_dist = self.start.distance_to(other.start)
        end_dist = self.end.distance_to(other.end)
        
        if start_dist > tolerance * 10 or end_dist > tolerance * 10:
            return False
        
        # Vérifier les points de contrôle
        ctrl1_dist = self.control1.distance_to(other.control1)
        
        if self.is_quadratic and other.is_quadratic:
            return ctrl1_dist < tolerance * 5
        elif not self.is_quadratic and not other.is_quadratic:
            ctrl2_dist = self.control2.distance_to(other.control2)
            return ctrl1_dist < tolerance * 5 and ctrl2_dist < tolerance * 5
        
        return False
    
    def __repr__(self):
        curve_type = "Quadratic" if self.is_quadratic else "Cubic"
        return f"BezierCurve({curve_type}, {self.start} → {self.end})"
