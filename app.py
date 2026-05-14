import os
import math
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from models import (get_user_by_id, get_user_by_telegram_id, get_user_by_telegram_id_any,
                    bootstrap_admin_from_env, register_pending_user,
                    get_other_admins, demote_other_admins,
                    get_dashboard_stats,
                    get_team_workload, get_unit_performance,
                    get_my_tasks, get_my_task_stats, get_overdue_count_for_filter,
                    get_task_by_id, get_assignable_users, get_verifiers_for_user,
                    create_task, update_task, update_task_status, delete_task,
                    get_task_comments, add_comment,
                    log_activity, get_db, init_db,
                    get_all_users, create_user, update_user, toggle_user_active,
                    get_all_units, get_unit_by_id,
                    create_unit, update_unit, get_admin_stats,
                    get_user_profile, get_user_notifications, get_notification_count,
                    get_team_workload_full, get_unit_performance_full,
                    get_report_data, get_activity_log,
                    get_unit_team_workload, get_unit_performance_for_head_of_unit,
                    get_unit_staff_list)
from auth import login_required, admin_required, role_required, validate_telegram_init_data
from translations import register_filters, status_uz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
register_filters(app)

# Ensure tables exist when the app is imported by a WSGI server (e.g. gunicorn).
with app.app_context():
    init_db()
    bootstrap_admin_from_env()


# --- Before Request / Context Processor ---

@app.before_request
def load_current_user():
    """Load current user from session into g."""
    user_id = session.get('user_id')
    if user_id:
        g.current_user = get_user_by_id(user_id)
    else:
        g.current_user = None


@app.context_processor
def inject_globals():
    """Inject current_user, is_admin, and notification_count into all templates."""
    user = g.get('current_user')
    notif_count = 0
    is_admin = False
    if user:
        notif_count = get_notification_count(user.id, user.role, user.unit_id)
        is_admin = bool(user.get('is_admin'))
    return {
        'current_user': user,
        'is_admin': is_admin,
        'notification_count': notif_count,
    }


@app.template_filter('timeago')
def timeago_filter(timestamp_str):
    """Convert a timestamp string to a relative time display."""
    if not timestamp_str:
        return ''
    try:
        dt = datetime.fromisoformat(str(timestamp_str))
    except (ValueError, TypeError):
        return str(timestamp_str)
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f'{mins}m ago'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f'{days}d ago'
    else:
        return dt.strftime('%b %d, %Y')


# --- Auth Routes ---

@app.route('/login')
def login():
    """Landing page - prompts user to open via Telegram or auto-authenticates."""
    if g.current_user:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/auth/telegram', methods=['POST'])
def auth_telegram():
    """Validate Telegram initData and create session."""
    if request.is_json:
        init_data = request.json.get('initData', '')
    else:
        init_data = request.form.get('initData', '')

    if not BOT_TOKEN:
        return jsonify({'error': 'Bot sozlanmagan'}), 500

    parsed = validate_telegram_init_data(init_data, BOT_TOKEN)
    if parsed is None:
        return jsonify({'error': 'Tasdiqlash xato yoki muddati o\'tgan'}), 401

    tg_user = parsed.get('user')
    if not tg_user or 'id' not in tg_user:
        return jsonify({'error': 'Tasdiqlashda foydalanuvchi ma\'lumotlari yo\'q'}), 401

    telegram_id = str(tg_user['id'])

    # Look up user by telegram_id
    user = get_user_by_telegram_id(telegram_id)
    if user is None:
        # Check if user exists but is inactive
        inactive_user = get_user_by_telegram_id_any(telegram_id)
        if inactive_user:
            return jsonify({'error': 'Hisobingiz o\'chirilgan. Administrator bilan bog\'laning.'}), 403
        return jsonify({'error': 'Siz tizimda ro\'yxatdan o\'tmagansiz. Administrator bilan bog\'laning.'}), 403

    session['user_id'] = user.id
    return jsonify({'success': True, 'redirect': url_for('dashboard')})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/bot/register', methods=['POST'])
def api_bot_register():
    """Called by bot.py on /start to upsert a pending user.

    Auth: requires header `X-Bot-Token` matching BOT_TOKEN. The endpoint is on
    the public URL, so the shared secret prevents anyone from spamming it.
    """
    import hmac as _hmac
    received = request.headers.get('X-Bot-Token', '')
    if not BOT_TOKEN or not _hmac.compare_digest(received, BOT_TOKEN):
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    telegram_id = str(data.get('telegram_id', '')).strip()
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400

    status = register_pending_user(
        telegram_id=telegram_id,
        telegram_username=data.get('username'),
        name=data.get('name'),
    )
    return jsonify({'status': status})


