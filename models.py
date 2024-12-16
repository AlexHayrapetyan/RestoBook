from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable = False)
    credit_card = db.Column(db.String(16), nullable = False, unique = True)
    cvv =  db.Column(db.Integer, nullable = False, unique = True)
    edate = db.Column(db.Date, nullable=False)
    money = db.Column(db.Integer, nullable = False)
    email = db.Column(db.String(50), unique = True, nullable = False)

class Tables(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable = False)

class Reservation(db.Model):
    reservation_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reservation_time = db.Column(db.Time, nullable=False)
    number = db.Column(db.Integer, nullable = False)
    #money = db.Column(db.Integer, nullable = False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    def __repr__(self):
        return f"<Reservation(id={self.table_id}, user_id={self.user_id}, date={self.date}, status = {self.status})>"


class Contacting(db.Model):
    first_name = db.Column(db.String(20), primary_key=True)
    last_name = db.Column(db.String(20), nullable = False)
    subject = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(500), nullable=False)

"""
class Payments(db.Model):
    payment_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    money = db.Column(db.Integer, nullable = False)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable = False)
"""
class ContactingResto(db.Model):
    first_name = db.Column(db.String(20), primary_key=True)
    last_name = db.Column(db.String(20), nullable = False)
    subject = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    
        