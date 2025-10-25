from flask import Response, current_app
import requests
from src.models.app import App
from src.models.user_setup import UserSetup
from src.models.app_event import AppEvent
from src.utils.redis_session import USSDSession
from src.utils.security import encrypt_data, decrypt_data, hash_pin, check_pin, generate_random_code
import time
import json
import os
from bson.objectid import ObjectId

EASICRYPT_WALLET_API = os.getenv('EASICRYPT_WALLET_API')

def _generate_ussd_response(message, session_type="CON"):
    return Response(f"{session_type} {message}", mimetype="text/plain")

def handle_ussd_request(request):
    session_id = request.form.get("sessionId")
    service_code = request.form.get("serviceCode")
    phone_number = request.form.get("phoneNumber")
    text = request.form.get("text", "").strip()

    session = USSDSession(session_id)
    session_data = session.get()
    
    current_app.logger.info(f"USSD Request: Session={session_id}, Phone={phone_number}, Text='{text}', SessionData={session_data}")

    if not session_data:
        return _handle_initial_request(session, phone_number)
    else:
        return _handle_subsequent_request(session, phone_number, text, session_data)

def _handle_initial_request(session, phone_number):
    visible_apps = App.get_visible_apps()
    menu_items = ["1. EasiCrypt Wallet"]
    for i, app in enumerate(visible_apps):
        menu_items.append(f"{i+2}. {app['app_name']}")

    session.set({
        "phone_number": phone_number,
        "stage": "MAIN_MENU",
        "selected_app_id": None,
        "selected_app_name": None,
        "selected_app_type": None,
        "visible_apps_map": {str(i+2): str(app['_id']) for i, app in enumerate(visible_apps)}
    })
    AppEvent.log_event("ussd_session_start", phone_number=phone_number, event_type="session_start")
    return _generate_ussd_response("Welcome to EasiCrypt USSD. Select an option:\n" + "\n".join(menu_items))

def _handle_subsequent_request(session, phone_number, text, session_data):
    stage = session_data.get("stage")
    selected_app_id = session_data.get("selected_app_id")
    selected_app_name = session_data.get("selected_app_name")
    selected_app_type = session_data.get("selected_app_type")

    if text.lower() == '00':
        return _handle_initial_request(session, phone_number)

    if stage == "MAIN_MENU":
        if text == "1":
            session_data["selected_app_type"] = "wallet"
            session_data["selected_app_name"] = "EasiCrypt Wallet"
            session_data["stage"] = "WALLET_FORWARD"
            session.set(session_data)
            AppEvent.log_event("app_selection", phone_number=phone_number, app_id="EasiCrypt Wallet", metadata={"app_type": "wallet"})
            return _forward_to_external_app(EASICRYPT_WALLET_API, phone_number, "", session.session_id)
        
        elif text in session_data.get("visible_apps_map", {}):
            selected_app_id = session_data["visible_apps_map"][text]
            app = App.find_by_id(ObjectId(selected_app_id))
            if not app:
                session.delete()
                return _generate_ussd_response("Invalid app selection. Please try again.", session_type="END")

            session_data["selected_app_id"] = str(app['_id'])
            session_data["selected_app_name"] = app['app_name']
            session_data["selected_app_type"] = "defi_app"
            session_data["stage"] = "APP_HOME"
            session.set(session_data)
            AppEvent.log_event("app_selection", phone_number=phone_number, app_id=str(app['_id']), metadata={"app_type": "defi_app"})
            return _generate_ussd_response(f"You selected {app['app_name']}. Welcome! (Enter '00' to return to main menu)")
        else:
            return _generate_ussd_response("Invalid selection. Please try again.", session_type="END")

    elif selected_app_type == "wallet":
        return _forward_to_external_app(EASICRYPT_WALLET_API, phone_number, text, session.session_id)
    
    elif selected_app_type == "defi_app":
        app = App.find_by_id(ObjectId(selected_app_id))
        if not app:
            session.delete()
            return _generate_ussd_response("Selected app not found. Please try again.", session_type="END")

        user_setup = UserSetup.find_by_phone_and_app(phone_number, ObjectId(selected_app_id))

        if not user_setup:
            return _handle_app_setup(session, phone_number, text, session_data, app)
        else:
            return _handle_app_interaction(session, phone_number, text, session_data, app, user_setup)

    return _generate_ussd_response("An unexpected error occurred. Please try again later.", session_type="END")


