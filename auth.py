import hmac
import hashlib
import json
import time
from functools import wraps
from urllib.parse import parse_qs

from flask import session, redirect, url_for, g, flash, current_app


def validate_telegram_init_data(init_data_raw, bot_token, max_age=86400):
    """Validate Telegram Mini App initData using HMAC-SHA-256.

    Returns parsed data dict (with 'user' as a dict) if valid, None otherwise.
    max_age: maximum allowed age in seconds (default 24h).
    """
    if not init_data_raw or not bot_token:
        return None

    # Parse the query string
    try:
        parsed = {}
        for part in init_data_raw.split('&'):
            if '=' not in part:
                continue
            key, value = part.split('=', 1)
            parsed[key] = value
    except Exception:
        return None

    # Extract the hash
    received_hash = parsed.pop('hash', None)
    if not received_hash:
        return None

    # Check auth_date freshness
    auth_date = parsed.get('auth_date')
    if not auth_date:
        return None
    try:
        auth_timestamp = int(auth_date)
        if time.time() - auth_timestamp > max_age:
            return None
    except (ValueError, TypeError):
        return None

    # Build data-check-string: sort by key, join with \n
    from urllib.parse import unquote
    data_check_string = '\n'.join(
        f'{k}={unquote(v)}' for k, v in sorted(parsed.items())
    )

    # Compute HMAC: secret = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode('utf-8'), hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Decode URL-encoded values and parse user JSON
    result = {}
    for k, v in parsed.items():
        result[k] = unquote(v)

    if 'user' in result:
        try:
            result['user'] = json.loads(result['user'])
        except (json.JSONDecodeError, TypeError):
            pass

    return result


def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator that restricts access to users with is_admin flag."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for('login'))
        if not g.current_user.get('is_admin'):
            flash('Administrator huquqlariga ega emassiz.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator that restricts access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.current_user is None:
                return redirect(url_for('login'))
            if g.current_user.role not in roles:
                flash('Bu sahifaga kirish huquqingiz yo\'q.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
