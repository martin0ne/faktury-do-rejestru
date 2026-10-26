#!/usr/bin/env python3
"""faktury-do-rejestru — wyciąg danych z faktur PDF do rejestru CSV.

PO CO:   Małe biuro dostaje faktury mailem albo wrzuca do folderu. Ktoś
         przepisuje je ręcznie do rejestru/Excela. Ten skrypt czyta PDF-y
         Z WARSTWĄ TEKSTOWĄ i wyciąga: sprzedawca, NIP sprzedawcy, numer
         faktury, data wystawienia, termin płatności, kwota brutto.
         Wynik dopisuje do rejestru.csv (UTF-8, średnik — Excel PL otwiera
         bez importu).
ZASADY:  Wszystko dzieje się LOKALNIE. Plik nie wychodzi poza komputer.
         Brak telemetrii, brak chmury, brak sieci (poza --llm, domyślnie off).
         Nie księguje, nie podpiera decyzji księgowych — tylko rejestr roboczy.
CO NIE DZIAŁA (v0.1, mówimy wprost):
         - skany/bez warstwy tekstowej (moduł OCR = v0.2),
         - faktury zaszyfrowane/zabezpieczone,
         - gwarancja poprawności: procenty skuteczności w README są mierzone
           na testowym zbiorze i podane z liczbą n. Twoje faktury mogą
           wyglądać inaczej — zawsze sprawdź wiersz zanim użyjesz.

Użycie:
  python3 faktury_do_rejestru.py fakture.pdf inna.pdf          # pojedyncze pliki
  python3 faktury_do_rejestru.py ~/Faktury/*.pdf               # wildcard
  python3 faktury_do_rejestru.py --katalog ~/Faktury           # cały folder
  python3 faktury_do_rejestru.py --rejestr moj.csv plik.pdf    # inny rejestr
  python3 faktury_do_rejestru.py --dry-run plik.pdf            # bez zapisu

Wyjście: exit 0 = OK; exit 2 = nie znaleziono danych (PDF pusty/skan?);
exit 1 = błąd. Każda faktura raportowana osobno: co wyciągnięto, czego brak.
"""
import argparse
import csv
import datetime
import os
import re
import sys

REJESTR_DFLT = os.path.expanduser("~/faktury-rejestr/rejestr.csv")

POLA = ["plik", "sprzedawca", "nip_sprzedawcy", "nr_faktury",
        "data_wystawienia", "termin_platnosci", "kwota_brutto", "komentarz"]


def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- ekstrakcja tekstu ----------
def tekst_z_pdf(sciezka):
    import fitz  # pymupdf
    doc = fitz.open(sciezka)
    if doc.needs_pass:
        die(f"{os.path.basename(sciezka)}: PDF zaszyfrowany (hasło) — pomijam")
    tekst = "\n".join(page.get_text("text") for page in doc)
    doc.close()
    return tekst


# ---------- heurystyki pól ----------
RE_NIP = re.compile(r"NIP[:\s]*(?:PL[-\s]?)?"
                    r"(\d{3}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}|\d{3}[- ]?\d{2}[- ]?\d{2}[- ]?\d{3}|\d{10})")
RE_DATA = re.compile(r"(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})")
RE_KWOTA_STRICT = re.compile(
    r"(?:Do zapłaty|Razem do zapłaty|Wartość brutto|Kwota brutto|RAZEM BRUTTO)"
    r"[^\d\n]{0,40}?(\d{1,9}[\s\u00a0\u202f]?\d{0,3})(?:[.,](\d{2}))?(?:\s*zł)?", re.IGNORECASE)
RE_KWOTA_LUZ = re.compile(
    r"Razem(?!\s*netto)[^\d\n]{0,40}?(\d{1,9}[\s\u00a0\u202f]?\d{0,3})(?:[.,](\d{2}))?(?:\s*zł)?",
    re.IGNORECASE)


def znajdz_nip(tekst):
    """NIP sprzedawcy: pierwszy NIP występujący po nagłówku 'Sprzedawca'."""
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
    # fallback: "nr: FV/..." w osobnej linii (układ "Faktura VAT" / "nr: X")
    if re.search(r"Faktura", tekst, re.IGNORECASE):
        m = re.search(r"^\s*(?:nr|Numer)\s*[:\-]\s*([A-Z0-9][A-Z0-9/\\\-_.]{2,30})\s*$",
                      tekst, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).rstrip(".,;")
    # fallback: linia zaczynająca się od "FV..." w pobliżu słowa Faktura
    m = re.search(r"^\s*(FV[/\-][A-Z0-9/_.\-]{2,28})\s*$", tekst, re.MULTILINE)
    return m.group(1) if m else ""


def znajdz_date(tekst, etykiety):
    for et in etykiety:
        m = re.search(et + r"[^\d\n]{0,30}" + RE_DATA.pattern, tekst, re.IGNORECASE)
        if m:
            d, mo, y = (int(g) for g in m.groups()[-3:])
            if 1 <= d <= 31 and 1 <= mo <= 12:
                return f"{y:04d}-{mo:02d}-{d:02d}"
    return ""


