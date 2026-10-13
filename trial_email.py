"""
Generates a draft trial-booking email to a clinic. This is a starting
draft, not approved copy - review before sending.
"""

import datetime
from urllib.parse import quote


def _format_date(iso_date):
    try:
        return datetime.date.fromisoformat(iso_date).strftime("%B %-d")
    except (ValueError, TypeError):
        return iso_date  # not an ISO date (e.g. an older free-text entry) - show as-is


def format_preferred_dates(preferred_dates):
    dates = [_format_date(d) for d in (preferred_dates or []) if d]
    if not dates:
        return "Flexible - happy to work around your schedule"
    if len(dates) == 1:
        return dates[0]
    if len(dates) == 2:
        return f"{dates[0]} or {dates[1]}"
    return ", ".join(dates[:-1]) + f", or {dates[-1]}"


def render_trial_email(clinic_name, lead_name, parent_name, preferred_dates, family_email=None):
    subject = f"Trexo Device Trial Request - {lead_name}"

    if family_email:
        scheduling_line = (
            f"I've included {lead_name}'s family on this email so you can "
            "coordinate directly and confirm whichever of these dates/times "
            "works best for everyone."
        )
    else:
        scheduling_line = (
            "Could you please confirm your availability for one of these dates, "
            "or let us know a time that works better for your clinic's schedule?"
        )

    lines = [
        f"Hi {clinic_name} team,",
        "",
        f"We'd like to schedule a Trexo device trial at your clinic for {lead_name}.",
        "",
        f"Child's name: {lead_name}",
        f"Parent's name: {parent_name or 'N/A'}",
        f"Preferred date(s): {format_preferred_dates(preferred_dates)}",
        f"Family email: {family_email or 'N/A'}",
        "",
        scheduling_line,
        "",
        f"Thanks so much for partnering with us to support {lead_name} - we really appreciate it!",
        "",
        "Best regards,",
        "Trexo Robotics Team",
    ]
    body = "\n".join(lines)
    return subject, body


def mailto_link(to_address, subject, body, cc_address=None):
    to = quote(to_address or "")
    link = f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
    if cc_address:
        link += f"&cc={quote(cc_address)}"
    return link
