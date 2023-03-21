from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
import redis
import uuid
import json
import time
import datetime
import re
from mysql.connector import Error
import pyodbc

# CONSTANTS
SERVER = 'python-restful-api.database.windows.net'
DATABASE = 'Python-APi'
USERNAME = 'pythonAdmin'
password = ''
DRIVER = '{ODBC Driver 17 for SQL server}'

CREATE_TABLE_QUERY = """
CREATE TABLE guids (
        guid CHAR(32) PRIMARY KEY,
        metadata VARCHAR(255),
        expiration INT
    )
"""

# GuidHandler contains POST, GET, and DELETE functionality for the guids table in the Python-APi MySQL database hosted on Azure

class GuidHandler(RequestHandler):

    # Initialize GuidHandler with db and cache
    def initialize(self, db, cache):
        self.db = db
        self.cache = cache

    ### POST CALLS ###

    # Create or update a table entry

    def post(self, guid=None):
        # Validate input data is JSON format
        try:
            data = json.loads(self.request.body)
        except Error as err:
            self.set_status(400)
            self.write(f"Error: '{err}'")
            return

        # Set up expiration_time if not given one
        if "expiration" not in data:
            expiration_time = unixtime_30_days_from_now()

        # Otherwise Validate expiration from data
        else:
            expiration_time = int(data["expiration"])
            if not is_valid_unix_time(expiration_time):
                self.set_status(400)
                return

        # Create guid if one is not provided
        if guid is None or guid == '':
            guid = str(uuid.uuid4().hex.upper())
            # Add new entry to the db
            with self.db.cursor() as cursor:
                query = "INSERT INTO guids (guid, metadata, expiration) VALUES (?, ?, ?)"
                cursor.execute(query, (guid, json.dumps(
                    data["metadata"]), expiration_time))

        # Otherwise validate guid and determine if it is a duplicate
        else:
            if (not is_valid_guid(guid)):
                self.set_status(400)
                return
            # Find guid if it exists in db
            with self.db.cursor() as cursor:
                cursor.execute("SELECT * FROM guids WHERE guid=?", guid)
                result = cursor.fetchone()
                # If no match create new entry with given guid
                if result is None:
                    query = "INSERT INTO guids (guid, metadata, expiration) VALUES (?, ?, ?)"
                    cursor.execute(query, (guid, json.dumps(
                        data["metadata"]), expiration_time))
                # If match update the entry
                else:
                    query = "UPDATE guids SET metadata = ?, expiration = ? WHERE guid = ?"
                    cursor.execute(query, json.dumps(
                        data["metadata"]), expiration_time, guid)

        # update the cache with the new or updated GUID and metadata
        self.cache.set(guid, json.dumps(
            {"metadata": data["metadata"], "expiration_time": expiration_time}))

        # Save the changes in the db
        self.db.commit()
        self.set_status(201)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(
            {"guid": guid, "metadata": data["metadata"], "expiration": expiration_time}))
        return

    ### GET CALLS ###

    # Return data for a given GUID

    def get(self, guid=None):
        if guid is None or guid == '':
            self.set_status(400)
            return
        else:
            if not is_valid_guid(guid):
                self.set_status(400)
                return

        # Check the cache for the given guid
        guid_cache = self.cache.get(guid)
        # If it is in the cache - quickly get it and leave
        if guid_cache:
            self.set_status(200)
            data = json.loads(guid_cache)
            self.write(json.dumps(
                {"guid": guid, "metadata": data["metadata"], "expiration": ["expiration"]}))
            return
        # Otherwise look for it in the db
        else:
            with self.db.cursor() as cursor:
                query = "SELECT * FROM guids WHERE guid=?"
                cursor.execute(query, (guid,))
                result = cursor.fetchone()
            # If guid is in the db get the data and add it to the cache
            if result:
                data = json.loads(result)
                self.cache.set(guid, json.dumps(
                    {"metadata": data["metadata"], "expiration": data["expiration"]}))
                self.set_status(200)
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps(
                    {"guid": guid, "metadata": data["metadata"], "expiration": ["expiration"]}))
            # If guid is not in db - Not Found
            else:
                self.set_status(404)
        return

    ### DELETE CALLS ###

    # Delete entry given a guid

    def delete(self, guid=None):
        if guid is None or guid == '':
            self.set_status(400)
            return
        else:
            if not is_valid_guid(guid):
                self.set_status(400)
                return

        # Deletes the entry if guid exists in the db
        with self.db.cursor() as cursor:
            query = "DELETE FROM guids WHERE guid=?"
            cursor.execute(query, (guid))
        # If it did not exists - Not Found
        if cursor.rowcount == 0:
            self.set_status(404)
            return
        # If guid existed - delete from cache and save db
        self.cache.delete(guid)
        self.db.commit()
        self.set_status(204)
        return


### UTILITY FUNCTIONS ###

# Connect to DB using pyodbc
def create_server_connection():
    connection = None
    password = input("DB Password: ")
    try:
        connection = pyodbc.connect(
            f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={password}')
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


# Create a database given a connection and query
def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("DB Created Successfully")
    except Error as err:
        print(f"Error: '{err}'")


# Validates that a given guid is a len of 32, uppercase, and alphanumeric
def is_valid_guid(guid):
    pattern = re.compile("^[A-F0-9]{32}$")
    return bool(pattern.match(guid))


# Validate that a given timestamp is in Unix Time
def is_valid_unix_time(timestamp):
    try:
        time.gmtime(timestamp)
        return True
    except ValueError:
        return False


# Return unix time 30 days from now as an integer
def unixtime_30_days_from_now():
    now = datetime.datetime.now()
    future_30_days = now + datetime.timedelta(days=30)
    unix_time = int(time.mktime(future_30_days.timetuple()))
    return unix_time


### MAIN ###

if __name__ == '__main__':
    connection = create_server_connection()
    # UNCOMMENT BELOW TO CREATE DB
    # create_database(connection, CREATE_TABLE_QUERY)
    # connection.commit()

    # Connect to redis server
    redis_password = input("Redis Server Password: ")
    cache = redis.Redis(
        host='redis-16801.c53.west-us.azure.cloud.redislabs.com',
        port=16801,
        password=redis_password)

    # Start up tornado app
    app = Application(
        [(r"/guids/?(.*)", GuidHandler, dict(db=connection, cache=cache))])
    app.listen(8888)

    # Starts the Tornado web server and keeps it running
    IOLoop.current().start()
