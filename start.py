"""Single-process launcher: runs gunicorn (web) and bot.py (Telegram bot)
in one Railway service. Forwards signals; exits if either child dies."""

import os
import signal
import subprocess
import sys
import time


def main():
    port = os.environ.get('PORT', '8080')

    web = subprocess.Popen([
        'gunicorn', 'app:app',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '1',
        '--timeout', '60',
    ])

    bot_enabled = bool(os.environ.get('BOT_TOKEN')) and bool(os.environ.get('WEBAPP_URL'))
    bot = None
    if bot_enabled:
        bot = subprocess.Popen([sys.executable, '-u', 'bot.py'])
    else:
        print('[start] BOT_TOKEN or WEBAPP_URL not set; running web only', flush=True)

    children = [c for c in (web, bot) if c is not None]

    def forward(signum, _frame):
        for c in children:
            if c.poll() is None:
                c.send_signal(signum)

    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)

    try:
        while True:
            for c in children:
                rc = c.poll()
                if rc is not None:
                    print(f'[start] child pid={c.pid} exited rc={rc}; shutting down', flush=True)
                    for other in children:
                        if other is not c and other.poll() is None:
                            other.terminate()
                    for other in children:
                        try:
                            other.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            other.kill()
                    sys.exit(rc or 1)
            time.sleep(2)
    except KeyboardInterrupt:
        forward(signal.SIGTERM, None)
        for c in children:
            c.wait()


if __name__ == '__main__':
    main()
