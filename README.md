# Fleet notifications

This script contains serves 2 functions:
- [Notifying](#notifications) relevant numbers about car activity
- [Handling incoming calls](#twilio-endpoint) to a twilio number in order to pause/unpause a car

### Notifications

Python script that generates notifications on state changes of Fleet Protocol devices.

This script is responsible for calling the car admin number and the number assigned to stops. Car admins are called whenever a mission is started, stop numbers are called whenever a car reaches a stop.

Order states from the [Fleet Management API] are being checked constantly. If the received state belongs to a new order, the order gets saved locally until it is finished (this is currently only used to save the latest order state timestamp). If the newly saved order is the only one saved, the car admin phone is called. This assumes a new mission has started and the car admin should be notified. If a state has the status DONE, and the previous status was different, the phone number of the corresponding stop gets called.

The following flow chart is a simplified version of the program logic:

![Notifications Flow](./doc/img/notifications_flow.png)

### Twilio endpoint

This script also contains an HTTP endpoint for to serve as a webhook for inconming calls to twilio numbers. This endpoint verifies the calling number and uses the pause/unpause endpoint on [Fleet Management API] as needed.

## Requirements
Python 3.10.12+

## Usage

Activate virtual environment and install dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

To run the script execute the following from the root directory:

```bash
python3 -m fleet_notifications <path-to-config-file> [OPTIONS]
```

Command line options:

| Option         | Description                                          |
|----------------|------------------------------------------------------|
| `--allow-http` | Enable twilio validation on URLs that are not secure |

The script automatically connects to the PostgreSQL database using data from the config file. If you want to override these values, start the server with some of the following options:

| Option            | Short  | Description                                  |
|-------------------|--------|----------------------------------------------|
| `--username`      | `-usr` | Username for the PostgreSQL database         |
| `--password`      | `-pwd` | Password for the PostgreSQL database         |
| `--location`      | `-l`   | Location of the database (e.g., `localhost`) |
| `--port`          | `-p`   | Port number (e.g., `5430`)                   |
| `--database-name` | `-db`  | Database name                                |

Note that these data should comply with the requirements specified in SQLAlchemy [documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).

## Testing

To fully test the script, launch the unit tests and follow the procedure described in manual testing.

### Manual
Described in [testing](./doc/testing.md).

### Unit tests

#### Preparing the environment and dependencies

Set up the virtual environment and install the dependencies. Install the tests dependencies and the project itself in editable mode:

```bash
pip install -r tests/requirements.txt
pip install -e .
```

#### Running the tests

In the root folder, run the following

```bash
python -m tests [-h] [PATH1] [PATH2] ...
```

Each PATH is specified relative to the `tests` folder. If no PATH is specified, all the tests will run. Otherwise

- when PATH is a directory, the script will run all tests in this directory (and subdirectories),
- when PATH is a Python file, the script will run all tests in the file.

The `-h` flag makes the script display tests' coverage in an HTML format, for example in your web browser.

##### Example

```bash
python -m tests test_call_handler.py
```

## Configuration
The settings can be found in the `config/config.json`, including the database information and parameters for Fleet management connection.

```json
{
    "logging": {
        "console": {
            "level": "debug",
            "use": true
        },
        "file": {
            "level": "debug",
            "use": false,
            "path": "./log/"
        }
    },
    "http_server": {
        "port": 8082
    },
    "fleet_management_server": {
        "base_uri": "https://api.dev.bringautofleet.com/v2/management",
        "api_key": ""
    },
    "twilio": {
        "account_sid": "",
        "auth_token": "",
        "from_number": "+420123456789",
        "notifications": {
            "play_sound_url": "https://bringauto.com/wp-content/uploads/2021/10/BringAuto.mp3",
            "repeated_calls": 3,
            "call_status_timeout_s": 120
        },
        "call_handling": {
            "car_action_change_timeout_s": 5,
            "allowed_incoming_phone_numbers": {
                "+420987654321": "virtual_vehicle",
                "+420111111111": "bap2019_01"
            }
        }
    },
    "database": {
        "connection": {
            "location": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "1234",
            "database_name": "postgres"
        }
    }
}
```
- http_server
  - port: port used for the handle-call endpoint
- twilio
  - from_number: twilio phone number used for notifications and stopping the car
  - play_sound_url: url of a sound file to be played in notifications
  - repeated_calls: how many times a phone will be called until a call is picked up
  - call_status_timeout_s: how much time should pass for a call to be considered timeouted
  - car_action_change_timeout_s: how much time should pass before a car should change actions reliably
  - allowed_incoming_phone_numbers: which phone numbers are allowed to pause/unpause the car with an assigned name


  [Fleet Management API]: https://github.com/bringauto/fleet-management-http-api