import requests
import jwt
import json


def get_openid_keys(tenant_id):
    openid_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    keys = requests.get(openid_url).json()["keys"]
    return {key["kid"]: key for key in keys}


def decode_and_verify_jwt(token, tenant_id, app_id):
    unverified_header = jwt.get_unverified_header(token)

    kid = unverified_header["kid"]

    openid_keys = get_openid_keys(tenant_id)

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(openid_keys[kid]))

    payload = jwt.decode(
        token,
        public_key,
        algorithms="RS256",
        audience=app_id,
        issuer=f"https://sts.windows.net/{tenant_id}/",
    )
    return payload
