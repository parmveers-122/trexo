# Clinic Trial Requests (prototype)

A standalone prototype for sales reps: browse the clinic network, request a
Trexo trial for a family at a clinic, and get a draft email ready to send.

Nothing is connected to any external system - no Airtable, no CRM, no email
API. Clinic contact info and trial requests are stored in `trials.db`
(SQLite, gitignored). The app never sends email itself: the "Open in Gmail"
button opens the drafted email in the rep's own Gmail, and they click Send
there - no credentials needed.

## Run it

```bash
cd "trexo-clinic-trials"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://localhost:8070.

## What's here

- **Clinic directory** (`/`) - the clinic network as cards. Clinics that can
  take requests are listed first; the rest are greyed out. Each active card has
  a "Request a Trial" button and an editable contact info block. A search box
  sorts clinics by distance from a family's address.
- **Request a Trial** (`/clinic/<id>/book-trial`) - child's full name,
  parent's full name, one or more preferred dates (past dates are blocked), and
  the family's email. Clinics with their own online booking link (currently
  the head office) send reps straight to that link instead.
- **Trial email** - a drafted request email to the clinic, editable, with the
  family and sales@trexorobotics.com on CC. "Open in Gmail" opens it in the
  rep's Gmail; a link below it uses the default email app instead.
- **Requested Trials** (`/trials`) - a log of every trial requested so far.

## Deploying

The repo is connected to Vercel (`vercel.json`); pushing to `main` deploys it.
On Vercel the database lives in `/tmp` and is wiped when the function
restarts, so requests and saved contact info don't persist there.

## Adding or changing a clinic

All clinic details live in `CLINICS` in `trial_store.py`:

- `BOOKABLE_CLINIC_IDS` controls which clinics are active (the rest grey out).
- Optional per-clinic fields: `trial_details` (bullet list shown on the card
  and request page), `default_email` (clinic's booking email, used when none
  is saved through the app), `contact_name` (used in the email greeting), and
  `booking_link` (skips our form and links out). The head office
  `booking_link` is still a placeholder.

Email wording is in `trial_email.py`.
