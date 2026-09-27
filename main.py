from app.recommender import MovieRecommender


def main():
    recommender = MovieRecommender(
        movies_path="data/movies.csv",
        tags_path="data/tags.csv",
        ratings_path="data/ratings.csv"
    )

    print("Loading and training recommender system...")
    recommender.fit()
    print("System ready.\n")

    while True:
        print("===== Movie Recommendation System =====")
        movie_name = input("Enter a movie title (or type 'exit' to quit): ").strip()

        if movie_name.lower() == "exit":
            print("Exiting system. Goodbye!")
            break

        recommendations = recommender.recommend_movies(movie_name, top_n=5)

        if not recommendations:
            print("\nMovie not found.")
            suggestions = recommender.search_movies(movie_name)
            if suggestions:
                print("Did you mean:")
                for s in suggestions:
                    print(f"- {s}")
            print()
            continue

        print(f"\nTop recommendations for '{movie_name}':\n")
        for i, movie in enumerate(recommendations, start=1):
            print(f"{i}. {movie['title']}")
            print(f"   Genres: {movie['genres']}")
            print(f"   Similarity Score: {movie['similarity_score']}")
            print()

        print("-" * 50)


if __name__ == "__main__":
    main()