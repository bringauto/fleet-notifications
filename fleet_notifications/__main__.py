import sys

import fleet_notifications.script_args as _args

from fleet_notifications.database.database_controller import initialize_db
from fleet_notifications.state_checker import OrderStateChecker
from fleet_notifications.incoming_call_endpoint import IncomingCallHandler
from fleet_notifications.logs import configure_logging
from fleet_management_http_client_python import ApiClient, Configuration # type: ignore


def main():
    args = _args.request_and_get_script_arguments("Run the Fleet notifications script.")

    try:
        configure_logging("Fleet Notifications", args.config)
    except Exception as e:
        print(f"Error when configuring logging: {e}")
        sys.exit(1)

    config = args.config
    initialize_db(config.database.connection)
    api_client = ApiClient(Configuration(
        host=str(config.fleet_management_server.base_uri),
        api_key={'APIKeyAuth': config.fleet_management_server.api_key}
    ))

    state_checker = OrderStateChecker(config.twilio, api_client)
    state_checker.start_thread()
    incoming_call_handler = IncomingCallHandler(config.twilio, config.http_server, api_client,
                                                args.argvals["allow_http"])
    incoming_call_handler.run_app()

if __name__ == '__main__':
    main()