# --- Main Routes ---

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = g.current_user

    # Staff/Intern: redirect to merged tasks page (even if admin)
    if user.role in ('Staff', 'Intern'):
        return redirect(url_for('tasks_list'))

    stats = get_dashboard_stats(user)
    current_date = date.today().strftime('%A, %B %d, %Y')

    # Head/Deputy: team workload + unit performance
    team = get_team_workload() if user.role in ('Head', 'Deputy') else []
    units = get_unit_performance() if user.role in ('Head', 'Deputy') else []

    # HeadOfUnit: unit staff workload + other units summary
    unit_staff = get_unit_team_workload(user.unit_id) if user.role == 'HeadOfUnit' else []
    other_units = get_unit_performance_for_head_of_unit(user.unit_id) if user.role == 'HeadOfUnit' else []

    return render_template('dashboard.html',
                           stats=stats,
                           team_workload=team,
                           unit_performance=units,
                           unit_staff=unit_staff,
                           other_units=other_units,
                           current_date=current_date)


# --- Stub Routes (prevent url_for errors in templates) ---

@app.route('/tasks')
@login_required
def tasks_list():
    user = g.current_user

    # Head/Deputy don't have personal tasks - redirect to dashboard
    if user.role in ('Head', 'Deputy'):
        return redirect(url_for('dashboard'))

    status_filter = request.args.get('status', 'all')
    # HeadOfUnit can toggle between personal tasks and unit tasks
    view = request.args.get('view', 'unit' if user.role == 'HeadOfUnit' else 'my')
    staff_filter = request.args.get('staff', None, type=int)

    if user.role == 'HeadOfUnit' and view == 'unit':
        personal_only = False
    else:
        personal_only = user.role == 'HeadOfUnit'

    stats = get_my_task_stats(user, personal_only=personal_only)
    tasks = get_my_tasks(user, status_filter, personal_only=personal_only, staff_filter=staff_filter if view == 'unit' else None)
    overdue_count = get_overdue_count_for_filter(user)

    # Get user's unit name
    unit_name = None
    if user.unit_id:
        conn = get_db()
        row = conn.execute("SELECT name FROM units WHERE id = ?", (user.unit_id,)).fetchone()
        if row:
            unit_name = row['name']
        conn.close()

    # Check if user has active overload flag on any task (Staff/Intern/HeadOfUnit only)
    is_overloaded = False
    if user.role in ('Staff', 'Intern', 'HeadOfUnit'):
        conn = get_db()
        overload_row = conn.execute(
            """SELECT COUNT(*) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.overload_flag = 1 AND t.status != 'Completed'""",
            (user.id,)
        ).fetchone()
        is_overloaded = overload_row[0] > 0 if overload_row else False
        conn.close()

    # For Staff/Intern merged view, add dashboard-style data
    current_date = date.today().strftime('%A, %B %d, %Y') if user.role in ('Staff', 'Intern') else None

    # For HeadOfUnit unit view, get staff list for filter dropdown
    unit_staff_list = []
    staff_name = None
    if user.role == 'HeadOfUnit' and view == 'unit':
        unit_staff_list = get_unit_staff_list(user.unit_id)
        if staff_filter:
            for s in unit_staff_list:
                if s.id == staff_filter:
                    staff_name = s.name
                    break

    return render_template('tasks/my_tasks.html',
                           stats=stats,
                           tasks=tasks,
                           current_filter=status_filter,
                           overdue_count=overdue_count,
                           unit_name=unit_name,
                           is_overloaded=is_overloaded,
                           current_date=current_date,
                           current_view=view,
                           unit_staff_list=unit_staff_list,
                           staff_filter=staff_filter,
                           staff_name=staff_name)


