"""Small synthetic integration tests for the bounded-memory Task 1 scanner."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.task1_eda import scan_parquet


# Confirm one-row-per-spectrum files report molecule-level cardinality separately from row counts.
class Task1EdaTest(unittest.TestCase):
    def test_streaming_schema_counts_and_sample(self):
        frame = pd.DataFrame({
            "molecule_id": ["mol_a", "mol_a", "mol_b"],
            "spectrum_id": ["s1", "s2", "s3"],
            "precursor_mz": [200.1, 200.2, 350.5],
            "ms2_mzs": [[50.0, 100.0], [75.0], [80.0, 120.0, 220.0]],
            "ingest_lib": ["lib1", "lib1", "lib2"],
        })
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tiny.parquet"
            pq.write_table(pa.Table.from_pandas(frame), path)
            report, sample = scan_parquet(path, sample_rows=2, batch_size=1, seed=7)
        self.assertEqual(report["rows"], 3)
        self.assertEqual(report["unique_molecules"], 2)
        self.assertEqual(report["sample_rows"], 2)
        self.assertIn("molecule_id", [x["name"] for x in report["columns"]])
        self.assertEqual(len(sample), 2)


if __name__ == "__main__":
    unittest.main()
