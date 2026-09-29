<p align="center">
  <img src="assets/logo-lockup.png" alt="MovieMatcher Logo" width="560">
</p>

# MovieMatcher | AI Movie Recommendation System

A modern content-based movie recommendation system built using Python, Scikit-Learn, and Flask, featuring a responsive glassmorphic web interface with interactive AI similarity matching.

---

## 🌟 Features

### Frontend UI & Experience
*   **Vibrant Glassmorphic UI:** Ambient radiant gradient canvas with interactive particle stars, clean elevated app frame, and frosted translucent cards.
*   **Search Autocomplete:** Real-time suggestions as you type in the search bar.
*   **Dynamic Poster Integration:** High-quality movie cover art fetched dynamically using **The Movie Database (TMDb) API** (with iTunes Search API as fallback).
*   **Multi-Source Ratings & Metadata:** Aggregated review scores (IMDb, Rotten Tomatoes Critics & Audience, Metacritic), plot synopsis, director, and cast.
*   **Official Trailers & Streaming:** Embedded official YouTube trailers and live streaming availability ("Where to Watch" across Netflix, Prime Video, Apple TV, etc.).
*   **Genre Category Grid:** Clickable tabs (Action, Comedy, Drama, Thriller, etc.) to browse and filter movies dynamically.
*   **Full Catalog Browsing:** Paginated browse list of all 9,700+ movies in the database with lazy load-more capability.
*   **Responsive Layout:** Fully optimized for mobile, tablet, and widescreen desktop displays.

### Recommendation Engine
*   **Metadata Processing:** Combines genres and user tags for rich movie feature modeling.
*   **Similarity Computation:** Employs TF-IDF Vectorization and Cosine Similarity to find similar films.
*   **Ratings Aggregation:** Summarizes average ratings and review counts from `ratings.csv` to showcase on the interface.
*   **Smart Resolution:** Auto-matches search queries that omit the release year (e.g. typing "Inception" automatically matches "Inception (2010)").

---

## 📁 Project Structure

```bash
movie_recommendation_system/
│
├── data/                      # Dataset CSV Files
│   ├── movies.csv             # Movie names & original genres
│   ├── ratings.csv            # User ratings (aggregated for UI scores)
│   ├── tags.csv               # User tags (vectorized for similarity)
│   └── links.csv              # Movie database link identifiers
│
├── app/                       # Backend Package
│   ├── recommender.py         # TF-IDF Cosine Similarity engine
│   └── api.py                 # Flask server & REST API routes
│
├── templates/                 # Web HTML Templates
│   └── index.html             # Single-page frontend template
│
├── static/                    # Frontend Static Assets
│   ├── css/
│   │   └── styles.css         # UI design system & animations
│   └── js/
│       └── main.js            # Particle canvas, poster fetch, autocomplete, modals
│
├── notebook/                  # Research & EDA
│   └── movie_recommender.ipynb
│
├── main.py                    # Root Web Application Entry Point
├── requirements.txt           # Python Package Dependencies
├── .env.example               # Environment Variables Template
└── README.md                  # Project Documentation
```

---

## 🚀 Setup & Execution

### 1. Install Dependencies
Make sure you have Python 3.8+ installed. Install the required libraries using pip:

```bash
pip install -r requirements.txt
```

*(Includes: `flask`, `requests`, `pandas`, `numpy`, `scikit-learn`)*

### 2. Run the Application
Launch the server from the project root directory:

```bash
python main.py
```

*(or run `python app/api.py`)*

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📸 Preview

### Modern AI Recommender Interface
![Hero Dashboard](assets/Screenshot%202026-09-29%20184804.png)

### Real-Time New & Trending Releases
![New & Trending Releases](assets/Screenshot%202026-09-27%20160253.png)

### Interactive Cards with "View Info" and "Similar"
![Movie Cards with View Info & Similar Buttons](assets/Screenshot%202026-09-27%20160332.png)

### Multi-Source Ratings & Details Modal
![Multi-Source Ratings & Movie Details Modal](assets/Screenshot%202026-09-27%20160359.png)

### Official YouTube Trailer Integration
![Embedded Official YouTube Trailer](assets/Screenshot%202026-09-27%20160409.png)

### Personalized AI Vector Recommendations
![Personalized AI Recommendations](assets/Screenshot%202026-09-27%20160438.png)

---

## ⚡ REST API Endpoints

| Endpoint | Method | Params | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | None | Serves the single-page MovieMatcher application. |
| `/api/movies` | `GET` | `page`, `limit`, `genre`, `q` | Paginated catalog browsing with instant genre filtering. |
| `/api/genres` | `GET` | None | Returns list of unique genres in the dataset. |
| `/api/search` | `GET` | `q` | Real-time autocomplete suggestions with match scoring. |
| `/api/recommend` | `GET` | `movie`, `top_n` | Content-based recommendations with similarity match percentages. |
| `/api/poster` | `GET` | `movie` | Fast HTTP 302 CDN redirect directly to TMDB / Amazon poster artwork. |
| `/api/movie/meta` | `GET` | `movie`, `imdbId` | Aggregated ratings (IMDb, Rotten Tomatoes Critics & Audience, Metacritic), plot, cast, and official YouTube trailer. |
| `/api/movie/streaming` | `GET` | `movie`, `country` | Live streaming options ("Where to Watch") across Netflix, Prime Video, Apple TV, Disney+, etc. |
| `/api/movies/latest` | `GET` | `type` (`now_playing` or `popular`) | Live releases from The Movie Database (TMDb). |
| `/api/imdb/top250` | `GET` | None | Official IMDb Top 250 movies feed. |
| `/api/imdb/random` | `GET` | None | Random film discovery with full cast & director credits. |