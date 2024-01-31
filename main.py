from flask import Flask, render_template, request, redirect, session, flash
from flask_mail import Mail, Message
import pyrebase
from datetime import datetime

from requests import HTTPError

from pypaystack import Transaction
from utilities import string_to_datetime, toDateTime, defaultDateTimeFormat, getPaymentDate, send_mail, over_booking, \
    event_dict, get_min_date, archive, format_currency

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'Insert email here'
app.config['MAIL_PASSWORD'] = 'insert password here'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
app.secret_key = "Something Ominous"
config = {
    "apiKey": "AIzaSyDrY5Bjm-xTvqX5x-Qisx77zyTnqBcb7JU",
    "authDomain": "my-flask-app-392616.firebaseapp.com",
    "projectId": "my-flask-app-392616",
    "storageBucket": "my-flask-app-392616.appspot.com",
    "messagingSenderId": "718690831357",
    "appId": "1:718690831357:web:2327ec5d9838c4fc0be794",
    "measurementId": "G-N53S6X0HBV",
    "databaseURL": "https://my-flask-app-392616-default-rtdb.firebaseio.com/"
}
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
transactions = Transaction(authorization_key="sk_test_7e4d1f1b634b8817e2eb350f9bc4465b4c6c6295")
DEPOSIT = 100000
PRICE = 400000
app.jinja_env.globals.update(string_to_datetime=string_to_datetime, transactions=transactions,
                             getPaymentDate=getPaymentDate, datetime=datetime, get_min_date=get_min_date,
                             deposit=DEPOSIT, price=PRICE, format_currency=format_currency, len=len)
last_upcoming_event_index = 0


@app.route("/", methods=["GET", "POST"])
def home():
    archive(db)
    global last_upcoming_event_index
    if "user" in session:
        user = session["user"]
        events = db.child("events").order_by_child("event_time").get().each()
        if request.method == "POST":
            search_entry = request.form.get("search")
            if events is None: return render_template("index.html", user=user, events=[])
            upcoming_events = events[:last_upcoming_event_index]
            search_results = []
            for event in upcoming_events:
                if event.val()["booking_code"] == search_entry:
                    search_results.append(event)
                elif event.val()["last_name"] == search_entry:
                    search_results.append(event)
            flash(f"Search results for '{search_entry}'")
            return render_template("index.html", user=user, events=search_results)
        else:
            if events is None: return render_template("index.html", user=user, events=[])
            for event in events:
                event_value = event.val()
                if string_to_datetime(event_value["event_time"]) >= datetime.utcnow():
                    last_upcoming_event_index += 1
            upcoming_events = events[:last_upcoming_event_index]
            return render_template("index.html", user=user, events=upcoming_events)
    else:
        return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session["user"] = email
            return redirect("/")
        except HTTPError:
            flash("Invalid Email or Password")
            return redirect("/login")
    else:
        if "user" in session:
            return redirect("/")
        return render_template("login.html")


@app.route("/delete/<booking_code>")
def delete(booking_code):
    if "user" in session:
        event = db.child("events").child(booking_code).get().val()
        db.child("events").child(booking_code).remove()
        send_mail(mail, event, "cancelled", string_to_datetime(event["event_time"]))
        return redirect("/")
    return redirect("/login")


@app.route("/details/<booking_code>")
def details(booking_code):
    if "user" in session:
        event = db.child("events").child(booking_code).get().val()
        event_time = string_to_datetime(event["event_time"])
        month = defaultDateTimeFormat(event_time.month)
        day = defaultDateTimeFormat(event_time.day)
        hour = defaultDateTimeFormat(event_time.hour)
        minute = defaultDateTimeFormat(event_time.minute)
        return render_template("details.html", event=event, event_time=event_time,
                               month=month, day=day, hour=hour, minute=minute)
    return redirect("/login")


