import logging, time

from twilio.rest import Client # type: ignore
from twilio.rest.api.v2010.account.call import CallInstance # type: ignore
from fleet_notifications.script_args.configs import Twilio
from fleet_notifications.logs import LOGGER_NAME


PICK_UP_WAIT_INTERVAL = 2
logger = logging.getLogger(LOGGER_NAME)


class NotificationClient:
    def __init__(self, twilio_config: Twilio):
        self._account_sid = twilio_config.account_sid
        self._auth_token = twilio_config.auth_token
        self._from_number = twilio_config.from_number
        self._url = twilio_config.play_sound_url
        self._n_of_repeated_calls = twilio_config.repeated_calls
        self._call_status_timeout_s = twilio_config.call_status_timeout_s
        self._client = Client(self._account_sid, self._auth_token)


    def call_phone(self, phone_number: str, under_test: bool) -> None:
        """Calls the provided phone number and plays a sound. If the call is not picked up, it will be repeated."""
        if not under_test:
            if phone_number == "":
                logger.warning("No phone number provided.")
                return

            logger.info("Calling phone number: " + phone_number)
            try:
                for _ in range(self._n_of_repeated_calls):
                    sid = self._client.calls.create(
                        to=phone_number,
                        from_=self._from_number,
                        twiml=f'<Response><Play loop="10">{self._url}</Play></Response>'
                    )
                    if self._wait_for_pickup(sid):
                        break
            except Exception as e:
                logger.error(f"An error occured while handling a call to number {phone_number} : {e}")


    def _is_call_picked_up(self, call_status: CallInstance.Status) -> bool:
        """Returns true if the call was picked up, false otherwise."""
        if(call_status == CallInstance.Status.IN_PROGRESS or
           call_status == CallInstance.Status.COMPLETED or
           call_status == CallInstance.Status.BUSY or
           call_status == CallInstance.Status.NO_ANSWER or
           call_status == CallInstance.Status.CANCELED or
           call_status == CallInstance.Status.FAILED):
            return True
        return False


    def _wait_for_pickup(self, sid: CallInstance) -> bool:
        """Returns true if the call was picked up within a certain time frame, false otherwise."""
        logger.info("Waiting for pickup: " + sid.sid)
        call = self._client.calls.get(sid.sid)
        call_status = call.fetch().status
        timeout_count = 0

        while (not self._is_call_picked_up(call_status)):
            time.sleep(PICK_UP_WAIT_INTERVAL)
            call_status = call.fetch().status
            timeout_count += PICK_UP_WAIT_INTERVAL
            if timeout_count > self._call_status_timeout_s:
                logger.error("Call polling timed out.")
                return True

        if call_status == CallInstance.Status.FAILED:
            logger.warning(f"Call: {sid.sid} failed.")
            return True
        return call_status != CallInstance.Status.NO_ANSWER
