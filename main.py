import json
import re
from pathlib import Path
from datetime import date, datetime
from enum import Enum
from threading import Lock

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field, field_validator

app = FastAPI()

DATA_FILE = Path("requests.json")
file_lock = Lock()


class Reason(str, Enum):
    no_network = "нет доступа к сети"
    phone_not_working = "не работает телефон"
    no_emails = "не приходят письма"


class SubscriberRequest(BaseModel):
    surname: str
    name: str
    birth_date: date
    phone: str
    email: EmailStr
    reasons: list[Reason] = Field(min_length=1)
    problem_datetime: datetime

    @field_validator("surname", "name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[А-ЯЁ][а-яё]*", value):
            raise ValueError(
                "Первая буква должна быть заглавной, допускается только кириллица"
            )
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not re.fullmatch(r"\+?[0-9]{10,15}", value):
            raise ValueError("Некорректный номер телефона")
        return value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Дата рождения должна быть в прошлом")
        return value

    @field_validator("problem_datetime")
    @classmethod
    def validate_problem_datetime(cls, value: datetime) -> datetime:
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        if value > now:
            raise ValueError("Дата обнаружения проблемы не может быть в будущем")
        return value


@app.post("/requests/")
def create_request(request: SubscriberRequest):
    data = request.model_dump(mode="json")

    with file_lock:
        if DATA_FILE.exists():
            try:
                requests = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                requests = []
        else:
            requests = []

        requests.append(data)
        DATA_FILE.write_text(
            json.dumps(requests, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {"status": "ok", "request": data}
