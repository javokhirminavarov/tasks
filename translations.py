"""Uzbek (Latin) display translations for enum-like DB values.

DB columns keep their English values; these helpers are exposed as Jinja
filters so templates can render the Uzbek equivalents.
"""

ROLE_UZ = {
    'Admin': 'Administrator',
    'Head': 'Rahbar',
    'Deputy': "O'rinbosar",
    'HeadOfUnit': "Bo'lim boshlig'i",
    'Staff': 'Xodim',
    'Intern': 'Stajyor',
}

STATUS_UZ = {
    'Not Started': 'Boshlanmagan',
    'In Progress': 'Jarayonda',
    'Pending Approval': 'Tasdiqlash kutilmoqda',
    'Completed': 'Bajarilgan',
}

PRIORITY_UZ = {
    'Urgent': 'Shoshilinch',
    'High': 'Yuqori',
    'Normal': "O'rtacha",
    'Low': 'Past',
}

TYPE_UZ = {
    'Ad-hoc': 'Joriy',
}


def role_uz(value):
    return ROLE_UZ.get(value, value or '')


def status_uz(value):
    return STATUS_UZ.get(value, value or '')


def priority_uz(value):
    return PRIORITY_UZ.get(value, value or '')


def type_uz(value):
    return TYPE_UZ.get(value, value or '')


def register_filters(app):
    app.jinja_env.filters['role_uz'] = role_uz
    app.jinja_env.filters['status_uz'] = status_uz
    app.jinja_env.filters['priority_uz'] = priority_uz
    app.jinja_env.filters['type_uz'] = type_uz
