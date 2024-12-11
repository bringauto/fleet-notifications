import logging
import time

from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance
from fleet_notifications.script_args.configs import Twilio
from fleet_notifications.logs import LOGGER_NAME


logger = logging.getLogger(LOGGER_NAME)


class NotificationClient:
    def __init__(self, twilio_config: Twilio):
        self._account_sid = twilio_config.account_sid
        self._auth_token = twilio_config.auth_token
        self._from_number = twilio_config.from_number
        self._url = twilio_config.play_sound_url
        self._repeated_calls = twilio_config.repeated_calls
        self._call_status_timeout_s = twilio_config.call_status_timeout_s
        self._client = Client(self._account_sid, self._auth_token)


    def call_phone(self, phone_number: str, under_test: bool) -> None:
        if not under_test and phone_number != "":
            logger.info("Calling phone number: " + phone_number)
            try:
                for _ in range(self._repeated_calls):
                    sid = self._client.calls.create(
                        to=phone_number,
                        from_=self._from_number,
                        twiml=f'<Response><Play loop="10">{self._url}</Play></Response>'
                    )
                    if self._wait_for_pickup(sid):
                        break
            except Exception as e:
                logger.error(f"An error occured while handling a call to number {phone_number} : {e}")


    def _wait_for_pickup(self, sid: CallInstance) -> bool:
        logger.info("Waiting for pickup: " + sid.sid)
        call = self._client.calls.get(sid.sid)
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
            timeout_count += 2
            if timeout_count > self._call_status_timeout_s:
                logger.error("Call polling timed out.")
                return True

        if call_status == CallInstance.Status.FAILED:
            logger.warning(f"Call: {sid.sid} failed.")
            return True
        return call_status != CallInstance.Status.NO_ANSWER