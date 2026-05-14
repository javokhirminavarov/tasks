import sqlite3
import os
from datetime import date, timedelta

DATABASE = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db'),
)


def get_db():
    """Get a database connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            head_user_id INTEGER,
            FOREIGN KEY (head_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            unit_id INTEGER,
            telegram_id TEXT NOT NULL UNIQUE,
            phone TEXT,
            is_admin BOOLEAN DEFAULT 0,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (unit_id) REFERENCES units(id)
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Active',
            deadline DATE,
            created_by INTEGER NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL,
            project_id INTEGER,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            requester_id INTEGER NOT NULL,
            assignor_id INTEGER NOT NULL,
            deadline DATE NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_date TIMESTAMP,
            completion_note TEXT,
            overload_flag BOOLEAN DEFAULT 0,
            overload_timestamp TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (requester_id) REFERENCES users(id),
            FOREIGN KEY (assignor_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS task_assignees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment_text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row):
    """Convert a sqlite3.Row to a dict for dot-notation access via Jinja."""
    if row is None:
        return None
    return dict(row)


class DotDict(dict):
    """Dict subclass that allows attribute access (for Jinja2 dot notation)."""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def _to_dotdict(row):
    """Convert a sqlite3.Row to a DotDict."""
    if row is None:
        return None
    return DotDict(dict(row))


def get_user_by_id(user_id):
    """Return a user as DotDict by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _to_dotdict(row)


