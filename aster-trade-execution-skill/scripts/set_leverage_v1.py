#!/usr/bin/env python3
import argparse, json, sys
from v1_common import AsterV1Client, format_exchange_response, load_env_file, require_env

p=argparse.ArgumentParser(description='Set Aster V1 leverage')
p.add_argument('--symbol', required=True)
p.add_argument('--leverage', required=True, type=int)
p.add_argument('--env-file')
p.add_argument('--base-url', default='https://fapi.asterdex.com')
p.add_argument('--recv-window', type=int, default=5000)
args=p.parse_args()

try:
    if args.leverage<=0: raise ValueError('--leverage must be > 0')
    if args.env_file: load_env_file(args.env_file)
    c=AsterV1Client(args.base_url, require_env('ASTER_API_KEY'), require_env('ASTER_SECRET_KEY'), args.recv_window)
    code,body=c.signed_request('POST','/fapi/v1/leverage',{'symbol':args.symbol,'leverage':str(args.leverage)})
    print(json.dumps({'set_leverage':format_exchange_response(code,body)},ensure_ascii=False))
    sys.exit(0 if code==200 else 1)
except Exception as e:
    print(json.dumps({'error':str(e)},ensure_ascii=False)); sys.exit(1)
