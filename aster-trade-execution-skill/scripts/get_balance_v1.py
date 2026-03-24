#!/usr/bin/env python3
import argparse, json, sys
from v1_common import AsterV1Client, format_exchange_response, load_env_file, require_env

p=argparse.ArgumentParser(description='Get Aster V1 balance')
p.add_argument('--env-file')
p.add_argument('--base-url', default='https://fapi.asterdex.com')
p.add_argument('--recv-window', type=int, default=5000)
args=p.parse_args()

try:
    if args.env_file: load_env_file(args.env_file)
    c=AsterV1Client(args.base_url, require_env('ASTER_API_KEY'), require_env('ASTER_SECRET_KEY'), args.recv_window)
    code,body=c.signed_request('GET','/fapi/v1/balance',{})
    print(json.dumps({'balance':format_exchange_response(code,body)},ensure_ascii=False))
    sys.exit(0 if code==200 else 1)
except Exception as e:
    print(json.dumps({'error':str(e)},ensure_ascii=False)); sys.exit(1)
