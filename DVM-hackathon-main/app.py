from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# Database setup
def init_db():
    if not os.path.exists('users.db'):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE users (
            username TEXT PRIMARY KEY,
            full_name TEXT,
            school_name TEXT,
            class TEXT,
            roll_no TEXT,
            password TEXT,
            phone_no TEXT,
            email TEXT,
            birthdate TEXT
        )''')
        c.execute('''CREATE TABLE teams (
            team_name TEXT PRIMARY KEY,
            code TEXT,
            submission_time TEXT
        )''')
        c.execute('''CREATE TABLE hackathon_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            team_name TEXT,
            code TEXT,
            FOREIGN KEY (username) REFERENCES users (username),
            FOREIGN KEY (team_name) REFERENCES teams (team_name)
        )''')
        c.execute('''CREATE TABLE credits (
            username TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            last_update REAL DEFAULT 0,
            FOREIGN KEY (username) REFERENCES users (username)
        )''')
        c.execute('''CREATE TABLE rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            voucher TEXT,
            redeemed_at TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )''')
        conn.commit()
        conn.close()

# Initialize database
init_db()

def generate_username(full_name, birthdate):
    lower_name = full_name.lower().replace(' ', '')
    birthdate_formatted = birthdate.replace('-', '')  # Remove hyphens (YYYY-MM-DD to YYYYMMDD)
    return f"{lower_name}{birthdate_formatted}"

@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        school_name = request.form['school_name']
        class_name = request.form['class']
        roll_no = request.form['roll_no']
        password = request.form['password']
        phone_no = request.form['phone_no']
        email = request.form['email']
        birthdate = request.form['birthdate']
        username = generate_username(full_name, birthdate)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO users (username, full_name, school_name, class, roll_no, password, phone_no, email, birthdate)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (username, full_name, school_name, class_name, roll_no, password, phone_no, email, birthdate))
            # Add credits row
            now = datetime.datetime.now().timestamp()
            c.execute('INSERT INTO credits (username, points, last_update) VALUES (?, ?, ?)', (username, 0, now))
            conn.commit()
            flash(f'Successfully Registered! Your username is: {username}', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists! Please try again.', 'error')
        finally:
            conn.close()
    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (session['username'],))
    user = c.fetchone()
    c.execute('SELECT points FROM credits WHERE username = ?', (session['username'],))
    credits_row = c.fetchone()
    credits = credits_row[0] if credits_row else 0
    conn.close()

    if user:
        user_data = {
            'full_name': user[1],
            'school_name': user[2],
            'class': user[3],
            'roll_no': user[4],
            'phone_no': user[6],
            'email': user[7],
            'username': user[0],
            'birthdate': user[8],
            'credits': credits
        }
        return render_template('portal.html', user=user_data)
    return redirect(url_for('login'))

@app.route('/courses')
def courses():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('courses.html')

@app.route('/projects')
def projects():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('projects.html')

@app.route('/curriculum')
def curriculum():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('curriculum.html')

@app.route('/hackathon', methods=['GET', 'POST'])
def hackathon():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        team_name = request.form['team_name'].lower().replace(' ', '')
        code = request.form['code']
        
        if not team_name:
            flash('Team name is required', 'error')
            return redirect(url_for('hackathon'))
        
        if not code.strip():
            flash('Code is required', 'error')
            return redirect(url_for('hackathon'))

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if team already exists
        c.execute('SELECT * FROM teams WHERE team_name = ?', (team_name,))
        team = c.fetchone()
        
        if team:
            # Team exists, check if code matches
            if team[1] != code:
                flash('Team already has a different submission. Please contact your team.', 'error')
                conn.close()
                return redirect(url_for('hackathon'))
        else:
            # Insert new team and code
            c.execute('''INSERT INTO teams (team_name, code, submission_time)
                         VALUES (?, ?, ?)''',
                      (team_name, code, datetime.datetime.now().isoformat()))
        
        # Link user to team and store code in hackathon_submissions
        c.execute('''INSERT INTO hackathon_submissions (username, team_name, code)
                     VALUES (?, ?, ?)''',
                  (session['username'], team_name, code))
        
        conn.commit()
        conn.close()
        
        flash('Code submitted successfully!', 'success')
        return redirect(url_for('hackathon'))
    
    return render_template('hackathon.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.before_request
def award_credits():
    if 'username' in session:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT points, last_update FROM credits WHERE username = ?', (session['username'],))
        row = c.fetchone()
        now = datetime.datetime.now().timestamp()
        if row:
            points, last_update = row
            minutes = int((now - last_update) // 60)
            if minutes > 0:
                new_points = points + minutes
                c.execute('UPDATE credits SET points = ?, last_update = ? WHERE username = ?', (new_points, now, session['username']))
                conn.commit()
        else:
            c.execute('INSERT INTO credits (username, points, last_update) VALUES (?, ?, ?)', (session['username'], 0, now))
            conn.commit()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)