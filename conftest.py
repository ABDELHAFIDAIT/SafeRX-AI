import sys
import os
from unittest.mock import MagicMock, PropertyMock
from datetime import datetime, timezone


ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


os.environ.setdefault("DATABASE_URL",     "sqlite:///:memory:")
os.environ.setdefault("LLM_PROVIDER",     "none")
os.environ.setdefault("OLLAMA_BASE_URL",  "http://localhost:11434")
os.environ.setdefault("GEMINI_API_KEY",   "")
os.environ.setdefault("LR_MODEL_PATH",    "/tmp/lr_test_model.pkl")
os.environ.setdefault("LR_MIN_SAMPLES",   "20")
os.environ.setdefault("JWT_SECRET_KEY",   "test_secret_key_for_tests_only_32chars!")


def _mock_if_absent(module_name: str, mock_obj=None):
    """Injecte un mock dans sys.modules uniquement si le module est absent."""
    try:
        __import__(module_name)
    except ImportError:
        sys.modules[module_name] = mock_obj or MagicMock()


_mock_if_absent("sqlalchemy")
_mock_if_absent("sqlalchemy.orm")
_mock_if_absent("sqlalchemy.orm.session")
_mock_if_absent("sqlalchemy.ext.declarative")

if isinstance(sys.modules.get("sqlalchemy"), MagicMock):
    sa = sys.modules["sqlalchemy"]
    sa_orm = sys.modules["sqlalchemy.orm"]


    for attr in ["Column", "Integer", "String", "Boolean", "Float", "DateTime",
                 "JSON", "Enum", "ForeignKey", "func", "create_engine", "Text"]:
        setattr(sa, attr, MagicMock(return_value=None))


    class _FakeBase:
        __tablename__ = ""
        metadata = MagicMock()
        metadata.create_all = MagicMock()

    sa_orm.declarative_base = MagicMock(return_value=_FakeBase)
    sa_orm.sessionmaker     = MagicMock(return_value=MagicMock)
    sa_orm.Session          = MagicMock
    sa_orm.selectinload     = MagicMock(side_effect=lambda x: x)
    sa_orm.relationship     = MagicMock(return_value=None)

_mock_if_absent("fastapi")
_mock_if_absent("fastapi.security")

if isinstance(sys.modules.get("fastapi"), MagicMock):
    fastapi_mock = sys.modules["fastapi"]

    class _HTTPException(Exception):
        def __init__(self, status_code=400, detail="error", headers=None):
            self.status_code = status_code
            self.detail      = detail
            self.headers     = headers
            super().__init__(detail)

    fastapi_mock.HTTPException = _HTTPException
    fastapi_mock.APIRouter     = MagicMock
    fastapi_mock.Depends       = MagicMock(side_effect=lambda x: x)
    fastapi_mock.FastAPI       = MagicMock
    fastapi_mock.Query         = MagicMock(return_value=None)
    fastapi_mock.status        = MagicMock()
    fastapi_mock.status.HTTP_201_CREATED        = 201
    fastapi_mock.status.HTTP_204_NO_CONTENT     = 204
    fastapi_mock.status.HTTP_400_BAD_REQUEST    = 400
    fastapi_mock.status.HTTP_401_UNAUTHORIZED   = 401
    fastapi_mock.status.HTTP_403_FORBIDDEN      = 403
    fastapi_mock.status.HTTP_404_NOT_FOUND      = 404
    fastapi_mock.status.HTTP_409_CONFLICT       = 409
    fastapi_mock.status.HTTP_422_UNPROCESSABLE_ENTITY = 422

    security_mock = sys.modules["fastapi.security"]
    security_mock.OAuth2PasswordBearer = MagicMock(return_value=MagicMock())
    security_mock.OAuth2PasswordRequestForm = MagicMock

_mock_if_absent("jose")
_mock_if_absent("jose.jwt")
_mock_if_absent("jose.exceptions")
if isinstance(sys.modules.get("jose"), MagicMock):
    class _JWTError(Exception): pass
    sys.modules["jose"].JWTError = _JWTError
    sys.modules["jose.jwt"].decode  = MagicMock(return_value={"sub": "test@saferx.ma"})
    sys.modules["jose.jwt"].encode  = MagicMock(return_value="mock_token")

_mock_if_absent("passlib")
_mock_if_absent("passlib.context")
if isinstance(sys.modules.get("passlib"), MagicMock):
    ctx = MagicMock()
    ctx.verify = MagicMock(return_value=True)
    ctx.hash   = MagicMock(return_value="$2b$hashed")
    sys.modules["passlib.context"].CryptContext = MagicMock(return_value=ctx)

_mock_if_absent("pydantic")
_mock_if_absent("pydantic_settings")
if isinstance(sys.modules.get("pydantic"), MagicMock):
    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        model_config = {}
        def model_dump(self, **kwargs): return self.__dict__
    sys.modules["pydantic"].BaseModel  = _BaseModel
    sys.modules["pydantic"].Field      = MagicMock(return_value=None)
    sys.modules["pydantic"].field_validator = MagicMock(return_value=lambda f: f)

for mod in ["langchain_core", "langchain_core.messages",
            "langchain_ollama", "langchain_google_genai"]:
    _mock_if_absent(mod)

if isinstance(sys.modules.get("langchain_core"), MagicMock):
    class _HumanMessage:
        def __init__(self, content): self.content = content
    sys.modules["langchain_core.messages"].HumanMessage = _HumanMessage

import smtplib as _smtplib
_real_smtp = _smtplib.SMTP
class _MockSMTP:
    def __init__(self, *a, **kw): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def ehlo(self): pass
    def starttls(self): pass
    def login(self, *a): pass
    def sendmail(self, *a): pass
_smtplib.SMTP = _MockSMTP


class _FakeBase:
    __tablename__ = ""
    metadata = MagicMock()
    metadata.create_all = MagicMock()

_db_base = MagicMock()
_db_base.Base = _FakeBase
sys.modules.setdefault("backend.app.db.base", _db_base)

_db_session = MagicMock()
_db_session.SessionLocal = MagicMock()
_db_session.engine       = MagicMock()
sys.modules.setdefault("backend.app.db.session", _db_session)