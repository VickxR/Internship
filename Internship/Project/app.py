from flask import Flask, render_template, request
import pymysql

app = Flask(__name__)

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="Vicky@3016",
        database="flask_db"
    )

@app.route('/')
def home():
    return render_template('register.html')

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

    try:
        sql = """
        INSERT INTO event_registrations
        (phone, name, email, college, technical_event, non_technical_event) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (phone, name, email, college, technical_event, non_technical_event))
        conn.commit()

        return "<h2>Registration Successful!</h2>"

    except pymysql.err.IntegrityError:
        return "<h2>You're Already Registered!!</h2>"

    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
