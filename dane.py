"""dane — wczytanie JSON + policzenie sum."""
import datetime, json, os, re, sys
from decimal import ROUND_HALF_UP, Decimal

def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)

# ============================================================ WSPÓLNE DANE
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _data_ok(nazwa, v):
    """Format YYYY-MM-DD + realna data (31.02 → die)."""
    if not isinstance(v, str) or not RE_DATA.fullmatch(v):
        die(f"{nazwa}: zły format daty: {v!r} (oczekuję YYYY-MM-DD, np. 2026-10-05)", 2)
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        die(f"{nazwa}: nieistniejąca data: {v!r} (np. 31.02)", 2)
    return v

def _kwota_ok(nazwa, v, p):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        die(f"pozycja: pole {nazwa} musi być liczbą, jest: {v!r} ({p})", 2)
    if v < 0:
        die(f"pozycja: pole {nazwa} nie może być ujemne: {v!r} ({p})", 2)
    return v


def _norm_nip(v):
    """NIP z Excela może wylecieć jako liczba — wróć do stringa."""
    if isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return v.strip()
    return v


def _norm_vat(v):
    """stawka_vat: int albo 'zw'. Excel da int/float/str — normalizuję."""
    if isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        return v.strip().lower()
    return v


def _norm_komorka_str(v):
    """Wartość z Excela -> string dla pól daty/tekstowych (data jako datetime -> ISO)."""
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return v


# ============================================================ Wczytanie XLSX
POLA_KTOREGO = ("nazwa", "nip", "adres", "email")
POLA_DANE = ("numer", "data_wystawienia", "data_sprzedazy", "termin_platnosci",
             "forma_platnosci", "rachunek", "waluta", "uwagi")
NAGLOWKI_POZYCJI = ("nazwa", "ilosc", "jm", "cena_netto", "stawka_vat")


def _wczytaj_xlsx(sciezka):
    try:
        import openpyxl
    except ImportError:
        die("brak biblioteki openpyxl — zainstaluj: pip3 install openpyxl", 2)
    wb = openpyxl.load_workbook(sciezka, data_only=True)
    brak = [s for s in ("dane", "pozycje") if s not in wb.sheetnames]
    if brak:
        die(f"plik XLSX musi mieć arkusze 'dane' i 'pozycje' (wzór: szablon-faktura.xlsx), "
            f"brakuje: {', '.join(brak)}", 2)

    # arkusz "dane": pary klucz|wartość w kolumnach A|B
    dane, kto = {}, {}
    for row in wb["dane"].iter_rows(min_col=1, max_col=2, values_only=True):
        klucz = row[0] if row else None
        wart = row[1] if len(row) > 1 else None
        if klucz is None or not str(klucz).strip():
            continue
        klucz = str(klucz).strip()
        if klucz.endswith(POLA_KTOREGO) and klucz.startswith(("sprzedawca_", "nabywca_")):
            kto_ob, pod = klucz.split("_", 1)
            kto.setdefault(kto_ob, {})[pod] = "" if wart is None else wart
        elif klucz in POLA_DANE:
            dane[klucz] = wart
        else:
            print(f"UWAGA: pomijam nieznany klucz w arkuszu 'dane': {klucz!r}")
    if not kto:
        die("w arkuszu 'dane' brakuje pól sprzedawca_nazwa/nip/adres i nabywca_nazwa/nip/adres "
            "(wzór: szablon-faktura.xlsx)", 2)
    dane.update(kto)
    for kto_ob in ("sprzedawca", "nabywca"):
        if kto_ob in dane:
            for pod, v in list(dane[kto_ob].items()):
                if pod == "nip":
                    dane[kto_ob][pod] = _norm_nip(v)
                else:
                    dane[kto_ob][pod] = _norm_komorka_str(v)
    for k in POLA_DANE:
        if k in dane:
            dane[k] = _norm_komorka_str(dane[k])

    # arkusz "pozycje": nagłówek + wiersze pozycji (puste wiersze pomijam)
    wiersze = list(wb["pozycje"].iter_rows(values_only=True))
    if not wiersze:
        die("arkusz 'pozycje' jest pusty (wzór: szablon-faktura.xlsx)", 2)
    nagl = [str(c).strip().lower() if c is not None else "" for c in wiersze[0]]
    if tuple(nagl[:len(NAGLOWKI_POZYCJI)]) != NAGLOWKI_POZYCJI:
        die(f"arkusz 'pozycje': zły nagłówek: {nagl} (musi być: "
            f"{' | '.join(NAGLOWKI_POZYCJI)})", 2)
    pozycje = []
    for w in wiersze[1:]:
        if w is None or all(c is None or str(c).strip() == "" for c in w):
            continue
        pozycje.append(dict(zip(NAGLOWKI_POZYCJI, w)))
    if not pozycje:
        die("arkusz 'pozycje': nie ma żadnej pozycji pod nagłówkiem", 2)
    for p in pozycje:
        p["stawka_vat"] = _norm_vat(p.get("stawka_vat"))
        for k in ("nazwa", "jm"):
            if isinstance(p.get(k), str):
                p[k] = p[k].strip()
    dane["pozycje"] = pozycje
    return dane