def get_user_by_telegram_id(telegram_id):
    """Return a user as DotDict by telegram_id."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ? AND active = 1",
        (str(telegram_id),)
    ).fetchone()
    conn.close()
    return _to_dotdict(row)


def get_dashboard_stats(user):
    """Return role-scoped dashboard statistics."""
    conn = get_db()
    today = date.today().isoformat()

    if user.role in ('Head', 'Deputy'):
        # All tasks
        active_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('Not Started', 'In Progress', 'Pending Approval')"
        ).fetchone()[0]
        completed_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'Completed'"
        ).fetchone()[0]
        active_projects = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE status = 'Active'"
        ).fetchone()[0]
        deadlines_today = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deadline = ? AND status != 'Completed'", (today,)
        ).fetchone()[0]
    elif user.role == 'HeadOfUnit':
        # Tasks assigned to users in their unit
        active_tasks = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               JOIN users u ON ta.user_id = u.id
               WHERE u.unit_id = ? AND t.status IN ('Not Started', 'In Progress', 'Pending Approval')""",
            (user.unit_id,)
        ).fetchone()[0]
        completed_tasks = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               JOIN users u ON ta.user_id = u.id
               WHERE u.unit_id = ? AND t.status = 'Completed'""",
            (user.unit_id,)
        ).fetchone()[0]
        active_projects = conn.execute(
            """SELECT COUNT(DISTINCT p.id) FROM projects p
               JOIN tasks t ON t.project_id = p.id
               JOIN task_assignees ta ON t.id = ta.task_id
               JOIN users u ON ta.user_id = u.id
               WHERE u.unit_id = ? AND p.status = 'Active'""",
            (user.unit_id,)
        ).fetchone()[0]
        deadlines_today = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               JOIN users u ON ta.user_id = u.id
               WHERE u.unit_id = ? AND t.deadline = ? AND t.status != 'Completed'""",
            (user.unit_id, today)
        ).fetchone()[0]
    else:
        # Staff/Intern: own tasks only
        active_tasks = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.status IN ('Not Started', 'In Progress', 'Pending Approval')""",
            (user.id,)
        ).fetchone()[0]
        completed_tasks = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.status = 'Completed'""",
            (user.id,)
        ).fetchone()[0]
        active_projects = conn.execute(
            """SELECT COUNT(DISTINCT p.id) FROM projects p
               JOIN tasks t ON t.project_id = p.id
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND p.status = 'Active'""",
            (user.id,)
        ).fetchone()[0]
        deadlines_today = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.deadline = ? AND t.status != 'Completed'""",
            (user.id, today)
        ).fetchone()[0]

    conn.close()
    return DotDict(
        active_tasks=active_tasks,
        active_projects=active_projects,
        completed_tasks=completed_tasks,
        deadlines_today=deadlines_today
    )


def get_team_workload():
    """Return staff list with task counts for Head/Deputy dashboard."""
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.name, un.name as unit_name,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as task_count,
               MAX(t.overload_flag) as overload_flag
        FROM users u
        LEFT JOIN units un ON u.unit_id = un.id
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        WHERE u.role IN ('Staff', 'Intern', 'HeadOfUnit') AND u.active = 1
        GROUP BY u.id
        ORDER BY task_count DESC
    """).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_unit_performance():
    """Return unit performance stats for Head/Deputy dashboard."""
    conn = get_db()
    rows = conn.execute("""
        SELECT un.id, un.name,
               COUNT(DISTINCT t.id) as total_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks
        FROM units un
        LEFT JOIN users u ON u.unit_id = un.id
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        GROUP BY un.id
        ORDER BY un.name
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = DotDict(dict(r))
        d.completion_rate = round((d.completed_tasks / d.total_tasks * 100) if d.total_tasks > 0 else 0)
        result.append(d)
    return result


def get_my_task_stats(user, personal_only=False):
    """Return task stats for the current user: active, overdue, pending, completed, urgent_soon.

    If personal_only=True, HeadOfUnit sees only their personally assigned tasks.
    """
    conn = get_db()
    today = date.today().isoformat()
    urgent_cutoff = (date.today() + timedelta(days=3)).isoformat()

    if user.role in ('Head', 'Deputy'):
        # See all tasks
        where_clause = "1=1"
        params_base = ()
    elif user.role == 'HeadOfUnit' and not personal_only:
        where_clause = """t.id IN (
            SELECT ta2.task_id FROM task_assignees ta2
            JOIN users u2 ON ta2.user_id = u2.id
            WHERE u2.unit_id = ?)"""
        params_base = (user.unit_id,)
    else:
        # Staff/Intern or HeadOfUnit personal: own tasks
        where_clause = "t.id IN (SELECT ta2.task_id FROM task_assignees ta2 WHERE ta2.user_id = ?)"
        params_base = (user.id,)

    active = conn.execute(
        f"""SELECT COUNT(*) FROM tasks t
            WHERE {where_clause}
            AND t.status IN ('Not Started', 'In Progress', 'Pending Approval')""",
        params_base
    ).fetchone()[0]

    overdue = conn.execute(
        f"""SELECT COUNT(*) FROM tasks t
            WHERE {where_clause}
            AND t.deadline < ? AND t.status != 'Completed'""",
        params_base + (today,)
    ).fetchone()[0]

    pending = conn.execute(
        f"""SELECT COUNT(*) FROM tasks t
            WHERE {where_clause}
            AND t.status = 'Pending Approval'""",
        params_base
    ).fetchone()[0]

    completed = conn.execute(
        f"""SELECT COUNT(*) FROM tasks t
            WHERE {where_clause}
            AND t.status = 'Completed'""",
        params_base
    ).fetchone()[0]

    urgent_soon = conn.execute(
        f"""SELECT COUNT(*) FROM tasks t
            WHERE {where_clause}
            AND t.deadline <= ? AND t.deadline >= ? AND t.status != 'Completed'""",
        params_base + (urgent_cutoff, today)
    ).fetchone()[0]

    conn.close()
    return DotDict(
        active=active, overdue=overdue, pending=pending,
        completed=completed, urgent_soon=urgent_soon
    )


def get_my_tasks(user, status_filter=None, personal_only=False, staff_filter=None):
    """Return tasks visible to the user, optionally filtered by status.

    status_filter can be: None/'all', 'Not Started', 'In Progress',
    'Overdue', 'Pending Approval', 'Completed'.
    If personal_only=True, HeadOfUnit sees only their personally assigned tasks.
    If staff_filter is set (user_id), only show tasks assigned to that specific user.
    """
    conn = get_db()
    today = date.today().isoformat()

    if staff_filter and user.role == 'HeadOfUnit':
        # Filter to a specific staff member's tasks within the unit
        role_clause = """t.id IN (
            SELECT ta2.task_id FROM task_assignees ta2
            WHERE ta2.user_id = ?)"""
        role_params = (staff_filter,)
    elif user.role in ('Head', 'Deputy'):
        role_clause = "1=1"
        role_params = ()
    elif user.role == 'HeadOfUnit' and not personal_only:
        role_clause = """t.id IN (
            SELECT ta2.task_id FROM task_assignees ta2
            JOIN users u2 ON ta2.user_id = u2.id
            WHERE u2.unit_id = ?)"""
        role_params = (user.unit_id,)
    else:
        role_clause = "t.id IN (SELECT ta2.task_id FROM task_assignees ta2 WHERE ta2.user_id = ?)"
        role_params = (user.id,)

    # Status filtering
    if status_filter == 'Overdue':
        status_clause = "t.deadline < ? AND t.status != 'Completed'"
        status_params = (today,)
    elif status_filter and status_filter != 'all':
        status_clause = "t.status = ?"
        status_params = (status_filter,)
    else:
        status_clause = "1=1"
        status_params = ()

    rows = conn.execute(
        f"""SELECT t.*,
                   assignor.name as assignor_name,
                   p.name as project_name,
                   un.name as unit_name
            FROM tasks t
            LEFT JOIN users assignor ON t.assignor_id = assignor.id
            LEFT JOIN projects p ON t.project_id = p.id
            LEFT JOIN task_assignees ta ON t.id = ta.task_id
            LEFT JOIN users assigned_user ON ta.user_id = assigned_user.id
            LEFT JOIN units un ON assigned_user.unit_id = un.id
            WHERE {role_clause} AND {status_clause}
            GROUP BY t.id
            ORDER BY
                CASE t.priority
                    WHEN 'Urgent' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Normal' THEN 3
                    WHEN 'Low' THEN 4
                END,
                t.deadline ASC""",
        role_params + status_params
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        task = DotDict(dict(r))
        # Compute deadline display
        if task.status == 'Completed':
            task.deadline_text = 'Done'
            task.deadline_urgency = 'done'
        elif task.deadline:
            deadline_date = date.fromisoformat(task.deadline)
            days_left = (deadline_date - date.today()).days
            if days_left < 0:
                task.deadline_text = f"Overdue by {abs(days_left)}d"
                task.deadline_urgency = 'overdue'
            elif days_left == 0:
                task.deadline_text = "Today"
                task.deadline_urgency = 'today'
            elif days_left == 1:
                task.deadline_text = "Tomorrow"
                task.deadline_urgency = 'soon'
            elif days_left <= 3:
                task.deadline_text = f"In {days_left} days"
                task.deadline_urgency = 'soon'
            else:
                task.deadline_text = deadline_date.strftime('%b %d')
                task.deadline_urgency = 'normal'
        else:
            task.deadline_text = 'No deadline'
            task.deadline_urgency = 'normal'
        result.append(task)
    return result


def get_overdue_count_for_filter(user):
    """Return count of overdue tasks for showing in the filter badge."""
    conn = get_db()
    today = date.today().isoformat()

    if user.role in ('Head', 'Deputy'):
        count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE deadline < ? AND status != 'Completed'",
            (today,)
        ).fetchone()[0]
    elif user.role == 'HeadOfUnit':
        count = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               JOIN users u ON ta.user_id = u.id
               WHERE u.unit_id = ? AND t.deadline < ? AND t.status != 'Completed'""",
            (user.unit_id, today)
        ).fetchone()[0]
    else:
        count = conn.execute(
            """SELECT COUNT(DISTINCT t.id) FROM tasks t
               JOIN task_assignees ta ON t.id = ta.task_id
               WHERE ta.user_id = ? AND t.deadline < ? AND t.status != 'Completed'""",
            (user.id, today)
        ).fetchone()[0]
    conn.close()
    return count


