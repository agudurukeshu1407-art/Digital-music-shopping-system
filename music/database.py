
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Hari@44110032",
    "database": "music_eshoppe",
    "port": 3306
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

        connection.close()

    except Error as error:
        print("Database connection error:", error)

    return None
