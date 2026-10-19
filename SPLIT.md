# Split del 2026-10-18 — cosa è stato tolto e dove ritrovarlo

Questo repository è stato ridotto alla sola giurisprudenza della Corte di Cassazione
(Italgiure): 8 tool, 2 prompt, 1 risorsa. Qui sotto c'è l'inventario completo di ciò che
è stato rimosso, pensato come base per il **progetto parallelo** che raccoglierà il resto.

Niente è andato perso. Lo stato completo, prima dello split, è il commit **`64f288d`** (genitore del
commit di split, quindi sempre raggiungibile dalla storia di `main`), "Memoria che cresceva: sessioni mai chiuse e picchi della Consulta":

```bash
# nuovo progetto parallelo partendo dallo stato completo del fork
git clone https://github.com/cybermerlo/icodici-cassazione mcp-legal-it-strumenti
cd mcp-legal-it-strumenti && git switch -c strumenti 64f288d
```

---

## 1. Cosa resta qui

| Modulo | Tool |
|---|---|
| `tools/italgiure.py` | `cerca_giurisprudenza`, `leggi_sentenza`, `giurisprudenza_su_norma`, `giurisprudenza_articolo`, `ultime_pronunce` |
| `tools/orientamento.py` | `orientamento_su_norma`, `orientamento_su_principio`, `mappa_orientamento` |

Prompt: `analisi_giurisprudenziale`, `orientamento_giurisprudenziale`.
Risorsa: `legal://riferimenti/ricerca-giurisprudenziale`.
Librerie: `lib/italgiure`, `lib/brocardi`, `lib/visualex/map.py` + `models.py` (solo il resolver
dei nomi degli atti), `lib/_http.py`, `_paging.py`, `_cache.py`, `_sources.py`, `_result.py`.

Tre strumenti che toccano anche la Cassazione sono stati **tolti**, perché dipendono da fonti
che non sono più qui. `verifica_citazioni` verifica norme e sentenze insieme e si appoggia a
`cite_law`. `cerca_giurisprudenza_unificata` interroga in parallelo Italgiure, CeRDEF, TAR/CdS e
CGUE. `cerca_brocardi` restituisce ratio, spiegazione e massime di un articolo. Se servono
nel progetto parallelo, possono chiamare questo server come connettore separato.

---

## 2. Tool rimossi (210)

### Consultazione normativa e fonti ufficiali

| Modulo | Tag | Tool |
|---|---|---|
| `legal_citations.py` | normativa | `cite_law`, `fetch_law_article`, `fetch_law_annotations`, `cerca_brocardi`, `fetch_act_index`, `fetch_full_act`, `download_law_pdf`, `verifica_citazioni` |
| `gazzetta.py` | normativa | `cerca_gazzetta_ufficiale`, `leggi_atto_gazzetta`, `sommario_gazzetta`, `ultime_gazzette`, `scarica_pdf_gazzetta` |
| `eu_implementation.py` | normativa, giurisprudenza_ue | `get_italian_implementation`, `get_eu_basis`, `elenco_misure_nazionali` |
| `consob.py` | consob | `cerca_delibere_consob`, `leggi_delibera_consob`, `ultime_delibere_consob` |
| `gpdp.py` | privacy | `cerca_provvedimenti_garante`, `leggi_provvedimento_garante`, `ultimi_provvedimenti_garante` |

### Altre giurisdizioni

| Modulo | Tag | Tool |
|---|---|---|
| `corte_cost.py` | costituzionale, giurisprudenza | `cerca_pronuncia_costituzionale`, `leggi_pronuncia_costituzionale`, `pronunce_cost_su_norma`, `ultime_pronunce_cost` |
| `cerdef.py` | fiscale, giurisprudenza | `cerca_giurisprudenza_tributaria`, `cerdef_leggi_provvedimento`, `ultime_sentenze_tributarie` |
| `giustizia_amm.py` | giurisprudenza_amm | `cerca_giurisprudenza_amministrativa`, `leggi_provvedimento_amm`, `giurisprudenza_amm_su_norma`, `ultimi_provvedimenti_amm` |
| `cgue.py` | giurisprudenza_ue | `cerca_giurisprudenza_cgue`, `leggi_sentenza_cgue`, `giurisprudenza_cgue_su_norma`, `ultime_sentenze_cgue` |
| `giurisprudenza_unificata.py` | giurisprudenza (+ altre) | `cerca_giurisprudenza_unificata` |

