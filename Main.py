import pandas as pd
import re
import unicodedata
from rapidfuzz import fuzz

# ------------------ CONFIGURATION ------------------
FILE_A = 'playlist_a.csv'   # Change to your actual CSV filename
FILE_B = 'playlist_b.csv'
THRESHOLD = 90              # Adjust between 0 and 100 (90 is recommended)
# ----------------------------------------------------

def normalize_text(text):
    """
    Normalize text: lowercase, remove accents, common version terms, and punctuation.
    """
    # Remove accents and convert to lowercase
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = text.lower()

    # List of terms that do not define the song and should be ignored
    terms_to_remove = [
        'remastered', 'remaster', 'single version', 'album version',
        'live', 'deluxe edition', 'radio edit', 'feat.', 'ft.',
        'feat', 'ft',  # in case they appear without period
        'bonus track', 'demo', 'acoustic', 'instrumental', 'soundtrack', 'from', 'the'
    ]
    # Join terms into a regex pattern, escaping dots to avoid wildcard behavior
    pattern_terms = '|'.join(re.escape(t) for t in terms_to_remove)

    # Remove constructions like " - Remastered" (with optional spaces around hyphen)
    text = re.sub(r'\s*-\s*(?:' + pattern_terms + r')\b', '', text)
    # Remove standalone terms (e.g., "Remastered" without hyphen)
    text = re.sub(r'\b(?:' + pattern_terms + r')\b', '', text)

    # Remove punctuation and special characters (including residual hyphens)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_title(title):
    """Normalize a song title."""
    return normalize_text(title)

def normalize_artists(artists):
    """
    Normalize artist names: sort them alphabetically, then normalize.
    """
    if isinstance(artists, str):
        artist_list = sorted([a.strip() for a in artists.split(',')])
        combined = ' '.join(artist_list)
        return normalize_text(combined)
    else:
        return normalize_text('')

def load_csv(path):
    """
    Load CSV exported from Exportify and return a list of tuples (title, artists).
    """
    df = pd.read_csv(path)
    # Ensure required columns exist
    if 'Track Name' not in df.columns or 'Artist Name(s)' not in df.columns:
        raise ValueError(f"The file {path} does not have columns 'Track Name' and 'Artist Name(s)'")
    # Create list of tuples (title, artists)
    tracks = list(zip(df['Track Name'].astype(str), df['Artist Name(s)'].astype(str)))
    # Remove exact duplicates (same song added multiple times)
    tracks = list(set(tracks))
    return tracks

def fuzzy_match(tracks_a, tracks_b, threshold=90):
    """
    Compare tracks from A against B, giving double weight to title similarity.
    Returns a list of matches with combined score, sorted from highest to lowest similarity.
    """
    # Pre-normalize B (title and artist separately)
    norm_b = [
        (normalize_title(title), normalize_artists(artists), (title, artists))
        for title, artists in tracks_b
    ]

    matches = []
    for title_a, artists_a in tracks_a:
        norm_title_a = normalize_title(title_a)
        norm_artists_a = normalize_artists(artists_a)

        best_score = 0
        best_match = None

        for norm_title_b, norm_artists_b, original_b in norm_b:
            # Compute separate similarity scores
            title_score = fuzz.token_set_ratio(norm_title_a, norm_title_b)
            artist_score = fuzz.token_set_ratio(norm_artists_a, norm_artists_b)

            # Weighted combination: title twice as important as artist
            combined_score = (2 * title_score + artist_score) / 3

            if combined_score > best_score:
                best_score = combined_score
                best_match = original_b

        if best_score >= threshold:
            matches.append({
                'Title_A': title_a,
                'Artist_A': artists_a,
                'Title_B': best_match[0],
                'Artist_B': best_match[1],
                'Similarity': round(best_score, 2)  # rounded for cleaner output
            })

    # Sort matches by similarity descending
    matches.sort(key=lambda x: x['Similarity'], reverse=True)
    return matches

# --- MAIN PROGRAM ---
print("Loading playlist A...")
tracks_a = load_csv(FILE_A)
print(f"Playlist A: {len(tracks_a)} songs (after removing exact duplicates)")

print("Loading playlist B...")
tracks_b = load_csv(FILE_B)
print(f"Playlist B: {len(tracks_b)} songs (after removing exact duplicates)")

print(f"Comparing with threshold {THRESHOLD}...")
matches = fuzzy_match(tracks_a, tracks_b, threshold=THRESHOLD)

print(f"\nFound {len(matches)} songs from A that are in B (similarity >= {THRESHOLD}%).")

if matches:
    df_result = pd.DataFrame(matches)
    df_result.to_csv('matches.csv', index=False, encoding='utf-8-sig')
    print("Results saved to 'matches.csv' (sorted by similarity descending)")
else:
    print("No matches found with that threshold.")