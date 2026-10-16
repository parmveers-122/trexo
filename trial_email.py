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


def render_trial_email(clinic_name, lead_name, parent_name, preferred_dates, family_email=None, contact_name=None):
    subject = f"Trexo Trial Request - {lead_name}"

    if contact_name:
        greeting = f"Hi {contact_name} and the {clinic_name} team,"
    else:
        greeting = f"Hi {clinic_name} team,"

    if family_email:
        scheduling_line = (
            "I've included the family on this email so you can connect with "
            "them directly and confirm whichever date and time works best."
        )
    else:
        scheduling_line = (
            "Could you please let us know which of these dates works for your "
            "clinic, or suggest a time that suits you better?"
        )

    lines = [
        greeting,
        "",
        "I hope you're doing well! We have a family interested in a Trexo trial at your clinic and would love your help getting it scheduled.",
        "",
        f"Child's name: {lead_name}",
        f"Parent's name: {parent_name or 'N/A'}",
        f"Family email: {family_email or 'N/A'}",
        f"Available dates: {format_preferred_dates(preferred_dates)}",
        "",
        scheduling_line,
        "",
        "Thank you so much for your continued partnership - we really appreciate your help!",
        "",
        "Warm regards,",
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
