"""ksef — dane JSON -> XML FA(3) + walidacja lokalna."""
import datetime, os, re, sys
import dane as _dane
if not hasattr(_dane, "os"):
    _dane.os = os  # dane.py używa os.path.exists bez importu os — zabezpieczenie
from dane import wczytaj_dane, policz

def die(msg, code=1):
    print(f"BŁĄD: {msg}", file=sys.stderr)
    sys.exit(code)

# ============================================================ KSEF (XML FA(3))
NS_FA3 = "http://crd.gov.pl/wzor/2025/06/25/13775/"  # targetNamespace schemat/fa3.xsd

def ksef_nip(nip):
    nip = re.sub(r"\D", "", str(nip))
    if not re.fullmatch(r"[1-9]((\d[1-9])|([1-9]\d))\d{7}", nip):
        die(f"NIP nie przechodzi wzorca schemy FA(3): {nip}")
    return nip


def kw_xml(x):
    return f"{x:.2f}"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def cmd_ksef(a):
    dane = wczytaj_dane(a.dane)
    stawki, grupy, brutto = policz(dane)
    teraz = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if dane.get("waluta", "PLN") != "PLN":
        die("v0.2 generuje XML tylko dla waluty PLN (inne waluty = dodatkowe pola schemy; v0.3)")

    def adres(kto):
        return f"<Adres><KodKraju>PL</KodKraju><AdresL1>{esc(kto['adres'])}</AdresL1></Adres>"

    def kontaktowe(kto):
        if not kto.get("email"):
            return ""
        return f"<DaneKontaktowe><Email>{esc(kto['email'])}</Email></DaneKontaktowe>"

    pozycje_xml = []
    for i, p in enumerate(dane["pozycje"], 1):
        pozycje_xml.append(
            f"<FaWiersz><NrWierszaFa>{i}</NrWierszaFa>"
            f"<P_7>{esc(p['nazwa'])}</P_7>"
            f"<P_8A>{esc(p['jm'])}</P_8A>"
            f"<P_8B>{p['ilosc']:g}</P_8B>"
            f"<P_9A>{kw_xml(p['cena_netto'])}</P_9A>"
            f"<P_11>{kw_xml(p['_netto'])}</P_11>"
            f"<P_12>{p['stawka_vat']}</P_12></FaWiersz>")

    sumy = []
    for idx in sorted(grupy):
        g = grupy[idx]
        if idx == "5":
            # stawka "zw" = sprzedaż zwolniona -> w schemie FA(3) to P_13_7
            # (P_13_5 to procedura szczególna z działu XII rozdz. 6a — nie ryczałt zwolnienia)
            sumy.append(f"<P_13_7>{kw_xml(g['netto'])}</P_13_7>")
        else:
            sumy.append(f"<P_13_{idx}>{kw_xml(g['netto'])}</P_13_{idx}>")
            sumy.append(f"<P_14_{idx}>{kw_xml(g['vat'])}</P_14_{idx}>")
    sumy.append(f"<P_15>{kw_xml(brutto)}</P_15>")

    termin = ""
    if dane.get("termin_platnosci"):
        termin = ("<Platnosc><TerminPlatnosci>"
                  f"<Termin>{dane['termin_platnosci']}</Termin>"
                  "</TerminPlatnosci><FormaPlatnosci>6</FormaPlatnosci></Platnosc>")
        if dane.get("rachunek"):
            nr_rb = re.sub(r"\s", "", str(dane["rachunek"]))
            termin = termin.replace("</Platnosc>",
                                    f"<RachunekBankowy><NrRB>{esc(nr_rb)}</NrRB>"
                                    "</RachunekBankowy></Platnosc>")

    # Zwolnienie: schemat to xsd:choice — albo (P_19 + P_19A/P_19B/P_19C), albo P_19N.
    # TWybor1 dopuszcza TYLKO wartość "1", więc gałęzi nie wolno mieszać.
    if "zw" in stawki:
        podstawa = dane.get("podstawa_zwolnienia")
        if not podstawa:
            die("faktura ze stawką 'zw' wymaga pola 'podstawa_zwolnienia' (przepis ustawy, "
                "np. 'art. 43 ust. 1 ustawy' albo art. 113) — schemie FA(3) przy P_19=1 "
                "musi towarzyszyć P_19A/P_19B/P_19C")
        zwolnienie = f"<P_19>1</P_19><P_19A>{esc(podstawa)}</P_19A>"
    else:
        zwolnienie = "<P_19N>1</P_19N>"

    p6 = ""
    if dane.get("data_sprzedazy") and dane["data_sprzedazy"] != dane["data_wystawienia"]:
        p6 = f"<P_6>{dane['data_sprzedazy']}</P_6>"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="{NS_FA3}">
 <Naglowek>
  <KodFormularza kodSystemowy="FA (3)" wersjaSchemy="1-0E">FA</KodFormularza>
  <WariantFormularza>3</WariantFormularza>
  <DataWytworzeniaFa>{teraz}</DataWytworzeniaFa>
  <SystemInfo>faktury-do-rejestru v0.2</SystemInfo>
 </Naglowek>
 <Podmiot1>
  <DaneIdentyfikacyjne><NIP>{ksef_nip(dane['sprzedawca']['nip'])}</NIP>
   <Nazwa>{esc(dane['sprzedawca']['nazwa'])}</Nazwa></DaneIdentyfikacyjne>
  {adres(dane['sprzedawca'])}
  {kontaktowe(dane['sprzedawca'])}
 </Podmiot1>
 <Podmiot2>
  <DaneIdentyfikacyjne><NIP>{ksef_nip(dane['nabywca']['nip'])}</NIP>
   <Nazwa>{esc(dane['nabywca']['nazwa'])}</Nazwa></DaneIdentyfikacyjne>
  {adres(dane['nabywca'])}
  {kontaktowe(dane['nabywca'])}
  <JST>2</JST>
  <GV>2</GV>
 </Podmiot2>
 <Fa>
  <KodWaluty>PLN</KodWaluty>
  <P_1>{dane['data_wystawienia']}</P_1>
  <P_2>{esc(dane['numer'])}</P_2>
  {p6}
  {chr(10).join('  ' + s for s in sumy)}
  <Adnotacje>
   <P_16>2</P_16><P_17>2</P_17><P_18>2</P_18><P_18A>2</P_18A>
   <Zwolnienie>{zwolnienie}</Zwolnienie>
   <NoweSrodkiTransportu><P_22N>1</P_22N></NoweSrodkiTransportu>
   <P_23>2</P_23>
   <PMarzy><P_PMarzyN>1</P_PMarzyN></PMarzy>
  </Adnotacje>
  <RodzajFaktury>VAT</RodzajFaktury>
  {chr(10).join('  ' + p for p in pozycje_xml)}
  {termin}
 </Fa>
