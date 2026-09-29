import os
import sys
import re
import io
import time
import json
import urllib.parse
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template, Response, redirect

# ---------------------------------------------------------------------------
# Path setup — allows running as both `python app/api.py` and `python api.py`
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from app.recommender import MovieRecommender
except ModuleNotFoundError:
    from recommender import MovieRecommender

# ---------------------------------------------------------------------------
# Flask app setup
# ---------------------------------------------------------------------------
template_dir = os.path.join(ROOT_DIR, "templates")
static_dir   = os.path.join(ROOT_DIR, "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# ---------------------------------------------------------------------------
# Helper: Normalize movie titles for fast matching
# ---------------------------------------------------------------------------
def normalize_movie_title(t):
    t = re.sub(r"\s*\(\d{4}\)\s*$", "", str(t)).strip().lower()
    if t.endswith(", the"):
        return ("the " + t[:-5]).strip()
    if t.endswith(", a"):
        return ("a " + t[:-3]).strip()
    if t.endswith(", an"):
        return ("an " + t[:-4]).strip()
    return t

# ---------------------------------------------------------------------------
# Load & train recommender model at startup
# ---------------------------------------------------------------------------
recommender = MovieRecommender(
    movies_path  = os.path.join(ROOT_DIR, "data", "movies.csv"),
    tags_path    = os.path.join(ROOT_DIR, "data", "tags.csv"),
    ratings_path = os.path.join(ROOT_DIR, "data", "ratings.csv"),
    links_path   = os.path.join(ROOT_DIR, "data", "links.csv"),   # provides tmdbId & imdbId
)
recommender.fit()

# Precompute title normalization dictionaries for microsecond lookups
TITLE_TO_IMDB: dict = {}
TITLE_TO_TMDB: dict = {}
if recommender.final_df is not None:
    recommender.final_df["normalized_title"] = recommender.final_df["title"].apply(normalize_movie_title)
    TITLE_TO_IMDB = recommender.final_df.dropna(subset=["imdbId"]).set_index("normalized_title")["imdbId"].to_dict()
    TITLE_TO_TMDB = recommender.final_df.dropna(subset=["tmdbId"]).set_index("normalized_title")["tmdbId"].to_dict()

# Persistent poster cache — eliminates repeat external TMDb network lookups on launch
POSTER_CACHE_FILE = os.path.join(ROOT_DIR, "data", "poster_cache.json")
POSTER_CACHE: dict = {}
if os.path.exists(POSTER_CACHE_FILE):
    try:
        with open(POSTER_CACHE_FILE, "r", encoding="utf-8") as _f:
            POSTER_CACHE = json.load(_f)
    except Exception:
        POSTER_CACHE = {}

def save_poster_cache():
    try:
        with open(POSTER_CACHE_FILE, "w", encoding="utf-8") as _f:
            json.dump(POSTER_CACHE, _f)
    except Exception:
        pass

# In-memory caches — avoids repeat external lookups
META_CACHE: dict = {}
LATEST_CACHE: dict = {}
STREAMING_CACHE: dict = {}
RATINGS_RATE_LIMITED_UNTIL = 0.0

TMDB_API_KEY = "43ee7b893ee02a490d9f740cfc616b8d"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"

RAPIDAPI_KEY = "acf7bf9e49msh0f5125252daee33p15c5fcjsn497f4fc305c8"
RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"
IMDB_RAPIDAPI_HOST = "imdb236.p.rapidapi.com"
RATINGS_RAPIDAPI_HOST = "movies-ratings2.p.rapidapi.com"
YOUTUBE_RAPIDAPI_HOST = "youtube-data-api-v33.p.rapidapi.com"
IMDB_TOP250_CACHE = None

FALLBACK_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=400&q=80"

# Persistent HTTP Session with connection pooling & retries
http_session = requests.Session()
retries_policy = Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
http_adapter = HTTPAdapter(max_retries=retries_policy, pool_connections=30, pool_maxsize=30)
http_session.mount("https://", http_adapter)
http_session.mount("http://", http_adapter)
http_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json"
})

@app.route("/")
def home():
    """Serve the MovieMatcher single-page frontend."""
    if os.path.exists(os.path.join(template_dir, "index.html")):
        return render_template("index.html")
    return jsonify({"message": "API running — frontend index.html not found."})


