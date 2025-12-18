import os
import time
import jwt
import json
import yandexcloud

from yandex.cloud.iam.v1.iam_token_service_pb2 import (CreateIamTokenRequest)
from yandex.cloud.iam.v1.iam_token_service_pb2_grpc import IamTokenServiceStub

key_path = '/app/iam-key/key.json'

def openfile():
    with open(key_path, 'r') as f:
      obj = f.read()
      obj = json.loads(obj)
      private_key = obj['private_key']
      key_id = obj['id']
      service_account_id = obj['service_account_id']

    sa_key = {
        "id": key_id,
        "service_account_id": service_account_id,
        "private_key": private_key
    }
    return sa_key, private_key, key_id, service_account_id

def CreateJWT():
    info = openfile()
    now = int(time.time())
    payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': info[3],
            'iat': now,
            'exp': now + 3600
        }
    encoded_token = jwt.encode(
        payload,
        info[1],
        algorithm='PS256',
        headers={'kid': info[2]}
    )
    return encoded_token

def CreateIAMToken():
    jwt = CreateJWT()
    info = openfile()

    sdk = yandexcloud.SDK(service_account_key=info[0])
    iam_service = sdk.client(IamTokenServiceStub)
    iam_token = iam_service.Create(
        CreateIamTokenRequest(jwt=jwt)
    )

    return iam_token.iam_token
