"""
Interface graphique pour OptimLaser

Interface Tkinter pour la configuration et l'optimisation des découpes laser
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, List, Callable
import os
import locale
import json
import unicodedata
import gettext

# Configurer gettext pour l'internationalisation
_locale_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locale')
try:
    _translation = gettext.translation('OptimLaser', localedir=_locale_dir, fallback=True)
    _ = _translation.gettext
except Exception:
    def _(msg): return msg

# Importer la version
try:
    from optimlaser import __version__
except ImportError:
    __version__ = "2026.1"

# Configurer le locale français
try:
    locale.setlocale(locale.LC_NUMERIC, 'fr_FR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_NUMERIC, 'French_France.1252')
    except:
        pass  # Garder le locale par défaut


class OptimLaserGUI:
    """Interface graphique principale pour OptimLaser"""
    
    def __init__(self, 
                 master: tk.Tk,
                 on_apply: Optional[Callable] = None,
                 on_cancel: Optional[Callable] = None,
                 config_file: Optional[str] = None):
        """
        Initialise l'interface.
        
        Args:
            master: Fenêtre parent Tkinter
            on_apply: Callback appelé lors de l'application (reçoit les paramètres)
            on_cancel: Callback appelé lors de l'annulation
            config_file: Chemin vers le fichier OptimLaser.json
        """
        self.master = master
        self.on_apply = on_apply
        self.on_cancel = on_cancel
        self.config_file = config_file
        
        # Variables de configuration
        self.tolerance = tk.DoubleVar(value=0.15)
        self.enable_partial_overlap = tk.BooleanVar(value=True)

        self.enable_global_optimization = tk.BooleanVar(value=True)
        self.optimization_strategy = tk.StringVar(value="Zonage")
        self.max_iterations = tk.IntVar(value=50)
        self.zonage_direction = tk.StringVar(value="colonnes")
        self.zonage_size_mm = tk.DoubleVar(value=10.0)
        self.laser_speed = tk.DoubleVar(value=25.0)
        self.idle_speed = tk.DoubleVar(value=2800.0)
        self.remove_unmanaged_colors = tk.BooleanVar(value=True)
        self.save_as_cutting = tk.BooleanVar(value=True)
        self.speed_presets: Dict[str, float] = {}
        self.speed_labels: Dict[str, str] = {}
        self.label_to_name: Dict[str, str] = {}
        self.selected_speed_name = tk.StringVar(value="")
        
        # Liste des couleurs (ordre)
        self.colors_order: List[str] = []
        self.colors_order_initial: List[str] = []  # Pour détecter les modifications
        
        # Paramètres sauvegardés (avant destruction de la fenêtre)
        self.saved_parameters: Dict = {}
        
        # Charger la configuration si disponible
        if config_file and os.path.exists(config_file):
            self._load_config(config_file)
        
        # Si aucune couleur n'a été chargée, utiliser les couleurs par défaut
        if not self.colors_order:
            self.colors_order = ["#000000", "#0000ff", "#ff0000", "#007f00" ]

        # Si aucune vitesse n'a été chargée, utiliser des presets par défaut
        if not self.speed_presets:
            self.speed_presets = {
                "Lente": 10.0,
                "Normale": 25.0,
                "Rapide": 50.0,
                "Très rapide": 100.0,
            }
        if not self.speed_labels:
            self.speed_labels = {k: k for k in self.speed_presets}
        if not self.label_to_name:
            self.label_to_name = {self.speed_labels[k]: k for k in self.speed_presets}
            self.speed_labels = {k: k for k in self.speed_presets}
            self.label_to_name = {k: k for k in self.speed_presets}
        
        # Créer l'interface
        self._create_widgets()
    
    def _load_config(self, config_file: str):
        """Charge la configuration depuis le fichier .json"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Couleurs
                colors = data.get('colors', [])
                for color in colors:
                    color = color.strip()
                    if color:
                        if not color.startswith('#'):
                            color = '#' + color
                        if color not in self.colors_order:
                            self.colors_order.append(color)
                # Vitesses (dict avec value/label ou valeur directe)
                speeds = data.get('speeds', {})
                for name, value in speeds.items():
                    try:
                        if isinstance(value, dict):
                            val = float(value.get('value', 0))
                            label = value.get('label', name)
                        else:
                            val = float(value)
                            label = name
                        self.speed_presets[name] = val
                        self.speed_labels[name] = label
                        self.label_to_name[label] = name
                    except (TypeError, ValueError):
                        pass
                
                # Charger les dernières valeurs utilisées (à la fin pour ne pas être écrasées)
                self._last_used = data.get('last_used', {})
        except Exception:
            pass
        
        # Restaurer tous les paramètres sauvegardés
        if hasattr(self, '_last_used') and self._last_used:
            if 'tolerance' in self._last_used:
                self.tolerance.set(float(self._last_used['tolerance']))
            if 'enable_partial_overlap' in self._last_used:
                self.enable_partial_overlap.set(bool(self._last_used['enable_partial_overlap']))
            if 'enable_global_optimization' in self._last_used:
                self.enable_global_optimization.set(bool(self._last_used['enable_global_optimization']))
            if 'optimization_strategy' in self._last_used:
                self.optimization_strategy.set(str(self._last_used['optimization_strategy']))
            if 'max_iterations' in self._last_used:
                self.max_iterations.set(int(self._last_used['max_iterations']))
            if 'zonage_direction' in self._last_used:
                self.zonage_direction.set(str(self._last_used['zonage_direction']))
            if 'zonage_size_mm' in self._last_used:
                self.zonage_size_mm.set(float(self._last_used['zonage_size_mm']))
            if 'remove_unmanaged_colors' in self._last_used:
                self.remove_unmanaged_colors.set(bool(self._last_used['remove_unmanaged_colors']))
            if 'save_as_cutting' in self._last_used:
                self.save_as_cutting.set(bool(self._last_used['save_as_cutting']))

        # Si aucune couleur n'a été chargée, utiliser les couleurs par défaut
        if not self.colors_order:
            self.colors_order = ["#000000", "#0000ff", "#ff0000", "#007f00" ]

        # Si aucune vitesse n'a été chargée, utiliser des presets par défaut
        if not self.speed_presets:
            self.speed_presets = {
                "Lente": 10.0,
                "Normale": 25.0,
                "Rapide": 50.0,
                "Très rapide": 100.0,
            }

        # Initialiser les vitesses avec les dernières valeurs utilisées en priorité
        if hasattr(self, '_last_used') and self._last_used:
            if 'laser_speed' in self._last_used:
                self.laser_speed.set(float(self._last_used['laser_speed']))
            if 'idle_speed' in self._last_used:
                self.idle_speed.set(float(self._last_used['idle_speed']))
            if 'speed_preset' in self._last_used:
                self.selected_speed_name.set(self._last_used['speed_preset'])
        else:
            # Fallback si aucune valeur n'a été sauvegardée
            if "Defaut" in self.speed_presets:
                self.laser_speed.set(self.speed_presets["Defaut"])
                self.selected_speed_name.set("Defaut")
            elif self.speed_presets:
                first_name, first_value = next(iter(self.speed_presets.items()))
                self.laser_speed.set(first_value)
                self.selected_speed_name.set(first_name)
        
        # Définir la vitesse idle (déplacement) si elle n'a pas été chargée
        if not hasattr(self, '_last_used') or 'idle_speed' not in self._last_used:
            if "AVide" in self.speed_presets:
                self.idle_speed.set(self.speed_presets["AVide"])
    
    def _create_widgets(self):
        """Crée tous les widgets de l'interface"""
        
        # Configuration du style
        # Configuration du style moderne bleu et blanc
        style = ttk.Style()
        style.theme_use('clam')
        
        # Couleurs modernes
                
        bg_color = '#ffffff'  # Blanc
        bg_unselected = '#e6f2ff'
        bg_color_selected = '#0066cc'
        
        fg_color = '#0066cc'
        fgLight_color = '#004799'
        highlight_color = '#66b3ff'
        
        border_color        = "#2E7FDB"   # Bleu principal
        border_light_color  = "#E9F1FB"   # Très très léger bleu (presque blanc)
        border_dark_color   = "#C5D7EE"   # Bleu-gris doux, ombre très légère
        border_focus_color  = "#5A9FE0"   # Focus adouci, moins saturé
    
        # Stocker pour utilisation dans les autres méthodes
        self.fg_color = fg_color
        self.fgLight_color = fgLight_color
        self.highlight_color = highlight_color
        self.bg_color = bg_color
        self.bg_unselected = bg_unselected
        self.border_color = border_color
        self.border_light_color = border_light_color
        self.border_dark_color = border_dark_color
        self.border_focus_color = border_focus_color

        
        # Configurer les couleurs de base
        # Fonds non sélectionnés
        style.configure('TFrame', background=bg_unselected)
        style.configure('TLabel', background=bg_unselected, foreground=fg_color)
        # Correct style names for LabelFrame
        style.configure('TLabelframe', background=bg_unselected, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_unselected, foreground=fg_color, font=('Arial', 10, 'bold'))
        style.configure('TButton', background=bg_color, foreground=fg_color)
        style.map('TButton',
            background=[('active', highlight_color), ('pressed', fg_color)],
            foreground=[('active', fg_color), ('pressed', fgLight_color)])
        # Boutons d'options et cases à cocher
        style.configure('TCheckbutton', background=bg_unselected, foreground=fg_color)
        style.map('TCheckbutton',
            background=[('active', highlight_color), ('selected', highlight_color)],
            foreground=[('active', fgLight_color), ('selected', fgLight_color)])
        style.configure('TRadiobutton', background=bg_unselected, foreground=fg_color)
        style.map('TRadiobutton',
            background=[('active', highlight_color), ('selected', highlight_color)],
            foreground=[('active', fgLight_color), ('selected', fgLight_color)])
        style.configure('TCombobox', foreground=fg_color, fieldbackground='#ffffff', background=bg_unselected)
        # Assurer la cohérence du fond pour tous les états (notamment readonly) et lisibilité en sélection
        try:
            style.map('TCombobox',
                fieldbackground=[('readonly', '#ffffff'), ('!focus', '#ffffff'), ('focus', bg_color_selected), ('active', bg_color_selected)],
                background=[('readonly', bg_unselected), ('!focus', bg_unselected), ('focus', bg_color_selected), ('active', bg_color_selected)],
                foreground=[('readonly', fg_color), ('!focus', fg_color), ('focus', fgLight_color), ('active', fgLight_color)]
            )
        except Exception:
            pass
        style.configure('TSpinbox', foreground=fg_color, fieldbackground='#ffffff', background=bg_unselected, arrowcolor=fg_color)
        style.map('TSpinbox',
            background=[('active', highlight_color), ('pressed', fg_color)],
            arrowcolor=[('active', fgLight_color), ('pressed', fgLight_color)]
        )
        # Styles avec fond blanc pour les champs de saisie des fenêtres d'édition
        style.configure('White.TEntry', foreground=fg_color, fieldbackground='#ffffff')
        style.configure('White.TSpinbox', foreground=fg_color, fieldbackground='#ffffff', background=bg_unselected, arrowcolor=fg_color)
        style.map('White.TSpinbox',
            background=[('active', highlight_color), ('pressed', fg_color)],
            arrowcolor=[('active', fgLight_color), ('pressed', fgLight_color)]
        )
        # Scrollbar (ascenseur) cohérent avec le thème
        try:
            style.configure('TScrollbar', background=bg_unselected)
            # Certaines implémentations supportent ces options supplémentaires
            style.configure('TScrollbar', troughcolor=bg_unselected, arrowcolor=fg_color)
            style.map('TScrollbar',
                background=[('active', highlight_color), ('pressed', fg_color)],
                arrowcolor=[('active', fgLight_color), ('pressed', fgLight_color)]
            )
            style.configure('Vertical.TScrollbar', background=bg_unselected)
            style.configure('Horizontal.TScrollbar', background=bg_unselected)
        except Exception:
            pass
        style.configure('Treeview', background=bg_unselected, foreground=fg_color, fieldbackground=bg_unselected)
        style.configure('Treeview.Heading', background=bg_unselected, foreground=fg_color)
        style.map('Treeview', background=[('selected', highlight_color)], foreground=[('selected', fgLight_color)])
        # Notebook: onglets non sélectionnés et barre supérieure
        style.configure('TNotebook', background=bg_unselected)
        style.configure('TNotebook.Tab', background=bg_unselected, foreground=fg_color)
        # Onglet sélectionné
        style.map('TNotebook.Tab', background=[('selected', highlight_color)], foreground=[('selected', fgLight_color)])

        # Harmoniser les bordures grises avec la couleur de bord du thème (best effort selon support ttk)
        try:
            border_styles = [
                'TFrame', 'TLabelframe', 'TLabelframe.Label', 'TButton', 'TCheckbutton',
                'TRadiobutton', 'TCombobox', 'TSpinbox', 'Treeview', 'TNotebook', 'TNotebook.Tab',
                'TScrollbar'
            ]
            for style_name in border_styles:
                style.configure(style_name,
                    bordercolor=border_color,
                    lightcolor=border_light_color,
                    darkcolor=border_dark_color,
                    focuscolor=border_focus_color
                )
                
                style.map(style_name, bordercolor=[('focus', border_color), ('active', border_color)])
            # Réduire la bordure visible sur Notebook en la teignant
            style.configure('TNotebook', borderwidth=1)
        except Exception:
            pass

        # Combobox popdown Listbox styling (dropdown menu)
        try:
            # Couvrir les variantes de classes selon Tk/ttk
            for pattern in ("*TCombobox*Listbox*", "*Combobox*Listbox*"):
                self.master.option_add(f"{pattern}.background", bg_unselected)
                self.master.option_add(f"{pattern}.foreground", fg_color)
                self.master.option_add(f"{pattern}.selectBackground", bg_color_selected)
                self.master.option_add(f"{pattern}.selectForeground", fgLight_color)
                self.master.option_add(f"{pattern}.borderWidth", "1")
                self.master.option_add(f"{pattern}.relief", "solid")
                self.master.option_add(f"{pattern}.highlightColor", border_color)
                self.master.option_add(f"{pattern}.highlightBackground", border_color)
        except Exception:
            pass
        
        # Configurer la fenêtre principale
        self.master.configure(bg=bg_color)
        
        # Frame principal avec padding
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Titre
        title_label = ttk.Label(
            main_frame,
            text=_("OptimLaser - Optimisation pour découpe laser"),
            font=('Arial', 12, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Notebook pour les onglets
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Onglet 1: Paramètres
        self._create_duplicate_tab(notebook)
        
        # Onglet 2: Paramètres avancés
        self._create_advanced_tab(notebook)
        
        # Boutons en bas
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0))
        
        ttk.Button(
            button_frame,
            text=_("À propos"),
            command=self._show_about,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text=_("Annuler"),
            command=self._on_cancel_clicked,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text=_("Appliquer"),
            command=self._on_apply_clicked,
            width=15
        ).pack(side=tk.RIGHT, padx=5)
        
        # Configuration du redimensionnement
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def _create_duplicate_tab(self, parent):
        """Crée l'onglet paramètres avec détection de doublons et optimisation"""
        
        frame = ttk.Frame(parent, padding="10")
        parent.add(frame, text=_("Paramètres"))
        
        # === SECTION 1: Détection de doublons ===
        duplicate_frame = ttk.LabelFrame(frame, text=_("Détection de doublons"), padding="10")
        duplicate_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Tolérance
        ttk.Label(duplicate_frame, text=_("Tolérance de détection (mm):")).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        
        tolerance_frame = ttk.Frame(duplicate_frame)
        tolerance_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.tolerance_spinbox = ttk.Spinbox(
            tolerance_frame,
            from_=0.01,
            to=10.0,
            textvariable=self.tolerance,
            width=10,
            increment=0.01
        )
        self.tolerance_spinbox.pack(side=tk.LEFT)
        
        # Formater avec virgule
        self._format_spinbox_value(self.tolerance_spinbox, self.tolerance)
        
        ttk.Label(tolerance_frame, text="mm").pack(side=tk.LEFT, padx=(5, 0))
        
        # Informations
        info_text = (
            _("Détection avancée des doublons :") + "\n"
            "   • " + _("Lignes identiques ou partiellement superposées") + "\n"
            "   • " + _("Arcs et cercles similaires") + "\n"
            "   • " + _("Courbes de Bézier (quadratiques et cubiques)") + "\n\n"
            + _("La tolérance définit la distance maximale en mm pour considérer deux éléments comme identiques.") + "\n"
            + _("Si vous ne savez pas quoi mettre mettez la largeur du trait de coupe.")
        )
        
        info_label = ttk.Label(
            duplicate_frame,
            text=info_text,
            justify=tk.LEFT,
            foreground=self.fgLight_color
        )
        info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(15, 0))
        
        duplicate_frame.columnconfigure(1, weight=1)
        
        # === SECTION 2: Optimisation de la découpe ===
        optimization_frame = ttk.LabelFrame(frame, text=_("Optimisation de la découpe"), padding="10")
        optimization_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Activer l'optimisation
        ttk.Checkbutton(
            optimization_frame,
            text=_("Activer l'optimisation globale"),
            variable=self.enable_global_optimization,
            command=self._toggle_optimization
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Stratégie
        ttk.Label(optimization_frame, text=_("Stratégie d'optimisation :")).grid(
            row=1, column=0, sticky=tk.W, pady=5, padx=(20, 0)
        )
        
        self.strategy_combo = ttk.Combobox(
            optimization_frame,
            textvariable=self.optimization_strategy,
            values=[_("Plus proche voisin"), _("Optimisation locale"), _("Zonage")],
            state="readonly",
            width=20
        )
        self.strategy_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Itérations max (pour optimisation locale) - à côté de Stratégie
        ttk.Label(optimization_frame, text=_("Itérations max (pour optimisation locale):")).grid(
            row=1, column=2, sticky=tk.W, pady=5, padx=(20, 0)
        )
        
        ttk.Spinbox(
            optimization_frame,
            from_=10,
            to=500,
            textvariable=self.max_iterations,
            width=10
        ).grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # Options de zonage (visibles uniquement quand Zonage est sélectionné)
        self.zonage_frame = ttk.Frame(optimization_frame)
        self.zonage_frame.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(5, 0), padx=(20, 0))
        
        ttk.Label(self.zonage_frame, text=_("Direction :")).pack(side=tk.LEFT, padx=(0, 5))
        self.zonage_radio_col = ttk.Radiobutton(
            self.zonage_frame, text=_("Par colonnes"),
            variable=self.zonage_direction, value="colonnes"
        )
        self.zonage_radio_col.pack(side=tk.LEFT, padx=(0, 10))
        self.zonage_radio_row = ttk.Radiobutton(
            self.zonage_frame, text=_("Par lignes"),
            variable=self.zonage_direction, value="lignes"
        )
        self.zonage_radio_row.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(self.zonage_frame, text=_("Taille (mm) :")).pack(side=tk.LEFT, padx=(0, 5))
        self.zonage_size_spinbox = ttk.Spinbox(
            self.zonage_frame, from_=1, to=1000,
            textvariable=self.zonage_size_mm, width=6,
            increment=1
        )
        self.zonage_size_spinbox.pack(side=tk.LEFT)
        
        # Lier le changement de stratégie pour afficher/masquer les options de zonage
        self.optimization_strategy.trace_add('write', lambda *_: self._toggle_zonage_options())
        
        # Descriptions des stratégies
        strategy_text = (
            "• " + _("Plus proche voisin") + " : " + _("Rapide, solution de bonne qualité") + "\n"
            "• " + _("Optimisation locale") + " : " + _("Optimisation par échanges, meilleure qualité") + "\n"
            "• " + _("Zonage") + " : " + _("Regroupe par bandes (lignes ou colonnes) de taille définie")
        )
        
        strategy_info = ttk.Label(
            optimization_frame,
            text=strategy_text,
            justify=tk.LEFT,
            foreground=self.fgLight_color
        )
        strategy_info.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(15, 0))
        
        optimization_frame.columnconfigure(1, weight=1)
        optimization_frame.columnconfigure(3, weight=1)
        frame.columnconfigure(0, weight=1)
        
        # État initial
        self._toggle_optimization()
    
    def _format_spinbox_value(self, spinbox, variable):
        """Formate la valeur du Spinbox avec la notation régionale"""
        def on_change(*args):
            try:
                value = variable.get()
                formatted = locale.format_string("%.2f", value, grouping=False)
                if spinbox.get() != formatted:
                    spinbox.delete(0, tk.END)
                    spinbox.insert(0, formatted)
            except:
                pass
        
        variable.trace_add('write', on_change)
        on_change()  # Formater immédiatement
    
    def _parse_decimal(self, value_str):
        """Parse une valeur décimale avec virgule ou point"""
        try:
            # Remplacer virgule par point pour la conversion
            return float(value_str.replace(',', '.'))
        except:
            return 0.0
    
    def _on_colors_tab_leave(self, event, notebook):
        """Appelé quand on quitte l'onglet des paramètres avancés"""
        try:
            # Trouver l'index de l'onglet des paramètres avancés
            colors_tab_index = None
            for i in range(notebook.index("end")):
                if notebook.tab(i, "text") == _("Paramètres avancés"):
                    colors_tab_index = i
                    break
            
            # Vérifier qu'on a bien quitté l'onglet des paramètres avancés
            if colors_tab_index is not None and notebook.index(notebook.select()) != colors_tab_index:
                # Vérifier si les couleurs ont été modifiées
                if self.colors_order != self.colors_order_initial:
                    # Demander si on veut sauvegarder
                    if messagebox.askyesno(_("Enregistrer"), _("Enregistrer les modifications dans OptimLaser.json ?")):
                        self._save_colors_to_json()
                        # Mettre à jour le backup après enregistrement
                        self.colors_order_initial = self.colors_order.copy()
                    else:
                        # L'utilisateur refuse l'enregistrement, annuler les modifications
                        self.colors_order = self.colors_order_initial.copy()
        except Exception as e:
            # Ignorer les erreurs silencieusement
            pass
    
    def _create_advanced_tab(self, parent):
        """Crée l'onglet des paramètres avancés"""
        
        frame = ttk.Frame(parent, padding="10")
        tab_id = parent.add(frame, text=_("Paramètres avancés"))
        
        # Sauvegarder les couleurs initiales pour détecter les modifications
        self.colors_order_initial = self.colors_order.copy()
        
        # Bind pour détecter quand on quitte l'onglet
        parent.bind("<<NotebookTabChanged>>", lambda e: self._on_colors_tab_leave(e, parent))
        
        # === ZONE 1: PARAMÈTRES INDIVIDUELS (SANS FRAME) ===
        params_frame = ttk.Frame(frame)
        params_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), pady=(0, 10))
        
        # Checkbox pour supprimer les couleurs non gérées
        ttk.Checkbutton(
            params_frame,
            text=_("Supprimer les dessins de couleurs non gérées"),
            variable=self.remove_unmanaged_colors
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        
        # Infotext
        ttk.Label(
            params_frame,
            text=_("couleurs absentes de la liste ci-contre"),
            foreground=self.fgLight_color,
            font=("TkDefaultFont")
        ).grid(row=1, column=0, sticky=tk.W, padx=(20, 0), pady=(0, 10))
        
        # Checkbox pour sauvegarder sous découpe
        ttk.Checkbutton(
            params_frame,
            text=_("Sauvegarder sous Découpe"),
            variable=self.save_as_cutting
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 2))
        
        # Infotext
        ttk.Label(
            params_frame,
            text=_("Enregistrer le fichier optimisé avec le suffixe ' - découpe'"),
            foreground=self.fgLight_color,
            font=("TkDefaultFont")
        ).grid(row=3, column=0, sticky=tk.W, padx=(20, 0), pady=(0, 0))
        
        # === ZONE 2: VITESSES (AVEC FRAME) ===
        speeds_frame = ttk.LabelFrame(frame, text=_("Vitesses (mm/s)"), padding="10")
        speeds_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))

        ttk.Label(speeds_frame, text=_("Préréglage :")).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.speed_combo = ttk.Combobox(
            speeds_frame,
            textvariable=self.selected_speed_name,
            values=sorted([label for label, name in self.label_to_name.items() if name != "Deplacement"], key=lambda s: unicodedata.normalize('NFKD', s.lower())),
            state="readonly",
            width=25
        )
        self.speed_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        self.speed_combo.bind('<<ComboboxSelected>>', self._on_speed_preset_selected)
        
        # S'assurer que la valeur initiale est affichée dans le combobox
        if self.selected_speed_name.get():
            # Convertir le nom en label pour l'affichage
            preset_name = self.selected_speed_name.get()
            preset_label = self.speed_labels.get(preset_name, preset_name)
            self.speed_combo.set(preset_label)
        
        ttk.Button(
            speeds_frame,
            text="✎",
            command=self._edit_speed_presets,
            width=3
        ).grid(row=0, column=2, sticky=tk.W, pady=5, padx=(2, 0))
        
        ttk.Label(speeds_frame, text=_("Vitesse de découpe :")).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.laser_speed_spinbox = ttk.Spinbox(
            speeds_frame,
            from_=1.0,
            to=500.0,
            textvariable=self.laser_speed,
            width=10,
            increment=5.0
        )
        self.laser_speed_spinbox.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        self._format_spinbox_value(self.laser_speed_spinbox, self.laser_speed)
        ttk.Label(speeds_frame, text="mm/s").grid(row=1, column=2, sticky=tk.W, padx=(2, 0))
        
        ttk.Label(speeds_frame, text=_("Vitesse à vide :")).grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.idle_speed_spinbox = ttk.Spinbox(
            speeds_frame,
            from_=1.0,
            to=10000.0,
            textvariable=self.idle_speed,
            width=10,
            increment=10.0
        )
        self.idle_speed_spinbox.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        self._format_spinbox_value(self.idle_speed_spinbox, self.idle_speed)
        ttk.Label(speeds_frame, text="mm/s").grid(row=2, column=2, sticky=tk.W, padx=(2, 0))
        
        # === COLONNE DROITE: ORDRE DES COULEURS ===
        colors_container = ttk.LabelFrame(frame, text=_("Ordre des couleurs"), padding="10")
        colors_container.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Canvas pour le défilement
        list_frame = ttk.Frame(colors_container)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.colors_canvas = tk.Canvas(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=200,
            bg=self.bg_color,
            highlightthickness=1,
            highlightbackground=self.border_color
        )
        self.colors_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.colors_canvas.yview)
        
        # Frame intérieur pour les éléments
        self.colors_inner_frame = ttk.Frame(self.colors_canvas)
        self.colors_canvas_window = self.colors_canvas.create_window(
            (0, 0),
            window=self.colors_inner_frame,
            anchor='nw'
        )
        
        # Dictionnaire pour stocker Entry et Canvas de chaque couleur
        self.color_entries = {}  # {index: (entry_widget, canvas_widget)}
        self.focused_color_index = None  # Index de la couleur ayant le focus
        
        # Remplir la liste
        self._refresh_colors_list()
        
        # Bind pour mise à jour taille/scroll
        self.colors_inner_frame.bind(
            '<Configure>',
            lambda e: self.colors_canvas.configure(scrollregion=self.colors_canvas.bbox('all'))
        )
        self.colors_canvas.bind(
            '<Configure>',
            lambda e: self.colors_canvas.itemconfigure(self.colors_canvas_window, width=e.width)
        )
        
        # Boutons de gestion
        buttons_frame = ttk.Frame(colors_container)
        buttons_frame.grid(row=0, column=1, padx=(10, 0), sticky=tk.N)
        
        ttk.Button(
            buttons_frame,
            text=_("▲ Monter"),
            command=self._move_color_up,
            width=12
        ).pack(pady=2)
        
        ttk.Button(
            buttons_frame,
            text=_("▼ Descendre"),
            command=self._move_color_down,
            width=12
        ).pack(pady=2)
        
        ttk.Button(
            buttons_frame,
            text=_("+ Ajouter"),
            command=self._add_color,
            width=12
        ).pack(pady=2)
        
        ttk.Button(
            buttons_frame,
            text=_("− Supprimer"),
            command=self._remove_color,
            width=12
        ).pack(pady=2)
        
        colors_container.columnconfigure(0, weight=1)
        colors_container.rowconfigure(0, weight=1)
        
        frame.columnconfigure(0, weight=2, minsize=350)
        frame.columnconfigure(1, weight=1, minsize=150)
        frame.rowconfigure(0, weight=1)
    

        self.tolerance_spinbox.config(state='normal')  # Tolérance toujours active
    
    def _toggle_optimization(self):
        """Active/désactive les options d'optimisation"""
        state = 'readonly' if self.enable_global_optimization.get() else 'disabled'
        self.strategy_combo.config(state=state)
        self._toggle_zonage_options()
    
    def _toggle_zonage_options(self):
        """Affiche/masque les options de zonage selon la stratégie choisie."""
        show = (self.enable_global_optimization.get() and
                self.optimization_strategy.get() == _('Zonage'))
        if show:
            self.zonage_frame.grid()
        else:
            self.zonage_frame.grid_remove()

    def _on_speed_preset_selected(self, event=None):
        """Met à jour la vitesse en fonction du preset choisi"""
        label = self.selected_speed_name.get()
        name = self.label_to_name.get(label, label)
        if name in self.speed_presets:
            self.laser_speed.set(self.speed_presets[name])
            # Reformater l'affichage du spinbox
            self._format_spinbox_value(self.laser_speed_spinbox, self.laser_speed)
    
    def _edit_speed_presets(self):
        """Ouvre une fenêtre pour éditer les préréglages de vitesses"""
        edit_window = tk.Toplevel(self.master)
        edit_window.title(_("Éditer les préréglages de vitesses"))
        edit_window.geometry("750x450")
        edit_window.transient(self.master)
        edit_window.grab_set()
        edit_window.configure(bg=self.bg_unselected)
        
        # Définir l'icône de la fenêtre
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    edit_window.iconphoto(False, photo)
                    edit_window.image = photo  # Garder une référence
                except:
                    pass
        except:
            pass
        
        # Centrer sur la fenêtre parente
        edit_window.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        window_w = edit_window.winfo_width()
        window_h = edit_window.winfo_height()
        x = parent_x + (parent_w - window_w) // 2
        y = parent_y + (parent_h - window_h) // 2
        edit_window.geometry(f"+{x}+{y}")
        
        # Frame avec scrollbar
        canvas = tk.Canvas(edit_window, bg=self.bg_unselected, highlightthickness=0)
        scrollbar = ttk.Scrollbar(edit_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Headers
        ttk.Label(scrollable_frame, text=_("Nom interne"), font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(scrollable_frame, text=_("Label"), font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(scrollable_frame, text=_("Vitesse (mm/s)"), font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="", font=('Arial', 9, 'bold')).grid(row=0, column=3, padx=5, pady=5)
        
        # Configurer la largeur des colonnes pour rapprocher l'ascenseur
        scrollable_frame.columnconfigure(0, minsize=200)  # Nom interne
        scrollable_frame.columnconfigure(1, minsize=200)  # Label
        scrollable_frame.columnconfigure(2, minsize=80)   # Vitesse
        scrollable_frame.columnconfigure(3, minsize=35)   # Bouton supprimer
        
        # Variables pour stocker les éditions
        entries = {}
        
        def normalize_name(label):
            """Convertit un label en CamelCase majuscule sans espaces ni accents"""
            import unicodedata
            # Supprimer les accents
            nfkd = unicodedata.normalize('NFKD', label)
            ascii_str = ''.join([c for c in nfkd if not unicodedata.combining(c)])
            # Convertir en CamelCase
            words = ascii_str.split()
            return ''.join(word.capitalize() for word in words)
        
        def add_preset_row(name, label, value, row_num):
            """Ajoute une ligne pour un preset"""
            name_label = ttk.Label(scrollable_frame, text=name)
            name_label.grid(row=row_num, column=0, padx=5, pady=2, sticky=tk.W)
            
            label_var = tk.StringVar(value=label)
            label_entry = ttk.Entry(scrollable_frame, textvariable=label_var, width=25)
            label_entry.grid(row=row_num, column=1, padx=5, pady=2)
            label_entry.configure(style='White.TEntry')
            
            value_var = tk.DoubleVar(value=value)
            value_entry = ttk.Spinbox(scrollable_frame, textvariable=value_var, from_=1, to=3000, width=10)
            value_entry.grid(row=row_num, column=2, padx=5, pady=2)
            value_entry.configure(style='White.TSpinbox')
            
            # Bouton supprimer
            def delete_preset():
                if name != "AVide":  # Ne pas supprimer AVide
                    if messagebox.askyesno(_("Confirmation"), _("Supprimer le préréglage '{}' ?").format(label)):
                        if name in entries:
                            del entries[name]
                        rebuild_list()
            
            delete_btn = ttk.Button(scrollable_frame, text="×", command=delete_preset, width=3)
            delete_btn.grid(row=row_num, column=3, padx=5, pady=2)
            
            entries[name] = (label_var, value_var, [name_label, label_entry, value_entry, delete_btn])
        
        def rebuild_list():
            """Reconstruit la liste des préréglages"""
            # Supprimer tous les widgets sauf les headers
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            # Recréer les headers
            ttk.Label(scrollable_frame, text=_("Nom interne"), font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            ttk.Label(scrollable_frame, text=_("Label"), font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=5, pady=5)
            ttk.Label(scrollable_frame, text=_("Vitesse (mm/s)"), font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=5, pady=5)
            ttk.Label(scrollable_frame, text="", font=('Arial', 9, 'bold')).grid(row=0, column=3, padx=5, pady=5)
            
            # Recréer toutes les lignes triées par label (insensible aux accents)
            row = 1
            for name in sorted(entries.keys(), key=lambda n: unicodedata.normalize('NFKD', entries[n][0].get().lower())):
                label_var, value_var, widgets = entries[name]
                add_preset_row(name, label_var.get(), value_var.get(), row)
                row += 1
        
        # Charger les presets existants (triés par label, insensible aux accents)
        row = 1
        sorted_names = sorted(
            [n for n in self.speed_presets if n != "AVide"],
            key=lambda n: unicodedata.normalize('NFKD', self.speed_labels.get(n, n).lower())
        )
        for name in sorted_names:
            value = self.speed_presets[name]
            label = self.speed_labels.get(name, name)
            add_preset_row(name, label, value, row)
            row += 1
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="left", fill="y", pady=10, padx=(0, 10))
        
        # Boutons à droite, empilés verticalement
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(side="right", padx=10, pady=10, anchor=tk.N)
        
        ttk.Button(button_frame, text=_("Ajouter"), command=lambda: add_new_preset(), width=12).pack(pady=3)
        ttk.Button(button_frame, text=_("Annuler"), command=edit_window.destroy, width=12).pack(pady=3)
        ttk.Button(button_frame, text=_("Sauver"), command=lambda: save_presets(True), width=12).pack(pady=3)
        
        def add_new_preset():
            """Ajoute un nouveau préréglage"""
            add_window = tk.Toplevel(edit_window)
            add_window.title(_("Ajouter un préréglage"))
            add_window.geometry("300x150")
            add_window.transient(edit_window)
            add_window.grab_set()
            add_window.configure(bg=self.bg_unselected)

            # Icône de la fenêtre d'ajout
            try:
                icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
                if os.path.exists(icon_path):
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    img.thumbnail((24, 24), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    add_window.iconphoto(False, photo)
                    add_window.image = photo  # garder la référence
            except Exception:
                pass
            
            # Centrer
            add_window.update_idletasks()
            x = edit_window.winfo_x() + (edit_window.winfo_width() - 300) // 2
            y = edit_window.winfo_y() + (edit_window.winfo_height() - 150) // 2
            add_window.geometry(f"+{x}+{y}")
            
            ttk.Label(add_window, text=_("Label :")).grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
            new_label = tk.StringVar()
            label_entry = ttk.Entry(add_window, textvariable=new_label, width=20)
            label_entry.grid(row=0, column=1, padx=10, pady=10)
            label_entry.configure(style='White.TEntry')
            
            ttk.Label(add_window, text=_("Vitesse (mm/s) :")).grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
            new_speed = tk.DoubleVar(value=25.0)
            speed_entry = ttk.Spinbox(add_window, textvariable=new_speed, from_=1, to=3000, width=20)
            speed_entry.grid(row=1, column=1, padx=10, pady=10)
            speed_entry.configure(style='White.TSpinbox')
            
            def confirm_add():
                label = new_label.get().strip()
                if not label:
                    messagebox.showwarning(_("Attention"), _("Le label ne peut pas être vide"))
                    return
                name = normalize_name(label)
                if name in entries or name in self.speed_presets:
                    messagebox.showwarning(_("Attention"), _("Un préréglage avec le nom '{}' existe déjà").format(name))
                    return
                entries[name] = (tk.StringVar(value=label), tk.DoubleVar(value=new_speed.get()), [])
                add_window.destroy()
                rebuild_list()
            
            btn_frame = ttk.Frame(add_window)
            btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
            ttk.Button(btn_frame, text=_("Ajouter"), command=confirm_add, width=10).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text=_("Annuler"), command=add_window.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        def save_presets(close_window: bool = False):
            """Sauvegarde les presets dans le JSON et optionnellement ferme la fenêtre."""
            # Supprimer les anciens (sauf AVide)
            to_remove = [k for k in self.speed_presets.keys() if k != "AVide"]
            for k in to_remove:
                del self.speed_presets[k]
                if k in self.speed_labels:
                    del self.speed_labels[k]
            
            # Ajouter les nouveaux
            for name, (label_var, value_var, widgets) in entries.items():
                self.speed_presets[name] = value_var.get()
                self.speed_labels[name] = label_var.get()
            
            # Reconstruire label_to_name
            self.label_to_name = {self.speed_labels[k]: k for k in self.speed_presets}
            # Mettre à jour la combobox
            self.speed_combo['values'] = sorted([label for label, name in self.label_to_name.items() if name != "AVide"], key=lambda s: unicodedata.normalize('NFKD', s.lower()))
            
            # Sauvegarder dans le JSON
            self._save_colors_to_json()
            
            if close_window:
                edit_window.destroy()
    
    def _move_color_up(self):
        """Déplace la couleur ayant le focus vers le haut"""
        if self.focused_color_index is not None and self.focused_color_index > 0:
            idx = self.focused_color_index
            self.colors_order[idx], self.colors_order[idx - 1] = \
                self.colors_order[idx - 1], self.colors_order[idx]
            self.focused_color_index = idx - 1
            self._refresh_colors_list()
            # Remettre le focus sur la couleur déplacée
            if idx - 1 in self.color_entries:
                self.color_entries[idx - 1][0].focus_set()
    
    def _move_color_down(self):
        """Déplace la couleur ayant le focus vers le bas"""
        if self.focused_color_index is not None and self.focused_color_index < len(self.colors_order) - 1:
            idx = self.focused_color_index
            self.colors_order[idx], self.colors_order[idx + 1] = \
                self.colors_order[idx + 1], self.colors_order[idx]
            self.focused_color_index = idx + 1
            self._refresh_colors_list()
            # Remettre le focus sur la couleur déplacée
            if idx + 1 in self.color_entries:
                self.color_entries[idx + 1][0].focus_set()
    
    def _remove_color(self):
        """Supprime la dernière couleur de la liste"""
        if self.colors_order:
            self.colors_order.pop()
            self._refresh_colors_list()
    
    def _add_color(self):
        """Ajoute une nouvelle couleur"""
        from tkinter import colorchooser
        color = colorchooser.askcolor(title=_("Choisir une couleur"))
        if color and color[1]:
            hex_color = color[1].lower()
            if hex_color not in self.colors_order:
                self.colors_order.append(hex_color)
                self._refresh_colors_list()
    
    def _refresh_colors_list(self):
        """Actualise la liste des couleurs avec Entry dynamique et Rectangle"""
        # Supprimer tous les widgets existants
        for widget in self.color_entries.values():
            widget[0].destroy()  # Entry
            widget[1].destroy()  # Canvas
        self.color_entries.clear()
        
        # Créer un widget pour chaque couleur
        for idx, color in enumerate(self.colors_order):
            # Frame pour chaque ligne
            item_frame = ttk.Frame(self.colors_inner_frame, relief='flat')
            item_frame.grid(row=idx, column=0, sticky=(tk.W, tk.E), padx=2, pady=2)
            
            # Entry pour éditer le code couleur
            color_entry = tk.Entry(
                item_frame,
                width=12,
                font=('Arial', 10),
                fg=self.fg_color,
                bg='#ffffff',
                highlightthickness=1,
                highlightcolor=self.border_light_color,
                highlightbackground=self.border_color
            )
            color_entry.pack(side=tk.LEFT, padx=5)
            color_entry.insert(0, color)
            
            # Gérer le focus pour rendre la sélection visible
            def make_focus_handler(index, entry):
                def on_focus_in(event):
                    self.focused_color_index = index
                    entry.config(background=self.highlight_color)
                def on_focus_out(event):
                    entry.config(background='#ffffff')
                return on_focus_in, on_focus_out
            
            focus_in, focus_out = make_focus_handler(idx, color_entry)
            color_entry.bind('<FocusIn>', focus_in)
            color_entry.bind('<FocusOut>', focus_out)
            
            # Canvas pour afficher la couleur (50x10 = proportion 5:1)
            color_canvas = tk.Canvas(
                item_frame,
                width=50,
                height=10,
                bg=color,
                highlightthickness=0
            )
            color_canvas.pack(side=tk.LEFT, padx=(5, 10))

            def open_color_picker(index, entry, canvas):
                from tkinter import colorchooser
                current = entry.get().strip() or color
                chosen = colorchooser.askcolor(color=current, title=_("Choisir une couleur"))
                if chosen and chosen[1]:
                    hex_color = chosen[1].lower()
                    self.colors_order[index] = hex_color
                    canvas.config(bg=hex_color)
                    entry.delete(0, tk.END)
                    entry.insert(0, hex_color)
            
            # Bind pour mise à jour dynamique
            def make_color_updater(index, entry, canvas):
                def on_color_change(event):
                    try:
                        new_color = entry.get().strip()
                        if new_color.startswith('#') and len(new_color) == 7:
                            # Valider la couleur hex
                            int(new_color[1:], 16)
                            self.colors_order[index] = new_color
                            canvas.config(bg=new_color)
                        elif len(new_color) == 6:
                            # Ajouter # si manquant
                            int(new_color, 16)
                            self.colors_order[index] = '#' + new_color
                            canvas.config(bg='#' + new_color)
                            entry.delete(0, tk.END)
                            entry.insert(0, '#' + new_color)
                    except ValueError:
                        # Couleur invalide, ignorer
                        pass
                return on_color_change
            
            color_entry.bind('<KeyRelease>', make_color_updater(idx, color_entry, color_canvas))

            # Clic sur le rectangle pour choisir une couleur via color picker
            color_canvas.bind(
                "<Button-1>",
                lambda e, i=idx, entry=color_entry, canvas=color_canvas: open_color_picker(i, entry, canvas)
            )
            
            self.color_entries[idx] = (color_entry, color_canvas)
        
        # Mettre à jour la région de défilement
        self.colors_inner_frame.update_idletasks()
        self.colors_canvas.configure(scrollregion=self.colors_canvas.bbox('all'))
    
    def _save_colors_to_json(self, show_message: bool = True):
        """Sauvegarde les couleurs et vitesses dans OptimLaser.json"""
        if not self.config_file:
            return
        
        try:
            # Charger l'existant pour ne pas perdre d'autres champs
            data = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}
            # Mettre à jour les couleurs (sans # pour rester compact)
            data['colors'] = [c.lstrip('#') for c in self.colors_order]
            # Mettre à jour les vitesses nommées avec label
            speeds_obj = {}
            for name, value in self.speed_presets.items():
                label = self.speed_labels.get(name, name)
                speeds_obj[name] = {
                    'value': float(value),
                    'label': label
                }
            data['speeds'] = speeds_obj
            
            # Sauvegarder tous les paramètres utilisés
            data['last_used'] = {
                'tolerance': self._parse_decimal(self.tolerance_spinbox.get()),
                'enable_partial_overlap': self.enable_partial_overlap.get(),
                'enable_global_optimization': self.enable_global_optimization.get(),
                'optimization_strategy': self.optimization_strategy.get(),
                'max_iterations': self.max_iterations.get(),
                'zonage_direction': self.zonage_direction.get(),
                'zonage_size_mm': self.zonage_size_mm.get(),
                'laser_speed': self._parse_decimal(self.laser_speed_spinbox.get()),
                'idle_speed': self._parse_decimal(self.idle_speed_spinbox.get()),
                'speed_preset': self.selected_speed_name.get(),
                'remove_unmanaged_colors': self.remove_unmanaged_colors.get(),
                'save_as_cutting': self.save_as_cutting.get()
            }
            
            # Écrire le fichier
            # Convertir en JSON compact puis insérer un saut de ligne avant chaque clé de commentaire
            json_str = json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
            json_str = json_str.replace('"_comment_', '\n"_comment_')

            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            if show_message:
                messagebox.showinfo(_("Succès"), _("Configuration enregistrée dans OptimLaser.json"))
        except Exception as e:
            messagebox.showerror(_("Erreur"), _("Erreur lors de l'enregistrement : {}").format(str(e)))
    
    def _on_apply_clicked(self):
        """Gère le clic sur Appliquer"""
        # Sauvegarder les paramètres AVANT de détruire la fenêtre
        self.saved_parameters = self.get_parameters()
        
        # Mettre à jour le JSON avec les dernières valeurs utilisées
        self._save_colors_to_json(show_message=False)
        
        # Sauvegarder les couleurs pour la fenêtre de progression
        saved_colors = {
            'bg_unselected': self.bg_unselected,
            'fg_color': self.fg_color,
            'fgLight_color': self.fgLight_color
        }
        
        # Fermer la fenêtre principale
        self.master.quit()
        self.master.destroy()
        
        # Afficher la fenêtre de progression (APRÈS la destruction)
        self._show_progress_window(saved_colors)
        
        if self.on_apply:
            self.on_apply(self.saved_parameters)
    
    def _show_progress_window(self, colors):
        """Affiche une fenêtre de progression pendant l'optimisation"""
        # Créer une NOUVELLE fenêtre Tk (pas Toplevel car le parent est détruit)
        self.progress_window = tk.Tk()
        self.progress_window.title(_("Optimisation en cours..."))
        self.progress_window.geometry("550x400")
        self.progress_window.resizable(False, False)
        self.progress_window.configure(bg=colors['bg_unselected'])
        
        # Centrer la fenêtre
        self.progress_window.update_idletasks()
        screen_width = self.progress_window.winfo_screenwidth()
        screen_height = self.progress_window.winfo_screenheight()
        x = (screen_width - 550) // 2
        y = (screen_height - 400) // 2
        self.progress_window.geometry(f"550x400+{x}+{y}")
        
        # Icône
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
            if os.path.exists(icon_path):
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.progress_window.iconphoto(False, photo)
                self.progress_window.image = photo
        except:
            pass
        
        # Frame principal
        main_frame = ttk.Frame(self.progress_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label de statut
        self.progress_label = ttk.Label(
            main_frame,
            text=_("Optimisation en cours..."),
            font=('Arial', 16, 'bold'),
            foreground=colors['fg_color']
        )
        self.progress_label.pack(pady=(0, 10))
        
        # Texte informatif (adapté selon le mode de sauvegarde)
        save_as_cutting = self.saved_parameters.get('SauvegarderSousDecoupe', True)
        if save_as_cutting:
            info_text = (_("Le fichier de découpe va s'ouvrir.") + "\n"
                         + _("Le fichier original n'aura pas été modifié."))
        else:
            info_text = (_("⚠ Toutes les modifications sont faites dans le fichier original.") + "\n"
                         + _("Si vous souhaitez le garder intact pour faciliter les") + "\n"
                         + _("retouches ultérieures, cochez la case :") + "\n"
                         + _("\"Sauvegarder sous découpe\""))
        
        info_label = ttk.Label(
            main_frame,
            text=info_text,
            font=('Arial', 12, 'bold'),
            foreground=colors['fgLight_color'],
            justify=tk.CENTER
        )
        info_label.pack(pady=(0, 15))
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=510,
            maximum=100
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar['value'] = 0
        
        # Compteur pour le remplissage progressif
        self.progress_steps = 0
        self.progress_increment = 5  # Incrément par étape
        
        # Label de tâche en cours
        self.task_label = ttk.Label(
            main_frame,
            text=_("Démarrage..."),
            font=('Arial', 9),
            foreground=colors['fg_color'],
            justify=tk.CENTER
        )
        self.task_label.pack(pady=(5, 0))
        
        # Frame pour les boutons (Annuler dès le départ, OK ajouté plus tard)
        self.progress_btn_frame = ttk.Frame(main_frame)
        self.progress_btn_frame.pack(pady=(10, 0))
        
        self._cancel_requested = False
        self.progress_cancel_button = ttk.Button(
            self.progress_btn_frame,
            text=_("Annuler"),
            command=self._cancel_during_progress,
            width=12
        )
        self.progress_cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Empêcher la fermeture par la croix (redirige vers Annuler)
        self.progress_window.protocol("WM_DELETE_WINDOW", self._cancel_during_progress)
        self.progress_window.bind('<Escape>', lambda e: self._cancel_during_progress())
        
        # Forcer l'affichage initial
        self.progress_window.update_idletasks()
        self.progress_window.update()
    
    def _cancel_during_progress(self):
        """Annulation demandée pendant le traitement.
        Positionne un flag que _run_optimization peut consulter."""
        self._cancel_requested = True
        if hasattr(self, 'task_label'):
            self.task_label.config(text=_("Annulation en cours..."))
        if hasattr(self, 'progress_cancel_button'):
            self.progress_cancel_button.config(state='disabled')
    
    def update_progress(self, task_text=None):
        """Force la mise à jour de la fenêtre de progression
        
        Args:
            task_text: Texte de la tâche en cours à afficher (optionnel)
        """
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                if task_text and hasattr(self, 'task_label'):
                    self.task_label.config(text=task_text)
                
                # Incrémenter la barre de progression
                if hasattr(self, 'progress_bar') and hasattr(self, 'progress_steps'):
                    # Ne pas dépasser 90% (laisser les 10% finaux pour le finish)
                    if self.progress_bar['value'] < 90:
                        self.progress_bar['value'] += self.progress_increment
                
                self.progress_window.update()
            except:
                pass
    
    def complete_progress(self, result_text=None, on_cancel=None):
        """Complète la barre de progression à 100% et affiche le résultat avec boutons OK + Annuler.
        
        Args:
            result_text: Texte de résumé à afficher (optionnel)
            on_cancel: Callback appelé si l'utilisateur clique sur Annuler (optionnel).
        """
        self._progress_result = 'ok'
        self._on_cancel_progress = on_cancel
        
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                if hasattr(self, 'progress_bar'):
                    self.progress_bar['value'] = 100
                
                # Mettre à jour le label principal
                if hasattr(self, 'progress_label'):
                    self.progress_label.config(text=_("Optimisation terminée !"))
                
                # Afficher le texte de résultat
                if result_text and hasattr(self, 'task_label'):
                    self.task_label.config(text=result_text, wraplength=490)
                elif hasattr(self, 'task_label'):
                    self.task_label.config(text=_("Terminé."))
                
                # La fenêtre est déjà à la taille finale (550x400)
                
                # Autoriser la fermeture par la croix
                self.progress_window.protocol("WM_DELETE_WINDOW", self._close_completed_progress)
                
                # Label du timer de fermeture automatique
                self._auto_close_remaining = 60
                self._auto_close_label = ttk.Label(
                    self.progress_window,
                    text=_("Fermeture automatique de la fenêtre dans {} s").format(self._auto_close_remaining),
                    font=("Segoe UI", 8),
                    foreground="gray"
                )
                self._auto_close_label.pack(pady=(5, 0))
                
                # Ajouter le bouton OK à droite du bouton Annuler existant
                ok_button = ttk.Button(
                    self.progress_btn_frame,
                    text="OK",
                    command=self._close_completed_progress,
                    width=12
                )
                ok_button.pack(side=tk.LEFT, padx=5)
                ok_button.focus_set()
                
                # Réactiver et rebrancher le bouton Annuler sur le callback de restauration
                self.progress_cancel_button.config(
                    state='normal',
                    command=self._cancel_completed_progress
                )
                
                # Bind Entrée et Escape
                self.progress_window.bind('<Return>', lambda e: self._close_completed_progress())
                self.progress_window.bind('<Escape>', lambda e: self._cancel_completed_progress())
                
                self.progress_window.update()
                
                # Lancer le timer de fermeture automatique
                self._auto_close_tick()
                
                # Attendre que l'utilisateur clique sur OK ou Annuler
                self.progress_window.mainloop()
            except:
                pass
    
    def _auto_close_tick(self):
        """Décompte du timer de fermeture automatique (1 tick/s)."""
        if not hasattr(self, 'progress_window') or not self.progress_window:
            return
        try:
            self._auto_close_remaining -= 1
            if self._auto_close_remaining <= 0:
                self._close_completed_progress()
                return
            self._auto_close_label.config(
                text=_("Fermeture automatique de la fenêtre dans {} s").format(self._auto_close_remaining)
            )
            self._auto_close_timer_id = self.progress_window.after(1000, self._auto_close_tick)
        except:
            pass
    
    def _close_completed_progress(self):
        """Ferme la fenêtre de progression après clic sur OK ou expiration du timer."""
        self._progress_result = 'ok'
        self._stop_auto_close_and_destroy()
    
    def _cancel_completed_progress(self):
        """Annule le traitement et appelle le callback de restauration."""
        self._progress_result = 'cancel'
        self._stop_auto_close_and_destroy()
        if self._on_cancel_progress:
            try:
                self._on_cancel_progress()
            except Exception:
                pass
    
    def _stop_auto_close_and_destroy(self):
        """Arrête le timer et ferme la fenêtre."""
        if hasattr(self, '_auto_close_timer_id'):
            try:
                self.progress_window.after_cancel(self._auto_close_timer_id)
            except:
                pass
        if hasattr(self, 'progress_window') and self.progress_window:
            try:
                self.progress_window.quit()
                self.progress_window.destroy()
                self.progress_window = None
            except:
                pass
    
    def _on_cancel_clicked(self):
        """Gère le clic sur Annuler"""
        if self.on_cancel:
            self.on_cancel()
        self.master.quit()
        self.master.destroy()
    
    def _show_about(self):
        """Affiche la fenêtre À propos avec les informations"""
        about_window = tk.Toplevel(self.master)
        about_window.title(_("À propos - OptimLaser"))
        about_window.geometry("400x380")
        about_window.transient(self.master)
        about_window.grab_set()
        about_window.resizable(False, False)
        
        # Icône de la fenêtre
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    about_window.iconphoto(False, photo)
                    about_window.image = photo
                except:
                    pass
        except:
            pass
        
        # Centrer sur la fenêtre parente
        about_window.update_idletasks()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        window_w = about_window.winfo_width()
        window_h = about_window.winfo_height()
        x = parent_x + (parent_w - window_w) // 2
        y = parent_y + (parent_h - window_h) // 2
        about_window.geometry(f"+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(about_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Image en haut
        image_loaded = False
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
            if os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path)
                    img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    image_label = ttk.Label(main_frame, image=photo)
                    image_label.image = photo
                    image_label.pack(pady=(0, 15))
                    image_loaded = True
                except:
                    pass
        except:
            pass
        
        # Texte d'information
        info_text = (
            _("OptimLaser v{}").format(__version__) + "\n\n"
            + _("Auteur : Frank SAURET") + "\n"
            + _("Licence : GPLv2") + "\n\n"
            + _("Modules :") + "\n"
            "  • " + _("Détection de doublons intelligente") + "\n"
            "  • " + _("Optimisation du parcours (3 stratégies)") + "\n"
        )
        
        ttk.Label(
            main_frame,
            text=info_text,
            justify=tk.CENTER,
            foreground=self.fg_color
        ).pack(pady=(0, 10))
        
        # Lien GitHub
        github_url = "https://github.com/FrankSAURET/OptimLaser"
        link_label = tk.Label(
            main_frame,
            text=github_url,
            fg="#0066cc",
            bg=self.bg_unselected,
            cursor="hand2",
            font=('Arial', 9, 'underline')
        )
        link_label.pack(pady=(0, 15))
        link_label.bind("<Button-1>", lambda e: __import__('webbrowser').open(github_url))
        
        # Bouton OK
        ttk.Button(
            main_frame,
            text="OK",
            command=about_window.destroy,
            width=10
        ).pack()
    
    def get_parameters(self) -> Dict:
        """
        Récupère tous les paramètres de l'interface.
        
        Returns:
            Dictionnaire avec tous les paramètres
        """
        return {
            'tolerance': self._parse_decimal(self.tolerance_spinbox.get()),
            'enable_partial_overlap': self.enable_partial_overlap.get(),
            'overlap_threshold': 0.0,
            'enable_global_optimization': self.enable_global_optimization.get(),
            'optimization_strategy': self.optimization_strategy.get(),
            'max_iterations': self.max_iterations.get(),
            'zonage_direction': self.zonage_direction.get(),
            'zonage_size_mm': self.zonage_size_mm.get(),
            'laser_speed': self._parse_decimal(self.laser_speed_spinbox.get()),
            'idle_speed': self._parse_decimal(self.idle_speed_spinbox.get()),
            'colors_order': self.colors_order.copy(),
            'speed_preset': self.selected_speed_name.get(),
            'SupprimerCouleursNonGerees': self.remove_unmanaged_colors.get(),
            'SauvegarderSousDecoupe': self.save_as_cutting.get()
        }


def show_gui(config_file: Optional[str] = None,
             on_apply: Optional[Callable] = None,
             on_cancel: Optional[Callable] = None):
    """
    Affiche l'interface graphique et retourne les paramètres et l'instance GUI.
    
    Args:
    config_file: Chemin vers OptimLaser.json
        on_apply: Callback lors de l'application
        on_cancel: Callback lors de l'annulation
        
    Returns:
        Tuple (paramètres, instance_gui)
    """
    root = tk.Tk()
    root.title(_("OptimLaser"))
    root.resizable(True, True)
    
    # Centrer la fenêtre avant de définir sa taille
    window_width = 700
    window_height = 550
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Définir l'icône de la fenêtre
    try:
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'optimlaser.png')
        if os.path.exists(icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                root.iconphoto(False, photo)
                root.image = photo  # Garder une référence
            except:
                pass
    except:
        pass
    
    # Mettre la fenêtre en premier plan
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    root.focus_force()
    
    # Icône (si disponible)
    # root.iconbitmap("icon.ico")
    
    gui = OptimLaserGUI(root, on_apply, on_cancel, config_file)
    
    root.mainloop()
    
    # Retourner les paramètres sauvegardés et l'instance GUI
    return gui.saved_parameters, gui


# Test standalone
if __name__ == '__main__':
    def on_apply(params):
        print("\n=== Paramètres appliqués ===")
        for key, value in params.items():
            print(f"{key}: {value}")
        import sys
        sys.exit(0)
    
    def on_cancel():
        print("Annulé")
        import sys
        sys.exit(0)
    
    # Trouver le fichier de config
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OptimLaser.json')
    
    show_gui(config_file=config_path, on_apply=on_apply, on_cancel=on_cancel)
