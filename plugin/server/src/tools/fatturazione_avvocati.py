"""Calcolo parcelle avvocati: compensi DM 55/2014 (agg. DM 147/2022), nota proforma,
fattura elettronica, contributo unificato, spese trasferta."""

import json
from pathlib import Path

from src.server import mcp

_DATA = Path(__file__).resolve().parent.parent / "data"

with open(_DATA / "parametri_forensi.json") as f:
    _PARAMETRI = json.load(f)

_FASI_CIVILE = ["studio", "introduttiva", "istruttoria", "decisionale"]
_FASI_PENALE = ["studio", "introduttiva", "istruttoria", "decisionale"]
_FASI_VOLONTARIA = ["studio", "trattazione"]
_COMPETENZE_PENALE = [c["tipo"] for c in _PARAMETRI["penale"]["competenze"]]


def _scaglione_label(scaglione: dict, scaglioni: list[dict]) -> str:
    if not scaglione.get("oltre"):
        return f"fino a {scaglione['fino_a']}€"
    finite = [s["fino_a"] for s in scaglioni if not s.get("oltre")]
    return f"oltre {finite[-1]}€" if finite else "oltre"


def _find_scaglione_civile(valore_causa: float) -> dict:
    for s in _PARAMETRI["civile"]["scaglioni"]:
        if s.get("oltre"):
            return s
        if valore_causa <= s["fino_a"]:
            return s
    return _PARAMETRI["civile"]["scaglioni"][-1]


def _find_scaglione_stragiudiziale(valore_pratica: float) -> dict:
    for s in _PARAMETRI["stragiudiziale"]["scaglioni"]:
        if s.get("oltre"):
            return s
        if valore_pratica <= s["fino_a"]:
            return s
    return _PARAMETRI["stragiudiziale"]["scaglioni"][-1]


def _find_scaglione_volontaria(valore_causa: float) -> dict:
    for s in _PARAMETRI["volontaria_giurisdizione"]["scaglioni"]:
        if s.get("oltre"):
            return s
        if valore_causa <= s["fino_a"]:
            return s
    return _PARAMETRI["volontaria_giurisdizione"]["scaglioni"][-1]


_TABELLE = _PARAMETRI["tabelle"]


def _tabella(nome: str) -> dict | None:
    return _TABELLE.get(nome) if not nome.startswith("_") else None


def _indice_scaglione(tab: dict, valore: float) -> int:
    """Indice dello scaglione di valore. L'ultimo copre anche tutto cio' che eccede."""
    for i, soglia in enumerate(tab["_scaglioni"]):
        if valore <= soglia:
            return i
    return len(tab["_scaglioni"]) - 1


def _etichetta_scaglione(tab: dict, i: int, valore: float) -> str:
    soglie = tab["_scaglioni"]
    if valore > soglie[-1]:
        return f"oltre € {soglie[-1]:,.0f}".replace(",", ".")
    da = 0 if i == 0 else soglie[i - 1]
    return f"da € {da:,.0f} a € {soglie[i]:,.0f}".replace(",", ".")


