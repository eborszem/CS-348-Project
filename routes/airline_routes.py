from app import app, mysql, db
from flask import render_template, request, redirect, url_for, flash, jsonify
from models import *

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


# ORM
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

# FLIGHT REPORT INTERFACE
@app.route('/flight_report', methods=['GET', 'POST'])
def flight_report():
    airline_code = request.args.get('airline', '')
    origin_code = request.args.get('origin', '')
    dest_code = request.args.get('destination', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # ORM
    Airport_origin = db.aliased(Airport)
    Airport_dest = db.aliased(Airport)
    
    query = db.session.query(
        Flight,
        Airline.name.label('airline_name'),
        Airport_origin.name.label('origin_name'),
        Airport_dest.name.label('dest_name'),
        db.func.count(Passenger.flight_number).label('passenger_count')
    ).join(
        Airline, Flight.airline_code == Airline.code
    ).join(
        Airport_origin, Flight.origin == Airport_origin.code
    ).join(
        Airport_dest, Flight.destination == Airport_dest.code
    ).outerjoin(
        Passenger, Flight.flight_number == Passenger.flight_number
    ).group_by(
        Flight.flight_number,
        Airline.name,
        Airport_origin.name,
        Airport_dest.name
    )
    
    if airline_code:
        query = query.filter(Flight.airline_code == airline_code)
    if origin_code:
        query = query.filter(Flight.origin == origin_code)
    if dest_code:
        query = query.filter(Flight.destination == dest_code)
    if start_date:
        query = query.filter(Flight.departure_date >= start_date)
    if end_date:
        query = query.filter(Flight.departure_date <= end_date)
    
    flights = query.all()
    
    stats = {}
    cur = mysql.connection.cursor()
    
    base_sql = """
        SELECT 
            COUNT(*) as total_flights,
            AVG(passenger_count) as avg_passengers,
            MIN(departure_date) as earliest_date,
            MAX(departure_date) as latest_date
        FROM (
            SELECT 
                f.flight_number,
                COUNT(p.flight_number) as passenger_count,
                f.departure_date
            FROM flights f
            LEFT JOIN passengers p ON f.flight_number = p.flight_number
            WHERE 1=1
    """
    
    params = []
    conditions = []
    
    if airline_code:
        conditions.append("f.airline_code = %s")
        params.append(airline_code)
    if origin_code:
        conditions.append("f.origin = %s")
        params.append(origin_code)
    if dest_code:
        conditions.append("f.destination = %s")
        params.append(dest_code)
    if start_date:
        conditions.append("f.departure_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("f.departure_date <= %s")
        params.append(end_date)
    
    sql = base_sql
    if conditions:
        sql += " AND " + " AND ".join(conditions)
    sql += " GROUP BY f.flight_number ) as flight_stats"
    
    cur.execute(sql, params)
    stats = cur.fetchone()
    cur.close()
    
    airlines = Airline.query.order_by(Airline.name).all()
    airports = Airport.query.order_by(Airport.code).all()
    
    return render_template('flight_report.html',
                         flights=flights,
                         stats=stats,
                         airlines=airlines,
                         airports=airports,
                         filters={
                             'airline': airline_code,
                             'origin': origin_code,
                             'destination': dest_code,
                             'start_date': start_date,
                             'end_date': end_date
                         })