# ---------------------------------------------------------------------------
# /api/movies  — paginated, filterable movie list
# ---------------------------------------------------------------------------
@app.route("/api/movies", methods=["GET"])
def get_movies():
    genre = request.args.get("genre", "all")
    page  = request.args.get("page",  1,  type=int)
    limit = request.args.get("limit", 20, type=int)
    query = request.args.get("q", "").strip()

    df = recommender.final_df
    if df is None:
        return jsonify({"error": "Dataset not loaded"}), 500

    # Genre filter
    if genre and genre.lower() != "all":
        mask = (
            recommender.movies_df["genres"]
            .fillna("")
            .str.lower()
            .str.split("|")
            .apply(lambda x: genre.lower() in x)
        )
        df = df[mask]

    # Title search filter
    if query:
        df = df[df["title"].str.lower().str.contains(query.lower(), na=False)]

    total_count = len(df)
    start_idx   = (page - 1) * limit
    paginated   = df.iloc[start_idx : start_idx + limit]

    return jsonify({
        "movies": recommender._movie_records(paginated),
        "total":  total_count,
        "page":   page,
        "limit":  limit,
        "pages":  (total_count + limit - 1) // limit,
    })


# ---------------------------------------------------------------------------
# /api/genres  — unique genre list
# ---------------------------------------------------------------------------
@app.route("/api/genres", methods=["GET"])
def get_genres():
    return jsonify(recommender.get_genres())


# ---------------------------------------------------------------------------
# /api/poster  — Fast 302 redirect directly to TMDB / Amazon CDN poster
# ---------------------------------------------------------------------------
@app.route("/api/poster", methods=["GET"])
def get_movie_poster():
    movie = request.args.get("movie", "").strip()
    if not movie:
        return redirect(FALLBACK_POSTER, code=302)

    clean = re.sub(r"\s*\(\d{4}\)\s*$", "", movie).strip()
    if clean.lower().endswith(", the"):
        clean = "The " + clean[:-5].strip()
    elif clean.lower().endswith(", a"):
        clean = "A " + clean[:-3].strip()
    elif clean.lower().endswith(", an"):
        clean = "An " + clean[:-4].strip()

    # Fast in-memory cache check (<0.1ms)
    if clean in POSTER_CACHE and POSTER_CACHE[clean]:
        resp = redirect(POSTER_CACHE[clean], code=302)
        resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
        return resp

    norm_clean = normalize_movie_title(movie)
    poster_url = None

    # 1. Fast lookup via precomputed TMDB map (from links.csv tmdbId)
    tmdb_id = TITLE_TO_TMDB.get(norm_clean)
    if tmdb_id and str(tmdb_id).lower() != "nan":
        try:
            api_url = f"{TMDB_BASE_URL}/movie/{int(float(tmdb_id))}?api_key={TMDB_API_KEY}"
            res = http_session.get(api_url, timeout=1.8)
            if res.status_code == 200:
                data = res.json()
                if data.get("poster_path"):
                    poster_url = TMDB_IMG_BASE_URL + data["poster_path"]
        except Exception as exc:
            app.logger.warning(f"TMDB poster lookup failed for tmdbId={tmdb_id}: {exc}")

    # 2. Fast OMDb fallback (high-resolution Amazon / IMDb CDN poster)
    if not poster_url:
        try:
            omdb_url = f"http://www.omdbapi.com/?apikey=trilogy&t={urllib.parse.quote(clean)}"
            res = http_session.get(omdb_url, timeout=1.8)
            if res.status_code == 200:
                data = res.json()
                omdb_poster = data.get("Poster")
                if omdb_poster and omdb_poster != "N/A" and omdb_poster.startswith("http"):
                    poster_url = omdb_poster
        except Exception as exc:
            app.logger.warning(f"OMDb poster fallback failed for '{clean}': {exc}")

    # 3. TMDB search query fallback
    if not poster_url:
        try:
            search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={urllib.parse.quote(clean)}"
            res = http_session.get(search_url, timeout=1.8)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results and results[0].get("poster_path"):
                    poster_url = TMDB_IMG_BASE_URL + results[0]["poster_path"]
        except Exception as exc:
            app.logger.warning(f"TMDB search poster fallback failed for '{clean}': {exc}")

    # Final fallback: high-quality cinema placeholder, never 404 or broken image
    if not poster_url:
        poster_url = FALLBACK_POSTER

    POSTER_CACHE[clean] = poster_url
    POSTER_CACHE[movie] = poster_url
    save_poster_cache()
    resp = redirect(poster_url, code=302)
    resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return resp


