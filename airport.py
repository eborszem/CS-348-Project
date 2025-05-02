from app import app, mysql, db
from flask import render_template, request, redirect, url_for, flash, jsonify

@app.route('/')
def index():
    return render_template('index.html')

# ORM Models ################################################################
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

class Flight(db.Model):
    __tablename__ = 'flights'
    flight_number = db.Column(db.String(10), primary_key=True)
    origin = db.Column(db.String(3), db.ForeignKey('airports.code'))
    destination = db.Column(db.String(3), db.ForeignKey('airports.code'))
    departure_date = db.Column(db.Date)
    airline_code = db.Column(db.String(2), db.ForeignKey('airlines.code'), nullable=False)
    
    airline = db.relationship('Airline', backref='flights')
    origin_airport = db.relationship('Airport', foreign_keys=[origin])
    dest_airport = db.relationship('Airport', foreign_keys=[destination])

class Passenger(db.Model):
    __tablename__ = 'passengers'
    first = db.Column(db.String(50), primary_key=True)
    last = db.Column(db.String(50), primary_key=True)
    flight_number = db.Column(db.String(10), db.ForeignKey('flights.flight_number'), primary_key=True)
    
    flight = db.relationship('Flight', backref='passengers')

#############################################################################
# MANAGE AIRPORTS
@app.route('/airports', methods=['GET', 'POST'])
def airports():
    if request.method == 'POST':
        code = request.form['code'].upper()
        name = request.form['name']
        city = request.form['city']
        country = request.form['country']
        
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO airports (code, name, city, country) VALUES (%s, %s, %s, %s)",
                (code, name, city, country)
            )
            mysql.connection.commit()
            flash('Airport added successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding airport: {str(e)}', 'danger')
        finally:
            cur.close()
        return redirect(url_for('airports'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM airports ORDER BY code")
    airports = cur.fetchall()
    cur.close()
    return render_template('airports.html', airports=airports)

@app.route('/edit_airport/<code>', methods=['GET', 'POST'])
def edit_airport(code):
    if request.method == 'POST':
        try:
            airport = Airport.query.get(code)
            if airport:
                airport.name = request.form['name']
                airport.city = request.form['city']
                airport.country = request.form['country']
                db.session.commit()
                flash('Airport updated successfully!', 'success')
            else:
                flash('Airport not found!', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating airport: {str(e)}', 'danger')
        return redirect(url_for('airports'))
    
    airport = Airport.query.get_or_404(code)
    return render_template('edit_airport.html', airport=airport)

@app.route('/delete_airport/<code>', methods=['POST'])
def delete_airport(code):
    try:
        airport = Airport.query.get(code)
        if airport:
            db.session.delete(airport)
            db.session.commit()
            flash('Airport deleted successfully!', 'success')
        else:
            flash('Airport not found!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting airport: {str(e)}', 'danger')
    return redirect(url_for('airports'))

####################################################################################################
# MANAGE AIRLINES
@app.route('/airlines', methods=['GET', 'POST'])
def airlines():
    if request.method == 'POST':
        code = request.form['code'].upper()
        name = request.form['name']
        
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO airlines (code, name) VALUES (%s, %s)", 
                (code, name)
            )
            mysql.connection.commit()
            flash('Airline added successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding airline: {str(e)}', 'danger')
        finally:
            cur.close()
        return redirect(url_for('airlines'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM airlines ORDER BY code")
    airlines = cur.fetchall()
    cur.close()
    return render_template('airlines.html', airlines=airlines)

@app.route('/airline_operations/<airline_code>', methods=['GET', 'POST'])
def airline_operations(airline_code):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        selected_airports = request.form.getlist('airports')
        
        try:
            for airport_code in selected_airports:
                cur.execute(
                    "INSERT INTO operates (airline_code, airport_code) VALUES (%s, %s)",
                    (airline_code, airport_code)
                )
            mysql.connection.commit()
            flash(f'Successfully added {len(selected_airports)} operations!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding operations: {str(e)}', 'danger')
        
        return redirect(url_for('airline_operations', airline_code=airline_code))
    
    cur.execute("SELECT name FROM airlines WHERE code = %s", (airline_code,))
    airline = cur.fetchone()
    
    if not airline:
        flash('Airline not found!', 'danger')
        return redirect(url_for('airlines'))
    
    cur.execute("""
        SELECT a.code, a.name, a.city 
        FROM airports a
        JOIN operates o ON a.code = o.airport_code
        WHERE o.airline_code = %s
        ORDER BY a.code
    """, (airline_code,))
    operations = cur.fetchall()
    
    cur.execute("SELECT code, name, city FROM airports ORDER BY code")
    all_airports = cur.fetchall()
    
    cur.close()
    
    operated_airports = {op['code'] for op in operations}
    airports = []
    for airport in all_airports:
        airport_dict = dict(airport)
        airport_dict['operated'] = airport['code'] in operated_airports
        airports.append(airport_dict)
    
    return render_template('airline_operations.html',
                         airline_code=airline_code,
                         airline_name=airline['name'],
                         operations=operations,
                         airports=[a for a in airports if not a['operated']])


@app.route('/delete_operation/<airline_code>/<airport_code>', methods=['POST'])
def delete_operation(airline_code, airport_code):
    try:
        operation = Operates.query.filter_by(
            airline_code=airline_code,
            airport_code=airport_code
        ).first()
        
        if operation:
            db.session.delete(operation)
            db.session.commit()
            flash('Operation removed successfully!', 'success')
        else:
            flash('Operation not found!', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing operation: {str(e)}', 'danger')
    return redirect(url_for('airline_operations', airline_code=airline_code))

@app.route('/edit_airline/<code>', methods=['GET', 'POST'])
def edit_airline(code):
    if request.method == 'POST':
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE airlines SET name = %s WHERE code = %s",
                (request.form['name'], code)
            )
            mysql.connection.commit()
            flash('Airline updated successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating airline: {str(e)}', 'danger')
        finally:
            cur.close()
        return redirect(url_for('airlines'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM airlines WHERE code = %s", (code,))
    airline = cur.fetchone()
    cur.close()
    
    if not airline:
        flash('Airline not found!', 'danger')
        return redirect(url_for('airlines'))
    
    return render_template('edit_airline.html', airline=airline)

@app.route('/delete_airline/<code>', methods=['POST'])
def delete_airline(code):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT 1 FROM flights WHERE airline_code = %s LIMIT 1", (code,))
        if cur.fetchone():
            flash('Cannot delete - airline has existing flights!', 'danger')
            return redirect(url_for('airlines'))
        
        cur.execute("SELECT 1 FROM operates WHERE airline_code = %s LIMIT 1", (code,))
        if cur.fetchone():
            flash('Cannot delete - airline has existing operations!', 'danger')
            return redirect(url_for('airlines'))
        
        cur.execute("DELETE FROM airlines WHERE code = %s", (code,))
        mysql.connection.commit()
        flash('Airline deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error deleting airline: {str(e)}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('airlines'))

####################################################################################################
# CREATE FLIGHT
@app.route('/create_flight', methods=['GET', 'POST'])
def create_flight():
    if request.method == 'POST':
        try:
            flight = Flight(
                flight_number=request.form['flight_number'],
                origin=request.form['origin'],
                destination=request.form['destination'],
                departure_date=request.form['departure_date'],
                airline_code=request.form['airline_code']
            )
            db.session.add(flight)
            db.session.commit()
            flash('Flight created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating flight: {str(e)}', 'danger')
        return redirect(url_for('create_flight'))
    
    airlines = Airline.query.order_by(Airline.name).all()
    return render_template('create_flight.html', airlines=airlines)

# CREATE A FLIGHT LIST
@app.route('/get_airline_airports/<airline_code>')
def get_airline_airports(airline_code):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.code, a.name 
        FROM airports a
        JOIN operates o ON a.code = o.airport_code
        WHERE o.airline_code = %s
        ORDER BY a.code
    """, (airline_code,))
    airports = cur.fetchall()
    cur.close()
    return jsonify(airports)

####################################################################################################
# BOOK FLIGHT
@app.route('/book_flight', methods=['GET', 'POST'])
def book_flight():
    if request.method == 'POST':
        flight_number = request.form['flight_number']
        first = request.form['first_name']
        last = request.form['last_name']
        
        try:
            flight = Flight.query.get(flight_number)
            if not flight:
                flash('Flight not found!', 'danger')
                return redirect(url_for('book_flight'))
            
            passenger = Passenger(
                first=first,
                last=last,
                flight_number=flight_number
            )
            db.session.add(passenger)
            db.session.commit()
            flash(f'Booking created for {first} {last} on flight {flight_number}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating booking: {str(e)}', 'danger')
        return redirect(url_for('book_flight'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT code, name FROM airlines ORDER BY name")
    airlines = cur.fetchall()
    cur.close()
    return render_template('book_flight.html', airlines=airlines)

# BOOK A FLIGHT LIST
@app.route('/get_flights/<airline_code>')
def get_flights(airline_code):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.flight_number, 
               a1.code as origin_code, a1.name as origin_name,
               a2.code as dest_code, a2.name as dest_name,
               f.departure_date
        FROM flights f
        JOIN airports a1 ON f.origin = a1.code
        JOIN airports a2 ON f.destination = a2.code
        WHERE f.airline_code = %s
        ORDER BY f.departure_date
    """, (airline_code,))
    flights = cur.fetchall()
    cur.close()
    return jsonify(flights)

####################################################################################################
# VIEW ALL FLIGHTS
@app.route('/view_all_flights')
def view_all_flights():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            f.flight_number,
            al.name as airline_name,
            a1.code as origin_code,
            a1.name as origin_name,
            a2.code as dest_code,
            a2.name as dest_name,
            f.departure_date,
            COUNT(p.flight_number) as passenger_count
        FROM flights f
        JOIN airlines al ON f.airline_code = al.code
        JOIN airports a1 ON f.origin = a1.code
        JOIN airports a2 ON f.destination = a2.code
        LEFT JOIN passengers p ON f.flight_number = p.flight_number
        GROUP BY f.flight_number
        ORDER BY f.departure_date DESC
    """)
    flights = cur.fetchall()
    cur.close()
    return render_template('view_all_flights.html', flights=flights)

####################################################################################################
# VIEW ALL BOOKINGS
@app.route('/view_flights')
def view_flights():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            p.first, 
            p.last, 
            p.flight_number,
            f.departure_date,
            a1.code as origin_code, 
            a1.name as origin_name,
            a2.code as dest_code, 
            a2.name as dest_name,
            al.code as airline_code,
            al.name as airline_name
        FROM passengers p
        JOIN flights f ON p.flight_number = f.flight_number
        JOIN airports a1 ON f.origin = a1.code
        JOIN airports a2 ON f.destination = a2.code
        JOIN airlines al ON f.airline_code = al.code
        ORDER BY f.departure_date DESC
    """)
    bookings = cur.fetchall()
    cur.close()
    return render_template('view_flights.html', bookings=bookings)

@app.route('/delete_booking/<flight_number>/<first>/<last>', methods=['POST'])
def delete_booking(flight_number, first, last):
    try:
        booking = Passenger.query.filter_by(
            first=first,
            last=last,
            flight_number=flight_number
        ).first()
        
        if booking:
            db.session.delete(booking)
            db.session.commit()
            flash('Booking deleted successfully!', 'success')
        else:
            flash('Booking not found!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting booking: {str(e)}', 'danger')
    return redirect(url_for('view_flights'))

@app.route('/update_booking/<flight_number>/<first>/<last>', methods=['GET', 'POST'])
def update_booking(flight_number, first, last):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        new_flight = request.form['new_flight_number'].split(':')[0].strip()
        try:
            cur.execute(
                "DELETE FROM passengers WHERE first = %s AND last = %s AND flight_number = %s",
                (first, last, flight_number)
            )
            cur.execute(
                "INSERT INTO passengers (first, last, flight_number) VALUES (%s, %s, %s)",
                (first, last, new_flight)
            )
            mysql.connection.commit()
            flash('Booking updated successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating booking: {str(e)}', 'danger')
        finally:
            cur.close()
        return redirect(url_for('view_flights'))
    
    cur.execute("""
        SELECT f.flight_number, 
               a1.code as origin_code, a1.name as origin_name,
               a2.code as dest_code, a2.name as dest_name,
               f.departure_date
        FROM flights f
        JOIN airports a1 ON f.origin = a1.code
        JOIN airports a2 ON f.destination = a2.code
        ORDER BY f.departure_date
    """)
    flights = cur.fetchall()
    cur.close()
    return render_template('update_booking.html', 
                         flights=flights,
                         current_flight=flight_number,
                         first=first,
                         last=last)

