"""Calcoli per risarcimento danni: danno biologico micropermanenti (art. 139 CdA) e macropermanenti
(art. 138 CdA), danno non patrimoniale con tutte le componenti, danno parentale (tabelle Milano/Roma),
menomazioni plurime (Balthazard), indennizzo INAIL, equo indennizzo causa di servizio."""

import json
from pathlib import Path

from src.server import mcp

_DATA = Path(__file__).resolve().parent.parent / "data"

with open(_DATA / "tabella_danno_bio.json") as f:
    _DANNO_BIO = json.load(f)

with open(_DATA / "tabella_milano_roma.json") as f:
    _PARENTALE = json.load(f)

_MICRO = _DANNO_BIO["micropermanenti"]
_MACRO = _DANNO_BIO["macropermanenti"]


def _coefficiente_eta(eta: int) -> float:
    """Return age coefficient for macropermanenti from range keys."""
    for chiave, coeff in _MACRO["coefficiente_eta"].items():
        if chiave.startswith("_"):
            continue
        low, high = map(int, chiave.split("-"))
        if low <= eta <= high:
            return coeff
    return 0.40


def _interpola_punto_base(percentuale: int) -> float:
    """Interpolate punto_base from macropermanenti table."""
    punti = {int(k): v for k, v in _MACRO["punto_base"].items()}
    soglie = sorted(punti.keys())

    if percentuale in punti:
        return punti[percentuale]

    for i in range(len(soglie) - 1):
        if soglie[i] < percentuale < soglie[i + 1]:
            low, high = soglie[i], soglie[i + 1]
            ratio = (percentuale - low) / (high - low)
            return punti[low] + ratio * (punti[high] - punti[low])

    if percentuale < soglie[0]:
        return punti[soglie[0]]
    return punti[soglie[-1]]


