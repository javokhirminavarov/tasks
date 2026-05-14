"""Minimal Telegram bot: replies to /start with a button that opens the Mini App.

Runs as a separate Railway service from the same repo. Required env vars:
  BOT_TOKEN   - Telegram bot token from @BotFather
  WEBAPP_URL  - public HTTPS URL of the Flask Mini App (e.g. Railway domain)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
WEBAPP_URL = os.environ.get('WEBAPP_URL', '').strip()
API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'


def api_call(method, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{API_BASE}/{method}',
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def register_user(tg_user):
    """POST to Flask /api/bot/register. Returns one of 'new', 'inactive',
    'active', or None on failure."""
    payload = {
        'telegram_id': tg_user.get('id'),
        'username': tg_user.get('username'),
        'name': ' '.join(
            part for part in (tg_user.get('first_name'), tg_user.get('last_name')) if part
        ) or tg_user.get('username') or 'Foydalanuvchi',
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{WEBAPP_URL.rstrip("/")}/api/bot/register',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-Bot-Token': BOT_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8')).get('status')
    except Exception as exc:
        print(f'[bot] register call failed: {exc}', flush=True)
        return None


def send_active_reply(chat_id):
    api_call('sendMessage', {
        'chat_id': chat_id,
        'text': (
            "Vazifalarni boshqarish ilovasiga xush kelibsiz.\n\n"
            "Ilovani ochish uchun pastdagi tugmani bosing."
        ),
        'reply_markup': {
            'inline_keyboard': [[
                {'text': 'Ilovani ochish', 'web_app': {'url': WEBAPP_URL}}
            ]]
        },
    })


def send_pending_reply(chat_id, is_new):
    text = (
        "Siz tizimga ro'yxatdan o'tdingiz. Administrator hisobingizni "
        "faollashtirgach, /start buyrug'ini qaytadan yuboring."
        if is_new else
        "Hisobingiz hali faollashtirilmagan. Administrator bilan "
        "bog'laning va keyin /start ni qaytadan yuboring."
    )
    api_call('sendMessage', {'chat_id': chat_id, 'text': text})


def handle_update(update):
    message = update.get('message') or update.get('edited_message')
    if not message:
        return
    text = (message.get('text') or '').strip()
    chat_id = message.get('chat', {}).get('id')
    tg_user = message.get('from') or {}
    if not chat_id or not tg_user.get('id'):
        return
    if not text.startswith('/start'):
        return

    status = register_user(tg_user)
    if status == 'active':
        send_active_reply(chat_id)
    else:
        send_pending_reply(chat_id, is_new=(status == 'new'))


def poll():
    offset = None
    print(f'[bot] starting, webapp_url={WEBAPP_URL}', flush=True)
    while True:
        params = {'timeout': 30}
        if offset is not None:
            params['offset'] = offset
        url = f'{API_BASE}/getUpdates?' + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as exc:
            print(f'[bot] network error: {exc}', flush=True)
            time.sleep(5)
            continue
        except Exception as exc:
            print(f'[bot] error: {exc}', flush=True)
            time.sleep(5)
            continue

        if not payload.get('ok'):
            print(f'[bot] api error: {payload}', flush=True)
            time.sleep(5)
            continue

        for update in payload.get('result', []):
            offset = update['update_id'] + 1
            try:
                handle_update(update)
            except Exception as exc:
                print(f'[bot] handler error: {exc}', flush=True)


def main():
    if not BOT_TOKEN:
        print('[bot] BOT_TOKEN is not set', flush=True)
        sys.exit(1)
    if not WEBAPP_URL:
        print('[bot] WEBAPP_URL is not set', flush=True)
        sys.exit(1)
    if not WEBAPP_URL.startswith('https://'):
        print('[bot] WEBAPP_URL must start with https:// for Telegram Mini Apps', flush=True)
        sys.exit(1)
    poll()


if __name__ == '__main__':
    main()
