from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "farmerqueue-secret-key"


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            village TEXT NOT NULL,
            district TEXT NOT NULL,
            state TEXT NOT NULL,
            centre TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            centre TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            crop TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            token INTEGER,
            status TEXT DEFAULT 'Waiting',
            payment_status TEXT DEFAULT 'Pending',
            amount REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ================= HOME =================

@app.route("/")
def home():
    return render_template("index.html")


# ================= FARMER REGISTER =================

@app.route("/farmer-register", methods=["GET", "POST"])
def farmer_register():

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        password = request.form["password"]
        village = request.form["village"]
        district = request.form["district"]
        state = request.form["state"]
        centre = request.form["centre"]

        conn = sqlite3.connect("farmerqueue.db")
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO farmers
                (name, phone, password, village, district, state, centre)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                phone,
                password,
                village,
                district,
                state,
                centre
            ))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return """
            <h2>This mobile number is already registered.</h2>
            <a href="/farmer-register">Try Again</a>
            """

        conn.close()

        return """
        <h2>Registration successful!</h2>
        <p>Farmer account created successfully.</p>
        <a href="/farmer-login">Go to Farmer Login</a>
        """

    return render_template("farmer_register.html")


# ================= FARMER LOGIN =================

@app.route("/farmer-login", methods=["GET", "POST"])
def farmer_login():

    if request.method == "POST":

        phone = request.form["phone"]
        password = request.form["password"]

        conn = sqlite3.connect("farmerqueue.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM farmers
            WHERE phone = ? AND password = ?
        """, (phone, password))

        farmer = cursor.fetchone()

        conn.close()

        if farmer:

            session["farmer_id"] = farmer[0]

            return redirect("/farmer-dashboard")

        return """
        <h2>Invalid mobile number or password.</h2>
        <a href="/farmer-login">Try Again</a>
        """

    return render_template("farmer_login.html")


# ================= FARMER DASHBOARD =================

@app.route("/farmer-dashboard")
def farmer_dashboard():

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM farmers
        WHERE id = ?
    """, (farmer_id,))

    farmer = cursor.fetchone()

    booking = None
    all_bookings = []

    if farmer:

        # Latest booking of logged-in farmer
        cursor.execute("""
            SELECT * FROM bookings
            WHERE farmer_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (farmer_id,))

        booking = cursor.fetchone()

        # All bookings for viewing all tokens
        cursor.execute("""
            SELECT * FROM bookings
            ORDER BY date, time, token
        """)

        all_bookings = cursor.fetchall()

    conn.close()

    if farmer:

        return render_template(
            "farmer_dashboard.html",
            farmer=farmer,
            booking=booking,
            all_bookings=all_bookings
        )

    session.clear()

    return redirect("/farmer-login")


# ================= BOOK SLOT =================

@app.route("/book-slot", methods=["GET", "POST"])
def book_slot():

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    if request.method == "POST":

        centre = request.form["centre"]
        date = request.form["date"]
        time = request.form["time"]
        crop = request.form["crop"]
        quantity = request.form["quantity"]

        conn = sqlite3.connect("farmerqueue.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(token)
            FROM bookings
            WHERE centre = ?
            AND date = ?
            AND time = ?
        """, (centre, date, time))

        result = cursor.fetchone()

        if result[0] is None:
            token = 1
        else:
            token = result[0] + 1

        cursor.execute("""
            INSERT INTO bookings
            (
                farmer_id,
                centre,
                date,
                time,
                crop,
                quantity,
                token,
                status,
                payment_status,
                amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            farmer_id,
            centre,
            date,
            time,
            crop,
            quantity,
            token,
            "Waiting",
            "Pending",
            0
        ))

        booking_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO notifications
            (farmer_id, title, message)
            VALUES (?, ?, ?)
        """, (
            farmer_id,
            "Slot Booked",
            f"Your slot is booked successfully. Your queue token is {token}."
        ))

        conn.commit()
        conn.close()

        return f"""
        <html>
        <head>
            <title>Slot Booked</title>
        </head>
        <body>

        <h1>Slot Booked Successfully!</h1>

        <h2>Your Queue Token</h2>

        <h1>Token Number: {token}</h1>

        <p>Centre: {centre}</p>
        <p>Date: {date}</p>
        <p>Time: {time}</p>
        <p>Crop: {crop}</p>
        <p>Quantity: {quantity} kg</p>

        <br>

        <a href="/queue/{booking_id}">
            <button>View Live Queue</button>
        </a>

        <br><br>

        <a href="/procurement-status/{booking_id}">
            <button>View Procurement Status</button>
        </a>

        <br><br>

        <a href="/payment-status/{booking_id}">
            <button>View Payment Status</button>
        </a>

        <br><br>

        <a href="/notifications">
            <button>View Notifications</button>
        </a>

        <br><br>

        <a href="/farmer-dashboard">
            <button>Back to Dashboard</button>
        </a>

        </body>
        </html>
        """

    return render_template("book_slot.html")


