# testy jednostkowe czytaj.py — uruchamiasz: python3 -m unittest discover -s testy
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from czytaj import ekstrahuj, nip_suma_ok, POLA


def pdf_z_tekstem(tekst):
    """Minimalny PDF z warstwą tekstową (PyMuPDF) w katalogu tymczasowym."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 780), tekst, fontname="helv", fontsize=10)
    path = os.path.join(tempfile.mkdtemp(prefix="fdr-test-"), "test.pdf")
    doc.save(path)
    doc.close()
    return path


class TestNipSumaKontrolna(unittest.TestCase):
    def test_poprawny_nip(self):
        self.assertTrue(nip_suma_ok("5252445514"))

    def test_zly_nip(self):
        self.assertFalse(nip_suma_ok("5271112229"))

    def test_za_krotki(self):
        self.assertFalse(nip_suma_ok("1234"))

    def test_pusty(self):
        self.assertFalse(nip_suma_ok(""))


class TestKomentarzNip(unittest.TestCase):
    TEKST_DOBRZY = ("Faktura VAT nr 1/10/2026\nData wystawienia: 05.10.2026\n"
                    "Termin płatności: 20.10.2026\nSprzedawca: Firma Testowa Sp. z o.o.\n"
                    "NIP: 5252445514\nDo zapłaty: 1 234,56 zł")
    TEKST_ZLY = TEKST_DOBRZY.replace("5252445514", "5271112229")

    def test_dobry_nip_bez_ostrzezenia(self):
        r = ekstrahuj(pdf_z_tekstem(self.TEKST_DOBRZY))
        self.assertNotIn("NIP zła suma kontrolna", r["komentarz"])

    def test_zly_nip_ostrzezenie_nie_odrzucenie(self):
        r = ekstrahuj(pdf_z_tekstem(self.TEKST_ZLY))
        self.assertIn("NIP zła suma kontrolna", r["komentarz"])
        self.assertIn("nip_sprzedawcy", r)      # wiersz jest w rejestrze (ostrzeżenie)
        self.assertEqual(r["nip_sprzedawcy"], "5271112229")
        self.assertEqual(r["nr_faktury"], "1/10/2026")


class TestNotInvoices(unittest.TestCase):
    def test_junk_ma_komentarz_a_filter_nalezy_do_cmd(self):
        """ekstrahuj zawsze zwraca wiersz; odrzut „nie-faktury" robi cmd_czytaj
        (brak nr_faktury I brak kwota_brutto) — sprawdzane w testach regreseji."""
        r = ekstrahuj(pdf_z_tekstem("Dowód osobisty Jan Kowalski, ul. Kwiatowa 1, "
                                    "Warszawa, PESEL 90010112345, ważny do 2030 roku."))
        self.assertEqual(r["nr_faktury"], "")
        self.assertEqual(r["kwota_brutto"], "")


if __name__ == "__main__":
    unittest.main()
