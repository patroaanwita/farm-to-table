from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "tmp" / "pdfs" / "screens"
OUT = ROOT / "output" / "pdf" / "FarmTrack_Student_User_Manual.pdf"

GREEN = colors.HexColor("#173F35")
MID_GREEN = colors.HexColor("#75A843")
LIME = colors.HexColor("#CFE76B")
CREAM = colors.HexColor("#F5F1E7")
INK = colors.HexColor("#1E2C27")
MUTED = colors.HexColor("#68736E")
LINE = colors.HexColor("#DCE2DA")
WHITE = colors.white


def register_fonts():
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("Manual", str(regular)))
        pdfmetrics.registerFont(TTFont("Manual-Bold", str(bold)))
        return "Manual", "Manual-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", fontName=FONT_BOLD, fontSize=10, leading=13, textColor=LIME, alignment=TA_CENTER, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverTitle", fontName=FONT_BOLD, fontSize=30, leading=34, textColor=WHITE, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName=FONT, fontSize=12, leading=18, textColor=colors.HexColor("#D7E4DE"), alignment=TA_CENTER))
styles.add(ParagraphStyle(name="SectionKicker", fontName=FONT_BOLD, fontSize=8, leading=11, textColor=MID_GREEN, spaceAfter=4))
styles.add(ParagraphStyle(name="PageTitle", fontName=FONT_BOLD, fontSize=22, leading=27, textColor=GREEN, spaceAfter=8))
styles.add(ParagraphStyle(name="Lead", fontName=FONT, fontSize=11, leading=16, textColor=MUTED, spaceAfter=12))
styles.add(ParagraphStyle(name="BodyManual", fontName=FONT, fontSize=9.5, leading=14, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="BodySmall", fontName=FONT, fontSize=8, leading=11, textColor=MUTED))
styles.add(ParagraphStyle(name="StepTitle", fontName=FONT_BOLD, fontSize=10.5, leading=14, textColor=GREEN, spaceAfter=3))
styles.add(ParagraphStyle(name="StepBody", fontName=FONT, fontSize=8.8, leading=12.5, textColor=INK))
styles.add(ParagraphStyle(name="WhiteTitle", fontName=FONT_BOLD, fontSize=15, leading=19, textColor=WHITE))
styles.add(ParagraphStyle(name="WhiteBody", fontName=FONT, fontSize=9, leading=13, textColor=colors.HexColor("#D7E4DE")))


class PageLabel(Flowable):
    def __init__(self, number, title, body):
        super().__init__()
        self.number = str(number)
        self.title = title
        self.body = body
        self.width = 170 * mm
        self.height = 23 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(GREEN)
        c.roundRect(0, 0, 15 * mm, 15 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(LIME)
        c.setFont(FONT_BOLD, 15)
        c.drawCentredString(7.5 * mm, 5 * mm, self.number)
        title = Paragraph(self.title, styles["StepTitle"])
        body = Paragraph(self.body, styles["StepBody"])
        title.wrapOn(c, 148 * mm, 8 * mm)
        title.drawOn(c, 21 * mm, 13 * mm)
        body.wrapOn(c, 148 * mm, 13 * mm)
        body.drawOn(c, 21 * mm, 1 * mm)


def crop_image(src_name, out_name, crop_box):
    src = Image.open(SCREEN / src_name).convert("RGB")
    cropped = src.crop(crop_box)
    path = SCREEN / out_name
    cropped.save(path, quality=92)
    return path


def image_for_page(path, max_w=175 * mm, max_h=150 * mm):
    with Image.open(path) as img:
        width, height = img.size
    scale = min(max_w / width, max_h / height)
    return RLImage(str(path), width=width * scale, height=height * scale)


def header_footer(canvas, doc):
    page = canvas.getPageNumber()
    if page == 1:
        return
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 16 * mm, 190 * mm, 16 * mm)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10 * mm, "FarmTrack Student User Manual")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {page}")
    canvas.restoreState()


