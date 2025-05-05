import unittest
import threading

from fleet_management_http_client_python import ( # type: ignore
    ApiClient,
    Configuration,
    MobilePhone,
    CarApi, Car,
    OrderApi, Order,
    OrderStateApi, OrderState, OrderStatus
)

import fleet_notifications.database.database_controller as notifications_db
from fleet_notifications.state_checker import OrderStateChecker
from fleet_notifications.notifications_client import NotificationClient
from fleet_notifications.logs import LOGGER_NAME
from fleet_notifications.script_args.configs import Database
from tests._utils.mock_api import MockApi
from tests._utils.testing_configs import TEST_TWILIO_CONFIG


def _create_test_state_checker() -> OrderStateChecker:
    return OrderStateChecker(
        twilio_config=TEST_TWILIO_CONFIG,
        api_client=ApiClient(Configuration(
            host="http://example.com",
            api_key={'APIKeyAuth': "test_api_key"}
        ))
    )


class Test_State_Checker_Initialization(unittest.TestCase):
    """Tests the initialization of the OrderStateChecker class."""

    def test_initialization(self):
        state_checker = _create_test_state_checker()
        self.assertTrue(isinstance(state_checker.notification_client, NotificationClient))
        self.assertTrue(isinstance(state_checker.car_api, CarApi))
        self.assertTrue(isinstance(state_checker.order_api, OrderApi))
        self.assertTrue(isinstance(state_checker.order_state_api, OrderStateApi))
        self.assertTrue(isinstance(state_checker.orders, dict))
        self.assertTrue(isinstance(state_checker.thread, threading.Thread))


class Test_State_Checker_Is_Order_Finished(unittest.TestCase):
    """Tests the _is_order_finished method of the OrderStateChecker class."""

    def test_is_order_finished(self):
        """Tests if the _is_order_finished method returns true for finished orders and false for unfinished ones."""
        state_checker = _create_test_state_checker()
        order = Order(carId=0, targetStopId=0, stopRouteId=0,
                      last_state=OrderState(orderId=0, status=OrderStatus.DONE))
        self.assertTrue(state_checker._is_order_finished(order))
        order.last_state.status = OrderStatus.CANCELED
        self.assertTrue(state_checker._is_order_finished(order))
        order.last_state.status = OrderStatus.IN_PROGRESS
        self.assertFalse(state_checker._is_order_finished(order))


