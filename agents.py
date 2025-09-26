# agents.py
import os
import re
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# ---------- Entity Extractor (Hybrid) ----------
def entity_extractor_agent(text: str) -> Dict[str, Any]:
    """
    Hybrid entity extractor using Groq LLM + regex fallback.
    Extracts symptoms, medications, and urgency with explanation.
    """
    print("Using Groq LLM for entity extraction...")

    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are a medical assistant that extracts symptoms, medications, and urgency."},
            {"role": "user", "content": f"Extract symptoms, medications, and urgency from the message: '{text}' and return valid JSON with keys: symptoms, medications, urgency."}
        ],
        "temperature": 0,
        "max_tokens": 200
    }

    try:
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        output_text = response.json()["choices"][0]["message"]["content"].strip()
        start = output_text.find("{")
        if start >= 0:
            result = json.loads(output_text[start:])
            result["explanation"] = "Entities extracted using the Groq LLM."
            return result
    except Exception as e:
        print("Groq LLM extraction failed:", e)

    # Regex fallback
    print("Using regex fallback for entity extraction...")
    symptoms, meds, urgency = [], [], []

    # Symptom patterns
    symptom_patterns = [
        r"\b(headache|fever|cough|chest pain|shortness of breath|vomit|nausea|dizziness|rash|back pain)\b",
        r"\b(pain|ache|aching|sore|swelling|burning)\b\s*(\w+)?"
    ]
    for pat in symptom_patterns:
        for m in re.finditer(pat, text, flags=re.I):
            symptoms.append(m.group(0).strip())

    # Medication-like tokens
    for m in re.finditer(r"\b([A-Z][a-z0-9\-]{2,})\b", text):
        token = m.group(1)
        if re.search(r"(ine|ol|ide|cin|vir|azole|statin|cillin|in|mab)$", token, flags=re.I):
            meds.append(token)

    # Urgency detection
    if re.search(r"\b(emergency|urgent|immediately|now|asap|severe|high fever|can't breathe)\b", text, flags=re.I):
        urgency.append("high")
    elif re.search(r"\b(mild|low|sometimes|occasionally|after a while)\b", text, flags=re.I):
        urgency.append("low")

    return {
        "symptoms": list(dict.fromkeys(symptoms)),
        "medications": list(dict.fromkeys(meds)),
        "urgency": urgency or ["unknown"],
        "explanation": "Entities extracted using regex fallback."
    }


# ---------- Triage Agent ----------
def triage_agent(text: str) -> str:
    """
    Classify patient message into: Appointment, Symptom Report, Medication Issue, Administrative, Other.
    Adds explanation.
    """
    print("Running Triage Agent (Groq LLM)...")

    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are a medical assistant that classifies patient messages."},
            {"role": "user", "content": f"Classify the following patient message into one of: Appointment, Symptom Report, Medication Issue, Administrative, Other. Message: '{text}'. Answer with just the class label."}
        ],
        "temperature": 0,
        "max_tokens": 10
    }

    try:
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        label = response.json()["choices"][0]["message"]["content"].strip()
        label_lower = label.lower()

        if label_lower.startswith("appointment"):
            return "Appointment (Identified because the text contains scheduling or booking intent.)"
        if label_lower.startswith("symptom"):
            return "Symptom Report (Identified because the text describes medical complaints or discomfort.)"
        if "medic" in label_lower:
            return "Medication Issue (Identified because the text contains references to drugs, dosage, or prescriptions.)"
        if "admin" in label_lower:
            return "Administrative (Identified because the text relates to hospital procedures, fees, or paperwork.)"
        return "Other (No clear match found, defaulting to Other.)"

    except Exception as e:
        print("Groq LLM triage failed:", e)
        # Fallback rules
        if re.search(r"\b(appointment|book|schedule|visit|timings)\b", text, flags=re.I):
            return "Appointment (Matched via keyword rule for scheduling)."
        if re.search(r"\b(medication|dose|tablet|prescription|side effect|taking|syrup|medicine|medicines)\b", text, flags=re.I):
            return "Medication Issue (Matched via keyword rule for medicines)."
        if re.search(r"\b(hours|charge|charges|insurance|documents|cancel|teleconsultation|fees)\b", text, flags=re.I):
            return "Administrative (Matched via keyword rule for hospital procedures)."
        return "Symptom Report (Default classification when no other category matches)."


