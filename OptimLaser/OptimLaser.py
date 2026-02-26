#!/usr/bin/env python3
"""
OptimLaser - Extension Inkscape
Optimisation avancée pour découpe laser

Auteur: Frank SAURET
Licence: GPLv2
"""

import inkex
from inkex import PathElement
import sys
import os
import math
import json
import subprocess
from lxml import etree
import platform
import re
from datetime import datetime
import warnings
from tkinter import messagebox
import gettext
import copy

# Configurer gettext pour l'internationalisation
_locale_dir = os.path.join(os.path.dirname(__file__), 'locale')
try:
    _translation = gettext.translation('OptimLaser', localedir=_locale_dir, fallback=True)
    _ = _translation.gettext
except Exception:
    def _(msg): return msg

# Extraction dynamique de la version depuis Info.json
import json
import os
info_path = os.path.join(os.path.dirname(__file__), 'Info.json')
try:
    with open(info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)
        __version__ = info.get('version', 'unknown')
except Exception:
    __version__ = 'unknown'

# Ajouter le chemin des modules
sys.path.insert(0, os.path.dirname(__file__))

try:
    # Tentative d'import en tant que package
    from geometry import Point, Segment, Arc, BezierCurve
    from duplicate_remover import DuplicateRemover
    from ui.gui import show_gui
except ImportError:
    # Fallback en imports absolus
    from geometry import Point, Segment, Arc, BezierCurve
    from duplicate_remover import DuplicateRemover
    from ui.gui import show_gui

