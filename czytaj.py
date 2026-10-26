"""czytaj — PDF faktur -> rejestr CSV/XLSX."""
import csv, os, re, sys

POLA = ["plik", "sprzedawca", "nip_sprzedawcy", "nr_faktury",
        "data_wystawienia", "termin_platnosci", "kwota_brutto", "komentarz"]


def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)

# ============================================================ CZYTAJ (v0.1)
def tekst_z_pdf(sciezka):
    import fitz  # pymupdf
    doc = fitz.open(sciezka)
    if doc.needs_pass:
        die(f"{os.path.basename(sciezka)}: PDF zaszyfrowany (hasło) — pomijam")
    tekst = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    return tekst


RE_NIP = re.compile(r"NIP[:\s]*(?:PL[-\s]?)?"
                    r"(\d{3}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}|\d{3}[- ]?\d{2}[- ]?\d{2}[- ]?\d{3}|\d{10})")
RE_KWOTA_STRICT = re.compile(
    r"(?:Do zapłaty|Razem do zapłaty|Wartość brutto|Kwota brutto|RAZEM BRUTTO)"
    r"[^\d\n]{0,40}?(\d{1,9}[ \u00a0\u202f]?\d{0,3})(?:[.,](\d{2}))?(?:\s*zł)?", re.IGNORECASE)
RE_KWOTA_LUZ = re.compile(
    r"Razem(?!\s*netto)[^\d\n]{0,40}?(\d{1,9}[\s\u00a0\u202f]?\d{0,3})(?:[.,](\d{2}))?(?:\s*zł)?",
    re.IGNORECASE)
RE_DATA = re.compile(r"(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})")
RE_DATA_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_MIES = {"styczen":1,"january":1,"jan":1,"luty":2,"february":2,"feb":2,"marzec":3,"march":3,"mar":3,
         "kwiecien":4,"april":4,"apr":4,"maj":5,"may":5,"czerwiec":6,"june":6,"jun":6,
         "lipiec":7,"july":7,"jul":7,"sierpien":8,"august":8,"aug":8,"wrzesien":9,"september":9,"sep":9,
         "pazdziernik":10,"october":10,"oct":10,"listopad":11,"november":11,"nov":11,
         "grudzien":12,"december":12,"dec":12}
RE_DATA_EN1 = re.compile(r"(\d{1,2})\s+([A-Za-zęóąśłżźćń]+)\.?,?\s+(\d{4})")   # 12 October, 2025
RE_DATA_EN2 = re.compile(r"([A-Za-zęóąśłżźćń]+)\.?\s+(\d{1,2}),?\s+(\d{4})")  # July 23, 2026 / Aug 05 2024
RE_KWOTA_STRICT_EN = re.compile(
    r"(?:Total Amount Due|Balance Due|Grand Total|Amount Due|Total)"
    r"[^\d\n]{0,40}?([$€£])?"
    r"(\d{1,9}(?:[ ,\u00a0\u202f]\d{3})*)"
    r"(?:[.,](\d{2}))?"
    r"(?!\s*(?:dni|days|%))", re.IGNORECASE)


def znajdz_nip(tekst):
    m = re.search(r"Sprzedawca", tekst)
    obszar = tekst[m.start():m.start() + 400] if m else tekst
    hits = RE_NIP.findall(obszar)
    if hits:
        nip = re.sub(r"\D", "", hits[0])
        if len(nip) == 10:
            return nip
    hits_all = RE_NIP.findall(tekst)
    if hits_all:
        return re.sub(r"\D", "", hits_all[0])
    return ""


def znajdz_nr_fv(tekst):
    m = re.search(r"(?:Faktura[^\n]{0,40}?(?:numer|nr\.?)|Faktura VAT nr)\s*[:\-]?\s*"
                  r"([A-Z0-9][A-Z0-9/\\\-_.]{2,30})", tekst, re.IGNORECASE)
    if m:
        return m.group(1).rstrip(".,;")
    if re.search(r"Faktura", tekst, re.IGNORECASE):
        m = re.search(r"^\s*(?:nr|Numer)\s*[:\-]\s*([A-Z0-9][A-Z0-9/\\\-_.]{2,30})\s*$",
                      tekst, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).rstrip(".,;")
    m = re.search(r"^\s*(FV[/\-][A-Z0-9/_.\-]{2,28})\s*$", tekst, re.MULTILINE)
    if m:
        return m.group(1)
    # EN: "Invoice No: 00000001" / "Invoice #: INV-2026-7892"
    m = re.search(r"Invoice\s*(?:No\.?|#|Number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-_.]{2,30})",
                  tekst, re.IGNORECASE)
    if m:
        return m.group(1).rstrip(".,;")
    return ""


