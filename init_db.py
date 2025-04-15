# init_db.py
# Script to initialize MongoDB with sample data for the hackathon platform

from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import random

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["hackathon_db"]

# Clear existing collections
collections = ["users", "hackathons", "teams", "projects", "submissions", "evaluations", "notifications", "judges"]
for collection in collections:
    db[collection].delete_many({})

print("Cleared existing collections.")

# Sample data
# -----------

# Create admin users
admin_ids = []
admins = [
    {"name": "Admin User", "email": "admin@example.com", "password": "admin123"},
    {"name": "Jane Admin", "email": "jane@example.com", "password": "jane123"}
]

for admin in admins:
    admin_id = db.users.insert_one({
        "name": admin["name"],
        "email": admin["email"],
        "password": generate_password_hash(admin["password"]),
        "role": "admin",
        "skills": ["management", "organization"],
        "created_at": datetime.now()
    }).inserted_id
    admin_ids.append(admin_id)
    print(f"Created admin user: {admin['name']}")

# Create judge users
judge_ids = []
judges = [
    {"name": "Judge One", "email": "judge1@example.com", "password": "judge123"},
    {"name": "Judge Two", "email": "judge2@example.com", "password": "judge123"},
    {"name": "Judge Three", "email": "judge3@example.com", "password": "judge123"},
    {"name": "Judge Four", "email": "judge4@example.com", "password": "judge123"}
]

for judge in judges:
    judge_id = db.users.insert_one({
        "name": judge["name"],
        "email": judge["email"],
        "password": generate_password_hash(judge["password"]),
        "role": "judge",
        "skills": ["technical expertise", "evaluation"],
        "created_at": datetime.now()
    }).inserted_id
    judge_ids.append(judge_id)
    print(f"Created judge user: {judge['name']}")

# Create participant users
participant_ids = []
skills_options = [
    "Python", "JavaScript", "React", "Node.js", "MongoDB", "Flask",
    "Django", "Machine Learning", "Data Science", "UI/UX Design",
    "Frontend", "Backend", "Mobile Development", "DevOps", "Cloud Computing"
]

participants = [
    {"name": "Alice Smith", "email": "alice@example.com", "password": "alice123"},
    {"name": "Bob Jones", "email": "bob@example.com", "password": "bob123"},
    {"name": "Charlie Brown", "email": "charlie@example.com", "password": "charlie123"},
    {"name": "Diana Prince", "email": "diana@example.com", "password": "diana123"},
    {"name": "Eva Green", "email": "eva@example.com", "password": "eva123"},
    {"name": "Frank Castle", "email": "frank@example.com", "password": "frank123"},
    {"name": "Grace Hopper", "email": "grace@example.com", "password": "grace123"},
    {"name": "Henry Ford", "email": "henry@example.com", "password": "henry123"},
    {"name": "Irene Adler", "email": "irene@example.com", "password": "irene123"},
    {"name": "Jack Sparrow", "email": "jack@example.com", "password": "jack123"},
    {"name": "Kathryn Janeway", "email": "kathryn@example.com", "password": "kathryn123"},
    {"name": "Leo Tolstoy", "email": "leo@example.com", "password": "leo123"},
    {"name": "Maria Hill", "email": "maria@example.com", "password": "maria123"},
    {"name": "Nick Fury", "email": "nick@example.com", "password": "nick123"},
    {"name": "Olivia Pope", "email": "olivia@example.com", "password": "olivia123"}
]

for participant in participants:
    # Assign 2-4 random skills to each participant
    user_skills = random.sample(skills_options, random.randint(2, 4))
    
    user_id = db.users.insert_one({
        "name": participant["name"],
        "email": participant["email"],
        "password": generate_password_hash(participant["password"]),
        "role": "participant",
        "skills": user_skills,
        "created_at": datetime.now()
    }).inserted_id
    participant_ids.append(user_id)
    print(f"Created participant user: {participant['name']} with skills: {user_skills}")

# Create hackathons
hackathon_ids = []
hackathon_themes = [
    ["AI for Good", "Sustainability", "Social Impact"],
    ["FinTech", "Blockchain", "Cryptocurrency"],
    ["Healthcare", "MedTech", "Wellness"],
    ["Smart Cities", "IoT", "Urban Planning"],
    ["Education", "EdTech", "Remote Learning"],
    ["Gaming", "Virtual Reality", "Augmented Reality"]
]

