from typing import Optional, Callable
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase

_connection_source: Optional[Engine] = None


class CannotConnectToDatabase(Exception):
    pass


class ConnectionSourceNotSet(Exception):
    pass


class InvalidConnectionArguments(Exception):
    pass


class Base(DeclarativeBase):
    pass


def get_connection_source() -> Engine:
    """Return the SQLAlchemy engine object used to connect to the database and
    raise exception if the engine object was not set yet.
    """
    global _connection_source
    if _connection_source is None:
        raise ConnectionSourceNotSet()
    else:
        assert isinstance(_connection_source, Engine)
        return _connection_source


def set_db_connection(
    dblocation: str,
    username: str = "",
    password: str = "",
    db_name: str = "",
    after_connect: tuple[Callable[[], None], ...] = (),
) -> None:

    """Create SQLAlchemy engine object used to connect to the database.
    Set module-level variable _connection_source to the new engine object."""

    global _connection_source
    source = _new_connection_source(
        dialect="postgresql",
        dbapi="psycopg",
        dblocation=dblocation,
        username=username,
        password=password,
        db_name=db_name,
    )
    _connection_source = source
    assert _connection_source is not None
    create_all_tables(source)
    for foo in after_connect:
        foo()


def set_test_db_connection(dblocation: str = "", db_name: str = "") -> None:
    """Create test SQLAlchemy engine object used to connect to the database using SQLite.
    No username or password required.
    Set module-level variable _connection_source to the new engine object."""
    global _connection_source
    source = _new_connection_source(
        dialect="sqlite", dbapi="pysqlite", dblocation=dblocation, db_name=db_name
    )
    _connection_source = source
    assert _connection_source is not None
    create_all_tables(source)


def create_all_tables(source: Engine) -> None:
    Base.metadata.create_all(source)


def _new_connection_source(
    dialect: str,
    dbapi: str,
    dblocation: str,
    username: str = "",
    password: str = "",
    db_name: str = "",
    *args,
    **kwargs,
) -> Engine:

    try:
        url = _engine_url(dialect, dbapi, username, password, dblocation, db_name)
        engine = create_engine(url, *args, **kwargs)
        if engine is None:
            raise InvalidConnectionArguments(
                "Could not create new connection source ("
                f"{dialect},'+',{dbapi},://...{dblocation})"
            )
    except:
        raise InvalidConnectionArguments(
            "Could not create new connection source (" f"{dialect},'+',{dbapi},://...{dblocation})"
        )

    try:
        with engine.connect():
            pass
    except:
        raise CannotConnectToDatabase(
            "Could not connect to the database with the given connection parameters: \n"
            f"{url}\n\n"
            "Check the location, port number, username and password."
        )
    return engine


def _engine_url(
    dialect: str, dbapi: str, username: str, password: str, dblocation: str, db_name: str = ""
) -> str:
    if db_name != "":
        db_name = "/" + db_name

    if username != "" or password != "":
        user_info = username + ":" + password + "@"
    else:
        user_info = ""

    return ("").join([dialect, "+", dbapi, "://", user_info, dblocation, db_name])