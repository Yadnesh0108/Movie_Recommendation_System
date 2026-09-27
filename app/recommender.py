import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MovieRecommender:
    def __init__(self, movies_path, tags_path, ratings_path=None, links_path=None):
        self.movies_path = movies_path
        self.tags_path = tags_path
        self.ratings_path = ratings_path
        self.links_path = links_path

        self.movies_df = None
        self.tags_df = None
        self.ratings_df = None
        self.links_df = None
        self.final_df = None
        self.similarity_matrix = None
        self.indices = None

    def load_data(self):
        """Load CSV files."""
        self.movies_df = pd.read_csv(self.movies_path)
        self.tags_df = pd.read_csv(self.tags_path)

        if self.ratings_path and os.path.exists(self.ratings_path):
            self.ratings_df = pd.read_csv(self.ratings_path)

        if self.links_path and os.path.exists(self.links_path):
            self.links_df = pd.read_csv(self.links_path)

    def preprocess_data(self):
        """Clean and merge movie metadata, ratings, and TMDb IDs."""
        self.tags_df["tag"] = self.tags_df["tag"].fillna("")

        tags_grouped = (
            self.tags_df
            .groupby("movieId")["tag"]
            .apply(lambda x: " ".join(x))
            .reset_index()
        )

        self.final_df = pd.merge(self.movies_df, tags_grouped, on="movieId", how="left")
        self.final_df["tag"] = self.final_df["tag"].fillna("")

        # Merge IMDb and TMDb IDs from MovieLens links.csv
        if self.links_df is not None:
            cols_to_merge = ["movieId"]
            if "imdbId" in self.links_df.columns:
                cols_to_merge.append("imdbId")
            if "tmdbId" in self.links_df.columns:
                cols_to_merge.append("tmdbId")
            links_clean = self.links_df[cols_to_merge].copy()
            self.final_df = pd.merge(self.final_df, links_clean, on="movieId", how="left")
        else:
            self.final_df["tmdbId"] = None
            self.final_df["imdbId"] = None

        self.final_df["genres_display"] = (
            self.final_df["genres"]
            .fillna("Unknown")
            .str.replace("|", ", ", regex=False)
        )

        self.final_df["genres"] = (
            self.final_df["genres"]
            .fillna("")
            .str.replace("|", " ", regex=False)
            .str.lower()
        )
        self.final_df["tag"] = self.final_df["tag"].str.lower()
        self.final_df["title"] = self.final_df["title"].str.strip()

        if self.ratings_df is not None:
            ratings_grouped = (
                self.ratings_df
                .groupby("movieId")["rating"]
                .agg(["mean", "count"])
                .reset_index()
            )
            ratings_grouped.rename(
                columns={"mean": "average_rating", "count": "rating_count"},
                inplace=True
            )
            self.final_df = pd.merge(self.final_df, ratings_grouped, on="movieId", how="left")
        else:
            self.final_df["average_rating"] = 0.0
            self.final_df["rating_count"] = 0

        self.final_df["average_rating"] = self.final_df["average_rating"].fillna(0.0).round(1)
        self.final_df["rating_count"] = self.final_df["rating_count"].fillna(0).astype(int)

        # Keep tmdbId JSON-friendly: Python int when present, None when missing
        self.final_df["tmdbId"] = self.final_df["tmdbId"].apply(
            lambda x: int(x) if pd.notna(x) else None
        )
        if "imdbId" in self.final_df.columns:
            self.final_df["imdbId"] = self.final_df["imdbId"].apply(
                lambda x: f"tt{str(int(x)).zfill(7)}" if pd.notna(x) else None
            )
        else:
            self.final_df["imdbId"] = None

        self.final_df["metadata"] = self.final_df["genres"] + " " + self.final_df["tag"]
        self.indices = pd.Series(
            self.final_df.index,
            index=self.final_df["title"].str.lower()
        ).drop_duplicates()

    def build_similarity(self):
        """Create TF-IDF vectors and cosine similarity matrix."""
        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(self.final_df["metadata"])
        self.similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    def fit(self):
        """Complete training pipeline."""
        self.load_data()
        self.preprocess_data()
        self.build_similarity()

    def _movie_records(self, df):
        """Return frontend-friendly movie records."""
        cols = ["movieId", "imdbId", "tmdbId", "title", "genres_display", "average_rating", "rating_count"]
        data = df[cols].copy()
        data.rename(columns={"genres_display": "genres"}, inplace=True)
        return data.to_dict(orient="records")

    def recommend_movies(self, movie_title, top_n=5):
        """Recommend top N similar movies."""
        movie_title = movie_title.lower().strip()

        if movie_title not in self.indices:
            return []

        idx = self.indices[movie_title]
        sim_scores = list(enumerate(self.similarity_matrix[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1: top_n + 1]

        movie_indices = [i[0] for i in sim_scores]
        recommendations = self.final_df.iloc[movie_indices][[
            "movieId", "imdbId", "tmdbId", "title", "genres_display", "average_rating", "rating_count"
        ]].copy()
        recommendations.rename(columns={"genres_display": "genres"}, inplace=True)
        recommendations["similarity_score"] = [round(score[1], 3) for score in sim_scores]

        return recommendations.to_dict(orient="records")

    def search_movies(self, keyword):
        """Search movies by partial keyword. Returns titles only for CLI compatibility."""
        keyword = keyword.lower().strip()
        matches = self.final_df[self.final_df["title"].str.lower().str.contains(keyword, na=False)]
        return matches["title"].head(10).tolist()

    def search_movies_detailed(self, keyword, limit=10):
        """Search movies by partial keyword and return detailed info for UI autocomplete."""
        keyword = keyword.lower().strip()
        matches = self.final_df[self.final_df["title"].str.lower().str.contains(keyword, na=False)]
        return self._movie_records(matches.head(limit))

    def get_movies_by_genre(self, genre, page=1, limit=30):
        """Get paginated movies filtered by genre."""
        if genre and genre.lower() != "all":
            mask = self.movies_df["genres"].fillna("").str.lower().str.split("|").apply(
                lambda x: genre.lower() in x
            )
            filtered = self.final_df[mask]
        else:
            filtered = self.final_df

        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        total_count = len(filtered)
        paginated = filtered.iloc[start_idx:end_idx]

        return {
            "movies": self._movie_records(paginated),
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit
        }

    def get_genres(self):
        """Extract a list of unique genres from the dataset."""
        if self.movies_df is None:
            return []

        genre_set = set()
        for genres_str in self.movies_df["genres"].dropna():
            for genre in genres_str.split("|"):
                genre = genre.strip()
                if genre and genre.lower() != "(no genres listed)":
                    genre_set.add(genre)

        return sorted(list(genre_set))