def _handle_app_setup(session, phone_number, text, session_data, app):
    stage = session_data.get("stage")
    app_id = str(app['_id'])

    if stage == "APP_HOME":
        session_data["stage"] = "PROMPT_FOR_VERIFY_CODE"
        session.set(session_data)
        return _generate_ussd_response(f"Welcome to {app['app_name']}! It looks like you haven't set up this app yet. Please enter your verification code to proceed:")

    elif stage == "PROMPT_FOR_VERIFY_CODE":
        verify_code = text
        if not verify_code:
            return _generate_ussd_response("Verification code cannot be empty. Please enter your code:")

        verify_endpoint = app['endpoints'].get('verify_endpoint')
        if not verify_endpoint:
            return _generate_ussd_response("Verification not configured for this app. Please try again later.", session_type="END")

        start_time = time.time()
        try:
            response = requests.post(verify_endpoint, json={"code": verify_code})
            latency = (time.time() - start_time) * 1000
            AppEvent.log_event("endpoint_call", app_id=app_id, phone_number=phone_number,
                               event_type="verify_endpoint", status=response.status_code,
                               latency_ms=latency, metadata={"url": verify_endpoint, "payload": {"code": verify_code}})

            if response.status_code == 200 and response.json().get('status') == 'success':
                session_data["encrypted_code_from_verify"] = encrypt_data(verify_code)
                session_data["stage"] = "PROMPT_FOR_PIN"
                session.set(session_data)
                return _generate_ussd_response("Verification successful! Please set a 4-digit PIN for this app:")
            else:
                return _generate_ussd_response(f"Verification failed: {response.json().get('message', 'Invalid code')}. Please try again.", session_type="END")
        except requests.exceptions.RequestException as e:
            latency = (time.time() - start_time) * 1000
            AppEvent.log_event("endpoint_call", app_id=app_id, phone_number=phone_number,
                               event_type="verify_endpoint", status="failed", message=str(e),
                               latency_ms=latency, metadata={"url": verify_endpoint, "payload": {"code": verify_code}})
            current_app.logger.error(f"Error calling verify endpoint for app {app_id}: {e}")
            return _generate_ussd_response("Service temporarily unavailable. Please try again.", session_type="END")

    elif stage == "PROMPT_FOR_PIN":
        pin = text
        if not (pin.isdigit() and len(pin) == 4):
            return _generate_ussd_response("Invalid PIN. Please enter a 4-digit numeric PIN:")

        hashed_pin = hash_pin(pin)
        encrypted_code = session_data["encrypted_code_from_verify"]

        UserSetup.create(phone_number, ObjectId(app_id), encrypted_code, hashed_pin)
        AppEvent.log_event("registration", app_id=app_id, phone_number=phone_number, status="success")
        session_data["stage"] = "APP_INTERACTION_MENU"
        del session_data["encrypted_code_from_verify"]
        session.set(session_data)
        return _generate_ussd_response("PIN set and app setup complete! You can now interact with the app. (Enter '00' for options)")

    return _generate_ussd_response("An error occurred during setup. Please try again.", session_type="END")