# ---------- Routing Agent ----------
DEPARTMENT_RULES = {
    "Cardiology": ["chest pain", "shortness of breath", "palpitations"],
    "General Medicine": ["fever", "cough", "headache", "vomit", "nausea", "dizziness", "rash", "back pain"],
    "Dermatology": ["rash", "itch", "skin"],
    "Neurology": ["seizure", "dizziness", "headache", "weakness"],
    "Pharmacy": ["medication", "dose", "prescription", "tablet", "drug", "medicine", "capsule", "syrup"],
    "Admin": ["hours", "charges", "insurance", "documents", "cancel", "teleconsultation", "policy", "procedure", "fees"],
}

def routing_agent(category: str, entities: Dict[str, Any], text: str) -> str:
    """
    Route to the correct department with explanation.
    """
    print("Running Routing Agent...")

    text_lower = text.lower()
    meds = entities.get("medications", [])
    ent_text = " ".join(entities.get("symptoms", [])).lower()

    # Pharmacy
    med_keywords = r"\b(medication|tablet|dose|prescription|drug|medicine|capsule|syrup)\b"
    if meds or re.search(med_keywords, text_lower):
        return "Pharmacy (Detected medication-related terms, routed to Pharmacy.)"

    # Admin
    admin_keywords = r"\b(hours|charge|charges|insurance|documents|cancel|teleconsultation|policy|procedure|fees)\b"
    if "Administrative" in category or re.search(admin_keywords, text_lower):
        return "Admin (Detected administrative-related terms, routed to Admin.)"

    # Symptom-based routing
    scores = {}
    for dept, keywords in DEPARTMENT_RULES.items():
        if dept in ["Pharmacy", "Admin"]:
            continue
        for kw in keywords:
            if kw in ent_text or kw in text_lower:
                scores[dept] = scores.get(dept, 0) + 1
    if scores:
        best_match = max(scores.items(), key=lambda x: x[1])[0]
        return f"{best_match} (Symptoms matched with {', '.join(DEPARTMENT_RULES[best_match])}.)"

    # Appointment fallback
    if "Appointment" in category:
        return "Admin (Appointment request detected, routed to Admin for scheduling.)"

    # Default fallback
    return "General Medicine (No specific match, default fallback to General Medicine.)"


# ---------- Response Agent ----------
def response_agent(category: str, entities: Dict[str, Any], department: str) -> str:
    """
    Generates a detailed, patient-friendly response based on classification and routing.
    """
    print("Running Response Agent...")

    urgency = entities.get("urgency", "unknown")
    if isinstance(urgency, list):
        urgency_label = urgency[0] if urgency else "unknown"
    else:
        urgency_label = urgency

    symptoms = entities.get("symptoms", [])
    meds = entities.get("medications", [])

    # High urgency
    if urgency_label.lower() == "high":
        return (
            f"Alert: The patient reports urgent symptoms "
            f"({', '.join(symptoms) if symptoms else 'unspecified'}). "
            f"This case has been escalated immediately to {department}. "
            "Please ensure this patient receives priority attention."
        )

    # Appointment
    if "Appointment" in category:
        return (
            "Your request for an appointment has been recorded. "
            f"Our Admin team will coordinate with {department if department != 'Admin' else 'the appropriate department'} "
            "to confirm an available slot. You will be notified shortly."
        )

    # Medication Issue
    if "Medication Issue" in category:
        return (
            f"A medication-related query has been detected regarding {', '.join(meds) if meds else 'the mentioned medicines'}. "
            f"This has been routed to {department}. The Pharmacy team will review and provide guidance on availability, dosage, or alternatives."
        )

    # Administrative
    if "Administrative" in category:
        return (
            "Your administrative request has been received. "
            "Our Admin team will respond with the necessary details regarding hospital fees, procedures, or policies."
        )

    # Symptom Report
    if "Symptom Report" in category:
        return (
            "Thank you for reporting your health concerns. "
            f"Recorded symptoms: {', '.join(symptoms) if symptoms else 'unspecified'}. "
            f"This case has been routed to {department} for further review. "
            "A medical professional will provide guidance based on your symptoms. "
            "If your condition worsens, please seek emergency care immediately."
        )

    # Default fallback
    return (
        f"Your request has been forwarded to {department} for handling. "
        "You will receive a response shortly."
    )
