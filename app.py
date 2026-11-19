# -*- coding: utf-8 -*-
"""
MarkItDown App - interfaccia grafica (stile Windows 11) basata su customtkinter.

Avvio:  python app.py
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk

from converter import (ESTENSIONI_SUPPORTATE, Convertitore, Risultato, Settings,
                       Watcher, chiudi_logging, configura_logging)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:  # noqa: BLE001 - fallback al file picker
    HAS_DND = False

APP_TITLE = "MarkItDown App"
ACCENT = ("#0067C0", "#4CC2FF")        # blu Windows 11 (chiaro, scuro)
CARD = ("#FFFFFF", "#2B2B2B")
BG = ("#F3F3F3", "#202020")
MUTED = ("#605E5C", "#A19F9D")
OK_COL = ("#0F7B0F", "#6CCB5F")
ERR_COL = ("#C42B1C", "#FF99A4")
FONT = "Segoe UI"
MAX_PREVIEW = 300_000


def risorsa(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


_BaseWindow = (type("_Base", (ctk.CTk, TkinterDnD.DnDWrapper), {})
               if HAS_DND else ctk.CTk)


class App(_BaseWindow):
    def __init__(self) -> None:
        self.settings = Settings()
        ctk.set_appearance_mode(self.settings.tema)
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.dnd_ok = False
        if HAS_DND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_ok = True
            except Exception as exc:  # noqa: BLE001
                logging.warning("Drag & Drop non disponibile: %s", exc)

        configura_logging(self.settings.log_file)
        self.coda: "queue.Queue[Risultato]" = queue.Queue()
        self.conv = Convertitore(self.settings, on_risultato=self.coda.put)
        self.watcher = Watcher(self.conv)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="conv")
        self.cronologia: list[Risultato] = []
        self.ultimo_md: Path | None = None   # file mostrato in anteprima
        self._firma_files: tuple = ()
        self._tick = 0
        self.n_ok = self.n_err = 0

        self.title(APP_TITLE)
        self.geometry("1380x760")
        self.minsize(1180, 620)
        self.configure(fg_color=BG)
        self._icona()
        self._costruisci()
        self._collega_eventi()
        self._ridisegna_files()

        try:
            self.conv.assicura_cartelle()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Impossibile creare le cartelle dati:\n{exc}")
        if self.settings.watch_automatico:
            self._avvia_watch()
        self._aggiorna_watch_ui()
        self.after(150, self._svuota_coda)
        self.protocol("WM_DELETE_WINDOW", self._chiudi)

    # ------------------------------------------------------------------ UI
    def _icona(self) -> None:
        ico = risorsa("assets/icon.ico")
        if ico.exists():
            try:
                self.after(250, lambda: self.iconbitmap(str(ico)))
            except tk.TclError:
                pass

    def _card(self, parent, **kw) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=("#E5E5E5", "#3A3A3A"), **kw)

    def _costruisci(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- colonna sinistra: azioni ---
        sx = ctk.CTkFrame(self, fg_color="transparent", width=290)
        sx.grid(row=0, column=0, sticky="ns", padx=(16, 8), pady=16)
        sx.grid_propagate(False)
        sx.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sx, text="MarkItDown", font=(FONT, 26, "bold")).grid(
            row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(sx, text="Converti tutto in Markdown", font=(FONT, 13),
                     text_color=MUTED).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 12))

        self.drop = ctk.CTkFrame(sx, fg_color=CARD, corner_radius=14, height=190,
                                 border_width=2, border_color=ACCENT)
        self.drop.grid(row=2, column=0, sticky="ew")
        self.drop.grid_propagate(False)
        self.drop.grid_columnconfigure(0, weight=1)
        self.drop.grid_rowconfigure((0, 3), weight=1)
        ctk.CTkLabel(self.drop, text="⇩", font=(FONT, 40), text_color=ACCENT).grid(row=1, column=0)
        testo = ("Trascina qui i file" if self.dnd_ok
                 else "Seleziona i file da convertire")
        self.lbl_drop = ctk.CTkLabel(self.drop, text=testo, font=(FONT, 15, "bold"))
        self.lbl_drop.grid(row=2, column=0)
        ctk.CTkLabel(self.drop, text="PDF · Word · Excel · PowerPoint · EPUB · testo · codice",
                     font=(FONT, 11), text_color=MUTED, wraplength=250).grid(
            row=3, column=0, sticky="n", pady=(2, 0))

        def btn(row, text, cmd, primary=False):
            b = ctk.CTkButton(
                sx, text=text, command=cmd, height=40, corner_radius=8,
                font=(FONT, 14),
                fg_color=ACCENT if primary else ("#E6E6E6", "#383838"),
                hover_color=("#005A9E", "#6CD0FF") if primary else ("#D6D6D6", "#454545"),
                text_color=("#FFFFFF", "#000000") if primary else ("#1A1A1A", "#F2F2F2"))
            b.grid(row=row, column=0, sticky="ew", pady=(10, 0))
            return b

        btn(3, "📂  Seleziona file…", self.scegli_file, primary=True)
        btn(4, "📋  Incolla dagli appunti  (Ctrl+V)", self.incolla)
        self.btn_watch = btn(5, "", self.toggle_watch)
        btn(6, "📁  Apri cartella conversioni", lambda: self._apri(self.settings.conversioni))
        btn(7, "📥  Apri cartella ingresso", lambda: self._apri(self.settings.ingresso))

        sx.grid_rowconfigure(8, weight=1)
        self.lbl_stato = ctk.CTkLabel(sx, text="", font=(FONT, 12), text_color=MUTED,
                                      justify="left", anchor="sw", wraplength=260)
        self.lbl_stato.grid(row=8, column=0, sticky="sew", padx=4)

        # --- colonna destra: schede ---
        self.tabs = ctk.CTkTabview(self, fg_color=CARD, corner_radius=12,
                                   segmented_button_selected_color=ACCENT)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=8, pady=16)
        t_prev = self.tabs.add("Anteprima")
        t_cron = self.tabs.add("Cronologia")
        t_set = self.tabs.add("Impostazioni")

        # --- colonna destra: file in conversioni/ ---
        dx = self._card(self, width=330)
        dx.grid(row=0, column=2, sticky="ns", padx=(8, 16), pady=16)
        dx.grid_propagate(False)
        dx.grid_columnconfigure(0, weight=1)
        dx.grid_rowconfigure(1, weight=1)
        testa = ctk.CTkFrame(dx, fg_color="transparent")
        testa.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        testa.grid_columnconfigure(0, weight=1)
        self.lbl_nfile = ctk.CTkLabel(testa, text="Conversioni", font=(FONT, 16, "bold"),
                                      anchor="w")
        self.lbl_nfile.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(testa, text="↻", width=32, height=32, font=(FONT, 16),
                      fg_color=("#E6E6E6", "#383838"), hover_color=("#D6D6D6", "#454545"),
                      text_color=("#1A1A1A", "#F2F2F2"),
                      command=self._ridisegna_files).grid(row=0, column=1)
        self.lista_md = ctk.CTkScrollableFrame(dx, fg_color="transparent")
        self.lista_md.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 8))
        self.lista_md.grid_columnconfigure(0, weight=1)

        # Anteprima
        t_prev.grid_columnconfigure(0, weight=1)
        t_prev.grid_rowconfigure(1, weight=1)
        barra = ctk.CTkFrame(t_prev, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        barra.grid_columnconfigure(0, weight=1)
        self.lbl_file = ctk.CTkLabel(barra, text="Nessuna conversione", font=(FONT, 13, "bold"),
                                     anchor="w")
        self.lbl_file.grid(row=0, column=0, sticky="ew")
        self.btn_copia = ctk.CTkButton(barra, text="Copia Markdown", width=140, height=32,
                                       command=self.copia_md, fg_color=ACCENT,
                                       text_color=("#FFFFFF", "#000000"),
                                       hover_color=("#005A9E", "#6CD0FF"))
        self.btn_copia.grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(barra, text="Apri file", width=90, height=32,
                      fg_color=("#E6E6E6", "#383838"), hover_color=("#D6D6D6", "#454545"),
                      text_color=("#1A1A1A", "#F2F2F2"),
                      command=self.apri_ultimo).grid(row=0, column=2, padx=(8, 0))
        ctk.CTkButton(barra, text="Svuota", width=80, height=32,
                      fg_color=("#E6E6E6", "#383838"), hover_color=("#D6D6D6", "#454545"),
                      text_color=("#1A1A1A", "#F2F2F2"),
                      command=self.svuota_anteprima).grid(row=0, column=3, padx=(8, 0))
        self.preview = ctk.CTkTextbox(t_prev, font=("Cascadia Mono", 13), wrap="word",
                                      fg_color=("#FAFAFA", "#1F1F1F"), corner_radius=8)
        self.preview.grid(row=1, column=0, sticky="nsew")
        tb = self.preview._textbox
        tb.tag_config("h", font=("Segoe UI", 15, "bold"), foreground="#0067C0")
        tb.tag_config("code", foreground="#8A6D00")
        self._set_preview("L'anteprima del Markdown generato apparira' qui.\n\n"
                          "Trascina un file, incolla del testo o avvia il Watch.")

        # Cronologia
        t_cron.grid_columnconfigure(0, weight=1)
        t_cron.grid_rowconfigure(0, weight=1)
        self.lista = ctk.CTkScrollableFrame(t_cron, fg_color="transparent")
        self.lista.grid(row=0, column=0, sticky="nsew")
        self.lista.grid_columnconfigure(0, weight=1)
        self.lbl_vuoto = ctk.CTkLabel(self.lista, text="Ancora nessuna conversione.",
                                      text_color=MUTED)
        self.lbl_vuoto.grid(row=0, column=0, pady=20)

        # Impostazioni
        t_set.grid_columnconfigure(1, weight=1)
        self.var_ing = ctk.StringVar(value=str(self.settings.ingresso))
        self.var_conv = ctk.StringVar(value=str(self.settings.conversioni))
        self._riga_cartella(t_set, 0, "Cartella ingresso", self.var_ing, "ingresso")
        self._riga_cartella(t_set, 1, "Cartella conversioni", self.var_conv, "conversioni")
        ctk.CTkLabel(t_set, text="Cartella log").grid(row=2, column=0, sticky="w", pady=8, padx=4)
        ctk.CTkLabel(t_set, text=str(self.settings.log_dir), text_color=MUTED,
                     anchor="w").grid(row=2, column=1, sticky="ew", padx=8)
        ctk.CTkButton(t_set, text="Apri", width=80,
                      command=lambda: self._apri(self.settings.log_dir),
                      fg_color=("#E6E6E6", "#383838"), text_color=("#1A1A1A", "#F2F2F2"),
                      hover_color=("#D6D6D6", "#454545")).grid(row=2, column=2, padx=4)
        ctk.CTkLabel(t_set, text="Tema").grid(row=3, column=0, sticky="w", pady=8, padx=4)
        nomi = {"Light": "Chiaro", "Dark": "Scuro", "System": "Sistema"}
        self._tema_inv = {v: k for k, v in nomi.items()}
        self.menu_tema = ctk.CTkSegmentedButton(
            t_set, values=list(nomi.values()), command=self._cambia_tema,
            selected_color=ACCENT, selected_hover_color=ACCENT)
        self.menu_tema.set(nomi[self.settings.tema])
        self.menu_tema.grid(row=3, column=1, sticky="w", padx=8)
        self.var_auto = ctk.BooleanVar(value=self.settings.watch_automatico)
        ctk.CTkSwitch(t_set, text="Avvia il Watch all'apertura dell'app",
                      variable=self.var_auto, command=self._salva_auto,
                      progress_color=ACCENT).grid(row=4, column=0, columnspan=3,
                                                  sticky="w", pady=12, padx=4)

    def _riga_cartella(self, parent, riga, etichetta, var, attr) -> None:
        ctk.CTkLabel(parent, text=etichetta).grid(row=riga, column=0, sticky="w", pady=8, padx=4)
        ctk.CTkEntry(parent, textvariable=var, state="readonly").grid(
            row=riga, column=1, sticky="ew", padx=8)
        ctk.CTkButton(parent, text="Cambia…", width=80,
                      command=lambda: self._cambia_cartella(attr, var),
                      fg_color=("#E6E6E6", "#383838"), text_color=("#1A1A1A", "#F2F2F2"),
                      hover_color=("#D6D6D6", "#454545")).grid(row=riga, column=2, padx=4)

    def _collega_eventi(self) -> None:
        self.bind_all("<Control-v>", self._ctrl_v)
        self.bind_all("<Control-V>", self._ctrl_v)
        if self.dnd_ok:
            for w in (self, self.drop):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
                w.dnd_bind("<<DropEnter>>", lambda e: self.drop.configure(
                    fg_color=("#E8F2FB", "#1E3447")))
                w.dnd_bind("<<DropLeave>>", lambda e: self.drop.configure(fg_color=CARD))
        self.drop.bind("<Button-1>", lambda e: self.scegli_file())
        for c in self.drop.winfo_children():
            c.bind("<Button-1>", lambda e: self.scegli_file())

    # ------------------------------------------------------------- azioni
    def _on_drop(self, event) -> None:
        self.drop.configure(fg_color=CARD)
        self._importa(self.tk.splitlist(event.data))

    def scegli_file(self) -> None:
        tipi = " ".join("*" + e for e in sorted(ESTENSIONI_SUPPORTATE))
        files = filedialog.askopenfilenames(
            title="Seleziona i file da convertire",
            filetypes=[("File supportati", tipi), ("Tutti i file", "*.*")])
        if files:
            self._importa(files)

    def _importa(self, percorsi) -> None:
        n = 0
        for p in percorsi:
            p = Path(p)
            if p.is_dir():
                for f in sorted(x for x in p.iterdir() if x.is_file()):
                    self.pool.submit(self.conv.importa_e_converti, f)
                    n += 1
            elif p.is_file():
                self.pool.submit(self.conv.importa_e_converti, p)
                n += 1
        if n:
            self._stato(f"Conversione di {n} file in corso…")

    def _ctrl_v(self, event=None) -> str | None:
        # Non intercettare Ctrl+V dentro campi di testo editabili (entry)
        w = self.focus_get()
        if isinstance(w, tk.Entry) and str(w.cget("state")) == "normal":
            return None
        self.incolla()
        return "break"

    def incolla(self) -> None:
        try:
            testo = self.clipboard_get()
        except tk.TclError:
            testo = ""
        if not testo.strip():
            self._stato("Gli appunti non contengono testo.")
            return
        self._stato("Conversione del testo incollato…")
        self.pool.submit(self.conv.converti_testo_appunti, testo)

    def copia_md(self) -> None:
        testo = self.preview.get("1.0", "end-1c")
        if self.ultimo_md and self.ultimo_md.exists():
            try:
                testo = self.ultimo_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        if not self.ultimo_md:
            return
        self.clipboard_clear()
        self.clipboard_append(testo)
        self.update()
        self._stato("Markdown copiato negli appunti.")

    def apri_ultimo(self) -> None:
        if self.ultimo_md and self.ultimo_md.exists():
            self._apri(self.ultimo_md)

    def _apri(self, percorso: Path) -> None:
        try:
            Path(percorso).parent.mkdir(parents=True, exist_ok=True) \
                if not Path(percorso).suffix else None
            os.startfile(str(percorso))  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Impossibile aprire:\n{percorso}\n\n{exc}")

    # -------------------------------------------------------------- watch
    def _avvia_watch(self) -> None:
        try:
            self.watcher.avvia()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Watch non avviabile:\n{exc}")

    def toggle_watch(self) -> None:
        if self.watcher.attivo:
            self.watcher.ferma()
        else:
            self._avvia_watch()
        self._aggiorna_watch_ui()

    def _aggiorna_watch_ui(self) -> None:
        if self.watcher.attivo:
            self.btn_watch.configure(text="⏸  Pausa Watch  (attivo)")
            self._stato("Watch attivo: i file messi in ingresso vengono convertiti.")
        else:
            self.btn_watch.configure(text="▶  Avvia Watch  (in pausa)")
            self._stato("Watch in pausa.")

    # ------------------------------------------------------- impostazioni
    def _cambia_cartella(self, attr: str, var: ctk.StringVar) -> None:
        nuova = filedialog.askdirectory(title="Scegli cartella",
                                        initialdir=str(getattr(self.settings, attr)))
        if not nuova:
            return
        riattiva = self.watcher.attivo
        if riattiva:
            self.watcher.ferma()
        setattr(self.settings, attr, Path(nuova))
        self.settings.save()
        var.set(str(nuova))
        try:
            self.conv.assicura_cartelle()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
        if riattiva:
            self._avvia_watch()
        self._aggiorna_watch_ui()

    def _cambia_tema(self, valore: str) -> None:
        self.settings.tema = self._tema_inv[valore]
        ctk.set_appearance_mode(self.settings.tema)
        self.settings.save()

    def _salva_auto(self) -> None:
        self.settings.watch_automatico = bool(self.var_auto.get())
        self.settings.save()

    # ---------------------------------------------------------- risultati
    def _svuota_coda(self) -> None:
        try:
            while True:
                self._mostra(self.coda.get_nowait())
        except queue.Empty:
            pass
        self._tick += 1
        if self._tick % 13 == 0:   # ~2 s: intercetta cambi esterni alla cartella
            if tuple((p.name, m) for p, m in self._elenco_md()) != self._firma_files:
                self._ridisegna_files()
        self.after(150, self._svuota_coda)

    def _mostra(self, r: Risultato) -> None:
        self.cronologia.insert(0, r)
        del self.cronologia[200:]
        if r.ok:
            self.n_ok += 1
            self._anteprima(r)
        else:
            self.n_err += 1
        self._stato(f"{'✔' if r.ok else '✖'} {r.sorgente.name}: {r.messaggio}")
        self._ridisegna_cronologia()
        if not r.ok:
            self._ridisegna_files()   # se ok lo fa gia' _mostra_md

    def _anteprima(self, r: Risultato) -> None:
        self._mostra_md(r.destinazione, f"{r.sorgente.name}  →  {r.destinazione.name}")

    def _mostra_md(self, percorso: Path, titolo: str | None = None) -> None:
        self.ultimo_md = percorso
        self.lbl_file.configure(text=titolo or percorso.name)
        try:
            testo = percorso.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            testo = f"(Impossibile leggere l'anteprima: {exc})"
        if len(testo) > MAX_PREVIEW:
            testo = testo[:MAX_PREVIEW] + "\n\n… (anteprima troncata, apri il file per il testo completo)"
        self._set_preview(testo)
        self.tabs.set("Anteprima")
        self._ridisegna_files()

    def svuota_anteprima(self) -> None:
        """Pulisce solo l'anteprima: i file su disco restano intatti."""
        self.ultimo_md = None
        self.lbl_file.configure(text="Nessuna conversione")
        self._set_preview("")
        self._ridisegna_files()

    # ----------------------------------------------- lista conversioni/
    def _elenco_md(self) -> list[tuple[Path, float]]:
        try:
            voci = [(p, p.stat().st_mtime) for p in self.settings.conversioni.glob("*.md")
                    if p.is_file()]
        except OSError:
            return []
        voci.sort(key=lambda v: v[1], reverse=True)
        return voci

    def _ridisegna_files(self) -> None:
        voci = self._elenco_md()
        self._firma_files = tuple((p.name, m) for p, m in voci)
        for w in self.lista_md.winfo_children():
            w.destroy()
        self.lbl_nfile.configure(text=f"Conversioni ({len(voci)})")
        if not voci:
            ctk.CTkLabel(self.lista_md, text="Nessun file .md.", text_color=MUTED).grid(
                row=0, column=0, pady=20)
            return
        for i, (p, m) in enumerate(voci[:300]):
            sel = self.ultimo_md is not None and p == self.ultimo_md
            riga = ctk.CTkFrame(
                self.lista_md, corner_radius=8,
                fg_color=("#E8F2FB", "#1E3447") if sel else ("#F6F6F6", "#262626"),
                border_width=2 if (sel or i == 0) else 0,
                border_color=ACCENT if sel else ("#0F7B0F", "#6CCB5F"))
            riga.grid(row=i, column=0, sticky="ew", pady=3, padx=2)
            riga.grid_columnconfigure(0, weight=1)
            nome = ctk.CTkLabel(riga, text=p.name, anchor="w", font=(FONT, 12, "bold"),
                                cursor="hand2")
            nome.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=(6, 0))
            info = time.strftime("%d/%m %H:%M", time.localtime(m))
            if i == 0:
                info = "● Ultimo  ·  " + info
            sotto = ctk.CTkLabel(riga, text=info, anchor="w", font=(FONT, 10),
                                 text_color=OK_COL if i == 0 else MUTED)
            sotto.grid(row=1, column=0, sticky="ew", padx=(8, 4), pady=(0, 6))
            for w in (riga, nome, sotto):
                w.bind("<Button-1>", lambda e, x=p: self._mostra_md(x))
            b_copia = ctk.CTkButton(riga, text="📋", width=32, height=30,
                                    fg_color=("#E6E6E6", "#383838"),
                                    hover_color=("#D6D6D6", "#454545"),
                                    text_color=("#1A1A1A", "#F2F2F2"))
            b_copia.configure(command=lambda x=p, b=b_copia: self.copia_file(x, b))
            b_copia.grid(row=0, column=1, rowspan=2, padx=2, pady=4)
            ctk.CTkButton(riga, text="🗑️", width=32, height=30,
                          fg_color=("#E6E6E6", "#383838"),
                          hover_color=("#F4B6B0", "#7A2A25"),
                          text_color=("#1A1A1A", "#F2F2F2"),
                          command=lambda x=p: self.elimina_file(x)).grid(
                row=0, column=2, rowspan=2, padx=(2, 6), pady=4)

    def copia_file(self, p: Path, bottone=None) -> bool:
        try:
            testo = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._stato(f"✖ Lettura fallita: {exc}")
            return False
        self.clipboard_clear()
        self.clipboard_append(testo)
        self.update()
        self._stato(f"Copiato negli appunti: {p.name}")
        if bottone is not None:
            bottone.configure(text="✔")
            self.after(1200, lambda: bottone.winfo_exists() and bottone.configure(text="📋"))
        return True

    def elimina_file(self, p: Path, conferma: bool = True) -> bool:
        if conferma and not messagebox.askyesno(
                APP_TITLE, f"Eliminare definitivamente\n{p.name}\ndalla cartella conversioni?"):
            return False
        try:
            p.unlink()
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Impossibile eliminare:\n{exc}")
            return False
        logging.info("Eliminato %s", p)
        if self.ultimo_md == p:
            self.svuota_anteprima()
        else:
            self._ridisegna_files()
        self._stato(f"Eliminato: {p.name}")
        return True

    def _set_preview(self, testo: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", testo)
        tb = self.preview._textbox
        in_code = False
        for i, riga in enumerate(testo.split("\n"), start=1):
            if riga.lstrip().startswith("```"):
                in_code = not in_code
                tb.tag_add("code", f"{i}.0", f"{i}.end")
            elif in_code:
                tb.tag_add("code", f"{i}.0", f"{i}.end")
            elif riga.startswith("#"):
                tb.tag_add("h", f"{i}.0", f"{i}.end")
            if i > 5000:
                break
        self.preview.configure(state="disabled")

    def _ridisegna_cronologia(self) -> None:
        for w in self.lista.winfo_children():
            w.destroy()
        for i, r in enumerate(self.cronologia[:60]):
            riga = ctk.CTkFrame(self.lista, fg_color=("#F6F6F6", "#262626"), corner_radius=8)
            riga.grid(row=i, column=0, sticky="ew", pady=3)
            riga.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(riga, text="✔" if r.ok else "✖",
                         text_color=OK_COL if r.ok else ERR_COL,
                         font=(FONT, 16, "bold"), width=30).grid(row=0, column=0, rowspan=2)
            ctk.CTkLabel(riga, text=r.sorgente.name, anchor="w", font=(FONT, 13, "bold")).grid(
                row=0, column=1, sticky="ew", pady=(6, 0))
            dett = (f"{time.strftime('%H:%M:%S', time.localtime(r.quando))}  ·  "
                    + (f"→ {r.destinazione.name}" if r.ok else r.messaggio))
            ctk.CTkLabel(riga, text=dett, anchor="w", text_color=MUTED, font=(FONT, 11)).grid(
                row=1, column=1, sticky="ew", pady=(0, 6))
            if r.ok:
                ctk.CTkButton(riga, text="Anteprima", width=90, height=28,
                              command=lambda x=r: self._anteprima(x),
                              fg_color=ACCENT, text_color=("#FFFFFF", "#000000"),
                              hover_color=("#005A9E", "#6CD0FF")).grid(
                    row=0, column=2, rowspan=2, padx=8)

    def _stato(self, msg: str) -> None:
        self.lbl_stato.configure(
            text=f"{msg}\n\nConvertiti: {self.n_ok}   Errori: {self.n_err}")

    def _chiudi(self) -> None:
        try:
            self.watcher.ferma()
            self.pool.shutdown(wait=True, cancel_futures=True)
        finally:
            chiudi_logging()
            self.destroy()


def main() -> None:
    if "--smoke-test" in sys.argv:
        from smoke_test import run
        i = sys.argv.index("--smoke-test")
        out = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else Path.cwd() / "smoke_out"
        sys.exit(run(out))
    App().mainloop()


if __name__ == "__main__":
    main()
