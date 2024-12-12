# Testing

## Pausing/Unpausing car

- launch [etna](https://github.com/bringauto/etna) with profile all
- set up some sort of reverse proxy for twilio to be able to reach the handle-call endpoint
  - [ngrok](https://dashboard.ngrok.com/get-started/setup/linux) can be used for this (requires an account, but is free)
  - after installing, run it with `ngrok http <port>` (port is 8082 in the example config)
- set the address of the reverse proxy as a webhook for the required twilio number
  - [list of phone numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
  - in voice configuration of the required number, set a webhook url to `<reverse proxy address>/handle-call`
- create a valid config file (the config.json file is already mostly setup for running locally with etna)
  - in `twilio`, set `from_number` to the number that was configured in the previous step
  - `account_sid` and `auth_token` in `twilio` can be found [here](https://console.twilio.com/us1/account/keys-credentials/api-keys)
  - `allowed_incoming_phone_numbers` in `twilio` needs to be set with your phone number as the key and car id as the value (car id should be 1 in etna by default, this can be forced by purging the database with `docker compose --profile=all down`)
- run the script by `python3 -m fleet_notifications <path-to-config-file>`
- try calling the twilio phone number to see if it forces the car to pause/unpause (car position can be displayed in a browser at http://localhost:5000)
  - if the request fails because of an invalid url comment out line 51 in `incoming_call_endpoint.py` and uncomment line 52
  