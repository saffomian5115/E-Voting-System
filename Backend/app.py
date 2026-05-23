from flask import Flask
from flask_cors import CORS
from routes.auth import auth
from routes.vote import vote
from routes.result import result
from routes.admin import admin

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth)
app.register_blueprint(vote)
app.register_blueprint(result)
app.register_blueprint(admin)
@app.route("/")
def home():
    return {"message": "E-Voting Backend Running 🔥"}

if __name__ == "__main__":
    app.run(debug=True)
