"""
Local SQLite-backed store for the clinic trial-booking prototype.

Nothing here is connected to any external system (no Airtable, no real CRM,
no email sending) - this is a standalone prototype for sales reps to book
device trials at partner clinics and generate a draft email to send.

The clinic list itself is a hardcoded starter set (real names, provided by
the user) - contact info (email/phone/address) isn't known yet, so it's
editable per-clinic and stored locally rather than guessed.
"""

import json
import os
import sqlite3

# Vercel's deployment bundle is read-only - only /tmp is writable there (and
# it's wiped between cold starts, so booking/contact data won't persist
# reliably in that environment). Locally, keep the db next to this file as
# before.
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/trials.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trials.db")

# Starter clinic network. Add more here as the network grows.
# Addresses are each clinic's real public location (from kidsphysio.ca);
# lat/lon were geocoded once via OpenStreetMap Nominatim so "find nearest
# clinic" doesn't need to re-geocode these fixed points on every search.
CLINICS = [
    {
        "id": "trexo-head-office",
        "name": "Trexo Robotics Head Office",
        "address": "6705 Millcreek Dr Unit 3, Mississauga, ON L5N 5R8",
        "lat": 43.5944500,
        "lon": -79.7497110,
        "device_size": "S/M/L/XL",
        "free_trial": True,
        "is_internal": True,
    },
    {
        "id": "kids-physio-montreal",
        "name": "Kids Physio Group Montreal",
        "address": "5254 Rue Ferrier, Montreal, QC H4P 1L3",
        "lat": 45.4979728,
        "lon": -73.6566365,
        "device_size": "Medium",
        "free_trial": True,
    },
    {
        "id": "kids-physio-midtown-toronto",
        "name": "Kids Physio Group Midtown Toronto",
        "address": "5000-3080 Yonge Street, Toronto, ON M4N 3N1",
        "lat": 43.7255712,
        "lon": -79.4025904,
        "device_size": "Large",
        "free_trial": True,
    },
    {
        "id": "kids-physio-surrey",
        "name": "Kids Physio Group Surrey",
        "address": "302-14351 104 Avenue, Surrey, BC V3T 1Y1",
        "lat": 49.1920114,
        "lon": -122.8242848,
        "device_size": "Medium",
        "free_trial": True,
    },
    {
        "id": "kaylas-childrens-centre",
        "name": "Kayla's Children's Centre",
        "address": "36 Atkinson Avenue, Thornhill, ON L4J 8C9",
        "lat": 43.8099013,
        "lon": -79.4438989,
        "device_size": "Large",
        "free_trial": True,
    },
    {
        "id": "smile-therapy-vancouver",
        "name": "SMILE Therapy for Kids Vancouver",
        "address": "507-233 Nelson's Crescent, New Westminster, BC",
        "lat": 49.2243174,
        "lon": -122.8922050,
        "device_size": "Medium",
        "free_trial": True,
    },
    {
        "id": "smile-therapy-vaughan",
        "name": "S.M.I.L.E. Therapy for Kids - Vaughan/Thornhill",
        "address": "10-130 Racco Parkway, Thornhill, ON L4J 8X9",
        "lat": 43.8160646,
        "lon": -79.4756073,
        "device_size": "Medium",
        "free_trial": False,
    },
    {
        "id": "smile-therapy-burlington",
        "name": "S.M.I.L.E. Therapy for Kids - Burlington",
        "address": "108-3228 South Service Rd, Burlington, ON L7N 3H8",
        "lat": 43.3589447,
        "lon": -79.7955719,
        "device_size": "Medium",
        "free_trial": False,
    },
    {
        "id": "first-steps-wellness-regina",
        "name": "First Steps Wellness Centre",
        "address": "2339 2nd Ave, Regina, SK",
        "lat": 50.4664628,
        "lon": -104.6169265,
        "device_size": "Medium/XL",
        "free_trial": True,
        "default_email": "sandim@fswcregina.ca",
        "trial_details": [
            "Trials available Monday-Friday",
            "Average trial length: 60 minutes",
            "First trial is free",
            "Trial can't be claimed through insurance",
            "No cancellation fee",
        ],
    },
    {
        "id": "canadian-centre-development-calgary",
        "name": "Canadian Centre for Development",
        "address": "5970 Centre St S, Calgary, AB",
        "lat": 51.0423765,
        "lon": -114.0632736,
        "device_size": "Medium",
        "free_trial": False,
    },
]


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clinic_contacts (
            clinic_id TEXT PRIMARY KEY,
            email TEXT,
            phone TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trial_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinic_id TEXT NOT NULL,
            clinic_name TEXT NOT NULL,
            lead_name TEXT NOT NULL,
            preferred_datetime TEXT,
            preferred_dates TEXT,
            lead_contact TEXT,
            family_email TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    # preferred_dates/family_email were added after the initial schema - older
    # local/deployed databases won't have them yet, so add if missing rather
    # than dropping and recreating the table (which would lose bookings).
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(trial_bookings)")}
    if "preferred_dates" not in existing_columns:
        conn.execute("ALTER TABLE trial_bookings ADD COLUMN preferred_dates TEXT")
    if "family_email" not in existing_columns:
        conn.execute("ALTER TABLE trial_bookings ADD COLUMN family_email TEXT")
    conn.commit()
    conn.close()


def get_clinic_by_id(clinic_id):
    return next((c for c in CLINICS if c["id"] == clinic_id), None)


def get_clinic_contact(clinic_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM clinic_contacts WHERE clinic_id = ?", (clinic_id,)
    ).fetchone()
    conn.close()
    contact = dict(row) if row else {}
    # Fall back to the email hardcoded on the clinic (survives Vercel's wiped
    # /tmp db); an email saved through the UI still takes priority.
    clinic = get_clinic_by_id(clinic_id)
    if clinic and clinic.get("default_email") and not contact.get("email"):
        contact["email"] = clinic["default_email"]
    return contact


def save_clinic_contact(clinic_id, email, phone, updated_at):
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO clinic_contacts (clinic_id, email, phone, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(clinic_id) DO UPDATE SET
            email = excluded.email,
            phone = excluded.phone,
            updated_at = excluded.updated_at
        """,
        (clinic_id, email or None, phone or None, updated_at),
    )
    conn.commit()
    conn.close()


def add_trial_booking(clinic_id, clinic_name, lead_name, preferred_dates, lead_contact, family_email, created_at):
    """preferred_dates is a list of ISO date strings (e.g. ["2026-08-26"])."""
    conn = _get_conn()
    cursor = conn.execute(
        """
        INSERT INTO trial_bookings
            (clinic_id, clinic_name, lead_name, preferred_dates, lead_contact, family_email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (clinic_id, clinic_name, lead_name, json.dumps(preferred_dates), lead_contact or None, family_email or None, created_at),
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id


def _with_parsed_dates(row):
    booking = dict(row)
    try:
        booking["preferred_dates"] = json.loads(booking["preferred_dates"]) if booking["preferred_dates"] else []
    except (TypeError, ValueError):
        booking["preferred_dates"] = []
    return booking


def get_trial_booking(booking_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM trial_bookings WHERE id = ?", (booking_id,)).fetchone()
    conn.close()
    return _with_parsed_dates(row) if row else None


def list_trial_bookings(limit=200):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM trial_bookings ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_with_parsed_dates(r) for r in rows]


def count_trial_bookings_for_clinic(clinic_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as n FROM trial_bookings WHERE clinic_id = ?", (clinic_id,)
    ).fetchone()
    conn.close()
    return row["n"] if row else 0
