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

def wczytaj_dane(sciezka):
    if not os.path.exists(sciezka):
        die(f"plik nie istnieje: {sciezka}", 2)
    if not sciezka.lower().endswith(".json"):
        die("dane wystawienia przyjmuję jako JSON (wzór: przyklad-faktura.json)", 2)
    with open(sciezka, encoding="utf-8") as f:
        dane = json.load(f)
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