### Calcoli, atti e studio

| Modulo | Tag | Tool |
|---|---|---|
| `rivalutazioni_istat.py` (12) | rivalutazione | `rivalutazione_monetaria`, `rivalutazione_mensile`, `adeguamento_canone_locazione`, `calcolo_inflazione`, `rivalutazione_tfr`, `interessi_vari_capitale_rivalutato`, `lettera_adeguamento_canone`, `calcolo_devalutazione`, `rivalutazione_storica`, `variazioni_istat`, `rivalutazione_annuale_media`, `inflazione_titoli_stato` |
| `tassi_interessi.py` (10) | interessi | `interessi_legali`, `interessi_mora`, `interessi_tasso_fisso`, `calcolo_ammortamento`, `verifica_usura`, `interessi_acconti`, `calcolo_maggior_danno`, `interessi_corso_causa`, `calcolo_surroga_mutuo`, `calcolo_taeg` |
| `scadenze_termini.py` (11) | scadenze | `scadenza_processuale`, `termini_processuali_civili`, `termini_separazione_divorzio`, `scadenze_impugnazioni`, `scadenze_multe`, `termini_memorie_repliche`, `termini_procedimento_semplificato`, `termini_183_190_cpc`, `termini_esecuzioni`, `termini_deposito_atti_appello`, `termini_deposito_ctu` |
| `atti_giudiziari.py` (23) | giudiziario, credito | `contributo_unificato`, `diritti_copia`, `pignoramento_stipendio`, `sollecito_pagamento`, `decreto_ingiuntivo`, `calcolo_hash`, `tassazione_atti`, `copie_processo_tributario`, `note_iscrizione_ruolo`, `codici_iscrizione_ruolo`, `fascicolo_di_parte`, `procura_alle_liti`, `attestazione_conformita`, `relata_notifica_pec`, `indice_documenti`, `note_trattazione_scritta`, `sfratto_morosita`, `atto_di_precetto`, `nota_precisazione_credito`, `dichiarazione_553_cpc`, `testimonianza_scritta`, `istanza_visibilita_fascicolo`, `cerca_ufficio_giudiziario` |
| `procedura_civile.py` (3) | giudiziario | `competenza_giudice`, `verifica_mediazione_obbligatoria`, `gratuito_patrocinio` |
| `fatturazione_avvocati.py` (12) | parcelle_avv | `parcella_avvocato_civile`, `parcella_avvocato_penale`, `parcella_stragiudiziale`, `parcella_volontaria_giurisdizione`, `preventivo_volontaria_giurisdizione`, `fattura_avvocato`, `nota_spese`, `preventivo_civile`, `preventivo_stragiudiziale`, `spese_trasferta_avvocati`, `modello_notula`, `calcolo_notula_penale` |
| `parcelle_professionisti.py` (11) | parcelle_prof | `fattura_professionista`, `compenso_ctu`, `spese_mediazione`, `compenso_orario`, `ritenuta_acconto`, `compenso_curatore_fallimentare`, `compenso_delegati_vendite`, `compenso_mediatore_familiare`, `fattura_enasarco`, `ricevuta_prestazione_occasionale`, `tariffe_mediazione` |
| `risarcimento_danni.py` (7) | danni | `danno_biologico_micro`, `danno_biologico_macro`, `danno_parentale`, `menomazioni_plurime`, `risarcimento_inail`, `danno_non_patrimoniale`, `equo_indennizzo` |
| `diritto_penale.py` (5) | penale | `aumenti_riduzioni_pena`, `conversione_pena`, `fine_pena`, `prescrizione_reato`, `pena_concordata` |
| `diritto_lavoro.py` (6) | lavoro | `indennita_licenziamento`, `indennita_preavviso`, `calcolo_naspi`, `scadenze_licenziamento`, `costo_lavoro`, `offerta_conciliativa` |
| `diritto_societario.py` (4) | societario | `quorum_assembleari`, `soglie_organo_controllo_srl`, `scadenze_societarie`, `costi_costituzione` |
| `crisi_impresa.py` (4) | crisi_impresa | `test_crisi_impresa`, `composizione_negoziata`, `concordato_preventivo`, `compenso_occ` |
| `proprieta_successioni.py` (12) | proprieta | `calcolo_eredita`, `imposte_successione`, `calcolo_usufrutto`, `calcolo_imu`, `imposte_compravendita`, `pensione_reversibilita`, `grado_parentela`, `calcolo_valore_catastale`, `calcolo_superficie_commerciale`, `cedolare_secca`, `imposta_registro_locazioni`, `spese_condominiali` |
| `dichiarazione_redditi.py` (16) | fiscale | `calcolo_irpef`, `regime_forfettario`, `calcolo_tfr`, `ravvedimento_operoso`, `assegno_unico`, `detrazione_figli`, `detrazione_coniuge`, `detrazione_altri_familiari`, `detrazione_lavoro_dipendente`, `detrazione_pensione`, `detrazione_assegno_coniuge`, `detrazione_canone_locazione`, `acconto_irpef`, `acconto_cedolare_secca`, `rateizzazione_imposte`, `cerca_codice_tributo` |
| `investimenti.py` (5) | investimenti | `rendimento_bot`, `rendimento_btp`, `pronti_termine`, `rendimento_buoni_postali`, `confronto_investimenti` |
| `varie.py` (12) | utility | `codice_fiscale`, `decodifica_codice_fiscale`, `verifica_iban`, `conta_giorni`, `scorporo_iva`, `decurtazione_punti_patente`, `tasso_alcolemico`, `prescrizione_diritti`, `calcolo_tempo_trascorso`, `verifica_partita_iva`, `calcolo_eta_anagrafica`, `ricerca_codici_ateco` |
| `privacy_gdpr.py` (12) | privacy | `genera_informativa_privacy`, `genera_informativa_cookie`, `genera_informativa_dipendenti`, `genera_informativa_videosorveglianza`, `genera_dpa`, `genera_registro_trattamenti`, `genera_dpia`, `analisi_base_giuridica`, `verifica_necessita_dpia`, `valutazione_data_breach`, `calcolo_sanzione_gdpr`, `genera_notifica_data_breach` |
| `analisi_fornitori.py` (2) | privacy, utility | `verifica_partita_iva_vies`, `genera_report_fornitori` |
| `modelli_atti.py` (3) | atti | `genera_modello_atto`, `esporta_atto_docx`, `lista_categorie_atti` |
| `procure_quotazioni.py` (2) | atti, credito | `genera_procura_liti_docx`, `genera_quotazione_docx` |

