
import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Hari@44110032",
        database="music_eshoppe",
        port=3306
    )

    if connection.is_connected():
        print("SUCCESS: Python is connected to MySQL!")

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        print("Connected database:", cursor.fetchone()[0])

        cursor.execute("SHOW TABLES")
        print("Tables:", [row[0] for row in cursor.fetchall()])

        cursor.close()
        connection.close()

except Error as error:
    print("CONNECTION FAILED:", error)
