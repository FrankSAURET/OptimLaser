"""
 _______       _            _     _          ______        _                 _ 
(_______)     (_)       _  (_)   | |        (____  \      (_)               | |
 _______  ____ _  ___ _| |_ _  __| |_____    ____)  ) ____ _ _____ ____   __| |
|  ___  |/ ___) |/___|_   _) |/ _  | ___ |  |  __  ( / ___) (____ |  _ \ / _  |
| |   | | |   | |___ | | |_| ( (_| | ____|  | |__)  ) |   | / ___ | | | ( (_| |
|_|   |_|_|   |_(___/   \__)_|\____|_____)  |______/|_|   |_\_____|_| |_|\____|
    
Auteur: Frank SAURET(frank.sauret.prof@gmail.com) 
SauverFichier.py(Ɔ) 2023
Description : Forcer la sauvegarde
Créé le :  jeudi 19 janvier 2023, 10:45:04 
Dernière modification : dimanche 8 janvier 2023, 17:38:34"""

import os


def save_file_before_start(file_path):
    # Invite l'utilisateur à sauvegarder le fichier avant de continuer
    input("Please save your file before continuing. Press Enter to continue...")

    # Récupération du nom de fichier et de son extension
    base_file, file_extension = os.path.splitext(file_path)

    # Création du nouveau nom de fichier
    new_file_name = base_file + "-laser" + file_extension

    # Enregistrement de la nouvelle version du fichier
    os.rename(file_path, new_file_name)
    print(f"File saved as {new_file_name}")