@mcp.tool(tags={"parcelle_avv", "sinistro", "credito"})
def parcella_avvocato_civile(
    valore_causa: float,
    tabella: str = "tribunale",
    fasi: list[str] | None = None,
    livello: str = "medio",
    soggetti_assistiti: int = 1,
    atti_telematici: bool = False,
    entrambi_i_coniugi: bool = False,
    posizioni_non_distinte: bool = False,
    conciliazione_giudiziale: bool = False,
    memoria_378_cpc: bool = False,
) -> dict:
    """Compenso tabellare dell'avvocato secondo il DM 55/2014 (agg. DM 147/2022).

    ⚠️ SCEGLIERE LA TABELLA GIUSTA: il decreto ne ha una per ciascun tipo di procedimento e
    gli importi cambiano moltissimo. Su una causa da 10.000 € il tribunale (tab. 2) da' 5.077 €
    a fronte dei 567 € del decreto ingiuntivo (tab. 8, che prevede UNA sola voce per studio,
    istruttoria e fase conclusiva): applicare la tabella sbagliata sbaglia di otto volte.
    Il risultato dichiara sempre quale tabella e' stata applicata.

    Tabelle disponibili: giudice_di_pace (1), tribunale (2, default), lavoro (3),
    previdenza (4), locatizia (5, sfratti), precetto (6), monitorio (8, decreto ingiuntivo),
    istruzione_preventiva (9), cautelare (10), appello (12), cassazione (13),
    esecuzione_mobiliare (16), esecuzione_presso_terzi (17), esecuzione_immobiliare (18),
    fallimento (20), stragiudiziale (25), mediazione (25-bis), arbitrato (26).

    Vigenza: valori medi ufficiali del DM 55/2014 come modificato dal DM 147/2022,
    trascritti da Normattiva e verificati da scripts/verifica-parametri-forensi.py.
    Precisione: ESATTO sui valori tabellari. Il minimo e il massimo sono il medio ∓50%
    (art. 4 c. 1: aumento fino al 50%, diminuzione non oltre il 50%).

    Usa questo quando: devi quantificare il compenso di un'attivita' giudiziale o
    stragiudiziale. Per il penale usa parcella_avvocato_penale().
    Chaining: → nota_spese() per aggiungere spese generali 15%, CPA 4% e IVA.

    Args:
        valore_causa: Valore della causa/dell'affare in euro (€)
        tabella: Tipo di procedimento — vedi l'elenco sopra (default 'tribunale')
        fasi: Fasi da liquidare; se omesso, tutte quelle previste dalla tabella. Le fasi
              disponibili variano: la cassazione non ha istruttoria, il monitorio ha una
              voce unica, le esecuzioni ne hanno due
        livello: 'min', 'medio' (default) o 'max' — il medio ∓50% ex art. 4 c. 1
        soggetti_assistiti: Numero di assistiti con la stessa posizione processuale.
              Art. 4 c. 2: +30% per ciascuno oltre il primo fino a dieci, +10% per ciascuno
              oltre i dieci, fino a un massimo di trenta
        atti_telematici: Art. 4 c. 1-bis — +30% se gli atti depositati telematicamente
              consentono ricerca testuale e navigazione interna
        entrambi_i_coniugi: Art. 4 c. 3 — +20% se si assistono entrambi i coniugi nella
              separazione consensuale o nel divorzio congiunto
        posizioni_non_distinte: Art. 4 c. 4 — -30% se, a parita' di posizione processuale,
              la prestazione non ha richiesto l'esame di questioni distinte
        conciliazione_giudiziale: Art. 4 c. 6 — in caso di conciliazione o transazione, il
              compenso per tale attivita' e' pari alla fase decisionale aumentata di un quarto
        memoria_378_cpc: Art. 4 c. 10-quater — solo cassazione: fase decisionale +50% se e'
              depositata memoria ex art. 378 c.p.c.
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}
    if valore_causa < 0:
        return {"errore": "valore_causa non puo' essere negativo"}
    if soggetti_assistiti < 1 or soggetti_assistiti > 30:
        return {"errore": "soggetti_assistiti deve essere tra 1 e 30 (art. 4 c. 2)"}

    tab = _tabella(tabella)
    if tab is None:
        return {
            "errore": f"Tabella '{tabella}' non disponibile",
            "tabelle_disponibili": [k for k in _TABELLE if not k.startswith("_")],
        }
    if memoria_378_cpc and tabella != "cassazione":
        return {"errore": "memoria_378_cpc si applica solo alla tabella 'cassazione' (art. 4 c. 10-quater)"}

    fasi_tab = list(tab["fasi"])
    if fasi is None:
        fasi = fasi_tab
    else:
        assenti = [f for f in fasi if f not in fasi_tab]
        if assenti:
            return {
                "errore": f"Fasi non previste dalla tabella '{tabella}': {assenti}",
                "fasi_disponibili": fasi_tab,
            }

    i = _indice_scaglione(tab, valore_causa)
    moltiplicatore = {"min": 0.5, "medio": 1.0, "max": 1.5}[livello]

    dettaglio = []
    base = 0.0
    for fase in fasi:
        medio = tab["fasi"][fase][i]
        importo = medio * moltiplicatore
        if fase == "decisionale" and memoria_378_cpc:
            importo *= 1.5
        base += importo
        dettaglio.append({"fase": fase, "valore_medio_tabellare": medio, "importo": round(importo, 2)})

    passaggi = [{"voce": f"compenso tabellare ({livello})", "importo": round(base, 2)}]
    totale = base

    if conciliazione_giudiziale and "decisionale" in tab["fasi"]:
        # art. 4 c. 6: compenso per l'attivita' conciliativa = fase decisionale + 1/4,
        # fermo quanto maturato per l'attivita' gia' svolta
        agg = tab["fasi"]["decisionale"][i] * moltiplicatore * 1.25
        totale += agg
        passaggi.append({"voce": "conciliazione/transazione — fase decisionale +1/4 (art. 4 c. 6)", "importo": round(agg, 2)})

    if soggetti_assistiti > 1:
        oltre_primo = min(soggetti_assistiti - 1, 9)
        oltre_dieci = max(soggetti_assistiti - 10, 0)
        pct = oltre_primo * 30 + oltre_dieci * 10
        agg = totale * pct / 100
        totale += agg
        passaggi.append({"voce": f"{soggetti_assistiti} assistiti — +{pct}% (art. 4 c. 2)", "importo": round(agg, 2)})

    if entrambi_i_coniugi:
        agg = totale * 0.20
        totale += agg
        passaggi.append({"voce": "assistenza a entrambi i coniugi — +20% (art. 4 c. 3)", "importo": round(agg, 2)})

    if posizioni_non_distinte:
        rid = totale * 0.30
        totale -= rid
        passaggi.append({"voce": "questioni non distinte — -30% (art. 4 c. 4)", "importo": round(-rid, 2)})

    if atti_telematici:
        agg = totale * 0.30
        totale += agg
        passaggi.append({"voce": "atti telematici navigabili — +30% (art. 4 c. 1-bis)", "importo": round(agg, 2)})

    # se il valore cade in uno scaglione che non ho potuto riscontrare sul testo ufficiale,
    # o oltre l'ultimo scaglione della tabella, dirlo invece di restituire un numero muto
    non_verif = len(tab.get("_scaglioni_non_verificabili", []))
    avvisi = []
    if non_verif and i >= len(tab["_scaglioni"]) - non_verif:
        avvisi.append(
            "scaglione non riscontrabile sul testo ufficiale (Normattiva rende quella parte "
            "della tabella come immagine): valore da verificare prima dell'uso"
        )
    if valore_causa > tab["_scaglioni"][-1]:
        avvisi.append(
            f"il valore eccede l'ultimo scaglione della tabella (€ {tab['_scaglioni'][-1]:,.0f}): "
            f"si applica l'ultimo scaglione".replace(",", ".")
        )

    return {
        "valore_causa": valore_causa,
        "tabella_applicata": f"Tab. {tab['_tabella']} — {tab['_titolo']}",
        "scaglione": _etichetta_scaglione(tab, i, valore_causa),
        "livello": livello,
        "fasi": dettaglio,
        "compenso_tabellare": round(base, 2),
        "passaggi": passaggi,
        "totale_compenso": round(totale, 2),
        "avvertenza": (
            f"Applicata la tabella '{tabella}'. Se il procedimento e' di altro tipo il compenso "
            f"cambia anche di molto: verificare l'elenco delle tabelle disponibili. Importo al netto "
            f"di spese generali 15%, CPA e IVA — usare nota_spese()."
        ),
        "riferimento_normativo": (
            f"DM 55/2014 tab. {tab['_tabella']}, testo vigente (DM 147/2022); "
            f"art. 4 per le variazioni"
        ),
        **({"nota_tabella": tab["_nota"]} if "_nota" in tab else {}),
        **({"avvisi": avvisi} if avvisi else {}),
    }


@mcp.tool(tags={"parcelle_avv"})
def parcella_avvocato_penale(
    competenza: str,
    fasi: list[str] | None = None,
    livello: str = "medio",
) -> dict:
    """Calcola compenso tabellare avvocato per procedimento penale.
    Vigenza: DM 55/2014 aggiornato DM 147/2022 — Parametri forensi penale.
    Precisione: INDICATIVO (valori medi tabellari; il giudice può variare ±50% ex art. 4 DM 55/2014).

    Args:
        competenza: Organo giudicante: 'giudice_pace', 'tribunale_monocratico', 'tribunale_collegiale', 'corte_assise', 'corte_appello', 'cassazione'
        fasi: Fasi processuali da includere (default: tutte applicabili). Valori: 'studio', 'introduttiva', 'istruttoria', 'decisionale'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if competenza not in _COMPETENZE_PENALE:
        return {"errore": f"Competenza non valida: {competenza}. Ammesse: {_COMPETENZE_PENALE}"}

    comp_data = next(c for c in _PARAMETRI["penale"]["competenze"] if c["tipo"] == competenza)

    if fasi is None:
        fasi = [f for f in _FASI_PENALE if comp_data[f] is not None]
    else:
        invalid = [f for f in fasi if f not in _FASI_PENALE]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_PENALE}"}
        unavailable = [f for f in fasi if comp_data[f] is None]
        if unavailable:
            return {"errore": f"Fasi non disponibili per {competenza}: {unavailable}"}

    dettaglio = []
    totale = 0.0
    for fase in fasi:
        importo = comp_data[fase][livello]
        totale += importo
        dettaglio.append({"fase": fase, "importo": importo})

    return {
        "competenza": competenza,
        "label": comp_data["label"],
        "livello": livello,
        "fasi": dettaglio,
        "totale_compenso": round(totale, 2),
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Parametri forensi penale",
    }


