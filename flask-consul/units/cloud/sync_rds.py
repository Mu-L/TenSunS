#!/usr/bin/python3
import requests,json
from units import consul_kv
from config import consul_token,consul_url,vendors,regions
from units.config_log import *
headers = {'X-Consul-Token': consul_token}
geturl = f'{consul_url}/agent/services'
delurl = f'{consul_url}/agent/service/deregister'
puturl = f'{consul_url}/agent/service/register'
def w2consul(vendor,account,region,rds_dict):
    service_name = f'{vendor}_{account}_rds'
    params = {'filter': f'Service == "{service_name}" and "{region}" in Tags and Meta.account == "{account}"'}
    try:
        consul_rds_iid_list = requests.get(geturl, headers=headers, params=params).json().keys()
    except:
        consul_rds_iid_list = []
        
    #在consul中删除云厂商不存在的rds
    for del_rds in [x for x in consul_rds_iid_list if x not in rds_dict.keys()]:
        dereg = requests.put(f'{delurl}/{del_rds}', headers=headers)
        if dereg.status_code == 200:
            logger.info(f"code: 20000, data: {account}-删除成功！")
        else:
            logger.info(f"code: 50000, data: {dereg.status_code}:{dereg.text}")
    off,on = 0,0
    for k,v in rds_dict.items():
        iid = k
        #对consul中关机的rds做标记。
        if v['status'] in ['SHUTDOWN','非运行中']:
            off = off + 1
            tags = ['OFF',v['itype'],v['ver'], region]
            stat = 'off'
        else:
            on = on + 1
            tags = ['ON',v['itype'],v['ver'],region]
            stat = 'on'
        custom_rds = consul_kv.get_value(f'ConsulManager/assets/sync_rds_custom/{iid}')
        port = custom_rds.get('port')
        ip = custom_rds.get('ip')
        if port == None:
            port = v['port']
        if ip == None:
            ip = v['ip']
        instance = f'{ip}:{port}'
        if vendor == 'alicloud' and iid in consul_rds_iid_list and v['cpu'] == '无':
            continue

        data = {
            'id': iid,
            'name': service_name,
            'Address': ip,
            'port': port,
            'tags': tags,
            'Meta': {
                'iid': iid,
                'name': v['name'],
                'region': regions[vendor].get(region,'未找到'),
                'group': v['group'],
                'instance': instance,
                'account': account,
                'itype': v['itype'],
                'vendor': vendors.get(vendor,'未找到'),
                'disk': v['disk'],
                'cpu': v['cpu'],
                'mem': v['mem'],
                'ver': v['ver'],
                'domain':v['domain'],
                'exp': v['exp'],
                'stat': stat,
                'team': v.get('team','无')
            },
            "check": {
                "tcp": f"{ip}:{port}",
                "interval": "60s"
            }
        }
        reg = requests.put(puturl, headers=headers, data=json.dumps(data))
        if reg.status_code == 200:
            pass
        else:
            logger.info(f"{account}:code: 5000, data: {reg.status_code}:{reg.text}")
    return off,on
