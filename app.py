from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import re

app = Flask(__name__)
# Enable CORS for communication between frontend (on file:// or different port) and Flask
CORS(app) 

# --- Database Credentials ---
DB_CONFIG = {
    'host': "localhost",          
    'user': "root",       
    'password': "Samiya@17", 
    'database': "starsucks_db" 
}
TAX_RATE = 0.18 # 18% Tax

def get_db_connection():
    """Establishes and returns a database connection."""
    return mysql.connector.connect(**DB_CONFIG)

def setup_database():
    """Ensures both 'cart' and 'orders' tables exist."""
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 1. Create Cart Table (if not exists)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                price DECIMAL(10, 2) NOT NULL,
                quantity INT NOT NULL
            )
        """)
        
        # 2. Create Orders Table (Enhanced Schema for Payment Interface)
        # This table stores the final, processed order details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10, 2) NOT NULL,
                
                # Customer Contact Details
                customer_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                
                # Shipping Address Details
                address_line1 VARCHAR(255) NOT NULL,
                city VARCHAR(100) NOT NULL,
                zip_code VARCHAR(20) NOT NULL,
                
                # Payment Details (Masked to store only the last four digits securely)
                card_number_mask VARCHAR(20) NOT NULL,
                status VARCHAR(50) DEFAULT 'Completed'
            )
        """)
        
        db.commit()
        print("Database tables (cart, orders) checked/created successfully.")
    except mysql.connector.Error as err:
        print(f"Error during database setup: {err}")
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

# --- Cart Management Routes (Existing logic maintained) ---

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    db = None
    cursor = None 
    try:
        data = request.get_json()
        item_name = data.get('name')
        price = float(data.get('price'))
        quantity = int(data.get('quantity'))
        
        db = get_db_connection()
        cursor = db.cursor()

        if quantity > 0:
            # Use ON DUPLICATE KEY UPDATE to handle existing items
            upsert_query = """
                INSERT INTO cart (name, price, quantity)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                quantity = VALUES(quantity);
            """
            cursor.execute(upsert_query, (item_name, price, quantity))
        else:
            # Delete item if quantity is set to 0
            delete_query = "DELETE FROM cart WHERE name = %s"
            cursor.execute(delete_query, (item_name,))

        db.commit()
        return jsonify({"message": f"Cart updated successfully for {item_name}.", "quantity": quantity}), 200

    except Exception as e:
        print(f"Error in /add_to_cart: {e}")
        if db:
            db.rollback()
        return jsonify({"message": f"Server error during cart update: {e}"}), 500

    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

@app.route('/get_cart', methods=['GET'])
def get_cart():
    db = None
    cursor = None
    try:
        db = get_db_connection()
        # Use dictionary=True for easier access to column names
        cursor = db.cursor(dictionary=True) 
        cursor.execute("SELECT name, price, quantity FROM cart WHERE quantity > 0")
        cart_items = cursor.fetchall()
        return jsonify(cart_items), 200
    except Exception as e:
        print(f"Error in /get_cart: {e}")
        return jsonify({"message": "Server error retrieving cart."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM cart")
        db.commit()
        return jsonify({"message": "Cart cleared successfully"}), 200
    except Exception as e:
        print(f"Error in /clear_cart: {e}")
        if db:
            db.rollback()
        return jsonify({"message": "Server error clearing cart."}), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

# --- New Checkout Routes ---

def calculate_grand_total(cursor):
    """Calculates the subtotal and grand total from the cart table."""
    # Ensure cursor is dictionary=True for this function to work
    cursor.execute("SELECT SUM(price * quantity) AS subtotal FROM cart")
    result = cursor.fetchone()
    subtotal = float(result['subtotal']) if result and result['subtotal'] else 0.00
    tax = subtotal * TAX_RATE
    grand_total = subtotal + tax
    return subtotal, tax, grand_total

@app.route('/checkout_form', methods=['GET'])
def checkout_form():
    """Renders the HTML form for shipping and payment."""
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        
        # Check if cart is empty before proceeding
        cursor.execute("SELECT COUNT(*) as count FROM cart WHERE quantity > 0")
        if cursor.fetchone()['count'] == 0:
            # Redirect to a generic message page if the cart is empty
            return render_template('checkout_message.html', 
                                   message="Your cart is empty. Please add items to proceed to checkout.", 
                                   is_error=True)

        # Calculate the final total to display on the form
        subtotal, tax, grand_total = calculate_grand_total(cursor)
        
        # Render the form template with calculated totals
        return render_template('checkout_form.html', 
                               total_amount=f"{grand_total:.2f}",
                               subtotal=f"{subtotal:.2f}",
                               tax=f"{tax:.2f}")

    except Exception as e:
        print(f"Error rendering checkout form: {e}")
        return render_template('checkout_message.html', 
                               message="A server error occurred while preparing checkout.", 
                               is_error=True), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()


@app.route('/checkout_order', methods=['POST'])
def checkout_order():
    """Handles form submission, validates data, records order, and clears cart."""
    db = None
    cursor = None
    try:
        form_data = request.form
        
        # 1. Input Validation (Basic Server-Side)
        required_fields = ['customer_name', 'email', 'phone', 'address_line1', 'city', 'zip_code', 'card_number', 'expiry', 'cvv']
        if not all(form_data.get(field) for field in required_fields):
            return render_template('checkout_message.html', 
                                   message="Please fill in all mandatory fields.", 
                                   is_error=True)
            
        # Specific format checks (You can enhance these for production)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", form_data['email']):
            return render_template('checkout_message.html', message="Invalid email format.", is_error=True)
        
        card_number = form_data['card_number']
        if len(card_number) != 16 or not card_number.isdigit():
             return render_template('checkout_message.html', message="Card number must be 16 digits.", is_error=True)

        # 2. Calculate Final Total
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        subtotal, tax, grand_total = calculate_grand_total(cursor)

        if grand_total <= 0:
            return render_template('checkout_message.html', 
                                   message="Order cannot be placed. Your cart is empty.", 
                                   is_error=True)

        # 3. Record the Order
        last_four = card_number[-4:]
        
        insert_order_query = """
        INSERT INTO orders (
            total_amount, customer_name, email, phone, 
            address_line1, city, zip_code, card_number_mask
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        order_data = (
            grand_total, form_data['customer_name'], form_data['email'], form_data['phone'],
            form_data['address_line1'], form_data['city'], form_data['zip_code'], f"**** **** **** {last_four}"
        )
        
        cursor.execute(insert_order_query, order_data)
        
        # 4. Clear the Cart (only on successful order placement)
        cursor.execute("DELETE FROM cart")

        # 5. Commit both operations (order insert and cart clear)
        db.commit()

        # 6. Success Message
        return render_template('checkout_message.html', 
                               message=f"Order (Total: Rs. {grand_total:.2f}) placed successfully!", 
                               order_details=f"Your order ID is {cursor.lastrowid}. A confirmation will follow.",
                               is_error=False)

    except Exception as e:
        print(f"Error during order processing: {e}")
        if db:
            db.rollback()
        return render_template('checkout_message.html', message=f"A critical server error occurred: {e}", is_error=True), 500
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

if __name__ == '__main__':
    setup_database() # Ensure tables are ready when the app starts
    app.run(port=5500, debug=True)