def wczytaj_dane(sciezka):
    if not os.path.exists(sciezka):
        die(f"plik nie istnieje: {sciezka}", 2)
    ext = os.path.splitext(sciezka)[1].lower()
    if ext == ".json":
        with open(sciezka, encoding="utf-8") as f:
            try:
                dane = json.load(f)
            except json.JSONDecodeError as e:
                die(f"plik JSON jest uszkodzony ({e}) — wzór: przyklad-faktura.json", 2)
    elif ext == ".xlsx":
        dane = _wczytaj_xlsx(sciezka)
    else:
        die("przyjmuję JSON lub XLSX (wzory: przyklad-faktura.json, szablon-faktura.xlsx)", 2)
    # te same walidacje dla JSON i XLSX:
    for klucz in ["sprzedawca", "nabywca", "numer", "data_wystawienia", "pozycje"]:
        if not dane.get(klucz):
            die(f"w danych brakuje pola: {klucz}", 2)
    for pod in ["nazwa", "nip", "adres"]:
        for kto in ["sprzedawca", "nabywca"]:
            if not dane[kto].get(pod):
                die(f"w danych [{kto}] brakuje pola: {pod}", 2)
    # daty: data_wystawienia wymagana, data_sprzedazy defaults, termin_platnosci opcjonalny
    _data_ok("data_wystawienia", dane["data_wystawienia"])
    dane.setdefault("data_sprzedazy", dane["data_wystawienia"])
    _data_ok("data_sprzedazy", dane["data_sprzedazy"])
    if dane.get("termin_platnosci"):
        _data_ok("termin_platnosci", dane["termin_platnosci"])
    for p in dane["pozycje"]:
        for k in ["nazwa", "ilosc", "cena_netto"]:
            if p.get(k) is None:
                die(f"pozycja bez pola {k}: {p}", 2)
        _kwota_ok("ilosc", p["ilosc"], p)
        _kwota_ok("cena_netto", p["cena_netto"], p)
        p.setdefault("jm", "szt.")
        p.setdefault("stawka_vat", 23)
    dane.setdefault("waluta", "PLN")
    return dane


def _zaokr2(x):
    """Zaokrąglenie groszowe half-up (polska praktyka), nie bankierskie."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def policz(dane):
    """Sumy per stawka + grupy P_13/P_14 + brutto (zaokrąglenia half-up, bez dryfu)."""
    stawki = {}
    for p in dane["pozycje"]:
        sw = str(p["stawka_vat"])
        if sw not in ("23", "22", "8", "7", "5", "4", "3", "0", "zw"):
            die(f"nieobsługiwana stawka VAT v0.2: {sw} (obsługa: 23/8/5/0/zw)")
        netto = _zaokr2(p["ilosc"] * p["cena_netto"])
        vat = _zaokr2(netto * (0 if sw == "zw" else int(sw) / 100))
        p["_netto"], p["_vat"], p["_brutto"] = netto, vat, _zaokr2(netto + vat)
        s = stawki.setdefault(sw, {"netto": 0.0, "vat": 0.0})
        s["netto"] = _zaokr2(s["netto"] + netto)
        s["vat"] = _zaokr2(s["vat"] + vat)
    grupy = {}
    for sw, v in stawki.items():
        idx = {"23": "1", "22": "1", "8": "2", "7": "2", "5": "3", "4": "3", "3": "3",
               "0": "4", "zw": "5"}[sw]
        g = grupy.setdefault(idx, {"netto": 0.0, "vat": 0.0, "stawki": []})
        g["netto"] = _zaokr2(g["netto"] + v["netto"])
        g["vat"] = _zaokr2(g["vat"] + v["vat"])
        g["stawki"].append(sw)
    brutto = _zaokr2(sum(g["netto"] + g["vat"] for g in grupy.values()))
    return stawki, grupy, brutto
