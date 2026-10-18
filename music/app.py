
import os
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, abort
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from werkzeug.utils import secure_filename
from database import get_connection


app = Flask(__name__)

# --------------------------------------------------
# FLASK SETTINGS
# --------------------------------------------------

app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY",
    "replace-this-with-a-random-secret"
)

MUSIC_FOLDER = os.path.join(
    app.root_path, "uploads", "music"
)
COVER_FOLDER = os.path.join(
    app.root_path, "static", "uploads", "covers"
)

os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(COVER_FOLDER, exist_ok=True)

ALLOWED_MUSIC = {"mp3", "wav", "ogg", "m4a"}
ALLOWED_COVERS = {"jpg", "jpeg", "png", "webp"}

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


def allowed_file(filename, extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in extensions
    )


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not email or not password:
            flash("Please fill in all required fields.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        connection = get_connection()
        if connection is None:
            flash("Database connection failed.")
            return redirect(url_for("register"))

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                (email,)
            )

            if cursor.fetchone():
                flash("Email already registered.")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
            """, (name, email, password_hash))

            connection.commit()
            flash("Account created successfully. Please log in.")
            return redirect(url_for("login"))

        except Exception:
            connection.rollback()
            app.logger.exception("Registration failed")
            flash("Unable to create account.")

        finally:
            if cursor:
                cursor.close()
            connection.close()

    return render_template("register.html")


# --------------------------------------------------
# USER LOGIN
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()
        if connection is None:
            flash("Database connection failed.")
            return render_template("login.html")

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"], password
            ):
                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                return redirect(url_for("home"))

            flash("Invalid email or password.")

        except Exception:
            app.logger.exception("User login failed")
            flash("Unable to log in.")

        finally:
            if cursor:
                cursor.close()
            connection.close()

    return render_template("login.html")


# --------------------------------------------------
# USER HOME PAGE
# --------------------------------------------------

@app.route("/home")
def home():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template("home.html")


# --------------------------------------------------
# USER LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()
        if connection is None:
            flash("Database connection failed.")
            return render_template("admin_login.html")

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM admins WHERE username = %s",
                (username,)
            )
            admin = cursor.fetchone()

            if admin and check_password_hash(
                admin["password_hash"], password
            ):
                session.clear()
                session["admin_id"] = admin["admin_id"]
                session["admin_username"] = admin["username"]
                return redirect(url_for("admin_dashboard"))

            flash("Invalid admin username or password.")

        except Exception:
            app.logger.exception("Admin login failed")
            flash("Unable to log in.")

        finally:
            if cursor:
                cursor.close()
            connection.close()

    return render_template("admin_login.html")


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    return render_template("admin_dashboard.html")


# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# --------------------------------------------------
# ADD ALBUM
# --------------------------------------------------

@app.route("/admin/add-album", methods=["GET", "POST"])
def add_album():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        movie_name = request.form.get("movie_name", "").strip()
        album_name = request.form.get("album_name", "").strip()
        artist = request.form.get("artist", "").strip()
        release_year = request.form.get("release_year", "").strip()
        description = request.form.get("description", "").strip()
        price_text = request.form.get("price", "").strip()

        music_file = request.files.get("music_file")
        cover_file = request.files.get("cover_file")

        if not all([
            movie_name, album_name, artist,
            release_year, price_text,
            music_file, cover_file
        ]):
            flash("Please fill in all required fields.")
            return render_template("add_album.html")

        if not music_file.filename or not cover_file.filename:
            flash("Please select both music and cover files.")
            return render_template("add_album.html")

        if not allowed_file(music_file.filename, ALLOWED_MUSIC):
            flash("Unsupported music format.")
            return render_template("add_album.html")

        if not allowed_file(cover_file.filename, ALLOWED_COVERS):
            flash("Unsupported cover image format.")
            return render_template("add_album.html")

        try:
            year = int(release_year)
            price = float(price_text)

            if year < 1800 or year > 2100 or price < 0:
                raise ValueError

        except ValueError:
            flash("Enter a valid year and non-negative price.")
            return render_template("add_album.html")

        music_name = (
            str(uuid.uuid4()) + "_" +
            secure_filename(music_file.filename)
        )
        cover_name = (
            str(uuid.uuid4()) + "_" +
            secure_filename(cover_file.filename)
        )

        music_path = os.path.join(MUSIC_FOLDER, music_name)
        cover_path = os.path.join(COVER_FOLDER, cover_name)

        connection = get_connection()
        if connection is None:
            flash("Database connection failed.")
            return render_template("add_album.html")

        cursor = None
        music_saved = False
        cover_saved = False

        try:
            music_file.save(music_path)
            music_saved = True

            cover_file.save(cover_path)
            cover_saved = True

            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO albums (
                    movie_name, album_name, artist,
                    release_year, description, price,
                    cover_image, music_path
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                movie_name,
                album_name,
                artist,
                year,
                description,
                price,
                "uploads/covers/" + cover_name,
                music_name
            ))

            connection.commit()
            flash("Album added successfully!")
            return redirect(url_for("manage_albums"))

        except Exception:
            connection.rollback()
            app.logger.exception("Adding album failed")

            if music_saved and os.path.isfile(music_path):
                os.remove(music_path)

            if cover_saved and os.path.isfile(cover_path):
                os.remove(cover_path)

            flash("Unable to add album. Please check the details.")

        finally:
            if cursor:
                cursor.close()
            connection.close()

    return render_template("add_album.html")


# --------------------------------------------------
# MUSIC CATALOGUE
# --------------------------------------------------

@app.route("/music")
def music_catalogue():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = get_connection()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("home"))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
    SELECT album_id, movie_name, album_name, artist,
           release_year, description, price, cover_image
    FROM albums
    WHERE is_active = 1
    ORDER BY album_id DESC
""")


        albums = cursor.fetchall()
        return render_template("music.html", albums=albums)

    except Exception:
        app.logger.exception("Loading catalogue failed")
        flash("Unable to load the music catalogue.")
        return redirect(url_for("home"))

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# BUY ALBUM - DEMO PURCHASE, NO REAL PAYMENT
# --------------------------------------------------

