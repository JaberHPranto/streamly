import boto3
from fastapi import Cookie, HTTPException

cognito_client = boto3.client("cognito-idp", region_name="ap-southeast-1")


def _get_user_from_cognito(access_token: str):
    try:
        response = cognito_client.get_user(AccessToken=access_token)
        return {attr["Name"]: attr["Value"] for attr in response["UserAttributes"]}

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def get_current_user(access_token: str | None = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = _get_user_from_cognito(access_token)

    return user
