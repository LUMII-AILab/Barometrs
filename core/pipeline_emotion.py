"""
Emotion analysis pipeline

Steps:
  1. load_model              — validate model directory is accessible (fast-fail)
  2. data_import             — ingest TSV files, detect language, generate embeddings
  3. predict_comments        — Ekman emotion classification per comment
  4. extract_keywords_by_day — KeyBERT keyword extraction per emotion/day
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(ROOT))
from path_config import models_path


def _run(step_num: int, label: str, script: str) -> None:
    print(f'\n{"=" * 60}\nStep {step_num}: {label}\n{"=" * 60}')
    t = time.time()
    subprocess.run([sys.executable, str(ROOT / 'core' / script)], check=True)
    print(f'Finished in {time.time() - t:.1f}s')


if __name__ == '__main__':
    t_total = time.time()

    print(f'\n{"=" * 60}\nStep 1: Verify model directory (load_model)\n{"=" * 60}')
    model_dir = Path(models_path())
    if not model_dir.exists():
        print(f'ERROR: Model directory not found: {model_dir}')
        sys.exit(1)
    print(f'Model directory OK: {model_dir}')

    _run(2, 'Import raw data (data_import)', 'data_import.py')
    _run(3, 'Predict emotions (predict_comments)', 'predict_comments.py')
    # TODO: consider using lemmatized comments instead of raw comment text for keyword extraction
    _run(4, 'Extract keywords by day (extract_keywords_by_day)', 'extract_keywords_by_day.py')

    print(f'\nEmotion analysis pipeline completed in {time.time() - t_total:.1f}s')