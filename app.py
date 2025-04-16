# app.py - Main Flask Application

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change this to a secure secret key

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/hackathon_db'
mongo = PyMongo(app)

# Database collections
users = mongo.db.users
hackathons = mongo.db.hackathons
teams = mongo.db.teams
projects = mongo.db.projects
submissions = mongo.db.submissions
judges = mongo.db.judges
evaluations = mongo.db.evaluations
notifications = mongo.db.notifications
rounds = mongo.db.rounds

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    # Get upcoming hackathons for the homepage
    upcoming = list(hackathons.find({
        'start_date': {'$gte': datetime.now()}
    }).sort('start_date', 1).limit(3))
    
    # Get real-time statistics
    total_hackathons = hackathons.count_documents({})
    
    # Count active participants (users with role 'participant')
    total_participants = users.count_documents({'role': 'participant'})
    
    # Count total projects
    total_projects = projects.count_documents({})
    
    # Count ongoing hackathons
    current_time = datetime.now()
    ongoing_hackathons = hackathons.count_documents({
        'start_date': {'$lte': current_time},
        'end_date': {'$gte': current_time}
    })
    
    return render_template('index.html', 
                          upcoming_hackathons=upcoming,
                          total_hackathons=total_hackathons,
                          total_participants=total_participants,
                          total_projects=total_projects,
                          ongoing_hackathons=ongoing_hackathons)

# User Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user_type = request.form.get('user_type', 'participant')
            
            if not all([email, password]):
                flash('Email and password are required.', 'danger')
                return redirect(url_for('login'))
            
            user = users.find_one({'email': email})
            print(f"Login attempt for email: {email}")
            
            if user and check_password_hash(user['password'], password):
                # Check if user type matches
                if user['role'] != user_type:
                    flash(f'This account is registered as a {user["role"]}, not as a {user_type}.', 'warning')
                    return redirect(url_for('login'))
                
                session['user_id'] = str(user['_id'])
                session['user_email'] = user['email']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                print(f"Login failed for email: {email}")
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('login'))
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    user_type = request.args.get('user_type', 'participant')
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user_type = request.form.get('user_type', 'participant')
            
            # Validate required fields
            if not all([name, email, password]):
                flash('All fields are required.', 'danger')
                return redirect(url_for('register'))
            
            # Check if email already exists
            existing_user = users.find_one({'email': email})
            if existing_user:
                flash('Email already registered. Please login or use a different email.', 'warning')
                return redirect(url_for('register'))
            
            # Create new user document based on user type
            new_user = {
                'name': name,
                'email': email,
                'password': generate_password_hash(password),
                'role': user_type,
                'created_at': datetime.now()
            }
            
            # Add user type specific fields
            if user_type == 'participant':
                skills_input = request.form.get('skills', '').strip()
                skills = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
                new_user['skills'] = skills
            elif user_type == 'organizer':
                organization = request.form.get('organization', '').strip()
                bio = request.form.get('bio', '').strip()
                new_user['organization'] = organization
                new_user['bio'] = bio
                new_user['verified'] = False  # Organizers need verification
            
            # Insert the new user
            result = users.insert_one(new_user)
            user_id = result.inserted_id
            
            # Create welcome notification
            try:
                notifications.insert_one({
                    'user_id': user_id,
                    'title': 'Welcome to HackHub!',
                    'message': f'Welcome {name}! Thanks for joining our platform.',
                    'type': 'welcome',
                    'read': False,
                    'created_at': datetime.now()
                })
            except Exception as e:
                print(f"Notification creation error: {str(e)}")
                # Don't redirect here, continue with registration success
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html', user_type=user_type)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Dashboard Routes
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    
    try:
        user_id = ObjectId(session['user_id'])
        user = users.find_one({'_id': user_id})
        
        if not user:
            session.clear()
            flash('User not found. Please login again.', 'danger')
            return redirect(url_for('login'))
        
        # Get user's notifications
        user_notifications = list(notifications.find({
            'user_id': user_id,
            'read': False
        }).sort('created_at', -1))
        
        # Get role-specific data
        if user['role'] == 'organizer':
            # Get organizer's hackathons
            organizer_hackathons = list(hackathons.find({
                'organizer_id': user_id
            }).sort('created_at', -1))
            
            # Calculate participant count for each hackathon
            for hackathon in organizer_hackathons:
                # Find all teams for this hackathon
                hackathon_teams = list(teams.find({'hackathon_id': hackathon['_id']}))
                
                # Count total participants across all teams in this hackathon
                participant_count = 0
                for team in hackathon_teams:
                    participant_count += len(team.get('members', []))
                
                # Add participant count to the hackathon object
                hackathon['participant_count'] = participant_count
            
            # Calculate total participants across all hackathons
            total_participants = sum(hackathon.get('participant_count', 0) for hackathon in organizer_hackathons)
            
            return render_template('dashboard.html', 
                                 user=user, 
                                 notifications=user_notifications,
                                 hackathons=organizer_hackathons,
                                 total_participants=total_participants)
        else:
            # Get participant's teams
            participant_teams = list(teams.find({
                'members': user_id
            }))
            
            # Get hackathons the participant is registered for
            participant_hackathon_ids = [team['hackathon_id'] for team in participant_teams]
            participant_hackathons = list(hackathons.find({
                '_id': {'$in': participant_hackathon_ids}
            }))
            
            # Get participant's projects
            team_ids = [team['_id'] for team in participant_teams]
            participant_projects = list(projects.find({
                'team_id': {'$in': team_ids}
            }))
            
            return render_template('dashboard.html', 
                                 user=user, 
                                 notifications=user_notifications,
                                 teams=participant_teams,
                                 hackathons=participant_hackathons,
                                 projects=participant_projects)
                             
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('login'))