---

## 3. Prompt, risorse, dati

**Prompt rimossi (21)**: `analisi_sinistro`, `recupero_credito`, `causa_civile`,
`pianificazione_successione`, `parere_legale`, `quantificazione_danni`, `calcolo_parcella`,
`verifica_prescrizione`, `ricerca_normativa`, `analisi_articolo`, `confronto_norme`,
`mappatura_normativa`, `analisi_delibere_consob`, `novita_consob`, `analisi_tributaria`,
`analisi_giurisprudenza_europea`, `compliance_privacy`, `analisi_giurisprudenza_amministrativa`,
`analisi_costituzionale`, `ricerca_gazzetta`, `attuazione_direttiva`.

**Risorse rimosse (14)**, tutte sotto `legal://riferimenti/`: `procedura-civile`,
`termini-processuali`, `contributo-unificato`, `irpef-detrazioni`, `interessi-legali`,
`checklist-decreto-ingiuntivo`, `fonti-diritto-italiano`, `codici-e-leggi-principali`,
`gdpr-checklist`, `consob-delibere`, `cerdef-giurisprudenza`, `modelli-atti-catalogo`,
`giustizia-amministrativa`, `cgue-giurisprudenza`.

**Librerie rimosse** (`plugin/server/src/lib/`): `cerdef`, `cgue`, `consob`, `corte_cost`,
`eu_implementation`, `gazzetta`, `giustizia_amm`, `gpdp`, `vies`, `visualex/scraper.py`,
`visualex/akn_fetch.py`, `visualex/akn_parser.py`, `_data.py`, `_egress.py`.

