import logging, threading, time

import fleet_notifications.database.database_controller as notifications_db
from fleet_management_http_client_python import ApiClient, CarApi, OrderApi, OrderStateApi, OrderStatus, OrderState
from fleet_notifications.notifications_client import NotificationClient
from fleet_notifications.script_args.configs import Twilio
from fleet_notifications.logs import LOGGER_NAME


THREAD_RESTART_DELAY = 2
logger = logging.getLogger(LOGGER_NAME)


class OrderStateChecker:
    def __init__(self, twilio_config: Twilio, api_client: ApiClient):
        self.notification_client = NotificationClient(twilio_config)
        self.car_api = CarApi(api_client)
        self.order_api = OrderApi(api_client)
        self.order_state_api = OrderStateApi(api_client)
        self.orders = dict()
        self.thread = threading.Thread(target=self._start, daemon=True)


    def _load_unfinished_orders(self) -> int:
        """Loads all unfinished orders from the database and returns the timestamp of the newest order."""
        db_orders = notifications_db.get_orders()
        for order in db_orders:
            try:
                self.orders[order.id] = self.order_api.get_order(car_id=order.car_id, order_id=order.id)
            except Exception as e:
                logger.error(f"Error while getting order {order.id} from the api: {e}")
                notifications_db.delete_order(order.id)
                continue
        return max(self.orders, key=lambda order: order.timestamp, default=0)
    

    def _check_if_order_is_new(self, car_id: int, state: OrderState, admin_phone: str, under_test: bool) -> None:
        """Adds the order belonging to the state to the list of orders. If the order is the first new one,
        a notification is sent to the admin phone number. Returns false if the order can't be retrieved."""
        no_active_order = True
        for order in self.orders.values():
            if order.car_id == car_id:
                no_active_order = False
                break
        if state.order_id not in self.orders or state.status == OrderStatus.CANCELED:
            try:
                self.orders[state.order_id] = self.order_api.get_order(car_id=car_id, order_id=state.order_id)
            except:
                logger.error(f"Error while getting order with ID {state.order_id} from the api.")
                return False
        new_order_started = False
        for order in self.orders.values():
            if order.car_id == car_id:
                new_order_started = True
                break

        if (no_active_order and new_order_started and self.orders[state.order_id].last_state.status
            != OrderStatus.DONE and self.orders[state.order_id].last_state.status != OrderStatus.CANCELED):
            logger.info(f"New mission started.")
            threading.Thread(target=self.notification_client.call_phone, daemon=True,
                             args=(admin_phone, under_test,)).start()
        return True


    def _check_if_order_is_done(self, car_id: int, state: OrderState, under_test: bool) -> None:
        """Checks if the order is newly done and sends a notification to the phone number in the order."""
        if self.orders[state.order_id].last_state.status != OrderStatus.DONE and state.status == OrderStatus.DONE:
            logger.info(f"Order {state.order_id} is done.")
            self.orders[state.order_id] = self.order_api.get_order(car_id=car_id, order_id=state.order_id)

            notification_phone = self.orders[state.order_id].notification_phone
            if(notification_phone is None):
                logger.warning(f"Order {state.order_id} has no notification phone number.")
                return

            threading.Thread(target=self.notification_client.call_phone, daemon=True, args=(
                             notification_phone.phone, under_test,)).start()


    def _remove_finished_orders(self, since: int) -> None:
        """Removes finished orders from the list and the database. If an order is not finished,
        the since parameter is used as its latest timestamp."""
        orders_to_remove = []
        for order in self.orders.values():
            if order.last_state.status == OrderStatus.DONE or order.last_state.status == OrderStatus.CANCELED:
                orders_to_remove.append(order.id)
            else:
                try:
                    self.order_api.get_order(car_id=order.car_id, order_id=order.id)
                    notifications_db.update_order(order.id, order.car_id, since)
                except:
                    orders_to_remove.append(order.id)
        for order_id in orders_to_remove:
            self.orders.pop(order_id)
            notifications_db.delete_order(order_id)


    def _start(self) -> None:
        """Starts checking order states on the Fleet Management API and triggers notifications when needed.
        This function runs indefinitely and should be run in a separate thread. If an error occurs,
        the function will sleep for a few seconds and then restart."""
        since = self._load_unfinished_orders()

        while True:
            try:
                states = self.order_state_api.get_all_order_states(wait=True, since=since+1)
                if len(states) != 0:
                    all_orders = self.order_api.get_orders()
                else:
                    continue
                since = max(states, key=lambda state: state.timestamp).timestamp

                for state in states:
                    logger.info(f"New order state ID: {state.id} for order {state.order_id} with status "
                                f"{state.status.name}")

                    # Currently there is no better way to get car_id from an order state
                    car_id = 0
                    for order in all_orders:
                        if order.id == state.order_id:
                            car_id = order.car_id

                    # Get car data
                    try:
                        car = self.car_api.get_car(car_id)
                        car_id = car.id
                        if(car.car_admin_phone is None):
                            logger.warning(f"Car {car_id} has no admin phone number.")
                            admin_phone = ""
                        else:
                            admin_phone = car.car_admin_phone.phone
                        under_test = car.under_test
                    except:
                        logger.error(f"Car not found: {car_id}")
                        continue

                    if(not self._check_if_order_is_new(car_id, state, admin_phone, under_test)):
                        continue

                    self._check_if_order_is_done(car_id, state, under_test)
                self._remove_finished_orders(since)

            except KeyboardInterrupt:
                logger.info("Exiting the script.")
                return
            except Exception as e:
                logger.error(f"Unknown error: {e}, restarting.")
                time.sleep(THREAD_RESTART_DELAY)

    def start_thread(self) -> None:
        """Starts the thread that checks the order states."""
        self.thread.start()
