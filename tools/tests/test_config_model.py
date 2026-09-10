"""配置修改必须保真、拒绝不安全输入，并可追溯恢复。"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from config_model import FIELDS, parse_form, read_values, render, save_header, validate


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.original=(ROOT/'firmware/Core/Inc/snake_scan_config.h').read_bytes()
        self.values=read_values(self.original)
        self.form={f.key:str(self.values[f.key]) for f in FIELDS}
        self.form['SCAN_SPEED_UM_PER_SEC']=str(self.values['SCAN_SPEED_UM_PER_SEC']/1000)

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
                          ('SCAN_SPEED_UM_PER_SEC','100'),('MASK_SCAN_WIDTH_MM','1.5'),
                          ('MASK_SCAN_WIDTH_MM','101'),('MASK_SCAN_HEIGHT_MM','99'),
                          ('SCAN_LINE_STEP_MM','0'),('Y_AXIS_ADDR','2'),
                          ('LEAD_UM_PER_REV','999'),('X_FIRST_PASS_DIRECTION','2'),
                          ('MOTOR_MICROSTEP','257'),('SCAN_ACCELERATION','256')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                parse_form(dict(self.form,**{key:value}))

    def test_uint32_overflow_rejected(self):
        values=self.values.copy()
        values.update(MOTOR_FULL_STEPS_PER_REV=10000,MOTOR_MICROSTEP=256,
                      MASK_SCAN_WIDTH_MM=4294,X_AXIS_MAX_SAFE_TRAVEL_MM=4294)
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
        for source in [self.original.replace(b'1000UL',b'(1000UL)',1),self.original+self.original]:
            with self.assertRaises(ValueError):render(source,self.values)


if __name__=='__main__':unittest.main()