current_date = datetime.now()

hackathons = [
    {
        "title": "AI for Sustainable Development",
        "description": "Create innovative AI solutions to address sustainable development goals.",
        "start_date": current_date - timedelta(days=60),
        "end_date": current_date - timedelta(days=58),
        "location": "Virtual",
        "max_team_size": 4,
        "status": "completed",
        "themes": hackathon_themes[0]
    },
    {
        "title": "FinTech Innovation Challenge",
        "description": "Build the next generation of financial technology solutions.",
        "start_date": current_date - timedelta(days=30),
        "end_date": current_date - timedelta(days=28),
        "location": "New York",
        "max_team_size": 3,
        "status": "completed",
        "themes": hackathon_themes[1]
    },
    {
        "title": "Healthcare Hackathon",
        "description": "Solving healthcare challenges with technology.",
        "start_date": current_date - timedelta(days=5),
        "end_date": current_date + timedelta(days=1),
        "location": "Boston",
        "max_team_size": 5,
        "status": "active",
        "themes": hackathon_themes[2]
    },
    {
        "title": "Smart Cities Hackathon",
        "description": "Reimagine urban living with smart technology solutions.",
        "start_date": current_date + timedelta(days=15),
        "end_date": current_date + timedelta(days=17),
        "location": "San Francisco",
        "max_team_size": 4,
        "status": "upcoming",
        "themes": hackathon_themes[3]
    },
    {
        "title": "EdTech Challenge",
        "description": "Create innovative solutions for the future of education.",
        "start_date": current_date + timedelta(days=30),
        "end_date": current_date + timedelta(days=32),
        "location": "Chicago",
        "max_team_size": 3,
        "status": "upcoming",
        "themes": hackathon_themes[4]
    },
    {
        "title": "Game Development Jam",
        "description": "Build exciting games and immersive experiences.",
        "start_date": current_date + timedelta(days=45),
        "end_date": current_date + timedelta(days=47),
        "location": "Los Angeles",
        "max_team_size": 4,
        "status": "upcoming",
        "themes": hackathon_themes[5]
    }
]

# Assign organizers and judges to hackathons
for i, hackathon in enumerate(hackathons):
    organizer_id = admin_ids[i % len(admin_ids)]
    
    # Assign 2-3 judges to each hackathon
    hackathon_judges = random.sample(judge_ids, random.randint(2, 3))
    
    hackathon_id = db.hackathons.insert_one({
        "title": hackathon["title"],
        "description": hackathon["description"],
        "start_date": hackathon["start_date"],
        "end_date": hackathon["end_date"],
        "location": hackathon["location"],
        "max_team_size": hackathon["max_team_size"],
        "organizer_id": organizer_id,
        "status": hackathon["status"],
        "judges": hackathon_judges,
        "sponsors": [],
        "prizes": ["1st Place: $1000", "2nd Place: $500", "3rd Place: $250"],
        "themes": hackathon["themes"],
        "created_at": current_date - timedelta(days=90)
    }).inserted_id
    hackathon_ids.append(hackathon_id)
    print(f"Created hackathon: {hackathon['title']}")

# Create teams
team_ids = []
team_names = [
    "Code Wizards", "ByteBusters", "Algo Avengers", "Data Dynamos", 
    "Pixel Pirates", "Tech Titans", "Script Savants", "Logic Lords",
    "Cloud Crusaders", "Syntax Samurai", "Bug Slayers", "DevOps Demons",
    "Function Fellows", "Circuit Breakers", "Neural Ninjas", "Query Questers",
    "Stack Overflow", "Coding Catalysts", "Binary Bandits", "Hash Hackers"
]

