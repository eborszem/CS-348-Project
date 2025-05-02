from app import app, mysql, db
from flask import render_template, request, redirect, url_for, flash, jsonify
from models import *

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

