"""Validate deployment settings without printing credentials or sending messages."""

import os
import re
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from twilio.rest import Client


load_dotenv()


def check_database():
    raw_url = os.getenv("DATABASE_URL", "")
    if raw_url.startswith("postgres://"):
        url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgresql://"):
        url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        url = raw_url
    engine = None
    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
        )
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar() == 1, "NONE"
    except Exception as error:
        return False, type(error).__name__
    finally:
        if engine:
            engine.dispose()


def check_twilio():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    try:
        account = Client(sid, token).api.accounts(sid).fetch()
        return account.status in {"active", "suspended"}, "NONE"
    except Exception as error:
        return False, type(error).__name__


def main():
    database_ok, database_error = check_database()
    twilio_ok, twilio_error = check_twilio()
    recipient_text = os.getenv("DEMO_RECIPIENT_NUMBERS") or os.getenv("DEMO_RECIPIENT_NUMBER", "")
    recipients = [number.strip() for number in recipient_text.replace(";", ",").split(",") if number.strip()]
    print("SUPABASE_CONNECTION:", "OK" if database_ok else "FAILED")
    print("SUPABASE_ERROR_TYPE:", database_error)
    print("TWILIO_AUTH:", "OK" if twilio_ok else "FAILED")
    print("TWILIO_ERROR_TYPE:", twilio_error)
    print("RECIPIENT_COUNT:", len(recipients))
    print("ALL_RECIPIENTS_E164:", bool(recipients) and all(re.fullmatch(r"\+[1-9]\d{7,14}", number) for number in recipients))
    return 0 if database_ok and twilio_ok else 1


if __name__ == "__main__":
    sys.exit(main())