# ---------------------------------------------------------------------------
# /api/search  — autocomplete suggestions
# ---------------------------------------------------------------------------
@app.route("/api/search", methods=["GET"])
def autocomplete_search():
    keyword = request.args.get("q", "").strip()
    if not keyword or len(keyword) < 2:
        return jsonify([])
    return jsonify(recommender.search_movies_detailed(keyword, limit=8))


# ---------------------------------------------------------------------------
# /api/recommend  — content-based recommendations for a given movie title
# ---------------------------------------------------------------------------
@app.route("/api/recommend", methods=["GET"])
def get_recommendations():
    movie = request.args.get("movie", "").strip()
    top_n = request.args.get("top_n", default=6, type=int)

    if not movie:
        return jsonify({"error": "Provide a movie name using ?movie="}), 400

    recommendations = recommender.recommend_movies(movie, top_n=top_n)

    # Auto-resolve title without year — e.g. "Toy Story" → "Toy Story (1995)"
    if not recommendations:
        for suggestion in recommender.search_movies(movie):
            bare = re.sub(r"\s*\(\d{4}\)\s*$", "", suggestion).strip().lower()
            if bare == movie.lower():
                movie = suggestion
                recommendations = recommender.recommend_movies(movie, top_n=top_n)
                break

    if not recommendations:
        return jsonify({
            "error":       "Movie not found",
            "suggestions": recommender.search_movies(movie),
        }), 404

    # Build input movie details for the "Your Choice" panel
    match = recommender.final_df[recommender.final_df["title"].str.lower() == movie.lower()]
    input_details = None
    if not match.empty:
        row = match.iloc[0]
        input_details = {
            "movieId":        int(row["movieId"]),
            "tmdbId":         row["tmdbId"],
            "title":          row["title"],
            "genres":         row["genres_display"],
            "average_rating": float(row["average_rating"]),
            "rating_count":   int(row["rating_count"]),
        }

    return jsonify({
        "input_movie":     input_details or {"title": movie},
        "recommendations": recommendations,
    })


# ---------------------------------------------------------------------------
# /api/movie/meta — Rotten Tomatoes, IMDb rating, and Streaming Availability
# ---------------------------------------------------------------------------
RATINGS_RATE_LIMITED_UNTIL = 0
STREAMING_CACHE: dict = {}