# User Profile Routes
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = ObjectId(session['user_id'])
    user = users.find_one({'_id': user_id})
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Common fields for all user types
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            
            # Validate required fields
            if not all([name, email]):
                flash('Name and email are required fields.', 'danger')
                return redirect(url_for('edit_profile'))
            
            # Check if email is changed and already exists
            if email != user['email']:
                existing_user = users.find_one({'email': email, '_id': {'$ne': user_id}})
                if existing_user:
                    flash('Email already in use by another account.', 'danger')
                    return redirect(url_for('edit_profile'))
            
            # Prepare update data
            update_data = {
                'name': name,
                'email': email,
                'updated_at': datetime.now()
            }
            
            # Handle user type specific fields
            if user['role'] == 'participant':
                skills_input = request.form.get('skills', '').strip()
                skills = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
                update_data['skills'] = skills
                
                # Optional fields
                bio = request.form.get('bio', '').strip()
                github = request.form.get('github', '').strip()
                linkedin = request.form.get('linkedin', '').strip()
                
                if bio:
                    update_data['bio'] = bio
                if github:
                    update_data['github'] = github
                if linkedin:
                    update_data['linkedin'] = linkedin
                    
            elif user['role'] == 'organizer':
                organization = request.form.get('organization', '').strip()
                bio = request.form.get('bio', '').strip()
                
                if not organization:
                    flash('Organization name is required for organizers.', 'danger')
                    return redirect(url_for('edit_profile'))
                
                update_data['organization'] = organization
                update_data['bio'] = bio
                
                # Optional fields
                website = request.form.get('website', '').strip()
                if website:
                    update_data['website'] = website
            
            # Update password if provided
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if current_password and new_password:
                if not check_password_hash(user['password'], current_password):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('edit_profile'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return redirect(url_for('edit_profile'))
                
                update_data['password'] = generate_password_hash(new_password)
            
            # Handle profile image upload
            if 'profile_image' in request.files and request.files['profile_image'].filename:
                profile_image = request.files['profile_image']
                if profile_image and allowed_file(profile_image.filename, ['jpg', 'jpeg', 'png']):
                    filename = secure_filename(profile_image.filename)
                    unique_filename = f"profile_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    profile_image.save(file_path)
                    update_data['profile_image'] = unique_filename
            
            # Update user in database
            users.update_one({'_id': user_id}, {'$set': update_data})
            
            # Update session data
            session['user_name'] = name
            session['user_email'] = email
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Profile update error: {str(e)}")
            flash('An error occurred while updating your profile.', 'danger')
            return redirect(url_for('edit_profile'))
    
    return render_template('edit_profile.html', user=user)

# Hackathon Routes
@app.route('/list_hackathons')
def list_hackathons():
    # Redirect organizers to their hackathons page
    if 'user_role' in session and session['user_role'] == 'organizer':
        flash('As an organizer, you can manage your hackathons from your dedicated page.', 'info')
        return redirect(url_for('my_hackathons'))
        
    try:
        print("Fetching hackathons...")
        current_time = datetime.now()
        
        # Get ongoing hackathons
        ongoing_hackathons = list(mongo.db.hackathons.find({
            'start_date': {'$lte': current_time},
            'end_date': {'$gte': current_time}
        }))
        print(f"Found {len(ongoing_hackathons)} ongoing hackathons")
        
        # Get upcoming hackathons
        upcoming_hackathons = list(mongo.db.hackathons.find({
            'start_date': {'$gt': current_time}
        }))
        print(f"Found {len(upcoming_hackathons)} upcoming hackathons")
        
        # Get past hackathons
        past_hackathons = list(mongo.db.hackathons.find({
            'end_date': {'$lt': current_time}
        }))
        print(f"Found {len(past_hackathons)} past hackathons")
        
        # Ensure all hackathons have required fields
        for hackathon in ongoing_hackathons + upcoming_hackathons + past_hackathons:
            if '_id' not in hackathon:
                print(f"Warning: Hackathon missing _id: {hackathon}")
                continue
                
            # Convert string dates to datetime if needed
            if isinstance(hackathon.get('start_date'), str):
                try:
                    hackathon['start_date'] = datetime.strptime(hackathon['start_date'], '%Y-%m-%dT%H:%M:%S')
                except:
                    print(f"Error parsing start_date for hackathon {hackathon['_id']}")
                    
            if isinstance(hackathon.get('end_date'), str):
                try:
                    hackathon['end_date'] = datetime.strptime(hackathon['end_date'], '%Y-%m-%dT%H:%M:%S')
                except:
                    print(f"Error parsing end_date for hackathon {hackathon['_id']}")
        
        return render_template('hackathons.html',
                             ongoing_hackathons=ongoing_hackathons,
                             upcoming_hackathons=upcoming_hackathons,
                             past_hackathons=past_hackathons)
                             
    except Exception as e:
        print(f"Error listing hackathons: {str(e)}")
        flash('An error occurred while loading hackathons.', 'danger')
        return render_template('hackathons.html',
                             ongoing_hackathons=[],
                             upcoming_hackathons=[],
                             past_hackathons=[])

@app.route('/hackathons/create', methods=['GET', 'POST'])
def create_hackathon():
    if 'user_id' not in session or session['user_role'] not in ['admin', 'organizer']:
        flash('You must be an organizer to create hackathons', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Process form data
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            
            # Create new hackathon document
            new_hackathon = {
                'title': request.form['title'],
                'description': request.form['description'],
                'start_date': start_date,
                'end_date': end_date,
                'location': request.form['location'],
                'max_team_size': int(request.form['max_team_size']),
                'organizer_id': ObjectId(session['user_id']),
                'organizer_name': session['user_name'],
                'status': 'upcoming',
                'created_at': datetime.now(),
                'judges': [],
                'sponsors': [],
                'prizes': request.form.get('prizes', ''),
                'rules': request.form.get('rules', ''),
                'themes': [theme.strip() for theme in request.form.get('themes', '').split(',') if theme.strip()],
                'is_featured': 'is_featured' in request.form,
                'hackathon_type': request.form.get('hackathon_type', 'detailed')
            }
            
            # Process hackathon type-specific data
            if new_hackathon['hackathon_type'] == 'detailed':
                # Process detailed problem statements
                problem_count = int(request.form.get('problem_count', 1))
                problem_titles = request.form.getlist('problem_titles[]')
                problem_descriptions = request.form.getlist('problem_descriptions[]')
                problem_requirements = request.form.getlist('problem_requirements[]')
                problem_constraints = request.form.getlist('problem_constraints[]')
                
                problems = []
                for i in range(min(problem_count, len(problem_titles))):
                    # Handle empty problem_requirements and problem_constraints safely
                    req_list = []
                    if i < len(problem_requirements) and problem_requirements[i]:
                        req_list = [req.strip() for req in problem_requirements[i].split(',') if req.strip()]
                    
                    con_list = []
                    if i < len(problem_constraints) and problem_constraints[i]:
                        con_list = [con.strip() for con in problem_constraints[i].split(',') if con.strip()]
                    
                    problem = {
                        'problem_number': i + 1,
                        'title': problem_titles[i] if i < len(problem_titles) else f"Problem {i+1}",
                        'description': problem_descriptions[i] if i < len(problem_descriptions) else '',
                        'requirements': req_list,
                        'constraints': con_list,
                        'created_at': datetime.now()
                    }
                    problems.append(problem)
                
                new_hackathon['problems'] = problems
            else:  # open selection
                # Process open selection themes and criteria
                open_themes = request.form.get('open_themes', '')
                new_hackathon['open_themes'] = [theme.strip() for theme in open_themes.split(',') if theme.strip()]
                new_hackathon['selection_criteria'] = request.form.get('selection_criteria', '')
                new_hackathon['submission_requirements'] = request.form.get('submission_requirements', '')
            
            # Process hackathon levels
            level_count = int(request.form.get('level_count', 1))
            level_names = request.form.getlist('level_names[]')
            level_types = request.form.getlist('level_types[]')
            level_descriptions = request.form.getlist('level_descriptions[]')
            
            levels = []
            for i in range(min(level_count, len(level_names))):
                level = {
                    'level_number': i + 1,
                    'name': level_names[i] if i < len(level_names) else f"Level {i+1}",
                    'type': level_types[i] if i < len(level_types) else 'submission',
                    'description': level_descriptions[i] if i < len(level_descriptions) else '',
                    'status': 'pending' if i > 0 else 'active',  # First level is active by default
                    'start_date': start_date,  # Default to hackathon start date, can be updated later
                    'end_date': None,  # To be determined later
                    'teams_advanced': 0,  # Number of teams that advanced from this level
                    'submissions_count': 0,  # Number of submissions for this level
                    'created_at': datetime.now()
                }
                levels.append(level)
            
            new_hackathon['levels'] = levels
            
            # Handle banner image upload
            if 'banner_image' in request.files and request.files['banner_image'].filename:
                banner_image = request.files['banner_image']
                if banner_image and allowed_file(banner_image.filename, ['jpg', 'jpeg', 'png']):
                    filename = secure_filename(banner_image.filename)
                    # Create a unique filename
                    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    banner_image.save(file_path)
                    new_hackathon['banner_image'] = unique_filename
            
            # Insert the new hackathon
            hackathon_id = mongo.db.hackathons.insert_one(new_hackathon).inserted_id
            
            # Create notification for the organizer
            mongo.db.notifications.insert_one({
                'user_id': ObjectId(session['user_id']),
                'title': 'Hackathon Created',
                'message': f"You've successfully created '{new_hackathon['title']}' with {level_count} levels. Start inviting participants!",
                'type': 'success',
                'read': False,
                'created_at': datetime.now()
            })
            
            flash('Hackathon created successfully!', 'success')
            return redirect(url_for('hackathon_detail', hackathon_id=str(hackathon_id)))
            
        except Exception as e:
            import traceback
            print(f"Hackathon creation error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            flash('An error occurred during hackathon creation. Please try again.', 'danger')
            return redirect(url_for('create_hackathon'))
    
    return render_template('create_hackathon.html')

@app.route('/hackathons/<hackathon_id>')
def hackathon_detail(hackathon_id):
    try:
        # Validate hackathon_id format
        if not ObjectId.is_valid(hackathon_id):
            print(f"Invalid hackathon ID format: {hackathon_id}")
            flash('Invalid hackathon ID.', 'danger')
            return redirect(url_for('list_hackathons'))
            
        hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
        
        if not hackathon:
            flash('Hackathon not found', 'danger')
            return redirect(url_for('list_hackathons'))
        
        hackathon_teams = list(teams.find({'hackathon_id': ObjectId(hackathon_id)}))
        judge_ids = hackathon.get('judges', [])
        hackathon_judges = list(users.find({'_id': {'$in': judge_ids}}))
        
        # Calculate total participants
        total_participants = 0
        for team in hackathon_teams:
            total_participants += len(team.get('members', []))
        
        # Update hackathon status based on current time
        current_time = datetime.now()
        
        # Ensure dates are in datetime format
        if isinstance(hackathon.get('start_date'), str):
            try:
                hackathon['start_date'] = datetime.strptime(hackathon['start_date'], '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                print(f"Error parsing start_date: {str(e)}")
                hackathon['start_date'] = current_time
                
        if isinstance(hackathon.get('end_date'), str):
            try:
                hackathon['end_date'] = datetime.strptime(hackathon['end_date'], '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                print(f"Error parsing end_date: {str(e)}")
                hackathon['end_date'] = current_time
        
        if current_time < hackathon['start_date']:
            hackathon['status'] = 'upcoming'
        elif current_time > hackathon['end_date']:
            hackathon['status'] = 'completed'
        else:
            hackathon['status'] = 'ongoing'
        
        # Check if the current user is registered for this hackathon
        is_registered = False
        if 'user_id' in session:
            # Check if user is part of any team in this hackathon
            user_team = mongo.db.teams.find_one({
                'hackathon_id': ObjectId(hackathon_id),
                'members': ObjectId(session['user_id'])
            })
            is_registered = user_team is not None
            print(f"User is registered: {is_registered}")
        
        # Get team members for each team (for organizers to view)
        team_members = {}
        if hackathon_teams and (session.get('user_role') == 'organizer' or session.get('user_role') == 'admin'):
            for team in hackathon_teams:
                if 'members' in team:
                    member_ids = [ObjectId(member_id) for member_id in team['members']]
                    members = list(mongo.db.users.find({'_id': {'$in': member_ids}}, 
                                                    {'name': 1, 'email': 1, 'profile_image': 1}))
                    team_members[str(team['_id'])] = members
        
        return render_template('view_hackathon.html', 
                            hackathon=hackathon, 
                            teams=hackathon_teams,
                            judges=hackathon_judges,
                            total_participants=total_participants,
                            is_registered=is_registered,
                            team_members=team_members)
    except Exception as e:
        print(f"Error viewing hackathon detail: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('An error occurred while loading the hackathon details.', 'danger')
        return redirect(url_for('list_hackathons'))

@app.route('/hackathons/<hackathon_id>/edit', methods=['GET', 'POST'])
def edit_hackathon(hackathon_id):
    if 'user_id' not in session or session['user_role'] not in ['admin', 'organizer']:
        flash('You must be an admin or organizer to edit hackathons', 'danger')
        return redirect(url_for('index'))
    
    hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
    
    if not hackathon:
        flash('Hackathon not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    if str(hackathon['organizer_id']) != session['user_id']:
        flash('You can only edit hackathons you organize', 'danger')
        return redirect(url_for('hackathon_detail', hackathon_id=hackathon_id))
    
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        
        try:
            hackathons.update_one(
                {'_id': ObjectId(hackathon_id)},
                {'$set': {
                    'title': request.form['title'],
                    'description': request.form['description'],
                    'start_date': start_date,
                    'end_date': end_date,
                    'location': request.form['location'],
                    'max_team_size': int(request.form['max_team_size']),
                    'status': request.form['status'],
                    'themes': request.form['themes'].split(',') if request.form['themes'] else []
                }}
            )
            flash('Hackathon updated successfully!', 'success')
            return redirect(url_for('hackathon_detail', hackathon_id=hackathon_id))
        except Exception as e:
            flash('An error occurred during hackathon update. Please try again.', 'danger')
            print(f"Hackathon update error: {str(e)}")
            return redirect(url_for('edit_hackathon', hackathon_id=hackathon_id))
    
    return render_template('edit_hackathon.html', hackathon=hackathon)

@app.route('/hackathon/<hackathon_id>')
def view_hackathon(hackathon_id):
    try:
        print(f"Attempting to view hackathon with ID: {hackathon_id}")
        
        # Validate hackathon_id format
        if not ObjectId.is_valid(hackathon_id):
            print(f"Invalid hackathon ID format: {hackathon_id}")
            flash('Invalid hackathon ID.', 'danger')
            return redirect(url_for('list_hackathons'))
        
        # Get hackathon details
        hackathon = mongo.db.hackathons.find_one({'_id': ObjectId(hackathon_id)})
        print(f"Found hackathon: {hackathon}")
        
        if not hackathon:
            print(f"Hackathon not found with ID: {hackathon_id}")
            flash('Hackathon not found.', 'danger')
            return redirect(url_for('list_hackathons'))
        
        # Get registered teams
        teams_list = list(mongo.db.teams.find({'hackathon_id': ObjectId(hackathon_id)}))
        print(f"Found {len(teams_list)} teams")
        
        # Calculate total participants
        total_participants = sum(len(team.get('members', [])) for team in teams_list)
        print(f"Total participants: {total_participants}")
        
        # Set hackathon status based on current time
        current_time = datetime.now()
        
        # Convert string dates to datetime if needed
        if isinstance(hackathon.get('start_date'), str):
            try:
                hackathon['start_date'] = datetime.strptime(hackathon['start_date'], '%Y-%m-%dT%H:%M:%S')
            except:
                print(f"Error parsing start_date for hackathon {hackathon['_id']}")
                
        if isinstance(hackathon.get('end_date'), str):
            try:
                hackathon['end_date'] = datetime.strptime(hackathon['end_date'], '%Y-%m-%dT%H:%M:%S')
            except:
                print(f"Error parsing end_date for hackathon {hackathon['_id']}")
        
        # Set status based on dates
        if current_time < hackathon['start_date']:
            hackathon['status'] = 'upcoming'
        elif current_time > hackathon['end_date']:
            hackathon['status'] = 'completed'
        else:
            hackathon['status'] = 'ongoing'
            
        print(f"Hackathon status: {hackathon['status']}")
        
        # Check if the current user is registered for this hackathon
        is_registered = False
        if 'user_id' in session:
            # Check if user is part of any team in this hackathon
            user_team = mongo.db.teams.find_one({
                'hackathon_id': ObjectId(hackathon_id),
                'members': ObjectId(session['user_id'])
            })
            is_registered = user_team is not None
            print(f"User is registered: {is_registered}")
        
        # Get team members for each team (for organizers to view)
        team_members = {}
        if teams_list and (session.get('user_role') == 'organizer' or session.get('user_role') == 'admin'):
            for team in teams_list:
                if 'members' in team:
                    member_ids = [ObjectId(member_id) for member_id in team['members']]
                    members = list(mongo.db.users.find({'_id': {'$in': member_ids}}, 
                                                     {'name': 1, 'email': 1, 'profile_image': 1}))
                    team_members[str(team['_id'])] = members
        
        return render_template('view_hackathon.html', 
                             hackathon=hackathon, 
                             teams=teams_list,
                             total_teams=len(teams_list),
                             total_participants=total_participants,
                             is_registered=is_registered,
                             team_members=team_members)
                             
    except Exception as e:
        print(f"Error viewing hackathon: {str(e)}")
        flash('An error occurred while loading the hackathon details.', 'danger')
        return redirect(url_for('list_hackathons'))

@app.route('/hackathons/<hackathon_id>/teams/create', methods=['GET', 'POST'])
def create_team(hackathon_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
    
    if not hackathon:
        flash('Hackathon not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    # Check if user is already in a team for this hackathon
    existing_team = teams.find_one({
        'hackathon_id': ObjectId(hackathon_id),
        'members': ObjectId(session['user_id'])
    })
    
    if existing_team:
        flash('You are already in a team for this hackathon', 'warning')
        return redirect(url_for('team_detail', team_id=existing_team['_id']))
    
    if request.method == 'POST':
        new_team = {
            'name': request.form['name'],
            'description': request.form['description'],
            'hackathon_id': ObjectId(hackathon_id),
            'leader_id': ObjectId(session['user_id']),
            'members': [ObjectId(session['user_id'])],
            'created_at': datetime.now(),
            'looking_for_members': True if request.form.get('looking_for_members') else False
        }
        
        try:
            team_id = teams.insert_one(new_team).inserted_id
            
            # Create a default project for the team
            new_project = {
                'title': f"{new_team['name']}'s Project",
                'description': 'Project description here',
                'team_id': team_id,
                'hackathon_id': ObjectId(hackathon_id),
                'tech_stack': [],
                'github_link': '',
                'created_at': datetime.now(),
                'status': 'planning'
            }
            
            projects.insert_one(new_project)
            
            flash('Team created successfully!', 'success')
            return redirect(url_for('team_detail', team_id=team_id))
        except Exception as e:
            flash('An error occurred during team creation. Please try again.', 'danger')
            print(f"Team creation error: {str(e)}")
            return redirect(url_for('create_team', hackathon_id=hackathon_id))
    
    return render_template('create_team.html', hackathon=hackathon)

@app.route('/teams/<team_id>')
def team_detail(team_id):
    team = teams.find_one({'_id': ObjectId(team_id)})
    
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    hackathon = hackathons.find_one({'_id': team['hackathon_id']})
    team_members = list(users.find({'_id': {'$in': team['members']}}))
    team_project = projects.find_one({'team_id': ObjectId(team_id)})
    
    return render_template('team_detail.html', 
                          team=team, 
                          hackathon=hackathon,
                          members=team_members,
                          project=team_project)

@app.route('/teams/<team_id>/join', methods=['POST'])
def join_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    team = teams.find_one({'_id': ObjectId(team_id)})
    
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    if not team.get('looking_for_members', False):
        flash('This team is not looking for members', 'warning')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Check if user is already in a team for this hackathon
    existing_team = teams.find_one({
        'hackathon_id': team['hackathon_id'],
        'members': ObjectId(session['user_id'])
    })
    
    if existing_team:
        flash('You are already in a team for this hackathon', 'warning')
        return redirect(url_for('team_detail', team_id=existing_team['_id']))
    
    # Check if team is at maximum capacity
    hackathon = hackathons.find_one({'_id': team['hackathon_id']})
    if len(team['members']) >= hackathon['max_team_size']:
        flash('This team is already at maximum capacity', 'warning')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Add user to team
    try:
        teams.update_one(
            {'_id': ObjectId(team_id)},
            {'$push': {'members': ObjectId(session['user_id'])}}
        )
        flash('You have joined the team successfully!', 'success')
        return redirect(url_for('team_detail', team_id=team_id))
    except Exception as e:
        flash('An error occurred during team join. Please try again.', 'danger')
        print(f"Team join error: {str(e)}")
        return redirect(url_for('team_detail', team_id=team_id))

# Project Routes
@app.route('/teams/<team_id>/project/edit', methods=['GET', 'POST'])
def edit_project(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    team = teams.find_one({'_id': ObjectId(team_id)})
    
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    if ObjectId(session['user_id']) not in team['members']:
        flash('You must be a team member to edit the project', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    project = projects.find_one({'team_id': ObjectId(team_id)})
    
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    if request.method == 'POST':
        try:
            projects.update_one(
                {'_id': project['_id']},
                {'$set': {
                    'title': request.form['title'],
                    'description': request.form['description'],
                    'tech_stack': request.form['tech_stack'].split(',') if request.form['tech_stack'] else [],
                    'github_link': request.form['github_link'],
                    'status': request.form['status']
                }}
            )
            flash('Project updated successfully!', 'success')
            return redirect(url_for('team_detail', team_id=team_id))
        except Exception as e:
            flash('An error occurred during project update. Please try again.', 'danger')
            print(f"Project update error: {str(e)}")
            return redirect(url_for('edit_project', team_id=team_id))
    
    return render_template('edit_project.html', project=project, team=team)

@app.route('/teams/<team_id>/project/submit', methods=['GET', 'POST'])
def submit_project(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    team = teams.find_one({'_id': ObjectId(team_id)})
    
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    if ObjectId(session['user_id']) not in team['members']:
        flash('You must be a team member to submit the project', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    project = projects.find_one({'team_id': ObjectId(team_id)})
    hackathon = hackathons.find_one({'_id': team['hackathon_id']})
    
    if not project or not hackathon:
        flash('Project or hackathon not found', 'danger')
        return redirect(url_for('team_detail', team_id=team_id))
    
    # Check if project has already been submitted
    existing_submission = submissions.find_one({'project_id': project['_id']})
    
    if existing_submission:
        flash('Your project has already been submitted', 'warning')
        return redirect(url_for('team_detail', team_id=team_id))
    
    if request.method == 'POST':
        new_submission = {
            'project_id': project['_id'],
            'team_id': ObjectId(team_id),
            'hackathon_id': team['hackathon_id'],
            'submission_date': datetime.now(),
            'presentation_link': request.form['presentation_link'],
            'demo_link': request.form['demo_link'],
            'additional_notes': request.form['additional_notes'],
            'status': 'pending'
        }
        
        try:
            submissions.insert_one(new_submission)
            
            # Update project status
            projects.update_one(
                {'_id': project['_id']},
                {'$set': {'status': 'submitted'}}
            )
            
            flash('Project submitted successfully!', 'success')
            return redirect(url_for('team_detail', team_id=team_id))
        except Exception as e:
            flash('An error occurred during project submission. Please try again.', 'danger')
            print(f"Project submission error: {str(e)}")
            return redirect(url_for('submit_project', team_id=team_id))
    
    return render_template('submit_project.html', project=project, team=team, hackathon=hackathon)

# Judge Routes
@app.route('/hackathons/<hackathon_id>/judges/add', methods=['GET', 'POST'])
def add_judge(hackathon_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('You must be an admin to add judges', 'danger')
        return redirect(url_for('index'))
    
    hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
    
    if not hackathon:
        flash('Hackathon not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    if str(hackathon['organizer_id']) != session['user_id']:
        flash('You can only add judges to hackathons you organize', 'danger')
        return redirect(url_for('hackathon_detail', hackathon_id=hackathon_id))
    
    if request.method == 'POST':
        email = request.form['email']
        judge = users.find_one({'email': email})
        
        if not judge:
            # Create a new user with judge role
            hashed_password = generate_password_hash('temporary_password')
            judge_id = users.insert_one({
                'name': request.form['name'],
                'email': email,
                'password': hashed_password,
                'role': 'judge',
                'created_at': datetime.now()
            }).inserted_id
        else:
            judge_id = judge['_id']
            # Update user role to judge if they aren't already
            if judge['role'] != 'judge':
                users.update_one({'_id': judge_id}, {'$set': {'role': 'judge'}})
        
        # Add judge to hackathon if not already added
        if judge_id not in hackathon.get('judges', []):
            try:
                hackathons.update_one(
                    {'_id': ObjectId(hackathon_id)},
                    {'$push': {'judges': judge_id}}
                )
                
                # Create notification for the judge
                notifications.insert_one({
                    'user_id': judge_id,
                    'title': f"You've been added as a judge",
                    'message': f"You've been added as a judge for the hackathon: {hackathon['title']}",
                    'read': False,
                    'created_at': datetime.now()
                })
                
                flash('Judge added successfully!', 'success')
            except Exception as e:
                flash('An error occurred during judge addition. Please try again.', 'danger')
                print(f"Judge addition error: {str(e)}")
                return redirect(url_for('add_judge', hackathon_id=hackathon_id))
        else:
            flash('This judge is already assigned to this hackathon', 'warning')
        
        return redirect(url_for('hackathon_detail', hackathon_id=hackathon_id))
    
    return render_template('add_judge.html', hackathon=hackathon)

@app.route('/judge/evaluate/<submission_id>', methods=['GET', 'POST'])
def evaluate_submission(submission_id):
    if 'user_id' not in session or session['user_role'] != 'judge':
        flash('You must be a judge to evaluate submissions', 'danger')
        return redirect(url_for('index'))
    
    submission = submissions.find_one({'_id': ObjectId(submission_id)})
    
    if not submission:
        flash('Submission not found', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if judge is assigned to this hackathon
    hackathon = hackathons.find_one({
        '_id': submission['hackathon_id'],
        'judges': ObjectId(session['user_id'])
    })
    
    if not hackathon:
        flash('You are not assigned to judge this hackathon', 'danger')
        return redirect(url_for('dashboard'))
    
    project = projects.find_one({'_id': submission['project_id']})
    team = teams.find_one({'_id': submission['team_id']})
    
    # Check if judge has already evaluated this submission
    existing_evaluation = evaluations.find_one({
        'submission_id': ObjectId(submission_id),
        'judge_id': ObjectId(session['user_id'])
    })
    
    if request.method == 'POST':
        evaluation_data = {
            'submission_id': ObjectId(submission_id),
            'project_id': submission['project_id'],
            'hackathon_id': submission['hackathon_id'],
            'judge_id': ObjectId(session['user_id']),
            'innovation_score': int(request.form['innovation_score']),
            'technical_score': int(request.form['technical_score']),
            'presentation_score': int(request.form['presentation_score']),
            'impact_score': int(request.form['impact_score']),
            'total_score': (
                int(request.form['innovation_score']) +
                int(request.form['technical_score']) +
                int(request.form['presentation_score']) +
                int(request.form['impact_score'])
            ),
            'feedback': request.form['feedback'],
            'created_at': datetime.now()
        }
        
        try:
            if existing_evaluation:
                # Update existing evaluation
                evaluations.update_one(
                    {'_id': existing_evaluation['_id']},
                    {'$set': evaluation_data}
                )
                flash('Evaluation updated successfully!', 'success')
            else:
                # Create new evaluation
                evaluations.insert_one(evaluation_data)
                flash('Evaluation submitted successfully!', 'success')
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('An error occurred during evaluation submission. Please try again.', 'danger')
            print(f"Evaluation submission error: {str(e)}")
            return redirect(url_for('evaluate_submission', submission_id=submission_id))
    
    return render_template('evaluate_submission.html', 
                          submission=submission, 
                          project=project, 
                          team=team,
                          hackathon=hackathon,
                          existing_evaluation=existing_evaluation)

# Results and Analytics
@app.route('/hackathons/<hackathon_id>/results')
def hackathon_results(hackathon_id):
    hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
    
    if not hackathon:
        flash('Hackathon not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    # Get all submissions for this hackathon
    hackathon_submissions = list(submissions.find({'hackathon_id': ObjectId(hackathon_id)}))
    submission_ids = [sub['_id'] for sub in hackathon_submissions]
    
    # Get all evaluations for these submissions
    all_evaluations = list(evaluations.find({'submission_id': {'$in': submission_ids}}))
    
    # Calculate average scores and organize results
    results = []
    for submission in hackathon_submissions:
        project = projects.find_one({'_id': submission['project_id']})
        team = teams.find_one({'_id': submission['team_id']})
        
        # Get evaluations for this submission
        sub_evaluations = [e for e in all_evaluations if e['submission_id'] == submission['_id']]
        
        if sub_evaluations:
            avg_total = sum(e['total_score'] for e in sub_evaluations) / len(sub_evaluations)
            
            results.append({
                'team_name': team['name'],
                'project_title': project['title'],
                'average_score': avg_total,
                'judge_count': len(sub_evaluations),
                'team_id': team['_id'],
                'project_id': project['_id']
            })
    
    # Sort results by average score (descending)
    results.sort(key=lambda x: x['average_score'], reverse=True)
    
    return render_template('hackathon_results.html', 
                          hackathon=hackathon, 
                          results=results)

@app.route('/hackathon/<hackathon_id>/register', methods=['GET', 'POST'])
def register_hackathon(hackathon_id):
    if 'user_id' not in session:
        flash('Please login to register for hackathons.', 'warning')
        return redirect(url_for('login'))
    
    try:
        # Get user and hackathon details
        user_id = ObjectId(session['user_id'])
        user = mongo.db.users.find_one({'_id': user_id})
        hackathon = mongo.db.hackathons.find_one({'_id': ObjectId(hackathon_id)})
        
        if not hackathon:
            flash('Hackathon not found.', 'danger')
            return redirect(url_for('list_hackathons'))
            
        if hackathon.get('status') == 'completed':
            flash('This hackathon has already ended.', 'warning')
            return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))
            
        # Check if user is already registered
        existing_team = mongo.db.teams.find_one({
            'hackathon_id': ObjectId(hackathon_id),
            'members': user_id
        })
        
        if existing_team:
            flash('You are already registered for this hackathon.', 'info')
            return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))
        
        if request.method == 'POST':
            team_name = request.form.get('team_name')
            team_description = request.form.get('team_description')
            looking_for_members = 'looking_for_members' in request.form
            
            # Validate team name
            if not team_name:
                flash('Team name is required.', 'danger')
                return render_template('register_hackathon.html', hackathon=hackathon)
                
            # Check if team name is already taken
            existing_team = mongo.db.teams.find_one({
                'hackathon_id': ObjectId(hackathon_id),
                'name': team_name
            })
            
            if existing_team:
                flash('Team name is already taken.', 'danger')
                return render_template('register_hackathon.html', hackathon=hackathon)
            
            # Create new team
            team = {
                'name': team_name,
                'description': team_description,
                'hackathon_id': ObjectId(hackathon_id),
                'leader_id': user_id,
                'members': [user_id],
                'looking_for_members': looking_for_members,
                'created_at': datetime.now()
            }
            
            mongo.db.teams.insert_one(team)
            
            # Create notification
            notification = {
                'user_id': user_id,
                'title': f'Welcome to {team_name}!',
                'message': f'You have successfully registered for {hackathon["title"]} with team {team_name}.',
                'read': False,
                'created_at': datetime.now()
            }
            mongo.db.notifications.insert_one(notification)
            
            flash('Successfully registered for the hackathon!', 'success')
            return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))
            
        return render_template('register_hackathon.html', hackathon=hackathon)
        
    except Exception as e:
        print(f"Error registering for hackathon: {str(e)}")
        flash('An error occurred while registering for the hackathon.', 'danger')
        return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))

@app.route('/hackathon/<hackathon_id>/rounds')
@login_required
def hackathon_rounds(hackathon_id):
    hackathon = mongo.db.hackathons.find_one({'_id': ObjectId(hackathon_id)})
    if not hackathon:
        flash('Hackathon not found', 'error')
        return redirect(url_for('hackathons'))
    
    # Get user's team for this hackathon
    team = mongo.db.teams.find_one({
        'hackathon_id': ObjectId(hackathon_id),
        'members': ObjectId(session['user_id'])
    })
    
    if not team:
        flash('You must be part of a team to view rounds', 'warning')
        return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))
    
    # Get team members' information
    team_members = []
    for member_id in team['members']:
        user = mongo.db.users.find_one({'_id': member_id})
        if user:
            team_members.append({
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email']
            })
    
    # Get all rounds
    rounds_data = list(mongo.db.rounds.find().sort('round_number', 1))
    
    # Get team's submissions
    submissions = {
        sub['round_number']: sub
        for sub in mongo.db.submissions.find({
            'team_id': team['_id'],
            'hackathon_id': ObjectId(hackathon_id)
        })
    }
    
    # Determine current round
    current_round = 1
    for round_num in range(1, 4):
        if round_num in submissions:
            current_round = round_num + 1
    current_round = min(current_round, 3)
    
    return render_template('hackathon_rounds.html',
                         hackathon=hackathon,
                         team=team,
                         team_members=team_members,
                         current_round=current_round,
                         round1_submission=submissions.get(1),
                         round2_submission=submissions.get(2),
                         round3_submission=submissions.get(3))

@app.route('/hackathon/<hackathon_id>/submit/<int:round_number>', methods=['POST'])
@login_required
def submit_round(hackathon_id, round_number):
    hackathon = mongo.db.hackathons.find_one({'_id': ObjectId(hackathon_id)})
    if not hackathon:
        flash('Hackathon not found', 'error')
        return redirect(url_for('hackathons'))
    
    team = mongo.db.teams.find_one({
        'hackathon_id': ObjectId(hackathon_id),
        'members': ObjectId(session['user_id'])
    })
    
    if not team:
        flash('You must be part of a team to submit', 'error')
        return redirect(url_for('view_hackathon', hackathon_id=hackathon_id))
    
    # Get round requirements
    round_info = mongo.db.rounds.find_one({'round_number': round_number})
    if not round_info:
        flash('Invalid round', 'error')
        return redirect(url_for('hackathon_rounds', hackathon_id=hackathon_id))
    
    # Validate submission
    submission_data = {
        'team_id': team['_id'],
        'hackathon_id': ObjectId(hackathon_id),
        'round_number': round_number,
        'submitted_at': datetime.utcnow(),
        'submitted_by': ObjectId(session['user_id'])
    }
    
    # Handle file uploads and form data
    for req in round_info['requirements']:
        if req.endswith('_url'):
            submission_data[req] = request.form.get(req)
        elif req in request.files:
            file = request.files[req]
            if file:
                filename = secure_filename(f"{team['_id']}_{round_number}_{req}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                submission_data[req] = filename
        else:
            submission_data[req] = request.form.get(req)
    
    # Save submission
    try:
        mongo.db.submissions.update_one(
            {
                'team_id': team['_id'],
                'hackathon_id': ObjectId(hackathon_id),
                'round_number': round_number
            },
            {'$set': submission_data},
            upsert=True
        )
        flash('Submission successful!', 'success')
    except Exception as e:
        flash('Error saving submission. Please try again.', 'error')
    
    return redirect(url_for('hackathon_rounds', hackathon_id=hackathon_id))

# Helper function for date parsing
def safe_parse_date(date_value):
    """Safely parse a date value, handling different formats and returning a datetime object."""
    if not date_value:
        return datetime.now()
        
    if isinstance(date_value, datetime):
        return date_value
        
    if isinstance(date_value, str):
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue
    
    # Default fallback
    return datetime.now()

# Helper function for safe ObjectId conversion
def safe_object_id(id_value):
    """Safely convert a value to ObjectId, returning None if invalid."""
    if not id_value:
        return None
    
    if isinstance(id_value, ObjectId):
        return id_value
        
    try:
        return ObjectId(id_value)
    except:
        return None

# My Hackathons Route
@app.route('/my_hackathons')
@login_required
def my_hackathons():
    if session['user_role'] != 'organizer':
        flash('Only organizers can access this page.', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        # Get user_id in both ObjectId and string formats to handle both cases
        user_id_str = session['user_id']
        user_id = safe_object_id(user_id_str)
        
        if not user_id:
            flash('Invalid user ID format. Please log in again.', 'danger')
            return redirect(url_for('logout'))
            
        print(f"Loading hackathons for organizer ID: {user_id}")
        
        # First, try with ObjectId (proper format)
        organizer_hackathons = list(hackathons.find({
            'organizer_id': user_id
        }).sort('created_at', -1))
        
        # If none found, try with string ID format (fallback for data inconsistency)
        if not organizer_hackathons:
            print(f"No hackathons found with ObjectId, trying with string ID: {user_id_str}")
            organizer_hackathons = list(hackathons.find({
                'organizer_id': user_id_str
            }).sort('created_at', -1))
            
            # Auto-fix: If we found hackathons with string ID, update them to use ObjectId
            for hackathon in organizer_hackathons:
                print(f"Fixing string organizer_id for hackathon: {hackathon['_id']}")
                hackathons.update_one(
                    {'_id': hackathon['_id']},
                    {'$set': {'organizer_id': user_id}}
                )
        
        print(f"Found {len(organizer_hackathons)} hackathons for this organizer")
        
        # Calculate participant count for each hackathon
        for hackathon in organizer_hackathons:
            try:
                # Convert _id to string format
                if isinstance(hackathon.get('_id'), ObjectId):
                    hackathon['_id_str'] = str(hackathon['_id'])
                else:
                    hackathon['_id_str'] = str(hackathon.get('_id', ''))
                
                # Find all teams for this hackathon
                hackathon_teams = list(teams.find({'hackathon_id': hackathon['_id']}))
                
                # Count total participants across all teams in this hackathon
                participant_count = 0
                for team in hackathon_teams:
                    participant_count += len(team.get('members', []))
                
                # Add participant count to the hackathon object
                hackathon['participant_count'] = participant_count
                hackathon['team_count'] = len(hackathon_teams)
                
                # Ensure dates are properly parsed
                hackathon['start_date'] = safe_parse_date(hackathon.get('start_date'))
                hackathon['end_date'] = safe_parse_date(hackathon.get('end_date', 
                                    hackathon['start_date'] + timedelta(days=30)))
            except Exception as e:
                print(f"Error processing hackathon {hackathon.get('_id')}: {str(e)}")
                hackathon['participant_count'] = 0
                hackathon['team_count'] = 0
                hackathon['start_date'] = datetime.now()
                hackathon['end_date'] = datetime.now() + timedelta(days=30)
        
        # Calculate total participants across all hackathons
        total_participants = sum(hackathon.get('participant_count', 0) for hackathon in organizer_hackathons)
        
        # Simple status-based categorization
        current_time = datetime.now()
        ongoing_hackathons = []
        upcoming_hackathons = []
        past_hackathons = []
        
        for hackathon in organizer_hackathons:
            try:
                if current_time < hackathon['start_date']:
                    hackathon['status'] = 'upcoming'
                    upcoming_hackathons.append(hackathon)
                elif current_time > hackathon['end_date']:
                    hackathon['status'] = 'completed'
                    past_hackathons.append(hackathon)
                else:
                    hackathon['status'] = 'ongoing'
                    ongoing_hackathons.append(hackathon)
            except Exception as e:
                print(f"Error categorizing hackathon {hackathon.get('_id')}: {str(e)}")
                # Default to upcoming if there's an error
                hackathon['status'] = 'upcoming'
                upcoming_hackathons.append(hackathon)
        
        # Check which routes are available in the app
        available_routes = [
            'view_participants',
            'manage_levels',
            'delete_hackathon',
            'view_results'
        ]
        
        # Filter available routes based on what actually exists in the app
        actual_available_routes = []
        for route in available_routes:
            try:
                url_for(route, hackathon_id='dummy')
                actual_available_routes.append(route)
            except:
                pass
        
        return render_template('my_hackathons.html',
                             hackathons=organizer_hackathons,
                             ongoing_hackathons=ongoing_hackathons,
                             upcoming_hackathons=upcoming_hackathons,
                             past_hackathons=past_hackathons,
                             total_participants=total_participants,
                             available_routes=actual_available_routes)
                             
    except Exception as e:
        import traceback
        error_details = str(e)
        print(f"Error loading my hackathons: {error_details}")
        print(traceback.format_exc())
        
        # Check if we can fix this automatically
        try:
            if "ObjectId" in error_details or "not a valid ObjectId" in error_details:
                flash("Found an issue with ID format. Attempting to fix automatically...", "warning")
                return redirect(url_for('fix_hackathons'))
        except Exception as fix_error:
            print(f"Error in auto-fix attempt: {str(fix_error)}")
        
        flash('An error occurred while loading your hackathons. Try using the "Fix Hackathons" feature.', 'danger')
        return redirect(url_for('fix_hackathons'))

# Fix Hackathons Route - Enhanced to fix all possible issues
@app.route('/fix_hackathons')
@login_required
def fix_hackathons():
    if session['user_role'] != 'organizer':
        flash('Only organizers can access this feature.', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        user_id_str = session['user_id']
        user_id = safe_object_id(user_id_str)
        
        if not user_id:
            flash('Invalid user ID format. Please log in again.', 'danger')
            return redirect(url_for('logout'))
        
        fixes_count = 0
        current_time = datetime.now()
        
        # 1. Fix hackathons with string organizer_id
        string_id_query = {'organizer_id': {'$type': 'string'}}
        string_id_hackathons = list(hackathons.find(string_id_query))
        
        for hackathon in string_id_hackathons:
            try:
                # Check if the string ID matches this user
                if hackathon['organizer_id'] == user_id_str:
                    hackathons.update_one(
                        {'_id': hackathon['_id']},
                        {'$set': {'organizer_id': user_id}}
                    )
                    fixes_count += 1
            except Exception as e:
                print(f"Error fixing string ID hackathon {hackathon.get('_id')}: {str(e)}")
        
        # 2. Fix hackathons with missing or null organizer_id
        missing_organizer_hackathons = list(hackathons.find({
            '$or': [
                {'organizer_id': {'$exists': False}},
                {'organizer_id': None}
            ]
        }))
        
        # Always claim missing organizer hackathons for this user
        for hackathon in missing_organizer_hackathons:
            try:
                hackathons.update_one(
                    {'_id': hackathon['_id']},
                    {'$set': {
                        'organizer_id': user_id,
                        'organizer_name': session['user_name']
                    }}
                )
                fixes_count += 1
            except Exception as e:
                print(f"Error claiming hackathon {hackathon.get('_id')}: {str(e)}")
        
        # 3. Fix date fields for this user's hackathons
        date_fixes = 0
        user_hackathons = list(hackathons.find({
            '$or': [
                {'organizer_id': user_id},
                {'organizer_id': user_id_str}
            ]
        }))
        
        for hackathon in user_hackathons:
            date_updates = {}
            
            # Fix start_date
            if 'start_date' not in hackathon or hackathon['start_date'] is None:
                date_updates['start_date'] = current_time
                date_fixes += 1
            elif isinstance(hackathon['start_date'], str):
                parsed_date = safe_parse_date(hackathon['start_date'])
                date_updates['start_date'] = parsed_date
                date_fixes += 1
            
            # Fix end_date
            if 'end_date' not in hackathon or hackathon['end_date'] is None:
                start_date = hackathon.get('start_date', current_time)
                if isinstance(start_date, str):
                    start_date = safe_parse_date(start_date)
                date_updates['end_date'] = start_date + timedelta(days=30)
                date_fixes += 1
            elif isinstance(hackathon['end_date'], str):
                parsed_date = safe_parse_date(hackathon['end_date'])
                date_updates['end_date'] = parsed_date
                date_fixes += 1
            
            # Apply date updates if needed
            if date_updates:
                hackathons.update_one(
                    {'_id': hackathon['_id']},
                    {'$set': date_updates}
                )
                fixes_count += 1
        
        # 4. Fix team references
        team_fixes = 0
        teams_with_string_hackathon_id = list(teams.find({'hackathon_id': {'$type': 'string'}}))
        
        for team in teams_with_string_hackathon_id:
            try:
                hackathon_id = safe_object_id(team['hackathon_id'])
                if hackathon_id:
                    teams.update_one(
                        {'_id': team['_id']},
                        {'$set': {'hackathon_id': hackathon_id}}
                    )
                    team_fixes += 1
            except Exception as e:
                print(f"Error fixing team {team.get('_id')}: {str(e)}")
        
        total_fixes = fixes_count + date_fixes + team_fixes
        
        if total_fixes > 0:
            flash(f'Successfully fixed {total_fixes} issues in your hackathons database.', 'success')
        else:
            flash('No issues found with your hackathons.', 'info')
        
        # Always redirect back to my_hackathons
        return redirect(url_for('my_hackathons'))
        
    except Exception as e:
        import traceback
        print(f"Error fixing hackathons: {str(e)}")
        print(traceback.format_exc())
        flash('An error occurred while fixing hackathons. Please contact support.', 'danger')
        # Redirect to dashboard instead as a fallback
        flash('An error occurred during database cleanup.', 'danger')
        return redirect(url_for('dashboard'))

# Helper function for file upload validation
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Main execution
if __name__ == '__main__':
    app.run(debug=True)
