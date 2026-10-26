"""dane — wczytanie JSON + policzenie sum."""
import json, os, sys

def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)

# ============================================================ WSPÓLNE DANE
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
    for p in dane["pozycje"]:
        for k in ["nazwa", "ilosc", "cena_netto"]:
            if p.get(k) is None:
                die(f"pozycja bez pola {k}: {p}", 2)
        p.setdefault("jm", "szt.")
        p.setdefault("stawka_vat", 23)
    dane.setdefault("waluta", "PLN")
    dane.setdefault("data_sprzedazy", dane["data_wystawienia"])
    return dane


def policz(dane):
    """Sumy per stawka + grupy P_13/P_14 + brutto."""
    stawki = {}
    for p in dane["pozycje"]:
        sw = str(p["stawka_vat"])
        if sw not in ("23", "22", "8", "7", "5", "4", "3", "0", "zw"):
            die(f"nieobsługiwana stawka VAT v0.2: {sw} (obsługa: 23/8/5/0/zw)")
        netto = round(p["ilosc"] * p["cena_netto"], 2)
        vat = round(netto * (0 if sw == "zw" else int(sw) / 100), 2)
        p["_netto"], p["_vat"], p["_brutto"] = netto, vat, round(netto + vat, 2)
        s = stawki.setdefault(sw, {"netto": 0.0, "vat": 0.0})
        s["netto"] = round(s["netto"] + netto, 2)
        s["vat"] = round(s["vat"] + vat, 2)
    grupy = {}
    for sw, v in stawki.items():
        idx = {"23": "1", "22": "1", "8": "2", "7": "2", "5": "3", "4": "3", "3": "3",
               "0": "4", "zw": "5"}[sw]
        g = grupy.setdefault(idx, {"netto": 0.0, "vat": 0.0, "stawki": []})
        g["netto"] = round(g["netto"] + v["netto"], 2)
        g["vat"] = round(g["vat"] + v["vat"], 2)
        g["stawki"].append(sw)
    brutto = round(sum(g["netto"] + g["vat"] for g in grupy.values()), 2)
    return stawki, grupy, brutto


