from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import os
from core.utils import parse_resume, save_recommendations
from core.user_input import create_user_profile
from core.recommendation_system import CareerRecommendationSystem

# Initialize extensions globally (but unattached)
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, 
                static_folder='static', 
                template_folder='templates')

    app.secret_key = 'super_secret_key_change_this_in_production'

    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register Blueprints
    # (Wrapping imports inside the function prevents circular dependency errors)
    try:
        from app.blueprints.auth.routes import auth as auth_bp
        app.register_blueprint(auth_bp)
    except ImportError:
        pass # Handle gracefully if blueprint doesn't exist yet

    try:
        from app.blueprints.main.routes import main as main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass

    # --- DEFINING ROUTES INSIDE FACTORY OR IMPORTING THEM ---
    # ideally these should be in a blueprint, but for now we keep them here
    # to preserve existing functionality without breaking everything.
    
    register_routes(app)

    return app

def register_routes(app):
    # Initialize the system specifically for these routes
    # You can load the API key from env here safely
    API_KEY = "PLACEHOLDER_KEY_FOR_NOW" 
    system = CareerRecommendationSystem(API_KEY)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/upload_resume', methods=['POST'])
    def upload_resume():
        if 'resume' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file:
            try:
                data = parse_resume(file, file.filename)
                return jsonify(data)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Unknown error'}), 500

    @app.route('/submit', methods=['POST'])
    def submit():
        try:
            user_profile = create_user_profile(request.form)
            
            # These will fail without a real key, but the app structure is fixed
            career_recommendations = system.generate_career_recommendations(user_profile)
            college_recommendations = system.generate_college_recommendations(user_profile, career_recommendations)
            roadmap = system.generate_roadmap(user_profile, career_recommendations)

            if request.form.get('save'):
                save_recommendations(user_profile, career_recommendations, college_recommendations, roadmap)

            return render_template(
                'results.html',
                user_profile=user_profile,
                career_recommendations=career_recommendations,
                college_recommendations=college_recommendations,
                roadmap=roadmap
            )
        except Exception as e:
            return render_template("index.html", error=f"Error processing request: {str(e)}")

# User loader must be outside create_app or registered properly
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)