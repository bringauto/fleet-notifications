import dataclasses
from typing import Any
import argparse
import json

from fleet_notifications.script_args.configs import ScriptConfig as _ScriptConfig
import logging


_EMPTY_VALUE = None


@dataclasses.dataclass
class PositionalArgInfo:
    name: str
    type: type
    help: str


@dataclasses.dataclass(frozen=True)
class ScriptArgs:
    argvals: dict[str, str]
    config: _ScriptConfig


def request_and_get_script_arguments(
    script_description: str, *positional_args: PositionalArgInfo
) -> ScriptArgs:
    """Create base for the script.

    `script_description` is the summary of the scritp's purpose shown as the first part of the script's help.
    `positional_args` are the arguments that are required to run the script.

    The script then returns ScriptArgs which contains
    - `argvals` which is a dictionary of the arguments passed to the script,
    - `config` which is the configuration for the script. If some of the arguments overriding the configuration
       are passed, the configuration is updated with the arguments.

    Raises error if
    - the configuration file is not found or not valid,
    - any of the positional arguments are missing or of invalid type.
    """

    parser = _new_arg_parser(script_description)
    _add_positional_args_to_parser(parser, *positional_args)
    _add_config_arg_to_parser(parser)
    _add_db_args_to_parser(parser)
    return _parse_arguments(parser)


def _add_config_arg_to_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("<config-file-path>", type=str, help="The path to the config file.")


def _add_db_args_to_parser(parser: argparse.ArgumentParser) -> None:
    _add_str_option(parser, "-usr", "--username", "The username for the database server.")
    _add_str_option(parser, "-pwd", "--password", "The password for the database server.")
    _add_str_option(parser, "-l", "--location", "The location/address of the database")
    _add_str_option(parser, "-p", "--port", "The database port number.")
    _add_str_option(parser, "-db", "--database-name", "The name of the database.")


def _add_str_option(
    parser: argparse.ArgumentParser, short: str, full: str, description: str
) -> None:
    parser.add_argument(
        short,
        full,
        type=str,
        help=description,
        default=_EMPTY_VALUE,
        required=False,
    )


def _add_positional_args_to_parser(
    parser: argparse.ArgumentParser, *args: PositionalArgInfo
) -> None:
    for arg in args:
        parser.add_argument(arg.name, type=arg.type, help=arg.help)


def _new_arg_parser(script_description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=script_description)


def load_config_file(path: str) -> dict[str, Any]:
    try:
        with open(path) as config_file:
            config = json.load(config_file)
            return config
    except FileNotFoundError:
        raise ConfigFileNotFound(f"Could not load config file from path '{path}'.")
    except Exception as e:
        raise ValueError(f"Error when loading the config file: {e}")


def _parse_arguments(parser: argparse.ArgumentParser) -> ScriptArgs:
    args = parser.parse_args().__dict__
    config_path = args.pop("<config-file-path>")
    try:
        config_dict = load_config_file(config_path)
        config = _ScriptConfig(**config_dict)
        _update_config_with_args(args, config)
        return ScriptArgs(args, config)

    except ConfigFileNotFound as e:
        logging.error(f"Configuration file not found. {e}")
        raise
    except Exception as e:
        logging.error(f"Check the configuration file ('{config_path}'). {e}")
        raise e


def _update_config_with_args(args: dict[str, Any], config: _ScriptConfig) -> None:
    if args["username"] != _EMPTY_VALUE:
        config.database.connection.username = args["username"]
    if args["password"] != _EMPTY_VALUE:
        config.database.connection.password = args["password"]
    if args["location"] != _EMPTY_VALUE:
        config.database.connection.location = args["location"]
    if args["port"] != _EMPTY_VALUE:
        config.database.connection.port = args["port"]
    if args["database_name"] != _EMPTY_VALUE:
        config.database.connection.database_name = args["database_name"]


class ConfigFileNotFound(Exception):
    pass