def get_task_by_id(task_id):
    """Return a task as DotDict with its assignee list, assignee_ids, and related names."""
    conn = get_db()
    row = conn.execute(
        """SELECT t.*, assignor.name as assignor_name, requester.name as requester_name
           FROM tasks t
           LEFT JOIN users assignor ON t.assignor_id = assignor.id
           LEFT JOIN users requester ON t.requester_id = requester.id
           WHERE t.id = ?""",
        (task_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return None
    task = DotDict(dict(row))

    assignees = conn.execute(
        """SELECT u.id, u.name, u.role, un.name as unit_name FROM users u
           LEFT JOIN units un ON u.unit_id = un.id
           JOIN task_assignees ta ON u.id = ta.user_id
           WHERE ta.task_id = ?""",
        (task_id,)
    ).fetchall()
    task.assignees = [DotDict(dict(a)) for a in assignees]
    task.assignee_ids = [a['id'] for a in assignees]

    # Compute deadline info
    if task.status == 'Completed':
        task.deadline_text = 'Completed'
        task.deadline_urgency = 'done'
    elif task.deadline:
        deadline_date = date.fromisoformat(task.deadline)
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            task.deadline_text = f"Overdue by {abs(days_left)} day{'s' if abs(days_left) != 1 else ''}"
            task.deadline_urgency = 'overdue'
        elif days_left == 0:
            task.deadline_text = "Due today"
            task.deadline_urgency = 'today'
        elif days_left == 1:
            task.deadline_text = "Due tomorrow"
            task.deadline_urgency = 'soon'
        elif days_left <= 3:
            task.deadline_text = f"Due in {days_left} days"
            task.deadline_urgency = 'soon'
        else:
            task.deadline_text = deadline_date.strftime('%B %d, %Y')
            task.deadline_urgency = 'normal'
    else:
        task.deadline_text = 'No deadline'
        task.deadline_urgency = 'normal'

    conn.close()
    return task


def get_assignable_users(current_user):
    """Return users that can be assigned tasks by the current user.

    Head/Deputy see all non-Admin active users.
    HeadOfUnit sees only their unit's Staff/Intern (cannot assign to themselves).
    """
    conn = get_db()
    if current_user.role in ('Head', 'Deputy'):
        rows = conn.execute(
            """SELECT u.id, u.name, u.role, un.name as unit_name
               FROM users u LEFT JOIN units un ON u.unit_id = un.id
               WHERE u.role != 'Admin' AND u.active = 1
               ORDER BY un.name, u.name"""
        ).fetchall()
    else:
        # HeadOfUnit: only Staff/Intern in their unit (exclude themselves)
        rows = conn.execute(
            """SELECT u.id, u.name, u.role, un.name as unit_name
               FROM users u LEFT JOIN units un ON u.unit_id = un.id
               WHERE u.unit_id = ? AND u.role IN ('Staff', 'Intern') AND u.active = 1
               ORDER BY u.name""",
            (current_user.unit_id,)
        ).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_verifiers_for_user(user):
    """Return potential verifiers for self-request.

    Staff/Intern: Head, Deputy, and their HeadOfUnit.
    HeadOfUnit: Head and Deputy only (cannot verify their own tasks).
    """
    conn = get_db()
    if user.role == 'HeadOfUnit':
        # HeadOfUnit can only be verified by Head/Deputy
        rows = conn.execute(
            """SELECT u.id, u.name, u.role FROM users u
               WHERE u.active = 1 AND u.role IN ('Head', 'Deputy')
               ORDER BY
                   CASE u.role WHEN 'Head' THEN 1 WHEN 'Deputy' THEN 2 END,
                   u.name"""
        ).fetchall()
    else:
        # Staff/Intern: Head, Deputy, and their HeadOfUnit
        rows = conn.execute(
            """SELECT u.id, u.name, u.role FROM users u
               WHERE u.active = 1
               AND (u.role IN ('Head', 'Deputy')
                    OR (u.role = 'HeadOfUnit' AND u.unit_id = ?))
               ORDER BY
                   CASE u.role WHEN 'Head' THEN 1 WHEN 'Deputy' THEN 2 WHEN 'HeadOfUnit' THEN 3 END,
                   u.name""",
            (user.unit_id,)
        ).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def create_task(title, description, task_type, project_id, priority, status,
                requester_id, assignor_id, deadline, assignee_ids):
    """Insert a new task and its assignees. Returns the new task ID."""
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO tasks (title, description, type, project_id, priority, status,
                              requester_id, assignor_id, deadline)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, description, task_type, project_id or None, priority, status,
         requester_id, assignor_id, deadline)
    )
    task_id = cursor.lastrowid
    for uid in assignee_ids:
        conn.execute(
            "INSERT INTO task_assignees (task_id, user_id) VALUES (?, ?)",
            (task_id, uid)
        )
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id, title, description, task_type, project_id, priority,
                deadline, assignee_ids):
    """Update an existing task and replace its assignees."""
    conn = get_db()
    conn.execute(
        """UPDATE tasks SET title=?, description=?, type=?, project_id=?,
                            priority=?, deadline=?
           WHERE id=?""",
        (title, description, task_type, project_id or None, priority, deadline, task_id)
    )
    conn.execute("DELETE FROM task_assignees WHERE task_id = ?", (task_id,))
    for uid in assignee_ids:
        conn.execute(
            "INSERT INTO task_assignees (task_id, user_id) VALUES (?, ?)",
            (task_id, uid)
        )
    conn.commit()
    conn.close()