for hackathon_id in hackathon_ids:
    hackathon = db.hackathons.find_one({"_id": hackathon_id})
    
    # Create 3-5 teams for each hackathon
    num_teams = random.randint(3, 5)
    for i in range(num_teams):
        # Get a random team name that hasn't been used yet
        team_name = team_names.pop(0)
        
        # Select a random team leader
        leader_id = random.choice(participant_ids)
        
        # Determine team size (between 2 and max_team_size)
        team_size = random.randint(2, min(hackathon["max_team_size"], len(participant_ids)))
        
        # Select random team members, ensuring leader is included
        remaining_participants = [p_id for p_id in participant_ids if p_id != leader_id]
        member_ids = random.sample(remaining_participants, team_size - 1)
        member_ids.append(leader_id)
        
        looking_for_members = random.choice([True, False]) if team_size < hackathon["max_team_size"] else False
        
        team_id = db.teams.insert_one({
            "name": team_name,
            "description": f"Team description for {team_name}",
            "hackathon_id": hackathon_id,
            "leader_id": leader_id,
            "members": member_ids,
            "created_at": hackathon["start_date"] - timedelta(days=random.randint(1, 10)),
            "looking_for_members": looking_for_members
        }).inserted_id
        team_ids.append(team_id)
        print(f"Created team: {team_name} for hackathon: {hackathon['title']}")
        
        # Create project for the team
        tech_stack = random.sample(skills_options, random.randint(3, 5))
        
        project_id = db.projects.insert_one({
            "title": f"{team_name}'s Project",
            "description": f"An innovative project by {team_name} for the {hackathon['title']} hackathon.",
            "team_id": team_id,
            "hackathon_id": hackathon_id,
            "tech_stack": tech_stack,
            "github_link": f"https://github.com/{team_name.lower().replace(' ', '-')}/project",
            "created_at": hackathon["start_date"],
            "status": "submitted" if hackathon["status"] == "completed" else "in progress"
        }).inserted_id
        
        print(f"Created project for team: {team_name}")
        
        # For completed hackathons, create submissions and evaluations
        if hackathon["status"] == "completed":
            submission_id = db.submissions.insert_one({
                "project_id": project_id,
                "team_id": team_id,
                "hackathon_id": hackathon_id,
                "submission_date": hackathon["end_date"] - timedelta(hours=random.randint(1, 8)),
                "presentation_link": f"https://slides.com/{team_name.lower().replace(' ', '-')}/presentation",
                "demo_link": f"https://devpost.com/{team_name.lower().replace(' ', '-')}/demo",
                "additional_notes": "We're proud to present our solution that addresses the hackathon challenge.",
                "status": "evaluated"
            }).inserted_id
            
            print(f"Created submission for team: {team_name}")
            
            # Create evaluations from judges
            for judge_id in hackathon["judges"]:
                innovation_score = random.randint(6, 10)
                technical_score = random.randint(6, 10)
                presentation_score = random.randint(6, 10)
                impact_score = random.randint(6, 10)
                total_score = innovation_score + technical_score + presentation_score + impact_score
                
                db.evaluations.insert_one({
                    "submission_id": submission_id,
                    "project_id": project_id,
                    "hackathon_id": hackathon_id,
                    "judge_id": judge_id,
                    "innovation_score": innovation_score,
                    "technical_score": technical_score,
                    "presentation_score": presentation_score,
                    "impact_score": impact_score,
                    "total_score": total_score,
                    "feedback": "Great job! The project shows a lot of creativity and technical skill.",
                    "created_at": hackathon["end_date"] + timedelta(days=1)
                })
                
                judge_name = db.users.find_one({"_id": judge_id})["name"]
                print(f"Created evaluation from judge: {judge_name} for team: {team_name}")

# Create notifications
for user_id in participant_ids + judge_ids:
    user = db.users.find_one({"_id": user_id})
    
    # Sample notifications
    if user["role"] == "judge":
        hackathons_judging = list(db.hackathons.find({"judges": user_id}))
        
        for hackathon in hackathons_judging:
            db.notifications.insert_one({
                "user_id": user_id,
                "title": f"You're judging {hackathon['title']}",
                "message": f"You've been assigned as a judge for {hackathon['title']}. Please review submissions after the event ends.",
                "read": random.choice([True, False]),
                "created_at": hackathon["start_date"] - timedelta(days=5)
            })
    else:
        user_teams = list(db.teams.find({"members": user_id}))
        
        for team in user_teams:
            hackathon = db.hackathons.find_one({"_id": team["hackathon_id"]})
            
            db.notifications.insert_one({
                "user_id": user_id,
                "title": f"Welcome to {team['name']}",
                "message": f"You are now a member of {team['name']} for the {hackathon['title']} hackathon.",
                "read": random.choice([True, False]),
                "created_at": team["created_at"] + timedelta(hours=1)
            })

print("\nDatabase initialization complete!")
print("Sample user credentials:")
print("Admin: admin@example.com / admin123")
print("Judge: judge1@example.com / judge123")
print("Participant: alice@example.com / alice123")
