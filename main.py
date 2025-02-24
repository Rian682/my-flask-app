from dotenv import load_dotenv
import os
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import CheckConstraint
from wtforms import StringField, SubmitField
from wtforms import FloatField
import requests

app = Flask(__name__)
Bootstrap(app)

#### CREATING SQLite DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///top_ten_movies.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.String(500))
    rating = db.Column(db.Float, CheckConstraint("rating <= 10"), nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    review = db.Column(db.String(1000), nullable=True)
    img_url = db.Column(db.String(500))


with app.app_context():
    db.create_all()

# with app.app_context():
#     new_movie = [Movies(title="Phone Booth",
#     year="(2002)",
#     description= "Publicist Stuart Shepard finds himself trapped in a phone booth, pinned down by an extortionist's sniper rifle. Unable to leave or receive outside help,Stuart's negotiation with the caller leads to a jaw-dropping climax.",
#     rating=7.3,
#     ranking=10,
#     review="My favourite character was the caller.",
#     img_url="https://image.tmdb.org/t/p/w500/tjrX2oWRCM3Tvarz38zlZM7Uc10.jpg")
#     ]
#
#     db.session.add_all(new_movie)
#     db.session.commit()


# GET KEYS FROM ENV
load_dotenv()
secret_key = os.getenv("SECRET_KEY")
api = os.getenv("API_KEY")
auth = os.getenv("AUTHORIZATION")


# CREATING WTFORM
app.secret_key = secret_key


class RateMovieForm(FlaskForm):
    new_rating = FloatField(label="Your Rating Out of 10 e.g. 7.5")
    new_review = StringField(label="Your Review")
    submit = SubmitField(label="Done")


class AddMovieForm(FlaskForm):
    title = StringField(label="Movie Title")
    submit = SubmitField(label="Add Movie")


@app.route("/")
def home():
    # all_movies = Movies.query.all()
    all_movies = Movies.query.order_by(Movies.rating.asc()).all()

    all_movies_ranking = Movies.query.order_by(Movies.rating.desc()).all()
    for index, movie in enumerate(all_movies_ranking):
        movie.ranking = index + 1
    db.session.commit()
    return render_template("index.html", movies=all_movies)


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete_movie(id):
    movie = Movies.query.get(id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    add_movie_form = AddMovieForm()
    if add_movie_form.validate_on_submit():
        query = str(add_movie_form.title.data)
        api_key = api
        all_movies_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}"
        headers = {
            "accept": "application/json",
            "Authorization": auth
        }
        response = requests.get(all_movies_url, headers=headers)
        data = response.json()

        return render_template("select.html", movie_data=data)
    return render_template("add.html", wtform=add_movie_form)


@app.route("/select", methods=["GET", "POST"])
def select_movies():

    movie_id = request.args.get("id")
    headers = {
        "accept": "application/json",
        "Authorization": auth
    }
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"

    movie_response = requests.get(movie_url, headers=headers)
    movie_data = (movie_response.json())

    name = movie_data["original_title"]
    poster_url = f"https://image.tmdb.org/t/p/w500/{movie_data['poster_path']}"
    overview = movie_data["overview"]
    year = movie_data["release_date"].split("-")[0]

    if movie_id:
        with app.app_context():
            new_movie = [Movies(title=name,
                                year=f"({year})",
                                description=overview,
                                rating=None,
                                ranking=movie_id,
                                review=None,
                                img_url=poster_url)
                         ]
            db.session.add_all(new_movie)
            db.session.commit()

    movie_in_database = Movies.query.filter_by(title=name).first()
    if movie_in_database:
        return redirect(url_for("edit_rating", id=movie_in_database.id))


@app.route("/update/<int:id>", methods=["GET", "POST"])
def edit_rating(id):
    new_rating_form = RateMovieForm()

    movie = Movies.query.get(id)
    if new_rating_form.validate_on_submit():
        movie.rating = new_rating_form.new_rating.data
        movie.review = new_rating_form.new_review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", movie=movie, wtform=new_rating_form)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host='0.0.0.0', port=port, debug=True)