@mcp.tool(tags={"parcelle_avv"})
def parcella_stragiudiziale(
    valore_pratica: float,
    livello: str = "medio",
) -> dict:
    """Calcola compenso tabellare avvocato per attività stragiudiziale (diffida, trattativa, negoziazione).
    Vigenza: DM 55/2014 aggiornato DM 147/2022 — Parametri forensi stragiudiziale.
    Precisione: INDICATIVO (valori medi tabellari; il giudice può variare ±50% ex art. 4 DM 55/2014).

    Args:
        valore_pratica: Valore della pratica in euro (€)
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if valore_pratica < 0:
        return {"errore": "valore_pratica non può essere negativo"}

    scaglione = _find_scaglione_stragiudiziale(valore_pratica)
    scaglione_label = _scaglione_label(scaglione, _PARAMETRI["stragiudiziale"]["scaglioni"])
    compenso = scaglione[livello]

    return {
        "valore_pratica": valore_pratica,
        "scaglione": scaglione_label,
        "livello": livello,
        "compenso": compenso,
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Parametri forensi attività stragiudiziale",
    }


@mcp.tool(tags={"parcelle_avv"})
def parcella_volontaria_giurisdizione(
    valore_causa: float,
    fasi: list[str] | None = None,
    livello: str = "medio",
) -> dict:
    """Calcola compenso tabellare per procedimento di volontaria giurisdizione (Tab. 7 DM 55/2014).

    Si applica esclusivamente a procedimenti non contenziosi: interdizioni, inabilitazioni,
    amministrazioni di sostegno, tutele, curatele, DAT, autorizzazioni giudiziali.
    Per procedimenti contenziosi usare parcella_avvocato_civile.
    Vigenza: DM 55/2014 aggiornato DM 147/2022, Tabella 7.
    Precisione: INDICATIVO (valori medi tabellari; il giudice può variare ±50%).

    Args:
        valore_causa: Valore della causa in euro (€)
        fasi: Fasi da includere (default: tutte). Valori: 'studio', 'trattazione'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if valore_causa < 0:
        return {"errore": "valore_causa non può essere negativo"}

    if fasi is None:
        fasi = list(_FASI_VOLONTARIA)
    else:
        invalid = [f for f in fasi if f not in _FASI_VOLONTARIA]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_VOLONTARIA}"}

    scaglione = _find_scaglione_volontaria(valore_causa)
    scaglione_label = _scaglione_label(scaglione, _PARAMETRI["volontaria_giurisdizione"]["scaglioni"])

    dettaglio = []
    totale = 0.0
    for fase in fasi:
        importo = scaglione[fase][livello]
        totale += importo
        dettaglio.append({"fase": fase, "importo": importo})

    return {
        "valore_causa": valore_causa,
        "scaglione": scaglione_label,
        "livello": livello,
        "fasi": dettaglio,
        "totale_compenso": round(totale, 2),
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Tab. 7 Volontaria giurisdizione",
    }


