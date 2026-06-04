import whoosh.index as windex
from flask import Flask, render_template, request
from whoosh.qparser import QueryParser

app = Flask(__name__)
ix = windex.open_dir("index")
qp = QueryParser("snippet", schema=ix.schema)
searcher = ix.searcher()


def query(query_str):
    q = qp.parse(query_str)
    return searcher.search(q)


@app.route("/script.js")
def script():
    return render_template("script.js")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q")
    results = query(q)
    print(f"query '{q}' returned results ...")
    for r in results:
        print(f"result: {r}")
    return render_template("search.html", results=results, query=q)