@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    user = g.current_user

    task = get_task_by_id(task_id)
    if task is None:
        flash('Vazifa topilmadi.', 'error')
        return redirect(url_for('tasks_list'))

    # Permission check: user must be assignee, assignor, requester, or Head/Deputy
    is_assignee = user.id in task.assignee_ids
    is_assignor = user.id == task.assignor_id
    is_requester = user.id == task.requester_id
    is_head = user.role in ('Head', 'Deputy')
    is_unit_head = user.role == 'HeadOfUnit'

    # HeadOfUnit can see tasks assigned to users in their unit
    if is_unit_head and not (is_assignee or is_assignor or is_requester):
        conn = get_db()
        in_unit = conn.execute(
            """SELECT COUNT(*) FROM task_assignees ta
               JOIN users u ON ta.user_id = u.id
               WHERE ta.task_id = ? AND u.unit_id = ?""",
            (task_id, user.unit_id)
        ).fetchone()[0]
        conn.close()
        if not in_unit:
            flash('Bu vazifaga kirish huquqingiz yo\'q.', 'error')
            return redirect(url_for('tasks_list'))
    elif not (is_assignee or is_assignor or is_requester or is_head):
        flash('Bu vazifaga kirish huquqingiz yo\'q.', 'error')
        return redirect(url_for('tasks_list'))

    comments = get_task_comments(task_id)

    # Determine allowed status transitions
    can_start = is_assignee and task.status == 'Not Started'
    can_complete = is_assignee and task.status == 'In Progress'
    can_approve = (is_assignor or is_head) and task.status == 'Pending Approval'
    can_reject = (is_assignor or is_head) and task.status == 'Pending Approval'
    can_edit = is_assignor or is_head or (is_unit_head if is_unit_head else False)
    can_delete = is_assignor or is_head

    return render_template('tasks/task_detail.html',
                           task=task, comments=comments,
                           can_start=can_start, can_complete=can_complete,
                           can_approve=can_approve, can_reject=can_reject,
                           can_edit=can_edit, can_delete=can_delete)


