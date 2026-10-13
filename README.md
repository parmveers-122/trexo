# Clinic Trial Requests (prototype)

A standalone prototype for sales reps: browse the clinic network, book a
device trial for a lead at a clinic, and get a draft email ready to send.

Nothing is connected to any external system - no Airtable, no CRM, no email
API. Clinic contact info and booked trials are stored locally in
`trials.db` (SQLite, gitignored). Sending uses a `mailto:` link, which opens
your own email client with the draft pre-filled - no credentials needed.

## Run it

```bash
cd "trexo-clinic-trials"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5060.

## What's here

- **Clinic directory** (`/`) - the clinic network as cards, each with an
  optional editable contact info block and a "Request a Trial" button.
- **Request a Trial** - enter the lead's name, preferred date/time, and contact
  info for a given clinic.
- **Trial email** - a drafted request email to that clinic, editable, with
  an "Open in Email App" button (mailto link).
- **Requested Trials** (`/trials`) - a log of every trial requested so far.

## Notes for later

- Clinic list (`trial_store.py: CLINICS`) is hardcoded - add more clinics
  there, or move to a real data source once this needs to scale.
- Email wording in `trial_email.py` is a starting draft - refine it once
  there's a house style for outreach to clinics.