</Faktura>
"""
    xml = re.sub(r"\n\s*\n", "\n", xml)
    with open(a.wyjscie, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"OK: XML FA(3) -> {a.wyjscie} (brutto {kw_xml(brutto)} PLN)")
    if a.waliduj:
        waliduj_xml(a.wyjscie)
    print("Pamiętaj: plik wgrywasz do KSeF SWOIM kanałem (system księgowy / KSeF web / API). "
          "Najpierw przetestuj w środowisku testowym MF.")
    return 0


def waliduj_xml(sciezka_xml, dir_schemat=None):
    import lxml.etree as ET
    dir_schemat = dir_schemat or os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemat")
    xsd = os.path.join(dir_schemat, "fa3.xsd")
    if not os.path.exists(xsd):
        die(f"brak schematu: {xsd} (folder schemat/ powinien być w repo)", 1)
    schema = ET.XMLSchema(ET.parse(xsd))
    doc = ET.parse(sciezka_xml)
    if schema.validate(doc):
        print("WALIDACJA XML: OK (FA(3), schemat lokalny 1-0E)")
        return True
    for e in list(schema.error_log)[:10]:
        print(f"  WALIDACJA: linia {e.line}: {e.message}")
    die("XML nie przechodzi schemy FA(3) — nie wgrywaj takiego pliku do KSeF", 1)




def run(a):
    return cmd_ksef(a)