# ---------------------------------------------------------------------------
# /api/movie/meta — Fast Rotten Tomatoes, IMDb rating, Plot, Cast & Trailer
# ---------------------------------------------------------------------------
@app.route("/api/movie/meta", methods=["GET"])
def get_movie_meta():
    movie = request.args.get("movie", "").strip()
    if not movie:
        return jsonify({"error": "Missing movie title"}), 400

    clean = re.sub(r"\s*\(\d{4}\)\s*$", "", movie).strip()
    if clean.lower().endswith(", the"):
        clean = "The " + clean[:-5].strip()
    elif clean.lower().endswith(", a"):
        clean = "A " + clean[:-3].strip()
    elif clean.lower().endswith(", an"):
        clean = "An " + clean[:-4].strip()

    cache_key = clean.lower()
    if cache_key in META_CACHE:
        return jsonify(META_CACHE[cache_key])

    norm_clean = normalize_movie_title(movie)
    imdb_id = request.args.get("imdbId", "").strip() or TITLE_TO_IMDB.get(norm_clean) or ""

    meta = {
        "title": movie,
        "clean_title": clean,
        "imdbId": imdb_id,
        "imdbRating": None,
        "imdbReviews": None,
        "imdbUrl": None,
        "rottenTomatoes": None,
        "rottenTomatoesAudience": None,
        "rottenTomatoesUrl": None,
        "letterboxd": None,
        "letterboxdUrl": None,
        "metascore": None,
        "metacriticUserScore": None,
        "metacriticUrl": None,
        "averageScore": None,
        "plot": None,
        "director": None,
        "actors": None,
        "runtime": None,
        "released": None,
        "trailer": None
    }

    # Parallel worker helper functions
    def worker_omdb():
        try:
            omdb_url = f"http://www.omdbapi.com/?apikey=trilogy&t={urllib.parse.quote(clean)}"
            res = http_session.get(omdb_url, timeout=2.0)
            if res.status_code == 200:
                return res.json()
        except Exception as exc:
            app.logger.warning(f"OMDb fetch error: {exc}")
        return None

    def worker_ratings(tid):
        global RATINGS_RATE_LIMITED_UNTIL
        if not tid or time.time() < RATINGS_RATE_LIMITED_UNTIL:
            return None
        try:
            ratings_url = f"https://{RATINGS_RAPIDAPI_HOST}/ratings?id={tid}"
            res = http_session.get(ratings_url, headers={
                "x-rapidapi-host": RATINGS_RAPIDAPI_HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
            }, timeout=2.0)
            if res.status_code == 200:
                return res.json().get("ratings", {})
            elif res.status_code == 429:
                RATINGS_RATE_LIMITED_UNTIL = time.time() + 60
                app.logger.warning("RapidAPI Movies Ratings rate limit (429), backing off for 60s")
        except Exception as exc:
            app.logger.warning(f"Movies Ratings 2 fetch error: {exc}")
        return None

    def worker_trailer():
        # 1. Fast TMDB official YouTube trailer lookup
        tmdb_id = TITLE_TO_TMDB.get(norm_clean)
        if tmdb_id and str(tmdb_id).lower() != "nan":
            try:
                vid_url = f"{TMDB_BASE_URL}/movie/{int(float(tmdb_id))}/videos?api_key={TMDB_API_KEY}"
                res = http_session.get(vid_url, timeout=1.8)
                if res.status_code == 200:
                    vids = res.json().get("results", [])
                    for v in vids:
                        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                            v_key = v.get("key")
                            if v_key:
                                return {
                                    "videoId": v_key,
                                    "title": v.get("name") or f"{clean} Official Trailer",
                                    "thumbnail": f"https://img.youtube.com/vi/{v_key}/hqdefault.jpg",
                                    "watchUrl": f"https://www.youtube.com/watch?v={v_key}",
                                    "embedUrl": f"https://www.youtube.com/embed/{v_key}"
                                }
            except Exception as exc:
                app.logger.warning(f"TMDB trailer fetch error: {exc}")

        # 2. Fast RapidAPI YouTube Data API search
        try:
            q = urllib.parse.quote(f"{clean} official trailer")
            yt_url = f"https://{YOUTUBE_RAPIDAPI_HOST}/search?part=snippet&type=video&q={q}"
            res = http_session.get(yt_url, headers={
                "x-rapidapi-host": YOUTUBE_RAPIDAPI_HOST,
                "x-rapidapi-key": RAPIDAPI_KEY,
            }, timeout=2.0)
            if res.status_code == 200:
                items = res.json().get("items", [])
                for item in items:
                    v_id = item.get("id", {}).get("videoId")
                    if v_id:
                        snippet = item.get("snippet", {})
                        v_title = snippet.get("title") or f"{clean} Official Trailer"
                        v_thumb = (snippet.get("thumbnails", {}).get("high", {}).get("url") or 
                                   f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg")
                        return {
                            "videoId": v_id,
                            "title": v_title,
                            "thumbnail": v_thumb,
                            "watchUrl": f"https://www.youtube.com/watch?v={v_id}",
                            "embedUrl": f"https://www.youtube.com/embed/{v_id}"
                        }
        except Exception as exc:
            app.logger.warning(f"YouTube trailer search error: {exc}")

        # 3. Direct YouTube search link fallback
        return {
            "videoId": None,
            "title": f"{clean} Official Trailer",
            "thumbnail": None,
            "watchUrl": f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean + ' official trailer')}",
            "embedUrl": None
        }

    # Execute OMDb, Ratings & YouTube in parallel (fast!)
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_omdb = executor.submit(worker_omdb)
        fut_trailer = executor.submit(worker_trailer)
        fut_ratings = executor.submit(worker_ratings, imdb_id) if imdb_id else None

        omdb_data = fut_omdb.result()
        trailer_data = fut_trailer.result()

        # Resolve OMDb details & fallback imdbId
        if omdb_data and omdb_data.get("Response") == "True":
            if not imdb_id and omdb_data.get("imdbID") and omdb_data["imdbID"].startswith("tt"):
                imdb_id = omdb_data["imdbID"]
                meta["imdbId"] = imdb_id
                ratings_data = worker_ratings(imdb_id)
            elif fut_ratings:
                ratings_data = fut_ratings.result()
            else:
                ratings_data = None

            meta["imdbRating"] = omdb_data.get("imdbRating")
            meta["plot"] = omdb_data.get("Plot")
            meta["director"] = omdb_data.get("Director")
            meta["actors"] = omdb_data.get("Actors")
            meta["runtime"] = omdb_data.get("Runtime")
            meta["released"] = omdb_data.get("Released")
            for r in omdb_data.get("Ratings", []):
                if r.get("Source") == "Rotten Tomatoes" and not meta["rottenTomatoes"]:
                    meta["rottenTomatoes"] = r.get("Value")
                elif r.get("Source") == "Metacritic" and not meta["metascore"]:
                    meta["metascore"] = r.get("Value")
        else:
            ratings_data = fut_ratings.result() if fut_ratings else None

        # Parse Ratings
        if ratings_data:
            rt = ratings_data.get("rotten_tomatoes", {})
            if rt.get("tomatometer"):
                meta["rottenTomatoes"] = f"{rt['tomatometer']}%"
            if rt.get("audienceScore"):
                meta["rottenTomatoesAudience"] = f"{rt['audienceScore']}%"
            if rt.get("url"):
                meta["rottenTomatoesUrl"] = rt["url"]

            imdb_info = ratings_data.get("imdb", {})
            if imdb_info.get("score"):
                meta["imdbRating"] = str(imdb_info["score"])
            if imdb_info.get("reviewsCount"):
                meta["imdbReviews"] = imdb_info["reviewsCount"]
            if imdb_info.get("url"):
                meta["imdbUrl"] = imdb_info["url"]

            lb = ratings_data.get("letterboxd", {})
            if lb.get("score"):
                meta["letterboxd"] = str(lb["score"])
            if lb.get("url"):
                meta["letterboxdUrl"] = lb["url"]

            mc = ratings_data.get("metacritic", {})
            if mc.get("metascore"):
                meta["metascore"] = str(mc["metascore"])
            if mc.get("userScore"):
                meta["metacriticUserScore"] = str(mc["userScore"])
            if mc.get("url"):
                meta["metacriticUrl"] = mc["url"]

            avg = ratings_data.get("average", {})
            if avg.get("score"):
                meta["averageScore"] = round(float(avg["score"]), 1)

        meta["trailer"] = trailer_data

    META_CACHE[cache_key] = meta
    return jsonify(meta)


