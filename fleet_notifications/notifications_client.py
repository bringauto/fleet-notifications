import logging
import time

from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance


class NotificationClient:
    def __init__(self, config: dict):
        self._account_sid = config["account_sid"]
        self._auth_token = config["auth_token"]
        self._from_number = config["from_number"]
        self._url = config["play_sound_url"]
        self._repeated_calls = config["repeated_calls"]
        self._call_status_timeout_count = config["call_status_timeout_count"]
        self._client = Client(self._account_sid, self._auth_token)


    def call_phone(self, phone_number: str) -> None:
        logging.info("Calling phone number: " + phone_number)
        # for _ in range(self._repeated_calls):
        #     sid = self._client.calls.create(
        #         to=phone_number,
        #         from_=self._from_number,
        #         twiml=f'<Response><Play loop="10">{self._url}</Play></Response>'
        #     )
        #     if self._wait_for_pickup(sid):
        #         break
        time.sleep(10)
        logging.info("Async debug ended.")


    def _wait_for_pickup(self, sid: str) -> bool:
        logging.info("Waiting for pickup: " + sid)
        call = self._client.calls.get(sid)
        call_status = call.fetch().status
        timeout_count = 0

        while (
            call_status != CallInstance.Status.IN_PROGRESS and
            call_status != CallInstance.Status.COMPLETED and
            call_status != CallInstance.Status.BUSY and
            call_status != CallInstance.Status.NO_ANSWER and
            call_status != CallInstance.Status.CANCELED and
            call_status != CallInstance.Status.FAILED
        ):
            time.sleep(2)
            call_status = call.fetch().status
            timeout_count += 1
            if timeout_count > self._call_status_timeout_count:
                logging.error("Call polling timed out.")
                return True

        return call_status != CallInstance.Status.NO_ANSWER