def znajdz_kwote(tekst):
    m = RE_KWOTA_STRICT.search(tekst) or RE_KWOTA_LUZ.search(tekst)
    if not m:
        return ""
    zl = m.group(1)
    for sp in (" ", "\u00a0", "\u202f"):
        zl = zl.replace(sp, "")
    gr = m.group(2) or "00"
    return f"{zl},{gr}"


def znajdz_sprzedawce(tekst):
    # nazwa sprzedawcy = linia bezpośrednio po "Sprzedawca" (pierwsza niepusta)
    m = re.search(r"Sprzedawca[^\S\n]*\n+\s*(.+)", tekst)
    if m:
        kandydaci = [m.group(1).strip()]
        # czasem nazwa w kolejnej linii (adres najpierw)
        dalej = tekst[m.end():].splitlines()
        for linia in dalej[:4]:
            linia = linia.strip()
            if len(linia) >= 3 and not re.match(r"^(ul\.|al\.|ulica|NIP|REGON|tel|mail)", linia, re.IGNORECASE):
                if kandydaci and kandydaci[0] and re.match(r"^(ul\.|al\.|tel|mail)", kandydaci[0], re.IGNORECASE):
                    kandydaci.insert(0, linia)
                elif not kandydaci[0]:
                    kandydaci[0] = linia
                break
        nazwa = kandydaci[0].strip(" ,;")
        if 2 < len(nazwa) <= 80:
            return nazwa
    # fallback: pierwszy wiersz pliku bywa nagłówkiem firmy (może zawierać NIP — utnij)
    for linia in tekst.splitlines()[:5]:
        linia = linia.strip()
        if not (3 < len(linia) <= 100):
            continue
        if RE_NIP.search(linia):
            linia = linia.split("NIP")[0].rstrip(" ·•|-").strip()
            if not (3 < len(linia) <= 80):
                continue
        return linia
    return ""


def ekstrahuj(sciezka):
    """Zwraca dict POLA->wartość + komentarz, co się nie udało."""
    tekst = tekst_z_pdf(sciezka)
    if len(tekst.strip()) < 40:
        return None  # skan albo pusty PDF
    r = {k: "" for k in POLA}
    r["plik"] = os.path.basename(sciezka)
    r["nip_sprzedawcy"] = znajdz_nip(tekst)
    r["nr_faktury"] = znajdz_nr_fv(tekst)
    r["data_wystawienia"] = znajdz_date(tekst, [r"Data wystawienia", r"data wystawienia", r"Wystawiono"])
    r["termin_platnosci"] = znajdz_date(tekst, [r"Termin płatności", r"termin płatności", r"Płatność do", r"Splatnosci|termin"])
    r["kwota_brutto"] = znajdz_kwote(tekst)
    r["sprzedawca"] = znajdz_sprzedawce(tekst)

    braki = [k for k in ["sprzedawca", "nip_sprzedawcy", "nr_faktury", "kwota_brutto"] if not r[k]]
    r["komentarz"] = ("brak: " + ", ".join(braki)) if braki else "OK"
    return r


# ---------- rejestr ----------
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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pliki", nargs="*", help="pliki PDF faktur")
    p.add_argument("--katalog", help="przetwórz wszystkie *.pdf z folderu")
    p.add_argument("--rejestr", default=REJESTR_DFLT, help=f"ścieżka rejestru CSV (domyślnie {REJESTR_DFLT})")
    p.add_argument("--dry-run", action="store_true", help="pokaż wynik, nie zapisuj")
    a = p.parse_args()

    sciezki = list(a.pliki)
    if a.katalog:
        if not os.path.isdir(a.katalog):
            die(f"brak katalogu: {a.katalog}", 2)
        sciezki += sorted(
            os.path.join(a.katalog, f) for f in os.listdir(a.katalog)
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
        braki = r["komentarz"]
        print(f"  {r['plik']}: {r['nr_faktury'] or '—'} | {r['sprzedawca'][:40] or '—'} | "
              f"NIP {r['nip_sprzedawcy'] or '—'} | {r['kwota_brutto'] or '—'} zł | "
              f"termin {r['termin_platnosci'] or '—'}  [{braki}]")

    if not wiersze:
        die("żadnej faktury nie udało się odczytać (skany? zaszyfrowane?)", 2)
    n = dopisz_do_rejestru(a.rejestr, wiersze, a.dry_run)
    if a.dry_run:
        print(f"(dry-run: nic nie zapisano; {len(wiersze)} faktur odczytanych)")
    else:
        print(f"OK: dopisano {n}/{len(wiersze)} faktur -> {a.rejestr} "
              f"(pominięte: {skip})")
    return 0


if __name__ == "__main__":
    main()
