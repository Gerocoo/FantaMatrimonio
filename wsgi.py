from app import app, db
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()