class Test_State_Checker_Check_New_Order(unittest.TestCase):
    """Tests the _check_if_order_is_new method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        self.mock_api = MockApi()
        self.state_checker.order_api = self.mock_api
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS)),
            2: Order(carId=2, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=2, status=OrderStatus.IN_PROGRESS))
        }

    def test_check_new_order(self):
        """Tests if the _check_if_order_is_new method returns true for a new order.
        Also checks if the order is added to the list of orders."""
        state = OrderState(orderId=3, status=OrderStatus.IN_PROGRESS)
        self.state_checker.orders.clear()
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=3,
                                         last_state=OrderState(orderId=3, status=OrderStatus.IN_PROGRESS))])
        self.assertTrue(self.state_checker._check_if_order_is_new(1, state, "admin_phone", True))
        self.assertEqual(len(self.state_checker.orders), 1)

    def test_check_new_order_not_new(self):
        """Tests if the _check_if_order_is_new method returns true for an existing order.
        Also checks if the order is not added to the list of orders."""
        state = OrderState(orderId=1, status=OrderStatus.IN_PROGRESS)
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS))])
        self.assertTrue(self.state_checker._check_if_order_is_new(1, state, "admin_phone", True))
        self.assertEqual(len(self.state_checker.orders), 2)

    def test_check_new_order_not_found(self):
        """Tests if the _check_if_order_is_new method returns false for an order that is not found in the API."""
        state = OrderState(orderId=3, carId=1, status=OrderStatus.IN_PROGRESS)
        self.assertFalse(self.state_checker._check_if_order_is_new(1, state, "admin_phone", True))
        self.assertEqual(len(self.state_checker.orders), 2)


class Test_State_Checker_Call_If_Order_Done(unittest.TestCase):
    """Tests the _call_phone_if_order_is_done method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        self.mock_api = MockApi()
        self.state_checker.order_api = self.mock_api
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS)),
            2: Order(carId=2, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=2, status=OrderStatus.IN_PROGRESS))
        }

    def test_call_if_order_is_done(self):
        """Tests if the _call_phone_if_order_is_done method correctly considers an order as finished."""
        state = OrderState(orderId=1, status=OrderStatus.DONE)
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         notificationPhone=MobilePhone(phone="admin_phone"),
                                         last_state=OrderState(orderId=1, status=OrderStatus.DONE))])
        with self.assertLogs(LOGGER_NAME, level="INFO") as log:
            self.state_checker._call_phone_if_order_is_done(1, state, True)
            self.assertNotEqual(log.output[0].find(f"Order {state.order_id} is done."), -1)
        self.assertEqual(len(self.state_checker.orders), 2)

    def test_call_if_order_is_done_not_found(self):
        """Tests if the _call_phone_if_order_is_done method correctly handles an order that is not found in the API."""
        state = OrderState(orderId=2, carId=1, status=OrderStatus.DONE)
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.state_checker._call_phone_if_order_is_done(1, state, True)
            self.assertNotEqual(log.output[0].find(
                f"Unable to get order with ID {state.order_id} from the api: Order not found"
            ), -1)
        self.assertEqual(len(self.state_checker.orders), 2)

    def test_call_if_order_is_done_no_phone(self):
        """Tests if the _call_phone_if_order_is_done method correctly handles an order with no phone number."""
        state = OrderState(orderId=1, carId=1, status=OrderStatus.DONE)
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.DONE))])
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.state_checker._call_phone_if_order_is_done(1, state, True)
            self.assertNotEqual(log.output[0].find(
                f"Order {state.order_id} has no notification phone number."
            ), -1)
        self.assertEqual(len(self.state_checker.orders), 2)

    def test_no_call_if_order_is_not_done(self):
        """Tests if the _call_phone_if_order_is_done method does not call if the order is not done."""
        state = OrderState(orderId=1, carId=1, status=OrderStatus.IN_PROGRESS)
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS))])
        with self.assertNoLogs(LOGGER_NAME, level="INFO") as log:
            self.state_checker._call_phone_if_order_is_done(1, state, True)
        self.assertEqual(len(self.state_checker.orders), 2)


class Test_State_Checker_Check_All_Orders(unittest.TestCase):
    """Tests the _check_orders_and_call_if_done method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        self.mock_api = MockApi()
        self.state_checker.order_api = self.mock_api
        self.state_checker.car_api = self.mock_api

    def test_check_all_orders_order_not_found(self):
        """Tests if the _check_orders_and_call_if_done method correctly handles an order that is not found in the API."""
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.state_checker._check_orders_and_call_if_done(
                {1: OrderState(status=OrderStatus.IN_PROGRESS, orderId=0)},
            )
            self.assertNotEqual(log.output[0].find("Order not found: 1"), -1)

    def test_check_all_orders_car_not_found(self):
        """Tests if the _check_orders_and_call_if_done method correctly handles a car that is not found in the API."""
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS))])
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.state_checker._check_orders_and_call_if_done(
                {1: OrderState(status=OrderStatus.IN_PROGRESS, orderId=1)},
            )
            self.assertNotEqual(log.output[0].find("Car not found: 1"), -1)

    def test_check_all_orders_and_call(self):
        """Tests if the _check_orders_and_call_if_done method detects a new mission starting for a car."""
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS))])
        self.mock_api._set_cars([Car(id=1, platformHwId=1, name="test_name", underTest=True,
                                     carAdminPhone=MobilePhone(phone="admin_phone"))])
        with self.assertLogs(LOGGER_NAME, level="INFO") as log:
            self.state_checker._check_orders_and_call_if_done(
                {1: OrderState(status=OrderStatus.IN_PROGRESS, orderId=1)},
            )
            print(log.output)
            self.assertNotEqual(log.output[1].find("New mission started for car (ID=1)."), -1)


class Test_State_Checker_Load_Orders(unittest.TestCase):
    """Tests the _load_unfinished_orders method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        self.mock_api = MockApi()
        self.state_checker.order_api = self.mock_api
        notifications_db.initialize_db(
            Database.Connection(
                location="_",
                database_name="_",
                username="_",
                password="_",
                port=0
            ),
            test=True
        )

    def test_load_orders(self):
        """Tests if the _load_unfinished_orders method loads the orders correctly."""
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS, timestamp=2))])
        notifications_db.update_order(1, 1, 0)
        self.assertEqual(self.state_checker._load_unfinished_orders(), 2)

    def test_load_orders_no_orders(self):
        """Tests if the _load_unfinished_orders method logs a warning when an order was not found in the API."""
        notifications_db.update_order(1, 1, 0)
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.assertEqual(self.state_checker._load_unfinished_orders(), 0)
            self.assertNotEqual(log.output[0].find("Unable to get order 1 from the api: Order not found"), -1)
        self.assertEqual(len(self.state_checker.orders), 0)

    def test_load_orders_correct_timestamp(self):
        """Tests if the _load_unfinished_orders method loads the orders and returns the highest timestamp."""
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS, timestamp=1)),
                                   Order(carId=1, targetStopId=0, stopRouteId=0, id=2,
                                         last_state=OrderState(orderId=2, status=OrderStatus.IN_PROGRESS, timestamp=3)),
                                   Order(carId=1, targetStopId=0, stopRouteId=0, id=3,
                                         last_state=OrderState(orderId=3, status=OrderStatus.IN_PROGRESS, timestamp=2))])
        notifications_db.update_order(1, 1, 0)
        notifications_db.update_order(2, 1, 0)
        notifications_db.update_order(3, 1, 0)
        self.assertEqual(self.state_checker._load_unfinished_orders(), 3)


