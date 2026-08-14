"""Arithmetic verification tests for Sezione 7 — Risarcimento Danni."""

from tests.comparison.conftest import assert_close


def _call(fn_name, **kwargs):
    import importlib
    mod = importlib.import_module("src.tools.risarcimento_danni")
    fn = getattr(mod, fn_name)
    fn = getattr(fn, "fn", fn)
    return fn(**kwargs)


class TestMenomazioniPlurime:

    def test_balthazard_15_10(self):
        r = _call("menomazioni_plurime", percentuali=[15, 10])
        # IT = 1 - (1-0.15)*(1-0.10) = 1 - 0.85*0.90 = 1 - 0.765 = 0.235 → 23.5%
        assert_close(r["invalidita_complessiva_pct"], 23.5, tolerance=0.01, label="balth_15_10")
        assert_close(r["somma_aritmetica_pct"], 25.0, tolerance=0.01, label="balth_somma")

    def test_balthazard_20_10_5(self):
        r = _call("menomazioni_plurime", percentuali=[20, 10, 5])
        # IT = 1 - 0.80*0.90*0.95 = 1 - 0.684 = 0.316 → 31.6%
        expected = (1 - 0.80 * 0.90 * 0.95) * 100
        assert_close(r["invalidita_complessiva_pct"], round(expected, 2), tolerance=0.01, label="balth_3")

    def test_riduzione_vs_somma(self):
        r = _call("menomazioni_plurime", percentuali=[30, 20])
        assert r["invalidita_complessiva_pct"] < r["somma_aritmetica_pct"]


class TestDannoBiologicoMacro:

    def test_50pct_40anni(self):
        r = _call("danno_biologico_macro", percentuale_invalidita=50, eta_vittima=40)
        assert r["danno_base"] > 0
        assert r["percentuale_invalidita"] == 50

    def test_tetto_personalizzazione_30_pct(self):
        """Art. 138 c. 3: aumento fino al 30%. Il tetto del 50% era fuori legge."""
        r = _call("danno_biologico_macro", percentuale_invalidita=30, eta_vittima=35,
                   personalizzazione_pct=31)
        assert "errore" in r

    def test_avvertenza_stima(self):
        """Il risultato deve dichiarare che e' una stima, non una liquidazione."""
        r = _call("danno_biologico_macro", percentuale_invalidita=50, eta_vittima=40)
        assert "avvertenza" in r and "STIMA" in r["avvertenza"]

    def test_personalizzazione(self):
        r_base = _call("danno_biologico_macro", percentuale_invalidita=30, eta_vittima=35,
                        personalizzazione_pct=0)
        r_pers = _call("danno_biologico_macro", percentuale_invalidita=30, eta_vittima=35,
                        personalizzazione_pct=30)
        assert r_pers["totale_risarcimento"] > r_base["totale_risarcimento"]
        expected_magg = r_base["danno_base"] * 30 / 100
        assert_close(r_pers["maggiorazione_morale"], round(expected_magg, 2), tolerance=0.01, label="macro_pers")


