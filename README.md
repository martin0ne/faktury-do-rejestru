# faktury-do-rejestru

Faktury PDF z maila albo z folderu → rejestr CSV. Lokalnie, bez chmury, bez kont.

Powstało, bo w małych biurach ktoś codziennie przepisuje faktury do Excela ręcznie.
v0.1 czyta PDF-y **z warstwą tekstową** (większość e-faktur) i wyciąga: sprzedawcę,
NIP, numer faktury, datę wystawienia, termin płatności i kwotę brutto, po czym
dopisuje wiersz do `rejestr.csv` (średnik + UTF-8 — Excel PL otwiera bez importu).

## Instalacja

```bash
pip3 install pymupdf
```

## Użycie

```bash
python3 faktury_do_rejestru.py --katalog ~/Faktury          # cały folder
python3 faktury_do_rejestru.py faktura1.pdf faktura2.pdf    # wybrane pliki
python3 faktury_do_rejestru.py --dry-run faktura1.pdf       # podgląd bez zapisu
python3 faktury_do_rejestru.py --rejestr ~/biuro/rejestr.csv ~/Faktury/*.pdf
```

Domyślny rejestr: `~/faktury-rejestr/rejestr.csv`. Duplikaty (ten sam plik + nr
faktury) są pomijane — można odpuszczać na tym samym folderze wielokrotnie.

## Jak to działa (szczerze)

- Tekst z PDF przez PyMuPDF, potem **heurystyki** (regexy) na: NIP, numer faktury,
  daty, kwota po etykietach „Razem / Do zapłaty / Wartość brutto", nazwa pod
  nagłówkiem „Sprzedawca". Zero sztucznej inteligencji w v0.1 — deterministycznie
  i przewidywalnie; moduł LLM (lokalny, opcjonalny) planowany w v0.2.
- Skuteczność jest **zmierzona, nie obiecana**: patrz tabela niżej (zbiór testowy,
  liczba n, procent pól). Na swoich fakturach możesz wyciągnąć inne wyniki —
  dlatego każdy wiersz ma kolumnę `komentarz` z listą brakujących pól.

### Zmierzone wyniki (uaktualniane przy zmianie heurystyk)

| Zbiór | n | sprzedawca | NIP | nr faktury | kwota | termin płatności |
|---|---|---|---|---|---|---|
| syntetyczne PDF-y (3 szablony) | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| realne faktury (własne, anonimizowane ścieżki) | — | *brak pomiaru — dodaj własny zbiór i wpisz wynik* |

*(Nie podajemy liczby, której nie zmierzyliśmy. Uruchom na swoich fakturach —
`--dry-run` niczego nie zapisuje — i wpisz własny wiersz do tabeli.)*

## Czego to NIE robi

- **Skany bez warstwy tekstowej** — OCR dopiero w v0.2. Faktura-skan jest
  pomijana z jawnym komunikatem, nie „cicho zgaduje".
- **Księgowania i decyzji księgowych** — to rejestr roboczy, nie księga.
- **Wysyłania czegokolwiek do sieci** — brak telemetrii, brak chmury, brak kont.

## RODO i dane na fakturach

- Faktura z NIP osoby fizycznej / danymi kontaktowymi zawiera dane osobowe —
  ten skrypt przetwarza je **wyłącznie lokalnie** i nie wysyła niczego do nikogo.
- Rejestr CSV ląduje u Ciebie na dysku; zadbaj o jego zabezpieczenie jak o każdą
  teczkę z fakturami (backup, dysk szyfrowany).
- Narzędzie nie usuwa danych ze źródłowych PDF-ów — to niezmiennie Twoje pliki.
- RODO nie zabrania takiego przetwarzania w ramach obsługi własnej działalności
  (podstawa: uzasadniony interes / obowiązek prawny), ale decyzję o zasadach
  przetwarzania w Twojej firmie podejmujesz Ty — ten skrypt nie jest doradcą.

## Licencja

MIT — rób co chcesz, bez gwarancji. Zanim użyjesz w obiegu: sprawdź wyniki na
swoich fakturach (`--dry-run`) i porównaj z ręcznym przepisaniem.
