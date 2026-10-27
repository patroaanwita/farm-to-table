import io
import os
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from urllib.parse import quote

import qrcode
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect, text
from twilio.rest import Client

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-school-demo-key")

database_url = os.getenv("DATABASE_URL", "sqlite:///farmtrack.sqlite3")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)

BENGALURU_MARKETS = [
    {"name": "Bangalore Fruit & Vegetable APMC", "short_name": "Bangalore F&V APMC", "location": "Agrahara Tank Bund Road, Binnypet, Bengaluru 560023", "produce": "Beans, brinjal, cabbage, carrot, grapes, mango, orange and tomato", "type": "APMC mandi"},
    {"name": "Bangalore APMC, Yeshwanthpur", "short_name": "Yeshwanthpur APMC", "location": "Mahatma Gandhi Complex, Yeshwanthpur, Bengaluru 560022", "produce": "Onion, potato, coconut, grains, pulses and spices", "type": "APMC mandi"},
    {"name": "K. R. Market", "short_name": "K. R. Market", "location": "Chamarajpet, Bengaluru 560002", "produce": "City fruit, vegetable and flower market", "type": "BBMP public market"},
    {"name": "Doddaballapur APMC", "short_name": "Doddaballapur APMC", "location": "Doddaballapur, Bengaluru Rural 561203", "produce": "Leafy vegetables, maize, ragi and rice", "type": "APMC mandi"},
    {"name": "Hoskote APMC", "short_name": "Hoskote APMC", "location": "T. G. Extension, Hoskote, Bengaluru Rural", "produce": "Local agricultural produce and ragi", "type": "APMC mandi"},
]