def update_task_status(task_id, new_status, completion_note=None):
    """Update a task's status. Set completed_date if completing."""
    conn = get_db()
    if new_status == 'Completed':
        conn.execute(
            """UPDATE tasks SET status=?, completed_date=CURRENT_TIMESTAMP, completion_note=?
               WHERE id=?""",
            (new_status, completion_note, task_id)
        )
    else:
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    """Delete a task and its assignees and comments."""
    conn = get_db()
    conn.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM task_assignees WHERE task_id = ?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_task_comments(task_id):
    """Return all comments for a task with user info, ordered by timestamp."""
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, u.name as user_name, u.role as user_role
           FROM comments c
           JOIN users u ON c.user_id = u.id
           WHERE c.task_id = ?
           ORDER BY c.timestamp ASC""",
        (task_id,)
    ).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def add_comment(task_id, user_id, comment_text):
    """Add a comment to a task. Returns the new comment ID."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO comments (task_id, user_id, comment_text) VALUES (?, ?, ?)",
        (task_id, user_id, comment_text)
    )
    comment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return comment_id


def log_activity(user_id, action, entity_type=None, entity_id=None, details=None):
    """Insert a row into the activity_log table."""
    conn = get_db()
    conn.execute(
        """INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, action, entity_type, entity_id, details)
    )
    conn.commit()
    conn.close()


# --- Admin Functions ---

def get_all_users(status_filter=None, search=None):
    """Return all users with their unit names, optionally filtered."""
    conn = get_db()
    query = """SELECT u.*, un.name as unit_name
               FROM users u LEFT JOIN units un ON u.unit_id = un.id
               WHERE 1=1"""
    params = []

    if status_filter == 'active':
        query += " AND u.active = 1"
    elif status_filter == 'inactive':
        query += " AND u.active = 0"

    if search:
        query += " AND (u.name LIKE ? OR u.role LIKE ? OR un.name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY u.active DESC, u.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def create_user(name, role, telegram_id, unit_id=None, phone=None, is_admin=False):
    """Create a new user. Returns the new user ID."""
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO users (name, role, unit_id, telegram_id, phone, is_admin)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, role, unit_id or None, str(telegram_id), phone or None, 1 if is_admin else 0)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def update_user(user_id, name, role, unit_id=None, telegram_id=None, phone=None, is_admin=None):
    """Update an existing user's details."""
    conn = get_db()
    fields = ["name=?", "role=?", "unit_id=?"]
    params = [name, role, unit_id or None]

    if telegram_id is not None:
        fields.append("telegram_id=?")
        params.append(str(telegram_id))

    if phone is not None:
        fields.append("phone=?")
        params.append(phone or None)

    if is_admin is not None:
        fields.append("is_admin=?")
        params.append(1 if is_admin else 0)

    params.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()


def toggle_user_active(user_id):
    """Toggle a user's active status. Returns the new active state."""
    conn = get_db()
    row = conn.execute("SELECT active FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    new_active = 0 if row['active'] else 1
    conn.execute("UPDATE users SET active = ? WHERE id = ?", (new_active, user_id))
    conn.commit()
    conn.close()
    return new_active


def get_user_by_telegram_id_any(telegram_id):
    """Return a user by telegram_id regardless of active status (for auth error messages)."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (str(telegram_id),)
    ).fetchone()
    conn.close()
    return _to_dotdict(row)


def get_all_units():
    """Return all units with head user info and member count."""
    conn = get_db()
    rows = conn.execute("""
        SELECT un.id, un.name, un.head_user_id,
               h.name as head_name, h.active as head_active,
               COUNT(DISTINCT u.id) as member_count
        FROM units un
        LEFT JOIN users h ON un.head_user_id = h.id
        LEFT JOIN users u ON u.unit_id = un.id AND u.active = 1
        GROUP BY un.id
        ORDER BY un.name
    """).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_unit_by_id(unit_id):
    """Return a unit by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM units WHERE id = ?", (unit_id,)).fetchone()
    conn.close()
    return _to_dotdict(row)


def create_unit(name, head_user_id=None):
    """Create a new unit. Returns the new unit ID."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO units (name, head_user_id) VALUES (?, ?)",
        (name, head_user_id or None)
    )
    unit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return unit_id


def update_unit(unit_id, name, head_user_id=None):
    """Update an existing unit."""
    conn = get_db()
    conn.execute(
        "UPDATE units SET name=?, head_user_id=? WHERE id=?",
        (name, head_user_id or None, unit_id)
    )
    conn.commit()
    conn.close()


def get_admin_stats():
    """Return admin dashboard summary stats."""
    conn = get_db()
    total_units = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE active = 1").fetchone()[0]
    conn.close()
    return DotDict(total_units=total_units, total_users=total_users)



# --- New Model Functions ---

def get_user_profile(user_id):
    """Return user profile with unit name."""
    conn = get_db()
    row = conn.execute(
        """SELECT u.*, un.name as unit_name
           FROM users u LEFT JOIN units un ON u.unit_id = un.id
           WHERE u.id = ?""",
        (user_id,)
    ).fetchone()
    conn.close()
    return _to_dotdict(row)


def get_user_notifications(user_id, role, unit_id):
    """Return role-scoped activity log entries as notifications."""
    conn = get_db()

    if role in ('Head', 'Deputy'):
        rows = conn.execute(
            """SELECT al.*, u.name as user_name
               FROM activity_log al
               JOIN users u ON al.user_id = u.id
               ORDER BY al.timestamp DESC
               LIMIT 50"""
        ).fetchall()
    elif role == 'HeadOfUnit':
        rows = conn.execute(
            """SELECT al.*, u.name as user_name
               FROM activity_log al
               JOIN users u ON al.user_id = u.id
               WHERE u.unit_id = ? OR al.user_id = ?
               ORDER BY al.timestamp DESC
               LIMIT 50""",
            (unit_id, user_id)
        ).fetchall()
    else:
        # Staff/Intern: own task activity
        rows = conn.execute(
            """SELECT al.*, u.name as user_name
               FROM activity_log al
               JOIN users u ON al.user_id = u.id
               WHERE al.entity_type = 'Task'
                 AND al.entity_id IN (
                     SELECT ta.task_id FROM task_assignees ta WHERE ta.user_id = ?
                 )
               ORDER BY al.timestamp DESC
               LIMIT 50""",
            (user_id,)
        ).fetchall()

    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_notification_count(user_id, role, unit_id):
    """Return count of recent activity (last 24h, not by current user)."""
    conn = get_db()

    if role in ('Head', 'Deputy'):
        count = conn.execute(
            """SELECT COUNT(*) FROM activity_log
               WHERE user_id != ? AND timestamp >= datetime('now', '-1 day')""",
            (user_id,)
        ).fetchone()[0]
    elif role == 'HeadOfUnit':
        count = conn.execute(
            """SELECT COUNT(*) FROM activity_log al
               JOIN users u ON al.user_id = u.id
               WHERE al.user_id != ? AND (u.unit_id = ? OR al.user_id = ?)
                 AND al.timestamp >= datetime('now', '-1 day')""",
            (user_id, unit_id, user_id)
        ).fetchone()[0]
    else:
        count = conn.execute(
            """SELECT COUNT(*) FROM activity_log al
               WHERE al.user_id != ?
                 AND al.entity_type = 'Task'
                 AND al.entity_id IN (
                     SELECT ta.task_id FROM task_assignees ta WHERE ta.user_id = ?
                 )
                 AND al.timestamp >= datetime('now', '-1 day')""",
            (user_id, user_id)
        ).fetchone()[0]

    conn.close()
    return count


def get_team_workload_full():
    """Return enhanced team workload for the full page."""
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT u.id, u.name, u.role, un.name as unit_name,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as active_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks,
               COUNT(DISTINCT CASE WHEN t.deadline < ? AND t.status != 'Completed' THEN t.id END) as overdue_tasks,
               COUNT(DISTINCT t.id) as total_tasks,
               MAX(t.overload_flag) as overload_flag
        FROM users u
        LEFT JOIN units un ON u.unit_id = un.id
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        WHERE u.role IN ('Staff', 'Intern', 'HeadOfUnit') AND u.active = 1
        GROUP BY u.id
        ORDER BY active_tasks DESC
    """, (today,)).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_unit_performance_full():
    """Return enhanced unit performance for the full page."""
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT un.id, un.name,
               h.name as head_name,
               COUNT(DISTINCT u.id) as member_count,
               COUNT(DISTINCT t.id) as total_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as active_tasks,
               COUNT(DISTINCT CASE WHEN t.deadline < ? AND t.status != 'Completed' THEN t.id END) as overdue_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Not Started' THEN t.id END) as not_started_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'In Progress' THEN t.id END) as in_progress_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Pending Approval' THEN t.id END) as pending_tasks
        FROM units un
        LEFT JOIN users h ON un.head_user_id = h.id
        LEFT JOIN users u ON u.unit_id = un.id AND u.active = 1
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        GROUP BY un.id
        ORDER BY un.name
    """, (today,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = DotDict(dict(r))
        d.completion_rate = round((d.completed_tasks / d.total_tasks * 100) if d.total_tasks > 0 else 0)
        result.append(d)
    return result


def get_report_data():
    """Return comprehensive report data for the reports page."""
    conn = get_db()
    today = date.today().isoformat()

    # Tasks by status
    by_status = conn.execute(
        """SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY
           CASE status WHEN 'Not Started' THEN 1 WHEN 'In Progress' THEN 2
                       WHEN 'Pending Approval' THEN 3 WHEN 'Completed' THEN 4 END"""
    ).fetchall()

    # Tasks by priority
    by_priority = conn.execute(
        """SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority ORDER BY
           CASE priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2
                         WHEN 'Normal' THEN 3 WHEN 'Low' THEN 4 END"""
    ).fetchall()

    # Tasks by user
    by_user = conn.execute(
        """SELECT u.name, u.role, un.name as unit_name,
                  COUNT(DISTINCT t.id) as total,
                  COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed,
                  COUNT(DISTINCT CASE WHEN t.deadline < ? AND t.status != 'Completed' THEN t.id END) as overdue
           FROM users u
           LEFT JOIN units un ON u.unit_id = un.id
           JOIN task_assignees ta ON u.id = ta.user_id
           JOIN tasks t ON ta.task_id = t.id
           WHERE u.role != 'Admin'
           GROUP BY u.id
           ORDER BY total DESC""",
        (today,)
    ).fetchall()

    # Overall stats
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'").fetchone()[0]
    overdue = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE deadline < ? AND status != 'Completed'", (today,)
    ).fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status IN ('Not Started', 'In Progress', 'Pending Approval')"
    ).fetchone()[0]

    conn.close()

    completion_rate = round((completed / total * 100) if total > 0 else 0)

    return DotDict(
        by_status=[DotDict(dict(r)) for r in by_status],
        by_priority=[DotDict(dict(r)) for r in by_priority],
        by_user=[DotDict(dict(r)) for r in by_user],
        total=total,
        completed=completed,
        overdue=overdue,
        active=active,
        completion_rate=completion_rate,
    )


def get_activity_log(limit=50, offset=0):
    """Return activity log entries with pagination."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    rows = conn.execute(
        """SELECT al.*, u.name as user_name
           FROM activity_log al
           JOIN users u ON al.user_id = u.id
           ORDER BY al.timestamp DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows], total


def get_unit_staff_list(unit_id):
    """Return list of staff/intern users in a unit (for filter dropdown)."""
    conn = get_db()
    rows = conn.execute(
        """SELECT u.id, u.name, u.role FROM users u
           WHERE u.unit_id = ? AND u.role IN ('Staff', 'Intern') AND u.active = 1
           ORDER BY u.name""",
        (unit_id,)
    ).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_unit_team_workload(unit_id):
    """Return staff/interns in a specific unit with their task counts (for HeadOfUnit dashboard)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.name, u.role, un.name as unit_name,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as task_count,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as active_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks,
               COUNT(DISTINCT CASE WHEN t.deadline < date('now') AND t.status != 'Completed' THEN t.id END) as overdue_tasks,
               COUNT(DISTINCT t.id) as total_tasks,
               MAX(t.overload_flag) as overload_flag
        FROM users u
        LEFT JOIN units un ON u.unit_id = un.id
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        WHERE u.unit_id = ? AND u.role IN ('Staff', 'Intern') AND u.active = 1
        GROUP BY u.id
        ORDER BY task_count DESC
    """, (unit_id,)).fetchall()
    conn.close()
    return [DotDict(dict(r)) for r in rows]


def get_unit_performance_for_head_of_unit(own_unit_id):
    """Return unit performance for HeadOfUnit: just total task counts per unit."""
    conn = get_db()
    rows = conn.execute("""
        SELECT un.id, un.name,
               COUNT(DISTINCT t.id) as total_tasks,
               COUNT(DISTINCT CASE WHEN t.status = 'Completed' THEN t.id END) as completed_tasks,
               COUNT(DISTINCT CASE WHEN t.status IN ('Not Started', 'In Progress', 'Pending Approval') THEN t.id END) as active_tasks
        FROM units un
        LEFT JOIN users u ON u.unit_id = un.id AND u.active = 1
        LEFT JOIN task_assignees ta ON u.id = ta.user_id
        LEFT JOIN tasks t ON ta.task_id = t.id
        WHERE un.id != ?
        GROUP BY un.id
        ORDER BY un.name
    """, (own_unit_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = DotDict(dict(r))
        d.completion_rate = round((d.completed_tasks / d.total_tasks * 100) if d.total_tasks > 0 else 0)
        result.append(d)
    return result
