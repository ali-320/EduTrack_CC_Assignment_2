import os
import psycopg2 # Placeholder: Replace with your actual database driver
from flask import Flask, jsonify, request

app = Flask(__name__)

# Environment variables - these values will be supplied by your Kubernetes Deployment
PROJECT_ID = os.environ.get("PROJECT_ID", "your-gcp-project-id") 
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1") 
DB_PORT = os.environ.get("DB_PORT", "5434") 
DB_NAME = os.environ.get("DB_NAME", "enrollment_db") # Ensure this matches your Cloud SQL database name
DB_USER = os.environ.get("DB_USER", "enrollment_user")
DB_PASSWORD_FILE = os.environ.get("DB_PASSWORD_FILE") # Path to mounted secret file

def get_db_password():
    """
    Retrieves the database password from the mounted file.
    This function expects DB_PASSWORD_FILE to be set and the file to exist.
    """
    if DB_PASSWORD_FILE and os.path.exists(DB_PASSWORD_FILE):
        try:
            with open(DB_PASSWORD_FILE, 'r') as f:
                return f.read().strip()
        except Exception as e:
            app.logger.error(f"Error reading DB password file {DB_PASSWORD_FILE}: {e}")
            return None
    else:
        app.logger.error(f"DB_PASSWORD_FILE environment variable not set or file not found at {DB_PASSWORD_FILE}")
        return None

def init_db_connection():
    """Initializes and returns a database connection."""
    db_password = get_db_password()
    if not db_password:
        app.logger.error("Database password not retrieved. Cannot connect to DB.")
        return None

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=db_password,
        )
        app.logger.info("Successfully connected to the database.")
        return conn
    except Exception as e:
        app.logger.error(f"Error connecting to database '{DB_NAME}' at {DB_HOST}:{DB_PORT} for user '{DB_USER}': {e}")
        return None

# --- Health Check Endpoint ---
@app.route('/')
def health_check():
    """
    Simple health check endpoint for Load Balancer.
    Returns 200 OK if the application is running.
    """
    app.logger.debug("Health check requested.")
    return "OK", 200

# --- Enrollment Service Endpoints (Placeholder) ---
@app.route('/enrollments', methods=['POST'])
def enroll_student():
    data = request.get_json()
    student_id = data.get('student_id')
    course_id = data.get('course_id')

    if not student_id or not course_id:
        return jsonify({"error": "student_id and course_id are required"}), 400

    conn = init_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Basic validation: check if student and course exist (optional, would use actual service calls in microservices)
            # For simplicity, assuming they exist for this placeholder
            cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s) RETURNING id", (student_id, course_id))
            enrollment_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return jsonify({"id": enrollment_id, "student_id": student_id, "course_id": course_id}), 201
        except Exception as e:
            app.logger.error(f"Error enrolling student: {e}")
            conn.rollback()
            return jsonify({"error": "Failed to enroll student"}), 500
        finally:
            conn.close()
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/enrollments/<int:student_id>', methods=['GET'])
def get_student_enrollments(student_id):
    conn = init_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, course_id FROM enrollments WHERE student_id = %s", (student_id,))
            enrollments = [{"id": row[0], "course_id": row[1]} for row in cursor.fetchall()]
            cursor.close()
            return jsonify(enrollments)
        except Exception as e:
            app.logger.error(f"Error fetching enrollments: {e}")
            return jsonify({"error": "Failed to fetch enrollments"}), 500
        finally:
            conn.close()
    return jsonify({"error": "Database connection failed"}), 500

# Add other enrollment-related endpoints

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

