import os
import base64
import os.path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import imaplib
import email
from email.header import decode_header
import spacy
import sqlite3
import re
from datetime import date




def get_db_connection():
    conn = sqlite3.connect('internships.db')
    conn.row_factory = sqlite3.Row
    return conn


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

#option 1:
#get email info using google gmail api (reccomended)
def get_emails():
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if creds and creds.expired:
            if creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("Token successfully refreshed")
                except Exception as e:
                    print(f"Error refreshing token: {e}")
            else:
                creds = reauthenticate()
    else: 
        creds = reauthenticate()

    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])

        email_bodies = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            
            payload = msg.get('payload', {})
            body = get_body(payload)

            if body:
                email_bodies.append(body)
            else:
                # Fallback to snippet if no body is found
                snippet = msg.get('snippet', '')
                email_bodies.append(snippet)
            
        return email_bodies

    except HttpError as error:
        print(f'An error occurred: {error}')

def get_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                data = part['body'].get('data', '')
                text = base64.urlsafe_b64decode(data).decode('utf-8')
                return text
            elif mime_type == 'text/html':
                data = part['body'].get('data', '')
                html = base64.urlsafe_b64decode(data).decode('utf-8')
                # Optionally, strip HTML tags to get plain text
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text()
                return text
            elif mime_type.startswith('multipart/'):
                # Recursively process nested parts
                return get_body(part)
    else:
        data = payload.get('body', {}).get('data', None)
        if data:
            mime_type = payload.get('mimeType', '')
            decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
            if mime_type == 'text/plain':
                return decoded_data
            elif mime_type == 'text/html':
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(decoded_data, 'html.parser')
                text = soup.get_text()
                return text
    return None


nlp = spacy.load("en_core_web_sm")

def is_base64(s):
    try: 
        return base64.b64.encode(base64.b64decode(s)) == s.encode('utf-8')
    except Exception:
        return False

def fix_base64_padding(data):
    missing_padding = len(data) % 4
    if missing_padding: 
        data += '=' * (4 - missing_padding)
    return data

def decode_body(body):
    if isinstance(body, bytes):
        try:
            body = body.decode('utf-8')
            print(f"Successfully decoded body as utf-8")
                   
        except (UnicodeDecodeError, base64.binascii.Error, ValueError) as e:
            print(f"Failed to decode body as utf-8: {e}")
            return None

    if isinstance(body, bytes):
        print(f"Body is still bytes, possibly binary data, skipping further processing")
        return None
    
    if isinstance(body, str) and is_base64(body):
        try:
            body = fix_base64_padding(body)
            body = base64.urlsafe_b64decode(body).decode('utf-8')
        except (UnicodeDecodeError, base64.binascii.Error, ValueError) as e:
            print(f"Failed to decode body: {e}")
            return None
        
    if not isinstance(body, str):
        print(f"Error: body is not a string: {type(body)}")
        return None
    
    print(f"successfully decoded body")
    return body

def analyze_email(body): 
    #uses spacy to process the email body
    new_body = decode_body(body)

    doc = nlp(new_body)

    position = extract_position(new_body)
    position = position.strip().lower() if position else None

    company = extract_company(new_body)
    company = company.strip().lower() if company else None

    print(f"Extracted company: {company} and position: {position}")
    #keyword-based approach to detect status
    if any(keyword in doc.text.lower() for keyword in ['unfortunetely', 'other candidates', 'thank you for your interest', 'have decided not', ]):
        status = "Denied"
    elif any(keyword in doc.text.lower() for keyword in ['congratulations', 'we are pleased', 'offer']):
        status = "Position Offered"
    elif any(keyword in doc.text.lower() for keyword in ['assessment', 'interview', 'schedule']):
        status = "OA"
    else:
        status = "Unknown"

    print(f"Determined status: {status}")
    return company, position, status
    
def extract_company(body):
    doc = nlp(body)

    conn = sqlite3.connect('internships.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT company FROM internships')
    companies = [row[0] for row in c.fetchall()]
    conn.close()
    
    extracted_company = None
    for company in companies:
        
        if company.lower() in doc.text.lower():
            print(f"company found: '{company}'")
            extracted_company = company
            break 

    if extracted_company == None:
        for ent in doc.ents:
            if ent.label_ == "ORG":
                extracted_company = ent.text
                break

    return extracted_company

def extract_position(body):
    doc = nlp(body)
    position = None

    conn = sqlite3.connect('internships.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT position FROM internships')
    positions = [row[0] for row in c.fetchall()]
    conn.close()
    
    for job_title in positions:
        if job_title.lower() in doc.text.lower():
            print(f"position found: '{position}'")
            position = job_title
            break 

    return position

def reauthenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret_591032654485-78cujvqj4l96u8glato5k64ojq1u3rnl.apps.googleusercontent.com.json', SCOPES)
    creds = flow.run_local_server(port=0)
    print("Token file missing. Please authenticate your app.")

    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    return creds

###todo
def add_from_button(company, position):
    status = 'Applied'
    date_applied = date.today()
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO internships (company, position, status, date_applied) VALUES (?, ?, ?, ?)',
                             (company, position, status, date_applied))
        conn.commit()
        conn.close()
        print("Data inserted successfully")

                  # Debugging step
    except Exception as e:
        print(f"Error inserting data: {e}")
    return None



