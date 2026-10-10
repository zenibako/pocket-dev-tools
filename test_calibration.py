import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import calibration


def log(mode='reference', cycles=0):
    order=[(j,r) for j in range(16) for r in range(3)]
    order += [(16+s,r) for r in range(3) for s in [6,5,4,3,2,1,0,7]]
    lines=[f'CALINFO 0123456789abcdef {mode} cpu_hz=100000000 os_version=00000007 core_variant=0 caps_version=2',
           'CALPIXELS 12345678']
    lines += [f'CALRESULT {i} {j} {r} probe 10 80 {cycles} 00000001 00000001' for i,(j,r) in enumerate(order)]
    return '\n'.join(lines+['CALIBRATION PASS HAL init'])+'\n'


class CalibrationEvidenceTest(unittest.TestCase):
    def test_complete_log_and_different_valid_timing_match_reference(self):
        reference=calibration.parse(log(),'reference')
        actual=calibration.parse(log('hardware',100),'hardware')
        calibration.match_reference(actual,reference)
        self.assertEqual(len(actual['rows']),72)

    def test_incomplete_duplicate_reordered_and_failed_runs_rejected(self):
        text=log()
        first='CALRESULT 0 0 0 probe 10 80 0 00000001 00000001\n'
        for changed in [text.replace(first,''),text+first,
                        text.replace('CALRESULT 0 0 0','CALRESULT 0 1 0'),
                        text+'FRAMEHARNESS FAIL calibration oracle\n',
                        text.replace('CALIBRATION PASS HAL init',''),
                        text.replace('00000001 00000001','00000002 00000001',1)]:
            with self.subTest(log=changed[:100]),self.assertRaises(ValueError):calibration.parse(changed,'reference')

    def test_timing_mode_clock_and_capability_mismatches_rejected(self):
        for text,mode in [(log('rtl',0),'rtl'),(log('reference',1),'reference'),
                          (log('rtl',1),'hardware'),
                          (log('hardware',1).replace('cpu_hz=100000000','cpu_hz=75000000'),'hardware'),
                          (log('hardware',1).replace('caps_version=2','caps_version=1'),'hardware')]:
            with self.subTest(mode=mode),self.assertRaises(ValueError):calibration.parse(text,mode)

    def test_rtl_uart_recap_is_parsed_once_and_truncation_rejected(self):
        text=log('rtl',100)
        recap=text+'\n=== UART BEGIN ===\n'+text+'\n=== UART END ===\n'
        self.assertEqual(calibration.parse(recap,'rtl'),calibration.parse(text,'rtl'))
        with self.assertRaises(ValueError):calibration.parse(recap.replace('=== UART END ===',''),'rtl')

    def test_saved_log_stops_at_nul_and_accepts_crlf(self):
        text=log('hardware',100)
        saved=text.replace('\n','\r\n')+'\0'+log('hardware',99)+'FRAMEHARNESS FAIL stale run'
        self.assertEqual(calibration.parse(saved,'hardware'),calibration.parse(text,'hardware'))

    def test_instance_uses_dedicated_second_save_slot(self):
        instance=json.loads((Path(calibration.__file__).parent/'calibration/pocket-instance.json').read_text())
        slots={s['id']:s['filename'] for s in instance['instance']['data_slots']}
        self.assertEqual(slots[11],'calibration_log.sav')
        self.assertEqual(slots[1],'os09.bin')
        self.assertEqual(slots[3],'os25_calibration.elf')
        self.assertFalse(any(s.startswith(('undertale_','deltarune_')) for s in slots.values()))

    def test_matching_reported_value_and_expected_cannot_override_reference(self):
        ref=calibration.parse(log(),'reference')
        for field,value in [('build_id','ffffffffffffffff'),('pixels','87654321')]:
            actual=copy.deepcopy(ref);actual[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):calibration.match_reference(actual,ref)
        for field,value in [('iterations',20),('operations',10),('name','other'),('value',2),('expected',2)]:
            actual=copy.deepcopy(ref);actual['rows'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):calibration.match_reference(actual,ref)
        actual=copy.deepcopy(ref);actual['rows'][0].update(value=2,expected=2)
        with self.assertRaises(ValueError):calibration.match_reference(actual,ref)

    def test_changed_hardware_elf_rejected_before_log_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);(d/'app.elf').write_bytes(b'calibrated');(d/'other.elf').write_bytes(b'different')
            with patch.object(calibration,'checked',return_value=(d,{},{})),self.assertRaisesRegex(ValueError,'Hardware ELF differs'):
                calibration.compare(d,d/'other.elf',d/'missing.log','test')

    def test_comparison_saves_ratios_and_preserves_supplied_log(self):
        # Synthetic parser fixture only: never a claim of device execution.
        reference=calibration.parse(log(),'reference')
        replay={'actual':calibration.parse(log('rtl',50),'rtl')}
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);(d/'app.elf').write_bytes(b'identical ELF')
            supplied=d/'supplied.log';supplied.write_bytes(log('hardware',100).encode()+b'\0\xff\x80stale slot bytes')
            before=supplied.read_bytes()
            for name in ['quiet-on','scanout-on']:
                (d/name).mkdir();(d/name/'results.json').write_text('{}')
            with patch.object(calibration,'checked',return_value=(d,{},{})),\
                 patch.object(calibration,'checked_reference',return_value=reference),\
                 patch.object(calibration,'verify_replay',return_value=replay):
                calibration.compare(d,d/'app.elf',supplied,'synthetic unit fixture')
                with self.assertRaisesRegex(ValueError,'Preserve previous hardware comparison'):
                    calibration.compare(d,d/'app.elf',supplied,'synthetic unit fixture')
            saved=list(d.glob('hardware-*/results.json'))
            self.assertEqual(len(saved),1)
            result=json.loads(saved[0].read_text())
            self.assertEqual(len(result['rows']),24)
            self.assertTrue(all(r['hardware_to_quiet_ratio']==2 for r in result['rows']))
            self.assertFalse(result['core_identity_independently_verified'])
            self.assertEqual(supplied.read_bytes(),before)


if __name__=='__main__':unittest.main()
