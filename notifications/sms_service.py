"""SMS service used by admin manual sends and by automated events.

Provides a provider-agnostic Twilio-style adapter and a production-safe
`send_token_sms` entrypoint for admin-triggered messages.

Design decisions:
- Read provider credentials only from environment variables.
- Prefix Indian 10-digit numbers with +91 automatically.
- Validate phone is 10 numeric digits before sending.
- Do not raise on provider errors; record results to `AdminSMSLog`.
- Background send to avoid blocking admin requests.
"""
import os
import threading
import logging
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_env(name: str) -> Optional[str]:
    return os.environ.get(name)


class _ProviderError(Exception):
    pass


class TwilioAdapter:
    def __init__(self):
        self.account_sid = _get_env('SMS_ACCOUNT_SID')
        self.auth_token = _get_env('SMS_AUTH_TOKEN')
        self.from_number = _get_env('SMS_FROM_NUMBER')
        if not (self.account_sid and self.auth_token and self.from_number):
            raise _ProviderError('Missing SMS provider credentials in env')

        try:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
            self._use_twilio_lib = True
        except Exception:
            self._client = None
            self._use_twilio_lib = False

    def send(self, to_number: str, body: str) -> dict:
        if self._use_twilio_lib and self._client:
            try:
                # If a Messaging Service SID (starts with 'MG') was supplied, use it
                if isinstance(self.from_number, str) and self.from_number.upper().startswith('MG'):
                    msg = self._client.messages.create(body=body, messaging_service_sid=self.from_number, to=to_number)
                else:
                    msg = self._client.messages.create(body=body, from_=self.from_number, to=to_number)
                return {'sid': getattr(msg, 'sid', None), 'status': getattr(msg, 'status', None)}
            except Exception as e:
                raise _ProviderError(str(e))

        try:
            import requests
        except Exception:
            raise _ProviderError('Neither twilio lib nor requests available to send SMS')

        url = f'https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json'
        # Support Messaging Service SID by posting MessagingServiceSid instead of From
        if isinstance(self.from_number, str) and self.from_number.upper().startswith('MG'):
            payload = {'MessagingServiceSid': self.from_number, 'To': to_number, 'Body': body}
        else:
            payload = {'From': self.from_number, 'To': to_number, 'Body': body}
        try:
            r = requests.post(url, data=payload, auth=(self.account_sid, self.auth_token), timeout=10)
            if r.status_code >= 400:
                raise _ProviderError(f'HTTP {r.status_code}: {r.text}')
            return r.json()
        except Exception as e:
            raise _ProviderError(str(e))


def _format_indian(phone: str) -> Optional[str]:
    """Validate and format a 10-digit Indian number to E.164 (+91XXXXXXXXXX).

    Returns formatted string or None if invalid.
    """
    if not phone:
        return None
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f'+91{digits}'
    # If caller already passed in with +91 and 12 digits, accept
    if digits.startswith('91') and len(digits) == 12:
        return f'+{digits}'
    return None


def _admin_background_send(log_obj, to_number: str, body: str):
    """Background worker that calls provider and updates AdminSMSLog. Never raises."""
    simulate = os.environ.get('SMS_SIMULATE', '').lower() in ('1','true','yes')
    try:
        provider = TwilioAdapter()
    except _ProviderError as e:
        logger.exception('SMS provider unavailable: %s', e)
        if simulate:
            # Simulate a successful send for local/dev testing
            log_obj.success = True
            log_obj.provider_id = 'SIMULATED'
            log_obj.details = f'Simulated send: {e}'
            log_obj.sent_at = timezone.now()
            log_obj.save()
            logger.info('Simulated SMS send to %s for queue %s', to_number, getattr(log_obj, 'queue_id', None))
            return
        log_obj.success = False
        log_obj.details = str(e)
        log_obj.sent_at = timezone.now()
        log_obj.save()
        return

    try:
        resp = provider.send(to_number, body)
        prov_id = None
        if isinstance(resp, dict):
            prov_id = resp.get('sid') or resp.get('message_sid') or resp.get('sid')
        log_obj.success = True
        log_obj.provider_id = prov_id
        log_obj.details = str(resp)
        log_obj.sent_at = timezone.now()
        log_obj.save()
        logger.info('Admin SMS sent to %s for queue %s', to_number, getattr(log_obj.queue_id, 'id', None))
    except Exception as e:
        logger.exception('Admin SMS send failed for %s: %s', to_number, e)
        log_obj.success = False
        log_obj.details = str(e)
        log_obj.sent_at = timezone.now()
        log_obj.save()


def send_token_sms(queue_obj, message: str, sent_by_admin_user=None):
    """Public entrypoint for sending a manual SMS tied to a queue token.

    - Validates message and phone formatting
    - Creates `AdminSMSLog` record (success=False) immediately for audit
    - Spawns background thread to call provider and update record
    - Returns the AdminSMSLog instance (not necessarily final success)

    Safety: does not raise provider errors to caller.
    """
    from notifications.models import AdminSMSLog

    # Basic validation
    if not message or not message.strip():
        raise ValueError('Message must not be empty')
    if len(message) > 160:
        raise ValueError('Message exceeds 160 characters')

    # Prefer `phone_number` on user model; fall back to legacy `phone` if present
    user = getattr(queue_obj, 'user', None)
    if not user:
        raise ValueError('Queue token has no associated user')

    # Respect opt-in if the attribute exists; otherwise assume True
    if hasattr(user, 'sms_opt_in') and not getattr(user, 'sms_opt_in'):
        raise PermissionError('User has opted out of SMS')

    # Obtain raw phone (accounts.User.phone expected to be 10-digit)
    raw_phone = getattr(user, 'phone_number', None) or getattr(user, 'phone', None)
    formatted = _format_indian(raw_phone)
    if not formatted:
        raise ValueError('Invalid or missing phone number for user')

    # Optional business rule: do not send if token is completed or cancelled
    status = getattr(queue_obj, 'status', None)
    if status in ('completed', 'cancelled'):
        raise ValueError('Cannot send SMS for completed or cancelled tokens')

    # Create audit log entry
    log = AdminSMSLog.objects.create(
        admin=sent_by_admin_user,
        queue=queue_obj,
        token_number=getattr(queue_obj, 'token_number', None),
        phone_number=formatted,
        message=message,
        success=False,
    )

    # Start background sender
    thread = threading.Thread(target=_admin_background_send, args=(log, formatted, message), daemon=True)
    thread.start()

    return log
