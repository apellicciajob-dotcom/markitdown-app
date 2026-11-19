# MarkItDown App

App desktop per Windows che converte PDF, Word, Excel, PowerPoint, EPUB, testo, log e codice in **Markdown**, basata su [MarkItDown](https://github.com/microsoft/markitdown) e [customtkinter](https://github.com/TomSchimansky/CustomTkinter).

## Funzioni

- **Drag & Drop** dei file nella finestra (o selezione multipla con il file picker)
- **Incolla dagli appunti** (`Ctrl+V`): il testo diventa un `.log` con timestamp in *ingresso* ed è subito convertito in `.md`
- **Watch** della cartella di ingresso con debounce su dimensione/mtime: i file appena creati sono sempre convertiti
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
