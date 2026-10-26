# Changelog

## v0.2 (2026-10-26)

- `wystaw`: generator faktury PDF (fpdf2, układ PL, kwota słownie z odmianą,
  stawki 23/22/8/7/5/4/3/zw, zaokrąglenia half-up)
- `ksef`: generator XML FA(3) (schemat 1-0E z crd.gov.pl) z lokalną walidacją XSD
  (`--waliduj`); bez wysyłki do KSeF — plik wgrywasz swoim kanałem
- `czytaj`: daty EN („12 October, 2025") i ISO, etykiety kwot EN
  (Total/Balance Due/Amount Due), separatory tysięcy (1 234 567,89 i 1.234,56),
  walidacja kalendza, waluta obca jawnie oznaczona, wyjście `--xlsx`
- dane wejściowe wystaw/ksef: **XLSX obok JSON** (szablon-faktura.xlsx)
- bezpieczeństwo: esc() na wszystkich polach XML, suma kontrolna NIP (mod 11),
  walidacja kalendza dat, half-up zaokrąglenia, well-formedness check bez --waliduj
- Windows: ścieżki fontów

## v0.1 (2026-10-26)

- `czytaj`: PDF faktur (warstwa tekstowa) -> rejestr CSV; heurystyki NIP
  (3 formaty), numeru, dat PL, kwoty po etykietach; dedup; --dry-run