def _handle_app_interaction(session, phone_number, text, session_data, app, user_setup):
    stage = session_data.get("stage", "APP_INTERACTION_MENU")
    app_id = str(app['_id'])
    
    menu_options_map = {
        "1": "Send Crypto",
        "2": "Check Balance",
        "3": "Change PIN"
    }
    
    off_ramp_endpoint = app['endpoints'].get('off_ramp_endpoint')
    if off_ramp_endpoint:
        menu_options_map["3"] = "Off-Ramp"
        menu_options_map["4"] = "Change PIN"

    menu_display_items = [f"{key}. {value}" for key, value in sorted(menu_options_map.items())]

    if stage == "APP_HOME" or stage == "APP_INTERACTION_MENU":
        session_data["stage"] = "APP_INTERACTION_MENU"
        session.set(session_data)
        return _generate_ussd_response(f"Welcome to {app['app_name']}. What would you like to do?\n" + "\n".join(menu_display_items) + "\n(Enter '00' to main menu)")

    elif stage == "APP_INTERACTION_MENU":
        selected_option = menu_options_map.get(text)

        if text == "1": # Send Crypto
            session_data["stage"] = "SEND_CRYPTO_AMOUNT"
            session.set(session_data)
            return _generate_ussd_response("Enter amount to send (e.g., 10.5):")
        elif text == "2": # Check Balance
            return _handle_balance_check(session, phone_number, session_data, app, user_setup)
        elif text == "3": 
            if off_ramp_endpoint and menu_options_map.get("3") == "Off-Ramp":
                session_data["stage"] = "OFF_RAMP_AMOUNT"
                session.set(session_data)
                return _generate_ussd_response("You can only off-ramp USDC. Enter amount of USDC to off-ramp (e.g., 5000.00):")
            elif menu_options_map.get("3") == "Change PIN":
                session_data["stage"] = "CHANGE_PIN_OLD"
                session.set(session_data)
                return _generate_ussd_response("Enter your current 4-digit PIN:")
            else:
                return _generate_ussd_response("Invalid option. Please select from the menu:\n" + "\n".join(menu_display_items), session_type="CON")
        elif text == "4":
            if off_ramp_endpoint and menu_options_map.get("4") == "Change PIN":
                session_data["stage"] = "CHANGE_PIN_OLD"
                session.set(session_data)
                return _generate_ussd_response("Enter your current 4-digit PIN:")
            else:
                return _generate_ussd_response("Invalid option. Please select from the menu:\n" + "\n".join(menu_display_items), session_type="CON")
        else:
            return _generate_ussd_response("Invalid option. Please select from the menu:\n" + "\n".join(menu_display_items), session_type="CON")

    elif stage == "SEND_CRYPTO_AMOUNT":
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            session_data["temp_amount"] = amount
            session_data["stage"] = "SEND_CRYPTO_TOKEN"
            session.set(session_data)
            return _generate_ussd_response(f"Amount {amount} set. Enter token symbol (ETH, DAI, USDC, LINK):")
        except ValueError:
            return _generate_ussd_response("Invalid amount. Please enter a numeric value (e.g., 10.5):")

    elif stage == "SEND_CRYPTO_TOKEN":
        token_symbol = text.upper().strip()
        supported_tokens = ["ETH", "DAI", "USDC", "LINK"]
        if token_symbol not in supported_tokens:
            return _generate_ussd_response(f"Invalid token symbol. Please enter one of: {', '.join(supported_tokens)}:")
        session_data["temp_token_symbol"] = token_symbol
        session_data["stage"] = "SEND_CRYPTO_RECIPIENT"
        session.set(session_data)
        return _generate_ussd_response(f"Token {token_symbol} set. Enter recipient phone number (if registered with this app) or wallet address:")

    elif stage == "SEND_CRYPTO_RECIPIENT":
        recipient_input = text.strip()
        if not recipient_input:
            return _generate_ussd_response("Recipient cannot be empty. Please enter recipient phone number or wallet address:")
        
        recipient_phone_number = None
        recipient_wallet_address = None
        recipient_code = None

        if recipient_input.isdigit() and 10 <= len(recipient_input) <= 15:
            recipient_user_setup = UserSetup.find_by_phone_and_app(recipient_input, ObjectId(app_id))
            if recipient_user_setup:
                recipient_phone_number = recipient_input
                recipient_code = decrypt_data(recipient_user_setup['encrypted_code'])
                session_data["temp_recipient_type"] = "phone_number"
            else:
                recipient_wallet_address = recipient_input
                session_data["temp_recipient_type"] = "wallet_address"
        else:
            recipient_wallet_address = recipient_input
            session_data["temp_recipient_type"] = "wallet_address"

        session_data["temp_recipient_phone"] = recipient_phone_number
        session_data["temp_recipient_wallet"] = recipient_wallet_address
        session_data["temp_recipient_code"] = recipient_code

        session_data["stage"] = "CONFIRM_SEND_CRYPTO"
        session.set(session_data)
        
        recipient_display = ""
        if session_data["temp_recipient_type"] == "phone_number":
            recipient_display = f"registered phone number {recipient_phone_number}"
        else:
            recipient_display = f"wallet address {recipient_wallet_address}"
            
        return _generate_ussd_response(f"Send {session_data['temp_amount']} {session_data['temp_token_symbol']} to {recipient_display}? Enter your 4-digit PIN to confirm:")
        
    elif stage == "CONFIRM_SEND_CRYPTO":
        pin = text
        if not (pin.isdigit() and len(pin) == 4):
            return _generate_ussd_response("Invalid PIN. Please enter your 4-digit numeric PIN to confirm:")
        
        if not check_pin(pin, user_setup['hashed_pin']):
            AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, status="failed", message="Incorrect PIN for send crypto")
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response("Incorrect PIN. Transaction cancelled.", session_type="END")

        send_endpoint = app['endpoints'].get('send_endpoint')
        if not send_endpoint:
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response("Send function not configured for this app. Transaction cancelled.", session_type="END")
        
        decrypted_code = decrypt_data(user_setup['encrypted_code'])
        payload = {
            "amount": session_data['temp_amount'],
            "token_symbol": session_data['temp_token_symbol'],
            "code": decrypted_code,
        }
        
        if session_data["temp_recipient_type"] == "phone_number":
            payload["recipient_code"] = session_data["temp_recipient_code"]
        else:
            payload["recipient_address"] = session_data["temp_recipient_wallet"]
            
        return _call_external_endpoint(
            app_id=app_id,
            phone_number=phone_number,
            endpoint_url=send_endpoint,
            payload=payload,
            event_type="send_crypto",
            success_message="Crypto sent successfully!",
            failure_message="Failed to send crypto. Please try again.",
            session=session,
            session_data=session_data
        )

    elif stage == "OFF_RAMP_AMOUNT":
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            session_data["temp_amount"] = amount
            session_data["stage"] = "OFF_RAMP_BANK_NAME"
            session.set(session_data)
            return _generate_ussd_response(f"Off-ramp {amount} USDC. Enter recipient Bank Name (e.g., First Bank):")
        except ValueError:
            return _generate_ussd_response("Invalid amount. Please enter a numeric value (e.g., 5000.00):")

    elif stage == "OFF_RAMP_BANK_NAME":
        bank_name = text.strip()
        if not bank_name:
            return _generate_ussd_response("Bank name cannot be empty. Please enter recipient Bank Name:")
        session_data["temp_bank_name"] = bank_name
        session_data["stage"] = "OFF_RAMP_ACCOUNT_NUMBER"
        session.set(session_data)
        return _generate_ussd_response(f"Bank name '{bank_name}' set. Enter recipient Account Number:")

    elif stage == "OFF_RAMP_ACCOUNT_NUMBER":
        account_number = text.strip()
        if not (account_number.isdigit() and len(account_number) >= 10 and len(account_number) <= 12):
            return _generate_ussd_response("Invalid account number. Please enter a numeric account number (10-12 digits):")
        session_data["temp_account_number"] = account_number
        session_data["stage"] = "CONFIRM_OFF_RAMP"
        session.set(session_data)
        return _generate_ussd_response(f"Confirm off-ramp {session_data['temp_amount']} USDC to {session_data['temp_bank_name']} - Acc No: {session_data['temp_account_number']}? Enter your 4-digit PIN to confirm:")

    elif stage == "CONFIRM_OFF_RAMP":
        pin = text
        if not (pin.isdigit() and len(pin) == 4):
            return _generate_ussd_response("Invalid PIN. Please enter your 4-digit numeric PIN to confirm:")
        
        if not check_pin(pin, user_setup['hashed_pin']):
            AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, status="failed", message="Incorrect PIN for off-ramp")
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response("Incorrect PIN. Off-ramp cancelled.", session_type="END")

        off_ramp_endpoint = app['endpoints'].get('off_ramp_endpoint')
        if not off_ramp_endpoint:
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response("Off-ramp function not configured for this app. Transaction cancelled.", session_type="END")
        
        decrypted_code = decrypt_data(user_setup['encrypted_code'])
        payload = {
            "code": decrypted_code,
            "amount": session_data['temp_amount'],
            "token_symbol": "USDC",
            "bank_name": session_data['temp_bank_name'],
            "account_number": session_data['temp_account_number']
        }
        
        return _call_external_endpoint(
            app_id=app_id,
            phone_number=phone_number,
            endpoint_url=off_ramp_endpoint,
            payload=payload,
            event_type="off_ramp",
            success_message="Off-ramp request submitted successfully!",
            failure_message="Failed to process off-ramp. Please try again.",
            session=session,
            session_data=session_data
        )

    elif stage == "CHANGE_PIN_OLD":
        old_pin = text
        if not (old_pin.isdigit() and len(old_pin) == 4):
            return _generate_ussd_response("Invalid PIN. Please enter your 4-digit current PIN:")
        
        if not check_pin(old_pin, user_setup['hashed_pin']):
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response("Incorrect current PIN. PIN change cancelled.", session_type="END")
        
        session_data["stage"] = "CHANGE_PIN_NEW"
        session.set(session_data)
        return _generate_ussd_response("Current PIN verified. Enter your new 4-digit PIN:")

    elif stage == "CHANGE_PIN_NEW":
        new_pin = text
        if not (new_pin.isdigit() and len(new_pin) == 4):
            return _generate_ussd_response("Invalid PIN. Please enter a new 4-digit numeric PIN:")
        
        # Hash and update PIN
        new_hashed_pin = hash_pin(new_pin)
        UserSetup.update_pin(str(user_setup['_id']), new_hashed_pin)
        AppEvent.log_event("pin_change", app_id=app_id, phone_number=phone_number, status="success")
        session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
        return _generate_ussd_response("Your PIN has been successfully updated!", session_type="END")

    return _generate_ussd_response("An unexpected error occurred during app interaction. Please try again.", session_type="END")

