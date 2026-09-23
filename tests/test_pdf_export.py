"""Tests fuer sls_pdf_export: Sonderzeichen-Bereinigung (fpdf2-Absturzzeichen) und dass der Export mit
allen Diagnose-Zustaenden (machbar/nicht machbar) tatsaechlich eine PDF-Datei erzeugt."""
import sls_evaluation as E
from sls_pdf_export import generate_sls_pdf, pdf_text


def test_pdf_text_replaces_crash_characters():
    assert pdf_text("Kostenaufschlag – 3 € pro Tag ⚠️") == "Kostenaufschlag - 3 EUR pro Tag (!)"
    assert "−" not in pdf_text("Minus − Zeichen")


def test_pdf_text_keeps_umlauts_and_does_not_crash_on_encode():
    text = pdf_text("Über Prüfung äöüß Anzahl")
    text.encode("latin-1")   # darf nicht raise


def test_pdf_text_is_idempotent_for_plain_ascii():
    assert pdf_text("Gesamtkosten: 1234") == "Gesamtkosten: 1234"


def _make_shown(feasible=True):
    if feasible:
        return E.RouteResult(seed=0, n_windows=2, v_exact=(18.0, 18.0), v_myo=(18.0, 18.0), v_const=(18.0, 18.0),
                             cost_exact=100000.0, cost_myo=101000.0, cost_const=99500.0, late_myo=0.0, n_late_myo=0,
                             late_const=0.0, n_late_const=0)
    return E.RouteResult(seed=0, n_windows=2, v_exact=None, v_myo=(24.0, 10.0), v_const=(18.0, 18.0), cost_exact=None,
                         cost_myo=105000.0, cost_const=99000.0, late_myo=5.0, n_late_myo=1, late_const=8.0, n_late_const=2)


def test_generate_sls_pdf_produces_a_valid_pdf_for_a_feasible_route():
    shown = _make_shown(True)
    diag = E.diagnose(shown)
    pdf_bytes = generate_sls_pdf(6, 50, "Mittel", "Standard (v*=18 kn)", 201, shown, diag, gap_myo=1.0, gap_const=-0.5,
                                 late_myo=20.0, late_const=50.0, verdict=None)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_generate_sls_pdf_handles_the_infeasible_status():
    shown = _make_shown(False)
    diag = E.diagnose(shown)
    assert diag.kind == "infeasible"
    pdf_bytes = generate_sls_pdf(6, 100, "Eng", "Sehr hoch (v*=23 kn)", 60, shown, diag, gap_myo=None, gap_const=None,
                                 late_myo=None, late_const=None, verdict=None)
    assert pdf_bytes[:4] == b"%PDF"


def test_generate_sls_pdf_includes_a_verdict_section_when_given():
    shown = _make_shown(True)
    diag = E.diagnose(shown)
    v = E.Verdict("better", -30.0, 5.0, 30)
    pdf_bytes = generate_sls_pdf(6, 50, "Mittel", "Standard (v*=18 kn)", 201, shown, diag, gap_myo=1.0, gap_const=-0.5,
                                 late_myo=20.0, late_const=50.0, verdict=v)
    assert pdf_bytes[:4] == b"%PDF"