# ================= LIVE QUEUE =================

@app.route("/queue/<int:booking_id>")
def live_queue(booking_id):

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bookings
        WHERE id = ?
        AND farmer_id = ?
    """, (booking_id, farmer_id))

    booking = cursor.fetchone()

    if booking is None:
        conn.close()
        return "Booking not found."

    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE centre = ?
        AND date = ?
        AND time = ?
        AND token < ?
        AND status != 'Completed'
    """, (
        booking[2],
        booking[3],
        booking[4],
        booking[7]
    ))

    farmers_ahead = cursor.fetchone()[0]

    conn.close()

    waiting_time = farmers_ahead * 10

    return render_template(
        "queue.html",
        booking=booking,
        farmers_ahead=farmers_ahead,
        waiting_time=waiting_time
    )


# ================= VIEW ANY TOKEN =================

@app.route("/view-token/<int:booking_id>")
def view_token(booking_id):

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bookings
        WHERE id = ?
    """, (booking_id,))

    booking = cursor.fetchone()

    conn.close()

    if booking is None:
        return "Booking not found."

    # Open the individual live queue page
    return redirect(f"/queue/{booking_id}")


# ================= PROCUREMENT STATUS =================

@app.route("/procurement-status/<int:booking_id>")
def procurement_status(booking_id):

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bookings
        WHERE id = ?
        AND farmer_id = ?
    """, (booking_id, farmer_id))

    booking = cursor.fetchone()

    conn.close()

    if booking is None:
        return "Booking not found."

    return render_template(
        "procurement_status.html",
        booking=booking
    )


# ================= PAYMENT STATUS =================

@app.route("/payment-status/<int:booking_id>")
def payment_status(booking_id):

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bookings
        WHERE id = ?
        AND farmer_id = ?
    """, (booking_id, farmer_id))

    booking = cursor.fetchone()

    conn.close()

    if booking is None:
        return "Booking not found."

    return render_template(
        "payment_status.html",
        booking=booking
    )


# ================= NOTIFICATIONS =================

@app.route("/notifications")
def notifications():

    farmer_id = session.get("farmer_id")

    if farmer_id is None:
        return redirect("/farmer-login")

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, message
        FROM notifications
        WHERE farmer_id = ?
        ORDER BY id DESC
    """, (farmer_id,))

    notifications_list = cursor.fetchall()

    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications_list
    )


# ================= CENTRE DASHBOARD =================

@app.route("/centre-dashboard")
def centre_dashboard():

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bookings
        ORDER BY date, time, token
    """)

    bookings = cursor.fetchall()

    conn.close()

    return render_template(
        "centre_dashboard.html",
        bookings=bookings
    )


# ================= UPDATE PROCUREMENT STATUS =================

@app.route("/update-status/<int:booking_id>", methods=["POST"])
def update_status(booking_id):

    status = request.form["status"]

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (status, booking_id))

    cursor.execute("""
        SELECT farmer_id, token
        FROM bookings
        WHERE id = ?
    """, (booking_id,))

    booking = cursor.fetchone()

    if booking:

        farmer_id = booking[0]
        token = booking[1]

        cursor.execute("""
            INSERT INTO notifications
            (farmer_id, title, message)
            VALUES (?, ?, ?)
        """, (
            farmer_id,
            "Procurement Update",
            f"Your procurement status for token {token} is now {status}."
        ))

    conn.commit()
    conn.close()

    return redirect("/centre-dashboard")


# ================= UPDATE PAYMENT AMOUNT =================

@app.route("/update-payment/<int:booking_id>", methods=["POST"])
def update_payment(booking_id):

    amount = request.form["amount"]

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET amount = ?
        WHERE id = ?
    """, (amount, booking_id))

    conn.commit()
    conn.close()

    return redirect("/centre-dashboard")


# ================= UPDATE PAYMENT STATUS =================

@app.route("/update-payment-status/<int:booking_id>", methods=["POST"])
def update_payment_status(booking_id):

    payment_status = request.form["payment_status"]

    conn = sqlite3.connect("farmerqueue.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET payment_status = ?
        WHERE id = ?
    """, (payment_status, booking_id))

    cursor.execute("""
        SELECT farmer_id, amount, token
        FROM bookings
        WHERE id = ?
    """, (booking_id,))

    booking = cursor.fetchone()

    if booking:

        farmer_id = booking[0]
        amount = booking[1]
        token = booking[2]

        if payment_status == "Paid":

            message = (
                f"Payment of Rs.{amount} for token {token} "
                f"has been processed successfully."
            )

        else:

            message = (
                f"Payment for token {token} is currently pending."
            )

        cursor.execute("""
            INSERT INTO notifications
            (farmer_id, title, message)
            VALUES (?, ?, ?)
        """, (
            farmer_id,
            "Payment Update",
            message
        ))

    conn.commit()
    conn.close()

    return redirect("/centre-dashboard")


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ================= START APPLICATION =================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)