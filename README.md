# faktury-do-rejestru

Trzy rzeczy dla małego biura, w całości lokalnie, bez chmury i bez kont:

| Podkomenda | Co robi |
|---|---|
| `czytaj` | PDF faktury (warstwa tekstowa) → wiersz w rejestrze CSV/XLSX |
| `wystaw` | dane z pliku JSON → faktura PDF (układ PL, kwota słownie, VAT) |
| `ksef` | te same dane → plik XML FA(3), walidowany lokalnie względem oficjalnej schemy |

Powstało, bo w małych firmach ktoś codziennie przepisuje faktury ręcznie, a programy
księgowe kosztują i wymagają integracji. To nie jest system księgowy.
To rejestr roboczy + generator dokumentów + plik do KSeF.

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
python3 faktury_do_rejestru.py wystaw szablon-faktura.xlsx --wyjscie FV.pdf

# plik XML FA(3) do KSeF + walidacja lokalna względem schemy
python3 faktury_do_rejestru.py ksef przyklad-faktura.json --wyjscie FV.xml --waliduj

# podgląd bez zapisu
python3 faktury_do_rejestru.py czytaj --dry-run faktura1.pdf
```

Rejestr: CSV (średnik + UTF-8; Excel PL otwiera bez importu) i opcjonalnie XLSX.
**Domyślnie rejestr zapisuje się w `~/faktury-rejestr/rejestr.csv`** (folder tworzy się
sam; ścieżkę zmienisz opcją `--rejestr` — pełna ścieżka jest wypisywana po zapisie).
Duplikaty (ten sam plik + nr faktury) są pomijane; folder można przegryzać wielokrotnie.
Plik bez numeru faktury i bez kwoty (np. skan dowodu osobistego) NIE trafia do rejestru —
jest pomijany z komunikatem „nie wygląda na fakturę”.

## 5 minut od zera (bez programowania)

0. Zdobądź program i Pythona (tylko za pierwszym razem):
   - **Skąd wziąć kod:** na stronie repo (github.com/martin0ne/faktury-do-rejestru)
     `git clone https://github.com/martin0ne/faktury-do-rejestru`, albo prościej:
     zielony przycisk **Code → Download ZIP** i rozpakuj pobrany plik.
   - **Gdzie wpisujesz komendy:** w **Terminal** (macOS: Launchpad → wpisz „Terminal”)
     albo **PowerShell** (Windows: Start → wpisz „powershell”). Wpisujesz tam dokładnie
     te same komendy co poniżej, każdą zatwierdzasz Enterem.
   - **Wejdź do folderu z programem** (`cd` + nazwa folderu, np.
     `cd faktury-do-rejestru` albo `cd faktury-do-rejestru-main` po ZIP-ie).
   - **Potrzebny Python 3 z pip3.** Sprawdź komendą `python3 --version` (Windows
     bywa też jako `py --version`). Jeśli nie masz — pobierz instalator ze strony
     [python.org/downloads](https://www.python.org/downloads/) i zainstaluj.
1. Zainstaluj jedną komendę: `pip3 install pymupdf fpdf2 openpyxl lxml`
   Sprawdź, że działa: `python3 -c 'import fitz, fpdf, openpyxl, lxml; print("instalacja OK")'` —
   ✅ instalacja jest dobra, gdy na końcu widzisz „instalacja OK” i nigdzie nie ma słowa ERROR.
2. Pobierz `szablon-faktura.xlsx` i wypełnij w Excelu: arkusz „dane" (Twoje dane,
   klient) i „pozycje" (co sprzedajesz). Daty w formacie RRRR-MM-DD.
3. Wygeneruj PDF: `python3 faktury_do_rejestru.py wystaw szablon-faktura.xlsx --wyjscie FV.pdf`
4. Potrzebujesz pliku do KSeF? `python3 faktury_do_rejestru.py ksef szablon-faktura.xlsx --wyjscie FV.xml --waliduj`

Jak wygląda wynik: `przyklad-faktura.pdf` w repo (dane fikcyjne).

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| „brak fontu z polskimi znakami" | ustaw `FDR_FONT` na plik TTF z polskimi znakami (Linux: `fonts-dejavu`; Windows/macOS: Arial jest w systemie) |
| „SKAN albo pusty PDF" | faktura to skan bez warstwy tekstowej; przepisz ręcznie albo poczekaj na OCR (v0.3) |
| „zła suma kontrolna NIP” | literówka w NIP. Dokładnie: sumę kontrolną (mod 11) sprawdza **tylko `ksef`** — z `--waliduj` i bez — i odrzuca błędny NIP, zanim wygeneruje plik; to uratowało Cię przed błędem w KSeF. `czytaj` i `wystaw` NIE sprawdzają sumy (rejestr roboczy): `czytaj` jedynie dopisze do wiersza komentarz „NIP zła suma kontrolna”, `wystaw` przepisze NIP taki, jaki wpisałeś |
| CSV otwiera się w jednej kolumnie | w Excelu: Dane → Z tekstu/CSV → separator średnik |
| „nieobsługiwana stawka VAT" | v0.2 przyjmuje 23/22/8/7/5/4/3/zw; stawka 0% w XML KSeF nie jest obsługiwana |
| „nieistniejąca data" | data w przyszłej formie albo 31.02 — popraw w danych |

Problemy i pomysły: zakładka **Issues** na GitHubie (spokojnie — można pisać po polsku)
albo mail **biuro@mjoldak.pl**. Do zgłoszenia dołącz komendę, którą odpalałeś, i ostatnią
linię komunikatu błędu.

## Jak to działa

