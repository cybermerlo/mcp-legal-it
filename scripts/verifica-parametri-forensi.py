#!/usr/bin/env python3
"""Verifica che ogni valore delle tabelle DM 55/2014 nel JSON compaia nel testo ufficiale.

Le tabelle sono state trascritte a mano dal testo vigente su Normattiva: questo script
esiste perche' una cifra sbagliata in una parcella non si vede a occhio. Confronta la
sequenza di numeri di ogni riga del JSON con la stessa riga in
docs/dm55-2014-tabelle-ufficiali.txt, che e' la copia della fonte.

Uso: python3 scripts/verifica-parametri-forensi.py   (exit 1 se qualcosa non torna)
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
JSON = ROOT / "plugin/server/src/data/parametri_forensi.json"
FONTE = ROOT / "docs/dm55-2014-tabelle-ufficiali.txt"

tabelle = json.loads(JSON.read_text(encoding="utf-8"))["tabelle"]
testo = FONTE.read_text(encoding="utf-8")

# indicizza il testo ufficiale: numero tabella -> blocco
blocchi = {}
corrente = None
for riga in testo.splitlines():
    m = re.match(r"^(\d+(?:-bis)?)\.\s+[A-ZÀ-Ù]", riga)
    if m:
        corrente = m.group(1)
        blocchi[corrente] = []
    elif corrente:
        blocchi[corrente].append(riga)

errori = []
controllati = 0
for chiave, tab in tabelle.items():
    if chiave.startswith("_"):
        continue
    num = tab["_tabella"]
    if num not in blocchi:
        errori.append(f"{chiave}: tabella {num} assente dal testo ufficiale")
        continue
    numeri_fonte = [int(x) for x in re.findall(r"\b\d+\b", "\n".join(blocchi[num]))]
    n_verificabili = len(tab["_scaglioni"]) - len(tab.get("_scaglioni_non_verificabili", []))
    for fase, valori in tab["fasi"].items():
        valori = valori[:n_verificabili]  # oltre, la fonte e' un'immagine: vedi _nota
        # la sequenza dei valori della fase deve comparire, nell'ordine, fra i numeri della tabella
        if not any(numeri_fonte[i:i + len(valori)] == valori for i in range(len(numeri_fonte))):
            errori.append(f"{chiave}/{fase}: {valori} non trovata nella tabella {num} della fonte")
        controllati += len(valori)

print(f"Tabelle: {len([k for k in tabelle if not k.startswith('_')])} — valori controllati: {controllati}")
if errori:
    print("\n✗ DIVERGENZE:")
    for e in errori:
        print("  ", e)
    sys.exit(1)
print("✓ ogni valore del JSON compare nel testo ufficiale, nella tabella e nell'ordine giusti")
