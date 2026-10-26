"""wystaw — dane JSON -> faktura PDF (fpdf2)."""
import os, sys
from dane import wczytaj_dane, policz
from slownie import slownie

def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)

# ============================================================ WYSTAW (PDF)
def znajdz_font():
    kandydaci = []
    env = os.environ.get("FDR_FONT")
    if env:
        kandydaci.append(env)
    try:
        import matplotlib
        kandydaci.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf"))
    except ImportError:
        pass
    kandydaci += [
        # Windows (fpdf2 działa; Arial/Segoe UI/Tahoma mają polskie znaki)
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        os.path.expanduser("~/Library/Fonts/Arial Unicode.ttf"),
    ]
    for k in kandydaci:
        if k and os.path.exists(k):
            return k
    die("brak fontu z polskimi znakami. Ustaw FDR_FONT=/ścieżka/do/DejaVuSans.ttf "
        "(Linux: fonts-dejavu; macOS: Arial Unicode jest w systemie).", 1)


def kwota_str(x, waluta="PLN", z_waluta=True):
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} {waluta}" if z_waluta else s


def blok_adresowy(kto):
    linie = [kto["nazwa"], kto["adres"], f"NIP: {kto['nip']}"]
    if kto.get("email"):
        linie.append(kto["email"])
    return linie


def cmd_wystaw(a):
    from fpdf import FPDF
    dane = wczytaj_dane(a.dane)
    stawki, grupy, brutto = policz(dane)
    font = znajdz_font()
    W = dane["waluta"]

    pdf = FPDF(format="A4")
    # Jeden wag fontu (bez "B") — wyróżnienia robimy rozmiarem, nie stylem.
    pdf.add_font("fdr", "", font)
    # Marginesy 10+10: tabela 190 mm mieści się dokładnie między l_margin a r_margin.
    pdf.set_margins(10, 12, 10)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("fdr", size=10)
    LM, RM = pdf.l_margin, pdf.r_margin
    szer = pdf.w - LM - RM  # 190 mm

    # -- nagłówek: "Faktura" + nr + daty (wyrównane do prawej) --------------
    pdf.set_font_size(20)
    pdf.cell(0, 12, "Faktura", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(11)
    pdf.cell(0, 7, f"nr: {dane['numer']}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(9)
    pdf.cell(0, 6, f"Wystawiono w dniu: {dane['data_wystawienia']}", align="R",
             new_x="LMARGIN", new_y="NEXT")
    if dane.get("data_sprzedazy"):
        pdf.cell(0, 6, f"Data dostawy/usługi: {dane['data_sprzedazy']}", align="R",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # -- dwie kolumny: Sprzedawca (lewa) | Nabywca (prawa, pod prawą krawędź) --
    col_w = (szer - 4) // 2  # 93 mm; 4 mm odstępu między kolumnami
    y0 = pdf.get_y()
    for tytul, kto, linie in (("Sprzedawca", dane["sprzedawca"], blok_adresowy(dane["sprzedawca"])),
                              ("Nabywca", dane["nabywca"], blok_adresowy(dane["nabywca"]))):
        x = LM if tytul == "Sprzedawca" else LM + szer - col_w
        pdf.set_xy(x, y0)
        pdf.set_font_size(10)
        pdf.cell(col_w, 7, tytul, new_x="RIGHT", new_y="NEXT")
        pdf.set_font_size(9)
        for linia in linie:
            pdf.set_x(x)
            pdf.cell(col_w, 5, linia[:70], new_x="RIGHT", new_y="NEXT")
    pdf.set_y(y0 + 7 + 5 * max(len(blok_adresowy(dane["sprzedawca"])),
                               len(blok_adresowy(dane["nabywca"]))))
    pdf.ln(4)

    # -- tabela pozycji: suma szerokości = 190 mm ----------------------------
    szer_kol = [10, 74, 12, 14, 22, 22, 12, 24]
    nagl = ["Lp.", "Nazwa towaru/usługi", "Ilość", "Jm", "Cena netto", "Netto", "VAT %", "Brutto"]
    assert abs(sum(szer_kol) - szer) < 0.5, f"suma szerokości kolumn {sum(szer_kol)} != {szer}"

    def naglowek_tabeli():
        pdf.set_font_size(8)
        pdf.set_fill_color(230, 230, 230)
        for w, t in zip(szer_kol, nagl):
            pdf.cell(w, 6, t, border=1, fill=True, align="C")
        pdf.ln()

    naglowek_tabeli()
    for i, p in enumerate(dane["pozycje"], 1):
        # gdy wiersz nie zmieści się na stronie — nowa strona + powtórzony nagłówek
        if pdf.get_y() + 2 * 6 > pdf.page_break_trigger:
            pdf.add_page()
            naglowek_tabeli()
        wiersz = [str(i), p["nazwa"][:60], f"{p['ilosc']:g}", p["jm"],
                  kwota_str(p["cena_netto"], W, False),
                  kwota_str(p["_netto"], W, False),
                  str(p["stawka_vat"]),
                  kwota_str(p["_brutto"], W, False)]
        for w, t in zip(szer_kol, wiersz):
            pdf.cell(w, 6, t, border=1, align="C" if w < 60 else "L")
        pdf.ln()
    pdf.ln(2)

    # -- sumy per stawka + Do zapłaty + słownie ------------------------------
    # Jedna komórka na wiersz (etykieta + kwota) — dzięki temu w warstwie
    # tekstowej etykieta i kwota są jednym wierszem (parsowalne przez czytaj.py).
    pdf.set_font_size(10)
    for sw in sorted(stawki):
        et = f"{sw}%" if sw != "zw" else "zw."
        g = stawki[sw]
        pdf.cell(0, 6, f"Netto ({et}): {kwota_str(g['netto'], W)}", align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"VAT ({et}): {kwota_str(g['vat'], W)}", align="R",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(11)
    pdf.cell(0, 7, f"Do zapłaty: {kwota_str(brutto, W)}", align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(9)
    pdf.cell(0, 6, f"Słownie: {slownie(brutto)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # -- płatność + uwagi -----------------------------------------------------
    if dane.get("termin_platnosci"):
        pdf.cell(0, 6, f"Termin płatności: {dane['termin_platnosci']}", new_x="LMARGIN", new_y="NEXT")
    if dane.get("forma_platnosci"):
        pdf.cell(0, 6, f"Sposób zapłaty: {dane['forma_platnosci']}", new_x="LMARGIN", new_y="NEXT")
    if dane.get("rachunek"):
        pdf.cell(0, 6, f"Rachunek: {dane['rachunek']}", new_x="LMARGIN", new_y="NEXT")
    if dane.get("uwagi"):
        pdf.ln(2)
        pdf.multi_cell(0, 5, f"Uwagi: {dane['uwagi']}")

    kat = os.path.dirname(os.path.abspath(a.wyjscie))
    if kat:
        os.makedirs(kat, exist_ok=True)
    pdf.output(a.wyjscie)
    print(f"OK: faktura PDF -> {a.wyjscie} (brutto {kwota_str(brutto, W)}; "
          f"sprawdź dane przed wysyłką — narzędzie nie jest systemem księgowym)")
    return 0


def run(a):
    return cmd_wystaw(a)
