import os
import numpy as np
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
        self.tfidf = None
        self.tfidf_matrix = None
        self._similarity_matrix = None
        self._sim_cache = {}
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

    @property
    def similarity_matrix(self):
        """Lazy-computed full similarity matrix for backward compatibility."""
        if self._similarity_matrix is None and self.tfidf_matrix is not None:
            self._similarity_matrix = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        return self._similarity_matrix

    def build_similarity(self):
        """Create TF-IDF vector matrix.
        
        Complexity: O(N * K) where N = 9,742 movies, K = vocabulary size.
        Avoids precomputing the massive O(N^2) = 94.9 million pairwise float matrix (724MB RAM).
        Instead, on-demand cosine vector dot-products take only ~2.5ms per query.
        """
        self.tfidf = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(self.final_df["metadata"])

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
        """Recommend top N similar movies using high-speed on-demand cosine similarity.
        
        Complexity: O(N) vector-matrix multiplication (~2.5ms) + O(N) argpartition top-N selection.
        """
        movie_title = movie_title.lower().strip()

        if movie_title not in self.indices:
            return []

        # Check in-memory recommendation cache
        cache_key = (movie_title, top_n)
        if cache_key in self._sim_cache:
            return self._sim_cache[cache_key]

        idx = self.indices[movie_title]
        
        # 1. On-demand single row cosine similarity: 1 x N vector dot products (~2.5ms)
        sim_scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).ravel()

        # 2. Fast O(N) top candidate selection using argpartition (avoids full O(N log N) sort)
        candidates_k = min(top_n + 15, len(sim_scores) - 1)
        top_candidates = np.argpartition(sim_scores, -candidates_k)[-candidates_k:]
        top_sorted = top_candidates[np.argsort(-sim_scores[top_candidates])]

        # 3. Filter out the query movie itself
        movie_indices = []
        top_scores = []
        for i in top_sorted:
            if i != idx:
                movie_indices.append(i)
                top_scores.append(float(sim_scores[i]))
                if len(movie_indices) == top_n:
                    break

        recommendations = self.final_df.iloc[movie_indices][[
            "movieId", "imdbId", "tmdbId", "title", "genres_display", "average_rating", "rating_count"
        ]].copy()
        recommendations.rename(columns={"genres_display": "genres"}, inplace=True)
        recommendations["similarity_score"] = [round(score, 3) for score in top_scores]

        result = recommendations.to_dict(orient="records")
        self._sim_cache[cache_key] = result
        return result

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