@mcp.tool(tags={"parcelle_avv"})
def preventivo_volontaria_giurisdizione(
    valore_causa: float,
    fasi: list[str] | None = None,
    livello: str = "medio",
    spese_generali: bool = True,
    cpa: bool = True,
    iva: bool = True,
) -> dict:
    """Genera preventivo completo per volontaria giurisdizione con spese generali (15%), CPA (4%) e IVA (22%).

    Si applica a procedimenti non contenziosi: interdizioni, inabilitazioni, amministrazioni di sostegno,
    tutele, curatele, DAT, autorizzazioni giudiziali.
    Vigenza: DM 55/2014 aggiornato DM 147/2022, Tabella 7.
    Precisione: INDICATIVO per compensi (valori tabellari medi); ESATTO per CPA e IVA.

    Args:
        valore_causa: Valore della causa in euro (€)
        fasi: Fasi da includere (default: tutte). Valori: 'studio', 'trattazione'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
        spese_generali: Se aggiungere 15% spese generali (default: True)
        cpa: Se aggiungere CPA 4% Cassa Previdenza Avvocati (default: True)
        iva: Se aggiungere IVA 22% (default: True)
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if valore_causa < 0:
        return {"errore": "valore_causa non può essere negativo"}

    if fasi is None:
        fasi = list(_FASI_VOLONTARIA)
    else:
        invalid = [f for f in fasi if f not in _FASI_VOLONTARIA]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_VOLONTARIA}"}

    scaglione = _find_scaglione_volontaria(valore_causa)
    scaglione_label = _scaglione_label(scaglione, _PARAMETRI["volontaria_giurisdizione"]["scaglioni"])

    dettaglio_fasi = []
    totale_compensi = 0.0
    for fase in fasi:
        importo = scaglione[fase][livello]
        totale_compensi += importo
        dettaglio_fasi.append({"fase": fase, "importo": importo})

    sg_importo = round(totale_compensi * 0.15, 2) if spese_generali else 0.0
    subtotale = round(totale_compensi + sg_importo, 2)
    cpa_importo = round(subtotale * 0.04, 2) if cpa else 0.0
    imponibile_iva = round(subtotale + cpa_importo, 2)
    iva_importo = round(imponibile_iva * 0.22, 2) if iva else 0.0
    totale_onorari = round(imponibile_iva + iva_importo, 2)

    linee = [
        f"PREVENTIVO VOLONTARIA GIURISDIZIONE — Valore causa: €{valore_causa:,.2f}",
        f"Scaglione: {scaglione_label} | Livello: {livello}",
        "",
        "COMPENSI PROFESSIONALI (DM 55/2014 agg. DM 147/2022, Tab. 7):",
    ]
    for d in dettaglio_fasi:
        linee.append(f"  - Fase {d['fase']}: €{d['importo']:,.2f}")
    linee.append(f"  Totale compensi: €{totale_compensi:,.2f}")
    if spese_generali:
        linee.append(f"  Spese generali 15%: €{sg_importo:,.2f}")
    linee.append(f"  Subtotale: €{subtotale:,.2f}")
    if cpa:
        linee.append(f"  CPA 4%: €{cpa_importo:,.2f}")
    if iva:
        linee.append(f"  IVA 22%: €{iva_importo:,.2f}")
    linee.append(f"  TOTALE ONORARI: €{totale_onorari:,.2f}")

    return {
        "testo_preventivo": "\n".join(linee),
        "dettaglio_calcoli": {
            "valore_causa": valore_causa,
            "scaglione": scaglione_label,
            "livello": livello,
            "fasi": dettaglio_fasi,
            "totale_compensi": round(totale_compensi, 2),
            "spese_generali_15pct": sg_importo,
            "subtotale": subtotale,
            "cpa_4pct": cpa_importo,
            "imponibile_iva": imponibile_iva,
            "iva_22pct": iva_importo,
            "totale_onorari": totale_onorari,
        },
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Tab. 7 Volontaria giurisdizione",
    }


@mcp.tool(tags={"parcelle_avv"})
def fattura_avvocato(
    imponibile: float,
    regime: str = "ordinario",
    cpa: bool = True,
) -> dict:
    """Genera struttura fattura avvocato con CPA, IVA e ritenuta d'acconto.
    Vigenza: L. 190/2014 (regime forfettario); DPR 633/1972 (IVA); DPR 600/1973 (ritenuta).
    Precisione: ESATTO (importi di legge: CPA 4%, IVA 22%, ritenuta 20%).

    Args:
        imponibile: Compenso professionale (imponibile) in euro (€)
        regime: Regime fiscale: 'ordinario' (IVA 22% + ritenuta 20%) o 'forfettario' (no IVA, no ritenuta)
        cpa: Se applicare Cassa Previdenza Avvocati 4% sull'imponibile (default: True)
    """
    if regime not in ("ordinario", "forfettario"):
        return {"errore": f"Regime non valido: {regime}. Usare: ordinario, forfettario"}

    if imponibile < 0:
        return {"errore": "imponibile non può essere negativo"}

    voci = [{"descrizione": "Compenso professionale", "importo": round(imponibile, 2)}]

    cpa_importo = 0.0
    if cpa:
        cpa_importo = round(imponibile * 0.04, 2)
        voci.append({"descrizione": "CPA 4% (Cassa Previdenza Avvocati)", "importo": cpa_importo})

    imponibile_iva = round(imponibile + cpa_importo, 2)

    iva_importo = 0.0
    ritenuta_importo = 0.0

    if regime == "ordinario":
        iva_importo = round(imponibile_iva * 0.22, 2)
        ritenuta_importo = round(imponibile * 0.20, 2)
        voci.append({"descrizione": "IVA 22%", "importo": iva_importo})
        voci.append({"descrizione": "Ritenuta d'acconto 20% (su compenso)", "importo": -ritenuta_importo})
        totale = round(imponibile_iva + iva_importo - ritenuta_importo, 2)
    else:
        totale = imponibile_iva
        voci.append({"descrizione": "IVA: esente (regime forfettario art. 1 c. 54-89 L. 190/2014)", "importo": 0.0})

    return {
        "regime": regime,
        "imponibile": round(imponibile, 2),
        "cpa_4pct": cpa_importo,
        "imponibile_iva": imponibile_iva,
        "iva_22pct": iva_importo,
        "ritenuta_acconto_20pct": ritenuta_importo,
        "totale_fattura": totale,
        "netto_a_pagare": totale,
        "voci": voci,
    }


@mcp.tool(tags={"parcelle_avv"})
def nota_spese(
    voci: list[dict],
) -> dict:
    """Calcola nota spese avvocato aggregando voci di compenso, spese generali (15%), CPA (4%) e IVA (22%).
    Vigenza: DM 55/2014 art. 2 co. 2 (spese generali 15%).
    Precisione: ESATTO per percentuali di legge; INDICATIVO per voci di compenso inserite manualmente.

    Args:
        voci: Lista di voci, ciascuna con: descrizione (str), importo (float in €), tipo ('compenso', 'spese_generali_15pct', 'spese_vive', 'spese_documentate')
    """
    tipi_validi = {"compenso", "spese_generali_15pct", "spese_vive", "spese_documentate"}
    for v in voci:
        if v.get("tipo") not in tipi_validi:
            return {"errore": f"Tipo voce non valido: {v.get('tipo')}. Ammessi: {sorted(tipi_validi)}"}
        if "importo" not in v or "descrizione" not in v:
            return {"errore": f"Voce incompleta: {v}. Richiesti 'descrizione' e 'importo'."}

    dettaglio = []
    totale_compensi = 0.0
    totale_spese_generali = 0.0
    totale_spese_vive = 0.0

    for v in voci:
        importo = round(v["importo"], 2)
        tipo = v["tipo"]

        if tipo == "compenso":
            totale_compensi += importo
            dettaglio.append({"descrizione": v["descrizione"], "tipo": tipo, "importo": importo})
        elif tipo == "spese_generali_15pct":
            sg = round(v["importo"] * 0.15, 2)
            totale_spese_generali += sg
            dettaglio.append({"descrizione": v["descrizione"] + " (15% spese generali)", "tipo": tipo, "importo": sg})
        elif tipo in ("spese_vive", "spese_documentate"):
            totale_spese_vive += importo
            dettaglio.append({"descrizione": v["descrizione"], "tipo": tipo, "importo": importo})

    subtotale = round(totale_compensi + totale_spese_generali, 2)
    cpa = round(subtotale * 0.04, 2)
    imponibile_iva = round(subtotale + cpa, 2)
    iva = round(imponibile_iva * 0.22, 2)
    totale = round(imponibile_iva + iva + totale_spese_vive, 2)

    return {
        "dettaglio_voci": dettaglio,
        "totale_compensi": totale_compensi,
        "totale_spese_generali_15pct": totale_spese_generali,
        "subtotale_compensi": subtotale,
        "cpa_4pct": cpa,
        "imponibile_iva": imponibile_iva,
        "iva_22pct": iva,
        "totale_spese_vive": totale_spese_vive,
        "totale_nota_spese": totale,
        "riferimento_normativo": "DM 55/2014 — Art. 2 c. 2 spese generali 15%",
    }


# --- Spese vive stimate per tipo procedimento civile ---
_SPESE_VIVE_STIMATE = {
    "contributo_unificato": [
        (1_100, 43),
        (5_200, 98),
        (26_000, 237),
        (52_000, 518),
        (260_000, 759),
        (520_000, 1_214),
        (float("inf"), 1_686),
    ],
    "marca_da_bollo": 27.0,
    "notifica_pec": 3.54,
    "notifica_ufficiale_giudiziario": 27.0,
    "diritti_copia": 15.0,
}


def _contributo_unificato(valore_causa: float) -> float:
    for soglia, importo in _SPESE_VIVE_STIMATE["contributo_unificato"]:
        if valore_causa <= soglia:
            return importo
    return _SPESE_VIVE_STIMATE["contributo_unificato"][-1][1]


@mcp.tool(tags={"parcelle_avv"})
def preventivo_civile(
    valore_causa: float,
    fasi: list[str] | None = None,
    livello: str = "medio",
    spese_generali: bool = True,
    cpa: bool = True,
    iva: bool = True,
) -> dict:
    """Genera preventivo completo per causa civile: compensi tabellari, spese generali (15%), CPA (4%), IVA (22%) e spese vive stimate.
    Vigenza: DM 55/2014 aggiornato DM 147/2022; contributo unificato ex DPR 115/2002 (importi di legge).
    Precisione: INDICATIVO per compensi (valori tabellari medi); ESATTO per contributo unificato e CPA/IVA.

    Args:
        valore_causa: Valore della causa in euro (€)
        fasi: Fasi processuali (default: tutte). Valori: 'studio', 'introduttiva', 'istruttoria', 'decisionale'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
        spese_generali: Se aggiungere 15% spese generali (default: True)
        cpa: Se aggiungere CPA 4% Cassa Previdenza Avvocati (default: True)
        iva: Se aggiungere IVA 22% (default: True)
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if valore_causa < 0:
        return {"errore": "valore_causa non può essere negativo"}

    if fasi is None:
        fasi = list(_FASI_CIVILE)
    else:
        invalid = [f for f in fasi if f not in _FASI_CIVILE]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_CIVILE}"}

    scaglione = _find_scaglione_civile(valore_causa)
    scaglione_label = _scaglione_label(scaglione, _PARAMETRI["civile"]["scaglioni"])

    dettaglio_fasi = []
    totale_compensi = 0.0
    for fase in fasi:
        importo = scaglione[fase][livello]
        totale_compensi += importo
        dettaglio_fasi.append({"fase": fase, "importo": importo})

    sg_importo = round(totale_compensi * 0.15, 2) if spese_generali else 0.0
    subtotale = round(totale_compensi + sg_importo, 2)
    cpa_importo = round(subtotale * 0.04, 2) if cpa else 0.0
    imponibile_iva = round(subtotale + cpa_importo, 2)
    iva_importo = round(imponibile_iva * 0.22, 2) if iva else 0.0
    totale_onorari = round(imponibile_iva + iva_importo, 2)

    # Spese vive stimate
    cu = _contributo_unificato(valore_causa)
    spese_vive = {
        "contributo_unificato": cu,
        "marca_da_bollo_iscrizione": _SPESE_VIVE_STIMATE["marca_da_bollo"],
        "notifica_pec": _SPESE_VIVE_STIMATE["notifica_pec"],
        "notifica_ufficiale_giudiziario": _SPESE_VIVE_STIMATE["notifica_ufficiale_giudiziario"],
        "diritti_copia": _SPESE_VIVE_STIMATE["diritti_copia"],
    }
    totale_spese_vive = round(sum(spese_vive.values()), 2)
    totale_preventivo = round(totale_onorari + totale_spese_vive, 2)

    linee = [
        f"PREVENTIVO CAUSA CIVILE — Valore causa: €{valore_causa:,.2f}",
        f"Scaglione: {scaglione_label} | Livello: {livello}",
        "",
        "COMPENSI PROFESSIONALI:",
    ]
    for d in dettaglio_fasi:
        linee.append(f"  - Fase {d['fase']}: €{d['importo']:,.2f}")
    linee.append(f"  Totale compensi: €{totale_compensi:,.2f}")
    if spese_generali:
        linee.append(f"  Spese generali 15%: €{sg_importo:,.2f}")
    linee.append(f"  Subtotale: €{subtotale:,.2f}")
    if cpa:
        linee.append(f"  CPA 4%: €{cpa_importo:,.2f}")
    if iva:
        linee.append(f"  IVA 22%: €{iva_importo:,.2f}")
    linee.append(f"  TOTALE ONORARI: €{totale_onorari:,.2f}")
    linee.append("")
    linee.append("SPESE VIVE STIMATE:")
    for k, v in spese_vive.items():
        linee.append(f"  - {k.replace('_', ' ').title()}: €{v:,.2f}")
    linee.append(f"  TOTALE SPESE VIVE: €{totale_spese_vive:,.2f}")
    linee.append("")
    linee.append(f"TOTALE PREVENTIVO: €{totale_preventivo:,.2f}")

    return {
        "testo_preventivo": "\n".join(linee),
        "dettaglio_calcoli": {
            "valore_causa": valore_causa,
            "scaglione": scaglione_label,
            "livello": livello,
            "fasi": dettaglio_fasi,
            "totale_compensi": round(totale_compensi, 2),
            "spese_generali_15pct": sg_importo,
            "subtotale": subtotale,
            "cpa_4pct": cpa_importo,
            "imponibile_iva": imponibile_iva,
            "iva_22pct": iva_importo,
            "totale_onorari": totale_onorari,
            "spese_vive": spese_vive,
            "totale_spese_vive": totale_spese_vive,
            "totale_preventivo": totale_preventivo,
        },
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Parametri forensi contenzioso civile",
    }