class OptimLaser(inkex.EffectExtension):

    """Extension Inkscape pour l'optimisation de découpe laser"""
    _distance_cache = {}
    ListeDeGris = []
    
    def add_arguments(self, pars):
        """Ajoute les arguments de la ligne de commande (pour compatibilité)"""
        # Onglet fictif pour compatibilité .inx
        pars.add_argument("--tab", type=str, default="gui", help="Onglet actif")
    
    def effect(self):
        """Fonction principale de l'extension"""
        
        # Toujours afficher la GUI
        self._show_gui_and_apply()
    
    def _show_gui_and_apply(self):
        """Affiche la GUI et applique les paramètres"""
        
        # Chemin vers le fichier de config
        config_file = os.path.join(os.path.dirname(__file__), 'OptimLaser.json')
        
        params = {}
        
        def on_apply(gui_params):
            """Callback quand l'utilisateur clique sur Appliquer"""
            params.update(gui_params)
            
        def on_cancel():
            """Callback quand l'utilisateur clique sur Annuler"""
            sys.exit(0)
        
        # Afficher la GUI et récupérer l'instance
        result = show_gui(config_file=config_file, on_apply=on_apply, on_cancel=on_cancel)
        if isinstance(result, tuple):
            params_dict, self.gui_instance = result
            params.update(params_dict)
        else:
            # Compatibilité avec l'ancien format
            params.update(result)
            self.gui_instance = None
        
        if params:
            # Utiliser les paramètres de la GUI
            self.tolerance = params['tolerance']
            self.enable_partial_overlap = params['enable_partial_overlap']
            self.overlap_threshold = params['overlap_threshold']
            self.enable_global_optimization = params['enable_global_optimization']
            self.optimization_strategy = params['optimization_strategy']
            self.max_iterations = params['max_iterations']
            self.zonage_direction = params.get('zonage_direction', 'colonnes')
            self.zonage_size_mm = params.get('zonage_size_mm', 10.0)
            self.laser_speed = params['laser_speed']
            self.idle_speed = params['idle_speed']
            self.SupprimerCouleursNonGerees = params.get('SupprimerCouleursNonGerees', True)
            self.SauvegarderSousDecoupe = params.get('SauvegarderSousDecoupe', True)
            
            # Lancer l'optimisation
            self._run_optimization()
    
    def _update_progress_window(self, task_text=None):
        """Met à jour la fenêtre de progression
        
        Args:
            task_text: Texte de la tâche en cours à afficher (optionnel)
        """
        if hasattr(self, 'gui_instance') and self.gui_instance:
            self.gui_instance.update_progress(task_text)
  
    def save_gray_elements(self):
        """
        Sauvegarde les éléments gris (remplissage ou contour) et leur couche dans ListeDeGris.
        """
        self.ListeDeGris = []
        for element in self.svg.descendants():
            couche = self.find_layer(element)
            style = element.style
            style_save = element.style
            # Vérifier le remplissage gris
            fill_value = style.get('fill', None)
            is_gray_fill = False
            if fill_value and fill_value.lower() != 'none':
                fill_color = inkex.Color(style('fill', None))
                r, v, b = fill_color.to_rgb()
                if (r == v and r == b and v == b):
                    is_gray_fill = True
                    style['fill'] = 'none'
            # Vérifier le contour gris
            stroke_value = style.get('stroke', None)
            is_gray_stroke = False
            if stroke_value and stroke_value.lower() != 'none':
                try:
                    stroke_color = inkex.Color(style('stroke', None))
                    r, v, b = stroke_color.to_rgb()
                    if (r == v and r == b and v == b):
                        is_gray_stroke = True
                except Exception:
                    pass
            # Ajouter à ListeDeGris si l'un ou l'autre est gris
            if is_gray_fill or is_gray_stroke:
                self.ListeDeGris.append((copy.deepcopy(element), couche, style_save))
    
    def restore_gray_elements(self):
        """
        Replace les éléments gris sauvegardés dans ListeDeGris dans leur couche d'origine.
        Si la couleur du contour est une couleur de découpe (définie dans le JSON), elle devient transparente.
        """
        # Charger les couleurs de découpe depuis le JSON
        cutting_colors = set()
        json_path = os.path.join(os.path.dirname(__file__), 'OptimLaser.json')
        try:
            with open(json_path, 'r') as json_file:
                config = json.load(json_file)
                cutting_colors = {c.lower() for c in config.get('colors', [])}
        except Exception:
            pass

        compteur_gris = 0
        for element, couche, style in self.ListeDeGris:
            element.style = style
            # Renommer l'id du chemin
            element.set('id', f'chemin_gris{compteur_gris+1}')
            # Si le contour est une couleur de découpe, le rendre transparent
            stroke_value = style.get('stroke', None)
            if stroke_value and stroke_value.lower() != 'none':
                stroke_hex = stroke_value.lstrip('#').lower()
                if stroke_hex in cutting_colors:
                    element.style['stroke-opacity'] = '0'
            if couche is not None:
                # couche.append(element)
                couche.insert(compteur_gris, element)
            else:
                self.document.getroot().insert(compteur_gris, element)
            compteur_gris += 1

        self.ListeDeGris = []
                
    def remove_unmanaged_colors(self):
        """Supprime les éléments dont la couleur de trait n'est pas gérée par la découpeuse laser"""
        if not self.SupprimerCouleursNonGerees:
            return

        # Lecture de l'ordre des couleurs depuis le fichier JSON
        json_path = os.path.join(os.path.dirname(__file__), 'OptimLaser.json')
        color_order = []
        try:
            with open(json_path, 'r') as json_file:
                config = json.load(json_file)
                color_order = [color.lower() for color in config.get('colors', [])]
        except Exception as e:
            return

        # Suppression des éléments avec couleur de trait non gérée
        for element in list(self.svg.descendants()):
            if hasattr(element, 'style') and 'stroke' in element.style:
                stroke_color = element.style.get('stroke', '#000000').lower()
                if stroke_color.startswith('#'):
                    stroke_color = stroke_color[1:]

                if stroke_color not in color_order:
                    parent = element.getparent()
                    if parent is not None:
                        parent.remove(element)

    def kill_other_inkscape_running(self):
        """Ferme toutes les autres instances d'inkscape"""
        if platform.system() == 'Windows':
            result = subprocess.run(['wmic', 'process', 'where', "name='inkscape.exe'", 'get', 'CreationDate,ProcessId'], text=True, capture_output=True)
            lines = result.stdout.strip().split('\n')[1:]
            processes = []
            for line in lines:
                if line != "":
                    parts = line.split()
                    pid = parts[1]
                    creation_date_str = re.sub(r'\+\d+$', '', parts[0])
                    creation_date = datetime.strptime(creation_date_str, '%Y%m%d%H%M%S.%f')
                    processes.append((pid, creation_date))
            processes.sort(key=lambda x: x[1])
            if len(processes) > 1:
                for process in processes[1:]:
                    subprocess.run(['taskkill', '/PID', process[0]])
    
    def _optimize_path_order(self):
        """
        Optimise l'ordre de découpe laser selon la stratégie choisie dans la GUI.
        
        Stratégies disponibles :
        - Plus proche voisin : glouton rapide, choisit toujours le plus proche
        - Optimisation locale : nearest-neighbor + amélioration 2-opt par échanges
        - Zonage : regroupement géographique (k-means) puis NN par zone
        
        Dans tous les cas, l'ordre des couleurs du JSON est respecté.
        
        Returns:
            dict avec statistiques d'optimisation
        """
        
        # --- 1. Charger l'ordre des couleurs depuis le JSON ---
        json_path = os.path.join(os.path.dirname(__file__), 'OptimLaser.json')
        color_order = []
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)
                color_order = [c.lower().lstrip('#') for c in config.get('colors', [])]
        except Exception:
            pass
        
        # --- 2. Collecter tous les PathElement du SVG ---
        all_path_elems = [el for el in self.svg.xpath('//svg:path')
                          if isinstance(el, PathElement)]
        if not all_path_elems:
            return {'improvement': 0.0, 'initial_idle': 0.0,
                    'final_idle': 0.0, 'estimated_time_s': 0.0, 'num_paths': 0}
        
        # --- 3. Extraire métadonnées de chaque chemin ---
        path_infos = []
        for el in all_path_elems:
            start, end = self.get_path_endpoints(el)
            if start is None or end is None:
                continue
            
            color_raw = '#000000'
            if hasattr(el, 'style') and el.style:
                color_raw = el.style.get('stroke', '#000000')
            color_hex = color_raw.lower().lstrip('#')
            
            path_abs = el.path.to_absolute()
            is_closed = any(seg.letter == 'Z' for seg in path_abs if hasattr(seg, 'letter'))
            cut_length = self._approximate_path_length(path_abs)
            
            path_infos.append({
                'element': el,
                'id': el.get('id', ''),
                'start': start,
                'end': end,
                'color': color_hex,
                'is_closed': is_closed,
                'cut_length': cut_length,
            })
        
        if not path_infos:
            return {'improvement': 0.0, 'initial_idle': 0.0,
                    'final_idle': 0.0, 'estimated_time_s': 0.0, 'num_paths': 0}
        
        # --- 4. Distance à vide initiale ---
        initial_idle = self._total_idle_distance(path_infos)
        
        # --- 5. Grouper par couleur (ordre du JSON) ---
        by_color = {}
        for pi in path_infos:
            by_color.setdefault(pi['color'], []).append(pi)
        
        sorted_colors = []
        for c in color_order:
            if c in by_color:
                sorted_colors.append(c)
        for c in by_color:
            if c not in sorted_colors:
                sorted_colors.append(c)
        
        # --- 6. Appliquer la stratégie choisie ---
        strategy = getattr(self, 'optimization_strategy', _('Plus proche voisin'))
        
        if strategy == _('Optimisation locale'):
            final_order = self._order_two_opt(by_color, sorted_colors)
        elif strategy == _('Zonage'):
            final_order = self._order_clustering(by_color, sorted_colors)
        else:
            # "Plus proche voisin" ou valeur par défaut
            final_order = self._order_nearest_neighbor(by_color, sorted_colors)
        
        # --- 7. Distance à vide finale ---
        final_idle = self._total_idle_distance(final_order)
        improvement = ((initial_idle - final_idle) / initial_idle * 100) if initial_idle > 0 else 0.0
        
        # --- 8. Réordonner dans le DOM SVG + renommer chemin1..N ---
        self._reorder_and_rename_svg(final_order)
        
        # --- 9. Estimer la durée de découpe ---
        total_cut = sum(pi['cut_length'] for pi in final_order)
        laser_speed = getattr(self, 'laser_speed', 50.0)
        idle_speed = getattr(self, 'idle_speed', 2800.0)
        
        cut_time = total_cut / laser_speed if laser_speed > 0 else 0.0
        idle_time = final_idle / idle_speed if idle_speed > 0 else 0.0
        estimated_time = cut_time + idle_time
        
        return {
            'improvement': improvement,
            'initial_idle': initial_idle,
            'final_idle': final_idle,
            'estimated_time_s': estimated_time,
            'num_paths': len(final_order),
            'total_cut_length': total_cut,
            'cut_time_s': cut_time,
            'idle_time_s': idle_time,
            'strategy': strategy,
        }
    
    # ──────────────── Stratégie 1 : Plus proche voisin ────────────────
    
    def _order_nearest_neighbor(self, by_color, sorted_colors, start_point=(0.0, 0.0)):
        """
        Nearest-neighbor par groupe-couleur.
        Pour chaque groupe, choisit le chemin dont le start (ou end pour
        les chemins ouverts) est le plus proche du point courant.
        Si le end est plus proche, le chemin ouvert est inversé.
        
        Args:
            by_color: dict couleur → liste de path_infos
            sorted_colors: couleurs triées selon l'ordre du JSON
            start_point: point de départ initial
            
        Returns:
            liste ordonnée de path_infos
        """
        final_order = []
        current_point = start_point
        
        for color in sorted_colors:
            group = by_color[color]
            remaining = list(range(len(group)))
            
            while remaining:
                best_idx = None
                best_dist = float('inf')
                best_reverse = False
                
                for idx in remaining:
                    p = group[idx]
                    d_start = math.dist(current_point, p['start'])
                    d_end = math.dist(current_point, p['end'])
                    
                    if d_start <= d_end:
                        if d_start < best_dist:
                            best_dist = d_start
                            best_idx = idx
                            best_reverse = False
                    else:
                        if d_end < best_dist:
                            best_dist = d_end
                            best_idx = idx
                            best_reverse = not p['is_closed']
                
                if best_idx is None:
                    break
                
                p = group[best_idx]
                if best_reverse:
                    self._reverse_path_in_svg(p)
                
                final_order.append(p)
                current_point = p['end']
                remaining.remove(best_idx)
        
        return final_order
    
    # ──────────── Stratégie 2 : Optimisation locale (2-opt) ───────────
    
    def _order_two_opt(self, by_color, sorted_colors):
        """
        Nearest-neighbor suivi d'une amélioration 2-opt par groupe-couleur.
        
        Le 2-opt inverse des segments de l'ordre pour réduire la distance
        à vide totale. On itère tant qu'il y a amélioration, avec un
        plafond de max_iterations passes.
        
        Args:
            by_color: dict couleur → liste de path_infos
            sorted_colors: couleurs triées selon l'ordre du JSON
            
        Returns:
            liste ordonnée de path_infos
        """
        final_order = []
        current_point = (0.0, 0.0)
        max_iter = getattr(self, 'max_iterations', 50)
        
        for color in sorted_colors:
            group = by_color[color]
            if not group:
                continue
            
            # Phase 1 : solution initiale par nearest-neighbor
            nn_order = self._nn_for_group(group, current_point)
            
            # Phase 2 : amélioration 2-opt
            n = len(nn_order)
            if n >= 3:
                improved = True
                iteration = 0
                while improved and iteration < max_iter:
                    improved = False
                    iteration += 1
                    for i in range(n - 1):
                        for j in range(i + 2, n):
                            # Coût actuel des arêtes (i→i+1) et (j→j+1 ou fin)
                            end_i = nn_order[i]['end']
                            start_i1 = nn_order[i + 1]['start']
                            old_d1 = math.dist(end_i, start_i1)
                            
                            if j < n - 1:
                                end_j = nn_order[j]['end']
                                start_j1 = nn_order[j + 1]['start']
                                old_d2 = math.dist(end_j, start_j1)
                            else:
                                old_d2 = 0.0
                            
                            # Coût si on inverse le segment [i+1..j]
                            # Nouvelle arête : end_i → start de l'ancien j (maintenant i+1)
                            new_d1 = math.dist(end_i, nn_order[j]['start'])
                            
                            if j < n - 1:
                                # Nouvelle arête : end de l'ancien i+1 (maintenant j) → start_j1
                                new_d2 = math.dist(nn_order[i + 1]['end'], start_j1)
                            else:
                                new_d2 = 0.0
                            
                            # Gain = anciennes distances - nouvelles
                            # NB: les distances internes du segment inversé sont
                            # recalculées via les start/end (pas les mêmes liaisons)
                            if (new_d1 + new_d2) < (old_d1 + old_d2) - 0.01:
                                # Inverser le sous-segment [i+1..j]
                                nn_order[i + 1:j + 1] = nn_order[i + 1:j + 1][::-1]
                                improved = True
            
            # Appliquer les inversions de chemins ouverts si bénéfiques
            self._apply_reversals_for_group(nn_order, current_point)
            
            final_order.extend(nn_order)
            if nn_order:
                current_point = nn_order[-1]['end']
        
        return final_order
    
    # ──────────── Stratégie 3 : Zonage géographique (k-means) ─────────
    
    def _order_clustering(self, by_color, sorted_colors):
        """
        Zonage par bandes (lignes ou colonnes) de taille définie.
        
        Découpe l'espace en bandes horizontales (lignes) ou verticales (colonnes)
        de largeur zonage_size_mm (en unités SVG ≈ px à 96dpi → 1mm ≈ 3.7795px).
        Les bandes sont parcourues en serpentin (gauche→droite puis droite→gauche
        ou haut→bas puis bas→haut), ce qui minimise les déplacements à vide.
        À l'intérieur de chaque bande : nearest-neighbor.
        
        Args:
            by_color: dict couleur → liste de path_infos
            sorted_colors: couleurs triées selon l'ordre du JSON
            
        Returns:
            liste ordonnée de path_infos
        """
        direction = getattr(self, 'zonage_direction', 'colonnes')
        size_mm = getattr(self, 'zonage_size_mm', 10.0)
        # Conversion mm → unités SVG (px à 96 dpi : 1mm = 3.7795275591 px)
        strip_size = size_mm * 3.7795275591
        if strip_size <= 0:
            strip_size = 37.795  # fallback 10mm
        
        final_order = []
        current_point = (0.0, 0.0)
        
        for color in sorted_colors:
            group = by_color[color]
            if not group:
                continue
            
            # Calculer le centre de chaque chemin
            centers = []
            for p in group:
                cx = (p['start'][0] + p['end'][0]) / 2.0
                cy = (p['start'][1] + p['end'][1]) / 2.0
                centers.append((cx, cy))
            
            # Assigner chaque chemin à une bande
            if direction == 'colonnes':
                # Bandes verticales (selon X)
                strip_indices = [int(cx // strip_size) for cx, cy in centers]
            else:
                # Bandes horizontales (selon Y)
                strip_indices = [int(cy // strip_size) for cx, cy in centers]
            
            # Regrouper par bande
            strips = {}
            for idx, strip_id in enumerate(strip_indices):
                strips.setdefault(strip_id, []).append(group[idx])
            
            # Trier les bandes par indice croissant
            sorted_strip_ids = sorted(strips.keys())
            
            # Parcours en serpentin : alterner le sens à chaque bande
            sub_order = []
            cp = current_point
            for band_num, strip_id in enumerate(sorted_strip_ids):
                strip_paths = strips[strip_id]
                strip_order = self._nn_for_group(strip_paths, cp)
                if strip_order:
                    self._apply_reversals_for_group(strip_order, cp)
                    # Serpentin : inverser le sens une bande sur deux
                    if band_num % 2 == 1:
                        strip_order.reverse()
                        self._apply_reversals_for_group(strip_order, cp)
                    sub_order.extend(strip_order)
                    cp = strip_order[-1]['end']
            
            final_order.extend(sub_order)
            if sub_order:
                current_point = sub_order[-1]['end']
        
        return final_order
    
    # ──────────────────── Sous-méthodes communes ────────────────────
    
    def _nn_for_group(self, group, start_point):
        """
        Nearest-neighbor simple pour un groupe de chemins.
        Retourne une nouvelle liste ordonnée (ne modifie pas le SVG).
        """
        remaining = list(range(len(group)))
        order = []
        current = start_point
        
        while remaining:
            best_idx = None
            best_dist = float('inf')
            
            for idx in remaining:
                p = group[idx]
                d = min(math.dist(current, p['start']),
                        math.dist(current, p['end']))
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            
            if best_idx is None:
                break
            
            p = group[best_idx]
            order.append(p)
            # Choisir le point de sortie le plus logique
            if math.dist(current, p['start']) <= math.dist(current, p['end']):
                current = p['end']
            else:
                current = p['start']
            remaining.remove(best_idx)
        
        return order
    
    def _apply_reversals_for_group(self, ordered_group, start_point):
        """
        Passe finale sur un groupe ordonné : inverse les chemins ouverts
        quand cela réduit la distance à vide.
        Modifie les éléments SVG in-place.
        """
        for pos in range(len(ordered_group)):
            pi = ordered_group[pos]
            if pi['is_closed']:
                continue
            
            prev_end = start_point if pos == 0 else ordered_group[pos - 1]['end']
            next_start = ordered_group[pos + 1]['start'] if pos < len(ordered_group) - 1 else None
            
            cost_normal = math.dist(prev_end, pi['start'])
            cost_reversed = math.dist(prev_end, pi['end'])
            if next_start:
                cost_normal += math.dist(pi['end'], next_start)
                cost_reversed += math.dist(pi['start'], next_start)
            
            if cost_reversed < cost_normal - 0.01:
                self._reverse_path_in_svg(pi)
    
    def _reverse_path_in_svg(self, pi):
        """Inverse un chemin dans le SVG et met à jour start/end dans pi."""
        reversed_path = self._reverse_path_object(pi['element'].path.to_absolute())
        pi['element'].path = reversed_path
        pi['start'], pi['end'] = pi['end'], pi['start']
    
    # ──────────────────── Sous-méthodes d'optimisation ────────────────────
    
    def _approximate_path_length(self, path_abs):
        """Longueur approx. d'un chemin (somme des segments linéarisés)."""
        points = self._sample_points_on_path(list(path_abs), num_samples=10)
        if len(points) < 2:
            return 0.0
        length = 0.0
        for i in range(1, len(points)):
            length += math.dist(points[i - 1], points[i])
        return length
    
    @staticmethod
    def _total_idle_distance(path_list):
        """Somme des distances à vide entre chemins consécutifs."""
        total = 0.0
        for i in range(len(path_list) - 1):
            end = path_list[i]['end']
            start = path_list[i + 1]['start']
            total += math.dist(end, start)
        return total
    
    def _reorder_and_rename_svg(self, ordered_paths):
        """
        Réordonne les éléments <path> dans le DOM SVG selon l'ordre optimisé
        et les renomme chemin1, chemin2, ..., cheminN.
        """
        if not ordered_paths:
            return
        
        # Déterminer le parent commun (layer ou racine SVG)
        first_parent = ordered_paths[0]['element'].getparent()
        if first_parent is None:
            first_parent = self.document.getroot()
        
        # Retirer tous les éléments à réordonner
        for pi in ordered_paths:
            el = pi['element']
            if el.getparent() is not None:
                el.getparent().remove(el)
        
        # Les remettre dans l'ordre optimal avec nouveau nom
        for idx, pi in enumerate(ordered_paths, start=1):
            el = pi['element']
            el.set('id', f'chemin{idx}')
            first_parent.append(el)
    
    def _optimize_path(self):
        """
        Affiche un tableau debug : ID chemin | Couleur chemin | coordonnée de début | coordonnée de fin
        Chaque chemin 2 fois (début-fin et fin-début)
        """
        path_elements = [el for el in self.svg.descendants() if isinstance(el, inkex.PathElement)]
        if not path_elements:
            return

        def point_tuple(pt):
            return (round(pt[0], 4), round(pt[1], 4))

        table = []
        path_data = {}  # Stocker les infos des chemins pour la fusion
        
        #extrait les informations des chemins SVG
        for el in path_elements:
            d = el.get('d')
            if not d:
                continue
            
            # Ignorer les chemins de texte ou police
            style_str = str(el.style).lower() if hasattr(el, 'style') else ''
            if 'text' in style_str or 'font' in style_str:
                continue
            
            color = el.style.get('stroke', '#000000').lower() if hasattr(el, 'style') else '#000000'
            # Extraire les coordonnées du d (en ignorant les commandes)
            coords = [float(x) for x in re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', d)]
            if len(coords) < 4:
                continue
            start = (round(coords[0], 4), round(coords[1], 4))
            end = (round(coords[-2], 4), round(coords[-1], 4))
            
            elem_id = el.get('id')
            table.append({'id': elem_id, 'color': color, 'start': start, 'end': end, 'd': d})
            table.append({'id': elem_id, 'color': color, 'start': end, 'end': start, 'd': d})
            
            # Stocker les infos du chemin
            path_data[elem_id] = {
                'element': el,
                'color': color,
                'start': start,
                'end': end,
                'path': el.path,
            }

        # Calculer les POINTS CRITIQUES UNE SEULE FOIS
        critical_points = self._compute_critical_points(path_data)
        
        # Fusionner itérativement tant qu'il y a des groupes à merger
        iteration = 0
        max_iterations = 100  # Sécurité
        
        while iteration < max_iterations:
            iteration += 1
            groups_to_merge = self._find_mergeable_paths(path_data, critical_points)
            
            if not groups_to_merge:
                break  # Pas de groupe à merger
            # Fusionner les groupes
            self._merge_touching_paths(path_data, groups_to_merge)
            
            # Mettre à jour path_data après fusion (supprimer les chemins fusionnés)
            merged_ids = set()
            for group in groups_to_merge:
                for path_id in group[1:]:  # Tous sauf le premier
                    merged_ids.add(path_id)
            
            for path_id in merged_ids:
                if path_id in path_data:
                    del path_data[path_id]
    
    def _compute_critical_points(self, path_data):
        """
        Calcule les points critiques (où >2 chemins de même couleur se touchent).
        À appeler une seule fois au début.
        
        Args:
            path_data: Dictionnaire des chemins
            
        Returns:
            Set de points critiques: ((x,y), color)
        """
        if not path_data:
            return set()
        
        # Construire le mapping point -> chemins
        point_connections = {}  # (point, color) -> list of path_id
        
        for path_id, data in path_data.items():
            start_key = (round(data['start'][0], 2), round(data['start'][1], 2))
            end_key = (round(data['end'][0], 2), round(data['end'][1], 2))
            color = data['color']
            
            key_start = (start_key, color)
            key_end = (end_key, color)
            
            if key_start not in point_connections:
                point_connections[key_start] = []
            if key_end not in point_connections:
                point_connections[key_end] = []
            
            point_connections[key_start].append(path_id)
            point_connections[key_end].append(path_id)
        
        # Identifier les points critiques (> 2 connexions)
        critical_points = set()
        for point_key, path_ids in point_connections.items():
            if len(path_ids) > 2:
                critical_points.add(point_key)
        
        return critical_points
    
    def _find_mergeable_paths(self, path_data, critical_points):
        """
        Trouve les groupes de chemins qui peuvent être mergés.
        Utilise les points critiques calculés une seule fois.
        
        Returns:
            Liste de groupes (chaque groupe est une liste d'IDs)
        """
        if not path_data:
            return []
        
        # Construire le mapping point -> chemins à partir de path_data courant
        point_connections = {}  # (point, color) -> list of path_id
        
        for path_id, data in path_data.items():
            start_key = (round(data['start'][0], 2), round(data['start'][1], 2))
            end_key = (round(data['end'][0], 2), round(data['end'][1], 2))
            color = data['color']
            
            key_start = (start_key, color)
            key_end = (end_key, color)
            
            if key_start not in point_connections:
                point_connections[key_start] = []
            if key_end not in point_connections:
                point_connections[key_end] = []
            
            point_connections[key_start].append(path_id)
            point_connections[key_end].append(path_id)
        
        # Identifier les points valides (exactement 2 connexions et pas dans critical_points)
        valid_merge_points = {}  # point_key -> (path_id1, path_id2)
        
        for point_key, path_ids in point_connections.items():
            if len(path_ids) == 2 and point_key not in critical_points:
                path_id1, path_id2 = path_ids
                # Ignorer si le même chemin se touche à lui-même (chemin fermé)
                if path_id1 != path_id2:
                    valid_merge_points[point_key] = tuple(path_ids)
        
        if not valid_merge_points:
            return []
        
        # Construire les groupes de chemins à merger
        groups_to_merge = []
        processed_paths = set()
        
        for point_key, (path_id1, path_id2) in valid_merge_points.items():
            if path_id1 in processed_paths or path_id2 in processed_paths:
                continue
            if path_id1 not in path_data or path_id2 not in path_data:
                continue
            
            # Construire la chaîne complète
            # Note: valid_merge_points garantit que le point de connexion n'est PAS critique
            group = self._build_merge_chain(point_key, path_id1, path_id2, path_data, valid_merge_points, critical_points, processed_paths)
            if len(group) > 1:
                groups_to_merge.append(group)
        
        return groups_to_merge
    
    def _build_merge_chain(self, start_point, path_id1, path_id2, path_data, valid_merge_points, critical_points, processed_paths):
        """
        Construit une chaîne de chemins connectés en respectant l'orientation et sans traverser de points critiques
        """
        # Vérifier l'orientation correcte de la paire initiale
        # Au point de départ, on doit avoir: fin(path_id1) = début(path_id2)
        path1_end = path_data[path_id1]['end']
        path1_start = path_data[path_id1]['start']
        path2_start = path_data[path_id2]['start']
        path2_end = path_data[path_id2]['end']
        
        path1_start_key = (round(path1_start[0], 2), round(path1_start[1], 2))
        path1_end_key = (round(path1_end[0], 2), round(path1_end[1], 2))
        path2_start_key = (round(path2_start[0], 2), round(path2_start[1], 2))
        path2_end_key = (round(path2_end[0], 2), round(path2_end[1], 2))
        
        # Déterminer l'ordre correct
        start_point_key = start_point[0]  # start_point est ((x,y), color), on prend (x,y)
        
        # Vérifier les 4 orientations possibles
        orientation = None
        if path1_end_key == start_point_key and path2_start_key == start_point_key:
            # Déjà bon ordre: path1 -> path2
            orientation = "path1->path2"
        elif path1_start_key == start_point_key and path2_end_key == start_point_key:
            # Inverser les deux: path2 -> path1
            path_id1, path_id2 = path_id2, path_id1
            orientation = "path2->path1"
        elif path1_end_key == start_point_key and path2_end_key == start_point_key:
            # path1 -> path2 inversé
            # Besoin de reverser path2
            orientation = "path1->path2_reversed"
        elif path1_start_key == start_point_key and path2_start_key == start_point_key:
            # path1 inversé -> path2
            # Besoin de reverser path1
            orientation = "path1_reversed->path2"
        
        chain = [path_id1, path_id2]
        processed_paths.add(path_id1)
        processed_paths.add(path_id2)
        
        # Chercher les continuations (en avant ET en arrière)
        extended = True
        extension_iterations = 0
        max_extension_iterations = 1000  # Sécurité contre boucles infinies
        
        while extended and extension_iterations < max_extension_iterations:
            extension_iterations += 1
            extended = False
            
            # Chercher une continuation EN AVANT (après le dernier chemin)
            last_id = chain[-1]
            last_end = path_data[last_id]['end']
            last_end_key = (round(last_end[0], 2), round(last_end[1], 2))
            last_color = path_data[last_id]['color']
            
            lookup_key = (last_end_key, last_color)
            if lookup_key in valid_merge_points:
                path_a, path_b = valid_merge_points[lookup_key]
                next_id = path_a if path_b == last_id else path_b
                
                if next_id not in processed_paths and next_id in path_data:
                    # Vérifier que l'autre extrémité de next_id n'est pas un point critique
                    next_end = path_data[next_id]['end']
                    next_end_key = (round(next_end[0], 2), round(next_end[1], 2))
                    next_color = path_data[next_id]['color']
                    critical_key = (next_end_key, next_color)
                    
                    if critical_key not in critical_points:
                        chain.append(next_id)
                        processed_paths.add(next_id)
                        extended = True
            
            # Chercher une continuation EN ARRIÈRE (avant le premier chemin)
            first_id = chain[0]
            first_start = path_data[first_id]['start']
            first_start_key = (round(first_start[0], 2), round(first_start[1], 2))
            first_color = path_data[first_id]['color']
            
            lookup_key = (first_start_key, first_color)
            if lookup_key in valid_merge_points:
                path_a, path_b = valid_merge_points[lookup_key]
                prev_id = path_a if path_b == first_id else path_b
                
                if prev_id not in processed_paths and prev_id in path_data:
                    # Vérifier que la fin de prev_id correspond au début de first_id
                    prev_end = path_data[prev_id]['end']
                    prev_end_key = (round(prev_end[0], 2), round(prev_end[1], 2))
                    
                    if prev_end_key == first_start_key:
                        # Vérifier que l'autre extrémité de prev_id n'est pas un point critique
                        prev_start = path_data[prev_id]['start']
                        prev_start_key = (round(prev_start[0], 2), round(prev_start[1], 2))
                        prev_color = path_data[prev_id]['color']
                        critical_key = (prev_start_key, prev_color)
                        
                        if critical_key not in critical_points:
                            chain.insert(0, prev_id)
                            processed_paths.add(prev_id)
                            extended = True
        
        return chain
    
    def _merge_touching_paths(self, path_data, groups_to_merge):
        """
        Fusionne les groupes de chemins connectés préalablement identifiés
        
        Args:
            path_data: Dictionnaire contenant les infos de chaque chemin
            groups_to_merge: Liste des groupes de chemins à fusionner
        """
        if not groups_to_merge:
            return
        
        # Fusionner chaque groupe
        for group_idx, group in enumerate(groups_to_merge, 1):
            try:
                merged_id = self._merge_path_group(group, path_data)
            except Exception as e:
                continue
            
            # Ajouter le chemin fusionné à path_data si fusion réussie
            if merged_id:
                # Le nouveau chemin est first_path_id + '_merged'
                first_path_id = group[0]
                new_path_id = first_path_id + '_merged'
                
                # Récupérer l'élément fusionné du SVG
                merged_element = self.svg.getElementById(new_path_id)
                if merged_element is not None:
                    # Extraire les coordonnées du nouveau chemin
                    d = merged_element.get('d')
                    if d:
                        coords = [float(x) for x in re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', d)]
                        if len(coords) >= 4:
                            start = (round(coords[0], 4), round(coords[1], 4))
                            end = (round(coords[-2], 4), round(coords[-1], 4))
                            
                            # Ajouter à path_data
                            path_data[new_path_id] = {
                                'element': merged_element,
                                'color': path_data[first_path_id].get('color', '#000000'),
                                'start': start,
                                'end': end,
                                'path': merged_element.path,
                            }
                
                # Supprimer les anciens chemins de path_data
                for path_id in group:
                    if path_id in path_data:
                        del path_data[path_id]
    
    def _merge_path_group(self, group_ids, path_data):
        """
        Fusionne un groupe de chemins connectés en un seul chemin
        
        Args:
            group_ids: Liste des IDs des chemins à fusionner
            path_data: Dict des chemins
            
        Returns:
            L'ID du chemin fusionné, ou None si échec
        """
        if len(group_ids) < 2:
            return None
        
        # Récupérer les données des chemins
        group_data = {path_id: path_data[path_id] for path_id in group_ids}
        
        # Construire une chaîne de chemins connectés
        merged_path = self._build_merged_path(group_ids, group_data)
        
        if merged_path is None:
            return None
        
        # Créer un nouvel élément PathElement pour le chemin fusionné
        first_path_id = group_ids[0]
        first_element = group_data[first_path_id]['element']
        
        # Créer le nouvel élément
        merged_element = inkex.PathElement()
        merged_id = first_path_id + '_merged'
        merged_element.set('id', merged_id)
        merged_element.path = merged_path
        merged_element.style = first_element.style
        
        # Remplacer le premier élément par le fusionné
        parent = first_element.getparent()
        if parent is not None:
            parent.replace(first_element, merged_element)
        
        # Supprimer les autres éléments
        for path_id in group_ids[1:]:
            element = group_data[path_id]['element']
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
        
        return merged_id
    
    def _build_merged_path(self, group_ids, group_data):
        """
        Construit un chemin fusionné à partir des chemins connectés
        en s'assurant que chaque fin touche le début du suivant
        
        Args:
            group_ids: Liste des IDs
            group_data: Dict des données
            
        Returns:
            inkex.Path fusionné
        """
        if not group_ids:
            return None
        
        if len(group_ids) == 1:
            return group_data[group_ids[0]]['path']
        
        # Construire un graphe d'adjacence avec les bonnes connexions
        # Clé: (start ou end, point), Valeur: (path_id, orientation)
        point_map = {}  # point -> list of (path_id, is_end)
        
        for path_id in group_ids:
            start = group_data[path_id]['start']
            end = group_data[path_id]['end']
            
            start_key = (round(start[0], 2), round(start[1], 2))
            end_key = (round(end[0], 2), round(end[1], 2))
            
            if start_key not in point_map:
                point_map[start_key] = []
            if end_key not in point_map:
                point_map[end_key] = []
            
            point_map[start_key].append((path_id, False))  # False = c'est le début
            point_map[end_key].append((path_id, True))     # True = c'est la fin
        
        # Trouver un point de départ (de préférence un point avec une seule connexion)
        start_point = None
        for point, connections in point_map.items():
            if len(connections) == 1:
                start_point = point
                break
        
        # Si tous les points ont 2 connexions (boucle), prendre n'importe quel point
        if start_point is None and point_map:
            start_point = list(point_map.keys())[0]
        
        if start_point is None:
            return None
        
        # Construire la chaîne de chemins
        ordered_paths = []  # List of (path_id, should_reverse)
        current_point = start_point
        processed = set()
        
        while len(processed) < len(group_ids):
            # Trouver le chemin qui commence ou finit à current_point
            found = False
            
            if current_point in point_map:
                for path_id, is_end in point_map[current_point]:
                    if path_id in processed:
                        continue
                    
                    # Ce chemin touche current_point
                    if is_end:
                        # Le chemin finit à current_point, donc il faut le prendre en normal
                        # Le début du chemin suivant sera donc au début de ce chemin
                        should_reverse = True
                        next_point_key = (round(group_data[path_id]['start'][0], 2), 
                                        round(group_data[path_id]['start'][1], 2))
                    else:
                        # Le chemin commence à current_point, donc il faut le prendre en normal
                        # Le prochain point sera la fin du chemin
                        should_reverse = False
                        next_point_key = (round(group_data[path_id]['end'][0], 2), 
                                        round(group_data[path_id]['end'][1], 2))
                    
                    ordered_paths.append((path_id, should_reverse))
                    processed.add(path_id)
                    current_point = next_point_key
                    found = True
                    break
            
            if not found:
                # Pas de chemin trouvé, la chaîne est brisée (prendre un autre chemin non-traité)
                for path_id in group_ids:
                    if path_id not in processed:
                        # Prendre ce chemin
                        ordered_paths.append((path_id, False))
                        processed.add(path_id)
                        current_point = (round(group_data[path_id]['end'][0], 2), 
                                       round(group_data[path_id]['end'][1], 2))
                        break
        
        # Fusionner les chemins dans l'ordre trouvé
        merged = None
        
        for i, (path_id, should_reverse) in enumerate(ordered_paths):
            path_obj = group_data[path_id]['path']
            
            if should_reverse:
                # Inverser le chemin
                path_obj = self._reverse_path_object(path_obj)
            
            if i == 0:
                # Commencer avec le premier chemin
                merged = inkex.Path(path_obj)
            else:
                # Fusionner en supprimant la commande M du chemin suivant
                commands = list(path_obj)
                if commands and commands[0].letter == 'M':
                    commands = commands[1:]
                
                for cmd in commands:
                    merged.append(cmd)
        
        return merged
    
    def _reverse_path_object(self, path_obj):
        """
        Inverse un objet inkex.Path
        
        Args:
            path_obj: L'objet Path à inverser
            
        Returns:
            Un nouvel objet Path inversé
        """
        commands = list(path_obj)
        if not commands or len(commands) < 2:
            return path_obj
        
        reversed_commands = []
        
        # Le nouveau point de départ est l'ancien point de fin
        last_cmd = commands[-1]
        
        # Déterminer le point final (endpoint de la dernière commande)
        # inkex: Curve endpoint=x4,y4 / Quadratic endpoint=x3,y3 / Line,Arc,Move endpoint=x,y
        if last_cmd.letter == 'L':
            new_start = (last_cmd.x, last_cmd.y)
        elif last_cmd.letter == 'A':
            new_start = (last_cmd.x, last_cmd.y)
        elif last_cmd.letter == 'C':
            new_start = (last_cmd.x4, last_cmd.y4)
        elif last_cmd.letter == 'Q':
            new_start = (last_cmd.x3, last_cmd.y3)
        elif last_cmd.letter == 'Z':
            new_start = (commands[0].x, commands[0].y)
        else:
            new_start = (commands[0].x, commands[0].y)
        
        # Ajouter le Move initial
        reversed_commands.append(inkex.paths.Move(*new_start))
        
        # Inverser les commandes
        for i in range(len(commands) - 1, 0, -1):
            cmd = commands[i]
            prev_cmd = commands[i-1] if i > 0 else commands[0]
            
            # Point cible = endpoint de la commande précédente (= début de la commande courante)
            if prev_cmd.letter == 'M':
                target = (prev_cmd.x, prev_cmd.y)
            elif prev_cmd.letter == 'L':
                target = (prev_cmd.x, prev_cmd.y)
            elif prev_cmd.letter == 'A':
                target = (prev_cmd.x, prev_cmd.y)
            elif prev_cmd.letter == 'C':
                target = (prev_cmd.x4, prev_cmd.y4)
            elif prev_cmd.letter == 'Q':
                target = (prev_cmd.x3, prev_cmd.y3)
            else:
                continue
            
            # Créer la commande inversée
            if cmd.letter == 'L':
                reversed_commands.append(inkex.paths.Line(*target))
            elif cmd.letter == 'A':
                reversed_commands.append(inkex.paths.Arc(
                    cmd.rx, cmd.ry, cmd.x_axis_rotation,
                    cmd.large_arc, 1 - cmd.sweep,
                    *target
                ))
            elif cmd.letter == 'C':
                reversed_commands.append(inkex.paths.Curve(
                    cmd.x3, cmd.y3,
                    cmd.x2, cmd.y2,
                    *target
                ))
            elif cmd.letter == 'Q':
                reversed_commands.append(inkex.paths.Quadratic(
                    cmd.x2, cmd.y2,
                    *target
                ))
        
        return inkex.Path(reversed_commands)

    def _save_optimized_file(self):
         if self.SauvegarderSousDecoupe:
            current_file_name = self.document_path()
            base_name, extension = os.path.splitext(current_file_name)
            new_file_name = base_name + " - decoupe" + extension
            with open(new_file_name, 'wb') as output_file:
                self.save(output_file)
            self.document = inkex.load_svg(current_file_name)
            self.kill_other_inkscape_running()
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                subprocess.Popen(["inkscape", new_file_name])
    
    def _restore_original_file(self):
        """Restaure le fichier original à son état initial (avant optimisation).
        
        Appelé quand l'utilisateur clique sur Annuler dans la fenêtre bilan.
        Réécrit le contenu sauvegardé au début de _run_optimization.
        """
        if not getattr(self, '_original_file_content', None):
            return
        try:
            current_file_name = self.document_path()
            with open(current_file_name, 'wb') as f:
                f.write(self._original_file_content)
            # Recharger le document dans Inkscape
            self.document = inkex.load_svg(current_file_name)
        except Exception:
            pass
    
    def _show_cancel_confirmation(self):
        """Affiche un message d'annulation dans la fenêtre de progression."""
        if hasattr(self, 'gui_instance') and self.gui_instance:
            self.gui_instance.complete_progress(
                _("Traitement annulé.") + "\n" + _("Le fichier original a été restauré."),
                on_cancel=None
            )

    def find_layer(self, element):
        while element is not None:
            if isinstance(element, etree._Element):
                if element.tag == inkex.addNS('g', 'svg') and element.get(inkex.addNS('groupmode', 'inkscape')) == 'layer':
                    return element
            element = element.getparent()
        return None

    def custom_to_path_element(self, element):
        """
        Convertit un élément en chemin (path). 
        Pour les ellipses, découpe systématiquement en 4 arcs de 90°.
        Pour les autres formes, utilise la méthode to_path_element() standard d'inkex.
        
        Args:
            element: L'élément à convertir en chemin
        
        Returns:
            Un élément de type PathElement
        """
        # Si l'élément est une ellipse, la découper en 4 arcs
        if isinstance(element, inkex.Ellipse):
            # Récupérer les propriétés de l'ellipse
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            rx = float(element.get('rx', 0))
            ry = float(element.get('ry', 0))
            
            # Créer un nouveau chemin avec 4 arcs de 90°
            path = inkex.Path()
            
            # Points cardinaux de l'ellipse (Est, Nord, Ouest, Sud)
            east = (cx + rx, cy)
            north = (cx, cy - ry)
            west = (cx - rx, cy)
            south = (cx, cy + ry)
            
            # Créer les 4 arcs de 90°
            path.append(inkex.paths.Move(*east))  # Partir du point Est
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *north))  # Arc Est -> Nord
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *west))   # Arc Nord -> Ouest
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *south))  # Arc Ouest -> Sud
            path.append(inkex.paths.Arc(rx, ry, 0, 0, 0, *east))   # Arc Sud -> Est
            
            # Créer le nouvel élément de chemin
            path_element = inkex.PathElement()
            path_element.path = path
            
            # Copier le style et les autres attributs de l'ellipse originale
            path_element.style = element.style
            
            # Copier les transformations
            if 'transform' in element.attrib:
                path_element.set('transform', element.get('transform'))
                
            # Copier l'ID ou en créer un nouveau
            path_element.set('id', element.get('id', 'path-' + str(id(path_element))))
            
            return path_element
        else:
            # Pour tous les autres types d'éléments, utiliser la méthode standard
            return element.to_path_element()

    def ungroup_and_apply_transform_to_children(self):
        """Décompose les groupes et applique la transformation à leurs enfants"""
        Nouvelle_selection = []
        elements_to_process = [elem for elem in self.svg.descendants()
                            if not isinstance(elem, inkex.TextElement)]

        def recursive_ungroup(element):
            """Décompose les groupes et applique la transformation à leurs enfants"""
            children_to_process = []
            for child in element.getchildren():
                if isinstance(child, inkex.Group):
                    for grandchild in child.getchildren():
                        if hasattr(grandchild, 'to_path_element'):
                            grandchild = self.custom_to_path_element(grandchild)
                            grandchild.path = grandchild.path.transform(grandchild.transform)
                            grandchild.path = grandchild.path.transform(child.transform)
                            grandchild.attrib.pop('transform', None)
                            parent_style = inkex.Style(child.attrib.get('style', ''))
                            child_style = inkex.Style(grandchild.attrib.get('style', ''))
                            for key, value in parent_style.items():
                                if key not in child_style or child_style[key] is None:
                                    child_style[key] = value
                            grandchild.attrib['style'] = str(child_style)
                        element.append(grandchild)
                        children_to_process.append(grandchild)
                    element.remove(child)
                else:
                    if hasattr(child, 'to_path_element'):
                        child = self.custom_to_path_element(child)
                        parent_style = inkex.Style(element.attrib.get('style', ''))
                        child_style = inkex.Style(child.attrib.get('style', ''))
                        for key, value in parent_style.items():
                            if key not in child_style or child_style[key] is None:
                                child_style[key] = value
                        child.attrib['style'] = str(child_style)
                        children_to_process.append(child)
                        Nouvelle_selection.append(child)
            return children_to_process

        while elements_to_process:
            current_element = elements_to_process.pop()
            if isinstance(current_element, inkex.Group):
                elements_to_process.extend(recursive_ungroup(current_element))

        for element in self.svg.descendants():
            if isinstance(element, (inkex.Circle, inkex.Ellipse, inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon)):
                if hasattr(element, 'to_path_element'):
                    parent = element.getparent()
                    new_path = self.custom_to_path_element(element)
                    if 'transform' in element.attrib:
                        transform = inkex.Transform(element.get('transform'))
                        new_path.path = new_path.path.transform(transform)
                        new_path.attrib.pop('transform', None)
                    if parent is not None:
                        parent.replace(element, new_path)
                        Nouvelle_selection.append(new_path)

    def replace_with_subpaths(self):
        """Remplace les chemins complexes par des segments simples"""
        self.numeroChemin = 0

        for element in self.svg.descendants():
            # Ignorer explicitement les TextElements
            if isinstance(element, inkex.TextElement):
                continue
            
            if (isinstance(element, (inkex.PathElement, inkex.Circle, inkex.Ellipse,
                                inkex.Rectangle, inkex.Line, inkex.Polyline, inkex.Polygon))
                and not any('font' in key.lower() for key in element.style.keys())):
                parent = element.getparent()
                couche = self.find_layer(element)
                style = element.style
                fill_value = style.get('fill', None)
                if fill_value and fill_value.lower() != 'none':
                    style['fill'] = 'none'

                if isinstance(element, inkex.PathElement) and 'transform' in element.attrib:
                    path = element.path
                    transform = inkex.Transform(element.get('transform'))
                    path = path.transform(transform)
                    element.attrib.pop('transform', None)
                    element.path = path

                path = element.path.to_non_shorthand()

                if len(path) > 0:
                    nb_Z = sum(1 for seg in path if seg.letter == 'Z')
                    val_Z=1
                    segments = iter(path)
                    segmentPrev = next(segments)
                    Premier = segmentPrev
                    
                    for segment in segments:
                        if segment.letter != 'Z':
                            debut = segmentPrev.end_point(None, None)
                            fin = segment.end_point(None, None)
                            segment_path = inkex.Path([inkex.paths.Move(*debut)] + [segment])
                            segmentPrev = segment
                        # Ferme le chemin s'il ne l'est pas uniquement le dernier chemin d'un path multiple    
                        elif val_Z==nb_Z: # uniquement le dernier Z du path
                            if segmentPrev.letter=='C':
                                debut = (round(segmentPrev.x4, 6), round(segmentPrev.y4, 6))
                            elif segmentPrev.letter=='Q':
                                debut = (round(segmentPrev.x3, 6), round(segmentPrev.y3, 6))
                            else:
                                debut = (round(segmentPrev.x, 6), round(segmentPrev.y, 6))
                            fin = (round(Premier.x, 6), round(Premier.y, 6))
                            segment_path = inkex.Path([inkex.paths.Move(*debut)] + [inkex.paths.Line(*fin)])
                            segmentPrev = segment
                            
                        if debut != fin:
                            self.numeroChemin += 1
                            new_element = inkex.PathElement(
                                id=f"chemin{self.numeroChemin}",
                                d=str(segment_path),
                                style=str(style),
                                transform=str(element.transform)
                            )

                            path_commands = [cmd.letter for cmd in new_element.path]
                            if not all(cmd == 'M' for cmd in path_commands):
                                if couche is not None:
                                    couche.append(new_element)
                                else:
                                    self.document.getroot().append(new_element)

                    parent.remove(element)

    def get_path_endpoints(self, element):
        """Retourne les points de début et fin d'un chemin selon son type"""
        if not isinstance(element, inkex.PathElement):
            return None, None

        try:
            # Obtenir le chemin en coordonnées absolues
            path = element.path.to_absolute()
            path_list = list(path)
            
            if not path_list:
                return None, None

            # Point de début (toujours la commande M)
            start_cmd = path_list[0]
            start = (float(start_cmd.x), float(start_cmd.y))

            # Point de fin : regarder le dernier segment qui n'est pas Z
            end = None
            for cmd in reversed(path_list):
                if cmd.letter == 'Z':
                    end = start  # Fermé = revenir au départ
                    break
                elif cmd.letter == 'M':
                    end = (float(cmd.x), float(cmd.y))
                    break
                elif cmd.letter == 'L':
                    end = (float(cmd.x), float(cmd.y))
                    break
                elif cmd.letter == 'A':
                    end = (float(cmd.x), float(cmd.y))
                    break
                elif cmd.letter == 'C':
                    # inkex Curve: x4, y4 est le point final
                    try:
                        end = (float(cmd.x4), float(cmd.y4))
                    except AttributeError:
                        try:
                            end = (float(cmd.x3), float(cmd.y3))
                        except AttributeError:
                            end = (float(cmd.x), float(cmd.y))
                    break
                elif cmd.letter == 'Q':
                    # inkex Quadratic: x3, y3 est le point final
                    try:
                        end = (float(cmd.x3), float(cmd.y3))
                    except AttributeError:
                        end = (float(cmd.x), float(cmd.y))
                    break
                elif cmd.letter in ['S', 'T']:
                    # Ces commandes ont aussi un point final
                    try:
                        end = (float(cmd.x), float(cmd.y))
                    except AttributeError:
                        pass
                    break
            
            if end is None:
                return None, None

            return start, end
        except Exception as e:
            # En cas d'erreur, retourner None
            return None, None


    def adjust_overlapping_segments(self):
        """Identifie et ajuste les chemins qui se chevauchent (lignes, arcs et courbes de Bézier)"""
        path_elements = []
        skipped_count = 0
        for element in self.svg.descendants():
            if not isinstance(element, inkex.PathElement):
                continue
            # Convertir en chemin absolu pour gérer les commandes relatives (minuscules)
            abs_path = element.path.to_absolute()
            path = list(abs_path)
            if len(path) < 2 or path[0].letter != 'M':
                skipped_count += 1
                continue
            start_point = (float(path[0].x), float(path[0].y))
            
            # Déterminer le type principal et le endpoint (dernier segment)
            path_type = None
            end_point = None
            
            # Identifier le type dominant du chemin (utiliser .upper() pour gérer les deux cas)
            cmd_types = set(cmd.letter.upper() for cmd in path[1:] if cmd.letter.upper() != 'Z')
            if not cmd_types:
                skipped_count += 1
                continue
            
            # Le type est déterminé par les commandes de dessin présentes
            if cmd_types <= {'L'}:
                path_type = 'L'
            elif 'C' in cmd_types:
                path_type = 'C'
            elif 'Q' in cmd_types:
                path_type = 'Q'
            elif 'A' in cmd_types:
                path_type = 'A'
            else:
                skipped_count += 1
                continue
            
            # Trouver le endpoint (dernier point du dernier segment de dessin)
            last_draw_cmd = None
            for cmd in reversed(path):
                if cmd.letter in ['L', 'A', 'C', 'Q']:
                    last_draw_cmd = cmd
                    break
            
            if last_draw_cmd is None:
                skipped_count += 1
                continue
            
            if last_draw_cmd.letter == 'L':
                end_point = (float(last_draw_cmd.x), float(last_draw_cmd.y))
            elif last_draw_cmd.letter == 'A':
                end_point = (float(last_draw_cmd.x), float(last_draw_cmd.y))
            elif last_draw_cmd.letter == 'C':
                # inkex Curve: x4,y4 = endpoint
                end_point = (float(last_draw_cmd.x4), float(last_draw_cmd.y4))
            elif last_draw_cmd.letter == 'Q':
                # inkex Quadratic: x3,y3 = endpoint
                end_point = (float(last_draw_cmd.x3), float(last_draw_cmd.y3))
            
            # Vérification de la validité des points
            if (not isinstance(start_point, tuple) or not isinstance(end_point, tuple) or
                len(start_point) != 2 or len(end_point) != 2 or
                not all(isinstance(v, float) for v in start_point+end_point)):
                skipped_count += 1
                continue
            
            # Traiter ce chemin
            if path_type in ['L', 'A', 'C', 'Q']:
                length = math.dist(start_point, end_point)
                if length > 0:
                    vector = ((end_point[0] - start_point[0])/length, (end_point[1] - start_point[1])/length)
                else:
                    vector = (0, 0)
                
                is_horizontal = abs(vector[1]) < 0.01
                is_vertical = abs(vector[0]) < 0.01
                
                path_elements.append({
                    'element': element,
                    'id': element.get('id'),
                    'start': start_point,
                    'end': end_point,
                    'style': element.style,
                    'length': length,
                    'vector': vector,
                    'color': element.style.get('stroke', '#000000').lower(),
                    'path_type': path_type,
                    'is_horizontal': is_horizontal,
                    'is_vertical': is_vertical,
                    'orig_path': abs_path
                })
        
        paths_by_color = {}
        for path in path_elements:
            color = path['color']
            if color not in paths_by_color:
                paths_by_color[color] = []
            paths_by_color[color].append(path)
        
        to_remove = set()
        for color, paths in paths_by_color.items():
            # Séparer les chemins par type
            straight_paths = [p for p in paths if p['path_type'] == 'L']
            arc_paths = [p for p in paths if p['path_type'] == 'A']
            cubic_bezier_paths = [p for p in paths if p['path_type'] == 'C']
            quadratic_bezier_paths = [p for p in paths if p['path_type'] == 'Q']
            
            # Traiter les chemins droits 
            if straight_paths:
                self._find_overlapping_straight_segments(straight_paths, to_remove)
            
            # Traiter les chemins courbes
            curve_paths = arc_paths + cubic_bezier_paths + quadratic_bezier_paths
            if curve_paths:
                self._find_overlapping_curve_segments(curve_paths, to_remove)
        
        count_removed = 0
        for element in list(self.svg.descendants()):
            if isinstance(element, inkex.PathElement) and element.get('id') in to_remove:
                parent = element.getparent()
                if parent is not None:
                    parent.remove(element)
                    count_removed += 1
        
        return count_removed > 0
    
    def _find_overlapping_straight_segments(self, segments, to_remove):
        """Trouve les segments droits qui se chevauchent"""
        tolerance = self.tolerance
        
        # Organiser les segments par orientation (horizontaux, verticaux, diagonaux)
        horizontal_segments = [s for s in segments if s['is_horizontal']]
        vertical_segments = [s for s in segments if s['is_vertical']]
        diagonal_segments = [s for s in segments if not s['is_horizontal'] and not s['is_vertical']]
        
        # Traiter chaque groupe séparément pour éviter de comparer des segments d'orientation différente
        for segment_group in [horizontal_segments, vertical_segments, diagonal_segments]:
            # Construire un graphe d'adjacence des segments qui se chevauchent
            overlap_graph = {}
            
            # Remplir le graphe
            for i in range(len(segment_group)):
                path1 = segment_group[i]
                if path1['id'] not in overlap_graph:
                    overlap_graph[path1['id']] = {'path': path1, 'overlaps': set()}
                
                for j in range(i + 1, len(segment_group)):
                    path2 = segment_group[j]
                    
                    # Si les segments ont la même orientation (vecteurs colinéaires)
                    dot_product = abs(path1['vector'][0]*path2['vector'][0] + path1['vector'][1]*path2['vector'][1])
                    if dot_product > 0.99:  # Presque parallèles
                        # Calculer la distance entre les segments
                        dist1 = self.point_to_segment_distance(path1['start'], path2['start'], path2['end'])
                        dist2 = self.point_to_segment_distance(path1['end'], path2['start'], path2['end'])
                        dist3 = self.point_to_segment_distance(path2['start'], path1['start'], path1['end'])
                        dist4 = self.point_to_segment_distance(path2['end'], path1['start'], path1['end'])
                        
                        # Si les segments sont suffisamment proches
                        if dist1 <= tolerance or dist2 <= tolerance or dist3 <= tolerance or dist4 <= tolerance:
                            # Vérifier si les segments se chevauchent
                            # Projeter les points sur la ligne de référence (utiliser le premier segment)
                            ref_vector = path1['vector']
                            ref_point = path1['start']
                            
                            # Fonction pour projeter un point sur la ligne de référence
                            def project_point(point):
                                vec = (point[0] - ref_point[0], point[1] - ref_point[1])
                                projection = vec[0] * ref_vector[0] + vec[1] * ref_vector[1]
                                return projection
                            
                            # Projeter les points de début et de fin des deux segments
                            p1_start_proj = project_point(path1['start'])
                            p1_end_proj = project_point(path1['end'])
                            p2_start_proj = project_point(path2['start'])
                            p2_end_proj = project_point(path2['end'])
                            
                            # S'assurer que les projections sont ordonnées (début < fin)
                            if p1_start_proj > p1_end_proj:
                                p1_start_proj, p1_end_proj = p1_end_proj, p1_start_proj
                            if p2_start_proj > p2_end_proj:
                                p2_start_proj, p2_end_proj = p2_end_proj, p2_start_proj
                            
                            # Vérifier si les segments se chevauchent sur l'axe de projection
                            overlap_start = max(p1_start_proj, p2_start_proj)
                            overlap_end = min(p1_end_proj, p2_end_proj)
                            
                            if overlap_start <= overlap_end:  # Les segments se chevauchent
                                # Ajouter au graphe d'adjacence
                                if path2['id'] not in overlap_graph:
                                    overlap_graph[path2['id']] = {'path': path2, 'overlaps': set()}
                                overlap_graph[path1['id']]['overlaps'].add(path2['id'])
                                overlap_graph[path2['id']]['overlaps'].add(path1['id'])
            
            # Traiter les groupes de segments qui se chevauchent
            self._process_overlapping_groups(overlap_graph, to_remove)

    def _process_overlapping_groups(self, overlap_graph, to_remove):
        """Traite les groupes de chemins qui se chevauchent.
        Pour les droites (L): crée un segment couvrant l'étendue maximale.
        Pour les courbes (A, C, Q): garde le chemin le plus long et supprime les autres."""
        # Parcourir les groupes de chemins qui se chevauchent
        processed = set()
        for path_id in overlap_graph:
            if path_id in processed or len(overlap_graph[path_id]['overlaps']) == 0:
                continue
            
            # Identifier le groupe complet avec BFS
            group = []
            queue = [path_id]
            group_processed = set([path_id])
            
            while queue:
                current_id = queue.pop(0)
                group.append(current_id)
                
                for overlapping_id in overlap_graph[current_id]['overlaps']:
                    if overlapping_id not in group_processed:
                        queue.append(overlapping_id)
                        group_processed.add(overlapping_id)
            
            # Traiter ce groupe de chemins qui se chevauchent
            if len(group) > 1:
                # Collecter tous les données du groupe
                first_path = None
                path_type = None
                
                for overlap_id in group:
                    path_data = overlap_graph[overlap_id]['path']
                    if first_path is None:
                        first_path = path_data
                        path_type = path_data.get('path_type', 'L')
                
                if first_path:
                    if path_type == 'L':
                        # Pour les droites: créer un segment couvrant l'étendue maximale
                        all_points = []
                        for overlap_id in group:
                            pd = overlap_graph[overlap_id]['path']
                            all_points.append((pd['start'], pd['end']))
                        
                        ref_vector = first_path['vector']
                        ref_point = first_path['start']
                        
                        projections = []
                        for start, end in all_points:
                            vec_s = (start[0] - ref_point[0], start[1] - ref_point[1])
                            proj_s = vec_s[0] * ref_vector[0] + vec_s[1] * ref_vector[1]
                            projections.append((proj_s, start))
                            vec_e = (end[0] - ref_point[0], end[1] - ref_point[1])
                            proj_e = vec_e[0] * ref_vector[0] + vec_e[1] * ref_vector[1]
                            projections.append((proj_e, end))
                        
                        extreme_start = min(projections, key=lambda p: p[0])[1]
                        extreme_end = max(projections, key=lambda p: p[0])[1]
                        
                        new_path = inkex.Path([inkex.paths.Move(*extreme_start), inkex.paths.Line(*extreme_end)])
                        
                        new_element = inkex.PathElement(
                            id=f"chemin_fusionne_{path_id}",
                            d=str(new_path),
                            style=str(first_path['style'])
                        )
                        
                        parent = first_path['element'].getparent()
                        if parent is not None:
                            parent.append(new_element)
                        
                        # Supprimer tous les chemins du groupe
                        for overlap_id in group:
                            to_remove.add(overlap_id)
                    
                    else:
                        # Pour les courbes (A, C, Q): garder le plus long, supprimer les autres
                        best_id = group[0]
                        best_length = overlap_graph[group[0]]['path']['length']
                        
                        for overlap_id in group[1:]:
                            l = overlap_graph[overlap_id]['path']['length']
                            if l > best_length:
                                best_length = l
                                best_id = overlap_id
                        
                        # Supprimer tous sauf le meilleur
                        for overlap_id in group:
                            if overlap_id != best_id:
                                to_remove.add(overlap_id)
            
            # Marquer tous les chemins de ce groupe comme traités
            processed.update(group)

    def _sample_points_on_path(self, path_cmds, num_samples=20):
        """Échantillonne des points régulièrement espacés le long d'un chemin SVG.
        
        Args:
            path_cmds: Liste de commandes inkex.Path
            num_samples: Nombre de points à échantillonner
            
        Returns:
            Liste de tuples (x, y) échantillonnés le long du chemin
        """
        points = []
        if not path_cmds or len(path_cmds) < 2:
            return points
        
        # Point de départ
        current = (float(path_cmds[0].x), float(path_cmds[0].y))
        
        for cmd in path_cmds[1:]:
            letter = cmd.letter
            
            if letter == 'L':
                end = (float(cmd.x), float(cmd.y))
                for i in range(num_samples + 1):
                    t = i / num_samples
                    x = current[0] + t * (end[0] - current[0])
                    y = current[1] + t * (end[1] - current[1])
                    points.append((x, y))
                current = end
            
            elif letter == 'A':
                end = (float(cmd.x), float(cmd.y))
                # Approximation linéaire pour les arcs (suffisant pour la comparaison)
                for i in range(num_samples + 1):
                    t = i / num_samples
                    x = current[0] + t * (end[0] - current[0])
                    y = current[1] + t * (end[1] - current[1])
                    points.append((x, y))
                current = end
            
            elif letter == 'C':
                # inkex Curve: x2,y2=1er ctrl, x3,y3=2ème ctrl, x4,y4=endpoint
                cp1 = (float(cmd.x2), float(cmd.y2))
                cp2 = (float(cmd.x3), float(cmd.y3))
                end = (float(cmd.x4), float(cmd.y4))
                for i in range(num_samples + 1):
                    t = i / num_samples
                    mt = 1 - t
                    x = mt**3 * current[0] + 3*mt**2*t * cp1[0] + 3*mt*t**2 * cp2[0] + t**3 * end[0]
                    y = mt**3 * current[1] + 3*mt**2*t * cp1[1] + 3*mt*t**2 * cp2[1] + t**3 * end[1]
                    points.append((x, y))
                current = end
            
            elif letter == 'Q':
                # inkex Quadratic: x2,y2=ctrl, x3,y3=endpoint
                cp = (float(cmd.x2), float(cmd.y2))
                end = (float(cmd.x3), float(cmd.y3))
                for i in range(num_samples + 1):
                    t = i / num_samples
                    mt = 1 - t
                    x = mt**2 * current[0] + 2*mt*t * cp[0] + t**2 * end[0]
                    y = mt**2 * current[1] + 2*mt*t * cp[1] + t**2 * end[1]
                    points.append((x, y))
                current = end
            
            elif letter == 'Z':
                # Fermeture vers le point de départ
                start = (float(path_cmds[0].x), float(path_cmds[0].y))
                for i in range(num_samples + 1):
                    t = i / num_samples
                    x = current[0] + t * (start[0] - current[0])
                    y = current[1] + t * (start[1] - current[1])
                    points.append((x, y))
                current = start
        
        return points
    
    def _hausdorff_distance(self, points1, points2):
        """Calcule la distance de Hausdorff entre deux ensembles de points.
        
        C'est la distance maximale d'un point d'un ensemble au point le plus proche
        de l'autre ensemble. Mesure à quel point deux courbes sont similaires.
        
        Args:
            points1, points2: Listes de tuples (x, y)
            
        Returns:
            Distance de Hausdorff (float)
        """
        if not points1 or not points2:
            return float('inf')
        
        def directed_hausdorff(set_a, set_b):
            max_dist = 0.0
            for pa in set_a:
                min_dist = float('inf')
                for pb in set_b:
                    d = math.dist(pa, pb)
                    if d < min_dist:
                        min_dist = d
                        if min_dist < max_dist:
                            break  # Optimisation : pas besoin de chercher plus
                if min_dist > max_dist:
                    max_dist = min_dist
            return max_dist
        
        return max(directed_hausdorff(points1, points2), directed_hausdorff(points2, points1))

    def _find_overlapping_curve_segments(self, segments, to_remove):
        """Trouve les segments courbes qui se chevauchent, y compris :
        - Chaînes de courbes connectées formant la même courbe globale
        - Chevauchements partiels (une courbe couvre une portion d'une autre)
        - Courbes simples quasi-identiques (mêmes endpoints, même géométrie)
        
        L'ordre de traitement est important : les chaînes sont comparées EN PREMIER
        pour éviter que la suppression de segments individuels casse les chaînes."""
        tolerance = self.tolerance
        
        # Échantillonner les points pour chaque segment (plus de points pour meilleure précision)
        for seg in segments:
            path_cmds = list(seg['orig_path'])
            seg['sampled_points'] = self._sample_points_on_path(path_cmds, num_samples=30)
        
        # === Phase 1 : Construire des chaînes et détecter chevauchements de chaînes ===
        # (DOIT être fait AVANT la détection individuelle pour ne pas casser les chaînes)
        chains = self._build_curve_chains(segments, tolerance)
        if len(chains) >= 2:
            self._find_chain_overlaps(chains, to_remove, tolerance)
        
        # === Phase 2 : Détecter les chevauchements partiels ===
        remaining = [s for s in segments if s['id'] not in to_remove]
        if len(remaining) >= 2:
            chains = self._build_curve_chains(remaining, tolerance)
            if len(chains) >= 2:
                self._find_partial_curve_overlaps(chains, to_remove, tolerance)
        
        # === Phase 3 : Détection simple résiduelle (segments individuels avec mêmes endpoints) ===
        remaining = [s for s in segments if s['id'] not in to_remove]
        if len(remaining) < 2:
            return
        
        overlap_graph = {}
        
        for i in range(len(remaining)):
            path1 = remaining[i]
            if path1['id'] not in overlap_graph:
                overlap_graph[path1['id']] = {'path': path1, 'overlaps': set()}
            
            for j in range(i + 1, len(remaining)):
                path2 = remaining[j]
                
                # Pré-filtre : bounding box basée sur les points échantillonnés
                pts1 = path1.get('sampled_points', [])
                pts2 = path2.get('sampled_points', [])
                if pts1 and pts2:
                    xs1 = [p[0] for p in pts1]
                    ys1 = [p[1] for p in pts1]
                    xs2 = [p[0] for p in pts2]
                    ys2 = [p[1] for p in pts2]
                    if (max(xs1) + tolerance < min(xs2) or max(xs2) + tolerance < min(xs1) or
                        max(ys1) + tolerance < min(ys2) or max(ys2) + tolerance < min(ys1)):
                        continue
                
                # Vérifier que les extrémités sont proches (sens direct ou inversé)
                dist_ss = math.dist(path1['start'], path2['start'])
                dist_se = math.dist(path1['start'], path2['end'])
                dist_es = math.dist(path1['end'], path2['start'])
                dist_ee = math.dist(path1['end'], path2['end'])
                
                endpoints_close = (
                    (dist_ss <= tolerance and dist_ee <= tolerance) or
                    (dist_se <= tolerance and dist_es <= tolerance)
                )
                
                if not endpoints_close:
                    continue
                
                if not pts1 or not pts2:
                    continue
                
                hausdorff = self._hausdorff_distance(pts1, pts2)
                
                if hausdorff <= tolerance:
                    if path2['id'] not in overlap_graph:
                        overlap_graph[path2['id']] = {'path': path2, 'overlaps': set()}
                    overlap_graph[path1['id']]['overlaps'].add(path2['id'])
                    overlap_graph[path2['id']]['overlaps'].add(path1['id'])
        
        # Traiter les chevauchements simples résiduels
        self._process_overlapping_groups(overlap_graph, to_remove)
    
    def _approximate_arc_length(self, points):
        """Calcule la longueur approximative d'une courbe à partir de ses points échantillonnés."""
        if len(points) < 2:
            return 0.0
        length = 0.0
        for i in range(1, len(points)):
            length += math.dist(points[i-1], points[i])
        return length
    
    def _build_curve_chains(self, segments, tolerance):
        """Construit des chaînes de segments courbes connectés de même couleur.
        
        Returns:
            Liste de chaînes, chaque chaîne contient :
            - 'segment_ids': IDs des segments dans l'ordre de la chaîne
            - 'segments': segments dans l'ordre
            - 'start': point de départ global
            - 'end': point de fin global
            - 'sampled_points': points échantillonnés le long de toute la chaîne
            - 'color': couleur du trait
            - 'bbox': (min_x, min_y, max_x, max_y)
        """
        by_color = {}
        for seg in segments:
            color = seg['color']
            by_color.setdefault(color, []).append(seg)
        
        all_chains = []
        
        for color, color_segs in by_color.items():
            # Utiliser des copies superficielles pour ne pas muter les segments originaux
            # (important car cette méthode peut être appelée plusieurs fois)
            seg_dict = {seg['id']: dict(seg) for seg in color_segs}
            used = set()
            
            for start_seg in color_segs:
                if start_seg['id'] in used:
                    continue
                
                # Initialiser la chaîne ordonnée avec ce segment
                chain_ids = [start_seg['id']]
                used.add(start_seg['id'])
                
                # Extension vers l'avant (à partir du end du dernier segment)
                extended = True
                while extended:
                    extended = False
                    last_seg = seg_dict[chain_ids[-1]]
                    chain_end = last_seg['end']
                    
                    best_id = None
                    best_dist = tolerance + 1  # Au-delà de la tolérance
                    best_reversed = False
                    
                    for other in color_segs:
                        if other['id'] in used:
                            continue
                        d_start = math.dist(chain_end, other['start'])
                        d_end = math.dist(chain_end, other['end'])
                        
                        if d_start <= tolerance and d_start < best_dist:
                            best_id = other['id']
                            best_dist = d_start
                            best_reversed = False
                        elif d_end <= tolerance and d_end < best_dist:
                            best_id = other['id']
                            best_dist = d_end
                            best_reversed = True
                    
                    if best_id is not None:
                        if best_reversed:
                            seg_dict[best_id]['start'], seg_dict[best_id]['end'] = \
                                seg_dict[best_id]['end'], seg_dict[best_id]['start']
                            if seg_dict[best_id].get('sampled_points'):
                                seg_dict[best_id]['sampled_points'] = list(reversed(
                                    seg_dict[best_id]['sampled_points']))
                        chain_ids.append(best_id)
                        used.add(best_id)
                        extended = True
                
                # Extension vers l'arrière (à partir du start du premier segment)
                extended = True
                while extended:
                    extended = False
                    first_seg = seg_dict[chain_ids[0]]
                    chain_start = first_seg['start']
                    
                    best_id = None
                    best_dist = tolerance + 1
                    best_reversed = False
                    
                    for other in color_segs:
                        if other['id'] in used:
                            continue
                        d_end = math.dist(chain_start, other['end'])
                        d_start = math.dist(chain_start, other['start'])
                        
                        if d_end <= tolerance and d_end < best_dist:
                            best_id = other['id']
                            best_dist = d_end
                            best_reversed = False
                        elif d_start <= tolerance and d_start < best_dist:
                            best_id = other['id']
                            best_dist = d_start
                            best_reversed = True
                    
                    if best_id is not None:
                        if best_reversed:
                            seg_dict[best_id]['start'], seg_dict[best_id]['end'] = \
                                seg_dict[best_id]['end'], seg_dict[best_id]['start']
                            if seg_dict[best_id].get('sampled_points'):
                                seg_dict[best_id]['sampled_points'] = list(reversed(
                                    seg_dict[best_id]['sampled_points']))
                        chain_ids.insert(0, best_id)
                        used.add(best_id)
                        extended = True
                
                # Construire les données de la chaîne
                chain_segs = [seg_dict[sid] for sid in chain_ids]
                chain_start = chain_segs[0]['start']
                chain_end = chain_segs[-1]['end']
                
                # Concaténer les points échantillonnés (éviter la duplication du point de jonction)
                all_points = []
                for idx_s, s in enumerate(chain_segs):
                    pts = s.get('sampled_points', [])
                    if idx_s > 0 and all_points and pts:
                        # Éviter de dupliquer le point de jonction
                        all_points.extend(pts[1:])
                    else:
                        all_points.extend(pts)
                
                # Bounding box à partir des points échantillonnés
                if all_points:
                    xs = [p[0] for p in all_points]
                    ys = [p[1] for p in all_points]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                else:
                    bbox = (min(chain_start[0], chain_end[0]),
                            min(chain_start[1], chain_end[1]),
                            max(chain_start[0], chain_end[0]),
                            max(chain_start[1], chain_end[1]))
                
                all_chains.append({
                    'segment_ids': chain_ids,
                    'segments': chain_segs,
                    'start': chain_start,
                    'end': chain_end,
                    'sampled_points': all_points,
                    'color': color,
                    'bbox': bbox
                })
        
        return all_chains
    
    def _find_chain_overlaps(self, chains, to_remove, tolerance):
        """Détecte les chevauchements entre chaînes de courbes.
        
        Deux chaînes se chevauchent si :
        1. Leurs extrémités globales (start/end) sont proches
        2. Leur distance de Hausdorff est inférieure à une tolérance adaptée
           (proportionnelle à la longueur de la chaîne pour tolérer les différences
           dues à des paramétrages Bézier différents de la même courbe)
        
        Quand un chevauchement est détecté, on garde la chaîne avec le plus de 
        segments (plus fidèle à la courbe originale) et on supprime l'autre.
        """
        for i in range(len(chains)):
            chain1 = chains[i]
            # Sauter si tous les segments de cette chaîne sont déjà supprimés
            if all(sid in to_remove for sid in chain1['segment_ids']):
                continue
            
            for j in range(i + 1, len(chains)):
                chain2 = chains[j]
                if all(sid in to_remove for sid in chain2['segment_ids']):
                    continue
                
                # Les chaînes doivent être de même couleur
                if chain1['color'] != chain2['color']:
                    continue
                
                # Pré-filtre : bounding boxes
                b1, b2 = chain1['bbox'], chain2['bbox']
                if b1 and b2:
                    margin = tolerance * 5
                    if (b1[2] + margin < b2[0] or b2[2] + margin < b1[0] or
                        b1[3] + margin < b2[1] or b2[3] + margin < b1[1]):
                        continue
                
                # Vérifier que les extrémités globales des chaînes sont proches
                dist_ss = math.dist(chain1['start'], chain2['start'])
                dist_ee = math.dist(chain1['end'], chain2['end'])
                dist_se = math.dist(chain1['start'], chain2['end'])
                dist_es = math.dist(chain1['end'], chain2['start'])
                
                endpoints_close = (
                    (dist_ss <= tolerance and dist_ee <= tolerance) or
                    (dist_se <= tolerance and dist_es <= tolerance)
                )
                
                if not endpoints_close:
                    continue
                
                pts1 = chain1['sampled_points']
                pts2 = chain2['sampled_points']
                if not pts1 or not pts2:
                    continue
                
                hausdorff = self._hausdorff_distance(pts1, pts2)
                
                # Tolérance adaptée pour les chaînes : plus permissive, proportionnelle
                # à la longueur de la courbe (différents approximations Bézier d'une
                # même courbe peuvent avoir une distance de Hausdorff significative)
                arc_len = max(self._approximate_arc_length(pts1),
                              self._approximate_arc_length(pts2))
                chain_tolerance = max(tolerance * 5, arc_len * 0.015)
                
                if hausdorff <= chain_tolerance:
                    # Les deux chaînes représentent la même courbe
                    # Garder la chaîne avec le plus de segments (plus fidèle)
                    if len(chain1['segment_ids']) >= len(chain2['segment_ids']):
                        keep_chain, remove_chain = chain1, chain2
                    else:
                        keep_chain, remove_chain = chain2, chain1
                    
                    for sid in remove_chain['segment_ids']:
                        to_remove.add(sid)
    
    def _find_partial_curve_overlaps(self, chains, to_remove, tolerance):
        """Détecte les chevauchements partiels : quand TOUS les points d'une courbe/chaîne
        sont proches d'une autre courbe/chaîne plus longue.
        
        Utilise la distance de Hausdorff dirigée : si tous les points de A sont
        proches de B, alors A est un sous-ensemble géométrique de B.
        """
        for i in range(len(chains)):
            chain_a = chains[i]
            if all(sid in to_remove for sid in chain_a['segment_ids']):
                continue
            
            for j in range(len(chains)):
                if i == j:
                    continue
                chain_b = chains[j]
                if all(sid in to_remove for sid in chain_b['segment_ids']):
                    continue
                
                # Les chaînes doivent être de même couleur
                if chain_a['color'] != chain_b['color']:
                    continue
                
                pts_a = chain_a['sampled_points']
                pts_b = chain_b['sampled_points']
                if not pts_a or not pts_b:
                    continue
                
                # A doit être plus courte ou égale à B pour être un sous-ensemble
                len_a = self._approximate_arc_length(pts_a)
                len_b = self._approximate_arc_length(pts_b)
                if len_a > len_b * 1.1:  # A est significativement plus longue, pas un sous-ensemble
                    continue
                
                # Pré-filtre : au moins une extrémité de A doit être proche de B
                min_dist_start = min(math.dist(chain_a['start'], p) for p in pts_b)
                min_dist_end = min(math.dist(chain_a['end'], p) for p in pts_b)
                
                # Tolérance adaptée pour les chevauchements partiels :
                # - Proportionnelle à la longueur de la courbe courte
                # - Cohérente avec la tolérance de chaîne (différentes approximations
                #   Bézier de la même courbe sous-jacente peuvent avoir des déviations
                #   significatives, surtout pour les courbes complexes)
                partial_tolerance = max(tolerance * 5, len_a * 0.04)
                if min_dist_start > partial_tolerance and min_dist_end > partial_tolerance:
                    continue
                
                # Distance de Hausdorff dirigée : A vers B
                # = max distance d'un point de A au point le plus proche de B
                directed_h = self._directed_hausdorff(pts_a, pts_b)
                
                if directed_h <= partial_tolerance:
                    # Tous les points de A sont proches de B → A est contenu dans B
                    for sid in chain_a['segment_ids']:
                        to_remove.add(sid)
                    break  # Chaîne A supprimée, passer à la suivante
    
    def _directed_hausdorff(self, set_a, set_b):
        """Calcule la distance de Hausdorff dirigée de set_a vers set_b.
        
        C'est la distance maximale d'un point de A au point le plus proche de B.
        Si cette distance est faible, tous les points de A sont proches de B.
        """
        max_dist = 0.0
        for pa in set_a:
            min_dist = float('inf')
            for pb in set_b:
                d = math.dist(pa, pb)
                if d < min_dist:
                    min_dist = d
                    if min_dist < max_dist:
                        break  # Optimisation
            if min_dist > max_dist:
                max_dist = min_dist
        return max_dist

    def point_to_segment_distance(self, point, segment_start, segment_end):
        """Calcule la distance minimale d'un point à un segment"""
        try:
            # Clé de cache unique pour cette opération
            cache_key = (point, segment_start, segment_end)

            # Vérifier si le résultat est déjà dans le cache
            if cache_key in self._distance_cache:
                return self._distance_cache[cache_key]

            px, py = point
            ax, ay = segment_start
            bx, by = segment_end

            segment_vector = (bx - ax, by - ay)
            point_vector = (px - ax, py - ay)

            segment_length_sq = segment_vector[0]**2 + segment_vector[1]**2

            if segment_length_sq == 0:
                result = math.dist(point, segment_start)
                self._distance_cache[cache_key] = result
                return result

            t = max(0, min(1, (point_vector[0] * segment_vector[0] +
                             point_vector[1] * segment_vector[1]) / segment_length_sq))

            projection_x = ax + t * segment_vector[0]
            projection_y = ay + t * segment_vector[1]

            result = math.dist(point, (projection_x, projection_y))



            # Stocker le résultat dans le cache
            self._distance_cache[cache_key] = result

            return result
        except Exception as e:
            return float('inf')

    def _is_cancel_requested(self):
        """Vérifie si l'utilisateur a demandé l'annulation via le bouton Annuler."""
        if hasattr(self, 'gui_instance') and self.gui_instance:
            if getattr(self.gui_instance, '_cancel_requested', False):
                return True
        return False
    
    def _run_optimization(self):
        # % Sauvegarde du fichier actuel avant optimisation
        # Rafraîchir la fenêtre de progression
        self._update_progress_window(_("Initialisation..."))
        
        # % Garder une copie du contenu original pour pouvoir annuler
        try:
            current_file_name = self.document_path()
            with open(current_file_name, 'rb') as f:
                self._original_file_content = f.read()
        except Exception:
            self._original_file_content = None
        
        try:
            with open(current_file_name, 'wb') as output_file:
                self.save(output_file)
        except Exception as e:
            messagebox.showwarning(_('Attention !'), _('Vous devez enregistrer le fichier puis relancer l\'extension.'))
            return
        
        # % Sauvegarder les éléments gris
        self._update_progress_window(_("Sauvegarde des éléments gris..."))
        self.save_gray_elements()

        # % Appliquer la transformation d'un groupe à chacun de ses éléments enfants
        self._update_progress_window(_("Dégroupement et transformation des éléments..."))
        self.ungroup_and_apply_transform_to_children()
        if self._is_cancel_requested():
            self._restore_original_file()
            self._show_cancel_confirmation()
            return
       
        # % Supprimer tout ce qui a des lignes qui ne sont pas dans les couleurs gérées
        self._update_progress_window(_("Suppression des couleurs non gérées..."))
        self.remove_unmanaged_colors()
        if self._is_cancel_requested():
            self._restore_original_file()
            self._show_cancel_confirmation()
            return

        # % Découpage en chemins simples
        self._update_progress_window(_("Découpage en chemins simples..."))
        self.replace_with_subpaths()
        if self._is_cancel_requested():
            self._restore_original_file()
            self._show_cancel_confirmation()
            return
        
        # % Suppression de doublons
        self._update_progress_window(_("Suppression des doublons..."))
        self.adjust_overlapping_segments()
        if self._is_cancel_requested():
            self._restore_original_file()
            self._show_cancel_confirmation()
            return
        
        # % Optimisation des chemins
        self._update_progress_window(_("Optimisation des chemins..."))
        self._optimize_path()
        if self._is_cancel_requested():
            self._restore_original_file()
            self._show_cancel_confirmation()
            return
        
        # % Optimisation de l'ordre de découpe
        self._update_progress_window(_("Optimisation de l'ordre de découpe..."))
        
        stats = None
        if self.enable_global_optimization:
            stats = self._optimize_path_order()
            if stats and stats.get('estimated_time_s', 0) > 0:
                minutes = int(stats['estimated_time_s'] // 60)
                seconds = int(stats['estimated_time_s'] % 60)
                self._update_progress_window(
                    _("Optimisation terminée : {} chemins, "
                    "trajet à vide réduit de {:.1f}%, "
                    "durée estimée : {}m{:02d}s").format(
                        stats['num_paths'], stats['improvement'], minutes, seconds)
                )
        
        # % Remettre les éléments gris
        self._update_progress_window(_("Restauration des éléments gris..."))
        self.restore_gray_elements()
                
        # % Création du fichier de découpe
        # Rafraîchir la fenêtre de progression
        self._update_progress_window(_("Création du fichier de découpe..."))  
        
        self._save_optimized_file()
        
        # Compléter la barre de progression avec le résumé
        result_text = _("Traitement terminé.")
        if stats is not None:
            try:
                minutes = int(stats['estimated_time_s'] // 60)
                seconds = int(stats['estimated_time_s'] % 60)
                result_text = (
                    _("{} chemins optimisés").format(stats['num_paths']) + "\n"
                    + _("Stratégie : {}").format(stats.get('strategy', '?')) + "\n"
                    + _("Trajet à vide réduit de {:.1f}%").format(stats['improvement']) + "\n"
                    + _("Durée estimée de découpe : {}m{:02d}s").format(minutes, seconds)
                )
            except Exception:
                pass
        
        if hasattr(self, 'gui_instance') and self.gui_instance:
            self.gui_instance.complete_progress(
                result_text,
                on_cancel=self._restore_original_file
            )
    
if __name__ == '__main__':
    OptimLaser().run()
