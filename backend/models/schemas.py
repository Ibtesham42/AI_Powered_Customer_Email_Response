from pydantic import BaseModel

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    company_name: str


class LoginRequest(BaseModel):
    email: str
    password: str