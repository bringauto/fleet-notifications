# Testing

## Notification calls

1. launch [etna](https://github.com/bringauto/etna) with profile all: `docker compose --profile=all up`
2. edit the provided config file (the default config.json most likely requires no changes when running with etna)
3. run the script by `python3 -m fleet_notifications <path-to-config-file>`
4. notification calls should be triggered in the script automatically as the car starts driving / reaches a stop (car position can be displayed in a browser at http://localhost:5000)(if no calls are attempted, the car likely has the `underTest` parameter set to true)

## Pausing/Unpausing car

### Setup

1. launch [etna](https://github.com/bringauto/etna) with profile all: `docker compose --profile=all up`
2. set up some sort of reverse proxy for twilio to be able to reach the handle-call endpoint
    - [ngrok](https://dashboard.ngrok.com/get-started/setup/linux) can be used for this (requires an account, but is free)
    - after installing, run it with `ngrok http <port>` (port is 8082 in the example config)
3. set the address of the reverse proxy as a webhook for the required twilio number
    - [list of phone numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
    - in voice configuration of the required number, set a webhook url to `<reverse proxy address>/v2/notifications/handle-call`
4. edit the provided config file (the config.json file is already mostly setup for running locally with etna)
    - in `twilio`, set `from_number` to the number that was configured in the previous step
    - `account_sid` and `auth_token` in `twilio` can be found [here](https://console.twilio.com/us1/account/keys-credentials/api-keys)
    - `allowed_incoming_phone_numbers` in `twilio` needs to be set with your phone number as the key and car id as the value (car id should be 1 in etna by default, this can be forced by purging the database with `docker compose --profile=all down`)
5. run the script by `python3 -m fleet_notifications <path-to-config-file> --allow-http`
6. monitor the car movement on http://localhost:5000
7. car states/action states can be observed on http://localhost:8081/v2/management/ui (api key is ManagementStaticAccessKey)

### Test 1

1. wait for the car to be in DRIVING state
2. call the `from_number` with the phone specified in `allowed_incoming_phone_numbers`
3. car should stop driving and enter PAUSED action state

### Test 2

1. make sure the car is in PAUSED action state
2. call the `from_number` with the phone specified in `allowed_incoming_phone_numbers`
3. car should continue driving and enter NORMAL action state

### Test 3

1. call the `from_number` with a different phone than specified in `allowed_incoming_phone_numbers`
2. car should not change any of its states