def _en_miesiec(nazwa):
    return _MIES.get(nazwa.lower().rstrip("ą").replace("ę", "e"), 0)


def znajdz_date(tekst, etykiety):
    for et in etykiety:
        # PL numeryczne: DD.MM.YYYY
        m = re.search(et + r"[^\d\n]{0,30}" + RE_DATA.pattern, tekst, re.IGNORECASE)
        if m:
            d, mo, y = (int(g) for g in m.groups()[-3:])
            if 1 <= d <= 31 and 1 <= mo <= 12:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        # EN: 12 October, 2025 albo July 23, 2026
        m = re.search(et + r"[^\d\nA-Za-z]{0,30}" + RE_DATA_EN1.pattern, tekst, re.IGNORECASE)
        if not m:
            m = re.search(et + r"[^\d\nA-Za-z]{0,30}" + RE_DATA_EN2.pattern, tekst, re.IGNORECASE)
        if m:
            g = m.groups()
            if g[0].isdigit():
                d, mies, y = int(g[0]), _en_miesiec(g[1]), int(g[2])
            else:
                mies, d, y = _en_miesiec(g[0]), int(g[1]), int(g[2])
            if 1 <= d <= 31 and 1 <= mies <= 12:
                return f"{y:04d}-{mies:02d}-{d:02d}"
        # ISO YYYY-MM-DD (nasze własne PDF-y z wystaw)
        m = re.search(et + r"[^\d\n]{0,30}" + RE_DATA_ISO.pattern, tekst, re.IGNORECASE)
        if m:
            y, mo, d = (int(g) for g in m.groups()[-3:])
            return f"{y:04d}-{mo:02d}-{d:02d}"
    return ""


def znajdz_kwote(tekst):
    """Zwraca (kwota, notka) — notka nie-pusta = waluta nie-PLN albo inny sygnał."""
    for rx, waluta_grupa in ((RE_KWOTA_STRICT, None), (RE_KWOTA_STRICT_EN, 1), (RE_KWOTA_LUZ, None)):
        m = rx.search(tekst)
        if not m:
            continue
        grupy = m.groups()
        # pozycja liczby zależy od tego, czy regex łapie symbol waluty
        offset = 1 if waluta_grupa is not None else 0
        zl = grupy[offset]
        sym = (grupy[0] or "") if waluta_grupa is not None else ""
        for sp in (" ", "\u00a0", "\u202f", ","):
            zl = (zl or "").replace(sp, "")
        if not zl:
            continue
        gr = grupy[offset + 1] or "00"
        notka = ""
        if sym in ("$", "€", "£"):
            notka = f"waluta nie-PLN ({sym})"
        return f"{zl},{gr}", notka
    return "", ""


def znajdz_sprzedawce(tekst):
    m = re.search(r"Sprzedawca[^\S\n]*\n+\s*(.+)", tekst)
    if m:
        nazwa = m.group(1).strip(" ,;")
        if 2 < len(nazwa) <= 80:
            return nazwa
    for linia in tekst.splitlines()[:5]:
        linia = linia.strip()
        if not (3 < len(linia) <= 100):
            continue
        # czysty tytuł dokumentu to nie sprzedawca
        if re.fullmatch(r"(?:SERVICE |PROFORMA |TAX |VAT )?INVOICE\s*(?:No\.?\s*[:#]?.*)?", linia, re.IGNORECASE) \
           and "From" not in linia:
            continue
        if re.match(r"(?:Date|Due|Invoice|Bill|Page|Tax|Total|Sub ?Total|Balance|Amount)\b", linia, re.IGNORECASE):
            continue
        linia = re.sub(r"^(?:From|Sprzedawca|Seller)\s*:\s*", "", linia, flags=re.IGNORECASE)
        if not (3 < len(linia) <= 80):
            continue
        if RE_NIP.search(linia):
            linia = linia.split("NIP")[0].rstrip(" ·•|-").strip()
            if not (3 < len(linia) <= 80):
                continue
        return linia
    return ""


