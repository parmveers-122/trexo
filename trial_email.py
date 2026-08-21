"""
Generates a draft trial-booking email to a clinic. This is a starting
draft, not approved copy - review before sending.
"""

from urllib.parse import quote


def render_trial_email(clinic_name, lead_name, preferred_datetime, lead_contact):
    subject = f"Trexo Device Trial Request - {lead_name}"

    lines = [
        f"Hi {clinic_name} team,",
        "",
        f"We'd like to schedule a Trexo device trial at your clinic for {lead_name}.",
        "",
        f"Child's name: {lead_name}",
        f"Preferred date/time: {preferred_datetime or 'Flexible - happy to work around your schedule'}",
        f"Family contact info: {lead_contact or 'N/A'}",
        "",
        "Could you please confirm your availability for this date, or let us "
        "know a time that works better for your clinic's schedule?",
        "",
        "We're happy to answer any questions about the Trexo device or the "
        "trial process in the meantime.",
        "",
        f"Thank you for partnering with us to support {lead_name}.",
        "",
        "Best regards,",
        "Trexo Robotics Team",
    ]
    body = "\n".join(lines)
    return subject, body


def mailto_link(to_address, subject, body):
    to = quote(to_address or "")
    return f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"