class TestDannoParentale:
    """Milano 2022 — validati sugli esempi ufficiali dell'Osservatorio (Allegato 1 del PDF).

    L'esempio 5 nell'ipotesi media riporta 285.025,00 €, ma 85 punti x 3.365,00 = 286.025,00:
    e' un refuso della fonte, dimostrato dagli altri due valori dello stesso esempio
    (70 punti -> 235.550,00 e 100 punti -> 336.500,00, entrambi coerenti). Qui si usa
    l'aritmetica, non il numero stampato.
    """

    ESEMPI = [
        # (eta_vittima, eta_superstite, convivenza, superstiti, punti_E, atteso)
        (15, 45, "conviventi", 2, 0, 249010.00),
        (15, 45, "conviventi", 2, 15, 299485.00),
        (15, 45, "conviventi", 2, 30, 336500.00),   # cap
        (10, 39, "conviventi", 0, 0, 275930.00),
        (10, 39, "conviventi", 0, 15, 326405.00),
        (45, 68, "non_conviventi", 2, 0, 161520.00),
        (45, 68, "non_conviventi", 2, 15, 211995.00),
        (45, 68, "non_conviventi", 2, 30, 262470.00),
        (80, 85, "conviventi", 1, 0, 168250.00),
        (80, 85, "conviventi", 1, 15, 218725.00),
        (80, 85, "conviventi", 1, 30, 269200.00),
        (48, 49, "conviventi", 1, 0, 235550.00),
        (48, 49, "conviventi", 1, 30, 336500.00),
    ]

    def test_esempi_ufficiali_milano(self):
        for eta_v, eta_s, conv, sup, punti_e, atteso in self.ESEMPI:
            r = _call("danno_parentale", eta_vittima=eta_v, eta_superstite=eta_s,
                      tabella="milano", convivenza=conv, superstiti_nucleo=sup,
                      punti_qualita_relazione=punti_e)
            assert_close(r["importo_liquidato"], atteso, tolerance=0.01,
                         label=f"milano_{eta_v}_{eta_s}_E{punti_e}")

    def test_cap_milano(self):
        r = _call("danno_parentale", eta_vittima=10, eta_superstite=39,
                  tabella="milano", convivenza="conviventi", superstiti_nucleo=0,
                  punti_qualita_relazione=30)
        assert r["cap_applicato"] is True
        assert r["importo_liquidato"] == 336500.00

    def test_fratello_nipote_valore_punto(self):
        r = _call("danno_parentale", eta_vittima=30, eta_superstite=35,
                  tabella="milano", rapporto="fratello_nipote",
                  convivenza="conviventi", superstiti_nucleo=1)
        # A=18 (21-30) + B=16 (31-40) + C=20 (conviventi) + D=14 (1 superstite) = 68 punti
        assert r["punti_totali"] == 68
        assert_close(r["importo_liquidato"], round(68 * 1461.20, 2), tolerance=0.01,
                     label="milano_fratelli")

    def test_roma_2025(self):
        r = _call("danno_parentale", eta_vittima=15, eta_superstite=45,
                  tabella="roma", relazione_roma="figlio", convivenza="conviventi")
        # relazione figlio 18 + eta vittima 11-20 = 4,5 + eta congiunto 41-50 = 3 + convivenza 4
        assert_close(r["punti_totali"], 29.5, tolerance=0.001, label="roma_punti")
        assert_close(r["importo_liquidato"], round(29.5 * 11549.20, 2), tolerance=0.01,
                     label="roma_importo")

    def test_roma_richiede_relazione(self):
        r = _call("danno_parentale", eta_vittima=15, eta_superstite=45, tabella="roma")
        assert "errore" in r


class TestDannoBiologicoMicro:
    """Art. 139 CdA — DM 20 luglio 2026 (GU 28/07/2026 n. 173): primo punto 988,45 €.

    Formula: punto_base x coefficiente(N) x N punti x (1 - 0,005 x (eta - 10)).
    NON la somma dei valori dei singoli punti (errore corretto il 2026-08-14).
    """

    BASE = 988.45
    COEFF = {1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3, 5: 1.5, 6: 1.7, 7: 1.9, 8: 2.1, 9: 2.3}

    def _atteso(self, p, eta):
        rid = 1 - 0.005 * max(0, eta - 10)
        return round(self.BASE * self.COEFF[p] * p * rid, 2)

    def test_formula_moltiplicativa(self):
        for p in range(1, 10):
            for eta in (5, 20, 40, 75):
                r = _call("danno_biologico_micro", percentuale_invalidita=p, eta_vittima=eta)
                assert_close(r["danno_permanente"], self._atteso(p, eta), tolerance=0.01,
                             label=f"micro_{p}pct_{eta}anni")

    def test_non_e_la_somma_dei_punti(self):
        """La vecchia formula sommava i punti: sul 9% dava circa un terzo in meno."""
        r = _call("danno_biologico_micro", percentuale_invalidita=9, eta_vittima=40)
        somma_vecchia = sum(self.BASE * self.COEFF[x] for x in range(1, 10)) * 0.85
        assert r["danno_permanente"] > somma_vecchia * 1.3

    def test_nessuna_riduzione_sotto_11_anni(self):
        r5 = _call("danno_biologico_micro", percentuale_invalidita=5, eta_vittima=5)
        r10 = _call("danno_biologico_micro", percentuale_invalidita=5, eta_vittima=10)
        assert r5["riduzione_eta"] == 1.0
        assert r10["riduzione_eta"] == 1.0

    def test_inabilita_temporanea(self):
        r = _call("danno_biologico_micro", percentuale_invalidita=1, eta_vittima=30,
                  giorni_itt=10, giorni_itp50=20)
        assert_close(r["danno_temporaneo"]["itt"]["importo"], round(10 * 57.64, 2),
                     tolerance=0.01, label="itt")
        assert_close(r["danno_temporaneo"]["itp_50"]["importo"], round(20 * 28.82, 2),
                     tolerance=0.01, label="itp50")

    def test_personalizzazione_max_20(self):
        r = _call("danno_biologico_micro", percentuale_invalidita=5, eta_vittima=30,
                  personalizzazione_pct=25)
        assert "errore" in r


