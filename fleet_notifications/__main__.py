import sys
sys.path.append("fleet_notifications")
import logging

from database.connection import set_db_connection
from database.database_controller import create_orders_table
import database.script_args as script_args  # type: ignore
from state_checker import start
from fleet_management_http_client_python import ApiClient, Configuration


def _connect_to_database(vals: script_args.ScriptArgs) -> None:
    """Connect to the database."""
    set_db_connection(
        dblocation = vals.argvals["location"] + ":" + str(vals.argvals["port"]),
        username = vals.argvals["username"],
        password = vals.argvals["password"],
        db_name = vals.argvals["database_name"]
    )


def _set_up_log_format() -> None:
    """Set up the logging format."""
    FORMAT = '%(asctime)s -- %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)


if __name__ == '__main__':
    vals = script_args.request_and_get_script_arguments("Run the Fleet notifications script.")
    config = vals.config
    _set_up_log_format()
    _connect_to_database(vals)
    create_orders_table()
    api_client = ApiClient(Configuration(
        host=config['fleet_management_server']['base_uri'],
        api_key={'APIKeyAuth': config['fleet_management_server']['api_key']}
    ))
    start(config, api_client)