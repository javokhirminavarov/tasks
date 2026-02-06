# Dashboard Template Modifications

## Summary
The static `code.html` file has been converted into a Flask/Jinja2 template following the guidelines in `CLAUDE.md`. The modifications transform the static dashboard into a dynamic, role-based interface that integrates with a Flask backend.

## Files Created/Modified

### 1. `dashboard.html` (renamed from `code.html`)
**Purpose:** Universal Dashboard page for all user roles

**Key Changes:**
- Converted to extend `base.html` template
- Replaced hardcoded values with Jinja2 template variables
- Added role-based visibility controls
- Made all sections dynamic with backend data

**Dynamic Elements:**
- **Greeting Section:** Shows current date and logged-in user's name
- **Overview Stats:** Displays real-time counts from database
  - Active Tasks: `{{ stats.active_tasks }}`
  - Active Projects: `{{ stats.active_projects }}`
  - Completed Tasks: `{{ stats.completed_tasks }}`
  - Deadlines Today: `{{ stats.deadlines_today }}`

- **Team Workload** (Head/Deputy only):
  - Loops through `team_workload` list
  - Color-coded indicators: Green (≤3 tasks), Yellow (4-6), Red (≥7)
  - Shows overload flag for staff with too many tasks
  - Avatar placeholders with initials

- **Unit Performance** (Head/Deputy only):
  - Loops through `unit_performance` list
  - Progress bars showing completion rates
  - Task counts per unit

- **Active Projects:**
  - Loops through `active_projects` list
  - Clickable project cards linking to detail page
  - Team member avatars
  - Progress bars and completion rates
  - Dynamic deadline text

### 2. `base.html` (newly created)
**Purpose:** Base template with common layout elements

**Features:**
- Complete HTML structure with all CSS/JS includes
- Tailwind CSS configuration with custom colors and theme
- Dark mode support
- Top App Bar with:
  - TaskFlow branding
  - Notifications button with unread indicator
  - User avatar with dropdown menu (Profile, Logout)

- Bottom Navigation Bar with:
  - Dashboard/Overview
  - Tasks
  - Projects
  - Admin Panel (for Admin users) or Settings (for others)
  - Active state highlighting

**Template Blocks:**
- `{% block title %}` - Page title
- `{% block extra_css %}` - Additional CSS for specific pages
- `{% block content %}` - Main page content
- `{% block extra_js %}` - Additional JavaScript for specific pages

## Required Backend Variables

The dashboard template expects the following variables from the Flask route:

```python
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html',
        current_user={
            'name': 'User Name',
            'role': 'Head'  # Admin, Head, Deputy, HeadOfUnit, Staff, Intern
        },
        current_date='Monday, Jan 28',
        notification_count=3,
        stats={
            'active_tasks': 12,
            'active_projects': 4,
            'completed_tasks': 28,
            'deadlines_today': 2
        },
        team_workload=[
            {
                'name': 'Staff Name',
                'unit_name': 'Unit Name',
                'task_count': 5,
                'overload_flag': False
            }
        ],
        unit_performance=[
            {
                'name': 'Unit Name',
                'total_tasks': 14,
                'completion_rate': 85
            }
        ],
        active_projects=[
            {
                'id': 1,
                'name': 'Project Name',
                'description': 'Project description',
                'completion_rate': 75,
                'deadline_text': 'Due in 2 days',
                'assignees': [
                    {'name': 'User 1'},
                    {'name': 'User 2'}
                ]
            }
        ]
    )
```

## Required Flask Routes

The template references these routes (need to be created):
- `dashboard` - Main dashboard page
- `tasks_list` - All tasks page
- `projects_list` - All projects page
- `project_detail` - Individual project page
- `team_workload` - Full team workload page
- `units_performance` - Full units performance page
- `notifications` - Notifications page
- `profile` - User profile page
- `settings` - Settings page
- `admin_panel` - Admin panel (for Admin role)
- `logout` - Logout action

## Role-Based Access Control

The template implements role-based visibility:
- **All Users:** Can see overview stats and active projects
- **Head/Deputy Only:** Can see Team Workload and Unit Performance sections
- **Admin Only:** Gets Admin Panel in bottom navigation instead of Settings

## Next Steps

1. **Create Flask App Structure:**
   ```
   task-management/
   ├── app.py
   ├── models.py
   ├── auth.py
   ├── templates/
   │   ├── base.html
   │   └── dashboard.html
   └── database.db
   ```

2. **Implement Backend Routes:**
   - Create database queries to fetch dashboard statistics
   - Implement team workload calculations
   - Calculate unit performance metrics
   - Fetch active projects with assignees

3. **Add Authentication:**
   - Implement session-based auth
   - Create login/logout routes
   - Add `current_user` to all templates

4. **Test with Sample Data:**
   - Create sample users with different roles
   - Add test tasks and projects
   - Verify role-based visibility

## Design Features

- **Responsive Design:** Mobile-first with Tailwind CSS
- **Dark Mode:** Full dark mode support with toggle capability
- **Modern UI:** Clean, professional interface with Material Symbols icons
- **Smooth Interactions:** Hover effects, transitions, and animations
- **Accessibility:** Semantic HTML, proper ARIA labels

## Notes

- All external images replaced with avatar placeholders showing initials
- "See All" buttons converted to proper links with `url_for()`
- Project cards made clickable for better UX
- Empty state handling for projects section
- Color-coded visual indicators for workload status
