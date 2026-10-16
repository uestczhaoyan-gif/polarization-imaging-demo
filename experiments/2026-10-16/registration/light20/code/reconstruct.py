from pathlib import Path
import sys
CASE=Path(__file__).resolve().parents[1]
ROOT=next(p for p in CASE.parents if (p/'reconstruction/snake_scan').is_dir())
sys.path.insert(0,str(ROOT/'reconstruction'))
from snake_scan.pipeline import reconstruct
from snake_scan.continuous_report import write_outputs
if __name__=='__main__':
    output=ROOT/'local/reconstruction/2026-10-16'/CASE.parent.name/CASE.name
    write_outputs(reconstruct(CASE/'config.json'),output)
    print(output)
