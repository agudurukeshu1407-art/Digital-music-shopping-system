
from getpass import getpass
from werkzeug.security import generate_password_hash
from database import get_connection

username = input("Enter admin username (admin): ").strip()
password = getpass("Enter your new password: ")
confirm_password = getpass("Confirm your new password: ")

if not username:
    print("Username cannot be empty.")
elif len(password) < 8:
    print("Password must be at least 8 characters long.")
elif password != confirm_password:
    print("Passwords do not match.")
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
            admin = cursor.fetchone()

            if admin is None:
                print("Admin username not found.")
            else:
                password_hash = generate_password_hash(password)

                cursor.execute(
                    "UPDATE admins SET password_hash = %s WHERE username = %s",
                    (password_hash, username)
                )
                connection.commit()
                print("Admin password reset successfully!")

        except Exception as error:
            connection.rollback()
            print("Error:", error)

        finally:
            if cursor:
                cursor.close()
            connection.close()
