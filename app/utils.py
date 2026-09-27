import pandas as pd
import matplotlib.pyplot as plt


def load_datasets(movies_path, ratings_path, tags_path):
    movies = pd.read_csv(movies_path)
    ratings = pd.read_csv(ratings_path)
    tags = pd.read_csv(tags_path)
    return movies, ratings, tags


def basic_eda(movies, ratings, tags):
    print("===== DATASET OVERVIEW =====")
    print(f"Movies shape  : {movies.shape}")
    print(f"Ratings shape : {ratings.shape}")
    print(f"Tags shape    : {tags.shape}")
    print()
    print(f"Unique movies : {movies['movieId'].nunique()}")
    print(f"Unique users  : {ratings['userId'].nunique()}")
    print(f"Unique ratings: {ratings.shape[0]}")
    print()


def plot_ratings_distribution(ratings):
    plt.figure(figsize=(8, 5))
    ratings["rating"].hist(bins=10, edgecolor="black")
    plt.title("Ratings Distribution")
    plt.xlabel("Rating")
    plt.ylabel("Count")
    plt.show()


def plot_top_rated_movies(movies, ratings, top_n=10):
    rating_counts = ratings.groupby("movieId").size().reset_index(name="num_ratings")
    top_movies = rating_counts.merge(movies, on="movieId").sort_values("num_ratings", ascending=False).head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(top_movies["title"], top_movies["num_ratings"])
    plt.gca().invert_yaxis()
    plt.title(f"Top {top_n} Most Rated Movies")
    plt.xlabel("Number of Ratings")
    plt.ylabel("Movie Title")
    plt.show()


def plot_genre_distribution(movies):
    genre_series = movies["genres"].str.split("|").explode()
    genre_counts = genre_series.value_counts()

    plt.figure(figsize=(10, 5))
    plt.bar(genre_counts.index, genre_counts.values)
    plt.title("Genre Distribution")
    plt.xlabel("Genre")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.show()


def plot_user_activity(ratings):
    user_activity = ratings.groupby("userId").size()

    plt.figure(figsize=(8, 5))
    user_activity.hist(bins=30, edgecolor="black")
    plt.title("Ratings per User")
    plt.xlabel("Number of Ratings")
    plt.ylabel("Number of Users")
    plt.show()