@mcp.tool(tags={"parcelle_avv"})
def preventivo_stragiudiziale(
    valore_pratica: float,
    livello: str = "medio",
    spese_generali: bool = True,
    cpa: bool = True,
    iva: bool = True,
) -> dict:
    """Genera preventivo per attività stragiudiziale (diffida, trattativa, mediazione) con spese generali (15%), CPA (4%) e IVA (22%).
    Vigenza: DM 55/2014 aggiornato DM 147/2022 — Parametri forensi stragiudiziale.
    Precisione: INDICATIVO per compensi (valori tabellari medi); ESATTO per CPA e IVA.

    Args:
        valore_pratica: Valore della pratica in euro (€)
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
        spese_generali: Se aggiungere 15% spese generali (default: True)
        cpa: Se aggiungere CPA 4% Cassa Previdenza Avvocati (default: True)
        iva: Se aggiungere IVA 22% (default: True)
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}

    if valore_pratica < 0:
        return {"errore": "valore_pratica non può essere negativo"}

    scaglione = _find_scaglione_stragiudiziale(valore_pratica)
    scaglione_label = _scaglione_label(scaglione, _PARAMETRI["stragiudiziale"]["scaglioni"])
    compenso = scaglione[livello]

    sg_importo = round(compenso * 0.15, 2) if spese_generali else 0.0
    subtotale = round(compenso + sg_importo, 2)
    cpa_importo = round(subtotale * 0.04, 2) if cpa else 0.0
    imponibile_iva = round(subtotale + cpa_importo, 2)
    iva_importo = round(imponibile_iva * 0.22, 2) if iva else 0.0
    totale = round(imponibile_iva + iva_importo, 2)

    linee = [
        f"PREVENTIVO ATTIVITÀ STRAGIUDIZIALE — Valore pratica: €{valore_pratica:,.2f}",
        f"Scaglione: {scaglione_label} | Livello: {livello}",
        "",
        f"  Compenso base: €{compenso:,.2f}",
    ]
    if spese_generali:
        linee.append(f"  Spese generali 15%: €{sg_importo:,.2f}")
    linee.append(f"  Subtotale: €{subtotale:,.2f}")
    if cpa:
        linee.append(f"  CPA 4%: €{cpa_importo:,.2f}")
    if iva:
        linee.append(f"  IVA 22%: €{iva_importo:,.2f}")
    linee.append(f"  TOTALE: €{totale:,.2f}")

    return {
        "testo_preventivo": "\n".join(linee),
        "dettaglio_calcoli": {
            "valore_pratica": valore_pratica,
            "scaglione": scaglione_label,
            "livello": livello,
            "compenso_base": compenso,
            "spese_generali_15pct": sg_importo,
            "subtotale": subtotale,
            "cpa_4pct": cpa_importo,
            "imponibile_iva": imponibile_iva,
            "iva_22pct": iva_importo,
            "totale": totale,
        },
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Parametri forensi attività stragiudiziale",
    }


@mcp.tool(tags={"parcelle_avv"})
def spese_trasferta_avvocati(
    km_distanza: float,
    ore_assenza: float,
    pernottamento: bool = False,
    mezzo: str = "auto",
) -> dict:
    """Calcola indennità di trasferta e rimborso chilometrico per avvocati.
    Vigenza: DM 55/2014 art. 27 — Spese di trasferta avvocati.
    Precisione: INDICATIVO (indennità calcolata come percentuale sull'onorario medio di riferimento).

    Args:
        km_distanza: Distanza andata/ritorno in km (valore positivo)
        ore_assenza: Ore di assenza dallo studio (es. 3.5)
        pernottamento: True se è necessario il pernottamento (rimborso a piè di lista)
        mezzo: Mezzo di trasporto: 'auto' (€0.30/km ACI), 'treno' (a piè di lista), 'aereo' (a piè di lista)
    """
    if mezzo not in ("auto", "treno", "aereo"):
        return {"errore": f"Mezzo non valido: {mezzo}. Usare: auto, treno, aereo"}

    if km_distanza < 0:
        return {"errore": "km_distanza non può essere negativo"}

    if ore_assenza < 0:
        return {"errore": "ore_assenza non può essere negativo"}

    # Rimborso chilometrico (solo auto)
    rimborso_km = round(km_distanza * 0.30, 2) if mezzo == "auto" else 0.0

    # Indennità di trasferta basata su ore assenza
    # Riferimento: onorario medio fase studio scaglione 26.000€ = 540€
    onorario_riferimento = 540.0
    if ore_assenza <= 4:
        pct_indennita = 10
    elif ore_assenza <= 8:
        pct_indennita = 20
    else:
        pct_indennita = 40
    indennita = round(onorario_riferimento * pct_indennita / 100, 2)

    voci = [
        {"voce": f"Indennità trasferta ({pct_indennita}% su €{onorario_riferimento})", "importo": indennita},
    ]
    if mezzo == "auto":
        voci.append({"voce": f"Rimborso km ({km_distanza} km × €0.30)", "importo": rimborso_km})
    else:
        voci.append({"voce": f"Rimborso {mezzo}: a piè di lista", "importo": 0.0})

    nota_pernottamento = None
    if pernottamento:
        nota_pernottamento = "Pernottamento: rimborso a piè di lista su presentazione di ricevuta/fattura"
        voci.append({"voce": "Pernottamento", "importo": 0.0, "nota": "a piè di lista"})

    totale_stimato = round(indennita + rimborso_km, 2)

    return {
        "km_distanza": km_distanza,
        "ore_assenza": ore_assenza,
        "mezzo": mezzo,
        "pernottamento": pernottamento,
        "indennita_trasferta": indennita,
        "percentuale_indennita": pct_indennita,
        "rimborso_km": rimborso_km,
        "totale_stimato": totale_stimato,
        "voci": voci,
        "nota_pernottamento": nota_pernottamento,
        "note": [
            "L'indennità è calcolata come percentuale dell'onorario medio (scaglione €26.000, fase studio)",
            "Per treno/aereo il rimborso è a piè di lista su documentazione",
            "Il pernottamento è sempre rimborsato a piè di lista",
        ],
        "riferimento_normativo": "DM 55/2014 art. 27 — Spese di trasferta avvocati",
    }


# Parametri forfettari per notule su procedimenti tipici
_NOTULA_PROCEDIMENTI = {
    "decreto_ingiuntivo": {
        "fasi_default": ["studio", "introduttiva"],
        "descrizione": "Ricorso per decreto ingiuntivo",
        "spese_vive_stimate": {"contributo_unificato_dimezzato": True, "marca_da_bollo": 27.0},
    },
    "precetto": {
        "fasi_default": ["studio", "introduttiva"],
        "descrizione": "Atto di precetto",
        "spese_vive_stimate": {"marca_da_bollo": 27.0, "notifica": 27.0},
    },
    "esecuzione_mobiliare": {
        "fasi_default": ["studio", "introduttiva", "istruttoria"],
        "descrizione": "Esecuzione mobiliare presso terzi",
        "spese_vive_stimate": {"contributo_unificato": True, "marca_da_bollo": 27.0},
    },
    "esecuzione_immobiliare": {
        "fasi_default": ["studio", "introduttiva", "istruttoria", "decisionale"],
        "descrizione": "Esecuzione immobiliare",
        "spese_vive_stimate": {"contributo_unificato": True, "marca_da_bollo": 27.0, "trascrizione": 300.0},
    },
}


@mcp.tool(tags={"parcelle_avv"})
def modello_notula(
    tipo_procedimento: str,
    avvocato: str,
    cliente: str,
    valore_causa: float,
    fasi: list[str] | None = None,
    livello: str = "medio",
) -> dict:
    """Genera notula (nota spese) completa formattata per procedimenti tipici di recupero crediti.
    Vigenza: DM 55/2014 aggiornato DM 147/2022; contributo unificato ex DPR 115/2002.
    Precisione: INDICATIVO per compensi (valori tabellari medi); ESATTO per contributo unificato e CPA/IVA.

    Args:
        tipo_procedimento: Tipo procedimento: 'decreto_ingiuntivo', 'precetto', 'esecuzione_mobiliare', 'esecuzione_immobiliare'
        avvocato: Nome e cognome dell'avvocato
        cliente: Nome e cognome / ragione sociale del cliente
        valore_causa: Valore della causa in euro (€)
        fasi: Fasi da includere (default: fasi tipiche del procedimento). Valori: 'studio', 'introduttiva', 'istruttoria', 'decisionale'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
    """
    if tipo_procedimento not in _NOTULA_PROCEDIMENTI:
        return {"errore": f"Tipo non valido: {tipo_procedimento}. Ammessi: {list(_NOTULA_PROCEDIMENTI.keys())}"}
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}
    if valore_causa < 0:
        return {"errore": "valore_causa non può essere negativo"}

    proc = _NOTULA_PROCEDIMENTI[tipo_procedimento]
    if fasi is None:
        fasi = proc["fasi_default"]
    else:
        invalid = [f for f in fasi if f not in _FASI_CIVILE]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_CIVILE}"}

    scaglione = _find_scaglione_civile(valore_causa)

    dettaglio_fasi = []
    totale_compensi = 0.0
    for fase in fasi:
        importo = scaglione[fase][livello]
        totale_compensi += importo
        dettaglio_fasi.append({"fase": fase, "importo": importo})

    sg = round(totale_compensi * 0.15, 2)
    subtotale = round(totale_compensi + sg, 2)
    cpa_importo = round(subtotale * 0.04, 2)
    imponibile_iva = round(subtotale + cpa_importo, 2)
    iva_importo = round(imponibile_iva * 0.22, 2)
    totale_onorari = round(imponibile_iva + iva_importo, 2)

    # Spese vive
    spese_vive_det = {}
    sv = proc["spese_vive_stimate"]
    if sv.get("contributo_unificato"):
        spese_vive_det["contributo_unificato"] = _contributo_unificato(valore_causa)
    if sv.get("contributo_unificato_dimezzato"):
        spese_vive_det["contributo_unificato_dimezzato"] = round(_contributo_unificato(valore_causa) / 2, 2)
    if sv.get("marca_da_bollo"):
        spese_vive_det["marca_da_bollo"] = sv["marca_da_bollo"]
    if sv.get("notifica"):
        spese_vive_det["notifica"] = sv["notifica"]
    if sv.get("trascrizione"):
        spese_vive_det["trascrizione"] = sv["trascrizione"]
    totale_spese_vive = round(sum(spese_vive_det.values()), 2)
    totale_notula = round(totale_onorari + totale_spese_vive, 2)

    linee = [
        "NOTULA — NOTA SPESE",
        f"Avv. {avvocato}",
        f"Cliente: {cliente}",
        f"Procedimento: {proc['descrizione']}",
        f"Valore causa: €{valore_causa:,.2f}",
        "",
        "COMPENSI PROFESSIONALI (DM 55/2014 agg. DM 147/2022):",
    ]
    for d in dettaglio_fasi:
        linee.append(f"  Fase {d['fase']}: €{d['importo']:,.2f}")
    linee.append(f"  Totale compensi: €{totale_compensi:,.2f}")
    linee.append(f"  Spese generali 15%: €{sg:,.2f}")
    linee.append(f"  Subtotale: €{subtotale:,.2f}")
    linee.append(f"  CPA 4%: €{cpa_importo:,.2f}")
    linee.append(f"  IVA 22%: €{iva_importo:,.2f}")
    linee.append(f"  TOTALE ONORARI: €{totale_onorari:,.2f}")
    linee.append("")
    linee.append("SPESE VIVE:")
    for k, v in spese_vive_det.items():
        linee.append(f"  {k.replace('_', ' ').title()}: €{v:,.2f}")
    linee.append(f"  TOTALE SPESE VIVE: €{totale_spese_vive:,.2f}")
    linee.append("")
    linee.append(f"TOTALE NOTULA: €{totale_notula:,.2f}")

    return {
        "testo_notula": "\n".join(linee),
        "dettaglio_calcoli": {
            "tipo_procedimento": tipo_procedimento,
            "avvocato": avvocato,
            "cliente": cliente,
            "valore_causa": valore_causa,
            "livello": livello,
            "fasi": dettaglio_fasi,
            "totale_compensi": round(totale_compensi, 2),
            "spese_generali_15pct": sg,
            "subtotale": subtotale,
            "cpa_4pct": cpa_importo,
            "iva_22pct": iva_importo,
            "totale_onorari": totale_onorari,
            "spese_vive": spese_vive_det,
            "totale_spese_vive": totale_spese_vive,
            "totale_notula": totale_notula,
        },
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022",
    }


@mcp.tool(tags={"parcelle_avv"})
def calcolo_notula_penale(
    competenza: str,
    fasi: list[str] | None = None,
    livello: str = "medio",
    spese_generali: bool = True,
) -> dict:
    """Calcola parcella penale completa con spese generali (15%), CPA (4%) e IVA (22%).
    Equivalente a parcella_avvocato_penale ma include già il calcolo del totale con accessori.
    Vigenza: DM 55/2014 aggiornato DM 147/2022 — Parametri forensi penale.
    Precisione: INDICATIVO per compensi (valori tabellari medi); ESATTO per CPA e IVA.

    Args:
        competenza: Organo giudicante: 'giudice_pace', 'tribunale_monocratico', 'tribunale_collegiale', 'corte_assise', 'corte_appello', 'cassazione'
        fasi: Fasi processuali (default: tutte applicabili). Valori: 'studio', 'introduttiva', 'istruttoria', 'decisionale'
        livello: Livello compenso tabellare: 'min', 'medio', 'max'
        spese_generali: Se aggiungere 15% spese generali art. 2 DM 55/2014 (default: True)
    """
    if livello not in ("min", "medio", "max"):
        return {"errore": f"Livello non valido: {livello}. Usare: min, medio, max"}
    if competenza not in _COMPETENZE_PENALE:
        return {"errore": f"Competenza non valida: {competenza}. Ammesse: {_COMPETENZE_PENALE}"}

    comp_data = next(c for c in _PARAMETRI["penale"]["competenze"] if c["tipo"] == competenza)

    if fasi is None:
        fasi = [f for f in _FASI_PENALE if comp_data[f] is not None]
    else:
        invalid = [f for f in fasi if f not in _FASI_PENALE]
        if invalid:
            return {"errore": f"Fasi non valide: {invalid}. Ammesse: {_FASI_PENALE}"}
        unavailable = [f for f in fasi if comp_data[f] is None]
        if unavailable:
            return {"errore": f"Fasi non disponibili per {competenza}: {unavailable}"}

    dettaglio_fasi = []
    totale_compensi = 0.0
    for fase in fasi:
        importo = comp_data[fase][livello]
        totale_compensi += importo
        dettaglio_fasi.append({"fase": fase, "importo": importo})

    sg_importo = round(totale_compensi * 0.15, 2) if spese_generali else 0.0
    subtotale = round(totale_compensi + sg_importo, 2)
    cpa_importo = round(subtotale * 0.04, 2)
    imponibile_iva = round(subtotale + cpa_importo, 2)
    iva_importo = round(imponibile_iva * 0.22, 2)
    totale = round(imponibile_iva + iva_importo, 2)

    return {
        "competenza": competenza,
        "label": comp_data["label"],
        "livello": livello,
        "fasi": dettaglio_fasi,
        "totale_compensi": round(totale_compensi, 2),
        "spese_generali_15pct": sg_importo,
        "subtotale": subtotale,
        "cpa_4pct": cpa_importo,
        "imponibile_iva": imponibile_iva,
        "iva_22pct": iva_importo,
        "totale": totale,
        "riferimento_normativo": "DM 55/2014 aggiornato DM 147/2022 — Parametri forensi penale",
    }
