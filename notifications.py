"""Telegram notifications sent from the Flask process.

Used to ping assignees / approvers / requesters when tasks change so they
hear about updates without needing to open the Mini App.

Calls to send_*() are non-blocking: each message is posted from a daemon
thread so the request handler can return immediately.
"""

import json
import os
import threading
import urllib.error
import urllib.request


def _bot_token():
    return os.environ.get('BOT_TOKEN', '').strip()


def _webapp_url():
    return os.environ.get('WEBAPP_URL', '').strip()


_PRIORITY_UZ = {
    'Urgent': 'Shoshilinch',
    'High': 'Yuqori',
    'Normal': "O'rtacha",
    'Low': 'Past',
}

_STATUS_UZ = {
    'Not Started': 'Boshlanmagan',
    'In Progress': 'Jarayonda',
    'Pending Approval': 'Tasdiqlash kutilmoqda',
    'Completed': 'Bajarilgan',
}


def _post(payload):
    token = _bot_token()
    if not token:
        return False
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            if not body.get('ok'):
                print(f"[notify] telegram error: {body}", flush=True)
                return False
            return True
    except (urllib.error.URLError, Exception) as exc:
        print(f"[notify] failed chat_id={payload.get('chat_id')}: {exc}", flush=True)
        return False


def send_message(telegram_id, text, with_app_button=True):
    """Fire-and-forget send. Returns immediately; actual HTTP happens in a thread."""
    if not telegram_id or not _bot_token():
        return
    payload = {
        'chat_id': str(telegram_id),
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    webapp = _webapp_url()
    if with_app_button and webapp.startswith('https://'):
        payload['reply_markup'] = {
            'inline_keyboard': [[
                {'text': 'Ilovani ochish', 'web_app': {'url': webapp}}
            ]]
        }
    threading.Thread(target=_post, args=(payload,), daemon=True).start()


def _fmt_priority(p):
    return _PRIORITY_UZ.get(p, p or '')


def _fmt_status(s):
    return _STATUS_UZ.get(s, s or '')


def notify_task_assigned(assignees, task, assignor_name):
    """Notify each assignee that a new task is on their plate.

    assignees: iterable of dicts/DotDicts with .telegram_id
    task: dict-like with title, priority, deadline
    assignor_name: display name of who assigned the task
    """
    text = (
        "📋 <b>Sizga yangi vazifa biriktirildi</b>\n\n"
        f"«{task['title']}»\n"
        f"⚡ Muhimligi: <b>{_fmt_priority(task.get('priority'))}</b>\n"
        f"📅 Muddat: <b>{task.get('deadline', '—')}</b>\n"
        f"👤 Biriktirgan: {assignor_name}"
    )
    for a in assignees:
        send_message(a.get('telegram_id') if hasattr(a, 'get') else a['telegram_id'], text)


def notify_verifier_self_request(verifier, task, requester_name):
    """Notify a Head/Deputy/HeadOfUnit that a self-request is awaiting their verification."""
    text = (
        "🔍 <b>Tasdiqlash uchun yangi so'rov</b>\n\n"
        f"«{task['title']}»\n"
        f"⚡ Muhimligi: <b>{_fmt_priority(task.get('priority'))}</b>\n"
        f"📅 Muddat: <b>{task.get('deadline', '—')}</b>\n"
        f"👤 So'rovchi: {requester_name}"
    )
    send_message(verifier.get('telegram_id') if hasattr(verifier, 'get') else verifier['telegram_id'], text)


def notify_pending_approval(approver, task, assignee_name):
    """Notify the assignor / approver that a task was submitted and needs approval."""
    text = (
        "✅ <b>Vazifa tasdiqlashga yuborildi</b>\n\n"
        f"«{task['title']}»\n"
        f"👤 Bajaruvchi: {assignee_name}\n"
        f"📅 Muddat: <b>{task.get('deadline', '—')}</b>"
    )
    send_message(approver.get('telegram_id') if hasattr(approver, 'get') else approver['telegram_id'], text)


def notify_status_changed(recipient, task, new_status):
    """Generic status-change notification."""
    text = (
        "🔔 <b>Vazifa holati o'zgardi</b>\n\n"
        f"«{task['title']}»\n"
        f"Yangi holat: <b>{_fmt_status(new_status)}</b>"
    )
    send_message(recipient.get('telegram_id') if hasattr(recipient, 'get') else recipient['telegram_id'], text)
