import tkinter as tk
from tkinter import messagebox
import mysql.connector
from datetime import datetime
import re

# --- Database Configuration (Copied from your app.py for consistency) ---
DB_CONFIG = {
    'host': "localhost",          
    'user': "root",       
    'password': "Samiya@17", 
    'database': "starsucks_db" 
}

# --- Database Setup Helper ---
def create_orders_table():
    """Ensures the necessary 'orders' table exists with all required fields."""
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        
        # NOTE: Using IF NOT EXISTS will create the table only if it doesn't exist.
        # If the table already exists but without these columns, you would need to run ALTER TABLE.
        # For simplicity, we assume the table needs to be created or already matches this schema.
        create_table_query = """
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
            
            # Payment Details
            payment_method VARCHAR(50) NOT NULL,
            card_number_mask VARCHAR(20) NOT NULL,
            status VARCHAR(50) DEFAULT 'Completed'
        )
        """
        cursor.execute(create_table_query)
        db.commit()
        print("MySQL 'orders' table checked/created successfully.")
    except mysql.connector.Error as err:
        print(f"Error checking/creating 'orders' table: {err}")
    finally:
        if cursor: cursor.close()
        if db and db.is_connected(): db.close()

# --- Main Checkout Application Class ---
class CheckoutApp:
    def __init__(self, master):
        self.master = master
        master.title("Starsucks Secure Checkout")
        master.geometry("600x700")
        
        # Simulated Total (In a real scenario, this would be fetched from the database)
        self.grand_total = 899.75
        
        self.style_config()
        create_orders_table() 
        
        self.create_widgets()

    def style_config(self):
        self.main_bg = "#f4f4f4"
        self.green = "#00704A"
        self.white = "#ffffff"
        self.master.configure(bg=self.main_bg)

    def create_widgets(self):
        # Main container frame
        main_frame = tk.Frame(self.master, bg=self.white, padx=25, pady=25, bd=1, relief="groove")
        main_frame.pack(fill='both', expand=True, padx=30, pady=30)

        # Title
        tk.Label(main_frame, text="Secure Checkout", font=("Poppins", 20, "bold"), fg=self.green, bg=self.white).pack(pady=(0, 10))
        
        # Total Display
        tk.Label(main_frame, text=f"Order Total: Rs. {self.grand_total:.2f}", 
                 font=("Poppins", 15, "bold"), bg="#fcfcfc", fg="#333", 
                 padx=10, pady=10, borderwidth=1, relief="solid").pack(pady=(5, 20), fill='x')

        # Scrollable area for the form
        canvas = tk.Canvas(main_frame, bg=self.white)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.white)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- Form Sections ---
        self.entry_vars = {}
        
        # 1. Shipping Details Section
        self.create_form_section(scrollable_frame, "Shipping and Contact Information", [
            ("Customer Name", 'customer_name', None),
            ("Email Address", 'email', self.validate_email),
            ("Phone Number", 'phone', self.validate_phone),
            ("Address Line 1", 'address_line1', None),
            ("City", 'city', None),
            ("Zip/Postal Code", 'zip_code', self.validate_zip)
        ], start_row=0)

        # 2. Payment Details Section
        self.create_form_section(scrollable_frame, "Payment Information", [
            ("Card Number", 'card_number', self.validate_card_number),
            ("Name on Card (as per bank)", 'name_on_card', None),
            ("Expiry (MM/YY)", 'expiry', self.validate_expiry),
            ("CVV", 'cvv', self.validate_cvv)
        ], start_row=10, is_payment=True)
        
        # Submit Button
        submit_button = tk.Button(main_frame, text="Pay Now & Complete Order", command=self.process_payment,
                                  font=("Poppins", 14, "bold"), bg=self.green, fg=self.white, 
                                  activebackground="#00563C", activeforeground=self.white,
                                  cursor="hand2", width=30, pady=10)
        submit_button.pack(pady=(20, 10))

        # Instructions/Disclaimer
        tk.Label(main_frame, text="All card data is simulated and not stored for security.", 
                 font=("Poppins", 9, "italic"), fg="#888", bg=self.white).pack(pady=5)
                 
    def create_form_section(self, parent, title, fields, start_row, is_payment=False):
        
        tk.Label(parent, text=title, font=("Poppins", 13, "bold"), fg="#555", bg=self.white, anchor="w").grid(row=start_row, column=0, columnspan=2, sticky="w", pady=(15, 5))
        
        for i, (label_text, key, validate_func) in enumerate(fields):
            row = start_row + i + 1
            tk.Label(parent, text=label_text + ":", font=("Poppins", 10), bg=self.white, anchor="w").grid(row=row, column=0, sticky="w", pady=5, padx=5)
            
            var = tk.StringVar(self.master)
            entry = tk.Entry(parent, textvariable=var, font=("Poppins", 11), width=45, bd=1, relief="solid")
            entry.grid(row=row, column=1, pady=5, padx=5, ipady=4, sticky="ew")
            
            self.entry_vars[key] = var
            
            if validate_func:
                vcmd = (self.master.register(validate_func), '%P')
                entry.config(validate='key', validatecommand=vcmd)
            
            # Special setting for CVV
            if key == "cvv":
                entry.config(show="*")

    # --- Input Validation Methods ---
    def validate_card_number(self, P):
        """Allows only digits and limits length to 16."""
        if P.isdigit() or P == "":
            return len(P) <= 16
        return False

    def validate_cvv(self, P):
        """Allows only digits and limits length to 4."""
        if P.isdigit() or P == "":
            return len(P) <= 4
        return False
        
    def validate_expiry(self, P):
        """Allows MM/YY format."""
        if re.match(r'^(\d{0,2}/?\d{0,2})$', P) is None and P != "":
            return False
            
        if len(P) > 5:
            return False

        current_text = self.entry_vars["expiry"].get()
        if len(current_text) == 2 and len(P) == 3 and P.isdigit():
            self.entry_vars["expiry"].set(current_text + '/' + P[2])
            return False 

        return True
    
    def validate_email(self, P):
        """Simple email validation check."""
        if P == "": return True
        # Basic check for @ and . (too strict for keypress, so we rely on final validation)
        # For keypress validation, we only ensure no invalid characters are used
        return True # For simplicity in Tkinter key validation
        
    def validate_phone(self, P):
        """Allows only digits, spaces, hyphens, and limits length."""
        if re.match(r'^[\d\s-]*$', P) is None:
            return False
        return len(P) <= 15
        
    def validate_zip(self, P):
        """Allows only digits and limits length."""
        if P.isdigit() or P == "":
            return len(P) <= 10
        return False

    # --- Payment Processing & Database Interaction ---
    def process_payment(self):
        # 1. Gather and Validate Data
        data = {key: var.get().strip() for key, var in self.entry_vars.items()}
        
        # Mandatory fields validation
        if not all(data.values()):
            messagebox.showerror("Error", "All fields are mandatory. Please fill in all shipping and payment details.")
            return

        # Detailed validation
        if len(data['card_number']) != 16 or not data['card_number'].isdigit():
            messagebox.showerror("Error", "Please enter a valid 16-digit card number.")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
            messagebox.showerror("Error", "Please enter a valid email address.")
            return

        # 2. Simulate Payment Gateway Check (Always successful for this simulation)
        is_successful = True
        
        if is_successful:
            # 3. Handle Database Operations
            try:
                self.record_order_and_clear_cart(data)
                messagebox.showinfo("Success", f"Order Placed! Rs. {self.grand_total:.2f} charged successfully.\n\nThank you, {data['customer_name']}!")
                self.master.destroy() # Close the app on success
            except Exception as e:
                messagebox.showerror("Database Error", f"Payment successful, but failed to save order or clear cart: {e}")
        else:
            messagebox.showerror("Error", "Payment failed. Please check your card details.")


    def record_order_and_clear_cart(self, data):
        """
        Records the order and clears the cart in the MySQL database.
        """
        db = None
        cursor = None
        try:
            db = mysql.connector.connect(**DB_CONFIG)
            cursor = db.cursor()

            # 1. Record the Order
            last_four = data['card_number'][-4:]
            
            insert_order_query = """
            INSERT INTO orders (
                total_amount, customer_name, email, phone, 
                address_line1, city, zip_code, payment_method, card_number_mask
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Credit Card', %s)
            """
            order_data = (
                self.grand_total, data['customer_name'], data['email'], data['phone'],
                data['address_line1'], data['city'], data['zip_code'], f"**** **** **** {last_four}"
            )
            
            cursor.execute(insert_order_query, order_data)
            
            # 2. Clear the Cart
            clear_cart_query = "DELETE FROM cart"
            cursor.execute(clear_cart_query)

            # 3. Commit both operations
            db.commit()

        except mysql.connector.Error as err:
            db.rollback()
            raise Exception(f"MySQL Error: {err}") 
        finally:
            if cursor: cursor.close()
            if db and db.is_connected(): db.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = CheckoutApp(root)
    root.mainloop()