def screenshot_frame(path, caption, max_h=146 * mm):
    img = image_for_page(path, max_h=max_h)
    table = Table([[img], [Paragraph(caption, styles["BodySmall"]) ]], colWidths=[178 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LEFTPADDING", (0, 0), (-1, 0), 4),
        ("RIGHTPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("LEFTPADDING", (0, 1), (-1, 1), 7),
        ("RIGHTPADDING", (0, 1), (-1, 1), 7),
        ("TOPPADDING", (0, 1), (-1, 1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    return table


def title_block(kicker, title, lead):
    return [Paragraph(kicker.upper(), styles["SectionKicker"]), Paragraph(title, styles["PageTitle"]), Paragraph(lead, styles["Lead"])]


def make_pdf():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    home_top = crop_image("01-home.png", "01-home-top.jpg", (0, 0, 1056, 1180))
    track_top = crop_image("02-track.png", "02-track-top.jpg", (0, 0, 1056, 780))
    track_lower = crop_image("02-track.png", "02-track-lower.jpg", (0, 620, 1056, 1702))
    market_top = crop_image("03-markets.png", "03-markets-top.jpg", (0, 0, 1056, 1250))

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=23 * mm, title="FarmTrack Student User Manual", author="FarmTrack Team - Class 9")
    story = []

    cover_box = Table([[Paragraph("GRADE 9 - ROBOTICS, AUTOMATION & SMART MANUFACTURING", styles["CoverKicker"])], [Paragraph("FarmTrack<br/>Student User Manual", styles["CoverTitle"])], [Paragraph("A step-by-step guide to following vegetables from a Bengaluru farm, through the mandi, to the retailer and consumer.", styles["CoverSub"])], [Spacer(1, 14 * mm)], [Paragraph("Created for the FarmTrack team prototype", styles["CoverKicker"]) ]], colWidths=[170 * mm], rowHeights=[None, None, None, 45 * mm, None])
    cover_box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, 0), 20 * mm), ("BOTTOMPADDING", (0, -1), (-1, -1), 18 * mm), ("BOX", (0, 0), (-1, -1), 0, GREEN)]))
    story += [Spacer(1, 23 * mm), cover_box, Spacer(1, 12 * mm), Paragraph("PUBLIC WEBSITE", styles["SectionKicker"]), Paragraph("https://riddhi-farmtrack.onrender.com", styles["BodyManual"]), PageBreak()]

    story += title_block("1 - Understanding the project", "What does FarmTrack do?", "FarmTrack gives each vegetable batch a digital journey. A QR code opens the public record, while Presenter Mode lets the student add new checkpoints and send updates.")
    roles = [
        ["Stage", "Person", "What FarmTrack records"],
        ["Farm", "Farmer", "Crop, farm, harvest date, quantity and starting location"],
        ["Transport", "Driver or logistics team", "Movement, distance, time, temperature and handling notes"],
        ["Mandi", "Mandi trader", "Market name, receipt, quality, storage and purchase price"],
        ["Retailer", "Shop team", "Delivery, location, storage and selling price"],
        ["Consumer", "Shopper", "Reads the journey by scanning the QR code"],
    ]
    rt = Table([[Paragraph(str(cell), styles["StepTitle"] if r == 0 else styles["StepBody"]) for cell in row] for r, row in enumerate(roles)], colWidths=[28 * mm, 43 * mm, 99 * mm], repeatRows=1)
    rt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE), ("GRID", (0, 0), (-1, -1), .5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, CREAM]), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [rt, Spacer(1, 10 * mm), Paragraph("The sample batch travels from Nandi Fresh Farm in Doddaballapur to Bangalore Fruit & Vegetable APMC in Binnypet, and then to a retailer in Indiranagar.", styles["BodyManual"]), PageBreak()]

    story += title_block("2 - Public home page", "Start at the FarmTrack home page", "Anyone can open this page. No password is required for public tracking.")
    story += [screenshot_frame(home_top, "The home page introduces the project and shows the sample batch.", 130 * mm), Spacer(1, 7 * mm), PageLabel(1, "Open the website", "Enter the FarmTrack address on a phone or laptop."), PageLabel(2, "Choose the tomato batch", "Tap <b>Open sample batch</b> or scroll to TOM-001 and select <b>View full journey</b>."), PageBreak()]

    story += title_block("3 - Consumer tracking journey", "Read the batch summary", "The first part of the tracking page answers the shopper's most important questions immediately.")
    story += [screenshot_frame(track_top, "The summary shows age, total distance, current location and freshness score.", 128 * mm), Spacer(1, 6 * mm), PageLabel(1, "Check the batch identity", "Confirm the vegetable name and batch code TOM-001."), PageLabel(2, "Read the freshness information", "The score uses days since harvest and the latest recorded temperature as a simple project indicator."), PageLabel(3, "Check the origin", "The farmer panel shows who grew the produce and where the journey began."), PageBreak()]

    story += title_block("4 - Journey timeline", "Follow every checkpoint", "Read the timeline from top to bottom. Each checkpoint adds evidence about who handled the batch, where it went and how it was stored.")
    story += [screenshot_frame(track_lower, "The timeline includes the Bengaluru mandi checkpoint and the final retail delivery.", 154 * mm), Spacer(1, 5 * mm), Paragraph("Look for the Bangalore Fruit & Vegetable APMC checkpoint. It records receipt at Binnypet, the distance travelled, temperature and covered storage condition.", styles["BodyManual"]), PageBreak()]

    story += title_block("5 - Bengaluru mandi directory", "Choose the correct market", "The directory helps the presenter use a real Bengaluru-area market name when recording a mandi checkpoint.")
    story += [screenshot_frame(market_top, "FarmTrack includes official APMC and BBMP market names used for the prototype.", 145 * mm), Spacer(1, 5 * mm), Paragraph("For the tomato example, use <b>Bangalore Fruit & Vegetable APMC, Binnypet</b>. The directory also includes Yeshwanthpur APMC, K. R. Market, Doddaballapur APMC and Hoskote APMC.", styles["BodyManual"]), PageBreak()]

    story += title_block("6 - QR code and sharing", "Open the journey from a vegetable pack", "The QR label connects the physical crate or vegetable pack to the online batch record.")
    share_steps = [[Paragraph("1", styles["WhiteTitle"]), Paragraph("Open the camera", styles["StepTitle"]), Paragraph("Point a phone camera at the printed QR code.", styles["StepBody"])], [Paragraph("2", styles["WhiteTitle"]), Paragraph("Tap the detected link", styles["StepTitle"]), Paragraph("The phone opens the public TOM-001 tracking page.", styles["StepBody"])], [Paragraph("3", styles["WhiteTitle"]), Paragraph("Share if needed", styles["StepTitle"]), Paragraph("Use <b>Share by SMS</b> or <b>Copy tracking link</b>. Sharing does not change the batch record.", styles["StepBody"])]]
    st = Table(share_steps, colWidths=[14 * mm, 46 * mm, 110 * mm], rowHeights=[25 * mm] * 3)
    st.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), GREEN), ("BACKGROUND", (1, 0), (-1, -1), CREAM), ("GRID", (0, 0), (-1, -1), .5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    story += [st, Spacer(1, 9 * mm), Paragraph("Important: the QR code must contain the exact deployed Render address. If a QR code opens a Not Found page, check PUBLIC_BASE_URL and regenerate the QR image.", styles["BodyManual"]), PageBreak()]

    story += title_block("7 - Presenter Mode", "Unlock the demonstration controls", "Presenter Mode protects all actions that change data. The public tracking page remains open to everyone.")
    story += [screenshot_frame(SCREEN / "04-login.png", "Enter the value configured as ADMIN_PASSWORD. Do not use a GitHub, Supabase or Twilio password.", 95 * mm), Spacer(1, 8 * mm), PageLabel(1, "Select Presenter mode", "Use the link in the top navigation."), PageLabel(2, "Enter the project password", "Ask the supervising adult for the demonstration password. Keep it private."), PageLabel(3, "Open the control centre", "After login, choose a batch action: View, Add checkpoint or Send SMS."), PageBreak()]

    story += title_block("8 - Add a journey checkpoint", "Record what happened next", "Each form field explains one part of the supply-chain event. Use realistic information during the demonstration.")
    checkpoint_rows = [
        ["Field", "Example for the tomato batch"], ["Journey stage", "At mandi"], ["Date and time", "Time the mandi accepted the lot"], ["Location", "Bangalore Fruit & Vegetable APMC, Binnypet"], ["Distance", "Distance from the previous checkpoint"], ["Handled by", "Mandi trader"], ["Temperature", "22 C"], ["Storage", "Covered mandi platform"], ["Produce received?", "Yes, accepted"], ["Purchase price", "Prototype value in rupees per kg"], ["Handling notes", "Lot received, weighed and quality checked"],
    ]
    ct = Table([[Paragraph(c, styles["StepTitle"] if r == 0 else styles["StepBody"]) for c in row] for r, row in enumerate(checkpoint_rows)], colWidths=[52 * mm, 118 * mm], repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE), ("GRID", (0, 0), (-1, -1), .5, LINE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, CREAM]), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [ct, Spacer(1, 7 * mm), Paragraph("After saving, reopen the public tracking page. The new event should appear at the bottom of the timeline, and the current status should match the latest stage.", styles["BodyManual"]), PageBreak()]

    story += title_block("9 - Send an SMS update", "Notify a verified demonstration phone", "Twilio trial accounts send only to numbers verified in Twilio. FarmTrack masks the numbers in Presenter Mode.")
    story += [PageLabel(1, "Choose a batch", "Use TOM-001 for the prepared demonstration."), PageLabel(2, "Select a masked phone number", "Choose one of the verified recipients. Full phone numbers should never appear in screenshots or presentation slides."), PageLabel(3, "Select Send SMS", "FarmTrack sends the current status and public tracking link through Twilio."), PageLabel(4, "Open the message", "The recipient taps the link and sees the same public journey page."), Spacer(1, 7 * mm)]
    warning = Table([[Paragraph("TRIAL ACCOUNT RULE", styles["SectionKicker"]), Paragraph("Every recipient must be verified in Twilio before testing. If delivery fails, FarmTrack still saves a demonstration notification in the activity log.", styles["BodyManual"]) ]], colWidths=[42 * mm, 128 * mm])
    warning.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM), ("BOX", (0, 0), (-1, -1), 1, MID_GREEN), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story += [warning, PageBreak()]

    story += title_block("10 - Presentation-day checklist", "A simple demonstration script", "Practice this sequence once on the actual phone and internet connection before presenting.")
    checklist = [
        ("Before school", "Wake the free Render service by opening the site. Confirm TOM-001 loads."),
        ("Introduce the problem", "Explain that shoppers usually cannot see harvest date, distance or handling history."),
        ("Show the solution", "Open the home page and explain QR tracking, Supabase storage and Twilio updates."),
        ("Scan the QR", "Open the consumer journey on a phone and point out freshness, handlers and mandi."),
        ("Add a checkpoint", "Use Presenter Mode to record one new supply-chain event."),
        ("Send the update", "Send an SMS to one verified phone and open its tracking link."),
        ("Use the backup", "If school internet fails, show saved screenshots and explain the same steps."),
    ]
    for i, (title, body) in enumerate(checklist, 1):
        story.append(PageLabel(i, title, body))
        story.append(Spacer(1, 2 * mm))
    story += [Spacer(1, 5 * mm), Paragraph("Never show the .env file, database password, Twilio token or full recipient numbers during the presentation.", styles["BodyManual"])]

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUT)


if __name__ == "__main__":
    make_pdf()
