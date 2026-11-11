from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pymysql
import pymysql.cursors
import os
import time

app = Flask(__name__)
CORS(app)

# Connection details environment variables se aate hain (RDS ke liye)
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'notesdb'),
    'cursorclass': pymysql.cursors.DictCursor,
}


def get_db_connection():
    """Create a MySQL connection."""
    return pymysql.connect(**DB_CONFIG)


def init_db(retries=10, delay=3):
    """Create the notes table. Retries until the database is reachable."""
    for attempt in range(1, retries + 1):
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS notes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()
            conn.close()
            print('Database ready')
            return
        except Exception as e:
            print(f'DB not ready (attempt {attempt}/{retries}): {e}')
            time.sleep(delay)
    print('Could not connect to the database')


def note_to_dict(note):
    return {
        'id': note['id'],
        'content': note['content'],
        'created_at': note['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
    }


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/health')
def health():
    """Simple health check (load balancer ya testing ke liye)."""
    return jsonify({'status': 'ok'}), 200


@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Retrieve all notes from the database."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM notes ORDER BY created_at DESC, id DESC')
            notes = cur.fetchall()
        conn.close()
        return jsonify([note_to_dict(n) for n in notes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes', methods=['POST'])
def create_note():
    """Create a new note."""
    try:
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400

        content = data['content'].strip()

        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('INSERT INTO notes (content) VALUES (%s)', (content,))
            note_id = cur.lastrowid
            conn.commit()
            cur.execute('SELECT * FROM notes WHERE id = %s', (note_id,))
            note = cur.fetchone()
        conn.close()

        return jsonify(note_to_dict(note)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a note by ID."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('DELETE FROM notes WHERE id = %s', (note_id,))
            deleted = cur.rowcount
        conn.commit()
        conn.close()

        if deleted == 0:
            return jsonify({'error': 'Note not found'}), 404

        return jsonify({'message': 'Note deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# gunicorn ke andar bhi table ban jaye, is liye import par chalta hai
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG') == '1')