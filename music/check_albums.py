
import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Hari@44110032",
    database="music_eshoppe"
)

cursor = connection.cursor()

cursor.execute("""
    SELECT album_id, movie_name, album_name, price
    FROM albums
""")

for album in cursor.fetchall():
    print(album)

cursor.close()
connection.close()
