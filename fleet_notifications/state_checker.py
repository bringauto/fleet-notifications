import logging, threading, time

import fleet_notifications.database.database_controller as notifications_db
from fleet_management_http_client_python import ApiClient, CarApi, Order, OrderApi, OrderStateApi, OrderStatus, OrderState # type: ignore
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
        self.orders = dict[int, Order]()
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


    def _is_order_finished(self, order: Order) -> bool:
        """Returns true if the order is finished."""
        return order.last_state.status == OrderStatus.DONE or order.last_state.status == OrderStatus.CANCELED


    def _check_if_order_is_new(self, car_id: int, state: OrderState, admin_phone: str, under_test: bool) -> bool:
        """Adds the order belonging to the state to the list of orders. If the order is the first new one,
        a notification is sent to the admin phone number. Returns false if the order can't be retrieved."""
        no_active_order = car_id not in (order.car_id for order in self.orders.values())
        if state.order_id not in self.orders or state.status == OrderStatus.CANCELED:
            try:
                self.orders[state.order_id] = self.order_api.get_order(car_id=car_id, order_id=state.order_id)
            except Exception as e:
                logger.error(f"Error while getting order with ID {state.order_id} from the api: {e}")
                return False

        if (no_active_order and not self._is_order_finished(self.orders[state.order_id])):
            logger.info(f"New mission started for car (ID={car_id}).")
            threading.Thread(target=self.notification_client.call_phone, daemon=True,
                             args=(admin_phone, under_test,)).start()
        return True


    def _call_phone_if_order_is_done(self, car_id: int, state: OrderState, under_test: bool) -> None:
        """Checks if the order is newly done and sends a notification to the phone number in the order."""
        if self.orders[state.order_id].last_state.status != OrderStatus.DONE and state.status == OrderStatus.DONE:
            logger.info(f"Order {state.order_id} is done.")
            try:
                self.orders[state.order_id] = self.order_api.get_order(car_id=car_id, order_id=state.order_id)
            except Exception as e:
                logger.error(f"Error while getting order with ID {state.order_id} from the api: {e}")
                return

            notification_phone = self.orders[state.order_id].notification_phone
            if(notification_phone is None):
                logger.warning(f"Order {state.order_id} has no notification phone number.")
                return

            threading.Thread(target=self.notification_client.call_phone, daemon=True, args=(
                             notification_phone.phone, under_test,)).start()


    def _remove_finished_orders(self) -> None:
        """Removes finished orders from the list and the database."""
        finished_order_ids = [order.id for order in self.orders.values() if self._is_order_finished(order)]
        active_order_ids = [order.id for order in self.order_api.get_orders()]
        deleted_order_ids = [
            order.id for order in self.orders.values() if order.id not in active_order_ids
        ]
        for order_id in finished_order_ids + deleted_order_ids:
            self.orders.pop(order_id)
            notifications_db.delete_order(order_id)


    def _update_latest_timestamps(self, since: int) -> None:
        """If an order is not finished, the since parameter is used as its latest timestamp."""
        orders_to_update = [order for order in self.orders.values() if not self._is_order_finished(order)]
        for order in orders_to_update:
            notifications_db.update_order(order.id, order.car_id, since)


    def _start(self) -> None:
        """Starts checking order states on the Fleet Management API and triggers notifications when needed.
        This function runs indefinitely and should be run in a separate thread. If an error occurs,
        the function will sleep for a few seconds and then restart."""
        since = self._load_unfinished_orders()

        while True:
            try:
                states: dict[int, OrderState] = {
                    state.order_id: state
                    for state in self.order_state_api.get_all_order_states(wait=True, since=since+1)
                }
                if states:
                    since = max(states.values(), key=lambda state: state.timestamp).timestamp
                    self._check_orders_and_call_if_done(states)
                    self._remove_finished_orders()
                    self._update_latest_timestamps(since)

            except KeyboardInterrupt:
                logger.info("Exiting the script.")
                return
            except Exception as e:
                logger.error(f"Unknown error: {e}, restarting.", exc_info=True)
                time.sleep(THREAD_RESTART_DELAY)


    def _check_orders_and_call_if_done(self, new_states: dict[int, OrderState]) -> None:
        """Checks if the orders in the new states are new or done and triggers notifications if needed.
        `new_states` is a dictionary with order IDs as keys and the new states (with corresponding order ID) as values.
        """
        all_orders = {order.id: order for order in self.order_api.get_orders()}
        for order_id, state in new_states.items():
            logger.info(
                f"New order state ID: {state.id} for order {order_id} with status {state.status.name}"
            )
            order = all_orders.get(order_id, None)
            if not order:
                logger.error(f"Order not found: {order_id}")
                continue
            try:
                car = self.car_api.get_car(order.car_id)
            except:
                logger.error(f"Car not found: {order.car_id}")
                continue
            phone = "" if car.car_admin_phone.phone is None else car.car_admin_phone.phone
            if self._check_if_order_is_new(car.id, state, phone, car.under_test):
                self._call_phone_if_order_is_done(car.id, state, car.under_test)


    def start_thread(self) -> None:
        """Starts the thread that checks the order states."""
        self.thread.start()
