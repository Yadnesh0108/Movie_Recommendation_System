# CineMatch | Movie Recommendation System

A modern content-based movie recommendation system built using Python, Scikit-Learn, and Flask, with a premium, responsive dark-themed frontend.

---

## 🌟 Features

### Frontend UI/UX (New)
*   **Premium Dark Theme:** Sleek charcoal and deep-slate colors with neon indigo and purple accents.
*   **HTML5 Canvas Particle Background:** Interactive particle stars moving in the background that respond to mouse movement.
*   **Glassmorphic Design:** Translucent cards, dropdowns, and layouts styled using `backdrop-filter: blur()`.
*   **Search Autocomplete:** Real-time suggestions as you type in the search bar.
*   **Dynamic Poster Integration:** High-quality movie cover art fetched dynamically using the official **The Movie Database (TMDb) API** (with iTunes Search API as a robust fallback).
*   **Glowing Hover Effects:** Micro-animations and scale transitions on interactive card elements.
*   **Genre Category Grid:** Clickable tabs (Action, Comedy, Drama, Thriller, etc.) to browse and filter movies dynamically.
*   **Full Catalog Browsing:** Paginated browse list of all 9,000+ movies in the database with lazy load-more capability.
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
│   ├── __init__.py
│   ├── recommender.py         # TF-IDF Cosine Similarity engine
│   ├── utils.py               # EDA & plotting functions
│   └── api.py                 # Flask Server & API routes
│
├── templates/                 # Web HTML Templates
│   └── index.html             # Homepage template
│
├── static/                    # Frontend Static Assets
│   ├── css/
│   │   └── styles.css         # Styling system & animations
│   └── js/
│       └── main.js            # Canvas particles, poster fetch, autocomplete
│
├── notebook/                  # Research & EDA
│   └── movie_recommender.ipynb
│
├── main.py                    # Legacy CLI Entry Point
├── requirements.txt           # Python Package Dependencies
└── README.md                  # Project Documentation
```

---

## 🚀 Setup & Execution

### 1. Install Dependencies
Make sure you have Python 3.8+ installed. Install the required libraries using pip:

```bash
pip install -r requirements.txt
```

*(Includes: `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `flask`)*

### 2. Run the Web Application
Launch the Flask development server from the project root directory:

```bash
python app/api.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### 3. Run the Command Line Interface (CLI)
If you prefer testing the recommendation system inside the terminal, run the CLI utility:

```bash
python main.py
```

---


## 📸 Preview

### Modern AI Recommender Interface
![Hero Dashboard](assets/Screenshot%202026-09-27%20160239.png)

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
| `/` | `GET` | None | Serves the single-page CineMatch application. |
| `/api/movies` | `GET` | `page`, `limit`, `genre`, `q` | Paginated catalog browsing with instant genre filtering. |
| `/api/genres` | `GET` | None | Returns list of unique genres in the dataset. |
| `/api/search` | `GET` | `q` | Real-time autocomplete suggestions with match scoring. |
| `/api/recommend` | `GET` | `movie`, `top_n` | Content-based recommendations with similarity match percentages. |
| `/api/poster` | `GET` | `movie` | Fast HTTP 302 CDN redirect directly to TMDB / Amazon poster artwork. |
| `/api/movie/meta` | `GET` | `movie`, `imdbId` | Aggregated ratings (IMDb, Rotten Tomatoes Critics & Audience, Letterboxd, Metacritic), plot, cast, and official YouTube trailer. |
| `/api/movie/streaming` | `GET` | `movie`, `country` | Live streaming options ("Where to Watch") across Netflix, Prime Video, Apple TV, Disney+, etc. |
| `/api/movies/latest` | `GET` | `type` (`now_playing` or `popular`) | Live releases from The Movie Database (TMDb). |
| `/api/imdb/top250` | `GET` | None | Official IMDb Top 250 movies feed. |
| `/api/imdb/random` | `GET` | None | Random film discovery with full cast & director credits. |
| `/recommend` | `GET` | `movie`, `top_n` | Legacy recommendation endpoint for scripts/CLI. |
| `/search` | `GET` | `q` | Legacy search endpoint. |