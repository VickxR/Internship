from flask import Flask, render_template, request, send_file, session, redirect, url_for, flash
from flask_bcrypt import Bcrypt
import pymysql
from pymysql.cursors import DictCursor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors 
import io, os

app = Flask(__name__)
app.secret_key = os.environ.get("Flask_secret_key", "dev_secret_key")

bcrypt = Bcrypt(app)

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password=os.environ.get("DB_PASS"),
        database="flask_db",
        cursorclass=DictCursor
    )

def admin_required():
    return session.get('role') in ['organizer', 'admin', 'hod']

# ---------------- HOME (UPDATED) ----------------
@app.route('/')
def home():
    return render_template('user/home.html')

# ---------------- STATIC PAGES (ADDED) ----------------
@app.route('/about')
def about():
    return render_template('user/about.html')

@app.route('/domains')
def domains():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""SELECT name,description, start_date, end_date,
                   event_time, venue, entry_fee, team_capacity
                    FROM events WHERE status = 1 and category = 'technical'""")
    technical_events = cursor.fetchall()

    cursor.execute("""SELECT name,description, start_date, end_date,
                   event_time, venue, entry_fee, team_capacity
                    FROM events WHERE status = 1 and category = 'non-technical'""")
    non_technical_events = cursor.fetchall()
    conn.close()
    
    return render_template('user/domains.html', 
        technical_events=technical_events, 
        non_technical_events=non_technical_events)

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('user/signup.html')

    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone, password, role)
            VALUES (%s, %s, %s, %s, 'student')
        """, (name, email, phone, hashed_password))
        conn.commit()
        return redirect(url_for('signin'))

    except pymysql.err.IntegrityError:
        return "<h3>User already exists</h3>"

    finally:
        conn.close()

# ---------------- SIGNIN ----------------
@app.route('/signin', methods=['GET', 'POST'])
def signin():

    next_page = request.form.get('next')

    if request.method == 'GET':
        return render_template('user/signin.html')

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password, role FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user['password'], password):

        session['user_id'] = user['id']
        session['role'] = user['role']

        if user['role'] in ['organizer', 'admin', 'hod']:
            return redirect(url_for('admin_dashboard'))

        if next_page == 'register':
            return redirect(url_for('register'))

        return redirect(url_for('home'))

    flash("Invalid Email or Password", "danger")
    return render_template('user/signin.html')

# ---------------- ADMIN DASHBOARD ----------------

@app.route('/prizes')
def prizes():
    return render_template('user/prizes.html')

@app.route('/faq')
def faq():
    return render_template('user/faq.html')

@app.route('/admin/users')
def admin_users():
    if not admin_required():
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, email, phone FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin/users.html', users=users)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('signin'))

    if request.method == 'GET':
        return render_template('admin/home.html')

# <----------------- admin_analytics ----------->
@app.route('/admin/analytics')
def admin_analytics():
    if not admin_required():
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT technical_event AS event_name, COUNT(*) AS count
        FROM event_registrations
        WHERE technical_event != 'Not Interested'
        GROUP BY technical_event
    """)
    tech_counts = cursor.fetchall()

    cursor.execute("""
        SELECT non_technical_event AS event_name, COUNT(*) AS count
        FROM event_registrations
        WHERE non_technical_event != 'Not Interested'
        GROUP BY non_technical_event
    """)
    nontech_counts = cursor.fetchall()

    conn.close()

    return render_template(
        'admin/analytics.html',
        tech_counts=tech_counts,
        nontech_counts=nontech_counts
    )

# -------------------- ADMIN EVENTS ----------------
@app.route('/admin/events')
def admin_events():
    if not admin_required():
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, category, description, start_date, end_date, event_time,
               venue, entry_fee, team_capacity, created_by, created_at
        FROM events
    """)
    events = cursor.fetchall()
    conn.close()

    return render_template('admin/events.html', events=events)


# ---------------- EDIT EVENT ----------------
@app.route('/admin/event/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'user_id' not in session or session.get('role') != 'organizer':
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        cursor.execute("""
            UPDATE events SET
                name=%s,
                category=%s,
                description=%s,
                start_date=%s,
                end_date=%s,
                event_time=%s,
                venue=%s,
                entry_fee=%s,
                team_capacity=%s
            WHERE id=%s
        """, (
            request.form['name'],
            request.form['category'],
            request.form['description'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['event_time'],
            request.form['venue'],
            request.form['entry_fee'],
            request.form['team_capacity'],
            event_id
        ))

        conn.commit()
        conn.close()
        return redirect(url_for('events'))

    cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
    event = cursor.fetchone()
    conn.close()

    return render_template('admin/edit_event.html', event=event)


#---------------- ADMIN EVENT MANAGEMENT ----------------
#----------------ADD EVENT ----------------
@app.route('/admin/event/add', methods=['GET','POST'])
def admin_add_event():
    if not admin_required():
        return redirect(url_for('signin'))

    if request.method == 'GET':
        return render_template('admin/add_event.html')
    
    data = request.form
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events
        (name, category, description, start_date, end_date, event_time, venue, entry_fee, team_capacity, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data.get('name'), data.get('category'), data.get('description'),
        data.get('start_date'), data.get('end_date'), data.get('event_time'), data.get('venue'),
        data.get('entry_fee'), data.get('team_capacity'), session['user_id']
    ))

    conn.commit()
    conn.close()
    flash("Event added successfully", "success")
    return redirect(url_for('events'))


#---------------- UPDATE EVENT ----------------
@app.route('/admin/event/update/<int:event_id>', methods=['POST'])
def admin_update_event(event_id):
    if not admin_required():
        return redirect(url_for('signin'))

    data = request.form
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE events SET
        name=%s, category=%s, description=%s,
        start_date=%s, end_date=%s, event_time=%s,
        venue=%s, entry_fee=%s, team_capacity=%s
        WHERE id=%s
    """, (
        data['name'], data['category'], data['description'],
        data['start_date'], data['end_date'], data['event_time'],
        data['venue'], data['entry_fee'], data['team_capacity'],
        event_id
    ))

    conn.commit()
    conn.close()
    return redirect(url_for('events'))

# ---------------- DELETE EVENT ----------------
@app.route('/admin/event/delete/<int:event_id>')
def admin_delete_event(event_id):
    if not admin_required():
        flash("Unauthorized access", "danger")
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM events WHERE id=%s", (event_id,))
    conn.commit()
    conn.close()

    flash("Event deleted successfully", "success")
    return redirect(url_for('events'))

# ---------------- EVENT REGISTRATION ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    
    if request.method == 'GET':
        return render_template('user/Register.html')
    
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
        WHERE email=%s OR phone=%s
    """, (email, phone))

    if cursor.fetchone():
        conn.close()
        return "<script>alert('Already registered');location.href='/'</script>"

    cursor.execute("""
        INSERT INTO event_registrations
        (phone, name, email, college, technical_event, non_technical_event)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (phone, name, email, college, technical_event, non_technical_event))

    conn.commit()
    conn.close()

    return render_template("user/success.html")

# ---------------- CERTIFICATE ----------------
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

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
