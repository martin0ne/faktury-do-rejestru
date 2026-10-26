# faktury-do-rejestru

Trzy rzeczy dla małego biura, w całości lokalnie, bez chmury i bez kont:

| Podkomenda | Co robi |
|---|---|
| `czytaj` | PDF faktury (warstwa tekstowa) → wiersz w rejestrze CSV/XLSX |
| `wystaw` | dane z pliku JSON → faktura PDF (układ PL, kwota słownie, VAT) |
| `ksef` | te same dane → plik XML FA(3), walidowany lokalnie względem oficjalnej schemy |

Powstało, bo w małych firmach ktoś codziennie przepisuje faktury ręcznie, a programy
księgowe kosztują i wymagają integracji. To narzędzie NIE jest systemem księgowym —
to rejestr roboczy + generator dokumentów + plik do KSeF.

## Instalacja

```bash
pip3 install pymupdf fpdf2 openpyxl lxml
```

## Użycie

```bash
# faktury z folderu -> rejestr (CSV + Excel)
python3 faktury_do_rejestru.py czytaj --katalog ~/Faktury
python3 faktury_do_rejestru.py czytaj --katalog ~/Faktury --xlsx

# wystawienie faktury z danych
python3 faktury_do_rejestru.py wystaw przyklad-faktura.json --wyjscie FV.pdf

# plik XML FA(3) do KSeF + walidacja lokalna względem schemy
python3 faktury_do_rejestru.py ksef przyklad-faktura.json --wyjscie FV.xml --waliduj

# podgląd bez zapisu
python3 faktury_do_rejestru.py czytaj --dry-run faktura1.pdf
```

Rejestr: CSV (średnik + UTF-8 — Excel PL otwiera bez importu) i opcjonalnie XLSX.
Duplikaty (ten sam plik + nr faktury) są pomijane — folder można przegryzać wielokrotnie.

## Jak to działa (szczerze)

- **`czytaj`**: tekst z PDF przez PyMuPDF, potem **heurystyki** (regexy): NIP w
  3 formatach (3-3-2-2, 3-2-2-3, 10 cyfr), numer faktury, daty (PL `DD.MM.YYYY`,
  EN `12 October, 2025` / `July 23, 2026` / ISO), kwota po etykietach („Do zapłaty",
  „Razem do zapłaty", „Balance Due", „Total", „Total Amount Due"…). Zero AI w v0.2 —
  deterministycznie; wyniki się różnią od układu faktury, dlatego każdy wiersz ma
  kolumnę `komentarz` z listą brakujących pól.
- **`wystaw`**: fpdf2 + font z polskimi znakami (szuka DejaVu/Arial Unicode; można
  wskazać zmienną `FDR_FONT`), kwota słownie po polsku z odmianą, obsługa stawek
  VAT 23/8/5/0/zw.
- **`ksef`**: generator XML FA(3) — struktury logicznej obowiązującej od 1.02.2026.
  Walidacja `--waliduj` przechodzi przeciwko **oficjalnej schemie XSD pobranej z
  crd.gov.pl** (folder `schemat/`, wersja 1-0E). Narzędzie NIE wysyła nic do KSeF —
  plik wgrywasz swoim kanałem (system księgowy, KSeF web, API), najpierw
  w środowisku testowym MF.

### Zmierzone wyniki (uaktualniane przy zmianie heurystyk)

| Zbiór | n | sprzedawca | NIP | nr faktury | kwota | data wyst. | termin płatności |
|---|---|---|---|---|---|---|---|
| syntetyczne PL (3 układy) | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| round-trip `wystaw` → `czytaj` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| syntetyczne EN (usługi, USD) | 2 | 2/2 | 0/2* | 2/2 | 2/2 | 2/2 | 2/2 |

\* EN-faktury w testach nie mają polskiego NIP — brak jest poprawnym wynikiem
(komentarz w wierszu mówi „brak: nip_sprzedawcy; waluta nie-PLN ($)").

**Brak pomiaru = brak deklaracji.** Uruchom na swoich fakturach (`--dry-run` nic
nie zapisuje) i wpisz własny wiersz do tabeli, jeśli chcesz go deklarować.

## Czego to NIE robi

- **Skany bez warstwy tekstowej** — OCR poza v0.2; faktura-skan jest pomijana
  z jawnym komunikatem, nie „cicho zgaduje".
- **Waluta obca**: kwoty wyciąga, ale oznacza wiersz „waluta nie-PLN ($)" —
  nie przelicza kursów.
- **XML KSeF**: faktura standardowa VAT, PLN, NIP PL po obu stronach, stawki
  23/8/5/0/zw. Korekty (KOR), zaliczki, waluty obce, ryczałty (P_13_6_x) — nie.
- **Księgowania i decyzji księgowych** — rejestr roboczy, nie księga.
- **Wysyłania czegokolwiek do sieci** — zero telemetrii, zero chmury, zero kont.
  Nawet `ksef --waliduj` działa wyłącznie na lokalnej kopii schemy.

## RODO i dane na fakturach

- Faktura z NIP osoby fizycznej / danymi kontaktowymi zawiera dane osobowe —
  ten skrypt przetwarza je **wyłącznie lokalnie** i niczego nie wysyła.
- Rejestr CSV/XLSX ląduje na Twoim dysku; zabezpiecz go jak teczkę z fakturami.
- `.gitignore` tego repo wyklucza pliki `*.csv` i prawdziwe dokumenty — Twoje
  dane nie powinny lądować w żadnym repozytorium.
- RODO nie zabrania takiego przetwarzania w ramach obsługi własnej działalności
  (podstawa: uzasadniony interes / obowiązek prawny), ale decyzję o zasadach
  przetwarzania w Twojej firmie podejmujesz Ty — **to narzędzie nie jest doradcą
  prawnym ani księgowym**. KSeF: harmonogram obowiązywania i sankcje są zmienne
  (komunikaty MF 2026) — weryfikuj aktualny stan w dniu wdrożenia.

## Struktura repo

```
faktury_do_rejestru.py   # CLI (czytaj / wystaw / ksef)
czytaj.py  wystaw.py  ksef.py  dane.py  slownie.py
schemat/                 # FA(3) XSD 1-0E z crd.gov.pl + importy (walidacja lokalna)
przyklad-faktura.json    # dane wejściowe dla wystaw/ksef
przyklad-rejestr.csv     # przykładowy wiersz rejestru (fikcyjny)
```

## Licencja

MIT — rób co chcesz, bez gwarancji. Zanim użyjesz w obiegu: sprawdź wyniki na
swoich fakturach i porównaj z ręcznym przepisaniem.
