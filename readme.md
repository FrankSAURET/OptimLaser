<h1 align="center">
  <span style="color:#045D97">⚡ OptimLaser ⚡</span>
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Version-2026.3-045D97?style=for-the-badge&logo=inkscape&logoColor=white" alt="Version"/>
  <img src="https://img.shields.io/badge/Inkscape-1.2_→_1.4.2-E0E0E0?style=for-the-badge&logo=inkscape&logoColor=black" alt="Inkscape"/>
  <img src="https://img.shields.io/badge/Licence-GPLv2-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
</p>

<p align="center">
  <span style="color:#045D97"><b>🔥 Extension Inkscape pour l'optimisation de découpe laser</b></span><br/>
  <b>🔥 Inkscape extension for laser cutting optimization</b>
</p>

<p align="center">
  <a href="#-français"><img src="https://img.shields.io/badge/🇫🇷_Français-045D97?style=flat-square" alt="FR"/></a>  
  <a href="#-english"><img src="https://img.shields.io/badge/🇬🇧_English-333333?style=flat-square" alt="EN"/></a>
</p>

---

## <span style="color:#045D97">🇫🇷 Français</span>

### <span style="color:#045D97">📋 Présentation</span>

<span style="color:#045D97">**OptimLaser** est une extension Inkscape qui optimise un dessin vectoriel pour la découpe laser.</span>


<span style="color:#045D97">**✨ Fonctionnalités principales :**</span>

- <span style="color:#045D97">✂️ Supprime les tracés en double (lignes superposées), sauf les courbes de Bézier ;</span>
- <span style="color:#045D97">🎨 Supprime les chemins dont la couleur n'est pas gérée par la découpeuse ;</span>
- <span style="color:#045D97">🚀 Optimise l'ordre de découpe pour réduire les déplacements à vide ;</span>
- <span style="color:#045D97">💾 Sauvegarde le fichier optimisé sous un nouveau nom (suffixe « - découpe ») ;</span>
- <span style="color:#045D97">🖥️ Interface graphique dynamique avec mémorisation des derniers réglages.</span>
- <span style="color:#045D97">🩶 Les éléments gris sont préservés pour la gravure.</span>

---

### <span style="color:#045D97">📦 Installation</span>

<span style="color:#045D97">Copiez le dossier <b>optimlaser</b> dans le répertoire d'extensions d'Inkscape :</span>

| <span style="color:#045D97">🖥️ Système</span> | <span style="color:#045D97">📂 Emplacement</span> |
|---|---|
| <span style="color:#045D97">**🪟 Windows**</span> | <span style="color:#045D97"><b>%appdata%\inkscape\extensions\</b></span> |
| <span style="color:#045D97">**🐧 Linux**</span> | <span style="color:#045D97"><b>~/.config/inkscape/extensions/</b></span> |
| <span style="color:#045D97">**🍎 macOS**</span> | <span style="color:#045D97"><b>~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/</b></span> |

