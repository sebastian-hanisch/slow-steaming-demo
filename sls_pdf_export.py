"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute sind erlaubt, aber "-" (Gedankenstrich), "-" (Minuszeichen),
"€", Emoji usw. lassen fpdf2 abstuerzen. Deshalb laeuft jeder Text durch pdf_text()."""
import time

import sls_constants as C

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "−": "-", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR", "±": "+-",
    "·": "-", "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "⚠️": "(!)", "⚠": "(!)", "✅": "", "ℹ️": "",
    "⛔": "", "🐌": "", "👁️": "", "🎯": "", "📊": "", "⛴️": "", "📐": "",
}


def pdf_text(text):
    """Text fuer die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def diagnosis_text(diag):
    if diag.kind == "infeasible":
        return "Diese Fenster sind selbst mit Vollgas auf jeder Etappe nicht einzuhalten - mindestens ein Fenster lockern oder die Route verkuerzen."
    markup = diag.markup_vs_const_pct
    sign = "teurer" if markup is not None and markup >= 0 else "billiger"
    return f"Machbar: alle {diag.n_windows} Fenster eingehalten, {abs(markup):.2f} % {sign} als die Politik konstant."


def verdict_text(v):
    if v.n == 0:
        return "Kein Vergleich moeglich: keine Route der Stichprobe ist fuer die Politik exakt machbar."
    if v.kind == "better":
        return f"Exakt gegen myopisch: im Mittel {abs(v.diff):.1f} Prozentpunkte weniger Verspaetungen je Route (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n})."
    if v.kind == "worse":
        return f"Exakt gegen myopisch: im Mittel {abs(v.diff):.1f} Prozentpunkte mehr Verspaetungen je Route (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n})."
    return f"Kein klarer Unterschied zwischen exakt und myopisch bei dieser Einstellung (Differenz {v.diff:+.1f}, Standardfehler {v.se:.1f}, n={v.n})."


def generate_sls_pdf(n_legs, window_share, tightness, rate_ratio, seed, shown, diag, gap_myo, gap_const,
                     late_myo, late_const, verdict=None, compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Route, Kosten je Politik, Diagnose, Zwei-Achsen-
    Vergleich, Urteil ueber die Stichprobe, Hinweise zum Modell."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        line(text, 8)
        pdf.set_font("Helvetica", "", 10)

    def pairs(rows):
        for label, value in rows:
            pdf.cell(75, 6, pdf_text(label), border=0)
            line(value, 6)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        for row in rows:
            for value, width in zip(row, widths):
                pdf.cell(width, 7, pdf_text(str(value)), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(7)

    def keep_together(height):
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def note(text, size=8):
        pdf.set_font("Helvetica", "I", size)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 5, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    line("Geschwindigkeitsoptimierung: Fenster halten statt nur sparen", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    heading("Route und Einstellung")
    pairs([("Etappen", str(n_legs)), ("Anteil mit Fenster", f"{window_share} %"), ("Fenster-Enge", tightness),
           ("Bunker-/Charter-Verhaeltnis", rate_ratio), ("Seed", str(seed))])
    pdf.ln(3)

    heading("Zusammenfassung")
    note(diagnosis_text(diag), 9)
    pairs([("Gesamtkosten (exakt)", "nicht machbar" if shown.cost_exact is None else f"{shown.cost_exact:,.0f}".replace(",", ".")),
           ("Gesamtkosten (myopisch)", f"{shown.cost_myo:,.0f}".replace(",", ".")),
           ("Gesamtkosten (konstant)", f"{shown.cost_const:,.0f}".replace(",", ".")),
           ("Fenster verpasst (myopisch/konstant)", f"{shown.n_late_myo} / {shown.n_late_const}")])
    pdf.ln(3)

    keep_together(60)
    heading("Zwei-Achsen-Vergleich (Stichprobe)")
    rows = [["Myopisch", "–" if gap_myo is None else f"{gap_myo:+.2f} %", "–" if late_myo is None else f"{late_myo:.1f} %"],
            ["Konstant", "–" if gap_const is None else f"{gap_const:+.2f} %", "–" if late_const is None else f"{late_const:.1f} %"]]
    table(["Politik", "Kostenaufschlag gegen exakt", "Verspaetungsanteil"], [40, 70, 60], rows)
    note(f"Basis: {C.SAMPLE_INSTANCES} Stichprobenrouten derselben Einstellung (nicht der eingestellte Seed), nur die fuer exakt machbaren.")
    pdf.ln(3)

    if verdict is not None:
        keep_together(40)
        heading("Urteil ueber die Stichprobe")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, pdf_text("- " + verdict_text(verdict)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    keep_together(70)
    heading("Hinweise zum Modell")
    pdf.set_font("Helvetica", "", 9)
    for text in [
        "Treibstoffkosten je Etappe ~ Distanz x Geschwindigkeit^2 (Verbrauch ~ v^3, Zeit = Distanz/v); Charterkosten ~ Distanz/Geschwindigkeit. Ohne Fenster ist die kostenoptimale Geschwindigkeit v* konstant und distanzunabhaengig (wirtschaftliche Geschwindigkeit, Ronen 1982).",
        "Konstant: immer v*, Fenster ignoriert. Myopisch: je Etappe lokal die langsamste Geschwindigkeit, die das EIGENE Fenster gerade noch schafft, ohne spaetere Etappen zu beruecksichtigen. Exakt: gemeinsame konvexe Optimierung ueber die ganze Route (trust-constr), haelt alle erreichbaren Fenster ein.",
        "Nur ein spaetestes Fenster je Etappe (kein fruehestes/Warten). Distanzen und Fenster-Enge synthetisch erzeugt, nicht an echten Bunkerpreisen/Charterraten kalibriert. Kein Wetter, keine Stroemung, keine Geschwindigkeitsschwankung durch Wellengang.",
        "Rechenzeit bei knappen/nicht machbaren Instanzen ist spuerbar hoeher als bei komfortablen (der Loeser iteriert laenger, bevor er aufgibt) - deshalb der kurze Ladeindikator statt einer Live-Berechnung ohne Anzeige.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
