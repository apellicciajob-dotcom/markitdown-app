# -*- coding: utf-8 -*-
"""
converter.py - core di conversione di MarkItDown App.

Riusa le regole del vecchio script di conversione a riga di comando:
  * MarkItDown per PDF/DOCX/XLSX/PPTX/EPUB/...
  * lettura UTF-8 per TXT/LOG/JSON/CSV/...
  * code fence per i file di codice
  * copia per i file Markdown
  * suffissi _1, _2 per non sovrascrivere mai nulla
  * logging su file

Novita' per Microsoft Store (MSIX): nessun dato viene scritto accanto
all'eseguibile (sola lettura in WindowsApps). Impostazioni e log vanno in
%LOCALAPPDATA%\\MarkItDownApp, i dati utente in Documents\\MarkItDownApp.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

APP_NAME = "MarkItDownApp"

# ---------------------------------------------------------------------------
# Estensioni (invariate rispetto al vecchio script)
# ---------------------------------------------------------------------------
ESTENSIONI_TESTO = {".txt", ".log", ".md", ".markdown",
                    ".json", ".csv", ".sql", ".tsv"}
ESTENSIONI_CODICE = {".py", ".js", ".ps1", ".bat", ".sh", ".html", ".css",
                     ".xml", ".yaml", ".yml", ".ini", ".cfg", ".toml"}
ESTENSIONI_MARKITDOWN = {".pdf", ".docx", ".doc", ".xlsx", ".xls",
                         ".pptx", ".ppt", ".epub", ".htm", ".rtf"}
ESTENSIONI_SUPPORTATE = (ESTENSIONI_TESTO | ESTENSIONI_CODICE
                         | ESTENSIONI_MARKITDOWN)

DEBOUNCE_SECONDI = 1.0      # dimensione/mtime stabili per almeno questo tempo
WATCH_INTERVALLO = 0.5      # periodo di polling del watcher


# ---------------------------------------------------------------------------
# Percorsi e impostazioni
# ---------------------------------------------------------------------------
def documents_dir() -> Path:
    """Cartella Documenti dell'utente (gestisce anche OneDrive/redirect)."""
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return Path(buf.value)
    except Exception:  # noqa: BLE001
        pass
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"


def local_appdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / APP_NAME


def default_data_dir() -> Path:
    return documents_dir() / APP_NAME


class Settings:
    """Impostazioni persistenti in %LOCALAPPDATA%\\MarkItDownApp\\settings.json."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else local_appdata_dir()
        self.file = self.config_dir / "settings.json"
        data = default_data_dir()
        self.ingresso: Path = data / "ingresso"
        self.conversioni: Path = data / "conversioni"
        self.tema: str = "System"        # Light | Dark | System
        self.watch_automatico: bool = True
        self.load()

    @property
    def log_dir(self) -> Path:
        return self.config_dir / "log"

    @property
    def log_file(self) -> Path:
        return self.log_dir / "conversione.log"

    def load(self) -> None:
        try:
            d = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if d.get("ingresso"):
            self.ingresso = Path(d["ingresso"])
        if d.get("conversioni"):
            self.conversioni = Path(d["conversioni"])
        if d.get("tema") in ("Light", "Dark", "System"):
            self.tema = d["tema"]
        self.watch_automatico = bool(d.get("watch_automatico", True))

    def save(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.file.write_text(json.dumps({
                "ingresso": str(self.ingresso),
                "conversioni": str(self.conversioni),
                "tema": self.tema,
                "watch_automatico": self.watch_automatico,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logging.error("Impossibile salvare le impostazioni: %s", exc)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def configura_logging(log_file: Path) -> None:
    """Log su file (nessuna console: l'app e' --noconsole)."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        if getattr(h, "_markitdown_app", False):
            root.removeHandler(h)
            h.close()
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler._markitdown_app = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    root.addHandler(handler)


def chiudi_logging() -> None:
    """Chiude esplicitamente gli handler di log: conversione.log non resta bloccato."""
    root = logging.getLogger()
    for h in list(root.handlers):
        if getattr(h, "_markitdown_app", False):
            try:
                h.flush()
                h.close()
            finally:
                root.removeHandler(h)
    logging.shutdown()


atexit.register(chiudi_logging)


# ---------------------------------------------------------------------------
# Risultato
# ---------------------------------------------------------------------------
@dataclass
class Risultato:
    sorgente: Path
    destinazione: Optional[Path]
    ok: bool
    messaggio: str = ""
    quando: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Convertitore
