from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
import redis
import uuid
import json
import time
import datetime
import re
import mysql.connector
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

# Connect to DB using pyodbc
def create_server_connection():
    connection = None
    password = input("DB Password: ")
    try:
        connection = pyodbc.connect(f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={password}')
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


 
#class MainHandler(RequestHandler):
 # async def get(self):
  #  self.application.cache = redis.cache

class GuidHandler(RequestHandler):
  def initialize(self, db):
        self.db = db

  def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

  
  ### POST CALLS ###
  
  # Create a table entry
  def post(self, guid=None):

    # Create guid if one is not provided
    if guid is None or guid == '':
      guid = str(uuid.uuid4().hex.upper())

    # Validate guid (is it uppercase, hexidecimal, 32bit)
    else:
        if(not is_valid_guid(guid)):
            self.set_status(400)
            return
    
    # Get the JSON data
    data = json.loads(self.request.body)

    # Set up expiration_time if not given one
    if "expiration" not in data:
      expiration_time = unixtime_30_days_from_now()

    # Validate expiration from data
    else:
      expiration_time = data["expiration"]
      if not is_valid_unix_time(expiration_time):
          self.set_status(400)
          return
    
    # Add data to the db
    with self.db.cursor() as cursor:
          query = "INSERT INTO guids (guid, metadata, expiration) VALUES (?, ?, ?)"        
          cursor.execute(query, (guid, json.dumps(data["metadata"]), expiration_time))
    self.db.commit()
    # Success Status
    self.set_status(201) 
    # Write out what you saved for reference
    self.write(json.dumps({"guid": guid, "metadata": data["metadata"], "expiration": expiration_time}))
    return
  


  # Edit a table entry
  def post(self, guid=None):
   if guid is None or guid == '':
      self.set_status(400)
      return
   else:
       if not is_valid_guid(guid):
          self.set_status(400)
          return
   data = json.load(self.request.body)



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
    
    with self.db.cursor() as cursor:
       query = "SELECT * FROM guids WHERE guid=?"
       cursor.execute(query, (guid,))
       result = cursor.fetchone()

    if result:
       data = {
          "GUID": result[0],
          "metadata": json.loads(result[1]),
          "expiration": result[2],
       }
       self.set_header("Content-Type", "application/json")
       self.write(data)
    else:
       self.set_status(400)
       self.write("GUID not found")



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
  
  # Deletes the entry
  with self.db.cursor() as cursor:
     query = "DELETE FROM guids WHERE guid=?"
     cursor.execute(query, (guid))
  self.db.commit()
  self.set_status(200)



### UTILITY FUNCTIONS ###

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
   unixtime_30_days_from_now()
   connection = create_server_connection()
   #create_database(connection, CREATE_TABLE_QUERY)
   #connection.commit()
   app = Application([(r"/guids/?(.*)", GuidHandler, dict(db=connection))])
   app.listen(8888)
   IOLoop.current().start()
   #connection.close()
