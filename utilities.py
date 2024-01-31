"""
    This file contains helper functions and classes
"""

from flask_mail import Message
from datetime import datetime
import locale


# Custom error message for invalid mail criteria: ['booked', 'updated', 'cancelled']
class MailError(Exception):
    pass


def event_dict(event_id, first_name, booking_code, last_name, email, number, event, people, event_time):
    table_format = {"id": event_id, "booking_code": booking_code, "first_name": first_name, "last_name": last_name,
                    "email": email, "number": number, "event": event, "people": people, "event_time": event_time,
                    "payment": 0, "payment_status": "No Payment Made"}
    return table_format


def format_currency(amount):
    return '₦{:20,.2f}'.format(amount)


def over_booking(date, db):
    events = db.child("events").get()
    if events.each() is None: return False
    for event in events.each():
        event_time_db = event.val()["event_time"].split("-")
        event_time = datetime(int(event_time_db[0]), int(event_time_db[1]), int(event_time_db[2]), int(event_time_db[3])
                              , int(event_time_db[4]))
        if event_time.year == date.year and event_time.month == date.month \
                and event_time.day == date.day:
            return True
    return False


def string_to_datetime(str_object):
    dt_list = str_object.split("-")
    for i in range(len(dt_list)):
        dt_list[i] = int(dt_list[i])
    dt_object = datetime(dt_list[0], dt_list[1], dt_list[2], dt_list[3], dt_list[4])
    return dt_object


def send_mail(mail_client, receiver, mail_criteria, date_out):
    mail_options = ["booked", "updated", "cancelled"]
    receiver_email = receiver["email"]
    print(receiver)
    msg_client = Message(
        'Palm Center', sender='knightp550@gmail.com', recipients=[receiver_email])
    if mail_criteria.lower() not in mail_options:
        raise MailError("Invalid Mail Criteria. Expecting either 'booked', 'updated', or 'cancelled'")
    msg_client.body = f"""Hi {receiver["first_name"]},\nYour event has been {mail_criteria}. 
    See details of your event below;\n
    Full Name: {receiver["first_name"]} {receiver["last_name"]}\nPhone Number: {receiver["number"]}\n
    Booking Code: {receiver["booking_code"]}\nEvent: {receiver["event"]}\n
    Number of People: {receiver["people"]}\nEvent Date: {date_out.strftime("%a, %B %d, %Y")}\n
    Event Time: {date_out.strftime("%I:%M %p")}"""
    mail_client.send(msg_client)


def getPaymentDate(ref, transactions):
    response = transactions.verify(ref)
    print(response)
    paid_datetime_formatted = toDateTime(response[3]["paid_at"].replace(".000Z", ""))
    return paid_datetime_formatted


# Archives past events
def archive(db):
    events = db.child("events").get().each()
    if events is not None:
        for event in events:
            if string_to_datetime(event.val()["event_time"]) < datetime.utcnow():
                db.child("history").child(event.val()["booking_code"]).set(event.val())
                db.child("events").child(event.val()["booking_code"]).remove()


# Takes in HTML Datetime object and converts to Python Datetime Object
def toDateTime(html_dtObject):
    date_processing = html_dtObject.replace(
        'T', '-').replace(':', '-').split('-')
    date_processing = [int(v) for v in date_processing]
    date_out = datetime(*date_processing)
    return date_out


# Formats Datetime objects
def defaultDateTimeFormat(dt_object):
    if len(str(dt_object)) == 1:
        format_date = "0" + str(dt_object)
        return format_date
    return dt_object


def get_min_date():
    dt_now = datetime.utcnow()
    dt_now_year = dt_now.year
    dt_now_month = dt_now.month
    if dt_now_month < 10:
        dt_now_month = "0" + str(dt_now_month)
    dt_now_day = dt_now.day
    if dt_now_day < 10:
        dt_now_day = "0" + str(dt_now_day)
    return f"{dt_now_year}-{dt_now_month}-{dt_now_day}T00:00"


def time_details_format(event):
    event_time = string_to_datetime(event["event_time"])
    year = event_time.year
    month = defaultDateTimeFormat(event_time.month)
    day = defaultDateTimeFormat(event_time.day)
    hour = defaultDateTimeFormat(event_time.hour)
    minute = defaultDateTimeFormat(event_time.minute)
    return year, month, day, hour, minute