@app.route("/historyDetails/<booking_code>")
def historyDetails(booking_code):
    if "user" in session:
        event = db.child("history").child(booking_code).get().val()
        event_time = string_to_datetime(event["event_time"])
        month = defaultDateTimeFormat(event_time.month)
        day = defaultDateTimeFormat(event_time.day)
        hour = defaultDateTimeFormat(event_time.hour)
        minute = defaultDateTimeFormat(event_time.minute)
        return render_template("history_details.html", event_time=event_time, event=event, month=month, day=day,
                               hour=hour, minute=minute)
    return redirect("/login")


@app.route("/edit/<booking_code>", methods=["GET", "POST"])
def edit(booking_code):
    if "user" in session:
        edit_event = db.child("events").child(booking_code).get().val()
        event_time = string_to_datetime(edit_event["event_time"])
        month = defaultDateTimeFormat(event_time.month)
        day = defaultDateTimeFormat(event_time.day)
        hour = defaultDateTimeFormat(event_time.hour)
        minute = defaultDateTimeFormat(event_time.minute)
        if request.method == "POST":
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            email = request.form.get("email")
            number = request.form.get("number")
            event = request.form.get("event")
            people = request.form.get("people")
            date_out = toDateTime(request.form.get("event_time"))
            if over_booking(date_out, db):
                if event_time.year == date_out.year and event_time.month == date_out.month \
                        and event_time.day == date_out.day:
                    pass
                else:
                    return render_template("details.html", errMessage="Day has already been booked", event=edit_event)
                event_time_new = str(date_out).replace(" ", "-").replace(":", "-")
                updated_event = event_dict(first_name=first_name, booking_code=booking_code,
                                           event_id=edit_event["id"], last_name=last_name,
                                           email=email, number=number, event=event, people=people,
                                           event_time=event_time_new)
                db.child("events").child(booking_code).update(updated_event)
                send_mail(mail, updated_event, "updated", date_out)
                flash("Update Successful! Please Refresh This Page")
            return render_template("details.html", event=edit_event, event_time=event_time, month=month, day=day,
                                   hour=hour, minute=minute)
        else:
            month = defaultDateTimeFormat(event_time.month)
            day = defaultDateTimeFormat(event_time.day)
            hour = defaultDateTimeFormat(event_time.hour)
            minute = defaultDateTimeFormat(event_time.minute)
            return render_template("edit.html", event=edit_event, event_time=event_time, month=month, day=day,
                                   hour=hour, minute=minute)
    return redirect("/login")


@app.route("/schedule")
def schedule():
    events = db.child("events").get().each() if db.child("events").get().each() is not None else []
    dates = ""
    for event in events:
        formatted_date = event.val()["event_time"][:10]
        dates += f"|{formatted_date}"
    # dates = dates.split("|")
    return render_template("schedule.html", dates=dates)


@app.route("/pay/<booking_code>/<payment_category>", methods=["GET", "POST"])
def pay(booking_code, payment_category):
    mail_title = ""
    mail_body = ""
    flash_message = ""
    if "user" in session:
        event = db.child("events").child(booking_code).get().val()
        if request.method == "POST":
            deposit = int(request.form.get("deposit"))
            new_payment = deposit + event["payment"]
            deposit_formatted = format_currency(deposit)
            db.child("events").child(booking_code).update({"payment": new_payment, "payment_status": f"Deposit Made:{deposit_formatted}"})
            mail_title = "Deposit Payment Confirmation"
            mail_body = f"""Hi {event['first_name']},
                        This email is to confirm that we have received your deposit of {deposit_formatted}.
                        Thank you for your patronage."""
            flash_message = f"Deposit made successfully!: {deposit_formatted}"
        # if payment_category == "deposit":
        #     db.child("events").child(booking_code).update({"payment": 100000, "payment_status": "Deposit Made"})
        #     mail_title = "Deposit Payment Confirmation"
        #     mail_body = f"""Hi {event['first_name']},
        #     This email is to confirm that we have received your deposit of N100,000.
        #     Thank you for your patronage."""
        #     flash_message = "Deposit made successfully!: N100,000"
        if payment_category == "complete":
            db.child("events").child(booking_code).update({"payment": PRICE, "payment_status": f"Payment Completed: {format_currency(PRICE)}"})
            mail_title = "Payment Confirmation"
            mail_body = f"""Hi {event['first_name']},
                       This email is to confirm that we have received your complete payment of {format_currency(PRICE)}.
                       Thank you for your patronage."""
            flash_message = f"Payment Completed Successfully!: {format_currency(PRICE)}"
        elif payment_category == "d_complete":
            db.child("events").child(booking_code).update({"payment": PRICE, "payment_status": f"Payment Completed: {format_currency(PRICE)}"})
            mail_title = "Payment Completed Confirmation"
            mail_body = f"""Hi {event['first_name']},
                       This email is to confirm that we have received your residual payment of {format_currency(PRICE-event["payment"])}.
                       Thank you for your patronage."""
            flash_message = f"Payment Completed Successfully!: {format_currency(PRICE-event['payment'])}"
        msg_us = Message(
            mail_title, sender='knightp550@gmail.com',
            recipients=[event["email"]])
        msg_us.body = mail_body
        mail.send(msg_us)
        flash(flash_message)
        return redirect(f"/details/{booking_code}")
    else:
        return redirect("/login")


