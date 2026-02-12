Task Management App - Development Guide
Project Overview
A role-based task management system with 6 user roles (Admin, Head/Deputy of Department, Head of Unit, Regular Staff, Intern) built incrementally from provided UI mockups.
Tech Stack (Lightweight)

Backend: Python Flask (simple, minimal)
Database: SQLite (single file database)
Frontend: HTML, CSS (Tailwind CDN), JavaScript (vanilla or minimal Alpine.js)
Authentication: Simple session-based auth (or Telegram Web Auth if needed later)
Notifications: Telegram Bot API (implement when needed)

Development Approach
IMPORTANT: Build this application incrementally.

I will provide HTML/CSS UI code for specific pages
You integrate the HTML and add backend functionality for that page only
Create database tables as needed for that specific feature
Test that feature works before moving to next page
Do NOT build everything at once

Project Structure
task-management/
├── app.py                 # Main Flask application
├── database.db            # SQLite database
├── models.py              # Database models/queries
├── auth.py                # Authentication logic
├── static/
│   ├── css/
│   └── js/
├── templates/
│   ├── base.html         # Base template with navigation
│   ├── dashboard.html
│   ├── tasks/
│   ├── admin/
│   └── reports/
└── README.md
Database Schema (Create tables as needed)
sql-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL, -- Admin, Head, Deputy, HeadOfUnit, Staff, Intern
    unit_id INTEGER,
    telegram_id TEXT,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES units(id)
);

-- Units table
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    head_user_id INTEGER,
    FOREIGN KEY (head_user_id) REFERENCES users(id)
);

-- Tasks table
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'Ad-hoc', -- Always Ad-hoc
    priority TEXT NOT NULL, -- Urgent, High, Normal, Low
    status TEXT NOT NULL, -- Not Started, In Progress, Pending Approval, Completed
    requester_id INTEGER NOT NULL,
    assignor_id INTEGER NOT NULL,
    deadline DATE NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_date TIMESTAMP,
    completion_note TEXT,
    overload_flag BOOLEAN DEFAULT 0,
    overload_timestamp TIMESTAMP,
    FOREIGN KEY (requester_id) REFERENCES users(id),
    FOREIGN KEY (assignor_id) REFERENCES users(id)
);

-- Task Assignees (many-to-many)
CREATE TABLE task_assignees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Comments table
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Activity Log (audit trail)
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT, -- Task, User
    entity_id INTEGER,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
Permission Implementation
Implement role-based access control based on this matrix:

Admin: User/unit management only, no task access
Head/Deputy: Full access to all tasks
Head of Unit: Access to unit tasks only
Staff/Intern: Own tasks only, can create tasks for approval

Check permissions on every route using decorators.
Key Implementation Guidelines
When I provide HTML for a page:

Extract the UI elements from the HTML
Create the Flask route for that page
Create database queries needed for that page
Add permission checks based on user role
Connect UI actions to backend (forms, buttons, filters)
Test with sample data before moving forward

Start Simple:

Begin with basic auth (username/password stored in users table)
Add Telegram auth later if needed
Use server-side rendering (Jinja templates) - keep it simple
Add AJAX for dynamic updates only when necessary
Focus on functionality over fancy features

Sample Data:
Create a simple script to populate test data:

1 Admin user
2 Head/Deputy users
4 Units with 1 Head of Unit each
5-10 Staff members distributed across units
10-15 sample tasks with various statuses
Development Phases
Phase 1: Foundation

Setup Flask app and SQLite
Create base template with navigation
Implement simple authentication
Universal Dashboard (read-only)

Phase 2: Core Task Management

Staff "My Tasks" page
Task detail view
Task creation and status updates
Task assignment workflow

Phase 3: Management Views

All Tasks page (Head/Deputy)
Unit Tasks page (Head of Unit)
Filtering and sorting

Phase 4: Admin & Reports

User management
Unit management
Basic reports

Phase 5: Enhancement

Comments
Activity log
Notifications (if time permits)

Current Status
Waiting for first HTML page to begin implementation.
Once you provide HTML, I will:

Integrate it into Flask templates
Add necessary backend routes
Create required database tables
Implement the functionality
Confirm it's working before next page

Reference
See attached Task_management.docx for complete requirements and workflows.