- **`czytaj`**: tekst z PDF przez PyMuPDF, potem **heurystyki** (regexy): NIP w
  3 formatach (3-3-2-2, 3-2-2-3, 10 cyfr), numer faktury, daty (PL `DD.MM.YYYY`,
  EN `12 October, 2025` / `July 23, 2026` / ISO), kwota po etykietach („Do zapłaty",
  „Razem do zapłaty", „Balance Due", „Total", „Total Amount Due"…). Zero AI w v0.2 —
  deterministycznie; wyniki się różnią od układu faktury; dlatego każdy wiersz ma
  kolumnę `komentarz` z listą brakujących pól. Wyciągnięty NIP dostaje sprawdzenie
  sumy kontrolnej (mod 11) — wynik negatywny to **ostrzeżenie w komentarzu** („NIP
  zła suma kontrolna”), nie odrzucenie wiersza; PDF-y bywają mylące. Plik, z którego
  nie wyciągnięto ani numeru faktury, ani kwoty, nie trafia do rejestru („nie
  wygląda na fakturę — pomijam”).
- **`wystaw`**: fpdf2 + font z polskimi znakami (szuka DejaVu/Arial Unicode
  na macOS/Linux/Windows; można wskazać zmienną `FDR_FONT`), kwota słownie po polsku z odmianą,
  obsługa stawek VAT 23/22/8/7/5/4/3/zw, zaokrąglenia half-up.
- **`ksef`**: generator XML FA(3), czyli struktury logicznej obowiązującej
  od 1.02.2026. Walidacja `--waliduj` przechodzi przeciwko **oficjalnej schemie
  XSD pobranej z crd.gov.pl** (folder `schemat/`, wersja 1-0E). Narzędzie NIE
  wysyła nic do KSeF: plik wgrywasz swoim kanałem (system księgowy, KSeF web,
  API), najpierw w środowisku testowym MF.

### Zmierzone wyniki (uaktualniane przy zmianie heurystyk)

| Zbiór | n | sprzedawca | NIP | nr faktury | kwota | data wyst. | termin płatności |
|---|---|---|---|---|---|---|---|
| syntetyczne PL (3 układy) | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| round-trip `wystaw` → `czytaj` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| syntetyczne EN (usługi, USD) | 2 | 2/2 | 0/2* | 2/2 | 2/2 | 2/2 | 2/2 |

\* EN-faktury w testach nie mają polskiego NIP; brak jest poprawnym wynikiem
(komentarz w wierszu mówi „brak: nip_sprzedawcy; waluta nie-PLN ($)").

**Brak pomiaru = brak deklaracji.** Fixture-y są w `testy/` (HTML; PDF wygenerujesz
Chrome headless). Uruchom na swoich fakturach (`--dry-run` nic nie zapisuje)
i wpisz własny wiersz do tabeli, jeśli chcesz go deklarować.

## Czego to NIE robi

- **Skany bez warstwy tekstowej**: OCR poza v0.2. Faktura-skan jest pomijana
  z jawnym komunikatem, nie „cicho zgaduje".
- **Waluta obca**: kwoty wyciąga, ale oznacza wiersz „waluta nie-PLN ($)"
  i nie przelicza kursów.
- **XML KSeF**: faktura standardowa VAT, PLN, NIP PL po obu stronach (suma
  kontrolna NIP sprawdzana), stawki 23/22/8/7/5/4/3/zw. Stawka 0% i korekty
  (KOR), zaliczki, waluty obce, ryczałty (P_13_6_x) nie są obsługiwane.
- **Księgowania i decyzji księgowych**: rejestr roboczy, nie księga.
- **Wysyłania czegokolwiek do sieci**: zero telemetrii, zero chmury, zero kont.
  Nawet `ksef --waliduj` działa wyłącznie na lokalnej kopii schemy.

## RODO i dane na fakturach

- Faktura z NIP osoby fizycznej / danymi kontaktowymi zawiera dane osobowe;
  ten skrypt przetwarza je **wyłącznie lokalnie** i niczego nie wysyła.
- Rejestr CSV/XLSX ląduje na Twoim dysku; zabezpiecz go jak teczkę z fakturami.
- `.gitignore` tego repo wyklucza pliki `*.csv` i prawdziwe dokumenty;
  Twoje dane nie powinny lądować w żadnym repozytorium.
- RODO nie zabrania takiego przetwarzania w ramach obsługi własnej działalności
  (podstawa: uzasadniony interes / obowiązek prawny), ale decyzję o zasadach
  przetwarzania w Twojej firmie podejmujesz Ty. **To narzędzie nie jest doradcą
  prawnym ani księgowym.** KSeF: harmonogram obowiązywania i sankcje są zmienne
  (komunikaty MF 2026); weryfikuj aktualny stan w dniu wdrożenia.

## Struktura repo

```
faktury_do_rejestru.py   # CLI (czytaj / wystaw / ksef)
czytaj.py  wystaw.py  ksef.py  dane.py  slownie.py
schemat/                 # FA(3) XSD 1-0E z crd.gov.pl + importy (walidacja lokalna)
testy/                   # fixtures HTML -> PDF (Chrome headless) do własnych pomiarów
przyklad-faktura.json    # dane wejściowe dla wystaw/ksef
przyklad-rejestr.csv     # przykładowy wiersz rejestru (fikcyjny)
szablon-faktura.xlsx     # template do wypełnienia w Excelu (wejście dla wystaw/ksef)
przyklad-faktura.pdf     # tak wygląda wynik (dane fikcyjne)
```

## Licencja

MIT. Rób co chcesz, bez gwarancji. Zanim użyjesz w obiegu: sprawdź wyniki na
swoich fakturach i porównaj z ręcznym przepisaniem.
