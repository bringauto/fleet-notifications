import logging
import time

from fleet_management_http_client_python import ApiClient, CarApi, OrderApi, OrderStateApi, OrderStatus
from fleet_notifications.notifications_client import NotificationClient


def start(config: dict, api_client: ApiClient) -> None:
    notification_client = NotificationClient(config['twilio'])

    # Get car ID
    logging.info(f"Car name: {config['car']['name']}")
    car_api = CarApi(api_client)
    cars = car_api.get_cars()
    car_id = 0
    admin_phone = ""
    for car in cars:
        if car.name == config['car']['name']:
            logging.info(f"Car found, ID: {car.id}")
            car_id = car.id
            admin_phone = car.car_admin_phone.phone
            break

    orders = dict()
    order_api = OrderApi(api_client)
    order_state_api = OrderStateApi(api_client)
    # TODO get since from database if its there
    since = 0

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
                if order_count == 0 and len(orders) > 0:
                    logging.info(f"New mission started.")
                    notification_client.call_phone(admin_phone)

                # Check if the order is done
                if orders[state.order_id].last_state.status != OrderStatus.DONE and state.status == OrderStatus.DONE:
                    logging.info(f"Order {state.order_id} is done.")
                    orders[state.order_id] = order_api.get_order(car_id=car_id, order_id=state.order_id)
                    notification_client.call_phone(orders[state.order_id].notification_phone.phone)

                # Update timestamp to the newest state
                if state.timestamp > since:
                    since = state.timestamp

            # Remove finished orders
            for order in orders.values():
                if order.last_state.status == OrderStatus.DONE or order.last_state.status == OrderStatus.CANCELED:
                    #orders.pop(order.id) TODO remove out of the loop
                    pass
                else:
                    # TODO store unfinished orders in database
                    pass
    except KeyboardInterrupt:
        logging.info("Exiting the script.")
        pass