**Dati** (`plugin/server/src/data/`, 24 JSON): `codici_ateco`, `codici_ruolo`, `codici_tributo`,
`comuni`, `contributo_unificato`, `festivita`, `gdpr_basi_giuridiche`, `gdpr_dpia_criteri`,
`gdpr_sanzioni`, `imposte_successione`, `indici_foi`, `irpef_scaglioni`,
`mediazione_obbligatoria`, `modelli_atti`, `parametri_forensi`, `preavviso_ccnl`,
`tabella_danno_bio`, `tabella_milano_roma`, `tassi_legali`, `tassi_mora`, `tegm`,
`tribunali_competenti`, `usufrutto_coefficienti`, `violazioni_patente`.

---

## 4. Plugin, packaging, documentazione, test

**Plugin Claude** (`plugin/`): 23 skill (`analisi-articolo`, `analisi-delibere-consob`,
`analisi-fornitori`, `analisi-giurisprudenziale`, `analisi-sinistro`, `calcolo-parcella`,
`causa-civile`, `compliance-privacy`, `confronto-norme`, `cookie-audit`, `data-breach`,
`esporta-documento`, `genera-atto`, `mappatura-normativa`, `novita-consob`, `parere-legale`,
`pianificazione-successione`, `procure-quotazioni`, `quantificazione-danni`, `recupero-credito`,
`redazione-contratto`, `ricerca-normativa`, `verifica-prescrizione`); 8 comandi (`codice-fiscale`,
`digest`, `interessi`, `norma`, `privacy`, `release`, `scadenza`, `sentenza`); 6 agenti
(`civilista`, `digest-giuridico`, `penalista`, `privacy-specialist`, `redattore-atti`,
`ricerca-giurisprudenziale`); l'hook `citation-gate.py`; `dist/web-skills`, `build-web-skills.py`,
`start_server.sh`, `.claude-plugin/plugin.json`, `.mcp.json`, `settings.json`, README, CHANGELOG e
LICENSE del plugin. La skill `analisi-giurisprudenziale`, il comando `sentenza` e l'agente
`ricerca-giurisprudenziale` riguardano la Cassazione ma presuppongono `cite_law` e il plugin:
qui li sostituiscono i 2 prompt e la risorsa.

**Packaging e release**: `.claude-plugin/marketplace.json`, `dxt/` (Desktop Extension .mcpb),
`plugin/server/manifest.json`, `plugin/server/pyproject.toml`, `plugin/server/.mcpbignore`,
`install.py`, `release.py`, `.mcp.json.example`, `.github/workflows/release.yml`,
`.github/workflows/data-freshness.yml`.

**Script** (`scripts/`): `build-all.sh`, `build-dxt.sh`, `build-plugin.sh`, `check_deps_sync.py`,
`generate_atti_denominati.py`, `refresh_data.py`, `update-data.py`,
`verifica-parametri-forensi.py` (riscontro automatico dei 269 valori del DM 55/2014).

