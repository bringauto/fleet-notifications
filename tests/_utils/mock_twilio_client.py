import random
import string

from twilio.rest.api.v2010.account.call import CallInstance # type: ignore


class MockCallInstance:
    def __init__(self):
        self.status = CallInstance.Status.QUEUED


class MockCall:
    def __init__(self, sid):
        self.sid = sid
        self._instance = MockCallInstance()

    def fetch(self):
        return self._instance


class MockCallList:
    def __init__(self):
        self.calls = []

    @staticmethod
    def _generate_random_sid():
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(16))

    def create(self, to="", from_="", twiml=""):
        if to == "EXCEPTION":
            raise Exception("Forced test exception")
        call = MockCall(self._generate_random_sid())
        self.calls.append(call)
        return call

    def get(self, sid):
        for call in self.calls:
            if call.sid == sid:
                return call


class MockTwilioClient:
    def __init__(self):
        self.calls = MockCallList()