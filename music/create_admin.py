
from getpass import getpass
from werkzeug.security import generate_password_hash
from database import get_connection

username = input("Enter admin username: ").strip()
password = getpass("Enter admin password: ")

if not username or len(password) < 8:
    print("Username is required and password must be at least 8 characters.")
else:
    connection = get_connection()

    if connection is None:
        print("Database connection failed. Check database.py.")
    else:
        cursor = None
        try:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT admin_id FROM admins WHERE username = %s",
                (username,)
            )

            if cursor.fetchone():
                print("This admin username already exists.")
            else:
                password_hash = generate_password_hash(password)

                cursor.execute(
                    """INSERT INTO admins (username, password_hash)
                       VALUES (%s, %s)""",
                    (username, password_hash)
                )
                connection.commit()
                print("Admin account created successfully!")

        except Exception as error:
            connection.rollback()
            print("Error:", error)

        finally:
            if cursor:
                cursor.close()
            connection.close()
