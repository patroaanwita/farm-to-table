# FarmTrack — Grade 9 Farm-to-Table Prototype

FarmTrack is a mobile-first Flask website that follows vegetable batches from harvest to market. It demonstrates QR traceability, cloud data and SMS notifications in a form a Grade 9 student can explain and present.

## Features

- Public batch tracking pages with journey timelines
- QR code generated for every batch
- Presenter dashboard for creating batches and checkpoints
- Twilio SMS integration with a built-in simulation fallback
- Supabase PostgreSQL support and local SQLite fallback
- Responsive design for phones, tablets and laptops
- Seeded tomato journey for an immediate demonstration

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`. The local default presenter password is `farmtrack9`; set `ADMIN_PASSWORD` before deployment.

## Supabase setup

1. Create a free Supabase project.
2. Open **Project Settings → Database** and copy the connection string for the transaction pooler.
3. Replace the password placeholder and set it as `DATABASE_URL` in Render.
4. Use the SQLAlchemy format shown in `.env.example`. Keep `sslmode=require`.

Tables are created automatically on first startup. The demonstration batch is also seeded automatically.

## Twilio setup

Verify the demonstration recipient in the Twilio trial account, then configure these Render environment variables:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `DEMO_RECIPIENT_NUMBER` (E.164 format, such as `+91...`)

Never commit these values. If they are absent or delivery fails, FarmTrack saves an on-screen simulated notification so the presentation continues.

## Deploy to Render

1. Push this folder to a GitHub repository.
2. In Render, choose **New → Blueprint** and select the repository.
3. Render reads `render.yaml`.
4. Enter the requested environment variables.
5. Set `PUBLIC_BASE_URL` to the final `https://...onrender.com` address and redeploy.
6. Open `/track/TOM-001` on a phone and test the QR code.

Free Render services sleep after inactivity. Open the site several minutes before the presentation to wake it.

## Presentation flow

1. Show the public landing page.
2. Open tomato batch `TOM-001` and explain the journey timeline.
3. Scan its QR code with a phone.
4. Enter Presenter Mode.
5. Add a new checkpoint.
6. Send an SMS update to the verified phone.
7. Reopen the public tracking page to show the updated record.

