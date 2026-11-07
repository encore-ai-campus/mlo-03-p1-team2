"""Collect Prometheus samples without needing a Grafana login."""
import time

PROMETHEUS = 'http://192.168.0.187:9090'
QUERIES = {
    'up': 'up',
    'cpu_percent': '100 * (1 - avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[1m])))',
    'memory_available_bytes': 'node_memory_MemAvailable_bytes',
    'disk_available_bytes': 'node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs",mountpoint="/"}',
    'boot_time': 'node_boot_time_seconds',
    'db_connections': 'mysql_global_status_threads_connected',
    'db_connection_limit': 'mysql_global_variables_max_connections',
    'db_lock_time': 'mysql_global_status_innodb_row_lock_time',
    'mongo_connections': 'mongodb_ss_connections',
}
CRITICAL_HOSTS = {'192.168.0.171', '192.168.0.174', '192.168.0.175', '192.168.0.176',
                  '192.168.0.177', '192.168.0.178', '192.168.0.179'}


async def collect(client):
    data = {'at': time.time(), 'metrics': {}}
    for name, query in QUERIES.items():
        response = await client.get(PROMETHEUS + '/api/v1/query', params={'query': query})
        response.raise_for_status()
        body = response.json()
        if body.get('status') != 'success':
            raise RuntimeError('Prometheus query failed: ' + name)
        data['metrics'][name] = body['data']['result']
    return data


def reason(sample, baseline):
    for name in QUERIES:
        rows = sample['metrics'].get(name, [])
        if not rows:
            return 'required_monitoring_series_missing:' + name
        if any(sample['at'] - float(row['value'][0]) > 120 for row in rows):
            return 'required_monitoring_series_stale:' + name
        if name in ('up', 'cpu_percent', 'memory_available_bytes', 'disk_available_bytes', 'boot_time'):
            hosts = {r['metric'].get('instance', '').split(':')[0] for r in rows}
            if not CRITICAL_HOSTS <= hosts:
                return 'critical_host_metrics_missing:' + name
    up_instances = {r['metric'].get('instance') for r in sample['metrics']['up']}
    if not {'192.168.0.171:9104', '192.168.0.174:9216'} <= up_instances:
        return 'database_exporter_missing'
    for row in sample['metrics']['up']:
        host = row['metric'].get('instance', '').split(':')[0]
        if host in CRITICAL_HOSTS and float(row['value'][1]) != 1:
            return 'critical_monitoring_target_down'
    for row in sample['metrics']['disk_available_bytes']:
        host = row['metric'].get('instance', '').split(':')[0]
        if host in CRITICAL_HOSTS and float(row['value'][1]) < 1024 ** 3:
            return 'critical_host_disk_below_1GiB'
    old_boot = {r['metric'].get('instance'): r['value'][1] for r in baseline['metrics']['boot_time']}
    for row in sample['metrics']['boot_time']:
        instance = row['metric'].get('instance', '')
        if instance.split(':')[0] in CRITICAL_HOSTS and instance in old_boot and old_boot[instance] != row['value'][1]:
            return 'critical_host_restarted'
    connections = sample['metrics']['db_connections']
    limits = sample['metrics']['db_connection_limit']
    if connections and limits and max(float(r['value'][1]) for r in connections) >= min(float(r['value'][1]) for r in limits):
        return 'database_connections_exhausted'
    return None
