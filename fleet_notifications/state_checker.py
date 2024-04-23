import logging

from fleet_management_http_client_python import ApiClient, CarApi, CarStateApi, CarState, CarStatus
from fleet_notifications.notifications_client import NotificationClient


_api_client : ApiClient = None
_notification_client : NotificationClient = None


def _call_admin_phone(car_state: CarState) -> None:
    car_api = CarApi(_api_client)
    car = car_api.get_car(car_state.car_id)
    _notification_client.call_phone(car.car_admin_phone.to_str())


def _call_stop_phone() -> None:
    _notification_client.call_phone("NYI")


def _handle_state_transition(old_state: CarStatus, car_state: CarState) -> None:
    logging.info(f"State transition: {old_state} -> {car_state.status}")
    if old_state == CarStatus.IDLE and car_state.status == CarStatus.DRIVING:
        _call_admin_phone(car_state)
    elif old_state == CarStatus.DRIVING and car_state.status == CarStatus.IN_STOP:
        _call_stop_phone()
    else:
        logging.info("State transition undefined.")


def start(config: dict, api_client: ApiClient) -> None:
    global _api_client, _notification_client
    _api_client = api_client
    _notification_client = NotificationClient(config['twilio'])

    logging.info(f"Car name: {config['car']['name']}")
    car_api = CarApi(api_client)
    cars = car_api.get_cars()
    car_id = 0
    for car in cars:
        if car.name == config['car']['name']:
            logging.info(f"Car found, ID: {car.id}")
            car_id = car.id
            break

    car_state_api = CarStateApi(api_client)
    since = 0
    old_state = CarStatus.OUT_OF_ORDER

    try:
        while car_id != 0:
            logging.info("Checking the state of the car.")
            states = car_state_api.get_car_states(
                car_id=car_id,
                wait=True,
                since=since+1,
                last_n=1
            )
            for state in states:
                logging.info(f"Car state: {state}")
                if state.timestamp > since:
                    if old_state != state.status:
                        _handle_state_transition(old_state, state)
                    old_state = state.status
                    since = state.timestamp
    except KeyboardInterrupt:
        logging.info("Exiting the script.")
        pass