# ---------------------------------------------------------------------------
class Convertitore:
    def __init__(self, settings: Settings,
                 on_risultato: Optional[Callable[[Risultato], None]] = None):
        self.settings = settings
        self.on_risultato = on_risultato
        self._lock = threading.Lock()          # nomi univoci + set elaborati
        self._md_lock = threading.Lock()       # istanza MarkItDown
        self._md = None
        self._elaborati: set[tuple[str, int, int]] = set()
        self.sorgenti_appunti: set[Path] = set()   # creati da 'Incolla dagli appunti' (sessione)

    # -- cartelle ----------------------------------------------------------
    @property
    def ingresso(self) -> Path:
        return self.settings.ingresso

    @property
    def conversioni(self) -> Path:
        return self.settings.conversioni

    def assicura_cartelle(self) -> None:
        self.ingresso.mkdir(parents=True, exist_ok=True)
        self.conversioni.mkdir(parents=True, exist_ok=True)

    # -- utilita' ----------------------------------------------------------
    @staticmethod
    def _chiave(p: Path) -> tuple[str, int, int]:
        st = p.stat()
        return (str(p), st.st_size, st.st_mtime_ns)

    def segna_elaborato(self, p: Path) -> None:
        try:
            k = self._chiave(p)
        except OSError:
            return
        with self._lock:
            self._elaborati.add(k)

    def e_elaborato(self, p: Path) -> bool:
        try:
            k = self._chiave(p)
        except OSError:
            return True
        with self._lock:
            return k in self._elaborati

    def _riserva_destinazione(self, stem: str) -> Path:
        """Crea atomicamente un file vuoto con nome libero (_1, _2, ...)."""
        self.conversioni.mkdir(parents=True, exist_ok=True)
        n = 0
        with self._lock:
            while True:
                nome = f"{stem}.md" if n == 0 else f"{stem}_{n}.md"
                dest = self.conversioni / nome
                try:
                    with open(dest, "x"):
                        return dest
                except FileExistsError:
                    n += 1

    @staticmethod
    def _leggi_testo(p: Path) -> str:
        return p.read_text(encoding="utf-8-sig", errors="replace")

    # -- strategie ---------------------------------------------------------
    def _markitdown(self, sorgente: Path) -> str:
        with self._md_lock:
            if self._md is None:
                from markitdown import MarkItDown
                self._md = MarkItDown()
            md = self._md
        return md.convert(str(sorgente)).text_content

    def _testo(self, sorgente: Path) -> str:
        est = sorgente.suffix.lower()
        if est in (".md", ".markdown"):
            return self._leggi_testo(sorgente)       # "copia" per MD
        testo = self._leggi_testo(sorgente)
        if est in ESTENSIONI_CODICE:
            lingua = est.lstrip(".")
            if lingua == "ps1":
                lingua = "powershell"
            testo = f"```{lingua}\n{testo.rstrip()}\n```\n"
        return testo

    # -- API pubblica ------------------------------------------------------
    def converti_file(self, sorgente: Path) -> Risultato:
        sorgente = Path(sorgente)
        est = sorgente.suffix.lower()
        self.segna_elaborato(sorgente)   # evita doppie conversioni dal watcher
        if est not in ESTENSIONI_SUPPORTATE:
            logging.warning("Tipo non supportato, saltato: %s", sorgente.name)
            return self._emetti(Risultato(
                sorgente, None, False, f"Tipo non supportato ({est or 'senza estensione'})"))

        dest = self._riserva_destinazione(sorgente.stem)
        try:
            if est in ESTENSIONI_MARKITDOWN:
                contenuto = self._markitdown(sorgente)
            else:
                contenuto = self._testo(sorgente)
            dest.write_text(contenuto, encoding="utf-8")
        except ImportError:
            dest.unlink(missing_ok=True)
            logging.error("MarkItDown non installato (pip install 'markitdown[all]')")
            return self._emetti(Risultato(sorgente, None, False, "MarkItDown non installato"))
        except Exception as exc:  # noqa: BLE001 - logghiamo qualsiasi errore
            dest.unlink(missing_ok=True)
            logging.error("Conversione fallita per %s: %s", sorgente.name, exc)
            return self._emetti(Risultato(sorgente, None, False, str(exc)))

        logging.info("OK  %-40s -> %s", sorgente.name, dest.name)
        return self._emetti(Risultato(sorgente, dest, True, "Convertito"))

    def importa_e_converti(self, sorgente: Path) -> Risultato:
        """Copia un file esterno in ingresso (senza sovrascrivere) e lo converte."""
        sorgente = Path(sorgente)
        self.assicura_cartelle()
        try:
            if sorgente.parent.resolve() == self.ingresso.resolve():
                copia = sorgente
            else:
                copia = self._copia_in_ingresso(sorgente)
        except OSError as exc:
            logging.error("Copia fallita per %s: %s", sorgente, exc)
            return self._emetti(Risultato(sorgente, None, False, f"Copia fallita: {exc}"))
        return self.converti_file(copia)

    def _copia_in_ingresso(self, sorgente: Path) -> Path:
        n = 0
        with self._lock:
            while True:
                nome = sorgente.name if n == 0 else f"{sorgente.stem}_{n}{sorgente.suffix}"
                dest = self.ingresso / nome
                if not dest.exists():
                    break
                n += 1
            # il file e' marcato "elaborato" dopo la copia in converti_file;
            # il watcher aspetta comunque il debounce, quindi nessuna corsa.
            shutil.copy2(sorgente, dest)
        return dest

    def converti_testo_appunti(self, testo: str) -> Risultato:
        """Salva il testo come .log con timestamp in ingresso e lo converte."""
        self.assicura_cartelle()
        base = "appunti_" + time.strftime("%Y%m%d_%H%M%S")
        n = 0
        with self._lock:
            while True:
                nome = f"{base}.log" if n == 0 else f"{base}_{n}.log"
                p = self.ingresso / nome
                try:
                    with open(p, "x", encoding="utf-8", newline="") as f:
                        f.write(testo)
                    break
                except FileExistsError:
                    n += 1
            self.sorgenti_appunti.add(p)
        return self.converti_file(p)

    def converti_ingresso(self) -> list[Risultato]:
        """Converte (una volta) tutti i file presenti in ingresso, come --batch."""
        self.assicura_cartelle()
        out = []
        for p in sorted(self.ingresso.iterdir()):
            if p.is_file() and not self.e_elaborato(p) and self._stabile(p):
                out.append(self.converti_file(p))
        return out

    @staticmethod
    def _stabile(p: Path) -> bool:
        try:
            return time.time() - p.stat().st_mtime >= DEBOUNCE_SECONDI
        except OSError:
            return False

    def _emetti(self, r: Risultato) -> Risultato:
        cb = self.on_risultato
        if cb:
            try:
                cb(r)
            except Exception:  # noqa: BLE001
                logging.exception("Errore nel callback risultato")
        return r


