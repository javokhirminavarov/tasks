"""Seed the database with test data. Run: python seed_data.py"""

import os
from datetime import date, timedelta
from models import get_db, init_db, DATABASE


def seed():
    # Remove existing database and start fresh
    if os.path.exists(DATABASE):
        os.remove(DATABASE)

    init_db()
    conn = get_db()

    # --- Units ---
    units = [
        ('Development',),
        ('Design',),
        ('Marketing',),
        ('Operations',),
    ]
    conn.executemany("INSERT INTO units (name) VALUES (?)", units)

    # --- Users ---
    # (name, role, unit_id, telegram_id, phone, is_admin)
    # Using fake telegram IDs for testing
    users = [
        ('Aziz Karimov',       'Head',       None, '100000001', '+998901111111', 1),  # Head + Admin
        ('Nodira Sultanova',    'Deputy',     None, '100000002', '+998901111112', 0),
        ('Rustam Aliyev',       'HeadOfUnit', 1,    '100000003', '+998901111113', 0),
        ('Dilnoza Khamidova',   'HeadOfUnit', 2,    '100000004', '+998901111114', 0),
        ('Bekzod Tashmatov',    'HeadOfUnit', 3,    '100000005', '+998901111115', 0),
        ('Gulnara Rakhimova',   'HeadOfUnit', 4,    '100000006', '+998901111116', 0),
        ('Jasur Mirzayev',      'Staff',      1,    '100000007', '+998901111117', 0),
        ('Madina Umarova',      'Staff',      1,    '100000008', '+998901111118', 0),
        ('Oybek Nazarov',       'Staff',      2,    '100000009', '+998901111119', 0),
        ('Shakhlo Karimova',    'Staff',      2,    '100000010', '+998901111120', 0),
        ('Farkhod Ismoilov',    'Staff',      3,    '100000011', '+998901111121', 0),
        ('Zarina Abdullaeva',   'Staff',      3,    '100000012', '+998901111122', 0),
        ('Timur Rakhmatov',     'Staff',      4,    '100000013', '+998901111123', 0),
        ('Sardor Yusupov',      'Intern',     1,    '100000014', '+998901111124', 0),
        ('Kamola Ergasheva',     'Intern',     4,    '100000015', '+998901111125', 0),
    ]
    conn.executemany(
        "INSERT INTO users (name, role, unit_id, telegram_id, phone, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
        users
    )

    # Set unit heads (user IDs shifted: head=1, deputy=2, unit_heads=3..6, staff=7..13, interns=14..15)
    conn.execute("UPDATE units SET head_user_id = 3 WHERE id = 1")
    conn.execute("UPDATE units SET head_user_id = 4 WHERE id = 2")
    conn.execute("UPDATE units SET head_user_id = 5 WHERE id = 3")
    conn.execute("UPDATE units SET head_user_id = 6 WHERE id = 4")

    # --- Projects ---
    today = date.today()
    projects = [
        ('Website Redesign',       'Complete overhaul of the company website',      'Active',    (today + timedelta(days=30)).isoformat(), 1),
        ('Mobile App v2',          'Second version of the mobile application',      'Active',    (today + timedelta(days=45)).isoformat(), 1),
        ('Marketing Campaign Q1',  'First quarter marketing campaign',             'Active',    (today + timedelta(days=15)).isoformat(), 1),
        ('Internal Tools Update',  'Update internal productivity tools',           'Active',    (today + timedelta(days=60)).isoformat(), 1),
        ('Brand Guidelines',       'Create new brand guidelines document',         'Completed', (today - timedelta(days=10)).isoformat(), 1),
    ]
    conn.executemany(
        "INSERT INTO projects (name, description, status, deadline, created_by) VALUES (?, ?, ?, ?, ?)",
        projects
    )

    # --- Tasks (all Ad-hoc) ---
    # requester_id=1 (Head), assignor_id varies
    tasks = [
        ('Design homepage mockup',       'Create wireframes and mockups for new homepage',          'Ad-hoc', 'High',   'Completed',        1, 1, (today - timedelta(days=5)).isoformat()),
        ('Implement responsive layout',  'Make the website responsive for all devices',             'Ad-hoc', 'High',   'In Progress',      1, 1, (today + timedelta(days=10)).isoformat()),
        ('Setup CI/CD pipeline',         'Configure automated deployment pipeline',                 'Ad-hoc', 'Normal', 'Not Started',      1, 1, (today + timedelta(days=20)).isoformat()),
        ('User authentication module',   'Build login and registration for mobile app',             'Ad-hoc', 'Urgent', 'In Progress',      1, 1, (today + timedelta(days=7)).isoformat()),
        ('Push notification system',     'Implement push notifications',                            'Ad-hoc', 'High',   'Not Started',      1, 1, (today + timedelta(days=25)).isoformat()),
        ('API integration',              'Connect mobile app to backend APIs',                      'Ad-hoc', 'Normal', 'Pending Approval', 1, 1, (today + timedelta(days=15)).isoformat()),
        ('Social media content plan',    'Create content calendar for Q1',                          'Ad-hoc', 'High',   'In Progress',      1, 5, (today + timedelta(days=5)).isoformat()),
        ('Email newsletter design',      'Design template for monthly newsletter',                  'Ad-hoc', 'Normal', 'Completed',        1, 5, (today - timedelta(days=3)).isoformat()),
        ('Analytics dashboard setup',    'Set up marketing analytics dashboard',                    'Ad-hoc', 'Normal', 'Not Started',      1, 5, (today + timedelta(days=12)).isoformat()),
        ('Update project management tool','Upgrade and configure PM tool',                          'Ad-hoc', 'Normal', 'In Progress',      1, 6, (today + timedelta(days=30)).isoformat()),
        ('Server maintenance',           'Perform routine server maintenance and updates',          'Ad-hoc', 'Urgent', 'Not Started',      1, 6, today.isoformat()),
        ('Write API documentation',      'Document all REST API endpoints',                         'Ad-hoc', 'Normal', 'In Progress',      3, 3, (today + timedelta(days=14)).isoformat()),
        ('Code review - auth module',    'Review authentication module code',                       'Ad-hoc', 'High',   'Pending Approval', 3, 3, (today + timedelta(days=3)).isoformat()),
        ('Onboard new intern',           'Setup workspace and access for new intern',               'Ad-hoc', 'Low',    'Completed',        6, 6, (today - timedelta(days=7)).isoformat()),
        ('Fix login bug',                'Users report intermittent login failures',                'Ad-hoc', 'Urgent', 'In Progress',      3, 3, today.isoformat()),
    ]
    conn.executemany(
        "INSERT INTO tasks (title, description, type, priority, status, requester_id, assignor_id, deadline) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tasks
    )

    # --- Task Assignees ---
    # user IDs: head=1, deputy=2, unit_heads=3..6, staff=7..13, interns=14..15
    assignments = [
        (1, 9),    # Design homepage - Oybek (Design)
        (1, 10),   # Design homepage - Shakhlo (Design)
        (2, 7),    # Responsive layout - Jasur (Dev)
        (2, 8),    # Responsive layout - Madina (Dev)
        (3, 7),    # CI/CD - Jasur (Dev)
        (4, 7),    # Auth module - Jasur (Dev)
        (4, 14),   # Auth module - Sardor intern (Dev)
        (5, 8),    # Push notifications - Madina (Dev)
        (6, 7),    # API integration - Jasur (Dev)
        (6, 8),    # API integration - Madina (Dev)
        (7, 11),   # Social media - Farkhod (Marketing)
        (7, 12),   # Social media - Zarina (Marketing)
        (8, 12),   # Newsletter - Zarina (Marketing)
        (9, 11),   # Analytics - Farkhod (Marketing)
        (10, 13),  # PM tool - Timur (Operations)
        (10, 15),  # PM tool - Kamola intern (Operations)
        (11, 13),  # Server maintenance - Timur (Operations)
        (12, 7),   # API docs - Jasur (Dev)
        (13, 3),   # Code review - Rustam unit head (Dev)
        (14, 6),   # Onboard intern - Gulnara unit head (Operations)
        (15, 7),   # Fix login bug - Jasur (Dev)
    ]
    conn.executemany(
        "INSERT INTO task_assignees (task_id, user_id) VALUES (?, ?)",
        assignments
    )

    # --- Comments ---
    comments = [
        (2, 7, 'Started working on the responsive layout. Using flexbox and grid.'),
        (2, 1, 'Make sure to test on iPad and Android tablets too.'),
        (4, 7, 'Auth module is taking shape. Using JWT tokens for sessions.'),
        (4, 14, 'I can help with the frontend integration for login forms.'),
        (6, 7, 'API integration is done. Ready for review.'),
        (6, 8, 'I tested the endpoints, all returning correct responses.'),
        (13, 3, 'Please check the edge cases in the password reset flow.'),
        (15, 7, 'Found the root cause - session cookie was expiring prematurely.'),
    ]
    conn.executemany(
        "INSERT INTO comments (task_id, user_id, comment_text) VALUES (?, ?, ?)",
        comments
    )

    # --- Activity Log ---
    activities = [
        (1, 'Created task', 'Task', 1, 'Design homepage mockup'),
        (1, 'Created task', 'Task', 2, 'Implement responsive layout'),
        (1, 'Created task', 'Task', 3, 'Setup CI/CD pipeline'),
        (1, 'Created task', 'Task', 4, 'User authentication module'),
        (7, 'Changed status to In Progress', 'Task', 2, 'Implement responsive layout'),
        (7, 'Changed status to In Progress', 'Task', 4, 'User authentication module'),
        (7, 'Added comment', 'Task', 2, None),
        (1, 'Added comment', 'Task', 2, None),
        (7, 'Changed status to Pending Approval', 'Task', 6, 'API integration'),
        (3, 'Created task', 'Task', 12, 'Write API documentation'),
        (3, 'Created task', 'Task', 13, 'Code review - auth module'),
        (1, 'Created user', 'User', 7, 'Jasur Mirzayev'),
        (1, 'Created user', 'User', 8, 'Madina Umarova'),
        (1, 'Created unit', 'Unit', 1, 'Development'),
        (1, 'Updated unit', 'Unit', 1, 'Development'),
        (6, 'Changed status to Completed', 'Task', 14, 'Onboard new intern'),
        (11, 'Changed status to In Progress', 'Task', 7, 'Social media content plan'),
        (7, 'Changed status to In Progress', 'Task', 15, 'Fix login bug'),
        (7, 'Added comment', 'Task', 15, None),
    ]
    conn.executemany(
        "INSERT INTO activity_log (user_id, action, entity_type, entity_id, details) VALUES (?, ?, ?, ?, ?)",
        activities
    )

    conn.commit()
    conn.close()
    print("Database seeded successfully!")
    print(f"Database file: database.db")
    print("\nTest users (authenticate via Telegram):")
    print("  Aziz Karimov     - Head + Admin (TG: 100000001)")
    print("  Nodira Sultanova  - Deputy (TG: 100000002)")
    print("  Rustam Aliyev     - HeadOfUnit/Dev (TG: 100000003)")
    print("  Jasur Mirzayev    - Staff/Dev (TG: 100000007)")
    print("  Sardor Yusupov    - Intern/Dev (TG: 100000014)")
    print("  ... and 10 more users")


if __name__ == '__main__':
    seed()
