from app import app, mysql, db
from flask import render_template, request, redirect, url_for, flash, jsonify
from models import *


# CREATE FLIGHT (ORM)
@app.route('/create_flight', methods=['GET', 'POST'])
def create_flight():
    if request.method == 'POST':
        # set isolation level - prevent race conditions when creating flights
        db.session.connection(
            execution_options={'isolation_level': 'REPEATABLE READ'}
        )
        
        try:
            # check if flight already exists with row lock
            existing_flight = Flight.query.with_for_update().get(
                request.form['flight_number']
            )
            
            if existing_flight:
                flash('Flight number already exists', 'danger')
                return redirect(url_for('create_flight'))
            

            capacity = int(request.form.get('capacity', 105))
            if capacity < 10:
                flash('Capacity must be at least 10', 'danger')
                return redirect(url_for('create_flight'))
            
            # Create new flight
            flight = Flight(
                flight_number=request.form['flight_number'],
                origin=request.form['origin'],
                destination=request.form['destination'],
                departure_date=request.form['departure_date'],
                airline_code=request.form['airline_code'],
                capacity=capacity # Default capacity
            )
            
            db.session.add(flight)
            db.session.commit()
            flash('Flight created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating flight: {str(e)}', 'danger')
        finally:
            db.session.close()
        return redirect(url_for('create_flight'))
    
    airlines = Airline.query.order_by(Airline.name).all()
    return render_template('create_flight.html', airlines=airlines)

# CREATE A FLIGHT LIST
# @app.route('/get_airline_airports/<airline_code>')
# def get_airline_airports(airline_code):
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT a.code, a.name 
#         FROM airports a
#         JOIN operates o ON a.code = o.airport_code
#         WHERE o.airline_code = %s
#         ORDER BY a.code
#     """, (airline_code,))
#     airports = cur.fetchall()
#     cur.close()
#     return jsonify(airports)

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
            f.capacity,
            f.capacity - COUNT(p.flight_number) as available,
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