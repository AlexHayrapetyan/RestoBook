from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_limiter import Limiter   # limiting requests per minute
from flask_limiter.util import get_remote_address    # same as Limiter
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.exceptions import BadRequest
from werkzeug.security import generate_password_hash
import uuid
import random
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from OpenSSL import SSL   
import os
import logging
logging.basicConfig(level = logging.DEBUG)
from dotenv import load_dotenv   
from redis import Redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from configurations import Config
from models import db, User, Tables, Reservation, Contacting, ContactingResto
from functions import authenticate_user, signup_user, is_overlapping, derive_names,validate_form_data, check_table_availability, hashing, checkPass
context = (
    os.path.join('./ssl', 'cert.pem'),  # Path to SSL certificate
    os.path.join('./ssl', 'key.pem')   # Path to SSL private key
)
load_dotenv()
rest = Flask(__name__)
rest.config.from_object(Config)
db.init_app(rest)
# Initialize Flask-Mail
mail = Mail(rest)

# Initialize Redis client
redis_client = Redis(host='localhost', port=6379)

# Initialize Limiter with Redis storage
limiter = Limiter(
    get_remote_address,
    app=rest,
    storage_uri="redis://localhost:6379"
)
serializer = URLSafeTimedSerializer(rest.secret_key)
scheduler = BackgroundScheduler()
scheduler.start()

def update_reservations_status():
    with rest.app_context():  # Ensure the function runs in the app context
        try:
            # Your existing logic for updating reservations
            current_time = datetime.now()

            # Query all reservations that have passed their time by at least 1 hour 
            # and have a status that is NULL or not 'Done'
            reservations_to_update = Reservation.query.filter(
                Reservation.reservation_time <= current_time - timedelta(hours=1),
                (Reservation.status != 'Done') | (Reservation.status == None)
            ).all()

            # Update the status of each reservation
            for reservation in reservations_to_update:
                reservation.status = 'Done'
                db.session.commit()
                logging.debug(f"Reservation {reservation.id} marked as 'Done'.")

        except Exception as e:
            logging.error(f"Error updating reservations: {str(e)}")


# Scheduler setup to run the task periodically
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=update_reservations_status,
        trigger=IntervalTrigger(minutes=1),  # Run every minute
        id='update_reservation_status',  # Job ID for reference
        name='Update reservations status every minute',  # Job name for reference
        replace_existing=True
    )
    scheduler.start()
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('signing'))
        return f(*args, **kwargs)
    return decorated_function

@rest.route('/', methods = ['GET', 'POST'])
def search():
    return render_template('search.html')

@rest.route('/contactingResto', methods = ['GET', 'POST'])
def contactingResto():
    if request.method == 'POST':
        full_name = request.form.get('Full Name')
        
        # Error handling for missing Full Name
        if not full_name or full_name.strip() == "":
            return "Error: Full Name is required.", 400
        
        # Use the derive_names function to split the full name
        first_name, last_name = derive_names(full_name)

        # Error handling if first name or last name are not correctly derived
        if first_name == "" and last_name == "":
            return "Error: Invalid input for Full Name.", 400

        subject = request.form.get('Subject')  # Make sure the form has a 'Subject' field
        if not subject or subject.strip() == "":
            return "Error: Subject is required.", 400
        
        email = request.form.get('Email Address')
        if not email or email.strip() == "":
            return "Error: Email Address is required.", 400
        
        message = request.form.get('Your Message')
        if not message or message.strip() == "":
            return "Error: Message is required.", 400

        # Create a new Contacting object with the provided form data
        new_contact = ContactingResto(
            first_name=first_name,
            last_name=last_name,
            subject=subject,
            email=email,
            message=message
        )
        
        # Add to the database
        db.session.add(new_contact)
        db.session.commit()

        # Return success or redirect to a confirmation page
        return render_template('contactingResto.html', message="Thank you for contacting us!")
    return render_template('contactingResto.html')    

@rest.route('/home', methods=['GET'])
def home():
    return render_template('homePage.html')

@rest.route('/login', methods=['GET', 'POST'])
def logIN():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authenticate user
        user, error = authenticate_user(username, password)
        if user:
            session['user_id'] = user.id
        if error:
            return render_template('login.html', error = error)
        return redirect(url_for('reservation'))
    return render_template('login.html')  

