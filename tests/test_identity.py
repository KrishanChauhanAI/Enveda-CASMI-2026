"""Identity tests — suite version 1.1.0, 2026-11-19 UTC; includes official metric examples."""
import unittest

import pandas as pd

from src.identity import canonicalize_smiles_to_ik14, deduplicate_candidates, mrr_at_k, validate_submission


# Verify stereochemistry is stripped before tautomer canonicalization, including the official regression pair.
class IdentityMetricTest(unittest.TestCase):
    # Check the metric's critical stereo-before-tautomer canonicalization order.
    def test_stereo_is_ignored_even_when_it_constrains_tautomerization(self):
        answer = "C=C(C)C1CCC2CCC(=O)C=C2C1"
        candidate = "C=C(C)[C@@H]1CCC2CCC(=O)C=C2C1"
        self.assertEqual(canonicalize_smiles_to_ik14(answer), canonicalize_smiles_to_ik14(candidate))

    # Confirm a keto/enol tautomer pair maps to the same competition identity.
    def test_tautomer_equivalence(self):
        self.assertEqual(canonicalize_smiles_to_ik14("CC(=O)C"), canonicalize_smiles_to_ik14("C=C(O)C"))

    # Confirm different connectivity remains a distinct identity.
    def test_connectivity_difference_is_not_ignored(self):
        self.assertNotEqual(canonicalize_smiles_to_ik14("CCO"), canonicalize_smiles_to_ik14("CC(=O)O"))

    # Reproduce the public metric notebook's 0.75 example: one rank-1 and one rank-2 hit.
    def test_official_notebook_example(self):
        solution = pd.DataFrame({"molecule_id": ["m_1", "m_2"], "smiles": ["CCO", "c1ccccc1"]})
        submission = pd.DataFrame({"molecule_id": ["m_1", "m_2"], "smiles": ["CCO;CC(=O)O", "CC(=O)O;c1ccccc1"]})
        self.assertAlmostEqual(mrr_at_k(solution, submission), 0.75)

    # Confirm the scoring routine awards reciprocal rank and zero when no answer appears.
    def test_mrr_rank_positions(self):
        solution = pd.DataFrame({"molecule_id": ["a", "b"], "smiles": ["CCO", "c1ccccc1"]})
        submission = pd.DataFrame({"molecule_id": ["a", "b"], "smiles": ["CC(=O)O;CCO", "CCO;c1ccccc1"]})
        self.assertAlmostEqual(mrr_at_k(solution, submission, k=25), (0.5 + 0.5) / 2)

    # Confirm blank semicolon slots do not shift ranks after the metric parser removes empty guesses.
    def test_blank_candidates_do_not_shift_rank(self):
        solution = pd.DataFrame({"molecule_id": ["a"], "smiles": ["CCO"]})
        submission = pd.DataFrame({"molecule_id": ["a"], "smiles": ["CC(=O)O;;CCO"]})
        self.assertEqual(mrr_at_k(solution, submission), 0.5)

    # Confirm candidate de-duplication retains the first SMILES for each connectivity identity.
    def test_deduplicates_stereoisomers_and_tautomers(self):
        got = deduplicate_candidates(["C[C@H](N)C(=O)O", "CC(N)C(=O)O", "CC(=O)C", "C=C(O)C"])
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0], "C[C@H](N)C(=O)O")

    # Reject duplicate molecule rows and invalid candidate strings before scoring/submission.
    def test_submission_validation(self):
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_submission(pd.DataFrame({"molecule_id": ["a", "a"], "smiles": ["CCO", "CCO"]}))
        with self.assertRaisesRegex(ValueError, "Invalid SMILES"):
            validate_submission(pd.DataFrame({"molecule_id": ["a"], "smiles": ["not-smiles"]}))


if __name__ == "__main__":
    unittest.main()
