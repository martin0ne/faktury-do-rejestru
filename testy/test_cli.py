# testy dispatcher-a CLI — uruchamiasz: python3 -m unittest discover -s testy
import os, subprocess, sys, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = [sys.executable, os.path.join(REPO, "faktury_do_rejestru.py")]


def run(args):
    p = subprocess.run(CLI + args, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


class TestNieznanaKomenda(unittest.TestCase):
    def test_czytanie_die_z_podpowiedzia(self):
        """Literówka 'czytanie' nie może cicho działać jako czytaj i ZAPISYWAĆ."""
        rc, out, err = run(["czytanie", "--katalog", "/tmp"])
        self.assertEqual(rc, 1)
        self.assertIn("nieznana komenda: czytanie", err)
        self.assertIn("czytaj", err)

    def test_xyzzy_te_zginie(self):
        rc, out, err = run(["xyzzy", "--katalog", "/tmp"])
        self.assertEqual(rc, 1)
        self.assertIn("nieznana komenda: xyzzy", err)

    def test_stara_forma_pdf_dziala(self):
        """Backward-compat: pliki .pdf bez podkomendy nadal wchodzą w czytaj."""
        rc, out, err = run([os.path.join("/nie", "ma", "takiego.pdf")])
        self.assertEqual(rc, 2)          # die "plik nie istnieje" — czyli doszedł do czytaj
        self.assertIn("plik nie istnieje", err)


class TestNieznaneFlagi(unittest.TestCase):
    def test_wynaleziona_flaga_nie_przechodzi_cicho(self):
        rc, out, err = run(["czytaj", "--wyjscie-rejestr", "gdzies.csv"])
        self.assertEqual(rc, 1)
        self.assertIn("nieznane argumenty", err)
        self.assertIn("--wyjscie-rejestr", err)
        self.assertIn("--help", err)


class TestPustyKatalog(unittest.TestCase):
    def test_pusty_katalog_mowi_prawde(self):
        d = tempfile.mkdtemp(prefix="fdr-pusty-")
        rc, out, err = run(["czytaj", "--katalog", d])
        self.assertEqual(rc, 2)
        self.assertIn("nie zawiera plików PDF", err)
        self.assertNotIn("podaj pliki PDF albo --katalog", err)

    def test_brak_katalogu_nadal_rc2(self):
        rc, out, err = run(["czytaj", "--katalog", "/nie/ma/takiego"])
        self.assertEqual(rc, 2)
        self.assertIn("brak katalogu", err)


if __name__ == "__main__":
    unittest.main()