@rest.route('/signfirst', methods=['GET', 'POST'])
def signing():
    if request.method == 'POST':
        try:
            # Get data from the first form
            username = request.form.get('name')
            email = request.form.get('email')
            password = str(request.form.get('password'))
            confirm = str(request.form.get('confirmPassword'))

            # Log form data for debugging
            logging.debug(f"Received data - username: {username}, email: {email}, password: {password}, confirmPassword: {confirm}")
            
            if not username or not email or not password or not confirm:
                logging.error("Missing required fields.")
                flash("Please fill out all fields.")
                return render_template('signfirst.html')

            # Store data in session for use in the next step
            session['username'] = username
            session['email'] = email
            session['password'] = password
            session['confirm'] = confirm
            
            # Validate passwords match
            if checkPass(password, confirm):
                logging.debug("passwords match")
                return redirect(url_for('signing2'))  # Redirect to the next step
            else:
                logging.error("Passwords do not match.")
                flash("Passwords don't match.")
                return render_template('signfirst.html')

        except Exception as e:
            logging.error(f"Error processing form: {e}")
            flash("An error occurred. Please try again.")
            return render_template('signfirst.html')

    return render_template('signfirst.html')

@rest.route('/signthecard', methods=['GET', 'POST'])
def signing2():
    if request.method == 'POST':    
        try:
            # Get the data from the second form (card details)
            fullname = request.form.get('fullname')
            card_number = request.form.get('cardnumber')
            edate = request.form.get('edate')
            cvv = request.form.get('cvv')

            logging.debug(f"Form data received: {request.form}")

            if not fullname or not card_number or not edate or not cvv:
                logging.error("Missing card details.")
                flash("Please fill out all card details.")
                return render_template('signthecard.html')

            # Get the data from the session
            username = session.get('username')
            email = session.get('email')
            password = str(session.get('password'))
            confirm = str(session.get('confirm'))

            # Log session data for debugging
            logging.debug(f"Session data - username: {username}, email: {email}, password: {password}, confirm: {confirm}")

            # Check if the passwords match before proceeding
            if not checkPass(password, confirm):
                logging.error("Passwords don't match at the second step.")
                flash("Passwords don't match.")
                return redirect(url_for('signing'))  # Redirect back to the first step if passwords don't match

            # Hash the password before saving
            hashed_password = hashing(password)
            logging.debug(f"Hashed password: {hashed_password}")

            # Log the sign-up process (check the signup_user function)
            logging.debug(f"Signing up user: fullname: {fullname}, cardnumber: {card_number}, edate: {edate}")

            # Signup user (ensure signup_user function is defined correctly)
            user, error = signup_user(username, email, hashed_password, card_number, cvv, edate)
            if error:
                logging.error(f"Error during signup: {error}")
                return render_template('signthecard.html', error=error)

            user_id = user.id
            session['user_id'] = user_id
            # Confirm that user is signed up and redirect
            logging.debug("User successfully signed up, redirecting to reservation.")
            return redirect(url_for('reservation'))  # Ensure 'reservation' is the correct route

        except Exception as e:
            logging.error(f"Error during sign-up process: {e}")
            flash("An error occurred during sign-up. Please try again.")
            return render_template('signthecard.html')

    return render_template('signthecard.html')


@rest.route('/aboutResto', methods = ['GET'])
def aboutResto():
    return render_template('aboutResto.html')

@rest.route('/reservation', methods=['GET', 'POST'])
@login_required
def reservation():
    error = None
    success = None

    if request.method == 'POST':
        user_id = session.get('user_id')

        if not user_id:
            error = "User not logged in."
            return render_template('reservation.html', error=error)

        visiting_date = request.form.get('date', '').strip()
        visiting_time = request.form.get('time', '').strip()
        number_of_people = request.form.get('people', '0').strip()
        table_number = request.form.get('table')

        try:
            # Validate input data
            date, time, number, table_id = validate_form_data(visiting_date, visiting_time, int(number_of_people), table_number)

            chosenTable = check_table_availability(table_id, number)
            if not chosenTable:
                error = "Table is not available."
                return render_template('reservation.html', error=error)

            chosenTable.status = 'Busy'
            db.session.commit()

            result = create_reservation(user_id, table_id, date, time, number)

            if "Error" in result:
                error = result
            else:
                success = result

            if success:
                send_reminder_email(user_id)
                return redirect(url_for('pricing'))

        except ValueError as e:
            error = str(e)
            db.session.rollback()
        except BadRequest as e:
            error = str(e)
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            error = "An unexpected error occurred: " + str(e)

    return render_template('reservation.html', error=error, success=success)