def ekstrahuj(sciezka):
    tekst = tekst_z_pdf(sciezka)
    if len(tekst.strip()) < 40:
        return None
    r = {k: "" for k in POLA}
    r["plik"] = os.path.basename(sciezka)
    r["nip_sprzedawcy"] = znajdz_nip(tekst)
    r["nr_faktury"] = znajdz_nr_fv(tekst)
    r["data_wystawienia"] = znajdz_date(tekst, [r"Data wystawienia", r"data wystawienia", r"Wystawiono", r"Invoice date", r"Date issued", r"Dated"])
    r["termin_platnosci"] = znajdz_date(tekst, [r"Termin płatności", r"termin płatności", r"Płatność do", r"Splatnosci|termin", r"Due date", r"Due on", r"Payment due", r"Due by"])
    r["kwota_brutto"], notka_waluty = znajdz_kwote(tekst)
    r["sprzedawca"] = znajdz_sprzedawce(tekst)
    braki = [k for k in ["sprzedawca", "nip_sprzedawcy", "nr_faktury", "kwota_brutto"] if not r[k]]
    r["komentarz"] = ("brak: " + ", ".join(braki)) if braki else "OK"
    if notka_waluty:
        r["komentarz"] = (r["komentarz"] + "; " if r["komentarz"] else "") + notka_waluty
    return r


def dopisz_do_rejestru(sciezka_rejestru, wiersze, dry=False):
    os.makedirs(os.path.dirname(sciezka_rejestru) or ".", exist_ok=True)
    nowy = not os.path.exists(sciezka_rejestru)
    istniejace = set()
    if not nowy:
        with open(sciezka_rejestru, newline="", encoding="utf-8-sig") as f:
            for w in csv.DictReader(f, delimiter=";"):
                istniejace.add((w.get("plik", ""), w.get("nr_faktury", "")))
    if dry:
        return 0
    with open(sciezka_rejestru, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=POLA, delimiter=";")
        if nowy:
            w.writeheader()
        n = 0
        for r in wiersze:
            if (r["plik"], r["nr_faktury"]) in istniejace:
                print(f"  (duplikat w rejestrze, pomijam: {r['plik']} / {r['nr_faktury'] or '—'})")
                continue
            w.writerow(r)
            n += 1
    return n


def zapisz_xlsx(sciezka_xlsx, wiersze):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "rejestr"
    ws.append(POLA)
    for r in wiersze:
        ws.append([r[k] for k in POLA])
    szer = {"A": 22, "B": 34, "C": 14, "D": 18, "E": 13, "F": 13, "G": 12, "H": 24}
    for kol, w in szer.items():
        ws.column_dimensions[kol].width = w
    wb.save(sciezka_xlsx)


def cmd_czytaj(a):
    sciezki = list(a.pliki)
    if a.katalog:
        if not os.path.isdir(a.katalog):
            die(f"brak katalogu: {a.katalog}", 2)
        sciezki += sorted(os.path.join(a.katalog, f) for f in os.listdir(a.katalog)
                          if f.lower().endswith(".pdf"))
    sciezki = [s for s in sciezki if s.lower().endswith(".pdf")]
    if not sciezki:
        die("podaj pliki PDF albo --katalog", 2)
    wiersze, skip = [], 0
    for s in sciezki:
        if not os.path.exists(s):
            die(f"plik nie istnieje: {s}", 2)
        try:
            r = ekstrahuj(s)
        except Exception as e:
            print(f"  {os.path.basename(s)}: błąd parsowania ({e})")
            skip += 1
            continue
        if r is None:
            print(f"  {os.path.basename(s)}: SKAN albo pusty PDF (brak warstwy tekstowej) — pomijam")
            skip += 1
            continue
        wiersze.append(r)
        print(f"  {r['plik']}: {r['nr_faktury'] or '—'} | {r['sprzedawca'][:40] or '—'} | "
              f"NIP {r['nip_sprzedawcy'] or '—'} | {r['kwota_brutto'] or '—'} zł | "
              f"termin {r['termin_platnosci'] or '—'}  [{r['komentarz']}]")
    if not wiersze:
        die("żadnej faktury nie udało się odczytać (skany? zaszyfrowane?)", 2)
    n = dopisz_do_rejestru(a.rejestr, wiersze, a.dry_run)
    if a.dry_run:
        print(f"(dry-run: nic nie zapisano; {len(wiersze)} faktur odczytanych)")
    else:
        print(f"OK: dopisano {n}/{len(wiersze)} faktur -> {a.rejestr} (pominięte: {skip})")
        if a.xlsx:
            x = os.path.splitext(a.rejestr)[0] + ".xlsx"
            zapisz_xlsx(x, wiersze)
            print(f"OK: rejestr Excel -> {x} (uwaga: --xlsx zapisuje TYLKO świeżo przeczytane faktury)")
    return 0




def run(a):
    return cmd_czytaj(a)