class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    produce_name = db.Column(db.String(80), nullable=False)
    variety = db.Column(db.String(80), nullable=False, default="")
    farm_name = db.Column(db.String(120), nullable=False)
    farmer_name = db.Column(db.String(120), nullable=False)
    origin = db.Column(db.String(160), nullable=False)
    harvest_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(60), nullable=False, default="Harvested")
    notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    events = db.relationship(
        "JourneyEvent", backref="batch", lazy=True, cascade="all, delete-orphan", order_by="JourneyEvent.event_time"
    )
    notifications = db.relationship(
        "Notification", backref="batch", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def total_distance(self):
        return round(sum(event.distance_km or 0 for event in self.events), 1)

    @property
    def latest_location(self):
        return self.events[-1].location if self.events else self.origin

    @property
    def freshness(self):
        days = (date.today() - self.harvest_date).days
        if days <= 2:
            return "Very fresh"
        if days <= 5:
            return "Fresh"
        return "Check before use"

    @property
    def days_since_harvest(self):
        return max(0, (date.today() - self.harvest_date).days)

    @property
    def freshness_score(self):
        latest_temperature = next((event.temperature_c for event in reversed(self.events) if event.temperature_c is not None), 22)
        return max(35, round(100 - min(self.days_since_harvest * 9, 54) - max(0, latest_temperature - 18) * 1.5))

    @property
    def handling_count(self):
        return len({event.handled_by.strip().lower() for event in self.events if event.handled_by.strip()})


class JourneyEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False, index=True)
    stage = db.Column(db.String(60), nullable=False)
    location = db.Column(db.String(160), nullable=False)
    event_time = db.Column(db.DateTime, nullable=False)
    distance_km = db.Column(db.Float, nullable=False, default=0)
    handled_by = db.Column(db.String(120), nullable=False, default="")
    notes = db.Column(db.Text, nullable=False, default="")
    market_name = db.Column(db.String(160), nullable=False, default="")
    temperature_c = db.Column(db.Float, nullable=True)
    storage_condition = db.Column(db.String(120), nullable=False, default="")
    received_ok = db.Column(db.Boolean, nullable=True)
    purchase_price_per_kg = db.Column(db.Float, nullable=True)
    selling_price_per_kg = db.Column(db.Float, nullable=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batch.id"), nullable=False, index=True)
    recipient_masked = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=False)
    delivery_status = db.Column(db.String(40), nullable=False)
    provider_id = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            flash("Please enter the demonstration password.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def public_base_url():
    return os.getenv("PUBLIC_BASE_URL", request.url_root.rstrip("/")).rstrip("/")


def mask_number(number):
    if not number:
        return "Demo phone"
    return f"{number[:3]} {'•' * max(4, len(number) - 7)}{number[-4:]}"


def demo_recipients():
    raw = os.getenv("DEMO_RECIPIENT_NUMBERS") or os.getenv("DEMO_RECIPIENT_NUMBER", "")
    return [number.strip() for number in raw.replace(";", ",").split(",") if number.strip()]


def seed_demo_data():
    existing = Batch.query.filter_by(code="TOM-001").first()
    if existing and existing.origin == "Sohna, Haryana":
        db.session.delete(existing)
        db.session.commit()
    elif existing:
        return

    today = date.today()
    batch = Batch(
        code="TOM-001",
        produce_name="Tomatoes",
        variety="Pusa Ruby",
        farm_name="Nandi Fresh Farm",
        farmer_name="Meera Gowda",
        origin="Doddaballapur, Bengaluru Rural",
        harvest_date=today - timedelta(days=1),
        quantity="24 crates (480 kg)",
        status="At local market",
        notes="A demonstration batch created for the Grade 9 FarmTrack prototype.",
    )
    db.session.add(batch)
    db.session.flush()

    start = datetime.combine(today - timedelta(days=1), datetime.min.time()).replace(hour=6, minute=30)
    events = [
        JourneyEvent(batch_id=batch.id, stage="Harvested", location="Nandi Fresh Farm, Doddaballapur", event_time=start, distance_km=0, handled_by="Farm team", notes="Picked in the cool morning hours.", temperature_c=19, storage_condition="Shaded harvest crates"),
        JourneyEvent(batch_id=batch.id, stage="Washed & sorted", location="Farm packing shed, Doddaballapur", event_time=start + timedelta(hours=2), distance_km=1.5, handled_by="Quality team", notes="Washed, quality checked and sorted.", temperature_c=20, storage_condition="Ventilated packing shed"),
        JourneyEvent(batch_id=batch.id, stage="Packed", location="Doddaballapur collection point", event_time=start + timedelta(hours=4), distance_km=6.5, handled_by="Collection team", notes="Packed in ventilated, reusable crates.", temperature_c=21, storage_condition="Reusable ventilated crates", received_ok=True, purchase_price_per_kg=24),
        JourneyEvent(batch_id=batch.id, stage="At mandi", location="Bangalore Fruit & Vegetable APMC, Binnypet", market_name="Bangalore Fruit & Vegetable APMC", event_time=start + timedelta(hours=7), distance_km=39, handled_by="Mandi trader", notes="Lot received, weighed and quality checked at the mandi.", temperature_c=22, storage_condition="Covered mandi platform", received_ok=True, purchase_price_per_kg=28),
        JourneyEvent(batch_id=batch.id, stage="Delivered", location="Neighbourhood retailer, Indiranagar", event_time=start + timedelta(days=1, hours=2), distance_km=9, handled_by="Retail shop team", notes="Received and placed on the fresh-produce shelf.", temperature_c=20, storage_condition="Cool display shelf", received_ok=True, selling_price_per_kg=38),
    ]
    db.session.add_all(events)
    db.session.commit()


def upgrade_demo_schema():
    """Add new worksheet fields to an earlier local prototype database."""
    if "journey_event" not in inspect(db.engine).get_table_names():
        return
    existing = {column["name"] for column in inspect(db.engine).get_columns("journey_event")}
    additions = {
        "market_name": "VARCHAR(160) NOT NULL DEFAULT ''",
        "temperature_c": "FLOAT",
        "storage_condition": "VARCHAR(120) NOT NULL DEFAULT ''",
        "received_ok": "BOOLEAN",
        "purchase_price_per_kg": "FLOAT",
        "selling_price_per_kg": "FLOAT",
    }
    for column, definition in additions.items():
        if column not in existing:
            db.session.execute(text(f"ALTER TABLE journey_event ADD COLUMN {column} {definition}"))
    db.session.commit()


@app.context_processor
def template_helpers():
    return {"current_year": date.today().year, "bengaluru_markets": BENGALURU_MARKETS}


@app.route("/")
def index():
    batches = Batch.query.order_by(Batch.created_at.desc()).all()
    total_distance = sum(batch.total_distance for batch in batches)
    event_count = JourneyEvent.query.count()
    return render_template("index.html", batches=batches, total_distance=total_distance, event_count=event_count)


@app.route("/track/<code>")
def track(code):
    batch = Batch.query.filter(func.lower(Batch.code) == code.lower()).first_or_404()
    track_url = f"{public_base_url()}{url_for('track', code=batch.code)}"
    sms_body = quote(f"FarmTrack: View the journey of {batch.produce_name} batch {batch.code}: {track_url}")
    return render_template("track.html", batch=batch, track_url=track_url, sms_body=sms_body)


@app.route("/markets")
def markets():
    return render_template("markets.html", markets=BENGALURU_MARKETS)


@app.route("/qr/<code>.png")
def qr_code(code):
    batch = Batch.query.filter(func.lower(Batch.code) == code.lower()).first_or_404()
    target = f"{public_base_url()}{url_for('track', code=batch.code)}"
    qr = qrcode.QRCode(version=4, box_size=10, border=3)
    qr.add_data(target)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#153b2f", back_color="white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", download_name=f"{batch.code}-qr.png")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        configured = os.getenv("ADMIN_PASSWORD", "farmtrack9")
        if request.form.get("password") == configured:
            session["admin"] = True
            flash("Demonstration controls unlocked.", "success")
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("That password was not correct.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have left demonstration mode.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    batches = Batch.query.order_by(Batch.created_at.desc()).all()
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(8).all()
    recipients = [{"value": number, "label": mask_number(number)} for number in demo_recipients()]
    return render_template("admin.html", batches=batches, notifications=notifications, recipients=recipients)


@app.route("/admin/batches/new", methods=["GET", "POST"])
@admin_required
def new_batch():
    if request.method == "POST":
        code = request.form["code"].strip().upper()
        if Batch.query.filter_by(code=code).first():
            flash("That batch code already exists.", "error")
            return render_template("batch_form.html")
        try:
            harvested = date.fromisoformat(request.form["harvest_date"])
        except ValueError:
            flash("Please enter a valid harvest date.", "error")
            return render_template("batch_form.html")
        batch = Batch(
            code=code,
            produce_name=request.form["produce_name"].strip(),
            variety=request.form.get("variety", "").strip(),
            farm_name=request.form["farm_name"].strip(),
            farmer_name=request.form["farmer_name"].strip(),
            origin=request.form["origin"].strip(),
            harvest_date=harvested,
            quantity=request.form["quantity"].strip(),
            status="Harvested",
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(JourneyEvent(batch_id=batch.id, stage="Harvested", location=batch.origin, event_time=datetime.now(), distance_km=0, handled_by=batch.farmer_name, notes="Batch entered into FarmTrack."))
        db.session.commit()
        flash(f"Batch {batch.code} created and QR code is ready.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("batch_form.html")


@app.route("/admin/batches/<int:batch_id>/events/new", methods=["GET", "POST"])
@admin_required
def new_event(batch_id):
    batch = db.get_or_404(Batch, batch_id)
    if request.method == "POST":
        try:
            event_time = datetime.fromisoformat(request.form["event_time"])
            distance = max(0, float(request.form.get("distance_km", 0)))
        except ValueError:
            flash("Check the date, time and distance values.", "error")
            return render_template("event_form.html", batch=batch)
        event = JourneyEvent(
            batch_id=batch.id,
            stage=request.form["stage"],
            location=request.form["location"].strip(),
            event_time=event_time,
            distance_km=distance,
            handled_by=request.form.get("handled_by", "").strip(),
            notes=request.form.get("notes", "").strip(),
            market_name=request.form.get("market_name", "").strip(),
            temperature_c=float(request.form["temperature_c"]) if request.form.get("temperature_c") else None,
            storage_condition=request.form.get("storage_condition", "").strip(),
            received_ok=request.form.get("received_ok") == "yes" if request.form.get("received_ok") else None,
            purchase_price_per_kg=float(request.form["purchase_price_per_kg"]) if request.form.get("purchase_price_per_kg") else None,
            selling_price_per_kg=float(request.form["selling_price_per_kg"]) if request.form.get("selling_price_per_kg") else None,
        )
        batch.status = request.form["stage"]
        db.session.add(event)
        db.session.commit()
        flash(f"Journey updated: {event.stage} at {event.location}.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("event_form.html", batch=batch, default_time=datetime.now().strftime("%Y-%m-%dT%H:%M"))


@app.post("/admin/batches/<int:batch_id>/notify")
@admin_required
def notify(batch_id):
    batch = db.get_or_404(Batch, batch_id)
    allowed_recipients = demo_recipients()
    recipient = request.form.get("recipient", "").strip()
    if not recipient and len(allowed_recipients) == 1:
        recipient = allowed_recipients[0]
    if recipient not in allowed_recipients:
        flash("Choose a configured demonstration recipient.", "error")
        return redirect(url_for("admin_dashboard"))
    track_url = f"{public_base_url()}{url_for('track', code=batch.code)}"
    message = f"FarmTrack: {batch.produce_name} batch {batch.code} is now {batch.status}. Track its journey: {track_url}"
    status = "Simulated"
    provider_id = None

    credentials = (
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
        os.getenv("TWILIO_PHONE_NUMBER"),
        recipient,
    )
    if all(credentials):
        try:
            sent = Client(credentials[0], credentials[1]).messages.create(
                body=message, from_=credentials[2], to=recipient
            )
            status = sent.status or "Queued"
            provider_id = sent.sid
            flash(f"SMS queued for {mask_number(recipient)}.", "success")
        except Exception:
            app.logger.exception("Twilio message could not be sent")
            status = "Failed — saved as demo"
            flash("SMS could not be delivered, but the demonstration notification was saved.", "error")
    else:
        flash("Demo notification saved. Add Twilio environment variables to send a real SMS.", "info")

    db.session.add(Notification(batch_id=batch.id, recipient_masked=mask_number(recipient), message=message, delivery_status=status, provider_id=provider_id))
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/health")
def health():
    return {"status": "ok"}


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


with app.app_context():
    db.create_all()
    upgrade_demo_schema()
    seed_demo_data()


if __name__ == "__main__":
    app.run(debug=True)

