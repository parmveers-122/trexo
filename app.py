import datetime
import os

from flask import Flask, flash, redirect, render_template, request, url_for

import geocode
import trial_email
import trial_store

# Explicit absolute static folder path - Vercel's serverless runtime doesn't
# always resolve Flask's default relative static path correctly, which is
# why the CSS wasn't loading there.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(_BASE_DIR, "static"), static_url_path="/static")
app.secret_key = "dev-only-not-for-production"
trial_store.init_db()

SALES_CC_EMAIL = "sales@trexorobotics.com"


@app.route("/")
def clinic_directory():
    lead_address = request.args.get("lead_address", "").strip()
    lead_coords = None
    address_not_found = False

    if lead_address:
        lead_coords = geocode.geocode_address(lead_address)
        if not lead_coords:
            address_not_found = True

    clinics = []
    for clinic in trial_store.CLINICS:
        contact = trial_store.get_clinic_contact(clinic["id"])
        distance_km = None
        if lead_coords:
            distance_km = geocode.haversine_km(
                lead_coords[0], lead_coords[1], clinic["lat"], clinic["lon"]
            )
        clinics.append({
            **clinic,
            "contact": contact,
            "trial_count": trial_store.count_trial_bookings_for_clinic(clinic["id"]),
            "distance_km": distance_km,
        })

    if lead_coords:
        clinics.sort(key=lambda c: c["distance_km"])

    # Bookable clinics first (stable sort keeps the distance/default order within each group).
    clinics.sort(key=lambda c: not c["bookable"])

    return render_template(
        "clinics.html",
        clinics=clinics,
        lead_address=lead_address,
        address_not_found=address_not_found,
    )


@app.route("/clinic/<clinic_id>/contact", methods=["POST"])
def save_clinic_contact(clinic_id):
    clinic = trial_store.get_clinic_by_id(clinic_id)
    if not clinic:
        flash("Unknown clinic.", "error")
        return redirect(url_for("clinic_directory"))

    trial_store.save_clinic_contact(
        clinic_id,
        request.form.get("email", "").strip(),
        request.form.get("phone", "").strip(),
        datetime.date.today().isoformat(),
    )
    flash(f"Contact info saved for {clinic['name']}.", "success")
    return redirect(url_for("clinic_directory"))


@app.route("/clinic/<clinic_id>/book-trial", methods=["GET", "POST"])
def book_trial(clinic_id):
    clinic = trial_store.get_clinic_by_id(clinic_id)
    if not clinic:
        flash("Unknown clinic.", "error")
        return redirect(url_for("clinic_directory"))

    if not clinic["bookable"]:
        flash(f"{clinic['name']} isn't available for trial requests yet.", "error")
        return redirect(url_for("clinic_directory"))

    if clinic.get("booking_link"):
        # Clinics with their own online booking link skip our form and email draft.
        return redirect(clinic["booking_link"])

    if request.method == "POST":
        lead_name = request.form.get("lead_name", "").strip()
        parent_name = request.form.get("parent_name", "").strip()
        family_email = request.form.get("family_email", "").strip()
        if not lead_name or not parent_name or not family_email:
            flash("Child's name, parent's name and family email are required.", "error")
            return redirect(url_for("book_trial", clinic_id=clinic_id))

        preferred_dates = sorted({d.strip() for d in request.form.getlist("preferred_dates") if d.strip()})
        if not preferred_dates:
            flash("Pick at least one preferred date.", "error")
            return redirect(url_for("book_trial", clinic_id=clinic_id))

        try:
            parsed_dates = [datetime.date.fromisoformat(d) for d in preferred_dates]
        except ValueError:
            flash("One of the preferred dates isn't valid.", "error")
            return redirect(url_for("book_trial", clinic_id=clinic_id))
        # The server may be on UTC, a day ahead of the rep, so allow yesterday's
        # server date; the date picker itself already blocks past dates locally.
        earliest = datetime.date.today() - datetime.timedelta(days=1)
        if any(d < earliest for d in parsed_dates):
            flash("Preferred dates can't be in the past.", "error")
            return redirect(url_for("book_trial", clinic_id=clinic_id))

        allowed_weekdays = clinic.get("available_weekdays")
        if allowed_weekdays and any(d.weekday() not in allowed_weekdays for d in parsed_dates):
            flash(
                f"{clinic['name']} only runs trials {clinic['available_days_label']} - "
                "please remove any other dates.",
                "error",
            )
            return redirect(url_for("book_trial", clinic_id=clinic_id))

        booking_id = trial_store.add_trial_booking(
            clinic_id,
            clinic["name"],
            lead_name,
            parent_name,
            preferred_dates,
            family_email,
            datetime.datetime.now().isoformat(timespec="minutes"),
        )

        if clinic.get("is_internal"):
            # Our own office - no external clinic to email, just log the booking.
            flash(f"Trial requested at {clinic['name']} for {lead_name}.", "success")
            return redirect(url_for("trials_log"))

        return redirect(url_for("trial_email_preview", booking_id=booking_id))

    return render_template("book_trial.html", clinic=clinic)


@app.route("/trial/<int:booking_id>/email")
def trial_email_preview(booking_id):
    booking = trial_store.get_trial_booking(booking_id)
    if not booking:
        flash("Trial request not found.", "error")
        return redirect(url_for("clinic_directory"))

    contact = trial_store.get_clinic_contact(booking["clinic_id"])
    clinic = trial_store.get_clinic_by_id(booking["clinic_id"]) or {}
    subject, body = trial_email.render_trial_email(
        booking["clinic_name"],
        booking["lead_name"],
        booking["parent_name"],
        booking["preferred_dates"] or ([booking["preferred_datetime"]] if booking["preferred_datetime"] else []),
        booking["family_email"],
        clinic.get("contact_name"),
    )
    to_address = contact.get("email", "") or ""
    # Family plus the shared sales mailbox, so sales@ keeps a copy of every request.
    cc_address = ", ".join(a for a in (booking["family_email"], SALES_CC_EMAIL) if a)
    return render_template(
        "compose_trial_email.html",
        booking=booking,
        subject=subject,
        body=body,
        to_address=to_address,
        cc_address=cc_address,
        mailto=trial_email.mailto_link(to_address, subject, body, cc_address),
    )


@app.route("/trials")
def trials_log():
    bookings = trial_store.list_trial_bookings()
    return render_template("trials_log.html", bookings=bookings)


if __name__ == "__main__":
    app.run(debug=True, port=8070, host='0.0.0.0')
