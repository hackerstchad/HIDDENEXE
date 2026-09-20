# HIdden.exe Builder

**Convertisseur avancé Python → EXE** avec interface graphique Tkinter stylisée *hacker* (vert, rouge, jaune/noir).
Créé par **hackers_tchad**.

---

## 🚀 Fonctionnalités

- Interface moderne en une seule fenêtre (Tkinter + ttk personnalisé).
- Conversion de n'importe quel script `.py` en exécutable Windows `.exe` via **PyInstaller**.
- Choix du mode : `--onefile` ou `--onedir`, `--windowed` ou `--console`.
- Icône personnalisée (`.ico`), image de profil/logo intégrée dans la fenêtre.
- Informations de version, nom de société, description, copyright.
- Barres de progression animées, statistiques, logs en temps réel.
- Vérification automatique de PyInstaller et proposition d'installation.
- Génération d'un fichier `.spec` modifiable.
- Onglets : **Build**, **Avancé**, **Profil**, **Logs**, **Aide**.

---

## 📦 Installation

```bash
cd hidden_exe_builder
pip install -r requirements.txt
```

> Sous Linux/macOS, la génération d'EXE Windows nécessite **Wine** + PyInstaller ou un environnement Windows. L'interface fonctionne partout.

---

## ▶️ Lancement

```bash
python hidden_builder.py
```

---

## 🛠️ Utilisation

1. Sélectionnez votre script Python source.
2. Choisissez le dossier de sortie.
3. (Optionnel) Ajoutez une icône `.ico`, une image de profil/logo, et des ressources supplémentaires.
4. Configurez le nom de l'EXE, la société, la version, etc.
5. Cliquez sur **Build EXE**.

---

## 🎨 Thème

- Fond noir (`#050505`)
- Accent vert (`#00ff41`)
- Accent rouge (`#ff1a1a`)
- Accent jaune (`#ffcc00`)
- Police monospace `Consolas`

---

## 📚 Ressources utiles

- PyInstaller : https://pyinstaller.org/
- Tkinter docs : https://docs.python.org/3/library/tkinter.html
- Créer une icône `.ico` : https://convertio.co/png-ico/

---

## ⚠️ Avertissement

Cet outil est fourni à des fins éducatives et légitimes. Ne l'utilisez pas pour empaqueter du code malveillant.

---

Créé par **hackers_tchad** — apprendre, comprendre, maîtriser.