# ---------------------------------------------------------------------------
# /api/movie/streaming — Dedicated streaming availability endpoint
# ---------------------------------------------------------------------------
@app.route("/api/movie/streaming", methods=["GET"])
def get_movie_streaming():
    movie = request.args.get("movie", "").strip()
    country = request.args.get("country", "us").lower().strip()
    if not movie:
        return jsonify([])

    clean = re.sub(r"\s*\(\d{4}\)\s*$", "", movie).strip()
    if clean.lower().endswith(", the"):
        clean = "The " + clean[:-5].strip()
    elif clean.lower().endswith(", a"):
        clean = "A " + clean[:-3].strip()
    elif clean.lower().endswith(", an"):
        clean = "An " + clean[:-4].strip()

    cache_key = f"{clean.lower()}:{country}"
    if cache_key in STREAMING_CACHE:
        return jsonify(STREAMING_CACHE[cache_key])

    streaming_opts = []
    try:
        stream_url = f"https://{RAPIDAPI_HOST}/shows/search/title?title={urllib.parse.quote(clean)}&country={country}&show_type=movie"
        res = http_session.get(stream_url, headers={
            "x-rapidapi-host": RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY,
        }, timeout=4.0)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                first_show = data[0]
                opts = first_show.get("streamingOptions", {}).get(country, [])
                seen = set()
                for opt in opts:
                    service = opt.get("service", {})
                    s_name = service.get("name")
                    s_type = opt.get("type")
                    key = (s_name, s_type)
                    if s_name and key not in seen:
                        seen.add(key)
                        logo = service.get("imageSet", {}).get("lightThemeImage") or service.get("imageSet", {}).get("whiteImage")
                        streaming_opts.append({
                            "service": s_name,
                            "type": s_type,
                            "link": opt.get("link"),
                            "logo": logo,
                            "price": opt.get("price", {}).get("formatted")
                        })
    except Exception as exc:
        app.logger.warning(f"Streaming Availability fetch error for '{clean}': {exc}")

    STREAMING_CACHE[cache_key] = streaming_opts
    return jsonify(streaming_opts)


