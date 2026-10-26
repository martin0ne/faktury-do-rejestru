"""slownie — kwota słowami po polsku."""
import sys

# ============================================================ SŁOWNIE
_JED = ["zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć"]
_NAST = ["dziesięć", "jedenaście", "dwanaście", "trzynaście", "czternaście",
         "piętnaście", "szesnaście", "siedemnaście", "osiemnaście", "dziewiętnaście"]
_DZI = ["", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt",
        "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt"]
_SET = ["", "sto", "dwieście", "trzysta", "czterysta", "pięćset", "sześćset",
        "siedemset", "osiemset", "dziewięćset"]

_MAX_ZL = 10 ** 9  # 999 999 999,99 zł — 9 cyfr netto; wyżej: brak sekcji "miliard"


def trojka(n):
    s, r = [], n
    setki, r = divmod(r, 100)
    if setki:
        s.append(_SET[setki])
    if 10 <= r <= 19:
        s.append(_NAST[r - 10])
    else:
        d, j = divmod(r, 10)
        if d:
            s.append(_DZI[d])
        if j:
            s.append(_JED[j])
    return " ".join(s)


def odmiana(n, formy):
    if n == 1:
        return formy[0]
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return formy[1]
    return formy[2]


def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)


def slownie(kwota):
    if kwota < 0:
        die(f"kwota ujemna nie jest obsługiwana: {kwota}")
    zl = int(kwota)
    gr = int(round((kwota - zl) * 100))
    if gr == 100:
        zl, gr = zl + 1, 0
    if zl >= _MAX_ZL:
        die("slownie obsługuje kwoty do 999 999 999,99 zł (9 cyfr netto); "
            f"podano: {kwota} — dla większych potrzebna jest sekcja 'miliard'")
    sekcje = []
    mln = zl // 10 ** 6
    tys = (zl % 10 ** 6) // 1000
    jedn = zl % 1000
    if mln:
        sekcje.append(f"{trojka(mln)} {odmiana(mln, ('milion', 'miliony', 'milionów'))}")
    if tys:
        sekcje.append(f"{trojka(tys)} {odmiana(tys, ('tysiąc', 'tysiące', 'tysięcy'))}")
    if jedn:
        sekcje.append(f"{trojka(jedn)} {odmiana(jedn, ('złoty', 'złote', 'złotych'))}")
    elif zl:
        # kwota jest wielokrotnością 1000/1 mln (jedn==0, zl>0):
        # forma rzeczownika "złotych/złote/złoty" jako samodzielna sekcja
        sekcje.append(odmiana(zl, ('złoty', 'złote', 'złotych')))
    if not sekcje:
        sekcje = ["zero złotych"]
    return " ".join(sekcje) + f" {gr:02d}/100"