class Test_State_Checker_Remove_Finished_Orders(unittest.TestCase):
    """Tests the _remove_finished_orders method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        self.mock_api = MockApi()
        self.state_checker.order_api = self.mock_api
        self.mock_api._set_orders([Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                                         last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS))])
        notifications_db.initialize_db(
            Database.Connection(
                location="_",
                database_name="_",
                username="_",
                password="_",
                port=0
            ),
            test=True
        )

    def test_remove_finished_orders(self):
        """Tests if the _remove_finished_orders method removes finished orders from the list."""
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.DONE))
        }
        self.state_checker._remove_finished_orders()
        self.assertEqual(len(self.state_checker.orders), 0)

    def test_remove_finished_orders_order_not_in_api(self):
        """Tests if the _remove_finished_orders method removes orders that are not in the API."""
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS)),
            2: Order(carId=2, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=2, status=OrderStatus.IN_PROGRESS))
        }
        self.state_checker._remove_finished_orders()
        self.assertEqual(len(self.state_checker.orders), 1)

    def test_remove_finished_orders_order_finished_and_not_in_api(self):
        """Tests if the _remove_finished_orders method removes orders that are finished and not in the API."""
        self.state_checker.orders = {
            2: Order(carId=1, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=1, status=OrderStatus.DONE))
        }
        self.state_checker._remove_finished_orders()
        self.assertEqual(len(self.state_checker.orders), 0)


class Test_State_Checker_Timestamp_Update(unittest.TestCase):
    """Tests the _update_latest_timestamps method of the OrderStateChecker class."""

    def setUp(self) -> None:
        self.state_checker = _create_test_state_checker()
        notifications_db.initialize_db(
            Database.Connection(
                location="_",
                database_name="_",
                username="_",
                password="_",
                port=0
            ),
            test=True
        )

    def test_updating_timestamps(self):
        """Tests if the _update_latest_timestamps method updates the timestamps of the orders."""
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.IN_PROGRESS, timestamp=1)),
            2: Order(carId=2, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=2, status=OrderStatus.IN_PROGRESS, timestamp=2))
        }
        self.state_checker._update_latest_timestamps(3)
        orders = notifications_db.get_orders()
        self.assertEqual(orders[0].timestamp, 3)
        self.assertEqual(orders[1].timestamp, 3)

    def test_updating_timestamps_finished_orders(self):
        """Tests if the _update_latest_timestamps method removes finished orders."""
        self.state_checker.orders = {
            1: Order(carId=1, targetStopId=0, stopRouteId=0, id=1,
                     last_state=OrderState(orderId=1, status=OrderStatus.DONE, timestamp=1)),
            2: Order(carId=2, targetStopId=0, stopRouteId=0, id=2,
                     last_state=OrderState(orderId=2, status=OrderStatus.CANCELED, timestamp=1))
        }
        self.state_checker._update_latest_timestamps(3)
        orders = notifications_db.get_orders()
        self.assertEqual(orders, [])


if __name__ == "__main__":
    unittest.main() # pragma: no cover