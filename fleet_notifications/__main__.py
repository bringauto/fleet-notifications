import threading

import fleet_notifications.script_args as _args
from fleet_notifications.database.connection import set_db_connection
from fleet_notifications.database.database_controller import create_orders_table
from fleet_notifications.state_checker import start
from fleet_notifications.incoming_call_endpoint import run_app
from fleet_notifications.logs import configure_logging
from fleet_management_http_client_python import ApiClient, Configuration


def _connect_to_database(connection: _args.Database.Connection) -> None:
    """Connect to the database."""
    set_db_connection(
        dblocation = connection.location + ":" + str(connection.port),
        username = connection.username,
        password = connection.password,
        db_name = connection.database_name
    )


if __name__ == '__main__':
    args = _args.request_and_get_script_arguments("Run the Fleet notifications script.")
    
    try:
        configure_logging("Fleet Notifications", args.config)
    except Exception as e:
        print(f"Error when configuring logging: {e}")
        exit(1)

    config = args.config
    _connect_to_database(config.database.connection)
    create_orders_table()
    api_client = ApiClient(Configuration(
        host=str(config.fleet_management_server.base_uri),
        api_key={'APIKeyAuth': config.fleet_management_server.api_key}
    ))
    
    threading.Thread(target=start, args=(config.twilio, api_client), daemon=True).start()
    run_app(config.twilio, config.http_server, api_client)