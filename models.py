# ORM
from app import db

class Airport(db.Model):
    __tablename__ = 'airports'
    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)

class Airline(db.Model):
    __tablename__ = 'airlines'
    code = db.Column(db.String(2), primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class Operates(db.Model):
    __tablename__ = 'operates'
    airline_code = db.Column(db.String(2), db.ForeignKey('airlines.code'), primary_key=True)
    airport_code = db.Column(db.String(3), db.ForeignKey('airports.code'), primary_key=True)

    __table_args__ = (
        db.Index('idx_operates_airport', 'airport_code'),
    )

class Flight(db.Model):
    __tablename__ = 'flights'
    flight_number = db.Column(db.String(10), primary_key=True)
    origin = db.Column(db.String(3), db.ForeignKey('airports.code'))
    destination = db.Column(db.String(3), db.ForeignKey('airports.code'))
    departure_date = db.Column(db.Date)
    airline_code = db.Column(db.String(2), db.ForeignKey('airlines.code'), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    
    airline = db.relationship('Airline', backref='flights')
    origin_airport = db.relationship('Airport', foreign_keys=[origin])
    dest_airport = db.relationship('Airport', foreign_keys=[destination])

    __table_args__ = (
        db.Index('idx_flight_origin_dest', 'origin', 'destination'),
        db.Index('idx_flight_airline', 'airline_code'),
        db.Index('idx_flight_number', 'flight_number'),
    )

class Passenger(db.Model):
    __tablename__ = 'passengers'
    first = db.Column(db.String(50), primary_key=True)
    last = db.Column(db.String(50), primary_key=True)
    flight_number = db.Column(db.String(10), db.ForeignKey('flights.flight_number'), primary_key=True)
    
    flight = db.relationship('Flight', backref='passengers')

    __table_args__ = (
        db.Index('idx_passenger_flight', 'flight_number'),
        db.Index('idx_passenger_name', 'last', 'first'),
    )