@mcp.tool(tags={"danni"})
def danno_biologico_micro(
    percentuale_invalidita: int,
    eta_vittima: int,
    giorni_itt: int = 0,
    giorni_itp75: int = 0,
    giorni_itp50: int = 0,
    giorni_itp25: int = 0,
    personalizzazione_pct: float = 0,
) -> dict:
    """Calcola il danno biologico per MICROPERMANENTI (≤9% di invalidità).
    Applica art. 139 Codice delle Assicurazioni (D.Lgs. 209/2005).
    Vigenza: DM 20 luglio 2026 (GU n.173 del 28/07/2026), valori in vigore da aprile 2026.
    Formula: punto_base x coefficiente(N) x N punti x (1 - 0,005 x (eta - 10)).
    Precisione: ESATTO (formula di legge applicata ai valori tabellari vigenti).

    Usa questo quando: sinistro stradale o sanitario con invalidità permanente tra 1% e 9%.
    NON usare per: invalidità ≥10% → usa danno_biologico_macro().
    NON usare per: danno non patrimoniale con tutte le componenti → usa danno_non_patrimoniale().
    Chaining: → danno_non_patrimoniale() → rivalutazione_monetaria() → interessi_legali()

    Args:
        percentuale_invalidita: Percentuale di invalidità permanente (1-9)
        eta_vittima: Età della vittima al momento del sinistro (0-120)
        giorni_itt: Giorni di invalidità temporanea totale al 100%
        giorni_itp75: Giorni di invalidità temporanea parziale al 75%
        giorni_itp50: Giorni di invalidità temporanea parziale al 50%
        giorni_itp25: Giorni di invalidità temporanea parziale al 25%
        personalizzazione_pct: Percentuale di personalizzazione per danno morale (0-20)
    """
    if not 1 <= percentuale_invalidita <= 9:
        return {"errore": "Micropermanenti: percentuale deve essere tra 1 e 9"}

    if not 0 <= eta_vittima <= 120:
        return {"errore": "Età non valida"}

    if personalizzazione_pct < 0 or personalizzazione_pct > _MICRO["maggiorazione_morale_max_pct"]:
        return {"errore": f"Personalizzazione deve essere tra 0 e {_MICRO['maggiorazione_morale_max_pct']}%"}

    punto_base = _MICRO["punto_base"]
    coefficienti = _MICRO["coefficienti_punto"]
    eta_inizio_decremento = _MICRO["eta_decremento_da"]
    decremento_pct = _MICRO["decremento_eta_pct_per_anno"]

    # Age adjustment: 0.5% reduction per year from age 11 onward (art. 139 c. 1)
    if eta_vittima >= eta_inizio_decremento:
        anni_sopra = eta_vittima - eta_inizio_decremento
        riduzione = 1 - (decremento_pct / 100) * anni_sopra
        riduzione = max(riduzione, 0)
    else:
        riduzione = 1.0

    # Art. 139 c. 1 lett. a) + c. 6: al grado COMPLESSIVO di invalidita' corrisponde UN
    # coefficiente, che si applica al valore del primo punto moltiplicato per i punti.
    #   danno = punto_base x coefficiente(N) x N x riduzione_eta
    # ⚠️ Non e' la somma dei valori dei singoli punti: quella sottostimava fino al 34%
    #    (9% a 40 anni: 11.546 € invece di 17.392 €). Correzione del 2026-08-14.
    coeff = coefficienti[str(percentuale_invalidita)]
    danno_permanente = punto_base * coeff * percentuale_invalidita * riduzione
    dettaglio_punti = [{
        "percentuale": percentuale_invalidita,
        "coefficiente": coeff,
        "valore_punto_applicato": round(punto_base * coeff * riduzione, 2),
    }]

    # Invalidità temporanea
    itt = giorni_itt * _MICRO["invalidita_temporanea_totale_giornaliera"]
    itp75 = giorni_itp75 * _MICRO["invalidita_temporanea_parziale_75_pct"]
    itp50 = giorni_itp50 * _MICRO["invalidita_temporanea_parziale_50_pct"]
    itp25 = giorni_itp25 * _MICRO["invalidita_temporanea_parziale_25_pct"]
    danno_temporaneo = itt + itp75 + itp50 + itp25

    danno_base = danno_permanente + danno_temporaneo

    # Personalizzazione (danno morale)
    maggiorazione_morale = danno_base * (personalizzazione_pct / 100)

    totale = danno_base + maggiorazione_morale

    return {
        "percentuale_invalidita": percentuale_invalidita,
        "eta_vittima": eta_vittima,
        "punto_base": punto_base,
        "riduzione_eta": round(riduzione, 4),
        "danno_permanente": round(danno_permanente, 2),
        "danno_temporaneo": {
            "itt": {"giorni": giorni_itt, "importo": round(itt, 2)},
            "itp_75": {"giorni": giorni_itp75, "importo": round(itp75, 2)},
            "itp_50": {"giorni": giorni_itp50, "importo": round(itp50, 2)},
            "itp_25": {"giorni": giorni_itp25, "importo": round(itp25, 2)},
            "totale": round(danno_temporaneo, 2),
        },
        "danno_base": round(danno_base, 2),
        "personalizzazione_pct": personalizzazione_pct,
        "maggiorazione_morale": round(maggiorazione_morale, 2),
        "totale_risarcimento": round(totale, 2),
        "dettaglio_punti": dettaglio_punti,
        "riferimento_normativo": "Art. 139 Cod. Assicurazioni (D.Lgs. 209/2005) — DM 20 luglio 2026 (GU 28/07/2026 n. 173)",
        "formula": "punto_base x coefficiente(N) x N punti x (1 - 0,005 x (eta - 10))",
    }