def _handle_balance_check(session, phone_number, session_data, app, user_setup):
    app_id = str(app['_id'])
    get_balance_endpoint = app['endpoints'].get('get_balance_endpoint')
    if not get_balance_endpoint:
        session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
        return _generate_ussd_response("Balance check not configured for this app.", session_type="END")

    decrypted_code = decrypt_data(user_setup['encrypted_code'])
    payload = {
        "code": decrypted_code
    }
    
    start_time = time.time()
    try:
        response = requests.post(get_balance_endpoint, json=payload) 
        latency = (time.time() - start_time) * 1000
        status_code = response.status_code
        response_json = response.json()
        
        if status_code == 200 and response_json.get('status') == 'success':
            balances = response_json.get('balances', {})
            
            if not balances:
                balance_display = "No balances found."
            else:
                balance_lines = [f"{token}: {amount:.4f}" for token, amount in balances.items()]
                balance_display = "\n".join(balance_lines)

            AppEvent.log_event("balance_check", app_id=app_id, phone_number=phone_number, status="success",
                               latency_ms=latency, metadata={"balances": balances})
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response(f"Your Balances:\n{balance_display}", session_type="END")
        else:
            AppEvent.log_event("balance_check", app_id=app_id, phone_number=phone_number, status="failed",
                               message=response_json.get('message', 'Unknown error'), latency_ms=latency)
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response(f"Failed to retrieve balance: {response_json.get('message', 'Service error')}", session_type="END")
    except requests.exceptions.RequestException as e:
        latency = (time.time() - start_time) * 1000
        AppEvent.log_event("balance_check", app_id=app_id, phone_number=phone_number, status="failed",
                           message=str(e), latency_ms=latency)
        current_app.logger.error(f"Error calling get_balance endpoint for app {app_id}: {e}")
        session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
        return _generate_ussd_response("Service temporarily unavailable. Please try again.", session_type="END")


