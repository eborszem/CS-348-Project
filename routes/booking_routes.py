from app import app, mysql, db
from flask import render_template, request, redirect, url_for, flash, jsonify
from models import *

# BOOK FLIGHT (ORM) 
@app.route('/book_flight', methods=['GET', 'POST'])
def book_flight():
    if request.method == 'POST':
        flight_number = request.form['flight_number']
        first = request.form['first_name']
        last = request.form['last_name']
        
        # isolation level: repeatable read
        db.session.connection(
            execution_options={'isolation_level': 'REPEATABLE READ'}
        )
        
        try:
            # get flight capacity
            flight = Flight.query.with_for_update().get(flight_number)  # row lock
            
            if not flight:
                flash('Flight not found!', 'danger')
                return redirect(url_for('book_flight'))
            
            # is flight full
            current_passengers = Passenger.query.filter_by(
                flight_number=flight_number
            ).count()
            
            if current_passengers >= flight.capacity:
                flash('Flight is fully booked!', 'danger')
                return redirect(url_for('book_flight'))
            
            # create booking
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
        finally:
            db.session.close()
        
        return redirect(url_for('book_flight'))
    
    # GET request handling
    airlines = Airline.query.order_by(Airline.name).all()
    return render_template('book_flight.html', airlines=airlines)

# # BOOK A FLIGHT LIST
# @app.route('/get_flights/<airline_code>')
# def get_flights(airline_code):
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT f.flight_number, 
#                a1.code as origin_code, a1.name as origin_name,
#                a2.code as dest_code, a2.name as dest_name,
#                f.departure_date
#         FROM flights f
#         JOIN airports a1 ON f.origin = a1.code
#         JOIN airports a2 ON f.destination = a2.code
#         WHERE f.airline_code = %s
#         ORDER BY f.departure_date
#     """, (airline_code,))
#     flights = cur.fetchall()
#     cur.close()
#     return jsonify(flights)

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

# ORM
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