@mcp.tool(tags={"danni"})
def danno_biologico_macro(
    percentuale_invalidita: int,
    eta_vittima: int,
    personalizzazione_pct: float = 0,
) -> dict:
    """Calcola il danno biologico per MACROPERMANENTI (≥10% di invalidità).
    ⚠️ STIMA, NON UNA LIQUIDAZIONE. I valori usati sono medi indicativi e i coefficienti per
    eta' sono a scaglioni decennali: NON riproducono ne' la tabella unica nazionale ex art. 138
    CdA (che va adottata con DPR e si applica ai soli sinistri successivi alla sua entrata in
    vigore, art. 1 c. 18 L. 124/2017) ne' le tabelle di Milano. Serve per un ordine di grandezza:
    per la liquidazione vera occorre la tabella applicabile al caso.
    Precisione: INDICATIVO.

    Usa questo quando: sinistro stradale o sanitario con invalidità permanente tra 10% e 100%.
    NON usare per: invalidità <10% → usa danno_biologico_micro().
    NON usare per: danno non patrimoniale con tutte le componenti → usa danno_non_patrimoniale().
    Chaining: → danno_non_patrimoniale() → rivalutazione_monetaria() → interessi_legali()

    Args:
        percentuale_invalidita: Percentuale di invalidità permanente (10-100)
        eta_vittima: Età della vittima al momento del sinistro (0-120)
        personalizzazione_pct: Personalizzazione ex art. 138 c. 3 (0-30)
    """
    if not 10 <= percentuale_invalidita <= 100:
        return {"errore": "Macropermanenti: percentuale deve essere tra 10 e 100"}

    if not 0 <= eta_vittima <= 120:
        return {"errore": "Età non valida"}

    # Art. 138 c. 3: aumento "fino al 30 per cento". Il tetto del 50% era fuori legge.
    if personalizzazione_pct < 0 or personalizzazione_pct > 30:
        return {"errore": "Art. 138 c. 3 Cod. Ass.: la personalizzazione non puo' superare il 30%"}

    punto_base = _interpola_punto_base(percentuale_invalidita)
    coeff_eta = _coefficiente_eta(eta_vittima)

    danno_base = punto_base * percentuale_invalidita * coeff_eta

    maggiorazione_morale = danno_base * (personalizzazione_pct / 100)
    totale = danno_base + maggiorazione_morale

    return {
        "percentuale_invalidita": percentuale_invalidita,
        "eta_vittima": eta_vittima,
        "punto_base_interpolato": round(punto_base, 2),
        "coefficiente_eta": coeff_eta,
        "danno_base": round(danno_base, 2),
        "personalizzazione_pct": personalizzazione_pct,
        "maggiorazione_morale": round(maggiorazione_morale, 2),
        "totale_risarcimento": round(totale, 2),
        "personalizzazione_max_pct": 30.0,
        "avvertenza": (
            "STIMA, non una liquidazione: valori medi indicativi e coefficienti per eta' a scaglioni "
            "decennali, che non riproducono ne' la TUN ex art. 138 CdA ne' le tabelle di Milano. "
            "Per la liquidazione usare la tabella applicabile al caso."
        ),
        "riferimento_normativo": "Art. 138 Cod. Assicurazioni (D.Lgs. 209/2005) — tetto personalizzazione 30% (c. 3)",
    }


def _punti_fascia(tabella_eta: dict, eta: int) -> tuple[int, float]:
    """Restituisce (punti, fascia) per l'eta' data, sulle fasce 'da-a' della tabella."""
    for chiave, punti in tabella_eta.items():
        if chiave.startswith("_"):
            continue
        low, high = map(int, chiave.split("-"))
        if low <= eta <= high:
            return punti, chiave
    return 0, "fuori scala"


