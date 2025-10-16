from datetime import date

from flask import Flask, render_template

app = Flask(__name__)

FEATURED_VLOGS = [
    {
        "title": "Moonlit Streets of Paris",
        "slug": "moonlit-paris",
        "thumbnail": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80",
        "duration": "08:42",
        "description": "A midnight escapade through the hidden courtyards, haute couture ateliers, and patisseries that never sleep.",
    },
    {
        "title": "Velvet Evenings in Kyoto",
        "slug": "velvet-kyoto",
        "thumbnail": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=1200&q=80",
        "duration": "12:18",
        "description": "Cherry blossoms, tatami sunsets, and a private tea ceremony curated for the modern wanderer.",
    },
    {
        "title": "Santorini Gold Hour",
        "slug": "santorini-gold-hour",
        "thumbnail": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
        "duration": "09:57",
        "description": "Sailing the caldera, champagne skies, and the island’s most exclusive terraces at twilight.",
    },
]

@app.route("/")
def index():
    return render_template("home.html", vlogs=FEATURED_VLOGS)

@app.route("/about")
def about():
    return render_template("about.html")


@app.context_processor
def inject_globals():
    return {"current_year": date.today().year}


if __name__ == "__main__":
    app.run()