@app.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def task_update_status(task_id):
    user = g.current_user
    task = get_task_by_id(task_id)
    if task is None:
        flash('Vazifa topilmadi.', 'error')
        return redirect(url_for('tasks_list'))

    new_status = request.form.get('status', '').strip()
    completion_note = request.form.get('completion_note', '').strip()

    valid_transitions = {
        'Not Started': ['In Progress'],
        'In Progress': ['Pending Approval'],
        'Pending Approval': ['Completed', 'In Progress'],
    }

    allowed = valid_transitions.get(task.status, [])
    if new_status not in allowed:
        flash('Holatni bunday o\'zgartirib bo\'lmaydi.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    # Permission checks
    is_assignee = user.id in task.assignee_ids
    is_assignor = user.id == task.assignor_id
    is_head = user.role in ('Head', 'Deputy')

    if new_status == 'In Progress' and task.status == 'Not Started' and not is_assignee:
        flash('Vazifani faqat bajaruvchilar boshlashi mumkin.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    if new_status == 'Pending Approval' and not is_assignee:
        flash('Tasdiqlashga faqat bajaruvchilar yuborishi mumkin.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    if new_status == 'Completed' and not (is_assignor or is_head):
        flash('Vazifani faqat biriktirgan shaxs yoki Rahbar/O\'rinbosar tasdiqlay oladi.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    if new_status == 'In Progress' and task.status == 'Pending Approval' and not (is_assignor or is_head):
        flash('Vazifani faqat biriktirgan shaxs yoki Rahbar/O\'rinbosar rad eta oladi.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    update_task_status(task_id, new_status, completion_note if new_status == 'Completed' else None)
    log_activity(user.id, f'Changed status to {new_status}', 'Task', task_id, task.title)
    flash(f'Vazifa holati "{status_uz(new_status)}" ga o\'zgartirildi.', 'success')
    return redirect(url_for('task_detail', task_id=task_id))


@app.route('/tasks/<int:task_id>/comment', methods=['POST'])
@login_required
def task_add_comment(task_id):
    user = g.current_user
    task = get_task_by_id(task_id)
    if task is None:
        flash('Vazifa topilmadi.', 'error')
        return redirect(url_for('tasks_list'))

    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        flash('Izoh bo\'sh bo\'lishi mumkin emas.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    add_comment(task_id, user.id, comment_text)
    log_activity(user.id, 'Added comment', 'Task', task_id)
    return redirect(url_for('task_detail', task_id=task_id))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def task_delete(task_id):
    user = g.current_user
    task = get_task_by_id(task_id)
    if task is None:
        flash('Vazifa topilmadi.', 'error')
        return redirect(url_for('tasks_list'))

    is_assignor = user.id == task.assignor_id
    is_head = user.role in ('Head', 'Deputy')

    if not (is_assignor or is_head):
        flash('Bu vazifani o\'chirishga ruxsatingiz yo\'q.', 'error')
        return redirect(url_for('task_detail', task_id=task_id))

    delete_task(task_id)
    log_activity(user.id, 'Deleted task', 'Task', task_id, task.title)
    flash('Vazifa muvaffaqiyatli o\'chirildi.', 'success')
    return redirect(url_for('tasks_list'))


@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def task_create():
    user = g.current_user

    # Staff/Intern/HeadOfUnit go to self-request form for their own tasks
    if user.role in ('Staff', 'Intern'):
        return redirect(url_for('self_request'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Normal')
        deadline = request.form.get('deadline', '').strip()
        assignee_ids = request.form.getlist('assignee_ids', type=int)

        errors = []
        if not title:
            errors.append('Task title is required.')
        if not deadline:
            errors.append('Deadline is required.')
        if not assignee_ids:
            errors.append('At least one assignee is required.')

        # HeadOfUnit cannot assign tasks to themselves
        if user.role == 'HeadOfUnit' and user.id in assignee_ids:
            errors.append('You cannot assign tasks to yourself. Use "Request Task" to create a task for yourself.')

        if errors:
            for e in errors:
                flash(e, 'error')
            users_list = get_assignable_users(user)
            return render_template('tasks/create_task.html',
                                   users=users_list, form=request.form)

        new_id = create_task(
            title=title, description=description, task_type='Ad-hoc',
            project_id=None, priority=priority, status='Not Started',
            requester_id=user.id, assignor_id=user.id,
            deadline=deadline, assignee_ids=assignee_ids
        )
        log_activity(user.id, 'Created task', 'Task', new_id, title)
        flash('Vazifa muvaffaqiyatli yaratildi.', 'success')
        return redirect(url_for('tasks_list'))

    # GET
    users_list = get_assignable_users(user)
    return render_template('tasks/create_task.html', users=users_list)


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def task_edit(task_id):
    user = g.current_user

    if user.role not in ('Head', 'Deputy', 'HeadOfUnit'):
        flash('Vazifalarni tahrirlashga ruxsatingiz yo\'q.', 'error')
        return redirect(url_for('tasks_list'))

    task = get_task_by_id(task_id)
    if task is None:
        flash('Vazifa topilmadi.', 'error')
        return redirect(url_for('tasks_list'))

    # HeadOfUnit can only edit tasks assigned to their unit
    if user.role == 'HeadOfUnit':
        conn = get_db()
        in_unit = conn.execute(
            """SELECT COUNT(*) FROM task_assignees ta
               JOIN users u ON ta.user_id = u.id
               WHERE ta.task_id = ? AND u.unit_id = ?""",
            (task_id, user.unit_id)
        ).fetchone()[0]
        conn.close()
        if not in_unit:
            flash('Faqat o\'z bo\'limingiz vazifalarini tahrirlashingiz mumkin.', 'error')
            return redirect(url_for('tasks_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Normal')
        deadline = request.form.get('deadline', '').strip()
        assignee_ids = request.form.getlist('assignee_ids', type=int)

        errors = []
        if not title:
            errors.append('Task title is required.')
        if not deadline:
            errors.append('Deadline is required.')
        if not assignee_ids:
            errors.append('At least one assignee is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            users_list = get_assignable_users(user)
            return render_template('tasks/create_task.html',
                                   task=task, users=users_list, form=request.form)

        update_task(
            task_id=task_id, title=title, description=description,
            task_type='Ad-hoc', project_id=None, priority=priority,
            deadline=deadline, assignee_ids=assignee_ids
        )
        log_activity(user.id, 'Updated task', 'Task', task_id, title)
        flash('Vazifa muvaffaqiyatli yangilandi.', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    # GET
    users_list = get_assignable_users(user)
    return render_template('tasks/create_task.html', task=task, users=users_list)


@app.route('/tasks/self-request', methods=['GET', 'POST'])
@login_required
def self_request():
    user = g.current_user

    # Staff/Intern/HeadOfUnit can use self-request
    if user.role not in ('Staff', 'Intern', 'HeadOfUnit'):
        return redirect(url_for('task_create'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Normal')
        deadline = request.form.get('deadline', '').strip()
        verifier_id = request.form.get('verifier_id', type=int)

        errors = []
        if not title:
            errors.append('Task title is required.')
        if not deadline:
            errors.append('Deadline is required.')
        if not verifier_id:
            errors.append('A verifier must be selected.')

        if errors:
            for e in errors:
                flash(e, 'error')
            verifiers = get_verifiers_for_user(user)
            return render_template('tasks/self_request.html',
                                   verifiers=verifiers, form=request.form)

        new_id = create_task(
            title=title, description=description, task_type='Ad-hoc',
            project_id=None, priority=priority, status='Pending Approval',
            requester_id=user.id, assignor_id=verifier_id,
            deadline=deadline, assignee_ids=[user.id]
        )
        log_activity(user.id, 'Submitted self-request', 'Task', new_id, title)
        flash('So\'rov tasdiqlash uchun yuborildi.', 'success')
        return redirect(url_for('tasks_list'))

    # GET
    verifiers = get_verifiers_for_user(user)
    return render_template('tasks/self_request.html', verifiers=verifiers)


@app.route('/api/toggle-overload', methods=['POST'])
@login_required
def toggle_overload():
    """Toggle overload flag on all active tasks assigned to the current user."""
    user = g.current_user
    conn = get_db()

    # Check current state
    current = conn.execute(
        """SELECT COUNT(*) FROM tasks t
           JOIN task_assignees ta ON t.id = ta.task_id
           WHERE ta.user_id = ? AND t.overload_flag = 1 AND t.status != 'Completed'""",
        (user.id,)
    ).fetchone()[0]

    new_flag = 0 if current > 0 else 1
    timestamp = date.today().isoformat() if new_flag else None

    conn.execute(
        """UPDATE tasks SET overload_flag = ?, overload_timestamp = ?
           WHERE id IN (
               SELECT t.id FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.status != 'Completed'
           )""",
        (new_flag, timestamp, user.id)
    )
    conn.commit()
    conn.close()

    return jsonify({'overloaded': bool(new_flag)})


@app.route('/team-workload')
@login_required
@role_required('Head', 'Deputy')
def team_workload():
    staff = get_team_workload_full()
    overloaded_count = sum(1 for s in staff if s.overload_flag)
    overdue_count = sum(1 for s in staff if s.overdue_tasks and s.overdue_tasks > 0)
    return render_template('team_workload.html',
                           staff=staff,
                           total_staff=len(staff),
                           overloaded_count=overloaded_count,
                           overdue_count=overdue_count)


@app.route('/units-performance')
@login_required
@role_required('Head', 'Deputy')
def units_performance():
    units = get_unit_performance_full()
    avg_rate = round(sum(u.completion_rate for u in units) / len(units)) if units else 0
    return render_template('units_performance.html',
                           units=units,
                           total_units=len(units),
                           avg_completion_rate=avg_rate)


@app.route('/notifications')
@login_required
def notifications():
    user = g.current_user
    items = get_user_notifications(user.id, user.role, user.unit_id)
    return render_template('notifications.html', notifications=items)


@app.route('/profile')
@login_required
def profile():
    user_profile = get_user_profile(g.current_user.id)
    return render_template('profile.html', profile=user_profile)


@app.route('/settings')
@login_required
def settings():
    user_profile = get_user_profile(g.current_user.id)
    return render_template('settings.html', profile=user_profile)


@app.route('/reports')
@login_required
@role_required('Head', 'Deputy')
def reports():
    data = get_report_data()
    return render_template('reports.html', data=data)


@app.route('/admin/activity-log')
@login_required
@admin_required
def admin_activity_log():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    entries, total = get_activity_log(limit=per_page, offset=offset)
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return render_template('admin/activity_log.html',
                           entries=entries, page=page,
                           total_pages=total_pages, total=total)


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin panel entry point - redirects to user management."""
    return redirect(url_for('admin_users'))


# --- Admin User Management ---

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    status_filter = request.args.get('filter', 'all')
    search = request.args.get('search', '').strip()
    users = get_all_users(
        status_filter=status_filter if status_filter != 'all' else None,
        search=search if search else None
    )
    units = get_all_units()
    roles = ['Head', 'Deputy', 'HeadOfUnit', 'Staff', 'Intern']
    other_admins = get_other_admins(g.current_user.id)
    return render_template('admin/users.html',
                           users=users, units=units, roles=roles,
                           current_filter=status_filter, search=search,
                           other_admins=other_admins)


@app.route('/admin/users/demote-others', methods=['POST'])
@login_required
@admin_required
def admin_demote_others():
    """Strip is_admin from every user except the currently logged-in admin.

    A safety tool: lets the bootstrap admin quickly recover if other accounts
    were accidentally promoted.
    """
    count = demote_other_admins(g.current_user.id)
    log_activity(g.current_user.id, 'Demoted other admins', 'User', None,
                 f'{count} ta foydalanuvchi')
    flash(f'{count} ta foydalanuvchidan administrator huquqi olib tashlandi.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'Staff')
    unit_id = request.form.get('unit_id', type=int)
    telegram_id = request.form.get('telegram_id', '').strip()
    phone = request.form.get('phone', '').strip()
    is_admin = request.form.get('is_admin') == '1'

    errors = []
    if not name:
        errors.append('Full name is required.')
    if not telegram_id:
        errors.append('Telegram ID is required.')
    elif not telegram_id.isdigit():
        errors.append('Telegram ID must be a number.')
    if telegram_id and get_user_by_telegram_id_any(telegram_id):
        errors.append('A user with this Telegram ID already exists.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('admin_users'))

    new_id = create_user(name=name, role=role, telegram_id=telegram_id,
                         unit_id=unit_id, phone=phone, is_admin=is_admin)
    log_activity(g.current_user.id, 'Created user', 'User', new_id, name)
    flash(f'"{name}" foydalanuvchisi muvaffaqiyatli yaratildi.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'Staff')
    unit_id = request.form.get('unit_id', type=int)
    telegram_id = request.form.get('telegram_id', '').strip()
    phone = request.form.get('phone', '').strip()
    is_admin = request.form.get('is_admin') == '1'

    if not name:
        flash('To\'liq ism kiritilishi shart.', 'error')
        return redirect(url_for('admin_users'))

    # Check telegram_id uniqueness if changed
    if telegram_id:
        existing = get_user_by_telegram_id_any(telegram_id)
        if existing and existing.id != user_id:
            flash('Bu Telegram ID bilan foydalanuvchi allaqachon mavjud.', 'error')
            return redirect(url_for('admin_users'))

    update_user(user_id, name, role, unit_id,
                telegram_id=telegram_id if telegram_id else None,
                phone=phone, is_admin=is_admin)
    log_activity(g.current_user.id, 'Updated user', 'User', user_id, name)
    flash(f'"{name}" foydalanuvchisi muvaffaqiyatli yangilandi.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/api/admin/toggle-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_user(user_id):
    new_active = toggle_user_active(user_id)
    if new_active is None:
        return jsonify({'error': 'User not found'}), 404
    log_activity(g.current_user.id,
                 'Activated user' if new_active else 'Deactivated user',
                 'User', user_id)
    return jsonify({'active': bool(new_active)})


# --- Admin Unit Management ---

@app.route('/admin/units')
@login_required
@admin_required
def admin_units():
    units = get_all_units()
    stats = get_admin_stats()
    # Get HeadOfUnit users for assigning heads
    all_users = get_all_users()
    return render_template('admin/units.html',
                           units=units, stats=stats, all_users=all_users)


@app.route('/admin/units/create', methods=['POST'])
@login_required
@admin_required
def admin_create_unit():
    name = request.form.get('name', '').strip()
    head_user_id = request.form.get('head_user_id', type=int)

    if not name:
        flash('Bo\'lim nomi kiritilishi shart.', 'error')
        return redirect(url_for('admin_units'))

    new_id = create_unit(name, head_user_id)
    log_activity(g.current_user.id, 'Created unit', 'Unit', new_id, name)
    flash(f'"{name}" bo\'limi muvaffaqiyatli yaratildi.', 'success')
    return redirect(url_for('admin_units'))


@app.route('/admin/units/<int:unit_id>/edit', methods=['POST'])
@login_required
@admin_required
def admin_edit_unit(unit_id):
    name = request.form.get('name', '').strip()
    head_user_id = request.form.get('head_user_id', type=int)

    if not name:
        flash('Bo\'lim nomi kiritilishi shart.', 'error')
        return redirect(url_for('admin_units'))

    update_unit(unit_id, name, head_user_id)
    log_activity(g.current_user.id, 'Updated unit', 'Unit', unit_id, name)
    flash(f'"{name}" bo\'limi muvaffaqiyatli yangilandi.', 'success')
    return redirect(url_for('admin_units'))


# --- App Startup ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
