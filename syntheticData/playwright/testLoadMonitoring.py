import copy
import unittest
import time

from syntheticData.playwright.loadMonitoring import reason, CRITICAL_HOSTS, QUERIES


def healthy():
    stamp = time.time()
    metrics = {k: [{'metric': {'instance': host + ':9100'}, 'value': [stamp, '1']}
                   for host in CRITICAL_HOSTS] for k in QUERIES}
    for row in metrics['disk_available_bytes']:
        row['value'][1] = str(10 * 1024**3)
    metrics['db_connections'] = [{'metric': {'instance': '192.168.0.171:9104'}, 'value': [stamp, '2']}]
    metrics['db_connection_limit'] = [{'metric': {'instance': '192.168.0.171:9104'}, 'value': [stamp, '150']}]
    for instance in ('192.168.0.171:9104', '192.168.0.174:9216'):
        metrics['up'].append({'metric': {'instance': instance}, 'value': [stamp, '1']})
    return {'at': stamp, 'metrics': metrics}


class MonitorTests(unittest.TestCase):
    def test_unrelated_old_outages_do_not_mask_new_critical_outages(self):
        baseline = healthy()
        baseline['metrics']['up'].append({'metric': {'instance': '192.168.0.172:9100'}, 'value': [time.time(), '0']})
        self.assertIsNone(reason(baseline, baseline))
        sample = copy.deepcopy(baseline)
        sample['metrics']['up'].append({'metric': {'instance': '192.168.0.175:9100'}, 'value': [time.time(), '0']})
        self.assertEqual(reason(sample, baseline), 'critical_monitoring_target_down')

    def test_empty_or_stale_required_metrics_fail_closed(self):
        for key in QUERIES:
            baseline = healthy()
            sample = copy.deepcopy(baseline)
            sample['metrics'][key] = []
            self.assertIsNotNone(reason(sample, baseline), key)
        baseline = healthy()
        sample = copy.deepcopy(baseline)
        sample['metrics']['up'][0]['value'][0] -= 600
        self.assertIsNotNone(reason(sample, baseline))

    def test_disappearing_critical_host_fails_closed(self):
        baseline = healthy()
        sample = copy.deepcopy(baseline)
        sample['metrics']['cpu_percent'] = [r for r in sample['metrics']['cpu_percent']
                                           if not r['metric']['instance'].startswith('192.168.0.175:')]
        self.assertIsNotNone(reason(sample, baseline))
