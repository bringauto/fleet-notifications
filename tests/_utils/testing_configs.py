from fleet_notifications.script_args.configs import Twilio


TEST_TWILIO_CONFIG = Twilio(
    account_sid="test_sid",
    auth_token="test_token",
    from_number="test_from_number",
    notifications=Twilio.Notifications(
        play_sound_url="http://example.com/sound.mp3",
        repeated_calls=3,
        call_status_timeout_s=3
    ),
    call_handling=Twilio.CallHandling(
        car_action_change_timeout_s=3,
        allowed_incoming_phone_numbers={
            "test_number": "test_name"
        }
    )
)