class TestRisarcimentoInail:

    def test_temporanea(self):
        r = _call("risarcimento_inail", retribuzione_annua=30000, percentuale_invalidita=0,
                   tipo="temporanea")
        giornaliera = 30000 / 365
        assert_close(r["retribuzione_giornaliera"], round(giornaliera, 2), tolerance=0.01, label="inail_giorn")
        assert_close(r["dal_4_al_90_giorno"]["indennita_giornaliera"],
                     round(giornaliera * 0.60, 2), tolerance=0.01, label="inail_60")

    def test_permanente_sotto_6(self):
        r = _call("risarcimento_inail", retribuzione_annua=30000, percentuale_invalidita=3,
                   tipo="permanente")
        assert r["esito"] == "Nessun indennizzo"

    def test_permanente_capitale(self):
        r = _call("risarcimento_inail", retribuzione_annua=30000, percentuale_invalidita=10,
                   tipo="permanente")
        assert r["forma"] == "capitale"

    def test_permanente_rendita(self):
        r = _call("risarcimento_inail", retribuzione_annua=30000, percentuale_invalidita=20,
                   tipo="permanente")
        assert r["forma"] == "rendita"
        assert r["rendita_annua"] > 0


class TestDannoNonPatrimoniale:

    def test_micro_5pct(self):
        r = _call("danno_non_patrimoniale", percentuale_invalidita=5, eta_vittima=35,
                   giorni_itt=30, spese_mediche=1000)
        assert "micropermanenti" in r["tipo_calcolo"]
        assert r["componenti"]["danno_biologico"] > 0
        assert r["componenti"]["danno_patrimoniale_emergente"]["spese_mediche"] == 1000.0

    def test_macro_20pct(self):
        """Morale ed esistenziale confluiscono in una personalizzazione unitaria
        (Cass. SS.UU. 26972/2008), entro il 30% dell'art. 138 c. 3."""
        r = _call("danno_non_patrimoniale", percentuale_invalidita=20, eta_vittima=40,
                   danno_morale_pct=30)
        assert "macropermanenti" in r["tipo_calcolo"]
        pers = r["componenti"]["personalizzazione_unitaria"]
        assert pers["applicata_pct"] == 30.0
        expected = r["componenti"]["danno_biologico"] * 30 / 100
        assert_close(pers["importo"], round(expected, 2), tolerance=0.01, label="dnp_pers")


class TestEquoIndennizzo:

    def test_categoria_5(self):
        r = _call("equo_indennizzo", categoria_tabella="5", percentuale_invalidita=35,
                   stipendio_annuo=30000)
        expected = 30000 * 3.0 * 35 / 100
        assert_close(r["equo_indennizzo"], round(expected, 2), tolerance=0.01, label="equo_5")

    def test_categoria_1_pensione(self):
        r = _call("equo_indennizzo", categoria_tabella="1", percentuale_invalidita=90,
                   stipendio_annuo=40000)
        assert r["pensione_privilegiata"] is True