# ---------------------------------------------------------------------------
# Watch thread-safe con debounce su dimensione/mtime
# ---------------------------------------------------------------------------
class Watcher:
    """
    Controlla la cartella di ingresso. Un file viene convertito solo quando
    dimensione e mtime non cambiano per DEBOUNCE_SECONDI e puo' essere aperto
    in lettura (la copia/scrittura e' finita). I file gia' presenti all'avvio
    sono considerati elaborati (come nel vecchio --watch).
    """

    def __init__(self, conv: Convertitore):
        self.conv = conv
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._guard = threading.Lock()

    @property
    def attivo(self) -> bool:
        t = self._thread
        return t is not None and t.is_alive()

    def avvia(self) -> None:
        with self._guard:
            if self.attivo:
                return
            self.conv.assicura_cartelle()
            for p in self.conv.ingresso.iterdir():
                if p.is_file():
                    self.conv.segna_elaborato(p)
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="watcher", daemon=True)
            self._thread.start()
        logging.info("Watch avviato su %s", self.conv.ingresso)

    def ferma(self) -> None:
        with self._guard:
            self._stop.set()
            t = self._thread
        if t and t is not threading.current_thread():
            t.join(timeout=5)
        logging.info("Watch fermato")

    def _loop(self) -> None:
        # nome -> (firma (size, mtime_ns), istante in cui la firma e' cambiata)
        visti: dict[Path, tuple[tuple[int, int], float]] = {}
        while not self._stop.wait(WATCH_INTERVALLO):
            try:
                presenti = [p for p in self.conv.ingresso.iterdir() if p.is_file()]
            except OSError:
                continue
            adesso = time.monotonic()
            for p in presenti:
                try:
                    st = p.stat()
                except OSError:
                    continue
                firma = (st.st_size, st.st_mtime_ns)
                prec = visti.get(p)
                if prec is None or prec[0] != firma:
                    visti[p] = (firma, adesso)
                    continue
                if adesso - prec[1] < DEBOUNCE_SECONDI:
                    continue
                if self.conv.e_elaborato(p):
                    continue
                if not self._apribile(p):
                    visti[p] = (firma, adesso)
                    continue
                self.conv.converti_file(p)
            for p in list(visti):
                if p not in presenti:
                    del visti[p]

    @staticmethod
    def _apribile(p: Path) -> bool:
        try:
            with open(p, "rb"):
                return True
        except OSError:
            return False
