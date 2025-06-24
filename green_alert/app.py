from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(300))
    status = db.Column(db.String(100), default='Pending')

# Admin credentials
ADMIN_EMAIL = 'admin@example.com'
ADMIN_PASSWORD = 'adminpass'

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))

        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', complaints=complaints)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    location = request.form['location']
    image = request.files['image']
    image_filename = None

    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_filename = filename

    complaint = Complaint(
        user_id=session['user_id'],
        title=title,
        description=description,
        location=location,
        image=image_filename
    )
    db.session.add(complaint)
    db.session.commit()
    flash('Complaint submitted.')
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:complaint_id>', methods=['POST'])
def delete_complaint(complaint_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.user_id != session['user_id']:
        flash('Unauthorized.')
        return redirect(url_for('dashboard'))

    db.session.delete(complaint)
    db.session.commit()
    flash('Complaint deleted.')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.')
    return render_template('admin_login.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        complaint_id = request.form['complaint_id']
        status = request.form['status']
        complaint = Complaint.query.get(complaint_id)
        if complaint:
            complaint.status = status
            db.session.commit()

    complaints = Complaint.query.all()
    return render_template('admin_dashboard.html', complaints=complaints)

@app.route('/update_status/<int:complaint_id>', methods=['POST'])
def update_status(complaint_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    new_status = request.form['status']
    complaint = Complaint.query.get(complaint_id)
    if complaint:
        complaint.status = new_status
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:complaint_id>', methods=['POST'])
def admin_delete_complaint(complaint_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    complaint = Complaint.query.get_or_404(complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    flash('Complaint deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_id', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin_login'))# Run App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
