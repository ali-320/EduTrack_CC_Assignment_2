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
    db_password_file = os.environ.get("DB_PASSWORD_FILE")
    if db_password_file and os.path.exists(db_password_file):
        with open(db_password_file, 'r') as f:
            return f.read().strip()
    else:
        # Fallback for local testing or if CSI is not configured to mount as file
        # or if you want to explicitly fetch via API in other contexts
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

@app.route('/enrollments', methods=['POST'])
def create_enrollment():
    data = request.get_json()
    student_id = data.get('student_id')
    course_id = data.get('course_id')
    status = data.get('status', 'enrolled') # Default to 'enrolled' if not provided

    if not all([student_id, course_id]):
        return jsonify({"error": "Missing data"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO enrollments (student_id, course_id, status) VALUES (%s, %s, %s) RETURNING enrollment_id;",
            (student_id, course_id, status)
        )
        enrollment_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Enrollment created", "enrollment_id": enrollment_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/enrollments/<int:enrollment_id>', methods=['GET'])
def get_enrollment(enrollment_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT enrollment_id, student_id, course_id, enrollment_date, status FROM enrollments WHERE enrollment_id = %s;", (enrollment_id,))
        enrollment = cur.fetchone()
        if enrollment:
            return jsonify({
                "enrollment_id": enrollment[0],
                "student_id": enrollment[1],
                "course_id": enrollment[2],
                "enrollment_date": enrollment[3].isoformat(),
                "status": enrollment[4]
            }), 200
        return jsonify({"message": "Enrollment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/enrollments/<int:enrollment_id>', methods=['PUT'])
def update_enrollment(enrollment_id):
    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({"error": "Missing status"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE enrollments SET status = %s WHERE enrollment_id = %s;",
            (status, enrollment_id)
        )
        if cur.rowcount == 0:
            return jsonify({"message": "Enrollment not found"}), 404
        conn.commit()
        return jsonify({"message": "Enrollment updated successfully"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/enrollments/<int:enrollment_id>', methods=['DELETE'])
def delete_enrollment(enrollment_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM enrollments WHERE enrollment_id = %s;", (enrollment_id,))
        if cur.rowcount == 0:
            return jsonify({"message": "Enrollment not found"}), 404
        conn.commit()
        return jsonify({"message": "Enrollment deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
