import streamlit as st
from datetime import datetime, timedelta
import sqlite3
import os
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Apartment Complaint System", layout="wide")
st.title("🏢 Apartment Complaint Management System")

# -------------------- DATABASE SETUP --------------------
conn = sqlite3.connect("complaints.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    flat_no TEXT,
    block TEXT,
    image_path TEXT,
    status TEXT,
    priority TEXT,
    created_at TEXT,
    deadline_at TEXT,
    resolved_at TEXT
)
""")
conn.commit()

# -------------------- TENANT FORM --------------------
st.header("📝 Tenant: Raise a Complaint")
with st.form("complaint_form"):
    title = st.text_input("Complaint Title")
    description = st.text_area("Description")
    flat_no = st.text_input("Flat Number")
    block = st.text_input("Block")
    image = st.file_uploader("Upload Image", type=["jpg","png","jpeg"])
    
    submitted = st.form_submit_button("Submit Complaint")
    if submitted:
        if not title or not flat_no or not block:
            st.error("Please fill all required fields (Title, Flat No, Block).")
        else:
            image_path = ""
            if image:
                if not os.path.exists("images"):
                    os.makedirs("images")
                image_path = os.path.join("images", image.name)
                with open(image_path, "wb") as f:
                    f.write(image.getbuffer())
            
            status = "Pending"
            priority = "Medium"

            title_lower = title.lower()
            if any(word in title_lower for word in ["electric", "short circuit", "fire"]):
                priority = "Critical"
            elif any(word in title_lower for word in ["leak", "water", "pipe"]):
                priority = "High"
            elif any(word in title_lower for word in ["clean", "fan", "light"]):
                priority = "Low"

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deadline_at = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO complaints (title, description, flat_no, block, image_path, status, priority, created_at, deadline_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, flat_no, block, image_path, status, priority, created_at, deadline_at))
            conn.commit()

            st.success("✅ Complaint submitted successfully!")
            st.info(f"🔔 New complaint from Flat {flat_no}: '{title}'")

# -------------------- OWNER DASHBOARD --------------------
st.markdown("---")
st.header("👨‍💼 Owner Dashboard")

# 🔄 ALWAYS reload latest data
df = pd.read_sql("SELECT * FROM complaints ORDER BY id DESC", conn)

# -------------------- SUMMARY --------------------
total = len(df)
pending = df[df['status']=="Pending"].shape[0]
resolved = df[df['status']=="Resolved"].shape[0]
overdue = df[(df['status']!="Resolved") & (pd.to_datetime(df['deadline_at']) < datetime.now())].shape[0]

st.subheader("📊 Summary")
st.write(f"Total complaints: {total}")
st.write(f"Pending: {pending}")
st.write(f"Resolved: {resolved}")
st.write(f"Overdue: {overdue} 🔴")

# -------------------- FLATS & BLOCKS --------------------
st.subheader("🏠 Flats & Blocks Overview")
flat_blocks = df[['flat_no','block']].drop_duplicates().sort_values(['block','flat_no'])

for idx, row in flat_blocks.iterrows():
    flat = row['flat_no']
    block = row['block']
    flat_data = df[df['flat_no']==flat]

    pending_count = flat_data[flat_data['status']=='Pending'].shape[0]
    resolved_count = flat_data[flat_data['status']=='Resolved'].shape[0]

    st.write(f"Flat {flat} | Block {block} | Pending: {pending_count} | Resolved: {resolved_count}")

    if st.button(f"Show Complaints for Flat {flat}", key=f"show_flat_{flat}_{idx}"):
        flat_complaints = df[df['flat_no']==flat]

        for _, c in flat_complaints.iterrows():
            st.write(f"🆔 ID: {c['id']} | Issue: {c['title']} | Status: {c['status']}")
            
            if c['image_path']:
                st.image(c['image_path'], width=200)

            col1, col2 = st.columns(2)

            # -------------------- IN PROGRESS --------------------
            with col1:
                if st.button(f"In Progress ⏳ ({c['id']})", key=f"inprogress_{c['id']}"):
                    cursor.execute("UPDATE complaints SET status=? WHERE id=?", ("In Progress", c['id']))
                    conn.commit()
                    st.success(f"Complaint {c['id']} marked In Progress")
                    st.rerun()

            # -------------------- RESOLVE BUTTON (FIXED) --------------------
            with col2:
                if st.button(f"Resolve ✅ ({c['id']})", key=f"resolved_{c['id']}"):
                    resolved_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    cursor.execute(
                        "UPDATE complaints SET status=?, resolved_at=? WHERE id=?",
                        ("Resolved", resolved_time, c['id'])
                    )
                    conn.commit()

                    # 🔔 Notifications
                    st.success(f"Complaint {c['id']} resolved successfully ✅")
                    st.info(f"📨 Tenant Notification: '{c['title']}' from Flat {c['flat_no']} resolved")
                    st.info(f"🔔 Owner Alert: Complaint {c['id']} closed")

                    # 🎉 UI effect
                    st.balloons()

                    # 🔄 Refresh UI
                    st.rerun()

# -------------------- RESOLVED HISTORY --------------------
st.subheader("📂 Resolved Complaints History")
resolved_df = df[df['status']=="Resolved"].copy()

if not resolved_df.empty:
    for _, c in resolved_df.iterrows():
        resolved_time = c['resolved_at'] if pd.notna(c['resolved_at']) else "Unknown"
        st.write(f"Flat {c['flat_no']} | Issue: {c['title']} | Resolved on: {resolved_time}")
        if c['image_path']:
            st.image(c['image_path'], width=150)
else:
    st.write("No resolved complaints yet.")

# -------------------- ANALYTICS --------------------
st.header("📊 Analytics")

common = df['title'].value_counts().reset_index()
common.columns = ['Complaint','Count']
st.dataframe(common)
fig1 = px.pie(common, names='Complaint', values='Count')
st.plotly_chart(fig1)

flat_count = df['flat_no'].value_counts().reset_index()
flat_count.columns = ['Flat','Count']
st.dataframe(flat_count)
fig2 = px.bar(flat_count, x='Flat', y='Count')
st.plotly_chart(fig2)

block_count = df['block'].value_counts().reset_index()
block_count.columns = ['Block','Count']
st.dataframe(block_count)
fig3 = px.bar(block_count, x='Block', y='Count')
st.plotly_chart(fig3)

status_count = df['status'].value_counts().reset_index()
status_count.columns = ['Status','Count']
fig4 = px.pie(status_count, names='Status', values='Count')
st.plotly_chart(fig4)

# -------------------- AVERAGE RESOLUTION TIME --------------------
st.subheader("⏱ Average Resolution Time")

resolved_only = df[df['status']=="Resolved"].copy()

if not resolved_only.empty:
    resolved_only['created_at'] = pd.to_datetime(resolved_only['created_at'])
    resolved_only['resolved_at'] = pd.to_datetime(resolved_only['resolved_at'], errors='coerce')

    resolved_only['resolution_days'] = (
        resolved_only['resolved_at'] - resolved_only['created_at']
    ).dt.days

    avg_days = resolved_only['resolution_days'].mean()

    if pd.isna(avg_days):
        avg_days = 3

    st.write(f"Average resolution time: {avg_days:.1f} days")
else:
    st.write("Average resolution time: 3 days (default)")