def _forward_to_external_app(target_url, phone_number, text, session_id):
    """Forwards USSD request to an external DeFi app or EasiCrypt Wallet."""
    forward_data = {
        "sessionId": session_id,
        "phoneNumber": phone_number,
        "text": text,
    }
    start_time = time.time()
    try:
        resp = requests.post(
            target_url,
            data=forward_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        latency = (time.time() - start_time) * 1000
        current_app.logger.info(f"Forwarded to {target_url}, status: {resp.status_code}, latency: {latency:.2f}ms")
        AppEvent.log_event("external_app_forward", phone_number=phone_number, status=resp.status_code,
                           latency_ms=latency, metadata={"target_url": target_url, "request_text": text})

        return Response(resp.text, status=200, mimetype="text/plain")
    except requests.exceptions.RequestException as e:
        latency = (time.time() - start_time) * 1000
        current_app.logger.error(f"Error forwarding USSD request to {target_url}: {e}, latency: {latency:.2f}ms")
        AppEvent.log_event("external_app_forward", phone_number=phone_number, status="failed",
                           message=str(e), latency_ms=latency, metadata={"target_url": target_url, "request_text": text})
        return _generate_ussd_response("Service temporarily unavailable. Please try again.", session_type="END")

def _call_external_endpoint(app_id, phone_number, endpoint_url, payload, event_type,
                            success_message, failure_message, session, session_data):
    """Generic function to call an external API endpoint for a DeFi app."""
    start_time = time.time()
    try:
        if endpoint_url.startswith('https://') or endpoint_url.startswith('http://'):
            response = requests.post(endpoint_url, json=payload, timeout=15)
        else:
            raise ValueError("Invalid endpoint URL format")

        latency = (time.time() - start_time) * 1000
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get('status') == 'success':
            AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, event_type=event_type, status="success", latency_ms=latency, metadata={"payload": payload})
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response(success_message, session_type="END")
        else:
            AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, event_type=event_type, status="failed", message=response_json.get('message', 'Unknown error'), latency_ms=latency, metadata={"payload": payload})
            session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
            return _generate_ussd_response(f"{failure_message}: {response_json.get('message', 'Service error')}", session_type="END")
    except requests.exceptions.RequestException as e:
        latency = (time.time() - start_time) * 1000
        AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, event_type=event_type, status="failed", message=str(e), latency_ms=latency, metadata={"payload": payload})
        current_app.logger.error(f"Error calling {event_type} endpoint for app {app_id}: {e}")
        session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
        return _generate_ussd_response("Service temporarily unavailable. Please try again.", session_type="END")
    except ValueError as e:
        AppEvent.log_event("transaction", app_id=app_id, phone_number=phone_number, event_type=event_type, status="failed", message=str(e), metadata={"payload": payload})
        current_app.logger.error(f"Configuration error for {event_type} endpoint for app {app_id}: {e}")
        session.set({**session_data, "stage": "APP_INTERACTION_MENU"})
        return _generate_ussd_response(f"Configuration error: {e}", session_type="END")
    finally:
        session_data.pop("temp_amount", None)
        session_data.pop("temp_token_symbol", None)
        session_data.pop("temp_recipient_type", None)
        session_data.pop("temp_recipient_phone", None)
        session_data.pop("temp_recipient_wallet", None)
        session_data.pop("temp_recipient_code", None)
        session_data.pop("temp_bank_name", None)
        session_data.pop("temp_account_number", None)
        session.set(session_data)