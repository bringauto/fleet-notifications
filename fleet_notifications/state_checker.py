import logging, threading, time

from fleet_management_http_client_python import ApiClient, CarApi, OrderApi, OrderStateApi, OrderStatus
from fleet_notifications.notifications_client import NotificationClient
from fleet_notifications.database.database_controller import get_orders, update_order, delete_order


def start(config: dict, api_client: ApiClient) -> None:
    notification_client = NotificationClient(config['twilio'])
    orders = dict()
    car_api = CarApi(api_client)
    order_api = OrderApi(api_client)
    order_state_api = OrderStateApi(api_client)

    # Load unfinished orders from the database
    since = 0
    db_orders = get_orders()
    for order in db_orders:
        try:
            orders[order.id] = order_api.get_order(car_id=order.car_id, order_id=order.id)
            # Currently disabled to not call on script restart
            #orders[order.id].last_state.status = OrderStatus.IN_PROGRESS
        except Exception as e:
            logging.error(f"Error while getting order {order.id} from the api: {e}")
            delete_order(order.id)
            continue
        if order.timestamp > since:
            since = order.timestamp

    while True:
        try:
            states = order_state_api.get_all_order_states(wait=True, since=since+1)
            if len(states) != 0:
                all_orders = order_api.get_orders()

            for state in states:
                logging.info(f"New order state ID: {state.id} for order {state.order_id} with status {state.status.name}")

                # Update timestamp to the newest state
                if state.timestamp > since:
                    since = state.timestamp

                # Currently there is no better way to get car_id from an order state
                car_id = 0
                for order in all_orders:
                    if order.id == state.order_id:
                        car_id = order.car_id

                # Get car data
                try:
                    car = car_api.get_car(car_id)
                    car_id = car.id
                    admin_phone = car.car_admin_phone.phone
                    under_test = car.under_test
                except:
                    logging.error(f"Car not found: {car_id}")
                    continue

                # Add order to the list if it is not there
                order_count = len(orders)
                if state.order_id not in orders or state.status == OrderStatus.CANCELED:
                    try:
                        orders[state.order_id] = order_api.get_order(car_id=car_id, order_id=state.order_id)
                    except:
                        continue

                # Mission started if there were no orders before
                if (order_count == 0 and len(orders) > 0 and orders[state.order_id].last_state.status != OrderStatus.DONE and 
                    orders[state.order_id].last_state.status != OrderStatus.CANCELED):
                    logging.info(f"New mission started.")
                    threading.Thread(target=notification_client.call_phone, daemon=True, args=(admin_phone, under_test,)).start()

                # Check if the order is done
                if orders[state.order_id].last_state.status != OrderStatus.DONE and state.status == OrderStatus.DONE:
                    logging.info(f"Order {state.order_id} is done.")
                    orders[state.order_id] = order_api.get_order(car_id=car_id, order_id=state.order_id)
                    threading.Thread(target=notification_client.call_phone, daemon=True, args=(
                        orders[state.order_id].notification_phone.phone, under_test,
                    )).start()

            # Remove finished orders
            orders_to_remove = []
            for order in orders.values():
                if order.last_state.status == OrderStatus.DONE or order.last_state.status == OrderStatus.CANCELED:
                    orders_to_remove.append(order.id)
                else:
                    try:
                        order_api.get_order(car_id=order.car_id, order_id=order.id)
                        update_order(order.id, order.car_id, since)
                    except:
                        orders_to_remove.append(order.id)
            for order_id in orders_to_remove:
                orders.pop(order_id)
                delete_order(order_id)

        except KeyboardInterrupt:
            logging.info("Exiting the script.")
            return
        except Exception as e:
            logging.error(f"Unknown error: {e}, restarting.")
            time.sleep(2)
