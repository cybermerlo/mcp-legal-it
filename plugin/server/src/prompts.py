"""MCP Prompts — 2 workflow guidati per la giurisprudenza di Cassazione."""

from src.server import mcp


@mcp.prompt(
    description="Analisi giurisprudenziale strutturata su un tema: ricerca su Italgiure, lettura decisioni chiave e sintesi orientamenti"
)
def analisi_giurisprudenziale(tema: str, archivio: str = "tutti") -> str:
    return f"""Esegui un'analisi giurisprudenziale strutturata sul tema indicato.

TEMA: {tema}
ARCHIVIO: {archivio} (civile / penale / tutti)

PROCEDURA:

### Fase 1 — Esplorazione distribuzione
Chiama `cerca_giurisprudenza(query="\\"{tema}\\"", archivio="{archivio}", modalita="esplora")`
per vedere la distribuzione per materia, sezione, anno e tipo provvedimento.
Usa virgolette per frasi esatte.

Se il tema riguarda una norma specifica (es. "art. 2043 c.c."), chiama prima
`giurisprudenza_su_norma(riferimento="art. ...")` per trovare le decisioni che la citano,
oppure `giurisprudenza_articolo(riferimento)` per partire dalle massime Brocardi.

### Fase 1b — Ricerca con filtri
In base ai facets, chiama `cerca_giurisprudenza` con filtri mirati (materia, sezione,
tipo_provvedimento="sentenza", max_risultati=10).
Per cercare solo nel dispositivo: `campo="dispositivo"`.

### Fase 2 — Approfondimento decisioni chiave
Seleziona le 2-3 decisioni più significative (privilegia Sezioni Unite se presenti).
Per ciascuna, chiama `leggi_sentenza(numero, anno)` per leggere il testo completo.

IMPORTANTE: usa `leggi_sentenza` — NON fare web search per sentenze già identificate.

### Fase 3 — Fondamento normativo
Per le norme citate nelle decisioni lette, verifica il testo vigente con un connettore
normativo (Normattiva, iCodici): questo server non contiene il testo delle norme.

### Fase 4 — Sintesi strutturata
Produci una sintesi che includa:
1. **Orientamento prevalente**: principio di diritto che emerge dalla giurisprudenza
2. **Evoluzione**: come si è evoluto l'orientamento nel tempo
3. **Contrasti**: eventuali divergenze tra sezioni o indirizzi minoritari
4. **Sezioni Unite**: se le SU si sono pronunciate, riporta il principio di diritto
5. **Norme di riferimento**: disposizioni normative rilevanti
6. **Decisioni citate**: elenco con estremi (Cass. civ./pen., sez., n./anno)

**IMPORTANTE — Human-in-the-loop**: DOPO la ricerca, presenta i risultati all'utente in formato tabella e chiedi "Quali sentenze vuoi approfondire?" PRIMA di chiamare leggi_sentenza. Non leggere mai il testo integrale senza la scelta esplicita dell'utente.

**Fallback web**: Se Italgiure non è raggiungibile, comunicarlo e chiedere se cercare sul web.

REGOLE:
- Non citare mai numeri di sentenza a memoria — usa esclusivamente i risultati dei tool.
- Ogni affermazione deve essere supportata da una sentenza o norma verificata.
- Se una sentenza non è trovata su Italgiure, indicarlo esplicitamente (l'archivio copre solo
  gli ultimi cinque anni circa).
"""


@mcp.prompt(
    description="Mappa descrittiva degli orientamenti di legittimità su una norma o un principio: conformi vs contrasti, Sezioni Unite, evoluzione temporale"
)
def orientamento_giurisprudenziale(riferimento: str, archivio: str = "tutti") -> str:
    return f"""Costruisci una mappa DESCRITTIVA degli orientamenti della Cassazione.

RIFERIMENTO: {riferimento} (una norma, es. "art. 2043 c.c.", oppure un principio/massima)
ARCHIVIO: {archivio} (civile / penale / tutti)

PROCEDURA:

### Fase 1 — Mappa orientamenti
Se il riferimento è una NORMA, chiama `mappa_orientamento(riferimento="{riferimento}", archivio="{archivio}")`
(orchestratore: ancora le massime Brocardi, recupera le decisioni successive, isola le Sezioni Unite).
In alternativa: `orientamento_su_norma(...)` per una norma o `orientamento_su_principio(principio="...")`
per un principio espresso a parole.

### Fase 2 — Lettura decisioni rappresentative
Presenta la distribuzione (Sezioni Unite, cluster per sezione, trend per anno, segnali testuali di
contrasto/conformità) e chiedi all'utente quali decisioni leggere. Per ciascuna scelta usa
`leggi_sentenza(numero, anno)`.

### Fase 3 — Fondamento normativo
Per le norme rilevanti verifica il testo vigente con un connettore normativo (Normattiva, iCodici).

### Fase 4 — Sintesi
Riporta: orientamento prevalente, eventuali contrasti segnalati, intervento delle Sezioni Unite (se
presente) ed evoluzione temporale.

REGOLE — IMPORTANTE:
- La mappa è DESCRITTIVA (distribuzioni, segnali testuali "contrasto/consolidato"), NON una previsione
  di overruling né una classifica dell'indirizzo "vincente" (art. 15 L. 132/2025 — ogni decisione su
  interpretazione, fatti e prove è riservata al magistrato).
- I segnali di (dis)conformità indicano che la decisione DISCUTE il contrasto/la conformità, non che essa
  conforma/diverge in fatto. Etichettali come "decisioni che segnalano...".
- L'archivio pubblico Italgiure è una finestra mobile di circa cinque anni (dal 2021): segnalare il
  limite temporale.
- Mai numeri di sentenza a memoria.
"""
