import os

username = os.environ.get("USERNAME")
password = os.environ.get("PASS")
user_email = os.environ.get("EMAIL")
user_email_password = os.environ.get("EMAIL_PASS")
email_to = os.environ.get("EMAIL_TO")
limit_of_pending = int(os.environ.get("LIMIT_PENDING"))
runtime_limit = int(os.environ.get("RUN_TIME_LIMIT"))
ban_limit = int(os.environ.get("BAN_LIMIT"))
database_url = os.environ.get("DATABASE_URL")