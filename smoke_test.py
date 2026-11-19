# -*- coding: utf-8 -*-
"""Smoke test headless: MarkItDownApp.exe --smoke-test <cartella_output>

Genera al volo PDF, DOCX, XLSX, PPTX e LOG reali, li converte con il core
dell'app (quindi con le librerie incluse nell'exe) e scrive il risultato in
<cartella_output>/smoke_result.txt. Codice di uscita 0 = tutto ok.
I file di prova restano in <cartella_output>: li elimina chi chiama il test.
"""
from __future__ import annotations

import sys
import traceback
import zipfile
from pathlib import Path

from converter import Convertitore, Settings, chiudi_logging, configura_logging

MARCATORE = "ZEBRA42"


def crea_pdf(p: Path) -> None:
    flusso = f"BT /F1 18 Tf 72 720 Td ({MARCATORE} pdf prova) Tj ET".encode()
    oggetti = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(flusso) + flusso + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(oggetti, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(oggetti) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(oggetti) + 1, xref)
    p.write_bytes(bytes(out))


def crea_docx(p: Path) -> None:
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
          'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.'
          'openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="'
          'application/xml"/><Override PartName="/word/document.xml" ContentType="application/'
          'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>')
    doc = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.'
           'openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
           f'{MARCATORE} docx prova</w:t></w:r></w:p></w:body></w:document>')
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


def crea_xlsx(p: Path) -> None:
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.append(["col", MARCATORE + " xlsx"])
    wb.save(p)


def crea_pptx(p: Path) -> None:
    from pptx import Presentation
    pr = Presentation()
    s = pr.slides.add_slide(pr.slide_layouts[5])
    s.shapes.title.text = MARCATORE + " pptx"
    pr.save(p)


def run(out: Path) -> int:
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    righe, ok_tot = [], True
    try:
        s = Settings(config_dir=out / "cfg")
        s.ingresso, s.conversioni = out / "ingresso", out / "conversioni"
        configura_logging(s.log_file)
        c = Convertitore(s)
        c.assicura_cartelle()
        src = out / "sorgenti"
        src.mkdir(exist_ok=True)
        casi = [("prova.pdf", crea_pdf), ("prova.docx", crea_docx),
                ("prova.xlsx", crea_xlsx), ("prova.pptx", crea_pptx),
                ("prova.log", lambda p: p.write_text(MARCATORE + " log\nERROR x\n", "utf-8"))]
        for nome, crea in casi:
            try:
                crea(src / nome)
                r = c.importa_e_converti(src / nome)
                good = r.ok and MARCATORE in r.destinazione.read_text("utf-8")
                righe.append(f"{'OK  ' if good else 'FAIL'} {nome}: {r.messaggio}")
            except Exception:  # noqa: BLE001
                good = False
                righe.append(f"FAIL {nome}:\n{traceback.format_exc()}")
            ok_tot &= good
        n_log = s.log_file.read_text("utf-8").count("[INFO] OK")
        righe.append(f"log: {n_log} conversioni registrate in {s.log_file}")
        ok_tot &= n_log >= len(casi)
    except Exception:  # noqa: BLE001
        ok_tot = False
        righe.append(traceback.format_exc())
    finally:
        chiudi_logging()
    righe.append("RISULTATO: " + ("PASS" if ok_tot else "FAIL"))
    (out / "smoke_result.txt").write_text("\n".join(righe), encoding="utf-8")
    return 0 if ok_tot else 1


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("smoke_out")))
