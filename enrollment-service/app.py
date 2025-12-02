import os
from flask import Flask, jsonify, request
import psycopg2
from google.cloud import secretmanager

app = Flask(__name__)

# Configuration for Enrollment Service
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1") # For local testing with proxy
DB_PORT = os.environ.get("DB_PORT", "5434")
DB_NAME = os.environ.get("DB_NAME", "enrollment_db")
DB_USER = os.environ.get("DB_USER", "enrollment_user")
SECRET_ID = os.environ.get("SECRET_ID", "enrollment-db-password")
PROJECT_ID = os.environ.get("PROJECT_ID", "edutrack-cc-ass-2")

def get_db_password():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_db_connection():
    db_password = get_db_password()
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=db_password
    )
    return conn

@app.route('/students', methods=['POST'])
def create_student():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')

    if not all([first_name, last_name, email]):
        return jsonify({"error": "Missing data"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (first_name, last_name, email) VALUES (%s, %s, %s) RETURNING student_id;",
            (first_name, last_name, email)
        )
        student_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Student created", "student_id": student_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id, first_name, last_name, email, registration_date FROM students WHERE student_id = %s;", (student_id,))
        student = cur.fetchone()
        if student:
            return jsonify({
                "student_id": student[0],
                "first_name": student[1],
                "last_name": student[2],
                "email": student[3],
                "registration_date": student[4].isoformat()
            }), 200
        return jsonify({"message": "Student not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# Add UPDATE and DELETE endpoints similarly

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
