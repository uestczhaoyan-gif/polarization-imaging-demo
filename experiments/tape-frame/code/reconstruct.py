"""Reproduce this case using the shared command-line implementation."""
from pathlib import Path
import subprocess, sys
CASE = Path(__file__).resolve().parents[1]
ROOT = next(p for p in CASE.parents if (p/'reconstruction/reconstruct.py').is_file())
if __name__ == '__main__':
    subprocess.run([sys.executable, str(ROOT/'reconstruction/reconstruct.py'),
                    'run', '--config', str(CASE/'config.json'), '--overwrite'], check=True)
