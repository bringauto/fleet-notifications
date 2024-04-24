from database.connection import get_connection_source


def create_orders_table() -> None:
    try:
        with get_connection_source().begin() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_orders (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    
                )
                """
            )
    except:
        pass


def update_last_car_status(car_id: int, timestamp: int, status: str) -> None:
    try:
        with get_connection_source().begin() as conn:
            conn.execute(
                f"INSERT INTO car_states (car_id, timestamp, status) VALUES ({car_id}, {timestamp}, '{status}')"
            )
    except:
        pass