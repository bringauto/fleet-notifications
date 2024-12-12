from __future__ import annotations
from typing import Literal

import pydantic


LoggingLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ScriptConfig(pydantic.BaseModel):
    logging: Logging
    http_server: HTTPServer
    fleet_management_server: FleetManagementServer
    twilio: Twilio
    database: Database


class Logging(pydantic.BaseModel):
    console: HandlerConfig
    file: HandlerConfig

    class HandlerConfig(pydantic.BaseModel):
        level: LoggingLevel
        use: bool
        path: str = ""

        @pydantic.field_validator("level", mode="before")
        @classmethod
        def validate_level(cls, level: str) -> str:
            return level.upper()


class HTTPServer(pydantic.BaseModel):
    port: pydantic.PositiveInt


class FleetManagementServer(pydantic.BaseModel):
    base_uri: pydantic.AnyUrl
    api_key: str


class Twilio(pydantic.BaseModel):
    account_sid: str
    auth_token: str
    from_number: str
    play_sound_url: pydantic.AnyUrl
    repeated_calls: pydantic.PositiveInt
    call_status_timeout_s: pydantic.PositiveInt
    car_action_change_timeout_s: pydantic.PositiveInt
    allowed_incoming_phone_numbers: dict[str, pydantic.PositiveInt]


class Database(pydantic.BaseModel):
    connection: Connection

    class Connection(pydantic.BaseModel):
        username: str
        password: str
        location: str = pydantic.Field(min_length=1)
        port: int
        database_name: str
