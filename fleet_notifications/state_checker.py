import logging
import threading

from fleet_management_http_client_python import ApiClient, CarApi, OrderApi, OrderStateApi, OrderStatus
from fleet_notifications.notifications_client import NotificationClient
from fleet_notifications.database.database_controller import get_orders, update_order, delete_order


def _get_car_id(car_name: str, api_client: ApiClient):
    car_api = CarApi(api_client)
    cars = car_api.get_cars()
    for car in cars:
        if car.name == car_name:
            logging.info(f"Car found, ID: {car.id}")
            return car.id, car.car_admin_phone.phone
    return 0, ""


def start(config: dict, api_client: ApiClient) -> None:
    notification_client = NotificationClient(config['twilio'])

    # Get car ID
    logging.info(f"Car name: {config['car']['name']}")
    car_id, admin_phone = _get_car_id(config['car']['name'], api_client)
    if car_id == 0:
        logging.error("Car not found.")
        return

    orders = dict()
    order_api = OrderApi(api_client)
    order_state_api = OrderStateApi(api_client)

    # Load unfinished orders from the database
    since = 0
    db_orders = get_orders()
    for order in db_orders:
        try:
            orders[order.id] = order_api.get_order(car_id=car_id, order_id=order.id)
            orders[order.id].last_state.status = OrderStatus.IN_PROGRESS
        except Exception as e:
            logging.error(f"Error while getting order {order.id} from the api: {e}")
            delete_order(order.id)
            continue
        if order.timestamp > since:
            since = order.timestamp

    while True:
        try:
            while car_id != 0:
                logging.info(f"Checking order states since: {since+1}")
                states = order_state_api.get_all_order_states(wait=True, since=since+1)

                for state in states:
                    logging.info(f"Order state: {state.to_str()}")

                    # Add order to the list if it is not there
                    order_count = len(orders)
                    if state.order_id not in orders:
                        orders[state.order_id] = order_api.get_order(car_id=car_id, order_id=state.order_id)

                    # Mission started if there were no orders before
                    if (order_count == 0 and len(orders) > 0 and orders[state.order_id].last_state.status != OrderStatus.DONE and 
                        orders[state.order_id].last_state.status != OrderStatus.CANCELED):
                        logging.info(f"New mission started.")
                        threading.Thread(target=notification_client.call_phone, args=(admin_phone)).start()

                    # Check if the order is done
                    if orders[state.order_id].last_state.status != OrderStatus.DONE and state.status == OrderStatus.DONE:
                        logging.info(f"Order {state.order_id} is done.")
                        orders[state.order_id] = order_api.get_order(car_id=car_id, order_id=state.order_id)
                        threading.Thread(target=notification_client.call_phone, args=(orders[state.order_id].notification_phone.phone)).start()

                    # Update timestamp to the newest state
                    if state.timestamp > since:
                        since = state.timestamp

                # Remove finished orders
                orders_to_remove = []
                for order in orders.values():
                    if order.last_state.status == OrderStatus.DONE or order.last_state.status == OrderStatus.CANCELED:
                        orders_to_remove.append(order.id)
                    else:
                        update_order(order.id, order.last_state.timestamp)
                for order_id in orders_to_remove:
                    orders.pop(order_id)
                    delete_order(order_id)
        except KeyboardInterrupt:
            logging.info("Exiting the script.")
            return
        except Exception as e:
            logging.error(f"Unknown error: {e}, restarting.")
        car_id, admin_phone = _get_car_id(config['car']['name'], api_client)
        if car_id == 0:
            logging.error("Car not found.")
            return



# TODO test
# load with empty database and no existing order - no action until an order is created
# load with empty database and existing finished order - no action until a new order is created
# load with empty database and existing unfinished order - no action until order is finished
# load with order in database that no longer exists - no action
# load with order in database that is finished - call station
# load with order in database that is unfinished - no action until order is finished
