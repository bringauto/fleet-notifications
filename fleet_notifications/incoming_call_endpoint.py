import logging, time

from flask import abort, Flask, request
from functools import wraps
from twilio.twiml.voice_response import VoiceResponse # type: ignore
from twilio.request_validator import RequestValidator # type: ignore
from fleet_notifications.script_args.configs import Twilio, HTTPServer
from fleet_management_http_client_python import ApiClient, CarActionApi, CarStateApi, CarActionStatus, CarStatus, CarApi # type: ignore
from fleet_notifications.logs import LOGGER_NAME


WAITING_TIME_PERIOD = 1
logger = logging.getLogger(LOGGER_NAME)

flask_app = Flask(__name__)


class FlaskAppWrapper(object):
    def __init__(self, app, **configs):
        self.app = app
        self.configs(**configs)

    def configs(self, **configs):
        for config, value in configs:
            self.app.config[config.upper()] = value

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=['GET'], *args, **kwargs):
        self.app.add_url_rule(endpoint, endpoint_name, handler, methods=methods, *args, **kwargs)

    def run(self, **kwargs):
        self.app.run(**kwargs)


class IncomingCallHandler:
    def __init__(self, twilio_config: Twilio, server_config: HTTPServer, api_client: ApiClient, allow_http: bool):
        self.twilio_auth_token = twilio_config.auth_token
        self.allowed_incoming_phone_numbers = twilio_config.call_handling.allowed_incoming_phone_numbers
        self.action_timeout_s = twilio_config.call_handling.car_action_change_timeout_s
        self.car_action_api = CarActionApi(api_client)
        self.car_state_api = CarStateApi(api_client)
        self.car_api = CarApi(api_client)
        self.server_port = server_config.port
        self.allow_http = allow_http


    def _car_action_status_occurred(self, awaited_statuses: set[CarActionStatus], car_id: int) -> bool:
        """Wait for the action status of the car with ID equal to car_id to change to one of the specified statuses.
        The set of awaited statuses must not be empty. Return True if the awaited status occured before timeout,
        False otherwise."""
        timeout_count = 0
        while self.car_action_api.get_car_action_states(car_id, last_n=1)[0].action_status not in awaited_statuses:
            time.sleep(WAITING_TIME_PERIOD)
            timeout_count += WAITING_TIME_PERIOD
            if timeout_count > self.action_timeout_s:
                return False
        return True


    def _car_status_occured(self, awaited_statuses: set[CarStatus], car_id: int) -> bool:
        """Wait for the status of the car with ID equal to car_id to change to one of the specified statuses.
        The set of awaited statuses must not be empty. Return True if the awaited status occured before timeout,
        False otherwise."""
        timeout_count = 0
        while self.car_state_api.get_car_states(car_id, last_n=1)[0].status not in awaited_statuses:
            time.sleep(WAITING_TIME_PERIOD)
            timeout_count += WAITING_TIME_PERIOD
            if timeout_count > self.action_timeout_s:
                return False
        return True


    def _get_car_id_from_name(self, name: str) -> int:
        """Get the car ID from its name"""
        for car in self.car_api.get_cars():
            if car.name == name:
                return car.id
        raise Exception(f"Car with name: {id} not found.")


    @staticmethod
    def _validate_twilio_request(f):
        """Validates that incoming requests genuinely originated from Twilio"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            call_handler = args[0]
            url = request.url
            if call_handler.allow_http:
                url = url.replace('http://', 'https://')
            validator = RequestValidator(call_handler.twilio_auth_token)
            request_valid = validator.validate(
                url,
                request.form,
                request.headers.get('X-Twilio-Signature', ''))
            if request_valid and request.values['From'] in call_handler.allowed_incoming_phone_numbers.keys():
                return f(*args, **kwargs)
            else:
                return abort(403)
        return decorated_function


    @_validate_twilio_request
    def _handle_call(self):
        """Handle incoming calls from Twilio"""
        resp = VoiceResponse()

        try:
            car_id = self._get_car_id_from_name(self.allowed_incoming_phone_numbers[request.values['From']])
            action_status = self.car_action_api.get_car_action_states(car_id, last_n=1)[0].action_status

            if action_status == CarActionStatus.PAUSED:
                self.car_action_api.unpause_car(car_id)
                if not self._car_action_status_occurred([CarActionStatus.NORMAL], car_id):
                    raise Exception("Car did not enter NORMAL action state in time.")
                resp.say("Car successfully unpaused.")
            else:
                self.car_action_api.pause_car(car_id)
                if not self._car_action_status_occurred([CarActionStatus.PAUSED], car_id):
                    raise Exception("Car did not enter PAUSED action state in time.")
                if not self._car_status_occured([CarStatus.IDLE, CarStatus.OUT_OF_ORDER], car_id):
                    raise Exception("Car did not enter IDLE state in time.")
                resp.say("Car successfully paused.")
        except Exception as e:
            logger.error(f"An error occured while handling a call: {e}", exc_info=True)
            resp.say("An error occured while handling the call.")
        
        return str(resp)


    def run_app(self):
        app = FlaskAppWrapper(flask_app)
        app.add_endpoint("/v2/notifications/handle-call", "handle_call", self._handle_call, methods=['GET', 'POST'])
        app.run(host='0.0.0.0', port=self.server_port)