**Documentazione**: `docs/` per intero (architettura, catalogo dei tool, data files, deploy,
plugin, prompt e risorse, testing, specs, audit, `dm55-2014-tabelle-ufficiali.txt`),
`CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `benchmarks/akn_vs_html.py`.

**Test**: `tests/comparison/` (32 file con valori numerici attesi), `tests/fixtures/akn/`,
`tests/test-queries.md` e 44 file di `tests/unit/` dei moduli rimossi. Da quelli tenuti sono stati
tolti solo i casi che chiamavano `cite_law`, `cerca_brocardi` o lo scraper Normattiva.

**Dipendenze** tolte da `pyproject.toml`: `fpdf2`, `python-docx`, `openpyxl`, `playwright`.

---

## 5. Per il progetto parallelo: cosa portarsi dietro

**Le correzioni del fork che l'upstream non ha**, documentate in `STUDIO.md` §§ 5-6 della
versione `64f288d`. Il risarcimento danni ha la formula delle micropermanenti, i valori del
DM 2026, il tetto del 30% dell'art. 138 e le tabelle parentali a punti di Milano e Roma,
oltre all'unitarietà del danno non patrimoniale. I compensi forensi hanno 18 tabelle del
DM 55/2014 invece di una sola, le variazioni dell'art. 4 e il riscontro automatico dei
valori. Ci sono poi le avvertenze di Cassazione dentro `interessi_legali` e
`rivalutazione_monetaria` (SS.UU. 1712/1995). L'ultima è la correzione di memoria della
Corte costituzionale (§ 8.2, `_iter_decade`). Anche `serve_studio.py`, il pin di FastMCP 2.x
e il `Dockerfile` per Coolify servono a entrambi i progetti.

**Le novità dell'upstream** (capazme, v2.12.1 → v2.16.0, 474 commit) da valutare per le
parti rimosse. Attenzione: l'upstream ha riscritto la storia git, quindi un merge diretto
non funziona e il confronto va fatto file per file.

| Versione | Novità |
|---|---|
| 2.16.0 | skill `cookie-audit`: pixel di tracciamento e newsletter (linee guida Garante, provv. 284/2026) |
| 2.15.3 | `cite_law` non serve più l'art. 1 al posto di un articolo inesistente; `verifica_citazioni` distingue *inesistente* da *non verificata* |
| 2.15.2 | allegati degli atti (es. D.Lgs. 36/2023) non scambiati con il corpo; lettura a pagine `da_carattere` per tutti i tool di lettura; ricerca alla Consulta dichiara l'anno coperto |
| 2.15.0 | benchmark su 115 tool contro le fonti ufficiali, con correzioni su scadenze, contributo unificato, compensi, imposte, immobili, danni, interessi, rivalutazione, penale, lavoro, crisi d'impresa, societario e privacy; flag `Regime: PREVIGENTE` |
| 2.14.x | CeRDEF riletto sul portale nuovo (#46); `stato_server` (diagnostica); `server.json` per l'MCP Registry; `LEGAL_PROFILE` di nuovo funzionante con FastMCP 3; marchi TMview; `verifica_dpa_fornitore`; registro dei rifiuti e `verbale_mensile`; provenienza delle fonti online in ogni risposta; tabelle riconciliate con le fonti (contributo unificato, imposte di successione, patente, comuni, codici ruolo, preavvisi CCNL) e `backlog_riconciliazione`; cache disattivabile |
| 2.13.0 | fonti parlamentari: `cerca_ddl`, `iter_ddl`, `ddl_su_norma` (Senato e Camera) |
| nuovi tool | `verifica_dpa_fornitore`; Parlamento (`cerca_ddl`, `iter_ddl`, `ddl_su_norma`); marchi TMview (`cerca_marchi`, `leggi_marchio`, `verifica_anteriorita_marchio`); `verbale_mensile`, `backlog_riconciliazione`, `stato_server` |

Attenzione al benchmark della 2.15.0, che tocca anche danni e compensi: va confrontato con
le correzioni del fork prima di accettarlo, perché le due versioni sono divergenti sugli
stessi file (`risarcimento_danni.py`, `fatturazione_avvocati.py`, `parametri_forensi.json`,
`tabella_danno_bio.json`, `tabella_milano_roma.json`).
