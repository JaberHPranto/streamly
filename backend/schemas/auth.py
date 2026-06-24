from pydantic import BaseModel


class SignupUserPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginUserPayload(BaseModel):
    email: str
    password: str


class ConfirmUserPayload(BaseModel):
    email: str
    code: str