@mcp.tool(tags={"danni"})
def danno_parentale(
    eta_vittima: int,
    eta_superstite: int,
    tabella: str = "milano",
    rapporto: str = "genitore_figlio_coniuge",
    convivenza: str = "non_conviventi",
    superstiti_nucleo: int = 1,
    punti_qualita_relazione: int = 0,
    relazione_roma: str = "",
) -> dict:
    """Liquida il danno da perdita del rapporto parentale con il SISTEMA A PUNTI.

    Vigenza: Milano — Osservatorio giustizia civile, tabelle integrate a punti ed. 28/06/2022.
             Roma — Tribunale di Roma, tabella ed. 2025 (valore punto 11.549,20 €).
    Precisione: ESATTO sui parametri oggettivi (eta', convivenza, superstiti, grado di parentela).
    Il parametro discrezionale resta a te: a Milano e' la 'qualita' e intensita' della relazione'
    (0-30 punti), che da sola vale fino a 100.950 € sulla tabella genitori/figli/coniuge.

    Perche' a punti: Cass. 10579/2021 impone una tabella che elenchi le circostanze rilevanti
    (eta' della vittima, eta' del superstite, grado di parentela, convivenza) con i relativi
    punteggi. Le vecchie forbici min-max NON sono piu' un criterio conforme.

    Usa questo quando: richiesta risarcimento iure proprio per morte del congiunto.
    NON usare per: danno biologico del superstite → danno_biologico_micro/macro().
    Chaining: → rivalutazione_monetaria() se la tabella e' di un'annualita' precedente.

    Args:
        eta_vittima: Eta' della vittima primaria (il deceduto) al momento del decesso
        eta_superstite: Eta' del congiunto superstite che chiede il risarcimento
        tabella: 'milano' (default) o 'roma'
        rapporto: SOLO Milano — 'genitore_figlio_coniuge' (include unione civile e convivente
                  di fatto) oppure 'fratello_nipote'
        convivenza: Milano tab. A: 'conviventi' | 'stesso_stabile' | 'non_conviventi'.
                  Milano tab. B: anche 'conviventi_oltre_30_anni' | 'conviventi_oltre_40_anni'.
                  Roma: 'conviventi' o 'non_conviventi'
        superstiti_nucleo: SOLO Milano — quanti altri congiunti del nucleo familiare primario
                  del de cuius sono in vita (0, 1, 2, 3): meno superstiti, piu' punti
        punti_qualita_relazione: SOLO Milano — parametro E, qualita' e intensita' della
                  relazione perduta (0-30). E' il parametro discrezionale: 0 = minimo tabellare
        relazione_roma: SOLO Roma — grado di parentela: genitore, figlio, coniuge, convivente,
                  unione_civile, fratello, avo, nipote, zio, cugino
    """
    tabella = tabella.lower().strip()
    if tabella not in ("milano", "roma"):
        return {"errore": "Tabella non valida: usare 'milano' o 'roma'"}
    if not 0 <= eta_vittima <= 120 or not 0 <= eta_superstite <= 120:
        return {"errore": "Eta' non valida"}

    if tabella == "milano":
        rapporto = rapporto.lower().strip()
        tab = _PARENTALE["milano"].get(rapporto)
        if tab is None:
            return {"errore": "rapporto non valido: 'genitore_figlio_coniuge' o 'fratello_nipote'"}
        if not 0 <= punti_qualita_relazione <= tab["qualita_relazione_max"]:
            return {"errore": f"punti_qualita_relazione deve essere tra 0 e {tab['qualita_relazione_max']}"}

        punti_a, fascia_a = _punti_fascia(tab["eta_vittima_primaria"], eta_vittima)
        punti_b, fascia_b = _punti_fascia(tab["eta_vittima_secondaria"], eta_superstite)

        conv = convivenza.lower().strip()
        if conv not in tab["convivenza"]:
            return {"errore": f"convivenza non valida per questa tabella: {list(tab['convivenza'])}"}
        punti_c = tab["convivenza"][conv]

        chiave_sup = str(min(max(superstiti_nucleo, 0), 3))
        punti_d = tab["superstiti"][chiave_sup]

        punti_totali = punti_a + punti_b + punti_c + punti_d + punti_qualita_relazione
        importo = punti_totali * tab["valore_punto"]
        cap_applicato = importo > tab["cap"]
        if cap_applicato:
            importo = tab["cap"]

        return {
            "tabella": "Milano — Osservatorio giustizia civile, ed. 28/06/2022 (tabelle integrate a punti)",
            "rapporto": rapporto,
            "valore_punto": tab["valore_punto"],
            "punti": {
                "A_eta_vittima": {"eta": eta_vittima, "fascia": fascia_a, "punti": punti_a},
                "B_eta_superstite": {"eta": eta_superstite, "fascia": fascia_b, "punti": punti_b},
                "C_convivenza": {"situazione": conv, "punti": punti_c},
                "D_superstiti_nucleo": {"numero": superstiti_nucleo, "punti": punti_d},
                "E_qualita_relazione": {"punti": punti_qualita_relazione, "max": tab["qualita_relazione_max"]},
            },
            "punti_totali": punti_totali,
            "punti_massimi_attribuibili": tab["punti_attribuibili"],
            "importo_liquidato": round(importo, 2),
            "cap": tab["cap"],
            "cap_applicato": cap_applicato,
            "avvertenza": (
                "Il parametro E (qualita' e intensita' della relazione, 0-30 punti) e' discrezionale e "
                "qui vale quanto indicato: con 0 punti si ottiene il MINIMO tabellare. Il totale non puo' "
                "di regola superare il cap, salvo circostanze eccezionali; contrasti gravi o reati della "
                "vittima secondaria verso la primaria possono ridurre fino ad azzerare l'importo."
            ),
            "riferimento": "Cass. 10579/2021 — sistema a punti obbligatorio per il danno parentale",
        }

    # ---------------- Roma 2025 ----------------
    tab = _PARENTALE["roma"]
    rel = (relazione_roma or "").lower().strip()
    if rel not in tab["relazione"]:
        return {
            "errore": "Per la tabella di Roma serve 'relazione_roma'",
            "valori_ammessi": list(tab["relazione"]),
        }
    punti_rel = tab["relazione"][rel]
    punti_ev, fascia_ev = _punti_fascia(tab["eta_vittima"], eta_vittima)
    punti_ec, fascia_ec = _punti_fascia(tab["eta_congiunto"], eta_superstite)
    conviventi = convivenza.lower().strip() in ("conviventi", "convivenza", "si", "true")
    punti_conv = tab["convivenza"]["convivenza_con_de_cuius"] if conviventi else 0

    punti_totali = punti_rel + punti_ev + punti_ec + punti_conv
    importo = punti_totali * tab["valore_punto"]

    return {
        "tabella": "Roma — Tribunale di Roma, ed. 2025",
        "relazione": rel,
        "valore_punto": tab["valore_punto"],
        "punti": {
            "relazione": punti_rel,
            "eta_vittima": {"eta": eta_vittima, "fascia": fascia_ev, "punti": punti_ev},
            "eta_congiunto": {"eta": eta_superstite, "fascia": fascia_ec, "punti": punti_ec},
            "convivenza": {"conviventi": conviventi, "punti": punti_conv},
        },
        "punti_totali": punti_totali,
        "importo_liquidato": round(importo, 2),
        "correttivi_NON_applicati": [
            "assenza di altri familiari conviventi: +3 punti",
            "assenza di familiari entro il 2^ grado: aumento da 1/3 alla meta' del punteggio complessivo",
            "non convivenza: riduzione fino a 1/2 del punteggio complessivo",
            "punteggio della relazione riducibile fino a 1/2, o azzerabile se manca il vincolo affettivo",
        ],
        "avvertenza": (
            "I correttivi sopra sono rimessi al giudice e NON sono applicati d'ufficio. "
            + tab["_nota_eta_congiunto"]
        ),
        "riferimento": "Cass. 10579/2021 — sistema a punti obbligatorio per il danno parentale",
    }


