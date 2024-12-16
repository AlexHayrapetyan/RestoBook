from flask import flash
import random
from models import db, User, Reservation, Tables
import bcrypt
from bcrypt import hashpw, gensalt
from datetime import datetime
from datetime import timedelta
from werkzeug.exceptions import BadRequest

def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    
    # Check if user exists
    if not user:
        return None, "User with that username doesn't exist"
    
    # Check if password is correct
    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return user, None  # Return user object if authentication succeeds
    
    return None, "Incorrect password"  # Return error message if password doesn't match

def hashing(password):
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

def checkPass(password, confirm_password):
    return password == confirm_password


def signup_user(username, email, password, credit_card, cvv, edate):
    # Check if the username already exists
    if User.query.filter_by(username=username).first():
        return None, "User already exists"
    
    # Check if the email already exists
    if User.query.filter_by(email=email).first():
        return None, "User with same email exists"
    
    # Check if the credit card already exists
    if User.query.filter_by(credit_card=credit_card).first():
        return None, "User with same card exists"
    
    # Check if the cvv already exists
    if User.query.filter_by(cvv=cvv).first():
        return None, "User with same cvv exists"
    
    # Hash the password
    hashed_password = hashing(password)
    
    # Generate random money for the new user
    random_money = random.randint(20000, 50000)
    
    # Create a new user instance
    new_user = User(
        username=username, 
        password=hashed_password,  # Store the hashed password
        money=random_money, 
        email=email, 
        credit_card=credit_card,
        cvv=cvv,
        edate=edate
    )
    
    # Save the new user to the database
    db.session.add(new_user)
    db.session.commit()
    
    return new_user, None


def is_overlapping(new_reservation_time, table_id):
    """ Check if the new reservation time overlaps with existing ones for the same table """
    # Find all reservations for the same table
    existing_reservations = Reservation.query.filter_by(table_id=table_id).all()
    for res in existing_reservations:
        existing_reservation_time = datetime.combine(res.date, res.reservation_time)
        existing_end_time = existing_reservation_time + timedelta(hours=1)

        # Check if new reservation time overlaps with any existing reservation
        if (new_reservation_time < existing_end_time) and (new_reservation_time + timedelta(hours=1) > existing_reservation_time):
            return True  # Overlapping
    return False     


def derive_names(full_name):
    """
    Takes a full name and returns the first name and last name.
    If only the first name is provided, the last name is set to an empty string.
    """
    if not full_name or full_name.strip() == "":
        return "", ""  # Return empty strings if the full name is invalid

    try:
        full_name = str(full_name)
    except ValueError:
        return "", ""  # Return empty strings if the input is not a valid string
    
    name_parts = full_name.split()
    if len(name_parts) == 1:
        first_name = name_parts[0]
        last_name = ""  # If only one name is provided, set last name as empty
    elif len(name_parts) > 1:
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])
    else:
        first_name = ""
        last_name = ""

    return first_name, last_name               


def validate_form_data(visiting_date, visiting_time, number_of_people, table_number):
    # Validate the date
    if not visiting_date:
        raise ValueError("Date is required.")
    try:
        date = datetime.strptime(visiting_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    # Validate the time
    if not visiting_time:
        raise ValueError("Time is required.")
    try:
        time = datetime.strptime(visiting_time, '%H:%M').time()
    except ValueError:
        raise ValueError("Invalid time format. Use HH:MM.")

    # Validate the number of people
    try:
        number = int(number_of_people)
    except ValueError:
        raise ValueError("Invalid number of people entered.")
    
    # Validate the table number
    try:
        table_id = int(table_number)
    except ValueError:
        raise ValueError("Invalid table number entered.")
    
    return date, time, number, table_id

def check_table_availability(table_id, number_of_people):
    # Get the table from the database
    chosenTable = db.session.get(Tables, table_id)
    if chosenTable is None:
        raise BadRequest("The selected table does not exist.")
    
    if chosenTable.status == 'Busy':
        raise BadRequest("The chosen table is busy.")
    
    if number_of_people < chosenTable.capacity - 1:
        raise BadRequest("Choose a table with sufficient capacity.")
    
    return chosenTable