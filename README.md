# Fleet notifications


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
To run the script execute the following from the root directory:

```bash
pip3 install -r requirements.txt
python3 -m fleet_notifications <path-to-config-file> [OPTIONS]
```
The script automatically connects to the PostgreSQL database using data from the config file. If you want to override these values, start the server with some of the following options:

| Option            | Short  | Description                                  |
|-------------------|--------|----------------------------------------------|
| `--username`      | `-usr` | Username for the PostgreSQL database         |
| `--password`      | `-pwd` | Password for the PostgreSQL database         |
| `--location`      | `-l`   | Location of the database (e.g., `localhost`) |
| `--port`          | `-p`   | Port number (e.g., `5430`)                   |
| `--database-name` | `-db`  | Database name                                |

Note that these data should comply with the requirements specified in SQLAlchemy [documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).

### Testing

Testing has to be done manually. Described in [testing](./doc/testing.md).

### Configuration
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
        "play_sound_url": "https://bringauto.com/wp-content/uploads/2021/10/BringAuto.mp3",
        "repeated_calls": 3,
        "call_status_timeout_s": 120,
        "car_action_change_timeout_s": 5,
        "allowed_incoming_phone_numbers": {
            "+420987654321": 1,
            "+420111111111": 5
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
  - allowed_incoming_phone_numbers: which phone numbers are allowed to pause/unpause the car with an assigned id


  [Fleet Management API]: https://github.com/bringauto/fleet-management-http-api