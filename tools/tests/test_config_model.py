"""配置修改必须保真、拒绝不安全输入，并可追溯恢复。"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from config_model import FIELDS, MM_DISPLAY_KEYS, parse_form, read_values, render, save_header, validate


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.original=(ROOT/'firmware/Core/Inc/snake_scan_config.h').read_bytes()
        self.values=read_values(self.original)
        self.form={f.key:str(self.values[f.key]/1000 if f.key in MM_DISPLAY_KEYS else self.values[f.key]) for f in FIELDS}

    def test_default_roundtrip_preserves_every_byte(self):
        self.assertEqual(render(self.original,self.values),self.original)
        self.assertEqual(parse_form(self.form),self.values)

    def test_speed_direction_and_only_requested_macros_change(self):
        self.form['SCAN_SPEED_UM_PER_SEC']='2'
        self.form['X_FIRST_PASS_DIRECTION']='0'
        self.form['Y_STEP_DIRECTION']='1'
        values=parse_form(self.form)
        self.assertEqual(values['SCAN_SPEED_UM_PER_SEC'],2000)
        self.assertEqual(values['X_ALTERNATE_PASS_DIRECTION'],1)
        self.assertEqual(validate(values)['rpm'],120)
        edited=render(self.original,values)
        self.assertEqual(render(edited,self.values),self.original)
        self.assertEqual(edited.count(b'\r\n'),self.original.count(b'\r\n'))

    def test_reject_bad_inputs_and_physical_constraints(self):
        for key,value in [('SCAN_SPEED_UM_PER_SEC','nan'),('SCAN_SPEED_UM_PER_SEC','0.0001'),
                          ('SCAN_SPEED_UM_PER_SEC','100'),('MASK_SCAN_WIDTH_UM','0.001'),
                          ('MASK_SCAN_WIDTH_UM','101'),('MASK_SCAN_HEIGHT_UM','99'),
                          ('SCAN_LINE_STEP_UM','0'),('Y_AXIS_ADDR','2'),
                          ('LEAD_UM_PER_REV','999'),('X_FIRST_PASS_DIRECTION','2'),
                          ('MOTOR_MICROSTEP','257'),('SCAN_ACCELERATION','256')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                parse_form(dict(self.form,**{key:value}))

    def test_uint32_overflow_rejected(self):
        values=self.values.copy()
        values.update(MOTOR_FULL_STEPS_PER_REV=10000,MOTOR_MICROSTEP=256,
                      MASK_SCAN_WIDTH_UM=4294000,X_AXIS_MAX_SAFE_TRAVEL_UM=4294000)
        with self.assertRaises(ValueError):validate(values)

    def test_backup_record_and_external_edit_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);header=folder/'config.h';header.write_bytes(self.original)
            values=self.values.copy();values['SCAN_SPEED_UM_PER_SEC']=2000
            backup=save_header(header,self.original,values,folder/'history')
            self.assertEqual(backup.read_bytes(),self.original)
            record=json.loads(next((folder/'history').glob('*.json')).read_text(encoding='utf-8'))
            self.assertEqual(record['parameters']['SCAN_SPEED_UM_PER_SEC'],2000)
            self.assertFalse(record['flashed'])
            edited=header.read_bytes()
            with self.assertRaises(ValueError):save_header(header,self.original,self.values,folder/'history')
            self.assertEqual(header.read_bytes(),edited)
            self.assertIsNone(save_header(header,edited,values,folder/'history'))

    def test_unrecognized_header_is_not_rewritten(self):
        for source in [self.original.replace(b'100000UL',b'(100000UL)',1),self.original+self.original]:
            with self.assertRaises(ValueError):render(source,self.values)

    def test_fractional_distances_are_exact_pulses(self):
        for mm,um,pulses in [('0.5',500,1600),('0.1',100,320),('0.05',50,160),('0.005',5,16)]:
            with self.subTest(mm=mm):
                v=parse_form(dict(self.form,MASK_SCAN_WIDTH_UM=mm,SCAN_LINE_STEP_UM=mm))
                self.assertEqual(v['SCAN_LINE_STEP_UM'],um)
                info=validate(v)
                self.assertEqual(info['x_pulses'],pulses)
                self.assertEqual(info['y_pulses'],pulses)
                self.assertEqual(info['minimum_step_mm'],0.005)
                self.assertEqual(read_values(render(self.original,v)),v)

    def test_subpulse_precision_division_and_more_than_65535_rows(self):
        for mm in ['0.001','0.003','0.0003125','0.015']:
            with self.subTest(mm=mm),self.assertRaises(ValueError):
                parse_form(dict(self.form,SCAN_LINE_STEP_UM=mm))
        v=parse_form(dict(self.form,MASK_SCAN_HEIGHT_UM='400',Y_AXIS_MAX_SAFE_TRAVEL_UM='400',SCAN_LINE_STEP_UM='0.005'))
        self.assertEqual(validate(v)['rows'],80000)
        v=parse_form(dict(self.form,MASK_SCAN_WIDTH_UM='80',MASK_SCAN_HEIGHT_UM='80',SCAN_LINE_STEP_UM='0.5',SCAN_SPEED_UM_PER_SEC='2'))
        self.assertEqual(validate(v)['ideal_motion_seconds'],6440)


if __name__=='__main__':unittest.main()
