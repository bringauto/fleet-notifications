from fleet_notifications.script_args import Database as _db_args
from fleet_notifications.database.connection import get_connection_source, set_db_connection
from sqlalchemy import MetaData ,Table, Column, Integer, BigInteger
from sqlalchemy.dialects.postgresql import insert
from fleet_management_http_client_python import Order # type: ignore


_meta = MetaData()
_orders = Table(
    'orders', _meta,
    Column('id', Integer, primary_key=True),
    Column('order_id', Integer, unique=True),
    Column('car_id', Integer),
    Column('timestamp', BigInteger)
)


def initialize_db(connection: _db_args.Connection) -> None:
    set_db_connection(
        dblocation = connection.location + ":" + str(connection.port),
        username = connection.username,
        password = connection.password,
        db_name = connection.database_name
    )
    try:
        print("Creating orders table")
        with get_connection_source().begin() as conn:
            _meta.create_all(conn, tables=[_orders])
    except Exception as e:
        print(e)


def update_order(order_id: int, car_id: int, timestamp: int) -> None:
    try:
        with get_connection_source().begin() as conn:
            update = insert(_orders).values(order_id=order_id, car_id=car_id, timestamp=timestamp)
            update = update.on_conflict_do_update(
                index_elements=['order_id'],
                set_=dict(car_id=car_id, timestamp=timestamp)
            )
            conn.execute(update)
    except Exception as e:
        print(e)


def delete_order(order_id: int) -> None:
    try:
        with get_connection_source().begin() as conn:
            conn.execute(_orders.delete().where(_orders.c.order_id == order_id))
    except Exception as e:
        print(e)


def get_orders() -> list[Order]:
    try:
        with get_connection_source().begin() as conn:
            result = conn.execute(_orders.select())
            orders = result.fetchall()
            ret_list = []
            for order in orders:
                ret_list.append(Order(
                    id=order[1],
                    timestamp=order[3],
                    carId=[2],
                    targetStopId=0,
                    stopRouteId=0
                    ))
            return ret_list
    except Exception as e:
        print(e)
        return []