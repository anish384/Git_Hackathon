from pymongo import MongoClient
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['hackathon_db']

# Clear existing collections
db.users.drop()
db.hackathons.drop()
db.teams.drop()
db.projects.drop()
db.submissions.drop()
db.notifications.drop()
db.rounds.drop()

# Initialize users collection with some sample data
users = [
    {
        "name": "John Doe",
        "email": "john@example.com",
        "password": generate_password_hash("password123"),
        "role": "participant",
        "skills": ["Python", "JavaScript", "React"],
        "created_at": datetime.now()
    },
    {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "password": generate_password_hash("password123"),
        "role": "participant",
        "skills": ["Java", "Spring", "MySQL"],
        "created_at": datetime.now()
    }
]

user_ids = db.users.insert_many(users).inserted_ids

# Initialize hackathons collection
now = datetime.now()
hackathons = [
    {
        "title": "AI Innovation Challenge",
        "description": "Create innovative AI solutions for real-world problems. This hackathon focuses on developing AI applications that can make a positive impact on society.",
        "start_date": now - timedelta(days=1),  # Started yesterday
        "end_date": now + timedelta(days=2),    # Ends in 2 days
        "prize_pool": 5000,
        "max_team_size": 4,
        "status": "ongoing",
        "technologies": ["Python", "TensorFlow", "PyTorch", "Machine Learning"]
    },
    {
        "title": "Web3 DeFi Hackathon",
        "description": "Build the future of decentralized finance. Develop innovative blockchain solutions and smart contracts for the next generation of financial applications.",
        "start_date": now + timedelta(days=7),  # Starts in a week
        "end_date": now + timedelta(days=9),    # 2-day hackathon
        "prize_pool": 10000,
        "max_team_size": 3,
        "status": "upcoming",
        "technologies": ["Solidity", "Web3.js", "Ethereum", "Smart Contracts"]
    },
    {
        "title": "Mobile App Challenge",
        "description": "Create innovative mobile applications that solve everyday problems. Focus on user experience and practical solutions for mobile users.",
        "start_date": now + timedelta(days=14),  # Starts in two weeks
        "end_date": now + timedelta(days=16),    # 2-day hackathon
        "prize_pool": 7500,
        "max_team_size": 4,
        "status": "upcoming",
        "technologies": ["React Native", "Flutter", "iOS", "Android"]
    },
    {
        "title": "Cloud Innovation Summit",
        "description": "Develop cloud-native solutions using cutting-edge technologies. Focus on scalability, reliability, and innovative cloud architectures.",
        "start_date": now - timedelta(days=10),  # Started 10 days ago
        "end_date": now - timedelta(days=8),     # Ended 8 days ago
        "prize_pool": 8000,
        "max_team_size": 4,
        "status": "completed",
        "technologies": ["AWS", "Azure", "Docker", "Kubernetes"]
    }
]

hackathon_ids = db.hackathons.insert_many(hackathons).inserted_ids

# Create hackathon rounds collection
db.rounds.insert_many([
    {
        "round_number": 1,
        "name": "Project Proposal",
        "description": "Submit your project idea and presentation",
        "requirements": ["project_title", "project_description", "presentation"]
    },
    {
        "round_number": 2,
        "name": "MVP Demo",
        "description": "Submit your working prototype and demo video",
        "requirements": ["github_url", "demo_video", "progress_update"]
    },
    {
        "round_number": 3,
        "name": "Final Submission",
        "description": "Submit your final project with documentation",
        "requirements": ["final_github_url", "documentation", "final_presentation", "highlights"]
    }
])

# Create submissions collection with indexes
db.submissions.create_index([("team_id", 1), ("hackathon_id", 1), ("round_number", 1)], unique=True)

# Initialize notifications
notifications = [
    {
        "user_id": user_ids[0],
        "title": "Welcome to HackHub!",
        "message": "Welcome to HackHub! Your account has been created successfully.",
        "read": False,
        "created_at": datetime.now()
    },
    {
        "user_id": user_ids[1],
        "title": "Welcome to HackHub!",
        "message": "Welcome to HackHub! Your account has been created successfully.",
        "read": False,
        "created_at": datetime.now()
    }
]

db.notifications.insert_many(notifications)

print("Database initialized successfully!")
