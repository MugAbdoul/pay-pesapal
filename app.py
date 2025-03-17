import os
import requests
import uuid
import hashlib
import hmac
import base64
import json
from flask import Flask, request, redirect, render_template, session, url_for
from dotenv import load_dotenv
from datetime import datetime
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(16)

# Pesapal API configuration
PESAPAL_API_URL = os.getenv("PESAPAL_API_URL")  # e.g. "https://pay.pesapal.com/v3"
CONSUMER_KEY = os.getenv("PESAPAL_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("PESAPAL_CONSUMER_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")  # Your callback URL for IPNs

# Database simulation (in production, use a proper database)
transactions_db = {}

def get_auth_token():
    """Get authentication token from Pesapal"""
    url = f"{PESAPAL_API_URL}/api/Auth/RequestToken"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "consumer_key": CONSUMER_KEY,
        "consumer_secret": CONSUMER_SECRET
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()["token"]
    else:
        # Log error properly in production
        print(f"Auth Error: {response.text}")
        return None

def generate_request_signature(request_data):
    """Generate HMAC signature for request"""
    message = json.dumps(request_data)
    digest = hmac.new(
        CONSUMER_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    return base64.b64encode(digest).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    if not request.form:
        return "Bad request", 400
    
    # Validate input
    amount = request.form.get('amount')
    description = request.form.get('description')
    
    if not amount or not amount.isdigit() or not description:
        return "Invalid input data", 400
    
    # Generate unique order ID
    order_id = f"ORDER-{uuid.uuid4().hex[:10]}"
    
    # Store transaction info securely
    transactions_db[order_id] = {
        'amount': amount,
        'description': description,
        'status': 'PENDING',
        'created_at': datetime.utcnow().isoformat(),
        'order_id': order_id  # Add this for status.html template
    }
    
    # Get access token
    token = get_auth_token()
    if not token:
        return render_template('error.html', error_message="Could not obtain authentication token. Check API credentials.")
    
    # Create payment request
    url = f"{PESAPAL_API_URL}/api/Transactions/SubmitOrderRequest"
    
    print(PESAPAL_API_URL)
    
    # Note: Currency might need to be different based on your account. 
    # Common options are KES (Kenya), UGX (Uganda), TZS (Tanzania), or USD
    request_data = {
        "id": order_id,
        "currency": "RWF",  # Changed from RW to USD - adjust according to your account
        "amount": float(amount),
        "description": description,
        "callback_url": CALLBACK_URL,
        "notification_id": os.getenv("NOTIFICATION_ID", ""),
        "billing_address": {
            "email_address": request.form.get('email', ''),
            "phone_number": request.form.get('phone', ''),
            "first_name": request.form.get('firstname', ''),
            "last_name": request.form.get('lastname', '')
        }
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=request_data)
        
        print(f"Request Data: {json.dumps(request_data)}")
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            redirect_url = response_data.get("redirect_url")
            if redirect_url:
                return redirect(redirect_url)
            else:
                error_msg = f"Payment gateway did not return a redirect URL. Response: {response.text}"
                print(error_msg)
                return render_template('error.html', error_message=error_msg)
        else:
            error_msg = f"Payment Error: Status {response.status_code}, Message: {response.text}"
            print(error_msg)
            return render_template('error.html', error_message=error_msg)
    except Exception as e:
        error_msg = f"Exception during payment processing: {str(e)}"
        print(error_msg)
        return render_template('error.html', error_message=error_msg)
    
@app.route('/test_auth')
def test_auth():
    """Test Pesapal authentication"""
    token = get_auth_token()
    if token:
        return f"Authentication successful. Token: {token[:10]}..."
    else:
        return "Authentication failed. Check your API credentials."

@app.route('/ipn', methods=['POST'])
def ipn_listener():
    """Handle Instant Payment Notifications from Pesapal"""
    # Verify the request is from Pesapal
    pesapal_notification = request.headers.get('X-Pesapal-Notification')
    
    if not pesapal_notification:
        return "Unauthorized", 401
    
    # Parse notification data
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    
    if not order_id or not status:
        return "Bad request", 400
    
    # Update transaction status
    if order_id in transactions_db:
        transactions_db[order_id]['status'] = status
        
        # In production, update your database here
        
        return "OK", 200
    else:
        return "Order not found", 404

@app.route('/transaction_status/<order_id>')
def transaction_status(order_id):
    """Check transaction status"""
    if order_id not in transactions_db:
        return "Order not found", 404
    
    token = get_auth_token()
    if not token:
        return "Service unavailable", 503
    
    url = f"{PESAPAL_API_URL}/api/Transactions/GetTransactionStatus?orderTrackingId={order_id}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Update local status
        status_data = response.json()
        transactions_db[order_id]['status'] = status_data.get('status', 'UNKNOWN')
        
        # Return status page
        return render_template('status.html', transaction=transactions_db[order_id])
    else:
        return "Could not retrieve transaction status", 500

if __name__ == '__main__':
    # In production, use a proper WSGI server and HTTPS
    app.run(debug=True)