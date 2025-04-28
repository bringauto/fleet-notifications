import unittest

from twilio.rest import Client # type: ignore
from twilio.rest.api.v2010.account.call import CallInstance # type: ignore

from fleet_notifications.notifications_client import NotificationClient
from fleet_notifications.logs import LOGGER_NAME
from tests._utils.mock_twilio_client import MockTwilioClient
from tests._utils.testing_configs import TEST_TWILIO_CONFIG


class Test_Notification_Client_Initialization(unittest.TestCase):

    def test_initialization(self):
        notification_client = NotificationClient(TEST_TWILIO_CONFIG)
        self.assertEqual(notification_client._account_sid, TEST_TWILIO_CONFIG.account_sid)
        self.assertEqual(notification_client._auth_token, TEST_TWILIO_CONFIG.auth_token)
        self.assertEqual(notification_client._from_number, TEST_TWILIO_CONFIG.from_number)
        self.assertEqual(notification_client._url, TEST_TWILIO_CONFIG.notifications.play_sound_url)
        self.assertEqual(notification_client._n_of_repeated_calls, TEST_TWILIO_CONFIG.notifications.repeated_calls)
        self.assertEqual(notification_client._call_status_timeout_s, TEST_TWILIO_CONFIG.notifications.call_status_timeout_s)
        self.assertTrue(isinstance(notification_client._client, Client))


class Test_Notification_Client_Is_Call_Picked_Up(unittest.TestCase):

    def test_is_call_picked_up(self):
        notification_client = NotificationClient(TEST_TWILIO_CONFIG)
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.IN_PROGRESS))
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.COMPLETED))
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.BUSY))
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.NO_ANSWER))
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.CANCELED))
        self.assertTrue(notification_client._is_call_picked_up(CallInstance.Status.FAILED))
        self.assertFalse(notification_client._is_call_picked_up(CallInstance.Status.QUEUED))
        self.assertFalse(notification_client._is_call_picked_up(CallInstance.Status.RINGING))


class Test_Notification_Client_Wait_For_Pickup(unittest.TestCase):

    def setUp(self) -> None:
        self.notification_client = NotificationClient(TEST_TWILIO_CONFIG)
        self.notification_client._client = MockTwilioClient()
        self.call = self.notification_client._client.calls.create()

    def test_wait_for_pickup_completed(self):
        self.notification_client._client.calls.get(self.call.sid).fetch().status = CallInstance.Status.COMPLETED
        self.assertTrue(self.notification_client._wait_for_pickup(self.call))

    def test_wait_for_pickup_no_answer(self):
        self.notification_client._client.calls.get(self.call.sid).fetch().status = CallInstance.Status.NO_ANSWER
        self.assertFalse(self.notification_client._wait_for_pickup(self.call))

    def test_wait_for_pickup_timeout(self):
        self.notification_client._client.calls.get(self.call.sid).fetch().status = CallInstance.Status.RINGING
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.assertTrue(self.notification_client._wait_for_pickup(self.call))
            self.assertNotEqual(log.output[0].find("Call polling timed out."), -1)

    def test_wait_for_pickup_failed(self):
        self.notification_client._client.calls.get(self.call.sid).fetch().status = CallInstance.Status.FAILED
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.assertTrue(self.notification_client._wait_for_pickup(self.call))
            self.assertNotEqual(log.output[0].find(f"Call: {self.call.sid} failed."), -1)


class Test_Notification_Client_Call_Phone(unittest.TestCase):

    def setUp(self) -> None:
        self.notification_client = NotificationClient(TEST_TWILIO_CONFIG)
        self.notification_client._client = MockTwilioClient()
        self.call = self.notification_client._client.calls.create()

    def test_call_phone_no_number(self):
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.notification_client.call_phone("", under_test=False)
            self.assertNotEqual(log.output[0].find("No phone number provided."), -1)

    def test_call_phone_success(self):
        self.notification_client._client.calls.get(self.call.sid).fetch().status = CallInstance.Status.COMPLETED
        with self.assertLogs(LOGGER_NAME, level="INFO") as log:
            self.notification_client.call_phone("test_number", under_test=False)
            self.assertNotEqual(log.output[0].find("Calling phone number: test_number"), -1)

    def test_call_phone_timeout(self):
        with self.assertLogs(LOGGER_NAME, level="WARNING") as log:
            self.notification_client.call_phone("test_number", under_test=False)
            self.assertNotEqual(log.output[0].find("Call polling timed out."), -1)

    def test_call_phone_exception(self):
        with self.assertLogs(LOGGER_NAME, level="ERROR") as log:
            self.notification_client.call_phone("EXCEPTION", under_test=False)
            self.assertNotEqual(log.output[0].find(
                "An error occured while handling a call to number EXCEPTION : Forced test exception"
            ), -1)

    def test_call_phone_under_test(self):
        with self.assertNoLogs(LOGGER_NAME, level="INFO") as log:
            self.notification_client.call_phone("test_number", under_test=True)


if __name__ == "__main__":
    unittest.main() # pragma: no cover