from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable = False)
    credit_card = db.Column(db.String(16), nullable = False, unique = True)
    money = db.Column(db.Integer, nullable = False)
    email = db.Column(db.String(50), unique = True, nullable = False)
    #is_confirmed = db.Column(db.Boolean, default=False)

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
    is_done = db.Column(db.VARCHAR, nullable = False)

    def __repr__(self):
        return f"<Reservation(id={self.table_id}, user_id={self.user_id}, date={self.date}, is_done = {self.is_done})>"


class Contacting(db.Model):
    first_name = db.Column(db.String(20), primary_key=True)
    last_name = db.Column(db.String(20), nullable = False)
    subject = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(35), nullable=False)
    message = db.Column(db.String(500), nullable=False)


class Payments(db.Model):
    payment_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    money = db.Column(db.Integer, nullable = False)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable = False)