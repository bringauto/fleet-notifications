import unittest

from fleet_management_http_client_python import ( # type: ignore
    ApiClient,
    Configuration,
    MobilePhone,
    CarApi, Car,
    CarStateApi, CarState, CarStatus,
    CarActionApi, CarActionState, CarActionStatus
)

from fleet_notifications.incoming_call_endpoint import IncomingCallHandler, InvalidCarName
from fleet_notifications.script_args.configs import HTTPServer
from fleet_notifications.logs import LOGGER_NAME
from tests._utils.mock_api import MockApi
from tests._utils.testing_configs import TEST_TWILIO_CONFIG


def _create_test_call_handler() -> IncomingCallHandler:
    return IncomingCallHandler(
        twilio_config=TEST_TWILIO_CONFIG,
        server_config=HTTPServer(port=8080),
        api_client=ApiClient(Configuration(
            host="http://example.com",
            api_key={'APIKeyAuth': "test_api_key"}
        )),
        allow_http=True
    )


class Test_Call_Handler_Initialization(unittest.TestCase):
    """Tests the initialization of the IncomingCallHandler class."""

    def test_initialization(self):
        """Tests if the IncomingCallHandler class is initialized correctly.
        Configured values are compared to the values in the test configuration."""
        call_handler = _create_test_call_handler()
        self.assertEqual(call_handler.twilio_auth_token, TEST_TWILIO_CONFIG.auth_token)
        self.assertEqual(
            call_handler.allowed_incoming_phone_numbers,
            TEST_TWILIO_CONFIG.call_handling.allowed_incoming_phone_numbers
        )
        self.assertEqual(
            call_handler.action_timeout_s,
            TEST_TWILIO_CONFIG.call_handling.car_action_change_timeout_s
        )
        self.assertTrue(isinstance(call_handler.car_api, CarApi))
        self.assertTrue(isinstance(call_handler.car_state_api, CarStateApi))
        self.assertTrue(isinstance(call_handler.car_action_api, CarActionApi))
        self.assertEqual(call_handler.server_port, 8080)
        self.assertTrue(call_handler.allow_http)


class Test_Call_Handler_Action_Checking(unittest.TestCase):
    """Tests the _car_action_status_occured method of the IncomingCallHandler class."""

    def setUp(self) -> None:
        self.call_handler = _create_test_call_handler()
        self.call_handler.car_action_api = MockApi()
        self.call_handler.car_action_api._set_car_action_states(
            [CarActionState(id=0, carId=1, timestamp=0, actionStatus=CarActionStatus.NORMAL)]
        )

    def test_car_action_status_occurred(self):
        """Tests if the _car_action_status_occurred method returns true when the action status is in the set."""
        self.assertTrue(
            self.call_handler._car_action_status_occurred({CarActionStatus.NORMAL}, 1)
        )

    def test_car_action_status_occurred_timeout(self):
        """Tests if the _car_action_status_occurred method returns false when the action status is not in the set.
        Action status will not be set to PAUSED in the mock API."""
        self.assertFalse(
            self.call_handler._car_action_status_occurred({CarActionStatus.PAUSED}, 1)
        )


class Test_Call_Handler_State_Checking(unittest.TestCase):
    """Tests the _car_status_occured method of the IncomingCallHandler class."""

    def setUp(self) -> None:
        self.call_handler = _create_test_call_handler()
        self.call_handler.car_state_api = MockApi()
        self.call_handler.car_state_api._set_car_states(
            [CarState(id=0, timestamp=0, status=CarStatus.IDLE, carId=1)]
        )

    def test_car_status_occurred(self):
        """Tests if the _car_status_occured method returns true when the status is in the set."""
        self.assertTrue(
            self.call_handler._car_status_occured({CarStatus.IDLE}, 1)
        )

    def test_car_status_occurred_timeout(self):
        """Tests if the _car_status_occured method returns false when the status is not in the set.
        Status will not be set to DRIVING in the mock API."""
        self.assertFalse(
            self.call_handler._car_status_occured({CarStatus.DRIVING}, 1)
        )


