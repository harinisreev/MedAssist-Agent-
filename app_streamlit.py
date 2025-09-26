# app_streamlit.py
import streamlit as st
import mysql.connector
from db import init_db, SessionLocal, PatientQuery, ExtractedEntity, PatientRemark, RoutingLog
from agents import entity_extractor_agent, triage_agent, routing_agent, response_agent

# Initialize DB (create tables if not exists)
init_db()

st.set_page_config(page_title="MedAssist Agent", layout="wide")

st.title("MedAssist Agents – A Multi-Agent AI System for Clinical Query Triage")

# ------------------- Query Form -------------------
with st.form("query_form"):
    query_text = st.text_area("Enter patient query/message", height=120)
    submitted = st.form_submit_button("Submit")

if submitted and query_text.strip():
    session = SessionLocal()
    try:
        # 1) Save raw query
        pq = PatientQuery(query_text=query_text)
        session.add(pq)
        session.commit()
        session.refresh(pq)
        qid = pq.id

        # 2) Entity extraction
        entities = entity_extractor_agent(query_text)
        for s in entities.get("symptoms", []):
            e = ExtractedEntity(query_id=qid, entity_type="Symptom", entity_text=s)
            session.add(e)
        for m in entities.get("medications", []):
            e = ExtractedEntity(query_id=qid, entity_type="Medication", entity_text=m)
            session.add(e)

        # urgency as remark
        if entities.get("urgency"):
            r = PatientRemark(query_id=qid, remark_type="Urgency", remark_text=str(entities.get("urgency")))
            session.add(r)

        session.commit()

        # 3) Triage
        triage_label = triage_agent(query_text)
        pq.triage_category = triage_label
        session.commit()

        # 4) Routing
        department = routing_agent(triage_label, entities, query_text)
        log = RoutingLog(query_id=qid, department=department, agent_details="Auto-routed")
        session.add(log)
        session.commit()

        # 5) Response
        suggested = response_agent(triage_label, entities, department)
        pq.suggested_response = suggested
        session.commit()

        # Display results
        st.success("Processed!")
        st.markdown(f"**Query ID:** {qid}")
        st.markdown("### Extracted Entities")
        st.write(entities)
        st.markdown("### Triage")
        st.write(triage_label)
        st.markdown("### Routing")
        st.write(department)
        st.markdown("### Suggested response")
        st.write(suggested)

    except Exception as e:
        session.rollback()
        st.error(f"Error: {e}")
    finally:
        session.close()

# ------------------- Recent Queries Section -------------------
st.markdown("---")
st.header("Recent Queries")
session = SessionLocal()
recent = session.query(PatientQuery).order_by(PatientQuery.received_at.desc()).limit(10).all()
for r in recent:
    st.write({
        "id": r.id,
        "text": r.query_text,
        "triage": r.triage_category,
        "suggested": r.suggested_response
    })
session.close()

# ------------------- Clear All Queries + Related Data -------------------
def clear_queries():
    conn = mysql.connector.connect(
        host="localhost", user="root", password="root1234", database="med_assist_agent"
    )
    cursor = conn.cursor()

    # Delete child tables first (to avoid foreign key errors)
    cursor.execute("DELETE FROM extracted_entities;")
    cursor.execute("DELETE FROM patient_remarks;")
    cursor.execute("DELETE FROM routing_logs;")
    cursor.execute("DELETE FROM patientqueries;")

    # Reset auto-increment counters
    cursor.execute("ALTER TABLE extracted_entities AUTO_INCREMENT = 1;")
    cursor.execute("ALTER TABLE patient_remarks AUTO_INCREMENT = 1;")
    cursor.execute("ALTER TABLE routing_logs AUTO_INCREMENT = 1;")
    cursor.execute("ALTER TABLE patientqueries AUTO_INCREMENT = 1;")

    conn.commit()
    conn.close()


if st.button("Clear Recent Queries"):
    clear_queries()
    st.success("All recent queries and related records have been cleared.")
