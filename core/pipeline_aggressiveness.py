"""
Aggressiveness analysis pipeline

Steps:
  1. data_import                    — precondition: ingest any new raw data (idempotent, skips already-imported files)
  2. lemmatize_comments             — Stanza lemmatization of raw comments per language
  3. import_aggressive_keywords     — load keyword list with weights into DB (truncates and re-imports)
  4. calculate_aggressiveness_by_day — score aggressiveness per day/language from lemmas + keyword weights
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _run(step_num: int, label: str, script: str) -> None:
    print(f'\n{"=" * 60}\nStep {step_num}: {label}\n{"=" * 60}')
    t = time.time()
    subprocess.run([sys.executable, str(ROOT / 'core' / script)], check=True)
    print(f'Finished in {time.time() - t:.1f}s')


if __name__ == '__main__':
    t_total = time.time()

    _run(1, 'Import raw data — precondition (data_import)', 'data_import.py')
    _run(2, 'Lemmatize comments (lemmatize_comments)', 'lemmatize_comments.py')
    _run(3, 'Import aggressive keywords (import_aggressive_keywords)', 'import_aggressive_keywords.py')
    _run(4, 'Calculate aggressiveness by day (calculate_aggressiveness_by_day)', 'calculate_aggressiveness_by_day.py')

    print(f'\nAggressiveness analysis pipeline completed in {time.time() - t_total:.1f}s')