@mcp.tool(tags={"danni"})
def menomazioni_plurime(
    percentuali: list[float],
) -> dict:
    """Calcola l'invalidità complessiva per menomazioni plurime con la formula Balthazard.
    Vigenza: formula medico-legale standard, recepita dalla prassi giurisprudenziale italiana.
    Precisione: ESATTO (formula matematica deterministica).

    Usa questo quando: il danneggiato presenta più menomazioni distinte da cumulare correttamente.
    NON usare per: una singola menomazione (non serve la formula di riduzione).

    Args:
        percentuali: Lista delle percentuali di invalidità per ciascuna menomazione in ordine decrescente,
                     es. [15, 10, 5]. Ogni valore deve essere compreso tra 0 e 100. Minimo 2 valori.
    """
    if not percentuali or len(percentuali) < 2:
        return {"errore": "Servono almeno 2 percentuali di invalidità"}

    for p in percentuali:
        if p < 0 or p > 100:
            return {"errore": f"Ogni percentuale deve essere tra 0 e 100 (trovato: {p})"}

    # Formula Balthazard: IT = 1 - prodotto(1 - pi/100)
    prodotto = 1.0
    passi = []
    for i, p in enumerate(percentuali):
        fattore = 1 - p / 100
        prodotto *= fattore
        passi.append({
            "menomazione": i + 1,
            "percentuale": p,
            "fattore_residuo": round(fattore, 4),
            "prodotto_parziale": round(prodotto, 6),
        })

    invalidita_complessiva = (1 - prodotto) * 100

    # Somma aritmetica per confronto
    somma_aritmetica = sum(percentuali)

    return {
        "percentuali_input": percentuali,
        "invalidita_complessiva_pct": round(invalidita_complessiva, 2),
        "somma_aritmetica_pct": round(somma_aritmetica, 2),
        "riduzione_pct": round(somma_aritmetica - invalidita_complessiva, 2),
        "formula": "IT = 1 - Π(1 - pi/100) × 100",
        "passi_calcolo": passi,
        "riferimento_normativo": "Formula Balthazard — riduzione proporzionale per invalidità concorrenti",
    }


