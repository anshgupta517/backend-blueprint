from prometheus_client import Counter, Histogram, Gauge

# Count business events — not just HTTP requests
user_registrations_total = Counter(
    "user_registrations_total",
    "Total number of user registrations",
)

login_attempts_total = Counter(
    "login_attempts_total",
    "Total login attempts",
    ["status"],     # label: 'success' or 'failure'
)

active_users_gauge = Gauge(
    "active_users_total",
    "Current number of active users in the system",
)