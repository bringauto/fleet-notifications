from database.connection import get_connection_source


def update_last_car_status(car_id: int, timestamp: int, status: str) -> None:
    try:
        with get_connection_source().begin() as conn:
            conn.execute(
                f"INSERT INTO car_states (car_id, timestamp, status) VALUES ({car_id}, {timestamp}, '{status}')"
            )
    except:
        pass