@mcp.tool(tags={"danni"})
def risarcimento_inail(
    retribuzione_annua: float,
    percentuale_invalidita: float,
    tipo: str = "permanente",
) -> dict:
    """Calcola l'indennizzo INAIL per infortunio sul lavoro o malattia professionale.
    Vigenza: D.Lgs. 38/2000 art. 13 — D.P.R. 1124/1965 TU INAIL — tabelle INAIL vigenti.
    Precisione: INDICATIVO (i coefficienti per la forma capitale sono una semplificazione;
    il valore esatto richiede la tabella INAIL ufficiale per anno e grado di invalidità).

    Usa questo quando: lavoratore infortunato o con malattia professionale riconosciuta dall'INAIL.
    NON usare per: danno biologico civilistico da illecito di terzi → usa danno_biologico_micro/macro().

    Args:
        retribuzione_annua: Retribuzione annua lorda del lavoratore in euro (€)
        percentuale_invalidita: Percentuale di invalidità accertata dall'INAIL (0-100)
        tipo: Tipo di indennizzo: 'permanente' (in capitale se ≤15%, rendita se >15%)
              o 'temporanea' (indennità giornaliera per i giorni di assenza)
    """
    tipo = tipo.lower()
    if tipo not in ("permanente", "temporanea"):
        return {"errore": "tipo deve essere 'permanente' o 'temporanea'"}

    if percentuale_invalidita < 0 or percentuale_invalidita > 100:
        return {"errore": "percentuale_invalidita deve essere tra 0 e 100"}

    if retribuzione_annua < 0:
        return {"errore": "retribuzione_annua non puo essere negativa"}

    if tipo == "temporanea":
        retribuzione_giornaliera = retribuzione_annua / 365
        # Primi 3 giorni: a carico del datore (100%)
        # Dal 4° al 90° giorno: INAIL paga 60%
        # Dal 91° giorno in poi: INAIL paga 75%
        indennita_60 = retribuzione_giornaliera * 0.60
        indennita_75 = retribuzione_giornaliera * 0.75

        return {
            "tipo": "temporanea",
            "retribuzione_annua": retribuzione_annua,
            "retribuzione_giornaliera": round(retribuzione_giornaliera, 2),
            "primi_3_giorni": "A carico del datore di lavoro (100%)",
            "dal_4_al_90_giorno": {
                "percentuale": "60%",
                "indennita_giornaliera": round(indennita_60, 2),
            },
            "dal_91_giorno": {
                "percentuale": "75%",
                "indennita_giornaliera": round(indennita_75, 2),
            },
            "riferimento_normativo": "D.P.R. 1124/1965 — TU INAIL",
        }

    # Permanente
    if percentuale_invalidita < 6:
        return {
            "tipo": "permanente",
            "percentuale_invalidita": percentuale_invalidita,
            "esito": "Nessun indennizzo",
            "nota": "Invalidità inferiore al 6%: nessun indennizzo INAIL erogabile",
            "riferimento_normativo": "D.Lgs. 38/2000 art. 13",
        }

    if percentuale_invalidita <= 15:
        # Indennizzo in capitale (una tantum)
        # Coefficienti indicativi tabelle INAIL
        coefficiente_capitale = 7.0 * percentuale_invalidita  # semplificazione
        indennizzo = retribuzione_annua * (coefficiente_capitale / 100)

        return {
            "tipo": "permanente",
            "forma": "capitale",
            "percentuale_invalidita": percentuale_invalidita,
            "retribuzione_annua": retribuzione_annua,
            "coefficiente_pct": round(coefficiente_capitale, 2),
            "indennizzo_capitale": round(indennizzo, 2),
            "nota": "Invalidità 6-15%: indennizzo in capitale (una tantum). Importo indicativo basato su tabelle INAIL.",
            "riferimento_normativo": "D.Lgs. 38/2000 art. 13 — Tabella indennizzo danno biologico",
        }

    # > 16%: rendita
    quota_biologica = retribuzione_annua * (percentuale_invalidita / 100) * 0.40
    quota_patrimoniale = 0.0
    if percentuale_invalidita > 16:
        quota_patrimoniale = retribuzione_annua * ((percentuale_invalidita - 16) / 100) * 0.60
    rendita_annua = quota_biologica + quota_patrimoniale
    rendita_mensile = rendita_annua / 12

    return {
        "tipo": "permanente",
        "forma": "rendita",
        "percentuale_invalidita": percentuale_invalidita,
        "retribuzione_annua": retribuzione_annua,
        "quota_danno_biologico": round(quota_biologica, 2),
        "quota_danno_patrimoniale": round(quota_patrimoniale, 2),
        "rendita_annua": round(rendita_annua, 2),
        "rendita_mensile": round(rendita_mensile, 2),
        "nota": "Invalidità >16%: rendita diretta. Composta da quota biologica + quota patrimoniale.",
        "riferimento_normativo": "D.Lgs. 38/2000 art. 13 — Rendita per danno biologico e patrimoniale",
    }


