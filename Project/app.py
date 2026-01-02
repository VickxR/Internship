from flask import Flask, render_template, request, send_file
import pymysql
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io
import os

app = Flask(__name__)

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password=os.environ.get("DB_PASS"),
        database="flask_db"
    )

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('register.html')

# ---------------- REGISTER (FIXED LOGIC) ----------------
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    college = request.form['college']
    technical_event = request.form['technical_event']
    non_technical_event = request.form['non_technical_event']

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔹 CHECK DUPLICATE (PHONE OR EMAIL)
    cursor.execute("""
        SELECT 1 FROM event_registrations
        WHERE email = %s OR phone = %s
    """, (email, phone))

    already_exists = cursor.fetchone()

    if already_exists:
        conn.close()
        return """
            <script>
                alert("You're already registered");
                window.location.href = "/";
            </script>
        """
    # 🔹 INSERT IF NOT EXISTS
    cursor.execute("""
        INSERT INTO event_registrations
        (phone, name, email, college, technical_event, non_technical_event)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (phone, name, email, college, technical_event, non_technical_event))

    conn.commit()
    conn.close()

    return render_template("success.html")

# ---------------- CERTIFICATE PAGE ----------------
@app.route('/certificate', methods=['GET', 'POST'])
def certificate():
    if request.method == 'GET':
        return render_template('certificate.html')

    email = request.form['email']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, college, technical_event, non_technical_event
        FROM event_registrations WHERE email=%s 
    """, (email,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return "<h2>No registration found</h2>"

    name, college, tech_event, nontech_event = data

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    def draw_certificate(event_name):
        pdf.setFillColorRGB(1.0, 0.95, 0.8)   # light gold
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        pdf.setFillColor(colors.black)

        pdf.setLineWidth(4)
        pdf.rect(30, 30, width - 60, height - 60)

        pdf.setLineWidth(1)
        pdf.rect(45, 45, width - 90, height - 90)

        # Header
        pdf.setFont("Times-Bold", 20)
        pdf.drawCentredString(width / 2, height - 120,
                              "RAJALAKSHMI ENGINEERING COLLEGE")

        pdf.setFont("Times-Roman", 14)
        pdf.drawCentredString(width / 2, height - 150,
                              "(An Autonomous Institution)")

        naac_logo = os.path.join(app.root_path, "static", "naac.jpg")
        aicte_logo = os.path.join(app.root_path, "static", "AICTE-logo.jpg")

        pdf.drawImage(naac_logo, width - 200, height - 180,
                      width=100, height=80, mask='auto')

        pdf.drawImage(aicte_logo, 80, height - 180,
                      width=80, height=80, mask='auto')

        pdf.setFont("Times-Bold", 28)
        pdf.drawCentredString(width / 2, height - 260,
                              "CERTIFICATE OF PARTICIPATION")

        pdf.setFont("Times-Roman", 16)
        pdf.drawCentredString(width / 2, height - 320,
                              "This is to certify that")

        pdf.setFont("Times-Bold", 22)
        pdf.drawCentredString(width / 2, height - 360, name)

        pdf.setFont("Times-Roman", 16)
        pdf.drawCentredString(width / 2, height - 400,
                              "has successfully participated in")

        pdf.setFont("Times-Bold", 18)
        pdf.drawCentredString(width / 2, height - 440, event_name)

        pdf.setFont("Times-Roman", 14)
        pdf.drawCentredString(width / 2, height - 480,
                              f"Conducted by {college}")

        pdf.setFont("Times-Roman", 12)
        pdf.drawString(80, 140, "Program Coordinator")
        pdf.drawString(width - 250, 140, "Head of the Institution")

        pdf.showPage()

    if tech_event != "Not Interested":
        draw_certificate(tech_event)

    if nontech_event != "Not Interested":
        draw_certificate(nontech_event)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Certificates.pdf",
        mimetype="application/pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)
