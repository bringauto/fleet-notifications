import logging

from twilio.rest import Client


class NotificationClient:
    def __init__(self, config: dict):
        self._account_sid = config["account_sid"]
        self._auth_token = config["auth_token"]
        self._from_number = config["from_number"]
        self._url = config["play_sound_url"]
        self._client = Client(self._account_sid, self._auth_token)


    def call_phone(self, phone_number: str) -> None:
        logging.info("Calling phone number: " + phone_number)
        # self._client.calls.create(
        #     to=phone_number,
        #     from_=self._from_number,
        #     twiml=f'<Response><Play loop="10">{self._url}</Play></Response>'
        # )