# Python-RESTful-API

## Overview
This project is a web application for managing Globally Unique Identifiers (GUIDs). It represents my first foray into backend development with Python, utilizing the Tornado web framework. The application offers functionalities such as creating, retrieving, and deleting GUIDs, and interfaces with a MySQL database for storage, along with Redis for efficient caching. 

## Learning Journey
As my first attempt at learning backend skills in Python, this project served as a practical introduction to several key concepts and technologies in web development, including asynchronous programming, database management, and server-side logic.

## Architecture
- **Tornado Framework**: A Python asynchronous networking library, forming the core of the web server.
- **Redis**: Used for high-performance in-memory data caching.
- **MySQL Database**: Handles persistent storage of GUIDs and associated metadata.
- **PyODBC**: Connects the application to the SQL database.

## Requirements
- Python 3.9
- Project dependencies as listed in the provided `Pipfile`.

## Setup Instructions
1. Install Python 3.9 on your system.
2. Clone the repository to your local machine.
3. Install the required dependencies: `pip install Pipfile`
4. Set up and configure your MySQL and Redis instances according to the application's requirements.

## Usage and Validation
- Run the Tornado server to launch the web application.
- The application's endpoints for managing GUIDs include:
  - **POST**: Create or update a GUID.
  - **GET**: Retrieve a GUID and its metadata.
  - **DELETE**: Delete a GUID.
- I used Postman to validate the functionality of these endpoints, ensuring correct behavior and responses.

## Notes
- Detailed information on each endpoint, including expected request formats and responses, is available in the `app.py` file.
- Ensure your database and cache instances are properly configured and secure for use with the application.

