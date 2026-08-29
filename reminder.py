"""
reminder.py

Checks all tracked assignments against fixed time-to-deadline thresholds
and sends a Telegram reminder. Handles missed polling windows (e.g. bot was
offline and remaining time skips straight past multiple thresholds) by
firing only the single most-urgent applicable threshold, not one alert per
skipped threshold. Dedupes via each assignment's `reminders_sent` list.
"""

from datetime import datetime, timedelta, timezone

REMINDER_THRESHOLDS = [
    ("24h", timedelta(hours=24)),
    ("6h", timedelta(hours=6)),
    ("1h", timedelta(hours=1)),
]


def check_reminders(state: dict, now: datetime, send_telegram) -> dict:
    """Mutates and returns `state` with updated reminders_sent lists.
    `send_telegram` is a function(text: str) -> None."""
    # Sorted ascending by threshold explicitly, rather than relying on
    # REMINDER_THRESHOLDS already being declared in descending order —
    # keeps the "nearest urgent threshold" logic correct even if someone
    # edits the list above without re-sorting it themselves.
    thresholds_ascending = sorted(REMINDER_THRESHOLDS, key=lambda pair: pair[1])

    for assignment_id, info in state.get("assignments", {}).items():
        due_str = info.get("due_date")
        if not due_str:
            continue  # No due date on record — nothing to check yet.

        try:
            due = datetime.fromisoformat(due_str)
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        except ValueError:
            continue  # Corrupt/unparseable date — skip rather than crash.

        remaining = due - now
        if remaining <= timedelta(0):
            continue  # Already overdue — no reminder value left to add.

        sent = set(info.get("reminders_sent", []))

        for label, threshold in thresholds_ascending:
            if remaining <= threshold:
                if label not in sent:
                    send_telegram(
                        f"Reminder: '{info['title']}' is due in less than {label}.\n{info['url']}"
                    )
                    # A missed polling window may mean we're jumping straight
                    # past one or more larger thresholds — mark all of them
                    # sent too, so this run's single alert doesn't get
                    # followed by a burst of "backdated" ones.
                    for l, t in REMINDER_THRESHOLDS:
                        if t >= threshold:
                            sent.add(l)
                break  # Only ever act on the nearest applicable threshold per run.

        info["reminders_sent"] = sorted(sent)

    return state