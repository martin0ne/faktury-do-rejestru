#!/usr/bin/env python3
"""faktury-do-rejestru — faktury: czytaj → rejestr, wystaw → PDF, ksef → XML FA(3).

  czytaj  PDF faktury (warstwa tekstowa) -> wiersz w rejestrze CSV/XLSX
  wystaw  dane z pliku JSON -> faktura PDF (układ PL, słownie, VAT)
  ksef    te same dane -> plik XML FA(3) gotowy do walidacji/uploadu do KSeF

ZASADY:  Wszystko dzieje się LOKALNIE. Zero sieci, zero chmury, zero telemetrii.
         Nie księguje, nie podpiera decyzji księgowych — rejestr roboczy
         i generator dokumentów.

Użycie:
  python3 faktury_do_rejestru.py czytaj --katalog ~/Faktury [--rejestr R] [--xlsx]
  python3 faktury_do_rejestru.py wystaw dane.json --wyjscie FV.pdf
  python3 faktury_do_rejestru.py ksef   dane.json --wyjscie FV.xml [--waliduj]
  (stara forma bez podkomendy nadal działa: python3 faktury_do_rejestru.py *.pdf)

Wyjście: exit 0 = OK; exit 2 = nic nie znaleziono/nie zrobiono; exit 1 = błąd.
"""
import argparse
import os
import sys

REJESTR_DFLT = os.path.expanduser("~/faktury-rejestr/rejestr.csv")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("czytaj", help="PDF faktur -> rejestr CSV/XLSX")
    c.add_argument("pliki", nargs="*")
    c.add_argument("--katalog")
    c.add_argument("--rejestr", default=REJESTR_DFLT)
    c.add_argument("--xlsx", action="store_true", help="dodatkowo zapisz rejestr.xlsx")
    c.add_argument("--dry-run", action="store_true")
    c.set_defaults(fn="czytaj")

    w = sub.add_parser("wystaw", help="dane JSON -> faktura PDF")
    w.add_argument("dane")
    w.add_argument("--wyjscie", required=True)
    w.set_defaults(fn="wystaw")

    k = sub.add_parser("ksef", help="dane JSON -> XML FA(3)")
    k.add_argument("dane")
    k.add_argument("--wyjscie", required=True)
    k.add_argument("--waliduj", action="store_true", help="waliduj względem schemy FA(3) (lokalnie)")
    k.set_defaults(fn="ksef")

    # backward-compat: pierwsza pozycja bez podkomendy = stara forma "czytaj *.pdf".
    # Nieznane słowo, które nie jest plikiem PDF, to pewnie literówka w komendzie —
    # nie przepuszczajmy jej cicho jako "pliku" (czytanie/xyzzy działały i ZAPISYWAŁY).
    argv = sys.argv[1:]
    if argv and argv[0] not in ("czytaj", "wystaw", "ksef") and not argv[0].startswith("-"):
        if not argv[0].lower().endswith(".pdf"):
            print(f"BŁĄD: nieznana komenda: {argv[0]} (masz na myśli „czytaj”?)\n"
                  f"Dostępne: czytaj / wystaw / ksef — sprawdź --help", file=sys.stderr)
            sys.exit(1)
        argv = ["czytaj"] + argv
    a, rest = p.parse_known_args(argv)
    if rest:
        print(f"BŁĄD: nieznane argumenty: {' '.join(rest)} (sprawdź --help — "
              f"program nie zgaduje flag i ignorowanie by zepsuło wynik)", file=sys.stderr)
        sys.exit(1)
    if not a.cmd:
        from czytaj import run as czytaj_run
        return czytaj_run(argparse.Namespace(pliki=rest, katalog=None, rejestr=REJESTR_DFLT,
                                             xlsx=False, dry_run=False))
    if a.fn == "czytaj":
        from czytaj import run as czytaj_run
        return czytaj_run(a)
    if a.fn == "wystaw":
        from wystaw import run as wystaw_run
        return wystaw_run(a)
    if a.fn == "ksef":
        from ksef import run as ksef_run
        return ksef_run(a)


if __name__ == "__main__":
    sys.exit(main())
