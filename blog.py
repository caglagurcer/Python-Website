from ast import Return
from colorama import Cursor
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

#login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Please login to view this page","danger")
            return redirect(url_for("login"))
        
    return decorated_function
#user registration form
class RegisterForm(Form):
    name = StringField("Name", validators = [validators.Length(min = 3, max = 25)])
    username = StringField("Username", validators = [validators.Length(min = 3, max = 35)])
    email = StringField("email", validators = [validators.Email(message = "please enter a valid email address")])
    password = PasswordField("Password",validators = [validators.DataRequired("plase enter a password"),
     validators.EqualTo(fieldname = "confirm",message = "your password does not match")])
    confirm = PasswordField("verify password")
    
class LoginForm(Form):
    username = StringField("Username")
    password = PasswordField("Password")

app = Flask(__name__)
app.secret_key = "blog"

app.config["MYSQL_HOST"] ="localhost"
app.config["MYSQL_USER"] ="root"
app.config["MYSQL_PASSWORD"] =""
app.config["MYSQL_DB"] ="blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():

    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

#article site
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "Select * From articles"
    result = cursor.execute(query)
    if result > 0 :
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s"
    result = cursor.execute(query,(session["username"],))
    if result > 0 :
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

#register
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        query = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(query,(name,email,username,password))
        mysql.connection.commit()

        cursor.close()

        flash("You have successfully registered","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)




#login
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        query = "Select * From users where username = %s"
        result = cursor.execute(query,(username,))
        if result > 0 :
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("You have sign in successfully","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("you entered your password incorrectly","danger")
                return redirect(url_for("login"))

        else:
            flash("there is no such user","danger")
            return redirect(url_for("login"))


    return render_template("login.html",form = form)

#Detail page
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "Select * from articles where id = %s "
    result = cursor.execute(query,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

#logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logout successfully","success")
    return redirect(url_for("index"))

#add article
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))

        mysql.connection.commit()
        cursor.close()
        flash("article successfully added","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

#delete article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(query,(session["username"],id))
    if result > 0:
        query2 = "Delete from articles where id = %s"
        cursor.execute(query2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash(" There is no such article or you are not authorized for this action")
        return redirect(url_for("index"))

#article update
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        query = "Select * From articles where id = %s and author= %s"
        result = cursor.execute(query,(id,session["username"]))
        if result == 0:
            flash("There is no such article or you are not authorized for this action","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article ["content"]
            return render_template("update.html",form = form)

#post request
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        query2 = "Update articles Set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Article is updated successfully!","success")
        return redirect(url_for("dashboard"))
        

#search url
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "Select * From articles where title like '%" + keyword +"%'"
        result = cursor.execute(query)
        if result == 0:
            flash("No article found matching the search term","warning")
            return redirect(url_for("articles"))
        else :
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)
 #article form
class ArticleForm(Form):
    title = StringField("Title of article",validators=[validators.length(min = 5, max = 100)])
    content = TextAreaField("Content of Article",validators=[validators.length(min = 10)])

if __name__ == "__main__":
    app.run(debug=True)