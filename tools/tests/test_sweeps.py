import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_lab import configuration,prepare
from analyze_sweep import summarize

def profile(kind='minimum_distance'):
    return json.loads((ROOT/'labs/03_stage_characterization/presets'/f'{kind}.json').read_text(encoding='utf-8'))

class SweepTests(unittest.TestCase):
    def test_offline_three_kinds_and_exact_single_pulse(self):
        for kind in ('minimum_distance','minimum_speed','maximum_speed'):
            p=profile(kind);_,_,r=configuration(p)
            self.assertEqual(r['lab']['LAB_LOG_ENABLE'],0)
            for stage in r['sweep']['levels']:
                group=[x for x in r['sweep']['plan'] if x['stage']==stage['stage']]
                self.assertEqual(group[-1]['commanded_position_mm'],0)
            if kind=='minimum_distance':
                self.assertEqual(r['sweep']['levels'][-1]['pulses'],1)
                self.assertAlmostEqual(r['sweep']['minimum_command_mm'],.0003125)
                self.assertAlmostEqual(r['sweep']['angle_per_pulse_deg'],.1125)

    def test_invalid_order_subpulse_duplicate_rpm_and_travel(self):
        cases=[]
        p=profile();p['sweep']['levels']=['.0001'];cases.append(p)
        p=profile();p['sweep']['levels']=['.01','.1'];cases.append(p)
        p=profile('minimum_speed');p['sweep']['levels']=['.02','.019'];cases.append(p)
        p=profile('minimum_speed');p['sweep']['levels']=['.001'];cases.append(p)
        p=profile();p['sweep']['preload_mm']='100';cases.append(p)
        p=profile('maximum_speed');p['sweep']['levels']=['51'];cases.append(p)
        p=profile();p['lab']['LAB_TEST_DWELL_MS']=0;cases.append(p)
        for p in cases:
            with self.assertRaises(ValueError):configuration(p)

    def test_prepared_header_plan_and_blank_results(self):
        with tempfile.TemporaryDirectory() as temp:
            out=prepare(profile(),Path(temp)/'test')
            record=json.loads((out/'prepared-config.json').read_text(encoding='utf-8'))
            with (out/'measurement-plan.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertIsNone(summarize(record,rows,.0001,.001)['best_tested_passing_value'])
            for row in rows:
                row.update(measured_position_mm=row['commanded_position_mm'],completed_yes_no='yes',stable_yes_no='yes')
            self.assertAlmostEqual(summarize(record,rows,.0001,.001)['best_tested_passing_value'],.0003125)
            # Coarser measurement cannot establish the smallest nominal steps.
            self.assertGreater(summarize(record,rows,.001,.001)['best_tested_passing_value'],.0003125)
            rows[0]['pulses']='1'
            with self.assertRaises(ValueError):summarize(record,rows,.0001,.001)

    def test_speed_failure_is_not_a_pass(self):
        _,_,r=configuration(profile('maximum_speed'));rows=copy.deepcopy(r['sweep']['plan'])
        for row in rows:row.update(completed_yes_no='yes',stable_yes_no='yes')
        for row in rows:
            if row['stage']==5:row['stable_yes_no']='no'
        self.assertEqual(summarize(r,rows)['best_tested_passing_value'],4)
        for row in rows:row['completed_yes_no']=''
        self.assertIsNone(summarize(r,rows)['best_tested_passing_value'])

if __name__=='__main__':unittest.main()
