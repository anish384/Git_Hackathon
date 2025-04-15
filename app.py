# app.py - Main Flask Application

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/hackathon_db"
app.secret_key = os.urandom(24)

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

# Routes
@app.route('/')
def index():
    upcoming_hackathons = list(hackathons.find({"start_date": {"$gte": datetime.now()}}).sort("start_date", 1).limit(3))
    return render_template('index.html', hackathons=upcoming_hackathons)

# User Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing_user = users.find_one({'email': request.form['email']})
        
        if existing_user is None:
            hashed_password = generate_password_hash(request.form['password'])
            users.insert_one({
                'name': request.form['name'],
                'email': request.form['email'],
                'password': hashed_password,
                'role': 'participant',
                'skills': request.form['skills'].split(','),
                'created_at': datetime.now()
            })
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        flash('Email already exists. Please log in.', 'danger')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users.find_one({'email': request.form['email']})
        
        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = str(user['_id'])
            session['user_role'] = user['role']
            session['user_name'] = user['name']
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Dashboard Routes
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = users.find_one({'_id': ObjectId(user_id)})
    
    if user['role'] == 'admin':
        # Admin dashboard
        user_hackathons = list(hackathons.find({'organizer_id': ObjectId(user_id)}))
        return render_template('admin_dashboard.html', hackathons=user_hackathons, user=user)
    
    elif user['role'] == 'judge':
        # Judge dashboard
        assigned_hackathons = list(hackathons.find({'judges': ObjectId(user_id)}))
        return render_template('judge_dashboard.html', hackathons=assigned_hackathons, user=user)
    
    else:
        # Participant dashboard
        user_teams = list(teams.find({'members': ObjectId(user_id)}))
        team_ids = [team['_id'] for team in user_teams]
        user_projects = list(projects.find({'team_id': {'$in': team_ids}}))
        user_hackathons = []
        
        for team in user_teams:
            if 'hackathon_id' in team:
                hackathon = hackathons.find_one({'_id': team['hackathon_id']})
                if hackathon:
                    user_hackathons.append(hackathon)
        
        return render_template('participant_dashboard.html', 
                              teams=user_teams, 
                              projects=user_projects, 
                              hackathons=user_hackathons, 
                              user=user)

# Hackathon Routes
@app.route('/hackathons')
def list_hackathons():
    all_hackathons = list(hackathons.find())
    return render_template('hackathons.html', hackathons=all_hackathons)

@app.route('/hackathons/create', methods=['GET', 'POST'])
def create_hackathon():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('You must be an admin to create hackathons', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        
        new_hackathon = {
            'title': request.form['title'],
            'description': request.form['description'],
            'start_date': start_date,
            'end_date': end_date,
            'location': request.form['location'],
            'max_team_size': int(request.form['max_team_size']),
            'organizer_id': ObjectId(session['user_id']),
            'status': 'upcoming',
            'created_at': datetime.now(),
            'judges': [],
            'sponsors': [],
            'prizes': [],
            'themes': request.form['themes'].split(',') if request.form['themes'] else []
        }
        
        hackathon_id = hackathons.insert_one(new_hackathon).inserted_id
        flash('Hackathon created successfully!', 'success')
        return redirect(url_for('hackathon_detail', hackathon_id=hackathon_id))
    
    return render_template('create_hackathon.html')

@app.route('/hackathons/<hackathon_id>')
def hackathon_detail(hackathon_id):
    hackathon = hackathons.find_one({'_id': ObjectId(hackathon_id)})
    
    if not hackathon:
        flash('Hackathon not found', 'danger')
        return redirect(url_for('list_hackathons'))
    
    hackathon_teams = list(teams.find({'hackathon_id': ObjectId(hackathon_id)}))
    judge_ids = hackathon.get('judges', [])
    hackathon_judges = list(users.find({'_id': {'$in': judge_ids}}))
    
    return render_template('hackathon_detail.html', 
                          hackathon=hackathon, 
                          teams=hackathon_teams,
                          judges=hackathon_judges)

@app.route('/hackathons/<hackathon_id>/edit', methods=['GET', 'POST'])
def edit_hackathon(hackathon_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('You must be an admin to edit hackathons', 'danger')
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
    
    return render_template('edit_hackathon.html', hackathon=hackathon)

# Team Routes
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
    teams.update_one(
        {'_id': ObjectId(team_id)},
        {'$push': {'members': ObjectId(session['user_id'])}}
    )
    
    flash('You have joined the team successfully!', 'success')
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
        
        submissions.insert_one(new_submission)
        
        # Update project status
        projects.update_one(
            {'_id': project['_id']},
            {'$set': {'status': 'submitted'}}
        )
        
        flash('Project submitted successfully!', 'success')
        return redirect(url_for('team_detail', team_id=team_id))
    
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

# Main execution
if __name__ == '__main__':
    app.run(debug=True)
