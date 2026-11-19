# Pubblicazione su Microsoft Store - passaggi finali

Prerequisito: account sviluppatore su [Partner Center](https://partner.microsoft.com/dashboard) (una tantum).

1. **Prenota il nome dell'app**
   Partner Center → *Apps and games* → *New product* → *MSIX or PWA app* → riserva il nome (es. "ApexCore - MarkItDown Avanzato").

2. **Copia l'identità del prodotto**
   *Product management* → *Product identity*: annota
   - `Package/Identity/Name` (es. `12345Nome.MarkItDownApp`)
   - `Package/Identity/Publisher` (es. `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)
   - `Package/Properties/PublisherDisplayName`

3. **Sostituisci Identity Name / Publisher e ricompila**
   Senza modificare a mano il manifest, passa i valori allo script (non usare `-SelfSignTest`):
   ```powershell
   .\build_msix.ps1 -IdentityName "12345Nome.MarkItDownApp" `
                    -Publisher "CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" `
                    -PublisherDisplayName "Il tuo nome editore" `
                    -Version 1.0.1.0
   ```
   Output: `dist\MarkItDownApp.msix` (non firmato: lo Store lo firma). A ogni nuova submission incrementa `-Version` (4° numero sempre `0`).

4. **Carica il pacchetto**
   Partner Center → *Start submission* → *Packages* → trascina `dist\MarkItDownApp.msix`.
   Compila *Store listings* (descrizione, screenshot ≥1, logo 1:1 300×300 se richiesto), *Properties*, *Age ratings*, *Pricing*.
   Poiché l'app usa `runFullTrust`, nella sezione *Notes for certification* spiega che è un'app desktop Win32 che salva i file in Documenti dell'utente.

5. **Invia per la certificazione** (*Submit to the Store*) e attendi l'esito.
