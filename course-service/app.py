import os
import psycopg2 # Placeholder: Replace with your actual database driver
from flask import Flask, jsonify, request

app = Flask(__name__)

# Environment variables - these values will be supplied by your Kubernetes Deployment
PROJECT_ID = os.environ.get("PROJECT_ID", "your-gcp-project-id") 
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1") 
DB_PORT = os.environ.get("DB_PORT", "5433") 
DB_NAME = os.environ.get("DB_NAME", "course_db") # Ensure this matches your Cloud SQL database name
DB_USER = os.environ.get("DB_USER", "course_user")
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

# --- Course Service Endpoints (Placeholder) ---
@app.route('/courses', methods=['GET'])
def get_courses():
    conn = init_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description, instructor FROM courses")
            courses = [{"id": row[0], "title": row[1], "description": row[2], "instructor": row[3]} for row in cursor.fetchall()]
            cursor.close()
            return jsonify(courses)
        except Exception as e:
            app.logger.error(f"Error fetching courses: {e}")
            return jsonify({"error": "Failed to fetch courses"}), 500
        finally:
            conn.close()
    return jsonify({"error": "Database connection failed"}), 500

@app.route('/courses/<int:course_id>', methods=['GET'])
def get_course_details(course_id):
    conn = init_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description, instructor FROM courses WHERE id = %s", (course_id,))
            course = cursor.fetchone()
            cursor.close()
            if course:
                return jsonify({"id": course[0], "title": course[1], "description": course[2], "instructor": course[3]})
            return jsonify({"message": "Course not found"}), 404
        except Exception as e:
            app.logger.error(f"Error fetching course details: {e}")
            return jsonify({"error": "Failed to fetch course details"}), 500
        finally:
            conn.close()
    return jsonify({"error": "Database connection failed"}), 500

# Add other course-related endpoints (e.g., POST for new courses)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

