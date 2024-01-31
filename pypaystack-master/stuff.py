# from pypaystack import transactions
from pypaystack.transactions import Transaction
from datetime import datetime

def toDateTime(html_dtObject):
    date_processing = html_dtObject.replace(
        'T', '-').replace(':', '-').replace(".000Z", "").split('-')
    date_processing = [int(v) for v in date_processing]
    date_out = datetime(*date_processing)
    return date_out

transactions = Transaction(authorization_key="sk_test_7e4d1f1b634b8817e2eb350f9bc4465b4c6c6295")
response = transactions.verify(381417848)
paid_datetime_formated = toDateTime(response[3]["paid_at"])
print(int(response[3]["amount"] / 100))

