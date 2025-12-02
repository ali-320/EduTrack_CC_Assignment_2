import os
from flask import Flask, jsonify, request
import psycopg2
from google.cloud import secretmanager

app = Flask(__name__)

# Configuration for Course Service
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1") # For local testing with proxy
DB_PORT = os.environ.get("DB_PORT", "5433")
DB_NAME = os.environ.get("DB_NAME", "course_db")
DB_USER = os.environ.get("DB_USER", "course_user")
SECRET_ID = os.environ.get("SECRET_ID", "course-db-password")
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

@app.route('/courses', methods=['POST'])
def create_course():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    instructor = data.get('instructor')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    price = data.get('price')

    if not title:
        return jsonify({"error": "Missing title"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO courses (title, description, instructor, start_date, end_date, price) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING course_id;""",
            (title, description, instructor, start_date, end_date, price)
        )
        course_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Course created", "course_id": course_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT course_id, title, description, instructor, start_date, end_date, price FROM courses WHERE course_id = %s;", (course_id,))
        course = cur.fetchone()
        if course:
            return jsonify({
                "course_id": course[0],
                "title": course[1],
                "description": course[2],
                "instructor": course[3],
                "start_date": course[4].isoformat() if course[4] else None,
                "end_date": course[5].isoformat() if course[5] else None,
                "price": float(course[6]) if course[6] is not None else None
            }), 200
        return jsonify({"message": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    instructor = data.get('instructor')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    price = data.get('price')

    if not title:
        return jsonify({"error": "Missing title"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """UPDATE courses SET title = %s, description = %s, instructor = %s, 
               start_date = %s, end_date = %s, price = %s WHERE course_id = %s;""",
            (title, description, instructor, start_date, end_date, price, course_id)
        )
        if cur.rowcount == 0:
            return jsonify({"message": "Course not found"}), 404
        conn.commit()
        return jsonify({"message": "Course updated successfully"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM courses WHERE course_id = %s;", (course_id,))
        if cur.rowcount == 0:
            return jsonify({"message": "Course not found"}), 404
        conn.commit()
        return jsonify({"message": "Course deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8081)))