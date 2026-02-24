from flask import Flask, render_template, request, send_file, session, url_for, redirect
import pymysql
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io
import os

app = Flask(__name__)
app.secret_key = os.environ.get("Flask_secret_key")

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password=os.environ.get("DB_PASS"),
        database="flask_db"
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, password))
        conn.commit()
        return render_template('signin.html')

    except pymysql.err.IntegrityError:
        return "<h3>User already exists</h3>"

    finally:
        conn.close()

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'GET':
        return render_template('signin.html')
    
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM users WHERE email=%s AND password=%s
    """, (email, password))

    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        return render_template('register.html')
    else:
        return "<h3>Invalid email or password</h3>"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin.html')

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM admin WHERE email=%s AND password=%s
    """, (email, password))

    admin = cursor.fetchone()

    if not admin:
        conn.close()
        return "<h3>Invalid admin credentials</h3>"

    
    cursor.execute("SELECT name, email, phone FROM users")
    users = cursor.fetchall()


    cursor.execute("""
        SELECT id, name, phone, email, college,
            technical_event, non_technical_event
        FROM event_registrations
    """)
    registrations = cursor.fetchall()


    conn.close()

    return render_template(
        'admin_dashboard.html',
        users=users,
        registrations=registrations
    )


@app.route('/')
def home():
    return render_template('signin.html')


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

    cursor.execute("""
        SELECT 1 FROM event_registrations
        WHERE email = %s OR phone = %s
    """, (email, phone))

    if cursor.fetchone():
        conn.close()
        return """
            <script>
                alert("You're already registered");
                window.location.href = "/";
            </script>
        """

    cursor.execute("""
        INSERT INTO event_registrations
        (phone, name, email, college, technical_event, non_technical_event)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (phone, name, email, college, technical_event, non_technical_event))

    conn.commit()
    conn.close()

    return render_template("success.html")


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
        pdf.setFillColorRGB(1.0, 0.95, 0.8)  
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        pdf.setFillColor(colors.black)

        pdf.setLineWidth(4)
        pdf.rect(30, 30, width - 60, height - 60)

        pdf.setLineWidth(1)
        pdf.rect(45, 45, width - 90, height - 90)

        
        pdf.setFont("Times-Bold", 20)
        pdf.drawCentredString(width / 2, height - 120,
                              "RAJALAKSHMI ENGINEERING COLLEGE")

        pdf.setFont("Times-Roman", 14)
        pdf.drawCentredString(width / 2, height - 150,
                              "(An Autonomous Institution)")

        naac_logo = os.path.join(app.root_path, "static", "naac.png")
        aicte_logo = os.path.join(app.root_path, "static", "AICTE-logo.jpg")
        sign1 = os.path.join(app.root_path, "static", "sign 1.png")
        sign2 = os.path.join(app.root_path, "static", "sign 2.png")

        pdf.drawImage(naac_logo, width - 200, height - 180,
                      width=100, height=80, mask='auto')

        pdf.drawImage(aicte_logo, 80, height - 180,
                      width=80, height=80, mask='auto')
        
        pdf.drawImage(sign1, 80, (height/2)/2,
                      width=80, height=80, mask='auto')
        
        pdf.drawImage(sign2, width-200, (height/2)/2,
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
        pdf.drawString(width - 200, 140, "Head of the Institution")

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

@app.route('/Logout')
def Logout():
    session.clear()
    return redirect(url_for('signin'))

@app.route('/Back')
def Back():
    session.clear()
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
