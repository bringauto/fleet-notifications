from flask import abort, Flask, request
from functools import wraps
from twilio.twiml.voice_response import VoiceResponse
from twilio.request_validator import RequestValidator
from fleet_notifications.script_args.configs import Twilio, HTTPServer
from fleet_management_http_client_python import ApiClient, CarActionApi, CarApi, CarActionStatus


app = Flask(__name__)
_twilio_auth_token = ""
_allowed_incoming_phone_numbers = dict()
_car_action_api = None


def validate_twilio_request(f):
    """Validates that incoming requests genuinely originated from Twilio"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        validator = RequestValidator(_twilio_auth_token)
        request_valid = validator.validate(
            request.url,
            #request.url.replace('http://', 'https://'), # use this when running locally
            request.form,
            request.headers.get('X-Twilio-Signature', ''))
        if request_valid and request.values['From'] in _allowed_incoming_phone_numbers.keys():
            return f(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function


# https://www.twilio.com/docs/voice/twiml/gather
# gather (twiml) can be used to collect dtmf presses during a call
# we can use this to select car ids if a number should have access to multiple cars
@app.route("/handle-call", methods=['GET', 'POST'])
@validate_twilio_request
def handle_call():
    """Handle incoming calls from Twilio"""
    resp = VoiceResponse()
    
    try:
        car_id = _allowed_incoming_phone_numbers[request.values['From']]
        action_status = _car_action_api.get_car_action_states(car_id, last_n=1)[0].action_status

        if action_status == CarActionStatus.PAUSED:
            _car_action_api.unpause_car(car_id)
            resp.say("Car successfully unpaused.")
        else:
            _car_action_api.pause_car(car_id)
            resp.say("Car successfully paused.")
    except Exception:
        resp.say("An error occured while handling the call.")
    
    return str(resp)


def run_app(twilio_config: Twilio, server_config: HTTPServer, api_client: ApiClient):
    global _twilio_auth_token
    global _allowed_incoming_phone_numbers
    global _car_action_api
    _twilio_auth_token = twilio_config.auth_token
    _allowed_incoming_phone_numbers = twilio_config.allowed_incoming_phone_numbers
    _car_action_api = CarActionApi(api_client)
    app.run(port=server_config.port)