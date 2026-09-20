#!/usr/bin/env python3
"""
HIdden.exe Builder - Convertisseur avancé Python -> EXE.
Interface Tkinter stylisée hacker (rouge, vert, jaune, noir).
Créé par hackers_tchad.
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, List, Optional

THEME = {
    "bg": "#050505",
    "bg_card": "#0d0d0d",
    "bg_input": "#141414",
    "fg": "#e6e6e6",
    "green": "#00ff41",
    "green_dim": "#008f11",
    "red": "#ff1a1a",
    "red_dim": "#8a0b0b",
    "yellow": "#ffcc00",
    "yellow_dim": "#997a00",
    "cyan": "#00ffff",
    "border": "#2a2a2a",
    "accent": "#00ff41",
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def resource_path(relative_path: str) -> str:
    """Retourne le chemin absolu d'une ressource (compatible PyInstaller)."""
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def centered_text(text: str, width: int = 70, char: str = "=") -> str:
    pad = max(0, width - len(text) - 2)
    left = pad // 2
    right = pad - left
    return f"{char * left} {text} {char * right}"


def format_bytes_size(num: float, suffix: str = "B") -> str:
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


def estimate_build_size(script_path: str, onefile: bool) -> str:
    try:
        base = os.path.getsize(script_path) if os.path.isfile(script_path) else 0
        factor = 12 if onefile else 4
        return format_bytes_size(base * factor)
    except Exception:
        return "Inconnu"


