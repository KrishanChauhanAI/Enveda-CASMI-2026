"""Neutral mass and adduct mapping checks — suite version 1.0.0, 2026-11-19 UTC."""
import math
import unittest

from src.chemistry import neutral_mass


# Check all ten adducts documented for the competition's test data return the known neutral mass.
class NeutralMassTest(unittest.TestCase):
    def test_all_official_test_adducts(self):
        neutral = 300.0
        shifts = {
            "[M+H]+": 1.007276, "[M+NH4]+": 18.033823, "[M-H2O+H]+": -17.003289,
            "[M-2H2O+H]+": -35.013854, "[M+Na]+": 22.989218, "[M+K]+": 38.963158,
            "[M-H]-": -1.007276, "[M-H2O-H]-": -19.017841,
            "[M+CH2O2-H]-": 44.998201, "[M+Cl]-": 34.969402,
        }
        for adduct, shift in shifts.items():
            with self.subTest(adduct=adduct):
                self.assertAlmostEqual(neutral_mass(neutral + shift, adduct), neutral, places=5)

    # Unknown adducts and invalid precursor values must not be mistaken for neutral mass.
    def test_unknown_adduct_and_invalid_mass_are_nan(self):
        self.assertTrue(math.isnan(neutral_mass(300.0, "unrecognized")))
        self.assertTrue(math.isnan(neutral_mass(float("nan"), "[M+H]+")))
        self.assertTrue(math.isnan(neutral_mass("not-a-number", "[M+H]+")))


if __name__ == "__main__":
    unittest.main()