def create_reservation(user_id, table_id, date, reservation_time, number):
    new_reservation_time = datetime.combine(date, reservation_time)
    if is_overlapping(new_reservation_time, table_id):
        return "This table is already booked, please choose another one"
    
    new_reservation = Reservation(user_id=user_id, table_id=table_id, date=date, reservation_time=reservation_time, number=number)
    db.session.add(new_reservation)
    db.session.commit()

    table = db.session.get(Tables, table_id)
    if table:
        table.status = 'Busy'
        db.session.commit()
        
    try:
        send_confirmation_email(user_id)
    except Exception as e:
        logging.error(f"This error occured: {e}")        
    return "Reservation created successfully."

def send_confirmation_email(user_id):
    user = db.session.get(User, user_id)
    try:
        if user:
            body = render_template('confirmation.html')
            msg = Message(
                'Reservation Reminder',
                recipients=[user.email],
                html=body  # Send the rendered HTML body
            )
            mail.send(msg)
        flash("User has not been found")
    except Exception as e:
        db.session.rollback()
        flash(f"{e} occured")        



def complete_reservation(reservation_id):
    # Fetch the reservation by ID
    reservation = db.session.get(Reservation, reservation_id)
    
    if reservation:
        # Update the status to "Done"
        reservation.status = "Done"
        db.session.commit()  # Commit the change to the database
        logging.debug(f"Reservation {reservation_id} marked as 'Done'.")
    else:
        logging.error(f"Reservation {reservation_id} not found.")


def send_reminder_email(user_id):
    user = db.session.get(User, user_id)  # Fetch the user from the database
    
    if user:
        reservation = Reservation.query.filter_by(user_id=user.id).filter(
            (Reservation.status != "Done") | (Reservation.status == "Pending")
        ).order_by(Reservation.date.desc()).first()
        logging.debug(f"Reservation for user {user.id}: {reservation}")
        if reservation:
            current_date = datetime.now().date()
            reserved_date = reservation.date
            difference = reserved_date - current_date

            # If the reservation is tomorrow, send a reminder email
            if difference.days == 1:
                # Render the email body with user and reservation details
                body = render_template('email.html', user=user, reservation=reservation)
                
                # Create the email message
                msg = Message(
                    'Reservation Reminder',
                    recipients=[user.email],
                    html=body  # Send the rendered HTML body
                )
                
                # Send the email
                mail.send(msg)
                flash("Reminder email sent successfully!", "success")
            else:
                flash("No upcoming reservation or it's not a day before the reservation.", "info")
        else:
            flash(f"No reservation found for user {user.id}", "error")
    else:
        flash(f"No user found with ID {user_id}", "error")

    
@rest.route('/pricing', methods = ['GET', 'POST'])
@login_required
def pricing():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    user_card = user.credit_card
    last_4_digits = user_card[-4:]
    return render_template('pricing.html', last_4_digits = last_4_digits)


@rest.route('/feedback', methods = ['GET', 'POST'])
def feedback():
    return render_template('feedback.html')

@rest.route('/contacting', methods=['GET', 'POST'])
def contacting():
    if request.method == 'POST':
        full_name = request.form.get('Full Name')
        
        # Error handling for missing Full Name
        if not full_name or full_name.strip() == "":
            return "Error: Full Name is required.", 400
        
        # Use the derive_names function to split the full name
        first_name, last_name = derive_names(full_name)

        # Error handling if first name or last name are not correctly derived
        if first_name == "" and last_name == "":
            return "Error: Invalid input for Full Name.", 400

        subject = request.form.get('Subject')  # Make sure the form has a 'Subject' field
        if not subject or subject.strip() == "":
            return "Error: Subject is required.", 400
        
        email = request.form.get('Email Address')
        if not email or email.strip() == "":
            return "Error: Email Address is required.", 400
        
        message = request.form.get('Your Message')
        if not message or message.strip() == "":
            return "Error: Message is required.", 400

        # Create a new Contacting object with the provided form data
        new_contact = Contacting(
            first_name=first_name,
            last_name=last_name,
            subject=subject,
            email=email,
            message=message
        )
        
        # Add to the database
        db.session.add(new_contact)
        db.session.commit()

        # Return success or redirect to a confirmation page
        return render_template('contacting.html', message="Thank you for contacting us!")

    return render_template('contacting.html')


@rest.route('/menu', methods = ['GET', 'POST'])
def menu():
    return render_template('menu.html')

@rest.route('/about', methods = ['GET', 'POST'])
def about():
    return render_template('about.html')    

if __name__ == '__main__':
    with rest.app_context():
        db.create_all()
        start_scheduler()
        try:
            rest.run(host='0.0.0.0', port=443, ssl_context=context, debug = True)
        except (KeyboardInterrupt, SystemExit):
            pass