# ---------------------------------------------------------------------------
# /api/movies/latest — Fetch new / trending movies from TMDB
# ---------------------------------------------------------------------------
@app.route("/api/movies/latest", methods=["GET"])
def get_latest_movies():
    feed_type = request.args.get("type", "now_playing").lower().strip()
    if feed_type in LATEST_CACHE:
        return jsonify(LATEST_CACHE[feed_type])

    endpoint = "now_playing" if feed_type == "now_playing" else "popular"
    url = f"{TMDB_BASE_URL}/movie/{endpoint}?api_key={TMDB_API_KEY}&language=en-US&page=1"
    
    try:
        res = http_session.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            results = []
            for item in data.get("results", [])[:18]:
                results.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "overview": item.get("overview"),
                    "release_date": item.get("release_date"),
                    "average_rating": round(item.get("vote_average", 0.0), 1),
                    "rating_count": item.get("vote_count", 0),
                    "poster_url": f"{TMDB_IMG_BASE_URL}{item.get('poster_path')}" if item.get("poster_path") else None
                })
            LATEST_CACHE[feed_type] = results
            return jsonify(results)
    except Exception as exc:
        app.logger.warning(f"TMDB latest movies fetch failed: {exc}")
    return jsonify([])


# ---------------------------------------------------------------------------
# /api/imdb/top250 — Fetch official IMDb Top 250 movies from RapidAPI IMDb
# ---------------------------------------------------------------------------
@app.route("/api/imdb/top250", methods=["GET"])
def get_imdb_top250():
    global IMDB_TOP250_CACHE
    if IMDB_TOP250_CACHE:
        return jsonify(IMDB_TOP250_CACHE)

    url = f"https://{IMDB_RAPIDAPI_HOST}/api/imdb/top250-movies"
    try:
        res = http_session.get(url, headers={
            "x-rapidapi-host": IMDB_RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY,
        }, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            results = []
            for item in data[:30]:
                results.append({
                    "id": item.get("id"),
                    "title": item.get("primaryTitle"),
                    "startYear": item.get("startYear"),
                    "averageRating": item.get("averageRating"),
                    "numVotes": item.get("numVotes"),
                    "description": item.get("description"),
                    "poster_url": item.get("primaryImage"),
                    "genres": item.get("genres", [])
                })
            IMDB_TOP250_CACHE = results
            return jsonify(results)
    except Exception as exc:
        app.logger.warning(f"IMDb Top 250 fetch failed: {exc}")
    return jsonify([])


# ---------------------------------------------------------------------------
# /api/imdb/random — Fetch a random movie from RapidAPI IMDb
# ---------------------------------------------------------------------------
@app.route("/api/imdb/random", methods=["GET"])
def get_imdb_random():
    url = f"https://{IMDB_RAPIDAPI_HOST}/api/imdb/random?type=movie"
    try:
        res = http_session.get(url, headers={
            "x-rapidapi-host": IMDB_RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY,
        }, timeout=4.0)
        if res.status_code == 200:
            data = res.json()
            return jsonify({
                "id": data.get("id"),
                "title": data.get("primaryTitle"),
                "year": data.get("startYear"),
                "averageRating": data.get("averageRating"),
                "description": data.get("description"),
                "poster_url": data.get("primaryImage"),
                "genres": data.get("genres", []),
                "director": data.get("directors", [{}])[0].get("fullName") if data.get("directors") else None,
                "cast": ", ".join([c.get("fullName") for c in data.get("cast", [])[:3] if c.get("fullName")])
            })
    except Exception as exc:
        app.logger.warning(f"IMDb random fetch failed: {exc}")
    return jsonify({"error": "Failed to fetch random movie"}), 500


# ===========================================================================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
