import requests
import ssl
from flask import Flask, request

app = Flask(__name__)
app.config["DEBUG"] = True


@app.route("/proxy")
def proxy():
    url = request.args.get("url", "https://example.com")
    response = requests.get(url, timeout=5, verify=False)
    return response.text


def insecure_context():
    context = ssl._create_unverified_context()
    return context


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
