# ApexCore - MarkItDown Avanzato

App desktop per Windows che converte PDF, Word, Excel, PowerPoint, EPUB, testo, log e codice in **Markdown**, basata su [MarkItDown](https://github.com/microsoft/markitdown) e [customtkinter](https://github.com/TomSchimansky/CustomTkinter).

## Download e installazione

1. Scarica **[MarkItDownApp-v1.2.0-win64.zip](https://github.com/apellicciajob-dotcom/markitdown-app/releases/download/v1.2.0/MarkItDownApp-v1.2.0-win64.zip)** (circa 117 MB) dalla pagina [Releases](https://github.com/apellicciajob-dotcom/markitdown-app/releases/latest). Requisiti: Windows 10/11 a 64 bit; non serve installare Python né altro.
2. Tasto destro sullo zip → **Estrai tutto…** in una cartella qualsiasi.
3. Apri `MarkItDownApp\MarkItDownApp.exe`. Non spostare il solo `.exe`: deve restare nella sua cartella insieme a `_internal`. Per un'icona sul Desktop: tasto destro → *Invia a* → *Desktop (crea collegamento)*.

Se Windows SmartScreen mostra "Windows ha protetto il PC" (l'app non e' ancora firmata): **Ulteriori informazioni → Esegui comunque**.

## Uso rapido

- **Incolla dagli appunti (`Ctrl+V`)**: il testo diventa `appunti_AAAAMMGG_HHMMSS` e viene convertito subito; la riga e' evidenziata in giallo ocra.
- **Trascina i file** nella zona tratteggiata oppure usa **Seleziona file…**.
- **Avvia/Pausa Watch**: converte automaticamente i file messi nella cartella *ingresso*.
- **Anteprima** al centro (*Copia Markdown*, *Svuota*); a destra la lista **Conversioni** con *Apri*, copia ed elimina per ogni file.
- Cartelle, tema e avvio automatico del Watch si cambiano da **Impostazioni**.
- Disinstallazione: elimina la cartella `MarkItDownApp` (e, se vuoi, i dati in `Documenti\MarkItDownApp` e `%LOCALAPPDATA%\MarkItDownApp`).

## Funzioni

- **Drag & Drop** dei file nella finestra (o selezione multipla con il file picker)
- **Incolla dagli appunti** (`Ctrl+V`): il testo diventa un `.log` con timestamp in *ingresso* ed è subito convertito in `.md`
- **Watch** della cartella di ingresso con debounce su dimensione/mtime: i file appena creati sono sempre convertiti
- Pulsante **Incolla dagli appunti** in primo piano, evidenziazione giallo ocra del testo appena incollato e toast di conferma
- **Lista live** della cartella conversioni con azioni Apri / Copia / Elimina per riga
- **Anteprima Markdown**, cronologia, *Copia Markdown*, apertura cartelle, tema Chiaro/Scuro/Sistema
- Nessuna sovrascrittura: se esiste già `nome.md` si crea `nome_1.md`, `nome_2.md`, …

| Tipo | Gestione |
|---|---|
| PDF, DOCX/DOC, XLSX/XLS, PPTX/PPT, EPUB, HTM, RTF | MarkItDown |
| TXT, LOG, JSON, CSV, TSV, SQL | lettura UTF-8 |
| PY, JS, PS1, BAT, SH, HTML, CSS, XML, YAML, INI, CFG, TOML | UTF-8 + code fence |
| MD | copia |

## Dove vengono salvati i dati

Compatibile con MSIX (la cartella dell'exe è in sola lettura):

| Cosa | Percorso (modificabile dalle Impostazioni, tranne log/config) |
|---|---|
| Ingresso | `Documenti\MarkItDownApp\ingresso` |
| Conversioni | `Documenti\MarkItDownApp\conversioni` |
| Log + `settings.json` | `%LOCALAPPDATA%\MarkItDownApp` |

## Esecuzione da sorgente

```powershell
& "$env:USERPROFILE\venvs\markitdown\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:USERPROFILE\venvs\markitdown\Scripts\python.exe" app.py
```

## Build dell'eseguibile (.exe)

```powershell
.\build_exe.ps1            # cartella dist\MarkItDownApp\MarkItDownApp.exe
.\build_exe.ps1 -OneFile   # singolo dist\MarkItDownApp.exe
```

Gli asset (`assets\icon.ico` e i PNG dello Store) sono generati da `make_assets.py` se mancanti.

## Pacchetto MSIX e Microsoft Store

1. Installa il [Windows SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) (serve `makeappx.exe`).
2. Registra l'app in [Partner Center](https://partner.microsoft.com/dashboard) e copia da *Identità del prodotto* `Package/Identity/Name`, `Publisher` e `PublisherDisplayName` dentro `AppxManifest.xml`.
3. Genera il pacchetto:
   ```powershell
   .\build_msix.ps1 -Version 1.0.0.0
   ```
   Output: `dist\MarkItDownApp.msix`. Per un test locale firmato aggiungi `-PfxPath cert.pfx -PfxPassword ...`.
4. Carica il `.msix` su Partner Center. Passaggi dettagliati in [STORE_SUBMISSION.md](STORE_SUBMISSION.md); test locale: `.\build_msix.ps1 -SelfSignTest`.

## Pubblicazione su GitHub

```powershell
git init
git add .
git commit -m "MarkItDown App"
gh repo create markitdown-app --public --source . --push
```

Allega l'`.exe`/`.msix` come asset di una *Release* (non committare `dist/`).

## Licenza

MIT - vedi [LICENSE](LICENSE).