@app.route("/create", methods=["GET", "POST"])
def create():
    if "user" in session:
        if request.method == "POST":
            first_name = request.form.get("create_first_name")
            last_name = request.form.get("create_last_name")
            email = request.form.get("create_email")
            number = request.form.get("create_number")
            event = request.form.get("create_event")
            people = request.form.get("create_people")
            date_in = request.form.get("create_event_time")
            date_out = toDateTime(date_in)
            date_viewing = date_in.replace('T', '').replace(':', '').split('-')
            date_viewing = "".join(v for v in date_viewing)

            if over_booking(date_out, db):
                return render_template("create.html", errMessage="Day has already been booked")
            # Created a reservation code based on information from the reservation
            try:
                get_id = list(db.child("events").get().val().keys())
                last_entry_key = get_id[-1]
                last_entry_id = db.child("events").child(last_entry_key).child("id").get().val()
                id = last_entry_id + 1
            except AttributeError:
                id = 1
            booking_code = event[2].lower() + event[0].lower() + \
                           event[1].lower() + date_viewing + str(id)
            date_out_final = str(date_out).replace(" ", "-").replace(":", "-")
            new_event = event_dict(first_name=first_name, booking_code=booking_code, last_name=last_name, email=email,
                                   number=number, event=event, people=people, event_time=date_out_final, event_id=id)
            new_event["dep_ref_code"] = 0
            new_event["ref_code"] = 0
            db.child("events").child(booking_code).set(new_event)
            send_mail(mail, new_event, "booked", date_out)
            flash(f"Event created successfully! A confirmatory email has been sent to {first_name} {last_name}")
            return render_template("create.html")
        else:
            return render_template("create.html")
    return redirect("/login")


@app.route("/history", methods=["GET", "POST"])
def history():
    global last_upcoming_event_index
    if "user" in session:
        events = db.child("history").order_by_child("event_time").get().each()
        quarter = len(events) // 4
        half = len(events) // 2
        full = len(events)
        events.reverse()
        if request.method == "POST":
            # Get index subscript from form
            data_filter = request.form.get("data_filter")
            # Check if the form submitted was for data filtering or searching
            if data_filter is not None:
                return render_template("history.html", events=events[:int(data_filter)], show_filter=True,
                                       data_filter=int(data_filter), quarter=quarter, half=half, full=full)
            search_entry = request.form.get("search")
            search_results = []
            for event in events:
                if event.val()["booking_code"] == search_entry:
                    search_results.append(event)
                elif event.val()["last_name"] == search_entry:
                    search_results.append(event)
            flash(f"Search results for '{search_entry}'")
            return render_template("history.html", events=search_results, show_filter=False)
        if len(events) > 15:
            return render_template("history.html", events=events[:15], show_filter=True, data_filter=15,
                                   quarter=quarter, half=half, full=full)
        return render_template("history.html", events=events, show_filter=True, data_filter=full, quarter=quarter,
                               half=half, full=full)
    else:
        return redirect("/login")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
