import secrets

import boto3
from botocore.exceptions import ClientError
from db.db import get_db
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from helper.auth_helper import get_secret_hash
from models.users import User
from schemas.auth import ConfirmUserPayload, LoginUserPayload, SignupUserPayload
from settings import Settings
from sqlalchemy.orm import Session

router = APIRouter()

settings = Settings()

COGNITO_CLIENT_ID = settings.COGNITO_CLIENT_ID
COGNITO_CLIENT_SECRET = settings.COGNITO_CLIENT_SECRET

cognito_client = boto3.client("cognito-idp", region_name="ap-southeast-1")


@router.post("/signup")
def signup_user(payload: SignupUserPayload, db: Session = Depends(get_db)):
    secret_hash = get_secret_hash(
        payload.email, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET
    )

    try:
        cognito_response = cognito_client.sign_up(
            ClientId=COGNITO_CLIENT_ID,
            SecretHash=secret_hash,
            Username=payload.email,
            Password=payload.password,
            UserAttributes=[
                {"Name": "email", "Value": payload.email},
                {"Name": "name", "Value": payload.name},
            ],
        )

        user = User(
            name=payload.name,
            email=payload.email,
            congnito_sub=cognito_response["UserSub"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    except cognito_client.exceptions.InvalidPasswordException as error:
        raise HTTPException(
            status_code=400,
            detail=error.response["Error"].get("Message", "Invalid password"),
        ) from error
    except cognito_client.exceptions.UsernameExistsException as error:
        raise HTTPException(status_code=409, detail="User already exists") from error
    except ClientError as error:
        raise HTTPException(
            status_code=400,
            detail=error.response["Error"].get("Message", "Could not sign up user"),
        ) from error

    return {"message": "User signed up successfully", "user": user}


@router.post("/login")
def login_user(payload: LoginUserPayload, response: Response):
    secret_hash = get_secret_hash(
        payload.email, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET
    )

    try:
        cognito_response = cognito_client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=COGNITO_CLIENT_ID,
            AuthParameters={
                "USERNAME": payload.email,
                "PASSWORD": payload.password,
                "SECRET_HASH": secret_hash,
            },
        )

        access_token = cognito_response["AuthenticationResult"]["AccessToken"]
        id_token = cognito_response["AuthenticationResult"]["IdToken"]
        refresh_token = cognito_response["AuthenticationResult"]["RefreshToken"]

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
        )

        return {
            "access_token": access_token,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "message": "Login successful",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@router.post("/confirm-signup")
def confirm_user(payload: ConfirmUserPayload):
    secret_hash = get_secret_hash(
        payload.email, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET
    )
    try:
        cognito_client.confirm_sign_up(
            ClientId=COGNITO_CLIENT_ID,
            Username=payload.email,
            ConfirmationCode=payload.code,
            SecretHash=secret_hash,
        )
        return {"message": "User confirmed successfully"}
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@router.post("/refresh")
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    user_cognito_sub: str | None = Cookie(None),
):
    if refresh_token is None or user_cognito_sub is None:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    secret_hash = get_secret_hash(
        user_cognito_sub, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET
    )
    try:
        cognito_response = cognito_client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
                "SECRET_HASH": secret_hash,
            },
        )

        access_token = cognito_response["AuthenticationResult"]["AccessToken"]
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return {"message": "Token refreshed successfully", "access_token": access_token}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
