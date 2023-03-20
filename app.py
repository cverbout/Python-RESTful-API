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
### TODO ####
# 1. EDIT -- CHECK
# 2. CACHE -- CHECK
# 3. VALIDATE
# 4. CLEAN
# 5. DOCUMENT

#class MainHandler(RequestHandler):
 # async def get(self):
  #  self.application.cache = redis.cache

class GuidHandler(RequestHandler):
  def initialize(self, db, cache):
    self.db = db
    self.cache = cache

  def set_default_headers(self):
    self.set_header("Content-Type", "application/json")

  
  ### POST CALLS ###
  
  # Create a table entry
  def post(self, guid=None):
    # Get the JSON data
    data = json.loads(self.request.body)

    # Set guid cache key
    guid_cache_key = f"guid:{guid}"

    # Set up expiration_time if not given one
    if "expiration" not in data:
      expiration_time = unixtime_30_days_from_now()

    # Validate expiration from data
    else:
      expiration_time = int(data["expiration"])
      if not is_valid_unix_time(expiration_time):
        self.set_status(400)
        return
    self.write("1")
    # Create guid if one is not provided
    if guid is None or guid == '':
      print("1")
      guid = str(uuid.uuid4().hex.upper())
      # Add data to the db
      with self.db.cursor() as cursor:
        query = "INSERT INTO guids (guid, metadata, expiration) VALUES (?, ?, ?)"        
        cursor.execute(query, (guid, json.dumps(data["metadata"]), expiration_time))
        
      #self.db.commit()
    # Validate guid (is it uppercase, hexidecimal, 32bit)
    else:
      print("2")
      if(not is_valid_guid(guid)):
        self.set_status(400)
        return 
      with self.db.cursor() as cursor:
        cursor.execute("SELECT * FROM guids WHERE guid=?", guid)
        result = cursor.fetchone()
        if result is None:
          print("3")
          query = "INSERT INTO guids (guid, metadata, expiration) VALUES (?, ?, ?)"
          cursor.execute(query, (guid, json.dumps(data["metadata"]), expiration_time))
        else:  
          print("4")
          query = "UPDATE guids SET metadata = ?, expiration = ? WHERE guid = ?"
          cursor.execute(query, json.dumps(data["metadata"]), expiration_time, guid)
      #self.db.commit()
    
    # update the cache with the new or updated GUID and metadata
    self.cache.set(guid, json.dumps({"metadata": data["metadata"], "expiration_time": expiration_time}))
    self.db.commit()
    # Success Status
    self.set_status(201) 
    # Write out what you saved for reference
    self.write(json.dumps({"guid": guid, "metadata": data["metadata"], "expiration": expiration_time}))
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
    
    guid_cache = self.cache.get(guid)
    if guid_cache:
      print("used cache")
      self.set_status(200)
      self.write(json.loads(guid_cache))
    else:
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
        self.cache.set(guid, json.dumps({"metadata": data["metadata"], "expiration": data["expiration"]}))
        self.write(data)
        self.set_status(200)
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
    self.cache.delete(guid)
    self.db.commit()
    self.set_status(200)



### UTILITY FUNCTIONS ###

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
  cache = redis.Redis(
  host='redis-16801.c53.west-us.azure.cloud.redislabs.com',
  port=16801,
  password='0KbfXGvDePtVK1GaRTCRDFQGz73HKcMC')
  #create_database(connection, CREATE_TABLE_QUERY)
  #connection.commit()
  app = Application([(r"/guids/?(.*)", GuidHandler, dict(db=connection, cache=cache))])
  app.listen(8888)
  IOLoop.current().start()
  #connection.close()
