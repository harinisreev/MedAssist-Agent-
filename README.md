MedAssist Agent

Author: Harinisree Venkatesan |

Overview

A multi-agent AI system that automatically processes patient queries, extracts relevant medical information (symptoms, medications, urgency), classifies them, and routes them to the correct hospital department using Python, MySQL, LLMs, and Streamlit.

Features:
Automatic triage of patient queries.
Extracts symptoms, medications, and urgency.
Classifies and routes queries to appropriate departments.
Logs all queries in SQL for traceability.
Streamlit UI for real-time query monitoring.

Tech Stack
Python, MySQL, LLMs (OpenAI + LangChain), Streamlit, SQLAlchemy, Pandas, Numpy, dotenv

Project Structure
MedAssist Agent/
├── db.py            # Database schema & connection
├── agents.py        # AI agent logic
├── app_streamlit.py # Streamlit frontend
├── requirements.txt     
└── README.md

Usage

Configure environment variables (.env) for DB access.
Set up MySQL database and import CSV queries.
Run app_streamlit.py to launch the interface.
View and manage query triage in real-time.

Conclusion
MedAssist Agent reduces manual workload in hospitals, improves response times, and enhances patient support via intelligent, automated query triage.
