import pymysql
import hashlib
import uuid
import os
from datetime import datetime, timedelta
from jinja2 import Environment
from flask import Flask, render_template, request, redirect, session, flash
app = Flask(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app.secret_key = "any-random-string-reshrdjtfkygluvchfjkhlbh"


def create_connection():
    return pymysql.connect(
        host="10.0.0.17",
        user="fremu",
        # host="127.0.0.1",
        # user="root",
        password="ARENA",
        db="fremu_test",
        # db="user_management",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


# User can access if matching id or is admin
def can_access(id):
    if "logged_in" in session:
        matching_id = session["id"] == int(id)
        is_admin = session["role"] == "admin"
        return matching_id or is_admin


# Encrypts the password
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
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s"

            values = (
                request.args['id']
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()

            sql = """SELECT * FROM posts
                    LEFT JOIN users ON posts.user_id = users.id WHERE users.id = %s
                """

            values = {
                session["id"]
            }
            cursor.execute(sql, values)
            result2 = cursor.fetchall()
    return render_template("view.html", result=result, result2=result2)


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

            sql = """SELECT * FROM posts
                    LEFT JOIN users ON posts.user_id
                    = users.id WHERE users.id = %s
                """

            values = {
                session["id"]
            }
            cursor.execute(sql, values)
            result2 = cursor.fetchall()
    return render_template("viewprofile.html", result2=result2, result=result)


# Feed Page
@app.route("/feed")
def feed():
    env = Environment()
    env.filters['reversed'] = reversed
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM posts LEFT JOIN users AS post_users ON posts.user_id = post_users.id
                    LEFT JOIN comments ON comments.post_id = posts.post_id LEFT JOIN users AS comment_users ON comments.user_id
                     = comment_users.id WHERE post_users.id != %s
                """
            cursor.execute(sql, session["id"])
            result = cursor.fetchall()
    return render_template("feed.html", result=result)


# Add Post function
@app.route("/post/add", methods=["GET", "POST"])
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

                image = request.files["cover_img"]
                if image:
                    # Choose a random filename to prevent clashes
                    ext = os.path.splitext(image.filename)[1]
                    filename = str(uuid.uuid4())[:8] + ext
                    image_path = os.path.join("static", "images", filename)
                    image.save(image_path)
                else:
                    image_path = None

                sql = "INSERT INTO posts (content, audio, genre, cover_img, user_id, song_name, artist) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                values = (request.form['content'], audio_path, request.form["genre"], image_path, session["id"], request.form["song"], request.form["artist"])
                cursor.execute(sql, values)
                connection.commit()
                flash("Posted Successfully", "success")
        return render_template("post_add.html")

    else:
        return render_template("post_add.html")


# Login Page
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT * FROM users
                         WHERE (email = %s OR username = %s) AND password = %s"""

                values = (
                    request.form["email"],
                    request.form["username"],
                    encrypt(request.form["password"])
                )

                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
            session["logged_in"] = True
            session["id"] = result["id"]
            session["first_name"] = result["first_name"]
            session["role"] = result["role"]
            flash("Logged In", "success")
            return redirect("/feed")

        else:
            flash("Incorrect Email or Password", "warning")
            redirect('/login')
    return render_template("login.html")


# Log out of account
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Check if email exists on sign up
def email_exists(email):
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            values = (email)
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return result is not None


# Sign up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if email_exists(request.form["email"]):
            flash("That email already exists.", "info")
            return redirect("/signup")

        dob = datetime.strptime(request.form["dateofbirth"], "%Y-%m-%d")
        min_dob = datetime.now() - timedelta(days=14*365)  # 14 years old
        if dob >= min_dob:
            flash("You must be at least 14 years old to sign up", "info")
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
                    (first_name, last_name, email,
                    username, password, dateofbirth, image)
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


#/update?id=1
@app.route("/update", methods=["GET", "POST"])
def update():
    if not can_access(request.args["id"]):
        flash("You don't have permission to do that", "warning")
        return redirect('/feed')

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
                    username = %s,
                    password = %s,
                    dateofbirth = %s,
                    image = %s
                    WHERE id = %s
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    request.form['username'],
                    encrypted_password,
                    request.form['dateofbirth'],
                    image_path,
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect("/viewprofile")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users where id = %s"
                values = (session["id"])
                cursor.execute(sql, values)
                result = cursor.fetchone()
        return render_template("update.html", result=result)


# Deletion of Posts
@app.route("/delete")
def delete():
    # Check if user has permission to delete post   
    if not can_access(request.args["user_id"]):
        flash("You don't have permission to do that", "warning")
        return redirect('/feed')

    with create_connection() as connection:
        with connection.cursor() as cursor:
            # Get the audio path before deleting the user
            sql = """SELECT * FROM posts
                LEFT JOIN users ON posts.user_id = users.id WHERE users.id = %s"""
            values = (request.args["id"])
            cursor.execute(sql, values)

            # Check if the audio file ex
            if "audio" in request.args and request.args["audio"] is not None and request.args["audio"]:
                audio_file = request.args["audio"]
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            else:
                pass

            if "image" in request.args and request.args["image"] is not None and request.args["image"]:
                image_file = request.args["image"]
                if os.path.exists(image_file):
                    os.remove(image_file)
            else:
                pass

            sql = "DELETE FROM posts WHERE post_id = %s"
            values = (request.args["id"])
            cursor.execute(sql, values)
            connection.commit()
            flash("Post has been deleted successfully", "success")
    return redirect("/viewprofile")


# Update Own Posts
@app.route("/my_posts/edit", methods=["GET", "POST"])
def updatepost(): 
    # if not can_access(request.args["id"]):
    #     flash("You don't have permission to do that")
    #     return redirect('/')

    
    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:

                image = request.files["cvrimage"]

                if image:
                    ext = os.path.splitext(image.filename)[1]
                    image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
                    image.save(image_path)

                    if request.form["old_image"]:
                        if os.path.exists(request.form["old_image"]):
                            os.remove(request.form["old_image"])
                        else:
                            # Handle the case when the file doesn't exist
                            flash("Previous image file not found", "warning")
                else:
                    image_path = request.form["old_image"]

                sql = """UPDATE posts SET
                        content = %s,
                        cover_img = %s
                        WHERE post_id = %s
                    """

                if not request.form['content']:
                    values = (
                        request.form["old_content"],
                        request.form["old_image"],
                        request.args['id']
                    )
                else:
                    values = (
                        request.form['content'],
                        image_path,
                        request.args['id']
                    )

                cursor.execute(sql, values)
                connection.commit()
        return redirect("/my_posts/edit?id=" + request.args["id"])
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users where id = %s"
                values = (session["id"])
                cursor.execute(sql, values)
                result = cursor.fetchone()

                sql = """SELECT * FROM posts
                    LEFT JOIN users ON posts.user_id = users.id WHERE post_id = %s
                """
                cursor.execute(sql, request.args["id"])
                result2 = cursor.fetchone()
        return render_template("editpost.html", result=result, result2 = result2)


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
        flash("You don't have permission to do that!", "warning")
    return redirect("/")

# Likes -------------------------------------------------------------------------------------------------------------------------------------------------

# Checks if the user has already liked the post
def user_liked(user_id, post_id):
    connection = create_connection()

    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM likes WHERE user_id = %s AND post_id = %s"
            cursor.execute(sql, (user_id, post_id))
            result = cursor.fetchone()

            if result:
                return True
            else:
                return False
    finally:
        connection.close()


# Adding like into database
def add_like(user_id, post_id):
    connection = create_connection()

    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO likes (user_id, post_id) VALUES (%s, %s)"
            cursor.execute(sql, (user_id, post_id))
        connection.commit()
    finally:
        connection.close()


# Updating likes count
def update_likes(post_id2):
    connection = create_connection()

    try:
        with connection.cursor() as cursor:
            likes_sql = "SELECT COUNT(*) FROM likes WHERE post_id = %s"
            cursor.execute(likes_sql, (post_id2,))
            result = cursor.fetchone()

            if result is not None and 'COUNT(*)' in result:
                count = result['COUNT(*)']
            else:
                count = 0

            update_sql = "UPDATE posts SET likes_count = %s WHERE post_id = %s"
            cursor.execute(update_sql, (count, post_id2))

        connection.commit()
    finally:
        connection.close()

# User dislikes after liking the post
def remove_like(user_id, post_id):
    connection = create_connection()

    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM likes WHERE user_id = %s AND post_id = %s"
            cursor.execute(sql, (user_id, post_id))
        connection.commit()
    finally:
        connection.close()


# Function to handle the post likes
@app.route("/feed/like", methods=["POST"])
def like_post():
    user_id = session["id"]
    post_id = request.form["post_id"] 
    post_id2 = post_id


    # Checks if user liked, else add like
    if request.form["action"] == "like":
        if user_liked(user_id, post_id):
            flash("Already Liked", "info")
        else:
            add_like(user_id, post_id)

    # Dislikes if there is a like, else pass
    elif request.form["action"] == "dislike":
        if user_liked(user_id, post_id):
            remove_like(user_id, post_id)
        else:
            flash("No like to dislike", "info")

    # update like count on post
    update_likes(post_id2)
    return redirect('/feed')


#COMMENTS -------------------------------------------------------------------------------------------------------------------------------------------------

# insert comment into database
def add_comment(user_id, post_id, comment):
    connection = create_connection()
    try:
        with connection.cursor() as cursor:
            if comment:
                sql = "INSERT INTO comments (user_id, post_id, comment) VALUES (%s, %s, %s)"
                cursor.execute(sql, (user_id, post_id, comment))
            else:
                pass
        connection.commit()
    finally:
        connection.close()

# def delete_comment(user_id, post_id, comment):
#     connection = create_connection()

#     if not can_access(request.args["comments_users.id"]):
#         flash("You don't have permission to do that")
#         return redirect('/feed')

#     try:
#         with connection.cursor() as cursor:
#             sql = "DELETE FROM comments WHERE comments.id = %s AND user = %s"
#             cursor.execute(sql, (, post_id))
#         connection.commit()
#     finally:
#         connection.close()


# Function to handle comment processes
@app.route("/feed/comment")
def comment():
    user_id = session["id"]
    post_id = request.args["post_id"] 
    comment = request.args["comment"]

    add_comment(user_id, post_id, comment)

    return redirect('/feed')


@app.route("/view_post")
def viewpost():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM posts 
                    LEFT JOIN users ON posts.user_id = users.id WHERE post_id = %s
                """
            cursor.execute(sql, request.args["id"])
            result = cursor.fetchone()

            
    return render_template("view_post.html", result=result)


app.run(debug = True)