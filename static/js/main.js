/**
 * CineMatch - Modern AI Recommender Frontend Script
 * Handles real-time recommendations, interactive device mockup, autocomplete,
 * dynamic poster loading, genre filtering, and full library browsing.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Initialize ambient particle effects & mockup demo
    initAmbientParticles();
    initMockupDemo();
    initNavbarScroll();
    
    // Core Application State
    const AppState = {
        genres: [],
        currentGenre: "all",
        browsePage: 1,
        browseLimit: 18,
        browseSearchQuery: "",
        autocompleteController: null,
        browseDebounceTimer: null,
        isPlayingDemo: true,
        demoTimerSeconds: 339 // 05:39
    };

    // DOM Elements
    const searchInput = document.getElementById("searchInput");
    const searchBtn = document.getElementById("searchBtn");
    const autocompleteResults = document.getElementById("autocompleteResults");
    const heroStartBtn = document.getElementById("heroStartBtn");
    const quickTags = document.getElementById("quickTags");
    const quickExploreBtn = document.getElementById("quickExploreBtn");
    const userMenuBtn = document.getElementById("userMenuBtn");
    
    const recommendationsSec = document.getElementById("recommendations");
    const selectedMovieCard = document.getElementById("selectedMovieCard");
    const recommendationsGrid = document.getElementById("recommendationsGrid");
    
    const genreTabs = document.getElementById("genreTabs");
    const genreMoviesGrid = document.getElementById("genreMoviesGrid");
    const newMoviesGrid = document.getElementById("newMoviesGrid");
    
    const browseMoviesGrid = document.getElementById("browseMoviesGrid");
    const loadMoreBtn = document.getElementById("loadMoreBtn");
    const totalMoviesCount = document.getElementById("totalMoviesCount");
    const browseSearchInput = document.getElementById("browseSearchInput");

    const movieModal = document.getElementById("movieModal");
    const modalContent = document.getElementById("modalContent");
    const modalCloseBtn = document.getElementById("modalCloseBtn");

    // ==========================================================================
    // INITIALIZATION & EVENT LISTENERS
    // ==========================================================================
    
    // Load Genres List
    fetchGenres();
    
    // Load Category Movies (All by default)
    loadGenreMovies("all");

    // Load In Theaters & Trending Releases
    loadNewReleases();
    
    // Load General Library Catalog
    loadBrowseCatalog(true);

    // Hero Action Buttons
    if (heroStartBtn) {
        heroStartBtn.addEventListener("click", () => {
            searchInput.focus();
            searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    }

    // Quick Tag Chips Click
    if (quickTags) {
        quickTags.addEventListener("click", (e) => {
            const tag = e.target.closest(".quick-tag");
            if (!tag) return;
            const movie = tag.dataset.movie;
            if (movie) {
                searchInput.value = movie;
                triggerRecommendation(movie);
            }
        });
    }

    // Quick Random Explore Button (Connected to Live IMDb Random API)
    if (quickExploreBtn) {
        quickExploreBtn.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/imdb/random");
                if (res.ok) {
                    const randMovie = await res.json();
                    if (randMovie && randMovie.title) {
                        searchInput.value = randMovie.title;
                        showQuickNotification(`🎲 Discovered on IMDb: ${randMovie.title} (${randMovie.year || 'Film'}) — ⭐ ${randMovie.averageRating || 'N/A'}`);
                        triggerRecommendation(randMovie.title);
                        return;
                    }
                }
            } catch (e) {
                console.warn("IMDb random fetch fallback:", e);
            }

            const samplePicks = [
                "Interstellar (2014)",
                "Inception (2010)",
                "Matrix, The (1999)",
                "Toy Story (1995)",
                "Pulp Fiction (1994)",
                "Dark Knight, The (2008)",
                "Fight Club (1999)",
                "Forrest Gump (1994)",
                "Gladiator (2000)",
                "Spirited Away (2001)"
            ];
            const randomPick = samplePicks[Math.floor(Math.random() * samplePicks.length)];
            searchInput.value = randomPick;
            triggerRecommendation(randomPick);
        });
    }

    // User Profile / Taste Quick Alert
    if (userMenuBtn) {
        userMenuBtn.addEventListener("click", () => {
            showQuickNotification("Guest Taste Profile active • 9,700+ films loaded for instant matching!");
        });
    }

    // Search Autocomplete Events
    searchInput.addEventListener("input", handleSearchInput);
    searchInput.addEventListener("keydown", handleSearchKeyDown);
    document.addEventListener("click", handleDocumentClick);
    
    // Recommendation Request Action
    searchBtn.addEventListener("click", () => {
        triggerRecommendation(searchInput.value);
    });

    // Genre Tabs Selection Action
    genreTabs.addEventListener("click", (e) => {
        const tab = e.target.closest(".genre-tab");
        if (!tab) return;
        
        // Update active class
        document.querySelectorAll(".genre-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        
        const selectedGenre = tab.dataset.genre;
        AppState.currentGenre = selectedGenre;
        loadGenreMovies(selectedGenre);
    });

    // Library Searching & Filtering
    browseSearchInput.addEventListener("input", () => {
        clearTimeout(AppState.browseDebounceTimer);
        AppState.browseDebounceTimer = setTimeout(() => {
            AppState.browseSearchQuery = browseSearchInput.value.trim();
            AppState.browsePage = 1;
            loadBrowseCatalog(true);
        }, 300);
    });

    // Load More Action
    loadMoreBtn.addEventListener("click", () => {
        AppState.browsePage++;
        loadBrowseCatalog(false);
    });

    // Modal Events
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener("click", closeModal);
    }
    if (movieModal) {
        movieModal.addEventListener("click", (e) => {
            if (e.target === movieModal) closeModal();
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });

    // ==========================================================================
    // BACKEND API CONNECTIVITY
    // ==========================================================================

    async function fetchGenres() {
        try {
            const res = await fetch("/api/genres");
            const data = await res.json();
            AppState.genres = data;
        } catch (err) {
            console.error("Failed to load genres:", err);
        }
    }

    async function loadGenreMovies(genre) {
        genreMoviesGrid.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
        `;
        
        try {
            const res = await fetch(`/api/movies?genre=${encodeURIComponent(genre)}&limit=12&page=1`);
            const data = await res.json();
            
            genreMoviesGrid.innerHTML = "";
            
            if (!data.movies || data.movies.length === 0) {
                genreMoviesGrid.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-face-frown empty-state-icon"></i>
                        <p>No movies found for genre "${genre}".</p>
                    </div>
                `;
                return;
            }
            
            data.movies.forEach(movie => {
                const card = createMovieCard(movie, false);
                genreMoviesGrid.appendChild(card);
            });
        } catch (err) {
            genreMoviesGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="color:#ef4444"></i>
                    <p>Failed to load movies. Is the server running?</p>
                </div>
            `;
            console.error("Genre load error:", err);
        }
    }

    async function loadNewReleases() {
        if (!newMoviesGrid) return;
        newMoviesGrid.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
        `;

        try {
            const res = await fetch("/api/movies/latest?type=now_playing");
            const movies = await res.json();

            newMoviesGrid.innerHTML = "";
            if (!movies || movies.length === 0) {
                newMoviesGrid.innerHTML = `
                    <div class="empty-state">
                        <p>No new releases available right now.</p>
                    </div>
                `;
                return;
            }

            movies.forEach(movie => {
                const card = document.createElement("div");
                card.className = "movie-card";

                const ratingVal = movie.average_rating > 0 ? movie.average_rating.toFixed(1) : "N/A";
                const year = movie.release_date ? movie.release_date.split("-")[0] : "";

                card.innerHTML = `
                    <div class="movie-poster-container">
                        <div class="card-badges-wrapper">
                            <div class="similarity-badge" style="background:linear-gradient(135deg, #10b981, #059669);">
                                <i class="fa-solid fa-fire"></i> New Release
                            </div>
                            <div class="rating-badge">
                                <i class="fa-solid fa-star"></i> ${ratingVal}
                            </div>
                        </div>
                        ${movie.poster_url 
                            ? `<img class="movie-poster-img" src="${movie.poster_url}" alt="${movie.title} Poster" loading="lazy">`
                            : `<div class="poster-fallback"><i class="fa-solid fa-film poster-fallback-icon"></i><div>${movie.title}</div></div>`
                        }
                    </div>
                    <div class="movie-details-body">
                        <h4 class="movie-card-title" title="${movie.title}">${movie.title}</h4>
                        <div class="movie-card-genres">${year ? `Released: ${year}` : 'Latest Release'}</div>
                        <div class="movie-card-stars-row">
                            <div class="movie-stars">${renderStarRating(movie.average_rating / 2)}</div>
                            <span class="rating-count">(${movie.rating_count || 0})</span>
                        </div>
                    </div>
                    <div class="movie-card-action">
                        <button class="card-info-btn" data-movie="${movie.title}" title="View details, ratings & trailer">
                            <i class="fa-solid fa-circle-info"></i>
                            View Info
                        </button>
                        <button class="card-action-btn" data-movie="${movie.title}" title="Find movies similar to ${movie.title}">
                            <i class="fa-solid fa-wand-magic-sparkles"></i>
                            Similar
                        </button>
                    </div>
                `;

                const infoBtn = card.querySelector(".card-info-btn");
                if (infoBtn) {
                    infoBtn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        openMovieModal(movie);
                    });
                }

                const simBtn = card.querySelector(".card-action-btn");
                if (simBtn) {
                    simBtn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        triggerRecommendation(movie.title);
                    });
                }

                card.addEventListener("click", () => {
                    openMovieModal(movie);
                });

                newMoviesGrid.appendChild(card);
            });
        } catch (err) {
            console.error("Failed to load new releases:", err);
            newMoviesGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="color:#ef4444"></i>
                    <p>Failed to load new releases from TMDb.</p>
                </div>
            `;
        }
    }

    async function loadBrowseCatalog(reset = false) {
        if (reset) {
            browseMoviesGrid.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                </div>
            `;
            loadMoreBtn.style.display = "none";
        }
        
        try {
            const queryParam = AppState.browseSearchQuery ? `&q=${encodeURIComponent(AppState.browseSearchQuery)}` : "";
            const res = await fetch(`/api/movies?page=${AppState.browsePage}&limit=${AppState.browseLimit}${queryParam}`);
            const data = await res.json();
            
            if (reset) {
                browseMoviesGrid.innerHTML = "";
            } else {
                const loader = browseMoviesGrid.querySelector(".loading-spinner");
                if (loader) loader.remove();
            }
            
            if (!data.movies || data.movies.length === 0) {
                if (reset) {
                    browseMoviesGrid.innerHTML = `
                        <div class="empty-state">
                            <i class="fa-solid fa-magnifying-glass empty-state-icon"></i>
                            <p>No movies match your search query.</p>
                        </div>
                    `;
                }
                totalMoviesCount.textContent = "0 movies found";
                loadMoreBtn.style.display = "none";
                return;
            }
            
            totalMoviesCount.textContent = `Showing ${reset ? data.movies.length : browseMoviesGrid.children.length + data.movies.length} of ${data.total} movies`;

            data.movies.forEach(movie => {
                const card = createMovieCard(movie, false);
                browseMoviesGrid.appendChild(card);
            });

            if (data.page < data.pages) {
                loadMoreBtn.style.display = "inline-flex";
            } else {
                loadMoreBtn.style.display = "none";
            }
        } catch (err) {
            browseMoviesGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="color:#ef4444"></i>
                    <p>Error loading movie library.</p>
                </div>
            `;
            console.error("Catalog load error:", err);
        }
    }

    async function triggerRecommendation(movieTitle) {
        if (!movieTitle || !movieTitle.trim()) return;
        
        searchInput.value = movieTitle;
        hideAutocomplete();

        // Reveal recommendations section and scroll smoothly
        recommendationsSec.classList.remove("hidden");
        recommendationsSec.scrollIntoView({ behavior: "smooth", block: "start" });
        
        selectedMovieCard.innerHTML = `
            <div class="loading-spinner" style="min-height:160px;">
                <div class="spinner"></div>
            </div>
        `;
        recommendationsGrid.innerHTML = `
            <div class="loading-spinner" style="min-height:160px;">
                <div class="spinner"></div>
            </div>
        `;

        try {
            const res = await fetch(`/api/recommend?movie=${encodeURIComponent(movieTitle)}&top_n=6`);
            if (!res.ok) {
                const errorData = await res.json();
                handleRecommendationError(errorData, movieTitle);
                return;
            }
            
            const data = await res.json();
            
            // Render Selected Movie Card
            renderSelectedMovie(data.input_movie);
            
            // Render Recommended List
            recommendationsGrid.innerHTML = "";
            data.recommendations.forEach(movie => {
                const card = createMovieCard(movie, true);
                recommendationsGrid.appendChild(card);
            });
            
        } catch (err) {
            console.error("Recommendations error:", err);
            recommendationsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-exclamation empty-state-icon" style="color:#ef4444"></i>
                    <p>Failed to generate recommendations. Please try again.</p>
                </div>
            `;
        }
    }

    function handleRecommendationError(errorData, searchTitle) {
        selectedMovieCard.innerHTML = `
            <div class="empty-state" style="padding: 1.5rem 0;">
                <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="font-size:2rem; color:#ef4444"></i>
                <p style="font-size:0.95rem; font-weight:700; color:var(--text-primary); margin-top:0.5rem;">"${searchTitle}" Not Found</p>
            </div>
        `;
        
        let suggestionsHTML = "";
        if (errorData.suggestions && errorData.suggestions.length > 0) {
            suggestionsHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <p style="margin-bottom: 1rem; font-weight:700; color:var(--text-primary);">Did you mean one of these titles?</p>
                    <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:0.6rem; max-width:480px; margin:0 auto;">
                        ${errorData.suggestions.map(s => `
                            <button class="suggestion-item-btn quick-tag" data-movie="${s}" style="padding:0.4rem 0.9rem; font-size:0.85rem;">
                                ${s}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        } else {
            suggestionsHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <i class="fa-solid fa-magnifying-glass empty-state-icon"></i>
                    <p>No similar titles found in the database. Please try a different name or browse the library below.</p>
                </div>
            `;
        }
        
        recommendationsGrid.innerHTML = suggestionsHTML;
        
        recommendationsGrid.querySelectorAll(".suggestion-item-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                triggerRecommendation(btn.dataset.movie);
            });
        });
    }

    // ==========================================================================
    // AUTOCOMPLETE SEARCH LOGIC
    // ==========================================================================
    
    async function handleSearchInput() {
        const value = searchInput.value.trim();
        
        if (value.length < 2) {
            hideAutocomplete();
            return;
        }

        if (AppState.autocompleteController) {
            AppState.autocompleteController.abort();
        }
        
        AppState.autocompleteController = new AbortController();
        const signal = AppState.autocompleteController.signal;

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(value)}`, { signal });
            const movies = await res.json();
            renderAutocomplete(movies);
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.error("Autocomplete error:", err);
            }
        }
    }

    function renderAutocomplete(movies) {
        if (!movies || movies.length === 0) {
            hideAutocomplete();
            return;
        }

        autocompleteResults.innerHTML = "";
        movies.forEach((movie) => {
            const item = document.createElement("div");
            item.className = "autocomplete-item";
            item.dataset.movie = movie.title;
            
            const ratingText = movie.average_rating > 0 
                ? `<i class="fa-solid fa-star"></i> ${movie.average_rating.toFixed(1)}` 
                : `<span style="color:var(--text-muted)">Unrated</span>`;

            item.innerHTML = `
                <div class="autocomplete-item-details">
                    <div class="autocomplete-item-title">${movie.title}</div>
                    <div class="autocomplete-item-genres">${movie.genres || 'General'}</div>
                </div>
                <div class="autocomplete-item-rating">${ratingText}</div>
            `;
            
            item.addEventListener("click", () => {
                triggerRecommendation(movie.title);
            });
            
            autocompleteResults.appendChild(item);
        });

        autocompleteResults.classList.remove("hidden");
    }

    function handleSearchKeyDown(e) {
        const items = autocompleteResults.querySelectorAll(".autocomplete-item");
        if (items.length === 0) return;

        let activeIdx = -1;
        items.forEach((item, idx) => {
            if (item.classList.contains("active")) {
                activeIdx = idx;
            }
        });

        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIdx = (activeIdx + 1) % items.length;
            setActiveAutocompleteItem(items, activeIdx);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIdx = (activeIdx - 1 + items.length) % items.length;
            setActiveAutocompleteItem(items, activeIdx);
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (activeIdx >= 0) {
                triggerRecommendation(items[activeIdx].dataset.movie);
            } else {
                triggerRecommendation(searchInput.value);
            }
        } else if (e.key === "Escape") {
            hideAutocomplete();
        }
    }

    function setActiveAutocompleteItem(items, index) {
        items.forEach(item => item.classList.remove("active"));
        if (index >= 0) {
            items[index].classList.add("active");
            searchInput.value = items[index].dataset.movie;
            items[index].scrollIntoView({ block: "nearest" });
        }
    }

    function hideAutocomplete() {
        autocompleteResults.classList.add("hidden");
        autocompleteResults.innerHTML = "";
    }

    function handleDocumentClick(e) {
        if (!e.target.closest(".search-container-outer")) {
            hideAutocomplete();
        }
    }

    // ==========================================================================
    // MOVIE CARD RENDERER & ARTWORK FETCHING
    // ==========================================================================

    function createMovieCard(movie, isRecommendation = false) {
        const card = document.createElement("div");
        card.className = "movie-card";
        
        const titleClean = cleanMovieTitle(movie.title);
        const ratingText = movie.average_rating > 0 ? movie.average_rating.toFixed(1) : "N/A";
        const simBadge = isRecommendation 
            ? `<div class="similarity-badge"><i class="fa-solid fa-bolt"></i> ${(movie.similarity_score * 100).toFixed(0)}% Match</div>` 
            : "";

        card.innerHTML = `
            <div class="movie-poster-container">
                <div class="card-badges-wrapper">
                    ${simBadge}
                    <div class="rating-badge"><i class="fa-solid fa-star"></i> ${ratingText}</div>
                </div>
                <div class="poster-loader" style="position:absolute; top:0; left:0; width:100%; height:100%; display:flex; justify-content:center; align-items:center; background:#111424;">
                    <div class="spinner" style="width:24px; height:24px; border-width:2px;"></div>
                </div>
                <img class="movie-poster-img" 
                     src="/api/poster?movie=${encodeURIComponent(movie.title)}" 
                     alt="${movie.title} Poster" 
                     loading="lazy" 
                     style="opacity:0; transition:opacity 0.25s ease;"
                     onload="this.style.opacity='1'; const l = this.parentElement.querySelector('.poster-loader'); if(l) l.remove();"
                     onerror="const l = this.parentElement.querySelector('.poster-loader'); if(l) l.remove(); this.remove(); const fb = this.parentElement?.querySelector('.poster-fallback'); if(fb) fb.classList.remove('hidden');">
                <div class="poster-fallback hidden">
                    <i class="fa-solid fa-film poster-fallback-icon"></i>
                    <div class="poster-fallback-title">${titleClean}</div>
                </div>
            </div>
            <div class="movie-details-body">
                <h4 class="movie-card-title" title="${movie.title}">${movie.title}</h4>
                <div class="movie-card-genres">${movie.genres || 'Genres Unlisted'}</div>
                
                <div class="movie-card-stars-row">
                    <div class="movie-stars">${renderStarRating(movie.average_rating)}</div>
                    <span class="rating-count">(${movie.rating_count || 0})</span>
                </div>
            </div>
            <div class="movie-card-action">
                <button class="card-info-btn" data-movie="${movie.title}" title="View details, ratings & trailer">
                    <i class="fa-solid fa-circle-info"></i>
                    View Info
                </button>
                <button class="card-action-btn" data-movie="${movie.title}" title="Find movies similar to ${movie.title}">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                    Similar
                </button>
            </div>
        `;

        const img = card.querySelector(".movie-poster-img");
        const loader = card.querySelector(".poster-loader");
        if (img && img.complete && img.naturalWidth > 0) {
            img.style.opacity = "1";
            if (loader) loader.remove();
        }

        // View Info button triggers details modal
        const infoBtn = card.querySelector(".card-info-btn");
        if (infoBtn) {
            infoBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                openMovieModal(movie);
            });
        }

        // Find Similar button triggers recommendation
        const simBtn = card.querySelector(".card-action-btn");
        if (simBtn) {
            simBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                triggerRecommendation(movie.title);
            });
        }

        // Clicking on the poster or body opens the quick view modal
        card.querySelector(".movie-poster-container").addEventListener("click", () => {
            openMovieModal(movie);
        });
        card.querySelector(".movie-details-body").addEventListener("click", () => {
            openMovieModal(movie);
        });

        return card;
    }

    async function renderSelectedMovie(movie) {
        selectedMovieCard.innerHTML = "";
        
        const ratingText = movie.average_rating > 0 ? movie.average_rating.toFixed(1) : "N/A";
        const titleClean = cleanMovieTitle(movie.title);
        
        const cardInner = document.createElement("div");
        cardInner.className = "selected-movie-header-info";
        cardInner.innerHTML = `
            <div class="movie-poster-container" style="border-radius:16px; margin-bottom:1.25rem; box-shadow:0 12px 28px -6px rgba(0,0,0,0.25); max-width:240px; width:100%;">
                <div class="card-badges-wrapper">
                    <div class="rating-badge"><i class="fa-solid fa-star"></i> ${ratingText}</div>
                </div>
                <div class="poster-loader" style="position:absolute; top:0; left:0; width:100%; height:100%; display:flex; justify-content:center; align-items:center; background:#111424;">
                    <div class="spinner" style="width:24px; height:24px; border-width:2px;"></div>
                </div>
                <img class="movie-poster-img" 
                     src="/api/poster?movie=${encodeURIComponent(movie.title)}" 
                     alt="${movie.title} Poster" 
                     style="border-radius:16px; opacity:0; transition:opacity 0.25s ease;"
                     onload="this.style.opacity='1'; const l = this.parentElement.querySelector('.poster-loader'); if(l) l.remove();"
                     onerror="const l = this.parentElement.querySelector('.poster-loader'); if(l) l.remove(); this.remove(); const fb = this.parentElement?.querySelector('.poster-fallback'); if(fb) fb.classList.remove('hidden');">
                <div class="poster-fallback hidden" style="border-radius:16px;">
                    <i class="fa-solid fa-film poster-fallback-icon"></i>
                    <div class="poster-fallback-title">${titleClean}</div>
                </div>
            </div>
            <h3 class="selected-movie-title">${movie.title}</h3>
            <div class="selected-movie-meta">
                <div style="font-size:0.85rem; color:var(--text-secondary);">${movie.genres || 'General'}</div>
                <div class="movie-card-stars-row" style="margin-top:0.3rem;">
                    <div class="movie-stars">${renderStarRating(movie.average_rating)}</div>
                    <span class="rating-count">(${movie.rating_count || 0} reviews)</span>
                </div>
                <div style="margin-top:0.85rem;">
                    <button class="card-info-btn selected-info-btn" style="display:inline-flex; width:auto; padding:0.45rem 1rem;">
                        <i class="fa-solid fa-circle-info"></i> View Details & Trailer
                    </button>
                </div>
            </div>
        `;
        
        selectedMovieCard.appendChild(cardInner);
        
        const img = cardInner.querySelector(".movie-poster-img");
        const loader = cardInner.querySelector(".poster-loader");
        if (img && img.complete && img.naturalWidth > 0) {
            img.style.opacity = "1";
            if (loader) loader.remove();
        }

        const selInfoBtn = cardInner.querySelector(".selected-info-btn");
        if (selInfoBtn) {
            selInfoBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                openMovieModal(movie);
            });
        }

        cardInner.style.cursor = "pointer";
        cardInner.title = "Click to view ratings, trailer & streaming availability";
        cardInner.addEventListener("click", () => {
            openMovieModal(movie);
        });
    }

    // ==========================================================================
    // POSTER LOADING HELPERS
    // ==========================================================================

    function lazyLoadPoster(img, loader, fallback, title) {
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    obs.disconnect();
                    loadPosterNow(img, loader, fallback, title);
                }
            });
        }, { rootMargin: '150px' });

        observer.observe(img);
    }

    function loadPosterNow(img, loader, fallback, title) {
        img.onload = () => {
            if (loader) loader.remove();
            img.classList.remove("hidden");
        };
        img.onerror = () => {
            if (loader) loader.remove();
            img.remove();
            fallback.classList.remove("hidden");
        };
        img.src = `/api/poster?movie=${encodeURIComponent(title)}`;
    }

    function cleanMovieTitle(title) {
        return title.replace(/\s*\(\d{4}\)\s*/g, "").replace(/,\s*The\s*$/gi, "").trim();
    }

    function renderStarRating(rating) {
        if (!rating || rating <= 0) return `<i class="fa-regular fa-star"></i>`.repeat(5);
        
        let stars = "";
        const fullStars = Math.floor(rating);
        const hasHalf = rating % 1 >= 0.3 && rating % 1 <= 0.7;
        const extraFull = rating % 1 > 0.7 ? 1 : 0;
        
        stars += `<i class="fa-solid fa-star"></i>`.repeat(fullStars + extraFull);
        if (hasHalf) stars += `<i class="fa-solid fa-star-half-stroke"></i>`;
        
        const emptyStars = 5 - (fullStars + extraFull + (hasHalf ? 1 : 0));
        if (emptyStars > 0) stars += `<i class="fa-regular fa-star"></i>`.repeat(emptyStars);
        
        return stars;
    }

    // ==========================================================================
    // INTERACTIVE MOCKUP SHOWCASE DEMO (Right Column in Hero)
    // ==========================================================================

    function initMockupDemo() {
        const playPauseBtn = document.getElementById("mockupPlayPauseBtn");
        const demoTimer = document.getElementById("demoTimer");
        const waveformBars = document.querySelectorAll(".waveform-bars .bar");
        const speechBubble = document.querySelector(".floating-insight-bubble");

        // Timer interval
        setInterval(() => {
            if (!AppState.isPlayingDemo) return;
            AppState.demoTimerSeconds++;
            const mins = String(Math.floor(AppState.demoTimerSeconds / 60)).padStart(2, "0");
            const secs = String(AppState.demoTimerSeconds % 60).padStart(2, "0");
            if (demoTimer) demoTimer.textContent = `00:${mins}:${secs}`;
        }, 1000);

        // Play/Pause button
        if (playPauseBtn) {
            playPauseBtn.addEventListener("click", () => {
                AppState.isPlayingDemo = !AppState.isPlayingDemo;
                const icon = playPauseBtn.querySelector("i");
                if (AppState.isPlayingDemo) {
                    icon.className = "fa-solid fa-pause";
                    waveformBars.forEach(b => b.style.animationPlayState = "running");
                } else {
                    icon.className = "fa-solid fa-play";
                    waveformBars.forEach(b => b.style.animationPlayState = "paused");
                }
            });
        }

        // Clicking speech bubble triggers live demo recommendation
        if (speechBubble) {
            speechBubble.style.cursor = "pointer";
            speechBubble.title = "Click to run AI match for Inception!";
            speechBubble.addEventListener("click", () => {
                triggerRecommendation("Inception (2010)");
            });
        }
    }

    // ==========================================================================
    // INTERACTIVE MOVIE MODAL
    // ==========================================================================

    async function openMovieModal(movie) {
        if (!movieModal || !modalContent) return;
        const initialRating = movie.average_rating > 0 ? movie.average_rating.toFixed(1) : "N/A";
        const posterSrc = movie.poster_url || `/api/poster?movie=${encodeURIComponent(movie.title)}`;
        const cleanTitle = cleanMovieTitle(movie.title);
        const movieImdbId = movie.imdbId || "";

        modalContent.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:1.4rem;">
                <!-- Header Row: Poster & Core Info -->
                <div style="display:flex; flex-direction:column; md:flex-row; gap:1.75rem; align-items:flex-start;">
                    <div style="max-width:210px; width:100%; border-radius:18px; overflow:hidden; box-shadow:0 15px 35px -10px rgba(0,0,0,0.25); flex-shrink:0;">
                        <img src="${posterSrc}" 
                             alt="${movie.title}" 
                             style="width:100%; height:auto; display:block; object-fit:cover;"
                             onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=400&q=80';">
                    </div>
                    <div style="flex:1; width:100%;">
                        <div style="display:inline-block; background:#f5f3ff; color:var(--accent-violet); padding:0.25rem 0.75rem; border-radius:9999px; font-size:0.75rem; font-weight:700; text-transform:uppercase; margin-bottom:0.6rem;">
                            ${movie.genres || 'Feature Film'}
                        </div>
                        <h2 style="font-size:1.75rem; font-weight:800; color:var(--text-primary); margin-bottom:0.3rem; line-height:1.2;">${movie.title}</h2>
                        
                        <!-- Multi-Source Ratings Strip -->
                        <div class="ratings-strip" id="modalRatingsStrip">
                            <span class="rating-pill-source rating-pill-tmdb" title="TMDb Community Rating"><i class="fa-solid fa-star"></i> TMDb: ${initialRating}</span>
                            <span id="modalRatingsDynamicSlot" style="display:contents;">
                                <!-- Dynamically loaded from RapidAPI: IMDb, Rotten Tomatoes Critics, RT Audience, Letterboxd, Metacritic -->
                            </span>
                        </div>

                        <!-- Plot / Overview -->
                        <p id="modalPlot" style="font-size:0.92rem; line-height:1.6; color:var(--text-secondary); margin-bottom:1rem;">
                            ${movie.overview || "Loading synopsis and metadata..."}
                        </p>

                        <!-- Director & Cast metadata -->
                        <div id="modalCredits" style="font-size:0.82rem; color:var(--text-muted); line-height:1.5; margin-bottom:1rem;">
                        </div>

                        <!-- Actions -->
                        <div style="display:flex; gap:0.75rem; margin-top:1rem; flex-wrap:wrap;">
                            <button id="modalRecommendBtn" class="btn-gradient-pill" style="font-size:0.95rem; padding:0.75rem 1.6rem;">
                                <span class="btn-arrow-circle"><i class="fa-solid fa-wand-magic-sparkles"></i></span>
                                <span>Find Similar Films</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Official YouTube Movie Trailer Section -->
                <div class="trailer-section" id="modalTrailerSection">
                    <div class="trailer-header">
                        <div class="trailer-title-left">
                            <i class="fa-brands fa-youtube" style="color:#ef4444; font-size:1.15rem;"></i>
                            <span>Official Movie Trailer</span>
                        </div>
                    </div>
                    <div id="modalTrailerContainer">
                        <div style="font-size:0.82rem; color:var(--text-muted); display:flex; align-items:center; gap:0.5rem; padding:0.6rem 0;">
                            <div class="spinner" style="width:16px; height:16px; border-width:2px;"></div>
                            Searching official YouTube trailer on RapidAPI...
                        </div>
                    </div>
                </div>

                <!-- Streaming Availability Section ("Where to Watch") -->
                <div class="streaming-section" id="modalStreamingSection">
                    <div class="streaming-header">
                        <i class="fa-solid fa-tv"></i>
                        <span>Where to Stream / Watch (US)</span>
                    </div>
                    <div class="streaming-grid" id="modalStreamingGrid">
                        <div style="font-size:0.82rem; color:var(--text-muted); display:flex; align-items:center; gap:0.5rem;">
                            <div class="spinner" style="width:16px; height:16px; border-width:2px;"></div>
                            Checking live streaming availability on RapidAPI...
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modalRecommendBtn = modalContent.querySelector("#modalRecommendBtn");
        if (modalRecommendBtn) {
            modalRecommendBtn.addEventListener("click", () => {
                closeModal();
                triggerRecommendation(movie.title);
            });
        }

        movieModal.classList.remove("hidden");

        const queryParams = new URLSearchParams({
            movie: movie.title,
            country: "us"
        });
        if (movieImdbId) queryParams.append("imdbId", movieImdbId);

        // 1. Fetch live multi-source ratings, plot, cast & official YouTube trailer
        fetch(`/api/movie/meta?${queryParams.toString()}`)
            .then(res => res.ok ? res.json() : null)
            .then(meta => {
                if (!meta) return;

                // Multi-source Ratings Rendering
                const ratingsSlot = document.getElementById("modalRatingsDynamicSlot");
                if (ratingsSlot) {
                    let pillsHTML = "";
                    
                    // IMDb Rating
                    if (meta.imdbRating && meta.imdbRating !== "N/A") {
                        const imdbLink = meta.imdbUrl || (meta.imdbId ? `https://www.imdb.com/title/${meta.imdbId}/` : "#");
                        const reviews = meta.imdbReviews ? ` <span style="font-size:0.7rem; opacity:0.8;">(${Number(meta.imdbReviews).toLocaleString()})</span>` : "";
                        pillsHTML += `
                            <a href="${imdbLink}" target="_blank" rel="noopener noreferrer" class="rating-pill-source rating-pill-imdb" title="View on IMDb">
                                <i class="fa-brands fa-imdb"></i> IMDb: ${meta.imdbRating}/10${reviews}
                            </a>
                        `;
                    }

                    // Rotten Tomatoes Tomatometer (Critics)
                    if (meta.rottenTomatoes) {
                        const rtLink = meta.rottenTomatoesUrl || `https://www.rottentomatoes.com/search?search=${encodeURIComponent(cleanTitle)}`;
                        pillsHTML += `
                            <a href="${rtLink}" target="_blank" rel="noopener noreferrer" class="rating-pill-source rating-pill-rt" title="Rotten Tomatoes Tomatometer (Critics)">
                                🍅 ${meta.rottenTomatoes} Critics
                            </a>
                        `;
                    }

                    // Rotten Tomatoes Audience Score
                    if (meta.rottenTomatoesAudience) {
                        const rtLink = meta.rottenTomatoesUrl || `https://www.rottentomatoes.com/search?search=${encodeURIComponent(cleanTitle)}`;
                        pillsHTML += `
                            <a href="${rtLink}" target="_blank" rel="noopener noreferrer" class="rating-pill-source rating-pill-rt-audience" title="Rotten Tomatoes Audience Popcorn Score">
                                🍿 ${meta.rottenTomatoesAudience} Audience
                            </a>
                        `;
                    }

                    // Letterboxd
                    if (meta.letterboxd) {
                        const lbLink = meta.letterboxdUrl || `https://letterboxd.com/search/${encodeURIComponent(cleanTitle)}/`;
                        pillsHTML += `
                            <a href="${lbLink}" target="_blank" rel="noopener noreferrer" class="rating-pill-source rating-pill-letterboxd" title="View on Letterboxd">
                                <i class="fa-solid fa-film"></i> Letterboxd: ${meta.letterboxd}/5
                            </a>
                        `;
                    }

                    // Metacritic
                    if (meta.metascore) {
                        const mcLink = meta.metacriticUrl || `https://www.metacritic.com/search/${encodeURIComponent(cleanTitle)}/`;
                        const mcClean = meta.metascore.replace("/100", "");
                        pillsHTML += `
                            <a href="${mcLink}" target="_blank" rel="noopener noreferrer" class="rating-pill-source rating-pill-metacritic" title="View on Metacritic">
                                Ⓜ️ Metascore: ${mcClean}
                            </a>
                        `;
                    }

                    ratingsSlot.innerHTML = pillsHTML;
                }

                // Plot overview update
                if (meta.plot && meta.plot !== "N/A") {
                    const plotEl = document.getElementById("modalPlot");
                    if (plotEl) plotEl.textContent = meta.plot;
                }

                // Director, Cast & Runtime
                const creditsEl = document.getElementById("modalCredits");
                if (creditsEl) {
                    let creditsHTML = "";
                    if (meta.director && meta.director !== "N/A") creditsHTML += `<div><strong>Director:</strong> ${meta.director}</div>`;
                    if (meta.actors && meta.actors !== "N/A") creditsHTML += `<div><strong>Cast:</strong> ${meta.actors}</div>`;
                    if (meta.runtime && meta.runtime !== "N/A") creditsHTML += `<div><strong>Runtime:</strong> ${meta.runtime}</div>`;
                    creditsEl.innerHTML = creditsHTML;
                }

                // Official YouTube Trailer
                const trailerContainer = document.getElementById("modalTrailerContainer");
                if (trailerContainer) {
                    if (meta.trailer && meta.trailer.embedUrl) {
                        trailerContainer.innerHTML = `
                            <div class="trailer-iframe-wrapper">
                                <iframe 
                                    src="${meta.trailer.embedUrl}" 
                                    title="${meta.trailer.title || cleanTitle + ' Official Trailer'}" 
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                                    referrerpolicy="strict-origin-when-cross-origin" 
                                    allowfullscreen>
                                </iframe>
                            </div>
                            <div class="trailer-meta-row">
                                <span class="trailer-video-title" title="${meta.trailer.title || ''}">
                                    <i class="fa-brands fa-youtube" style="color:#ef4444; margin-right:4px;"></i> 
                                    ${meta.trailer.title || cleanTitle + ' Official Trailer'}
                                </span>
                                <a href="${meta.trailer.watchUrl || '#'}" target="_blank" rel="noopener noreferrer" class="trailer-yt-link">
                                    Watch on YouTube <i class="fa-solid fa-arrow-up-right-from-square"></i>
                                </a>
                            </div>
                        `;
                    } else if (meta.trailer && meta.trailer.watchUrl) {
                        trailerContainer.innerHTML = `
                            <div style="padding: 0.5rem 0;">
                                <a href="${meta.trailer.watchUrl}" target="_blank" rel="noopener noreferrer" class="trailer-search-pill">
                                    <i class="fa-brands fa-youtube" style="color:#ef4444; font-size:1.1rem;"></i>
                                    <span>Watch official trailers for "${cleanTitle}" on YouTube</span>
                                    <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i>
                                </a>
                            </div>
                        `;
                    } else {
                        const trailerSection = document.getElementById("modalTrailerSection");
                        if (trailerSection) trailerSection.style.display = "none";
                    }
                }
            })
            .catch(err => {
                console.error("Meta fetch error:", err);
            });

        // 2. Fetch live Streaming Availability in parallel (Where to Watch)
        fetch(`/api/movie/streaming?${queryParams.toString()}`)
            .then(res => res.ok ? res.json() : [])
            .then(streaming => {
                const streamGrid = document.getElementById("modalStreamingGrid");
                if (streamGrid) {
                    if (streaming && streaming.length > 0) {
                        streamGrid.innerHTML = streaming.map(s => {
                            const typeLabel = s.type === "subscription" ? "Stream" : s.type;
                            const logoHTML = s.logo 
                                ? `<img src="${s.logo}" class="streaming-service-logo" alt="${s.service}">`
                                : `<i class="fa-solid fa-play" style="font-size:0.75rem; color:var(--accent-violet);"></i>`;
                            const priceHTML = s.price ? `<span style="font-size:0.72rem; color:var(--text-muted); font-weight:700;">${s.price}</span>` : "";
                            return `
                                <a href="${s.link}" target="_blank" rel="noopener noreferrer" class="streaming-pill-link" title="Watch on ${s.service}">
                                    ${logoHTML}
                                    <span>${s.service}</span>
                                    <span class="streaming-type-tag">${typeLabel}</span>
                                    ${priceHTML}
                                    <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.65rem; opacity:0.6;"></i>
                                </a>
                            `;
                        }).join("");
                    } else {
                        streamGrid.innerHTML = `
                            <div style="font-size:0.82rem; color:var(--text-muted);">
                                <i class="fa-solid fa-circle-info"></i> No active streaming providers detected in US region.
                            </div>
                        `;
                    }
                }
            })
            .catch(err => {
                console.error("Streaming fetch error:", err);
                const streamGrid = document.getElementById("modalStreamingGrid");
                if (streamGrid) {
                    streamGrid.innerHTML = `
                        <div style="font-size:0.82rem; color:var(--text-muted);">
                            <i class="fa-solid fa-circle-info"></i> Streaming availability search currently unavailable.
                        </div>
                    `;
                }
            });
    }

    function closeModal() {
        if (!movieModal) return;
        // Stop any active YouTube iframe video playback
        const iframe = movieModal.querySelector("iframe");
        if (iframe) {
            iframe.src = "";
        }
        movieModal.classList.add("hidden");
    }

    // ==========================================================================
    // AMBIENT PARTICLES SYSTEM (Soft floating sparkles on outer gradient)
    // ==========================================================================

    function initAmbientParticles() {
        const canvas = document.getElementById("particles-canvas");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        
        let particles = [];
        const maxParticles = 40;

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }

        window.addEventListener("resize", resizeCanvas);
        resizeCanvas();

        class SparkleParticle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2.5 + 0.8;
                this.speedX = (Math.random() - 0.5) * 0.3;
                this.speedY = (Math.random() - 0.5) * 0.3;
                this.alpha = Math.random() * 0.5 + 0.2;
                this.pulseSpeed = Math.random() * 0.02 + 0.005;
            }

            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                if (this.x < 0) this.x = canvas.width;
                if (this.x > canvas.width) this.x = 0;
                if (this.y < 0) this.y = canvas.height;
                if (this.y > canvas.height) this.y = 0;

                this.alpha += this.pulseSpeed;
                if (this.alpha > 0.8 || this.alpha < 0.15) {
                    this.pulseSpeed = -this.pulseSpeed;
                }
            }

            draw() {
                ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        for (let i = 0; i < maxParticles; i++) {
            particles.push(new SparkleParticle());
        }

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.update();
                p.draw();
            });
            requestAnimationFrame(animate);
        }

        animate();
    }

    // ==========================================================================
    // NAVBAR SCROLL & ACTIVE LINK TRACKER
    // ==========================================================================

    function initNavbarScroll() {
        const sections = document.querySelectorAll("section");
        const navLinks = document.querySelectorAll(".nav-link");

        window.addEventListener("scroll", () => {
            let currentSec = "";
            sections.forEach(sec => {
                const secTop = sec.offsetTop;
                if (window.scrollY >= secTop - 180) {
                    currentSec = sec.getAttribute("id");
                }
            });

            navLinks.forEach(link => {
                link.classList.remove("active");
                if (link.getAttribute("href").substring(1) === currentSec) {
                    link.classList.add("active");
                }
            });
        });
    }

    function showQuickNotification(msg) {
        const toast = document.createElement("div");
        toast.style.position = "fixed";
        toast.style.bottom = "24px";
        toast.style.right = "24px";
        toast.style.background = "#0f172a";
        toast.style.color = "#ffffff";
        toast.style.padding = "0.75rem 1.4rem";
        toast.style.borderRadius = "9999px";
        toast.style.fontSize = "0.85rem";
        toast.style.fontWeight = "600";
        toast.style.boxShadow = "0 10px 25px rgba(0,0,0,0.3)";
        toast.style.zIndex = "3000";
        toast.style.transition = "all 0.3s ease";
        toast.textContent = msg;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
});
