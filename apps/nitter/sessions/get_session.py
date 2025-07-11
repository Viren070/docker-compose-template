#!/usr/bin/env python3
import requests
import json
import sys
import pyotp
import os

# NOTE: pyotp and requests are dependencies
# > pip install pyotp requests

TW_CONSUMER_KEY = '3nVuSoBZnx6U4vzUxf5w'
TW_CONSUMER_SECRET = 'Bcs59EFbbsdF6Sl9Ng71smgStWEGwXXKSjYvPVt7qys'

def auth(username, password, otp_secret):
    bearer_token_req = requests.post("https://api.twitter.com/oauth2/token",
        auth=(TW_CONSUMER_KEY, TW_CONSUMER_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data='grant_type=client_credentials'
    ).json()
    bearer_token = ' '.join(str(x) for x in bearer_token_req.values())

    guest_token = requests.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers={'Authorization': bearer_token}
    ).json().get('guest_token')

    if not guest_token:
        print("Failed to obtain guest token.")
        sys.exit(1)

    twitter_header = {
        'Authorization': bearer_token,
        "Content-Type": "application/json",
        "User-Agent": "TwitterAndroid/10.21.0-release.0 (310210000-r-0) ONEPLUS+A3010/9 (OnePlus;ONEPLUS+A3010;OnePlus;OnePlus3;0;;1;2016)",
        "X-Twitter-API-Version": '5',
        "X-Twitter-Client": "TwitterAndroid",
        "X-Twitter-Client-Version": "10.21.0-release.0",
        "OS-Version": "28",
        "System-User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ONEPLUS A3010 Build/PKQ1.181203.001)",
        "X-Twitter-Active-User": "yes",
        "X-Guest-Token": guest_token,
        "X-Twitter-Client-DeviceID": ""
    }

    session = requests.Session()
    session.headers = twitter_header

    task1 = session.post(
        'https://api.twitter.com/1.1/onboarding/task.json',
        params={
            'flow_name': 'login',
            'api_version': '1',
            'known_device_token': '',
            'sim_country_code': 'us'
        },
        json={
            "flow_token": None,
            "input_flow_data": {
                "country_code": None,
                "flow_context": {
                    "referrer_context": {
                        "referral_details": "utm_source=google-play&utm_medium=organic",
                        "referrer_url": ""
                    },
                    "start_location": {
                        "location": "deeplink"
                    }
                },
                "requested_variant": None,
                "target_user_id": 0
            }
        }
    )

    session.headers['att'] = task1.headers.get('att')

    task2 = session.post(
        'https://api.twitter.com/1.1/onboarding/task.json',
        json={
            "flow_token": task1.json().get('flow_token'),
            "subtask_inputs": [{
                "enter_text": {
                    "suggestion_id": None,
                    "text": username,
                    "link": "next_link"
                },
                "subtask_id": "LoginEnterUserIdentifier"
            }]
        }
    )

    task3 = session.post(
        'https://api.twitter.com/1.1/onboarding/task.json',
        json={
            "flow_token": task2.json().get('flow_token'),
            "subtask_inputs": [{
                "enter_password": {
                    "password": password,
                    "link": "next_link"
                },
                "subtask_id": "LoginEnterPassword"
            }],
        }
    )

    for t3_subtask in task3.json().get('subtasks', []):
        if "open_account" in t3_subtask:
            return t3_subtask["open_account"]
        elif "enter_text" in t3_subtask:
            response_text = t3_subtask["enter_text"]["hint_text"]
            totp = pyotp.TOTP(otp_secret)
            generated_code = totp.now()
            task4resp = session.post(
                "https://api.twitter.com/1.1/onboarding/task.json",
                json={
                    "flow_token": task3.json().get("flow_token"),
                    "subtask_inputs": [
                        {
                            "enter_text": {
                                "suggestion_id": None,
                                "text": generated_code,
                                "link": "next_link",
                            },
                            "subtask_id": "LoginTwoFactorAuthChallenge",
                        }
                    ],
                }
            )
            task4 = task4resp.json()
            for t4_subtask in task4.get("subtasks", []):
                if "open_account" in t4_subtask:
                    return t4_subtask["open_account"]

    return None

if __name__ == "__main__":
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    otp_secret = os.getenv("OTP_SECRET")
    path = os.getenv("SESSION_PATH", "/app/sessions/sessions.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not username or not password:
        # parse session file
        try:
            with open(path, "r") as f:
                sessions = [json.loads(line) for line in f if line.strip()]
            # if no sessions found, exit
            if not sessions:
                print("No sessions found. Please provide username and password.")
                sys.exit(1)
            # exit with 0 status code
            print("No username or password provided. Using existing sessions.")
            sys.exit(0)
        except FileNotFoundError:
            print("Session file not found. Please provide username and password.")
            sys.exit(1)
            

    result = auth(username, password, otp_secret)
    if result is None:
        print("Authentication failed.")
        sys.exit(1)

    session_entry = {
        "oauth_token": result.get("oauth_token"),
        "oauth_token_secret": result.get("oauth_token_secret")
    }

    try:
        with open(path, "a") as f:
            f.write(json.dumps(session_entry) + "\n")
        print("Authentication successful. Session appended to", path)
    except Exception as e:
        print(f"Failed to write session information: {e}")
        sys.exit(1)