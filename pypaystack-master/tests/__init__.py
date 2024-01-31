import os
import time
from unittest import TestCase
from uuid import uuid4

from pypaystack import Customer, Plan, Transaction

test_auth_key = os.getenv('PAYSTACK_AUTHORIZATION_KEY')
