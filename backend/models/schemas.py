from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class SignupRequest(BaseModel):
    """Signup payload. Every signup creates a new Company; the signer is its Owner."""

    full_name: str
    company_name: str
    email: EmailStr
    phone: str
    password: str
    verify_password: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str

    @field_validator(
        "full_name",
        "company_name",
        "phone",
        "address",
        "city",
        "state",
        "country",
        "postal_code",
    )
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupRequest":
        if self.password != self.verify_password:
            raise ValueError("password and verify_password do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    # Optional: browser clients send the refresh token in an httpOnly cookie
    # (audit H1) and omit the body; non-browser clients still pass it here.
    refresh_token: str | None = None


class DraftUpdate(BaseModel):
    """Body for editing/rewriting an AI draft."""

    text: str


class RejectRequest(BaseModel):
    """Body for rejecting a draft (escalates the Ticket)."""

    reason: str | None = None


class ForgotPasswordRequest(BaseModel):
    """Body for requesting a password-reset link."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body for completing a password reset."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value


class UrlIngestRequest(BaseModel):
    """Body for ingesting a web page into the knowledge base."""

    url: HttpUrl


class FaqIngestRequest(BaseModel):
    """Body for adding an FAQ entry to the knowledge base.

    Length caps (B-6) bound a single FAQ's embedding work and storage; a long
    document belongs in a file upload, not an FAQ entry.
    """

    question: str = Field(max_length=500)
    answer: str = Field(max_length=5000)

    @field_validator("question", "answer")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()


class MailboxConnectRequest(BaseModel):
    """Body for connecting a Company's support mailbox."""

    email_address: EmailStr
    app_password: str
    imap_host: str = "imap.gmail.com"
    smtp_host: str = "smtp.gmail.com"

    @field_validator("app_password")
    @classmethod
    def normalize_app_password(cls, value: str) -> str:
        # Gmail shows App Passwords in spaced groups ("abcd efgh ijkl mnop");
        # the real secret has no spaces. Strip all whitespace so a value
        # pasted either way works.
        cleaned = "".join(value.split())
        if not cleaned:
            raise ValueError("app_password must not be empty")
        return cleaned