@mcp.tool(tags={"danni"})
def danno_non_patrimoniale(
    percentuale_invalidita: int,
    eta_vittima: int,
    tipo_danno: str = "biologico",
    giorni_itt: int = 0,
    spese_mediche: float = 0,
    danno_morale_pct: float = 0,
    danno_esistenziale_pct: float = 0,
) -> dict:
    """Calcola il danno non patrimoniale complessivo con tutte le componenti in un unico prospetto.

    Combina automaticamente danno biologico (micro se ≤9%, macro se ≥10%), danno morale
    (personalizzazione), danno esistenziale e patrimoniale emergente (spese mediche + ITT).
    Vigenza: art. 138-139 Cod. Assicurazioni; Tabelle Milano 2024; Cass. SU 26972/2008.
    Precisione: INDICATIVO (il danno biologico macro è interpolato; la personalizzazione
    morale ed esistenziale è soggetta a valutazione giudiziale discrezionale).

    Usa questo quando: vuoi un prospetto completo di tutte le componenti del danno non patrimoniale.
    NON usare per: solo danno biologico micro → usa danno_biologico_micro() (più dettagliato).
    NON usare per: solo danno biologico macro → usa danno_biologico_macro().
    NON usare per: danno da perdita del rapporto parentale → usa danno_parentale().
    Chaining: → rivalutazione_monetaria() per attualizzare → interessi_legali() per gli interessi compensativi

    Args:
        percentuale_invalidita: Percentuale di invalidità permanente (1-100)
        eta_vittima: Età della vittima al momento del sinistro (0-120)
        tipo_danno: Voce principale richiesta: 'biologico', 'morale', 'esistenziale', 'patrimoniale_emergente'
        giorni_itt: Giorni di invalidità temporanea totale al 100%
        spese_mediche: Spese mediche documentate in euro (€)
        danno_morale_pct: Percentuale di personalizzazione per danno morale (0-50)
        danno_esistenziale_pct: Percentuale di personalizzazione per danno esistenziale (0-50)
    """
    if not 1 <= percentuale_invalidita <= 100:
        return {"errore": "Percentuale invalidità deve essere tra 1 e 100"}

    if danno_morale_pct < 0 or danno_morale_pct > 50:
        return {"errore": "danno_morale_pct deve essere tra 0 e 50"}

    if danno_esistenziale_pct < 0 or danno_esistenziale_pct > 50:
        return {"errore": "danno_esistenziale_pct deve essere tra 0 e 50"}

    if giorni_itt < 0:
        return {"errore": "giorni_itt non puo essere negativo"}

    if spese_mediche < 0:
        return {"errore": "spese_mediche non puo essere negativo"}

    # Calcolo componente biologica (micro o macro)
    if percentuale_invalidita <= 9:
        punto_base = _MICRO["punto_base"]
        coefficienti = _MICRO["coefficienti_punto"]
        eta_inizio_decremento = _MICRO["eta_decremento_da"]
        decremento_pct = _MICRO["decremento_eta_pct_per_anno"]

        if eta_vittima >= eta_inizio_decremento:
            anni_sopra = eta_vittima - eta_inizio_decremento
            riduzione = max(1 - (decremento_pct / 100) * anni_sopra, 0)
        else:
            riduzione = 1.0

        danno_biologico = 0.0
        for p in range(1, percentuale_invalidita + 1):
            danno_biologico += punto_base * coefficienti[str(p)] * riduzione

        tipo_calcolo = "micropermanenti (art. 139)"
    else:
        punto_base = _interpola_punto_base(percentuale_invalidita)
        coeff_eta = _coefficiente_eta(eta_vittima)
        danno_biologico = punto_base * percentuale_invalidita * coeff_eta
        tipo_calcolo = "macropermanenti (art. 138)"

    # ITT
    itt_giornaliero = _MICRO["invalidita_temporanea_totale_giornaliera"]
    danno_itt = giorni_itt * itt_giornaliero

    # Componente morale
    danno_morale = danno_biologico * (danno_morale_pct / 100)

    # Componente esistenziale
    danno_esistenziale = danno_biologico * (danno_esistenziale_pct / 100)

    # Patrimoniale emergente
    danno_patrimoniale = spese_mediche + danno_itt

    totale = danno_biologico + danno_morale + danno_esistenziale + danno_patrimoniale

    return {
        "percentuale_invalidita": percentuale_invalidita,
        "eta_vittima": eta_vittima,
        "voce_principale_richiesta": tipo_danno,
        "tipo_calcolo": tipo_calcolo,
        "componenti": {
            "danno_biologico": round(danno_biologico, 2),
            "danno_morale": {
                "personalizzazione_pct": danno_morale_pct,
                "importo": round(danno_morale, 2),
            },
            "danno_esistenziale": {
                "personalizzazione_pct": danno_esistenziale_pct,
                "importo": round(danno_esistenziale, 2),
            },
            "danno_patrimoniale_emergente": {
                "spese_mediche": round(spese_mediche, 2),
                "itt": {"giorni": giorni_itt, "importo": round(danno_itt, 2)},
                "totale": round(danno_patrimoniale, 2),
            },
        },
        "totale_risarcimento": round(totale, 2),
        "riferimento_normativo": "Art. 138-139 Cod. Assicurazioni; Tabelle Milano 2024; Cass. SU 26972/2008",
    }