# -----------------------------------------------------------------------------
# Configuration du build
# -----------------------------------------------------------------------------
@dataclass
class BuildConfig:
    script_path: str = ""
    output_dir: str = ""
    exe_name: str = "output"
    icon_path: str = ""
    profile_image_path: str = ""
    additional_files: List[str] = field(default_factory=list)
    hidden_imports: List[str] = field(default_factory=list)
    onefile: bool = True
    windowed: bool = False
    uac_admin: bool = False
    disable_console: bool = False
    clean_build: bool = True
    company: str = "hackers_tchad"
    product: str = "HIdden.exe Output"
    version: str = "1.0.0.0"
    copyright_: str = "© hackers_tchad"
    description: str = "Application générée avec HIdden.exe Builder"

    def to_dict(self) -> dict:
        return {
            "script_path": self.script_path,
            "output_dir": self.output_dir,
            "exe_name": self.exe_name,
            "icon_path": self.icon_path,
            "profile_image_path": self.profile_image_path,
            "additional_files": self.additional_files,
            "hidden_imports": self.hidden_imports,
            "onefile": self.onefile,
            "windowed": self.windowed,
            "uac_admin": self.uac_admin,
            "disable_console": self.disable_console,
            "clean_build": self.clean_build,
            "company": self.company,
            "product": self.product,
            "version": self.version,
            "copyright": self.copyright_,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildConfig":
        cfg = cls()
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
            elif key == "copyright":
                cfg.copyright_ = value
        return cfg


# -----------------------------------------------------------------------------
# Logger GUI
# -----------------------------------------------------------------------------
class GuiLogger:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.text = text_widget

    def log(self, message: str, color: str = THEME["fg"], tag: Optional[str] = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full = f"[{timestamp}] {message}"
        self.text.configure(state="normal")
        if tag is None:
            tag = f"color_{color.replace('#', '')}"
        self.text.tag_configure(tag, foreground=color)
        self.text.insert("end", full + "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def info(self, message: str):
        self.log(message, THEME["green"])

    def warning(self, message: str):
        self.log(message, THEME["yellow"])

    def error(self, message: str):
        self.log(message, THEME["red"])


# -----------------------------------------------------------------------------
# Builder Engine
# -----------------------------------------------------------------------------
class BuilderEngine:
    def __init__(self, config: BuildConfig, logger: GuiLogger, progress_callback: Callable[[float, str], None]):
        self.config = config
        self.logger = logger
        self.progress = progress_callback
        self.cancelled = False
        self.spec_path: Optional[str] = None
        self.output_exe: Optional[str] = None

    def cancel(self):
        self.cancelled = True
        self.logger.warning("Annulation demandée par l'utilisateur...")

    def run(self) -> bool:
        try:
            self._check_prerequisites()
            if self.cancelled:
                return False
            self._prepare_workspace()
            if self.cancelled:
                return False
            self._generate_spec()
            if self.cancelled:
                return False
            self._build()
            if self.cancelled:
                return False
            self._post_build()
            return not self.cancelled
        except Exception as exc:
            self.logger.error(f"ERREUR FATALE: {exc}")
            return False

    def _check_prerequisites(self):
        self.progress(0.05, "Vérification de PyInstaller...")
        self.logger.info("Vérification des prérequis...")
        try:
            import PyInstaller
            self.logger.info(f"PyInstaller détecté: {PyInstaller.__version__}")
        except ImportError:
            self.logger.warning("PyInstaller non détecté. Tentative d'installation...")
            self._run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], timeout=120)

    def _prepare_workspace(self):
        self.progress(0.10, "Préparation du dossier de build...")
        cfg = self.config
        if not os.path.isfile(cfg.script_path):
            raise FileNotFoundError(f"Script introuvable: {cfg.script_path}")
        if not cfg.output_dir:
            cfg.output_dir = os.path.join(os.path.dirname(cfg.script_path), "dist")
        os.makedirs(cfg.output_dir, exist_ok=True)
        self.work_dir = os.path.join(cfg.output_dir, "hidden_build_work")
        if cfg.clean_build and os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
        os.makedirs(self.work_dir, exist_ok=True)
        shutil.copy2(cfg.script_path, os.path.join(self.work_dir, "main_script.py"))
        for f in cfg.additional_files:
            if os.path.isfile(f):
                shutil.copy2(f, self.work_dir)
                self.logger.info(f"Ressource copiée: {os.path.basename(f)}")
        self.logger.info(f"Espace de travail: {self.work_dir}")

    def _generate_spec(self):
        self.progress(0.20, "Génération du fichier .spec...")
        cfg = self.config
        script_name = "main_script.py"
        icon_line = f"icon='{self._escape(cfg.icon_path)}'," if cfg.icon_path and os.path.isfile(cfg.icon_path) else ""
        hidden_imports = ", ".join(repr(h) for h in cfg.hidden_imports) if cfg.hidden_imports else ""

        version_file = self._generate_version_file()

        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Analysis, PYZ, EXE, PKG, COLLECT

a = Analysis(
    ['{script_name}'],
    pathex=[r'{self._escape(self.work_dir)}'],
    binaries=[],
    datas=[],
    hiddenimports=[{hidden_imports}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
"""
        if cfg.onefile:
            spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{cfg.exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={not cfg.disable_console},
    hide_console='hide-early' if {cfg.disable_console} else None,
    {icon_line}
    version='{self._escape(version_file)}' if '{self._escape(version_file)}' else None,
    uac_admin={cfg.uac_admin},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    windowed={cfg.windowed},
)
"""
        else:
            spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{cfg.exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={not cfg.disable_console},
    {icon_line}
    version='{self._escape(version_file)}' if '{self._escape(version_file)}' else None,
    uac_admin={cfg.uac_admin},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    windowed={cfg.windowed},
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{cfg.exe_name}',
)
"""
        self.spec_path = os.path.join(self.work_dir, f"{cfg.exe_name}.spec")
        with open(self.spec_path, "w", encoding="utf-8") as f:
            f.write(spec_content)
        self.logger.info(f"Fichier .spec généré: {self.spec_path}")

    def _generate_version_file(self) -> str:
        cfg = self.config
        version_file = os.path.join(self.work_dir, "version_info.txt")
        parts = cfg.version.split(".") + ["0", "0", "0", "0"]
        vs = ",".join(parts[:4])
        content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    fileVersion=({vs}),
    productVersion=({vs}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{cfg.company}'),
        StringStruct(u'FileDescription', u'{cfg.description}'),
        StringStruct(u'FileVersion', u'{cfg.version}'),
        StringStruct(u'InternalName', u'{cfg.exe_name}'),
        StringStruct(u'LegalCopyright', u'{cfg.copyright_}'),
        StringStruct(u'OriginalFilename', u'{cfg.exe_name}.exe'),
        StringStruct(u'ProductName', u'{cfg.product}'),
        StringStruct(u'ProductVersion', u'{cfg.version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [0x409, 1200])])
  ]
)
"""
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)
        return version_file

    def _build(self):
        self.progress(0.30, "Compilation en cours...")
        cfg = self.config
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            self.spec_path,
            "--distpath", cfg.output_dir,
            "--workpath", os.path.join(self.work_dir, "build"),
            "--specpath", self.work_dir,
            "--noconfirm",
        ]
        if cfg.clean_build:
            cmd.append("--clean")
        self.logger.info(f"Commande: {' '.join(cmd)}")
        self._run_command(cmd, timeout=600)

    def _post_build(self):
        self.progress(0.95, "Finalisation...")
        cfg = self.config
        if cfg.onefile:
            candidate = os.path.join(cfg.output_dir, f"{cfg.exe_name}.exe")
        else:
            candidate = os.path.join(cfg.output_dir, cfg.exe_name, f"{cfg.exe_name}.exe")
        if os.path.isfile(candidate):
            self.output_exe = candidate
            size = format_bytes_size(os.path.getsize(candidate))
            self.logger.info(f"✅ EXE généré: {candidate} ({size})")
        else:
            self.logger.warning("Fichier EXE non trouvé à l'emplacement attendu.")
        if cfg.clean_build:
            shutil.rmtree(self.work_dir, ignore_errors=True)
        self.progress(1.0, "Terminé")

    def _run_command(self, cmd: List[str], timeout: int = 60):
        self.logger.info(f"Exécution: {' '.join(cmd[:5])}...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        start = time.time()
        try:
            for line in process.stdout:  # type: ignore
                if self.cancelled:
                    process.terminate()
                    break
                stripped = line.rstrip()
                if stripped:
                    self.logger.log(stripped, THEME["cyan"])
                if time.time() - start > timeout:
                    process.kill()
                    raise TimeoutError(f"Commande dépassée ({timeout}s)")
            process.wait(timeout=max(1, timeout - (time.time() - start)))
        except Exception:
            process.kill()
            raise
        if process.returncode != 0 and not self.cancelled:
            raise RuntimeError(f"Commande échouée avec code {process.returncode}")

    @staticmethod
    def _escape(path: str) -> str:
        return path.replace("\\", "/").replace("'", "\\'")


# -----------------------------------------------------------------------------
# Interface graphique
# -----------------------------------------------------------------------------
class HiddenBuilderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HIdden.exe Builder - by hackers_tchad")
        self.root.geometry("1100x850")
        self.root.configure(bg=THEME["bg"])
        self.root.option_add("*Font", ("Consolas", 10))

        self.config = BuildConfig()
        self._load_settings()

        self.style = ttk.Style()
        self._configure_styles()

        self._build_header()
        self._build_notebook()
        self._build_progress()
        self._build_console()
        self._build_footer()

        self._update_stats()

    def _configure_styles(self):
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=THEME["bg"])
        self.style.configure("TLabel", background=THEME["bg"], foreground=THEME["fg"], font=("Consolas", 10))
        self.style.configure("TButton", background=THEME["green_dim"], foreground=THEME["fg"], font=("Consolas", 10, "bold"), borderwidth=0)
        self.style.map("TButton", background=[("active", THEME["green"])], foreground=[("active", "#000000")])
        self.style.configure("Red.TButton", background=THEME["red_dim"], foreground=THEME["fg"])
        self.style.map("Red.TButton", background=[("active", THEME["red"])], foreground=[("active", "#000000")])
        self.style.configure("TEntry", fieldbackground=THEME["bg_input"], foreground=THEME["fg"], insertcolor=THEME["green"])
        self.style.configure("TCheckbutton", background=THEME["bg"], foreground=THEME["fg"])
        self.style.configure("TNotebook", background=THEME["bg"], tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", background=THEME["bg_card"], foreground=THEME["fg"], padding=[10, 4], font=("Consolas", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", THEME["green_dim"])], foreground=[("selected", "#000000")])

    def _build_header(self):
        header = tk.Frame(self.root, bg=THEME["bg"], height=100)
        header.pack(fill="x", padx=15, pady=(15, 5))
        header.pack_propagate(False)

        title = tk.Label(header, text="HIdden.exe", bg=THEME["bg"], fg=THEME["red"], font=("Impact", 42, "bold"))
        title.pack(side="left", padx=10)

        subtitle = tk.Label(header, text="Python to EXE Builder // hackers_tchad", bg=THEME["bg"], fg=THEME["green"], font=("Consolas", 12, "bold"))
        subtitle.pack(side="left", padx=10, pady=(20, 0))

        self.profile_label = tk.Label(header, bg=THEME["bg_card"], width=8, height=4, relief="solid", borderwidth=2, highlightbackground=THEME["green"])
        self.profile_label.pack(side="right", padx=15)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_build = tk.Frame(self.notebook, bg=THEME["bg"])
        self.tab_advanced = tk.Frame(self.notebook, bg=THEME["bg"])
        self.tab_profile = tk.Frame(self.notebook, bg=THEME["bg"])
        self.tab_logs = tk.Frame(self.notebook, bg=THEME["bg"])
        self.tab_help = tk.Frame(self.notebook, bg=THEME["bg"])

        self.notebook.add(self.tab_build, text=" Build ")
        self.notebook.add(self.tab_advanced, text=" Avancé ")
        self.notebook.add(self.tab_profile, text=" Profil ")
        self.notebook.add(self.tab_logs, text=" Logs ")
        self.notebook.add(self.tab_help, text=" Aide ")

        self._build_build_tab()
        self._build_advanced_tab()
        self._build_profile_tab()
        self._build_logs_tab()
        self._build_help_tab()

    def _build_build_tab(self):
        frame = self.tab_build
        card = tk.Frame(frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(card, text="Script Python source (.py)", bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 11, "bold")).grid(row=0, column=0, sticky="w", padx=15, pady=12)
        self.entry_script = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=70)
        self.entry_script.grid(row=0, column=1, padx=10, pady=12, sticky="ew")
        tk.Button(card, text="Parcourir", command=self._browse_script, bg=THEME["green_dim"], fg=THEME["fg"], font=("Consolas", 9, "bold"), relief="flat").grid(row=0, column=2, padx=10, pady=12)

        tk.Label(card, text="Dossier de sortie", bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 11, "bold")).grid(row=1, column=0, sticky="w", padx=15, pady=12)
        self.entry_output = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=70)
        self.entry_output.grid(row=1, column=1, padx=10, pady=12, sticky="ew")
        tk.Button(card, text="Parcourir", command=self._browse_output, bg=THEME["green_dim"], fg=THEME["fg"], font=("Consolas", 9, "bold"), relief="flat").grid(row=1, column=2, padx=10, pady=12)

        tk.Label(card, text="Nom de l'EXE", bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 11, "bold")).grid(row=2, column=0, sticky="w", padx=15, pady=12)
        self.entry_exe = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=40)
        self.entry_exe.insert(0, self.config.exe_name)
        self.entry_exe.grid(row=2, column=1, sticky="w", padx=10, pady=12)

        options = tk.Frame(card, bg=THEME["bg_card"])
        options.grid(row=3, column=0, columnspan=3, sticky="w", padx=15, pady=10)

        self.var_onefile = tk.BooleanVar(value=self.config.onefile)
        tk.Checkbutton(options, text="One File (--onefile)", variable=self.var_onefile, bg=THEME["bg_card"], fg=THEME["fg"], selectcolor=THEME["bg_input"], activebackground=THEME["bg_card"], activeforeground=THEME["green"]).pack(side="left", padx=10)

        self.var_windowed = tk.BooleanVar(value=self.config.windowed)
        tk.Checkbutton(options, text="Windowed (GUI)", variable=self.var_windowed, bg=THEME["bg_card"], fg=THEME["fg"], selectcolor=THEME["bg_input"], activebackground=THEME["bg_card"], activeforeground=THEME["green"]).pack(side="left", padx=10)

        self.var_noconsole = tk.BooleanVar(value=self.config.disable_console)
        tk.Checkbutton(options, text="No Console", variable=self.var_noconsole, bg=THEME["bg_card"], fg=THEME["fg"], selectcolor=THEME["bg_input"], activebackground=THEME["bg_card"], activeforeground=THEME["green"]).pack(side="left", padx=10)

        self.var_uac = tk.BooleanVar(value=self.config.uac_admin)
        tk.Checkbutton(options, text="Admin UAC", variable=self.var_uac, bg=THEME["bg_card"], fg=THEME["fg"], selectcolor=THEME["bg_input"], activebackground=THEME["bg_card"], activeforeground=THEME["green"]).pack(side="left", padx=10)

        actions = tk.Frame(card, bg=THEME["bg_card"])
        actions.grid(row=4, column=0, columnspan=3, pady=25)

        tk.Button(actions, text="🔥 BUILD EXE", command=self._start_build, bg=THEME["red"], fg="#000000", font=("Consolas", 14, "bold"), relief="flat", padx=30, pady=8).pack(side="left", padx=15)
        tk.Button(actions, text="Annuler", command=self._cancel_build, bg=THEME["yellow_dim"], fg=THEME["fg"], font=("Consolas", 12, "bold"), relief="flat", padx=20, pady=8).pack(side="left", padx=15)

        self.stats_label = tk.Label(card, text="Statistiques", bg=THEME["bg_card"], fg=THEME["cyan"], font=("Consolas", 10, "bold"), justify="left")
        self.stats_label.grid(row=5, column=0, columnspan=3, sticky="w", padx=15, pady=15)

        card.columnconfigure(1, weight=1)

    def _build_advanced_tab(self):
        frame = self.tab_advanced
        card = tk.Frame(frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        fields = [
            ("Icône (.ico)", "icon_path", self._browse_icon),
            ("Imports cachés (virgule)", "hidden_imports", None),
            ("Fichiers supplémentaires (virgule)", "additional_files", self._browse_files),
        ]
        self.adv_entries: dict = {}
        for idx, (label, key, cmd) in enumerate(fields):
            tk.Label(card, text=label, bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 10, "bold")).grid(row=idx, column=0, sticky="w", padx=15, pady=10)
            ent = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=70)
            ent.grid(row=idx, column=1, padx=10, pady=10, sticky="ew")
            self.adv_entries[key] = ent
            if cmd:
                tk.Button(card, text="Parcourir", command=cmd, bg=THEME["green_dim"], fg=THEME["fg"], font=("Consolas", 9, "bold"), relief="flat").grid(row=idx, column=2, padx=10, pady=10)

        card.columnconfigure(1, weight=1)

    def _build_profile_tab(self):
        frame = self.tab_profile
        card = tk.Frame(frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        fields = [
            ("Société", "company"),
            ("Produit", "product"),
            ("Version", "version"),
            ("Copyright", "copyright_"),
            ("Description", "description"),
        ]
        self.profile_entries: dict = {}
        for idx, (label, key) in enumerate(fields):
            tk.Label(card, text=label, bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 10, "bold")).grid(row=idx, column=0, sticky="w", padx=15, pady=10)
            ent = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=60)
            ent.insert(0, getattr(self.config, key))
            ent.grid(row=idx, column=1, padx=10, pady=10, sticky="w")
            self.profile_entries[key] = ent

        tk.Label(card, text="Image de profil", bg=THEME["bg_card"], fg=THEME["yellow"], font=("Consolas", 10, "bold")).grid(row=len(fields), column=0, sticky="w", padx=15, pady=10)
        self.entry_profile_img = tk.Entry(card, bg=THEME["bg_input"], fg=THEME["fg"], insertbackground=THEME["green"], relief="flat", width=60)
        self.entry_profile_img.grid(row=len(fields), column=1, padx=10, pady=10, sticky="w")
        tk.Button(card, text="Parcourir", command=self._browse_profile_image, bg=THEME["green_dim"], fg=THEME["fg"], font=("Consolas", 9, "bold"), relief="flat").grid(row=len(fields), column=2, padx=10, pady=10)

        card.columnconfigure(1, weight=1)

    def _build_logs_tab(self):
        frame = self.tab_logs
        self.log_text = scrolledtext.ScrolledText(frame, bg=THEME["bg"], fg=THEME["fg"], insertbackground=THEME["green"], font=("Consolas", 9), state="disabled", relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=THEME["border"])
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.logger = GuiLogger(self.log_text)

    def _build_help_tab(self):
        frame = self.tab_help
        text = scrolledtext.ScrolledText(frame, bg=THEME["bg"], fg=THEME["green"], font=("Consolas", 10), wrap="word", state="disabled", relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=THEME["border"])
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.configure(state="normal")
        help_content = """HIdden.exe Builder - Aide

1. Sélectionnez votre script Python source.
2. Choisissez le dossier de sortie.
3. Configurez le nom de l'EXE et les options.
4. (Optionnel) Ajoutez une icône, des imports cachés, des fichiers supplémentaires.
5. Remplissez les informations de version/profil.
6. Cliquez sur BUILD EXE.

Options:
- One File : génère un seul fichier EXE.
- Windowed : pour les applications graphiques.
- No Console : masque la console au lancement.
- Admin UAC : demande les droits administrateur.

Créé par hackers_tchad.
"""
        text.insert("1.0", help_content)
        text.configure(state="disabled")

    def _build_progress(self):
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label = tk.Label(self.root, text="Prêt", bg=THEME["bg"], fg=THEME["green"], font=("Consolas", 10, "bold"), anchor="w")
        self.progress_label.pack(fill="x", padx=15, pady=(0, 5))
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=1.0, mode="determinate")
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 10))

    def _build_console(self):
        pass

    def _build_footer(self):
        footer = tk.Label(self.root, text="[ HIdden.exe Builder ] [ Version 1.0.0 ] [ hackers_tchad ]", bg=THEME["bg"], fg=THEME["red"], font=("Consolas", 9, "bold"))
        footer.pack(fill="x", padx=15, pady=(0, 10))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _browse_script(self):
        path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.entry_script.delete(0, "end")
            self.entry_script.insert(0, path)
            base = Path(path).stem
            self.entry_exe.delete(0, "end")
            self.entry_exe.insert(0, base)
            if not self.entry_output.get():
                self.entry_output.insert(0, str(Path(path).parent / "dist"))

    def _browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, path)

    def _browse_icon(self):
        path = filedialog.askopenfilename(filetypes=[("Icon files", "*.ico"), ("All files", "*.*")])
        if path:
            self.adv_entries["icon_path"].delete(0, "end")
            self.adv_entries["icon_path"].insert(0, path)

    def _browse_files(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self.adv_entries["additional_files"].delete(0, "end")
            self.adv_entries["additional_files"].insert(0, ",".join(paths))

    def _browse_profile_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if path:
            self.entry_profile_img.delete(0, "end")
            self.entry_profile_img.insert(0, path)
            self._load_profile_image(path)

    def _load_profile_image(self, path: str):
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            img = img.resize((80, 80), Image.Resampling.LANCZOS)
            self.profile_photo = ImageTk.PhotoImage(img)
            self.profile_label.configure(image=self.profile_photo)
        except Exception as exc:
            self.logger.error(f"Impossible de charger l'image: {exc}")

    def _update_stats(self):
        script = self.entry_script.get()
        onefile = self.var_onefile.get()
        size = estimate_build_size(script, onefile) if script else "Inconnu"
        self.stats_label.configure(text=f"Mode: {'OneFile' if onefile else 'OneDir'} | Taille estimée: {size} | Statut: Prêt")

    def _gather_config(self) -> BuildConfig:
        cfg = BuildConfig()
        cfg.script_path = self.entry_script.get().strip()
        cfg.output_dir = self.entry_output.get().strip()
        cfg.exe_name = self.entry_exe.get().strip() or "output"
        cfg.icon_path = self.adv_entries["icon_path"].get().strip()
        cfg.hidden_imports = [x.strip() for x in self.adv_entries["hidden_imports"].get().split(",") if x.strip()]
        cfg.additional_files = [x.strip() for x in self.adv_entries["additional_files"].get().split(",") if x.strip()]
        cfg.profile_image_path = self.entry_profile_img.get().strip()
        cfg.onefile = self.var_onefile.get()
        cfg.windowed = self.var_windowed.get()
        cfg.disable_console = self.var_noconsole.get()
        cfg.uac_admin = self.var_uac.get()
        cfg.company = self.profile_entries["company"].get().strip()
        cfg.product = self.profile_entries["product"].get().strip()
        cfg.version = self.profile_entries["version"].get().strip()
        cfg.copyright_ = self.profile_entries["copyright_"].get().strip()
        cfg.description = self.profile_entries["description"].get().strip()
        return cfg

    def _start_build(self):
        self.config = self._gather_config()
        if not os.path.isfile(self.config.script_path):
            messagebox.showerror("Erreur", "Veuillez sélectionner un script Python valide.")
            return
        self._save_settings()
        self._update_stats()
        self.logger.info(f"Démarrage du build: {self.config.exe_name}")
        self.progress_var.set(0.0)
        self.builder = BuilderEngine(self.config, self.logger, self._set_progress)
        self.build_thread = threading.Thread(target=self._build_worker, daemon=True)
        self.build_thread.start()

    def _build_worker(self):
        success = self.builder.run()
        self.root.after(0, lambda: self._build_finished(success))

    def _build_finished(self, success: bool):
        if success and self.builder.output_exe:
            messagebox.showinfo("Succès", f"EXE généré:\n{self.builder.output_exe}")
        elif not success:
            messagebox.showerror("Échec", "La compilation a échoué. Consultez les logs.")
        self._update_stats()

    def _cancel_build(self):
        if hasattr(self, "builder"):
            self.builder.cancel()

    def _set_progress(self, value: float, text: str):
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.progress_label.configure(text=text))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _settings_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), ".hidden_exe_builder.json")

    def _save_settings(self):
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as exc:
            self.logger.warning(f"Impossible de sauver les paramètres: {exc}")

    def _load_settings(self):
        path = self._settings_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.config = BuildConfig.from_dict(json.load(f))
            except Exception as exc:
                self.config = BuildConfig()

    def run(self):
        self.logger.info("HIdden.exe Builder démarré.")
        self.logger.info("Prêt à convertir vos scripts Python en EXE.")
        self.root.mainloop()


def main():
    app = HiddenBuilderApp()
    app.run()


if __name__ == "__main__":
    main()
