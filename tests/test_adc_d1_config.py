import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RAW_CODE = ROOT / "raw-code"
PYTHON_PROGRAMS = (
    RAW_CODE / "ADC.py",
    RAW_CODE / "ADC Plot.py",
    RAW_CODE / "ADC_RandomY03.py",
)


class AdcD1ConfigTests(unittest.TestCase):
    def test_python_programs_read_d1_and_use_raw_code_csv(self):
        expected_csv = 'Path(__file__).resolve().parent / "plc_voltage_log.csv"'

        for program in PYTHON_PROGRAMS:
            with self.subTest(program=program.name):
                source = program.read_text(encoding="utf-8")
                self.assertIn("REGISTER_ADDRESS = 1", source)
                self.assertIn("address=REGISTER_ADDRESS", source)
                self.assertIn("result.registers[0]", source)
                self.assertIn(expected_csv, source)

    def test_notebook_reads_d1_and_uses_raw_code_csv(self):
        notebook = json.loads((RAW_CODE / "ADC.ipynb").read_text(encoding="utf-8"))
        source = "".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )

        self.assertIn("REGISTER_ADDRESS = 1  # D1", source)
        self.assertIn("result.registers[0]", source)
        self.assertIn(
            'CSV_FILENAME = Path(r"C:\\Prior_Work\\อบรมplc\\raw-code\\plc_voltage_log.csv")',
            source,
        )


if __name__ == "__main__":
    unittest.main()
