#!/usr/bin/env python3
import argparse, json, sys
from v1_common import AsterV1Client, format_exchange_response, load_env_file, require_env

p=argparse.ArgumentParser(description='Cancel Aster V1 order')
p.add_argument('--symbol', required=True)
p.add_argument('--order-id')
p.add_argument('--orig-client-order-id')
p.add_argument('--env-file')
p.add_argument('--base-url', default='https://fapi.asterdex.com')
p.add_argument('--recv-window', type=int, default=5000)
args=p.parse_args()

try:
    if bool(args.order_id)==bool(args.orig_client_order_id):
        raise ValueError('Provide exactly one of --order-id or --orig-client-order-id')
    if args.env_file: load_env_file(args.env_file)
    c=AsterV1Client(args.base_url, require_env('ASTER_API_KEY'), require_env('ASTER_SECRET_KEY'), args.recv_window)
    params={'symbol':args.symbol}
    if args.order_id: params['orderId']=args.order_id
    else: params['origClientOrderId']=args.orig_client_order_id
    code,body=c.signed_request('DELETE','/fapi/v1/order',params)
    print(json.dumps({'cancel_order':format_exchange_response(code,body)},ensure_ascii=False))
    sys.exit(0 if code==200 else 1)
except Exception as e:
    print(json.dumps({'error':str(e)},ensure_ascii=False)); sys.exit(1)
