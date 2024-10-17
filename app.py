from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from getEmailInfo import get_emails, analyze_email, extract_company, extract_position, decode_body
import pickle


app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('internships.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    internships = conn.execute('SELECT * FROM internships').fetchall()
    internships = [dict(internship) for internship in internships]
    conn.close()

    #stats of internships
    total_positions = len(internships)
    positions_offered = sum(1 for internship in internships if internship['status'] == 'Position Offered')
    positions_denied = sum(1 for internship in internships if internship['status'] == 'Denied')
    positions_ti = sum(1 for internship in internships if internship['status'] == 'TI')
    positions_oa = sum(1 for internship in internships if internship['status'] == 'OA')
    positions_applied = sum(1 for internship in internships if internship['status'] == 'Applied') 
   
    return render_template(
        'index.html',
        internships=internships,
        total_positions=total_positions,
        positions_offered=positions_offered,
        positions_denied=positions_denied,
        positions_ti=positions_ti,
        positions_oa=positions_oa,
        positions_applied=positions_applied
    )

@app.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        company = request.form['company']
        position = request.form['position']
        custom_position = request.form.get('custom_position')

        if position == "other" and custom_position:
            position = custom_position
        
        status = request.form['status']
        date_applied = request.form['date_applied']

        if company and position and status and date_applied:
            print("Form data:", company, position, status, date_applied)

            try:
                conn = get_db_connection()
                conn.execute('INSERT INTO internships (company, position, status, date_applied) VALUES (?, ?, ?, ?)',
                             (company, position, status, date_applied))
                conn.commit()
                conn.close()
                print("Data inserted successfully")

                  # Debugging step
            except Exception as e:
                print(f"Error inserting data: {e}")  # Log error if insertion fails

            return redirect(url_for('index'))

    return render_template('add.html')

@app.route('/delete/<string:company>/<string:position>', methods=['POST'])
def delete_internship(company, position):
    conn = get_db_connection()
    conn.execute('DELETE FROM internships WHERE company = ? AND position = ?', (company, position))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

def update_app_status(company, position, new_status):

    conn = sqlite3.connect('internships.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT LOWER(company) FROM internships')
    companies = [row[0] for row in c.fetchall()]
    conn.close()

    duplicate_companies= set()
    seen = set()

    #check if the company has multiple different positions
    for checkcompany in companies:
        if checkcompany in seen:
            duplicate_companies.add(checkcompany)
        else:
            seen.add(checkcompany)
    
    print(f"updating app status")
    conn = get_db_connection()
   
    #if company has multiple different positions, update specific position in email
    if company in duplicate_companies:
        print(f"Company is in duplicate companies")
        record = conn.execute('''
            SELECT * FROM internships 
            WHERE LOWER(company) = ? AND LOWER(position) = ?''', (company, position)).fetchone()
    
        if record:
            print(f"record found")
            conn.execute('''
                UPDATE internships
                SET status = ?
                WHERE LOWER(company) = ? AND LOWER(position) = ?''', (new_status, company, position)) 
            print(f"Updated {company} - {position} to {new_status}")  
  
        conn.commit()
        conn.close()

    #if only one company record, disregard position
    else:
        record = conn.execute('''
            SELECT * FROM internships 
            WHERE LOWER(company) = ? ''', (company, )).fetchone()
    
        if record:
            print(f"record found")
            conn.execute('''
                UPDATE internships
                SET status = ?
                WHERE LOWER(company) = ? ''', (new_status, company)) 
            print(f"Updated {company} to {new_status}") 

            updated_internship = conn.execute('''SELECT * FROM internships WHERE LOWER(company) = ? AND status = ?''', (company, new_status)).fetchone()
            if updated_internship:
                print(f"internship updated successfully in sqlite")
    conn.commit()
    conn.close()
        
@app.route('/check-emails', methods=['POST'])
def check_emails_update_status():
    emails = get_emails()

    vectorizer, classifier = load_model()

    
    

    for email_body in emails:
   # for email_body in emails:
        #skip bad ones
        
        ##added ml technique to check for confirmation and add it
        # email_content = email_body.get('body', '').lower()
        
        features = vectorizer.transform([email_body])
        
        is_confirmation = classifier.predict(features)[0]
        print(f"checking for confirmation email")
        if is_confirmation == 'confirmation':
            print(f"confirmation found")
            from ml_model import extract_name_from_custom_nlp
            company_name = extract_name_from_custom_nlp(email_body)
            position_name = extract_position(email_body)
            if company_name and position_name:
                from getEmailInfo import add_from_button
                add_from_button(company=company_name, position=position_name)


        company, position, status = analyze_email(email_body)
        if company and (position or status):
            if position != "other" and status != 'Unknown':
                update_app_status(company, position, status)
    return redirect(url_for('index'))

@app.route('/update_status/<string:company>/<string:position>', methods=['GET', 'POST'] )
def manual_update_status(company, position):
    if request.method == 'POST':
        new_status = request.form['status']
        update_app_status(company.lower(), position.lower(), new_status)
        return redirect(url_for('index'))
    return render_template('update.html', company=company, position=position)

#load machine learning model vectorizer and classifier from disk
def load_model():
    with open('tfidf_vectorizer.pkl', 'rb') as vec_file:
        vectorizer = pickle.load(vec_file)
    with open('email_classifier.pkl', 'rb') as model_file:
        classifier = pickle.load(model_file)
    return vectorizer, classifier
                        


if __name__ == '__main__':
    app.run(debug=True)
