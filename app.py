import os
import io
import csv
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openpyxl
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tanuku-drains-2026-secret')

# Database URL from Render
DATABASE_URL = os.environ.get('DATABASE_URL')

# Cloudinary config for photo uploads
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

def get_db_connection():
    # Force SSL mode for Render PostgreSQL
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn
def init_db():
    """Create tables and default users if they don't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                ward VARCHAR(10)
            )
        ''')
        
        # Drains table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS drains (
                id SERIAL PRIMARY KEY,
                drain_id VARCHAR(50),
                ward VARCHAR(10) NOT NULL,
                location TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                photo_url TEXT,
                work_type VARCHAR(100),
                work_date DATE,
                updated_by VARCHAR(50),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add default users - added ward29
        users = [
            ('admin', generate_password_hash('Tanuku@2026'), 'admin', None),
            ('ward11', generate_password_hash('Ward11@2026'), 'user', '11'),
            ('ward12', generate_password_hash('Ward12@2026'), 'user', '12'),
            ('ward29', generate_password_hash('Ward29@2026'), 'user', '29')
        ]
        
        for username, password_hash, role, ward in users:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, ward) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (username) DO NOTHING
            """, (username, password_hash, role, ward))
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database init error: {e}")
        # Don't crash the app if DB is temporarily unavailable
        pass

init_db()

@app.route('/')
def index():
    if 'username' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            session['ward'] = user['ward']
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if session.get('role') == 'admin':
        cur.execute("SELECT * FROM drains ORDER BY ward, drain_id")
    else:
        cur.execute("SELECT * FROM drains WHERE ward = %s ORDER BY drain_id", (session.get('ward'),))
    
    drains = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('dashboard.html', drains=drains)

@app.route('/upload_work/<int:drain_id>', methods=['GET', 'POST'])
def upload_work(drain_id):
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get drain details
    cur.execute("SELECT * FROM drains WHERE id = %s", (drain_id,))
    drain = cur.fetchone()
    
    # Check if user has access to this ward
    if session.get('role')!= 'admin' and drain['ward']!= session.get('ward'):
        flash('You do not have access to this drain')
        return redirect('/dashboard')
    
    if request.method == 'POST':
        work_type = request.form.get('work_type')
        status = request.form.get('status')
        photo_url = drain['photo_url'] # Keep old photo if no new upload
        
        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename!= '':
                try:
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(photo, folder="tanuku_drains")
                    photo_url = upload_result['secure_url']
                except Exception as e:
                    flash(f'Photo upload failed: {str(e)}')
                    return redirect(url_for('upload_work', drain_id=drain_id))
        
        # Update drain record
        cur.execute("""
            UPDATE drains 
            SET status = %s, photo_url = %s, work_type = %s, work_date = CURRENT_DATE, 
                updated_by = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, photo_url, work_type, session['username'], drain_id))
        
        conn.commit()
        cur.close()
        conn.close()
        flash('Work updated successfully')
        return redirect('/dashboard')
    
    cur.close()
    conn.close()
    return render_template('upload_work.html', drain=drain)

@app.route('/import_excel', methods=['GET', 'POST'])
def import_excel():
    if 'username' not in session or session.get('role')!= 'admin':
        return redirect('/login')
    
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            try:
                # Read Excel file
                wb = openpyxl.load_workbook(file)
                sheet = wb.active
                
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Clear old data
                cur.execute("DELETE FROM drains")
                
                count = 0
                # Skip header row, start from row 2
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    drain_id = str(row[0]) if row[0] else ''
                    ward = str(row[1]) if row[1] else ''
                    location = str(row[2]) if row[2] else ''
                    
                    if drain_id and ward: # Only insert if ID and ward exist
                        cur.execute("""
                            INSERT INTO drains (drain_id, ward, location, status) 
                            VALUES (%s, %s, %s, %s)
                        """, (drain_id, ward, location, 'Pending'))
                        count += 1
                
                conn.commit()
                cur.close()
                conn.close()
                flash(f'Successfully imported {count} drains from Excel')
                return redirect('/dashboard')
            except Exception as e:
                flash(f'Error importing Excel: {str(e)}')
                return redirect('/import_excel')
    
    return render_template('import_excel.html')

@app.route('/photo_report')
def photo_report():
    if 'username' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if session.get('role') == 'admin':
        cur.execute("""
            SELECT * FROM drains 
            WHERE photo_url IS NOT NULL AND photo_url!= '' 
            ORDER BY ward, work_date DESC
        """)
    else:
        cur.execute("""
            SELECT * FROM drains 
            WHERE ward = %s AND photo_url IS NOT NULL AND photo_url!= '' 
            ORDER BY work_date DESC
        """, (session.get('ward'),))
    
    drains = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('photo_report.html', drains=drains)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=False)