@app.route("/buy/<int:album_id>", methods=["POST"])
def buy_album(album_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    connection = get_connection()

    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("music_catalogue"))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT album_id, price
            FROM albums
            WHERE album_id = %s
        """, (album_id,))
        album = cursor.fetchone()

        if not album:
            flash("Album not found.")
            return redirect(url_for("music_catalogue"))

        cursor.execute("""
            SELECT p.purchase_id
            FROM purchases p
            JOIN purchase_items pi
              ON pi.purchase_id = p.purchase_id
            WHERE p.user_id = %s
              AND pi.album_id = %s
              AND p.status = 'COMPLETED'
            LIMIT 1
        """, (user_id, album_id))

        if cursor.fetchone():
            flash("You have already purchased this album.")
            return redirect(url_for("my_music"))

        cursor.execute("""
            INSERT INTO purchases (user_id, total_amount, status)
            VALUES (%s, %s, 'COMPLETED')
        """, (user_id, album["price"]))

        purchase_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO purchase_items (
                purchase_id, album_id, price
            )
            VALUES (%s, %s, %s)
        """, (purchase_id, album_id, album["price"]))

        connection.commit()
        flash("Demo purchase successful! Your album is now purchased.")
        return redirect(url_for("my_music"))

    except Exception:
        connection.rollback()
        app.logger.exception("Purchase failed")
        flash("Unable to complete the demo purchase.")
        return redirect(url_for("music_catalogue"))

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# MY MUSIC - PURCHASED ALBUMS
# --------------------------------------------------

@app.route("/my-music")
def my_music():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = get_connection()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("home"))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT
                a.album_id,
                a.movie_name,
                a.album_name,
                a.artist,
                a.release_year,
                a.cover_image
            FROM purchases p
            JOIN purchase_items pi
              ON pi.purchase_id = p.purchase_id
            JOIN albums a
              ON a.album_id = pi.album_id
            WHERE p.user_id = %s
              AND p.status = 'COMPLETED'
            ORDER BY a.album_id DESC
        """, (session["user_id"],))

        albums = cursor.fetchall()
        return render_template("my_music.html", albums=albums)

    except Exception:
        app.logger.exception("Loading My Music failed")
        flash("Unable to load your music.")
        return redirect(url_for("home"))

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# PLAY A PURCHASED ALBUM
# --------------------------------------------------

@app.route("/play/<int:album_id>")
def play_album(album_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    connection = get_connection()
    if connection is None:
        abort(503)

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.music_path
            FROM albums a
            JOIN purchase_items pi ON pi.album_id = a.album_id
            JOIN purchases p ON p.purchase_id = pi.purchase_id
            WHERE a.album_id = %s
              AND p.user_id = %s
              AND p.status = 'COMPLETED'
            LIMIT 1
        """, (album_id, session["user_id"]))

        album = cursor.fetchone()

        if not album:
            abort(403)

        filename = album["music_path"]

    finally:
        if cursor:
            cursor.close()
        connection.close()

    if not filename or os.path.basename(filename) != filename:
        abort(404)

    filepath = os.path.join(MUSIC_FOLDER, filename)

    if not os.path.isfile(filepath):
        abort(404)

    extension = os.path.splitext(filename)[1].lower()
    mimetypes = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4"
    }

    return send_file(
        filepath,
        mimetype=mimetypes.get(extension, "application/octet-stream"),
        as_attachment=False
    )


# --------------------------------------------------
# MANAGE ALBUMS
# --------------------------------------------------

@app.route("/admin/manage-albums")
def manage_albums():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    connection = get_connection()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("admin_dashboard"))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT album_id, movie_name, album_name, artist,
                   release_year, price, cover_image
            FROM albums
            ORDER BY album_id DESC
        """)

        albums = cursor.fetchall()
        return render_template("manage_albums.html", albums=albums)

    except Exception:
        app.logger.exception("Loading album management failed")
        flash("Unable to load albums.")
        return redirect(url_for("admin_dashboard"))

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# DELETE ALBUM
# Keeps purchase history safe
# --------------------------------------------------

@app.route(
    "/admin/delete-album/<int:album_id>",
    methods=["POST"]
)
def delete_album(album_id):
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    connection = get_connection()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("manage_albums"))

    cursor = None
    try:
        cursor = connection.cursor()

        cursor.execute("""
    UPDATE albums
    SET is_active = 0
    WHERE album_id = %s
""", (album_id,))
        
        if cursor.fetchone() is None:
            flash("Album not found.")
            return redirect(url_for("manage_albums"))

        cursor.execute("""
            SELECT COUNT(*)
            FROM purchase_items
            WHERE album_id = %s
        """, (album_id,))

        purchase_count = cursor.fetchone()[0]

        if purchase_count > 0:
            flash(
                "This album has purchase history and cannot be "
                "deleted. Purchase records have been preserved."
            )
            return redirect(url_for("manage_albums"))

        cursor.execute(
            "DELETE FROM albums WHERE album_id = %s",
            (album_id,)
        )
        connection.commit()
        flash("Album deleted successfully!")

    except Exception:
        connection.rollback()
        app.logger.exception("Album deletion failed")
        flash("Unable to delete album.")

    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for("manage_albums"))


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