class Test_Call_Handler_Car_Id(unittest.TestCase):
    """Tests the _get_car_id_from_name method of the IncomingCallHandler class."""

    def setUp(self) -> None:
        self.call_handler = _create_test_call_handler()
        self.call_handler.car_api = MockApi()
        self.call_handler.car_api._set_cars(
            [Car(id=1, platformHwId=1, name="test_name", carAdminPhone=MobilePhone(phone="test_number"))]
        )

    def test_get_car_id_from_name(self):
        """Tests if the _get_car_id_from_name method returns the correct car ID."""
        car_id = self.call_handler._get_car_id_from_name("test_name")
        self.assertEqual(car_id, 1)

    def test_get_car_id_from_name_not_found(self):
        """Tests if the _get_car_id_from_name method raises an exception when the car name is not found."""
        with self.assertRaises(InvalidCarName) as context:
            self.call_handler._get_car_id_from_name("non_existent_name")
        self.assertTrue("Car with name: non_existent_name not found." in str(context.exception))


class Test_Call_Handler_Call_Handling(unittest.TestCase):
    """Tests the handle_call_function method of the IncomingCallHandler class."""

    def setUp(self) -> None:
        self.call_handler = _create_test_call_handler()
        self.mock_api = MockApi()
        self.call_handler.car_api = self.mock_api
        self.call_handler.car_state_api = self.mock_api
        self.call_handler.car_action_api = self.mock_api
        self.mock_api._set_cars(
            [Car(id=1, platformHwId=1, name="test_name", carAdminPhone=MobilePhone(phone="test_number"))]
        )
        self.mock_api._set_car_states(
            [CarState(id=0, timestamp=0, status=CarStatus.DRIVING, carId=1)]
        )
        self.mock_api._set_car_action_states(
            [CarActionState(id=0, carId=1, timestamp=0, actionStatus=CarActionStatus.NORMAL)]
        )

    def test_car_pause(self):
        """Tests if the car is paused correctly."""
        response = self.call_handler.handle_call_function({"From": "test_number"})
        self.assertNotEqual(response.find("Car successfully paused."), -1)

    def test_car_pause_action_timeout(self):
        """Tests not changing the car action state to PAUSED from NORMAL throws an error.
        Action status will not be set to PAUSED in the mock API."""
        self.mock_api.actions_not_updating = True
        with self.assertLogs(LOGGER_NAME, level="ERROR") as log:
            response = self.call_handler.handle_call_function({"From": "test_number"})
            self.assertNotEqual(
                log.output[0].find(
                    "An error occured while handling a call: Car did not enter PAUSED action state in time."
                ),
                -1
            )
            self.assertNotEqual(response.find("An error occured while handling the call."), -1)

    def test_car_pause_state_timeout(self):
        """Tests not changing the car state to IDLE throws an error.
        Status will not be set to IDLE in the mock API."""
        self.mock_api.states_not_updating = True
        with self.assertLogs(LOGGER_NAME, level="ERROR") as log:
            response = self.call_handler.handle_call_function({"From": "test_number"})
            self.assertNotEqual(
                log.output[0].find(
                    "An error occured while handling a call: Car did not enter IDLE state in time."
                ),
                -1
            )
            self.assertNotEqual(response.find("An error occured while handling the call."), -1)

    def test_car_unpause(self):
        """Tests if the car is unpaused correctly."""
        self.mock_api._set_car_states(
            [CarState(id=0, timestamp=0, status=CarStatus.IDLE, carId=1)]
        )
        self.mock_api._set_car_action_states(
            [CarActionState(id=0, carId=1, timestamp=0, actionStatus=CarActionStatus.PAUSED)]
        )
        response = self.call_handler.handle_call_function({"From": "test_number"})
        self.assertNotEqual(response.find("Car successfully unpaused."), -1)

    def test_car_unpause_action_timeout(self):
        """Tests not changing the car action state to NORMAL from PAUSED throws an error.
        Action status will not be set to NORMAL in the mock API."""
        self.mock_api._set_car_states(
            [CarState(id=0, timestamp=0, status=CarStatus.IDLE, carId=1)]
        )
        self.mock_api._set_car_action_states(
            [CarActionState(id=0, carId=1, timestamp=0, actionStatus=CarActionStatus.PAUSED)]
        )
        self.mock_api.actions_not_updating = True
        with self.assertLogs(LOGGER_NAME, level="ERROR") as log:
            response = self.call_handler.handle_call_function({"From": "test_number"})
            self.assertNotEqual(
                log.output[0].find(
                    "An error occured while handling a call: Car did not enter NORMAL action state in time."
                ),
                -1
            )
            self.assertNotEqual(response.find("An error occured while handling the call."), -1)


if __name__ == "__main__":
    unittest.main() # pragma: no cover