<div style="background-color:#E6F4EA; border-left:4px solid #1A7F37; padding:8px 12px; border-radius:4px; margin:8px 0;">
<span style="color:#045D97">💡 Vous pouvez vérifier le chemin exact dans Inkscape : <b>Édition > Préférences > Système</b> (ligne « Extensions de l'utilisateur »).</span>
</div>

<span style="color:#045D97">🔁 Redémarrez Inkscape après la copie.</span>

<div style="background-color:#E6F4EA; border-left:4px solid #1A7F37; padding:8px 12px; border-radius:4px; margin:8px 0;">
<span style="color:#045D97">💡Elle peut être installée et mise à jour avec l'extension Màj : <b> extensions > Mise à jour des extensions de Frank SAURET...</b>.

Màj est téléchargeable  ici : https://github.com/FrankSAURET/Maj</span></div>

### <span style="color:#045D97">🚀 Lancement</span>

<span style="color:#045D97">Dans Inkscape, allez dans :</span>

<div style="background-color:#DBEAFE; border-left:4px solid #045D97; padding:8px 12px; border-radius:4px; margin:8px 0;">
<span style="color:#045D97">📌 <b>Extensions > Découpe Laser > Optimisation pour découpe laser…</b></span>
</div>

<span style="color:#045D97">La fenêtre de paramétrage s'ouvre automatiquement.</span>

---

### <span style="color:#045D97">⚙️ Paramètres</span>

#### <span style="color:#045D97">🔧 Onglet « Paramètres »</span>

| <span style="color:#045D97">⚙️ Paramètre</span> | <span style="color:#045D97">📝 Description</span> |
|---|---|
| <span style="color:#045D97">**📏 Tolérance de détection (mm)**</span> | <span style="color:#045D97">Distance en dessous de laquelle deux tracés sont considérés comme superposés (défaut : 0,15 mm).</span> |
| <span style="color:#045D97">**🔀 Chevauchement partiel**</span> | <span style="color:#045D97">Active la détection des segments partiellement superposés.</span> |
| <span style="color:#045D97">**🌐 Optimisation globale**</span> | <span style="color:#045D97">Active la réorganisation de l'ordre des chemins pour minimiser les trajets à vide.</span> |
| <span style="color:#045D97">**🧠 Stratégie d'optimisation**</span> | <span style="color:#045D97">Choix entre : **Plus proche voisin** (rapide), **Optimisation locale** (2-opt amélioré), **Zonage** (découpage géographique en colonnes ou lignes).</span> |
| <span style="color:#045D97">**🔢 Itérations max**</span> | <span style="color:#045D97">Nombre maximal d'itérations pour la stratégie d'optimisation locale.</span> |
| <span style="color:#045D97">**📐 Direction / Taille du zonage**</span> | <span style="color:#045D97">Pour la stratégie Zonage : direction (colonnes ou lignes) et taille des zones en mm.</span> |

#### <span style="color:#045D97">🔩 Onglet « Paramètres avancés »</span>

| <span style="color:#045D97">⚙️ Paramètre</span> | <span style="color:#045D97">📝 Description</span> |
|---|---|
| <span style="color:#045D97">**🎨 Supprimer les couleurs non gérées**</span> | <span style="color:#045D97">Supprime tous les éléments dont la couleur de trait n'est pas dans la liste des couleurs gérées.</span> |
| <span style="color:#045D97">**💾 Sauvegarder sous Découpe**</span> | <span style="color:#045D97">Enregistre le fichier optimisé avec le suffixe « - découpe ».</span> |
| <span style="color:#045D97">**⏱️ Vitesses (mm/s)**</span> | <span style="color:#045D97">Préréglages de vitesses de découpe par matériau (ex. : Contreplaqué, Acrylique, Carton…). Vitesse de découpe et vitesse à vide configurables. Les préréglages sont éditables et personnalisables.</span> |
| <span style="color:#045D97">**🌈 Ordre des couleurs**</span> | <span style="color:#045D97">Définit l'ordre de priorité des couleurs pour la découpe. Les couleurs peuvent être réordonnées, ajoutées ou supprimées.</span> |

---

### <span style="color:#045D97">📄 Configuration (OptimLaser.json)</span>

<span style="color:#045D97">Le fichier <b>OptimLaser.json</b> dans le dossier de l'extension contient :</span>

- <span style="color:#045D97">🎨 **colors** : liste ordonnée des couleurs gérées par la découpeuse ;</span>
- <span style="color:#045D97">⏱️ **speeds** : préréglages de vitesses par matériau ;</span>
- <span style="color:#045D97">💾 **last_used** : derniers paramètres utilisés (sauvegardés automatiquement).</span>

---

### <span style="color:#045D97">🌍 Traduction</span>

<span style="color:#045D97">L'interface d'OptimLaser est traduisible grâce au système **gettext**.</span>

<span style="color:#045D97">Un fichier modèle de traduction vierge (<b>.pot</b>) se trouve dans :</span>

<div style="background-color:#F3E8FF; border-left:4px solid #6F42C1; padding:8px 12px; border-radius:4px; margin:8px 0;">
<span style="color:#045D97">📂 <b>optimlaser/locale/none/LC_MESSAGES/OptimLaser.pot</b></span>
</div>

<span style="color:#045D97">**Pour créer une traduction :**</span>

<span style="color:#045D97">1️⃣ Copiez le fichier <b>OptimLaser.pot</b> et renommez-le en <b>OptimLaser.po</b> ;</span>

<span style="color:#045D97">2️⃣ Traduisez les chaînes <b>msgstr ""</b> dans le fichier <b>.po</b> avec un éditeur de texte ou un outil comme [Poedit](https://poedit.net/) ;</span>

<span style="color:#045D97">3️⃣ Compilez le fichier <b>.po</b> en <b>.mo</b> avec la commande :</span>

```bash
msgfmt OptimLaser.po -o OptimLaser.mo
```

<span style="color:#045D97">4️⃣ Placez les fichiers <b>.po</b> et <b>.mo</b> dans le dossier :</span>

<div style="background-color:#F3E8FF; border-left:4px solid #6F42C1; padding:8px 12px; border-radius:4px; margin:8px 0;">
<span style="color:#045D97">📂 <b>optimlaser/locale/&lt;code_langue&gt;/LC_MESSAGES/</b></span>
</div>

<span style="color:#045D97">(par exemple <b>optimlaser/locale/de/LC_MESSAGES/</b> pour l'allemand)</span>

<span style="color:#045D97">🤝 **Contribuer avec une traduction** : si vous réalisez une traduction, envoyez-moi le fichier <b>.po</b> ou faites une **pull request** sur le dépôt GitHub — je l'intégrerai avec plaisir !</span>

---

### <span style="color:#045D97">📜 Licence</span>

<span style="color:#045D97">Tout le code est proposé sous licence **GPLv2**.</span>
<span style="color:#045D97">✍️ Auteur : **Frank SAURET**</span>

---
---

## <a id="-english"></a>🇬🇧 English

### 📋 Overview

**OptimLaser** is an Inkscape extension that optimizes vector drawings for laser cutting.



**✨ Key features:**

- ✂️ Removes duplicate paths (overlapping lines), except Bézier curves;
- 🎨 Removes paths whose color is not managed by the laser cutter;
- 🚀 Optimizes cutting order to reduce idle travel distance;
- 💾 Saves the optimized file with a new name (suffix " - découpe");
- 🖥️ Dynamic GUI with automatic memorization of last-used settings.

---

### 📦 Installation

Copy the **`optimlaser`** folder into Inkscape's extensions directory:

| 🖥️ System | 📂 Location |
|---|---|
| **🪟 Windows** | `%appdata%\inkscape\extensions\` |
| **🐧 Linux** | `~/.config/inkscape/extensions/` |
| **🍎 macOS** | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/` |

<div style="background-color:#E6F4EA; border-left:4px solid #1A7F37; padding:8px 12px; border-radius:4px; margin:8px 0;">
💡 You can check the exact path in Inkscape: <b>Edit > Preferences > System</b> ("User extensions" line).
</div>

🔁 Restart Inkscape after copying.

---

### 🚀 Launch

In Inkscape, go to:

<div style="background-color:#DBEAFE; border-left:4px solid #045D97; padding:8px 12px; border-radius:4px; margin:8px 0;">
📌 <b>Extensions > Découpe Laser > Optimisation pour découpe laser…</b>
</div>

The settings window opens automatically.

---

### ⚙️ Settings

#### 🔧 "Paramètres" tab (Settings)

| ⚙️ Setting | 📝 Description |
|---|---|
| **📏 Detection tolerance (mm)** | Distance below which two paths are considered overlapping (default: 0.15 mm). |
| **🔀 Partial overlap** | Enables detection of partially overlapping segments. |
| **🌐 Global optimization** | Enables reordering of paths to minimize idle travel. |
| **🧠 Optimization strategy** | Choose from: **Nearest neighbor** (fast), **Local optimization** (improved 2-opt), **Zoning** (geographic grouping by columns or rows). |
| **🔢 Max iterations** | Maximum iterations for the local optimization strategy. |
| **📐 Zoning direction / size** | For the Zoning strategy: direction (columns or rows) and zone size in mm. |

#### 🔩 "Paramètres avancés" tab (Advanced settings)

| ⚙️ Setting | 📝 Description |
|---|---|
| **🎨 Remove unmanaged colors** | Removes all elements whose stroke color is not in the managed colors list. |
| **💾 Save as "Découpe"** | Saves the optimized file with the " - découpe" suffix. |
| **⏱️ Speeds (mm/s)** | Cutting speed presets per material (e.g., Plywood, Acrylic, Cardboard…). Cutting speed and idle speed are configurable. Presets are editable and customizable. |
| **🌈 Color order** | Defines the priority order of colors for cutting. Colors can be reordered, added, or removed. |

---

### 📄 Configuration (OptimLaser.json)

The `OptimLaser.json` file in the extension folder contains:

- 🎨 **colors**: ordered list of colors managed by the laser cutter;
- ⏱️ **speeds**: cutting speed presets per material;
- 💾 **last_used**: last-used parameters (saved automatically).

---

### 🌍 Translation

OptimLaser's interface is translatable using the **gettext** system.

A blank translation template file (`.pot`) is located at:

<div style="background-color:#F3E8FF; border-left:4px solid #6F42C1; padding:8px 12px; border-radius:4px; margin:8px 0;">
📂 <b>optimlaser/locale/none/LC_MESSAGES/OptimLaser.pot</b>
</div>

**To create a translation:**

1️⃣ Copy the file `OptimLaser.pot` and rename it to `OptimLaser.po`;

2️⃣ Translate the `msgstr ""` strings in the `.po` file using a text editor or a tool like [Poedit](https://poedit.net/);

3️⃣ Compile the `.po` file into `.mo` with the command:

```bash
msgfmt OptimLaser.po -o OptimLaser.mo
```

4️⃣ Place both `.po` and `.mo` files in:

<div style="background-color:#F3E8FF; border-left:4px solid #6F42C1; padding:8px 12px; border-radius:4px; margin:8px 0;">
📂 <b>optimlaser/locale/&lt;language_code&gt;/LC_MESSAGES/</b>
</div>

(e.g. `optimlaser/locale/de/LC_MESSAGES/` for German)

🤝 **Contribute a translation**: if you create a translation, send me the `.po` file or submit a **pull request** on the GitHub repository — I'll gladly include it!

---

### 📜 License

All code is offered under **GPLv2** license.
✍️ Author: **Frank SAURET**