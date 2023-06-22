import pymysql
import hashlib
import uuid
import os
from flask import Flask, render_template, request, redirect, session, flash
app = Flask(__name__)

app.secret_key = "any-random-string-reshrdjtfkygluvchfjkhlbh"


def create_connection():
    return pymysql.connect(
        host="10.0.0.17",
        user="fremu",
        # host="127.0.0.1",
        # user="root",
        password="ARENA",
        db="fremu_test",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def can_access(id):
    if "logged_in" in session:
        matching_id = session["id"] == int(request.args["id"])
        is_admin = session["role"] == "admin"
        return matching_id or is_admin


def encrypt(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Home Page
@app.route("/")
def home():
    with create_connection() as connection: 
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users"
            cursor.execute(sql)
            result = cursor.fetchall()
    return render_template("home.html", result=result)

# View Page
@app.route("/view")
def view_user():
    if not can_access(request.args["id"]):
        flash("You don't have permission to do that")
        return redirect('/')
        
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s"

            values = (
                request.args['id']
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return render_template("view.html", result=result)

# View Page
@app.route("/viewprofile")
def view_profile():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s"

            values = (
                session["id"]
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return render_template("viewprofile.html", result=result)

# /post?id=1
@app.route("/feed")
def feed():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM posts 
                    LEFT JOIN users ON posts.user_id = users.id 
                """
            # values = (  
            #     request.args['id'] #change this to be for all users
            # )
            cursor.execute(sql)
            result = cursor.fetchall()
    return render_template("feed.html", result=result)

@app.route("/post/add", methods = ["GET", "POST"])
def add_post():
    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:

                audio = request.files["audio"]
                if audio:
                    # Choose a random filename to prevent clashes
                    ext = os.path.splitext(audio.filename)[1]
                    audio_path = "static/audio/" + str(uuid.uuid4())[:8] + ext
                    audio.save(audio_path)
                else:
                    audio_path = None

                sql = "INSERT INTO posts (content, audio, user_id) VALUES (%s, %s, %s)"
                values = (request.form['content'], audio_path, session["id"])
                cursor.execute(sql, values)
                connection.commit()
        return render_template("post_add.html") 
    else:
        return render_template("post_add.html")  

# Login Page
@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == "POST": 
        with create_connection() as connection:
            with connection.cursor() as cursor: 
                sql = """SELECT * FROM users 
                WHERE email = %s or username = %s AND password = %s"""

                values = (
                    request.form["email"],
                    request.form["username"],
                    encrypt(request.form["password"])
                )

                cursor.execute(sql,values)
                result = cursor.fetchone()
        if result:
            session["logged_in"] = True
            session["id"] = result["id"]
            session["first_name"] = result["first_name"]
            session["role"] = result["role"]
            return redirect("/")
        else:
            flash("Incorrect Email or Password")
            redirect('/login')
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Sign up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":  
        if email_exists(request.form["email"]):
            flash("That email already exists.")
            return redirect("/signup")

        with create_connection() as connection:
            with connection.cursor() as cursor: 

                image = request.files["image"]
                if image:
                    # Choose a random filename to prevent clashes
                    ext = os.path.splitext(image.filename)[1]
                    image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
                    image.save(image_path)
                else:
                    image_path = None

                sql = """INSERT INTO users
                    (first_name, last_name, email, username, password, dateofbirth, image)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                values = (
                    request.form["first_name"],
                    request.form["last_name"],
                    request.form["email"],
                    request.form["username"],
                    encrypt(request.form["password"]),
                    request.form["dateofbirth"], 
                    image_path 
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect("/login")
    else:
        return render_template("signup.html")


# TODO: UPDATE 
#/update?id=1
@app.route("/update", methods = ["GET", "POST"])
def update(): 
    if not can_access(request.args["id"]):
        flash("You don't have permission to do that")
        return redirect('/')

    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:

                password = request.form["password"]
                if password:
                    encrypted_password = encrypt(password)
                else:
                    encrypted_password = request.form["old_password"]

                image = request.files["image"]

                if image:
                    ext = os.path.splitext(image.filename)[1]
                    image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
                    image.save(image_path)
                    if request.form["old_image"]:
                        os.remove(request.form["old_image"])
                else:
                    image_path = request.form["old_image"]

                sql = """UPDATE users SET 
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    password = %s,
                    dateofbirth = %s,
                    image = %s
                    WHERE id = %s
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    request.form['dateofbirth'],
                    image_path,
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect("/")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users where id = %s"
                values = (request.args["id"])
                cursor.execute(sql, values)
                result = cursor.fetchone()
        return render_template("update.html", result=result)



# DELETE
#/update?id=1
@app.route("/delete")
def delete():
    if not can_access(request.args["id"]):
        flash("You don't have permission to do that")
        return redirect('/')

    with create_connection() as connection:
            with connection.cursor() as cursor: 
                # Get the image path before deleting the user
                sql = "SELECT image FROM users WHERE id = %s"
                values = (request.args["id"])
                cursor.execute(sql, values)
                result = cursor.fetchone()
                if result["image"]:
                    os.remove(result["image"])

                sql = "DELETE FROM users WHERE id = %s"
                values = (request.args["id"])
                cursor.execute(sql, values)
                connection.commit()
    return redirect("/")


# /admin?id=1&role=admin
@app.route("/admin")
def toggle_admin():
    if "logged_in" in session and session["role"] == "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "UPDATE users SET role = %s WHERE id = %s"
                values = (
                    request.args["role"],
                    request.args["id"]
                )
                cursor.execute(sql, values)
                connection.commit()
    else:
        flash("You don't have permission to do that!")
    return redirect("/")   

# Check Email
def email_exists(email):
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            values = (email)
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return result is not None


app.run(debug = True)