@mcp.tool(tags={"danni"})
def equo_indennizzo(
    categoria_tabella: str,
    percentuale_invalidita: float,
    stipendio_annuo: float,
) -> dict:
    """Calcola l'equo indennizzo per causa di servizio per dipendenti pubblici (istituto abrogato).

    ATTENZIONE: Istituto ABROGATO per eventi successivi al 06/12/2011
    (art. 6 DL 201/2011 conv. L. 214/2011 — Riforma Fornero). Il calcolo resta valido
    esclusivamente per pratiche relative a fatti anteriori a tale data.

    Vigenza: DPR 834/1981 Tabella A — applicabile solo a fatti anteriori al 06/12/2011.
    Precisione: INDICATIVO (coefficienti tabellari semplificati; il calcolo esatto
    dipende dalla specifica categoria e dalla delibera della CMO).

    Usa questo quando: dipendente pubblico con infermità da causa di servizio anteriore al 06/12/2011.
    NON usare per: eventi successivi al 06/12/2011 (istituto abrogato).
    NON usare per: lavoratori privati infortunati → usa risarcimento_inail().

    Args:
        categoria_tabella: Categoria dalla Tabella A DPR 834/1981 ('1' = 81-100%, '8' = 1-10%)
        percentuale_invalidita: Percentuale di invalidità accertata dalla CMO (0-100)
        stipendio_annuo: Ultimo stipendio annuo lordo in euro (€)
    """
    coefficienti = {
        "1": {"range": "81-100%", "coefficiente": 8.0, "pensione_privilegiata": True},
        "2": {"range": "61-80%", "coefficiente": 6.5, "pensione_privilegiata": True},
        "3": {"range": "51-60%", "coefficiente": 5.0, "pensione_privilegiata": True},
        "4": {"range": "41-50%", "coefficiente": 4.0, "pensione_privilegiata": True},
        "5": {"range": "31-40%", "coefficiente": 3.0, "pensione_privilegiata": True},
        "6": {"range": "21-30%", "coefficiente": 2.5, "pensione_privilegiata": False},
        "7": {"range": "11-20%", "coefficiente": 1.5, "pensione_privilegiata": False},
        "8": {"range": "1-10%", "coefficiente": 0.7, "pensione_privilegiata": False},
    }

    cat = str(categoria_tabella).strip()
    if cat not in coefficienti:
        return {"errore": f"Categoria non valida. Valori ammessi: 1-8 (trovato: {categoria_tabella})"}

    if percentuale_invalidita < 0 or percentuale_invalidita > 100:
        return {"errore": "percentuale_invalidita deve essere tra 0 e 100"}

    if stipendio_annuo < 0:
        return {"errore": "stipendio_annuo non puo essere negativo"}

    info = coefficienti[cat]
    base = stipendio_annuo * info["coefficiente"] * (percentuale_invalidita / 100)
    indennizzo = round(base, 2)

    result = {
        "categoria_tabella": cat,
        "range_invalidita": info["range"],
        "percentuale_invalidita": percentuale_invalidita,
        "stipendio_annuo": stipendio_annuo,
        "coefficiente": info["coefficiente"],
        "equo_indennizzo": indennizzo,
        "pensione_privilegiata": info["pensione_privilegiata"],
    }

    if info["pensione_privilegiata"]:
        result["nota_pensione"] = (
            "Categoria 1ª-5ª: diritto a pensione privilegiata se cessazione dal servizio per infermità"
        )

    result["attenzione"] = (
        "Istituto ABROGATO per eventi successivi al 06/12/2011 "
        "(art. 6 DL 201/2011 conv. L. 214/2011 — Riforma Fornero). "
        "Il calcolo è valido solo per pratiche relative a fatti anteriori a tale data."
    )
    result["riferimento_normativo"] = "DPR 461/2001; DPR 834/1981 — Tabella A. Abrogato per nuovi eventi da art. 6 DL 201/2011 (L. 214/2011)"
    return result
