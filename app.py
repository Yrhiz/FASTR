"""
app.py - FASTR web application (Flask).

    python app.py          then open http://127.0.0.1:5000 in a browser

Set the environment variable FASTR_ONLINE=0 to turn off the online place lookup.
"""
import os

from flask import Flask, jsonify, render_template, request

from config import APP_CRITERIA, APP_WEIGHTS, SEASONS
from places import PlaceError, load_places, suggested_places
from service import recommend_trip
from trip import hour_label

app = Flask(__name__)
ONLINE = os.environ.get("FASTR_ONLINE", "1") == "1"

DEFAULT_FORM = {"origin": "", "destination": "", "hour": "8", "budget": "50", "no_budget": "",
                "max_wait": "", "season": "regular", "w": [str(round(w * 100)) for w in APP_WEIGHTS]}


def _number(text, name):
    """Parse an optional number from the form; empty text means 'not set'."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{name} must be a number.")


@app.route("/", methods=["GET", "POST"])
def index():
    form, result, error = dict(DEFAULT_FORM), None, None
    if request.method == "POST":
        form = {"origin": request.form.get("origin", ""), "destination": request.form.get("destination", ""),
                "hour": request.form.get("hour", "8"), "budget": request.form.get("budget", ""),
                "no_budget": request.form.get("no_budget", ""), "max_wait": request.form.get("max_wait", ""),
                "season": request.form.get("season", "regular"),
                "w": [request.form.get(f"w{i}", "0") for i in range(4)]}
        try:
            budget = None if form["no_budget"] else _number(form["budget"], "Budget")
            result = recommend_trip(
                form["origin"], form["destination"], int(form["hour"]), budget,
                _number(form["max_wait"], "Maximum waiting time"),
                [float(x) for x in form["w"]], online=ONLINE, season=form["season"])
        except (PlaceError, ValueError) as exc:
            error = str(exc)
    return render_template("index.html", form=form, result=result, error=error,
                           places=suggested_places(load_places()), criteria=APP_CRITERIA, seasons=SEASONS,
                           hours=[(h, hour_label(h)) for h in range(24)], online=ONLINE)


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    """JSON version: {"origin","destination","hour","budget","max_wait","weights":[4 numbers]}."""
    data = request.get_json(force=True, silent=True) or {}
    try:
        result = recommend_trip(data.get("origin", ""), data.get("destination", ""), int(data.get("hour", 8)),
                                data.get("budget"), data.get("max_wait"), data.get("weights"), online=ONLINE,
                                season=data.get("season", "regular"))
    except (PlaceError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
