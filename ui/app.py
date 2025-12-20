"""
AI Engineering Study Assistant - Streamlit Dashboard
Modern, eye-strain-reducing interface for engineering students

Features:
- AI Chat Interface with tool calling
- Visual Timeline with Gantt-style blocks
- Settings Panel for configuration
- Dark Mode with carefully chosen color palette
"""

import streamlit as st
import requests
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import os

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="AESA - AI Study Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# STYLING - Eye-Strain Reducing Dark Theme
# ============================================

DARK_THEME_CSS = """
<style>
/* Root CSS Variables */
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: #0f3460;
    --bg-card-hover: #1a4a7a;
    --text-primary: #e8e8e8;
    --text-secondary: #a8a8b3;
    --text-muted: #6b6b80;
    --accent-primary: #e94560;
    --accent-secondary: #0f4c75;
    --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --success: #4ecca3;
    --warning: #ffa500;
    --error: #ff6b6b;
    --info: #4facfe;
    --border-radius: 12px;
    --shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* Global Styles */
.stApp {
    background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
}

/* Hide Streamlit Branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Custom Card Component */
.aesa-card {
    background: var(--bg-card);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin: 0.75rem 0;
    box-shadow: var(--shadow-soft);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.aesa-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}

/* Timeline Block Styles */
.timeline-block {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
    cursor: pointer;
}

.timeline-block:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

/* Block type colors */
.block-class { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
    color: white;
}
.block-concept { 
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
    color: white;
}
.block-practice { 
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
    color: white;
}
.block-revision { 
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
    color: white;
}
.block-micro { 
    background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); 
    color: #333;
}
.block-sleep { 
    background: linear-gradient(135deg, #2c3e50 0%, #4a6fa5 100%); 
    color: #ddd;
}
.block-break { 
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
    color: #333;
}
.block-gap {
    background: rgba(255, 255, 255, 0.05);
    border: 2px dashed rgba(255, 255, 255, 0.2);
    color: var(--text-muted);
}

/* Metric Cards */
.metric-card {
    background: var(--bg-card);
    border-radius: var(--border-radius);
    padding: 1.25rem;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent-primary);
    margin-bottom: 0.25rem;
}

.metric-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Chat Message Bubbles */
.chat-user {
    background: var(--accent-secondary);
    color: white;
    padding: 1rem 1.25rem;
    border-radius: 18px 18px 4px 18px;
    margin: 0.5rem 0;
    margin-left: 20%;
}

.chat-assistant {
    background: var(--bg-card);
    color: var(--text-primary);
    padding: 1rem 1.25rem;
    border-radius: 18px 18px 18px 4px;
    margin: 0.5rem 0;
    margin-right: 20%;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Status Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}

.badge-success { background: var(--success); color: #000; }
.badge-warning { background: var(--warning); color: #000; }
.badge-error { background: var(--error); color: #fff; }
.badge-info { background: var(--info); color: #fff; }

/* Section Headers */
.section-header {
    color: var(--text-primary);
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Animations */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.loading {
    animation: pulse 1.5s infinite;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--accent-secondary);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--accent-primary);
}
</style>
"""

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# ============================================
# CONFIGURATION
# ============================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "settings" not in st.session_state:
    st.session_state.settings = {
        "api_base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model_name": "gpt-4",
        "sleep_start": 23,
        "sleep_duration": 7.0,
        "concept_peak": (8, 12),
        "practice_peak": (16, 20),
    }

if "current_date" not in st.session_state:
    st.session_state.current_date = date.today()

# ============================================
# API HELPER FUNCTIONS
# ============================================

def api_call(endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make API call to backend."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def send_chat_message(message: str) -> str:
    """Send message to AI chat endpoint."""
    response = api_call("/api/chat", "POST", {"message": message})
    if "error" in response:
        return f"Error: {response['error']}"
    return response.get("response", "No response received")


def get_today_schedule() -> Dict:
    """Get today's schedule."""
    return api_call("/api/schedule/today")


def get_progress_summary() -> Dict:
    """Get progress summary."""
    return api_call("/api/timeline/pending")

# ============================================
# SIDEBAR - Settings Panel
# ============================================

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # AI Configuration
    with st.expander("🤖 AI Configuration", expanded=False):
        api_base = st.text_input(
            "API Base URL",
            value=st.session_state.settings["api_base_url"],
            help="OpenAI-compatible API endpoint",
            key="api_base_input"
        )
        
        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.settings["api_key"],
            help="Your API key (stored locally only)",
            key="api_key_input"
        )
        
        model_options = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-sonnet", "llama3"]
        model_name = st.selectbox(
            "Model",
            model_options,
            index=model_options.index(st.session_state.settings["model_name"]) 
                  if st.session_state.settings["model_name"] in model_options else 0,
            help="AI model to use",
            key="model_select"
        )
        
        # Save settings
        if st.button("💾 Save AI Settings", use_container_width=True):
            st.session_state.settings["api_base_url"] = api_base
            st.session_state.settings["api_key"] = api_key
            st.session_state.settings["model_name"] = model_name
            st.toast("AI settings saved!", icon="✅")
    
    # Schedule Configuration
    with st.expander("📅 Schedule Settings", expanded=True):
        sleep_start = st.slider(
            "Sleep Start Time",
            min_value=20,
            max_value=24,
            value=st.session_state.settings["sleep_start"],
            format="%d:00",
            help="When you typically go to sleep"
        )
        
        sleep_duration = st.slider(
            "Sleep Duration (hours)",
            min_value=5.0,
            max_value=10.0,
            value=st.session_state.settings["sleep_duration"],
            step=0.5,
            help="How long you sleep"
        )
        
        st.markdown("---")
        st.markdown("**Peak Hours**")
        
        concept_peak = st.slider(
            "📖 Concept Study Peak",
            min_value=5,
            max_value=14,
            value=st.session_state.settings["concept_peak"],
            help="Best hours for conceptual learning"
        )
        
        practice_peak = st.slider(
            "✏️ Practice Peak",
            min_value=14,
            max_value=23,
            value=st.session_state.settings["practice_peak"],
            help="Best hours for problem-solving"
        )
        
        # Save schedule settings
        if st.button("💾 Save Schedule Settings", use_container_width=True):
            st.session_state.settings["sleep_start"] = sleep_start
            st.session_state.settings["sleep_duration"] = sleep_duration
            st.session_state.settings["concept_peak"] = concept_peak
            st.session_state.settings["practice_peak"] = practice_peak
            st.toast("Schedule settings saved!", icon="✅")
    
    # Subject Priorities
    with st.expander("📊 Subject Priorities"):
        subjects = ["MATH101", "PHYS102", "COMP101", "CHEM101", "ENG101"]
        priorities = {}
        for subject in subjects:
            priorities[subject] = st.slider(
                subject,
                min_value=1,
                max_value=10,
                value=5,
                key=f"priority_{subject}"
            )
    
    # Quick Stats
    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Streak", "7 🔥", "+1")
    with col2:
        st.metric("Today", "4h", "85%")

# ============================================
# MAIN LAYOUT
# ============================================

# Header
st.markdown("""
<div style="text-align: center; padding: 1rem 0 2rem 0;">
    <h1 style="color: #e94560; font-size: 2.5rem; margin-bottom: 0.25rem;">
        📚 AI Engineering Study Assistant
    </h1>
    <p style="color: #a8a8b3; font-size: 1.1rem;">
        Intelligent scheduling powered by constraint satisfaction
    </p>
</div>
""", unsafe_allow_html=True)

# Main columns
col_chat, col_timeline = st.columns([1, 1.3], gap="large")

# ============================================
# LEFT COLUMN - Chat Interface
# ============================================

with col_chat:
    st.markdown('<div class="section-header">💬 AI Assistant</div>', unsafe_allow_html=True)
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for msg in st.session_state.messages:
            css_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(
                f'<div class="{css_class}">{icon} {msg["content"]}</div>',
                unsafe_allow_html=True
            )
    
    # Chat input
    if prompt := st.chat_input("Ask me about your schedule..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get AI response
        with st.spinner("Thinking..."):
            response = send_chat_message(prompt)
        
        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Quick action buttons
    st.markdown("---")
    st.markdown("**Quick Actions:**")
    
    quick_cols = st.columns(2)
    with quick_cols[0]:
        if st.button("📊 Show Progress", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Show my progress summary"})
            st.rerun()
    
    with quick_cols[1]:
        if st.button("🔄 Optimize", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Optimize my schedule for this week"})
            st.rerun()
    
    quick_cols2 = st.columns(2)
    with quick_cols2[0]:
        if st.button("⚡ Fill Gaps", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Find micro-gaps I can fill"})
            st.rerun()
    
    with quick_cols2[1]:
        if st.button("📅 Today", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What's my schedule for today?"})
            st.rerun()

# ============================================
# RIGHT COLUMN - Timeline View
# ============================================

with col_timeline:
    st.markdown('<div class="section-header">📆 Weekly Timeline</div>', unsafe_allow_html=True)
    
    # Date navigation
    date_cols = st.columns([1, 2, 1])
    with date_cols[0]:
        if st.button("◀ Prev"):
            st.session_state.current_date -= timedelta(days=7)
    with date_cols[1]:
        st.markdown(
            f"<div style='text-align: center; color: #e8e8e8;'>"
            f"Week of {st.session_state.current_date.strftime('%B %d, %Y')}</div>",
            unsafe_allow_html=True
        )
    with date_cols[2]:
        if st.button("Next ▶"):
            st.session_state.current_date += timedelta(days=7)
    
    # Day tabs
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    tabs = st.tabs(day_names)
    
    # Demo schedule data
    demo_schedule = {
        0: [  # Sunday
            {"time": "00:00-06:00", "title": "🌙 Sleep", "type": "sleep"},
            {"time": "08:00-09:30", "title": "📖 Concept: Calculus Review", "type": "concept"},
            {"time": "09:30-10:00", "title": "⚡ Gap", "type": "gap"},
            {"time": "10:00-12:00", "title": "✏️ Practice: Physics Problems", "type": "practice"},
            {"time": "14:00-15:30", "title": "📚 Revision: CHEM101 Ch3", "type": "revision"},
        ],
        1: [  # Monday  
            {"time": "00:00-06:00", "title": "🌙 Sleep", "type": "sleep"},
            {"time": "08:00-09:30", "title": "🎓 MATH101 Lecture", "type": "class"},
            {"time": "09:30-10:00", "title": "⚡ Quick Review", "type": "micro"},
            {"time": "10:00-11:30", "title": "🎓 PHYS102 Lab", "type": "class"},
            {"time": "14:00-15:30", "title": "📖 Concept: Thermodynamics", "type": "concept"},
            {"time": "16:00-18:00", "title": "✏️ Assignment: COMP101", "type": "practice"},
        ],
        2: [  # Tuesday
            {"time": "00:00-06:00", "title": "🌙 Sleep", "type": "sleep"},
            {"time": "08:00-10:00", "title": "📖 Deep Work: Research", "type": "concept"},
            {"time": "10:00-11:30", "title": "🎓 CHEM101 Lecture", "type": "class"},
            {"time": "13:00-14:00", "title": "☕ Break", "type": "break"},
            {"time": "15:00-17:00", "title": "✏️ Practice: Math Problem Set", "type": "practice"},
        ],
    }
    
    for i, tab in enumerate(tabs):
        with tab:
            day_schedule = demo_schedule.get(i, [
                {"time": "08:00-12:00", "title": "📖 Study Block", "type": "concept"},
                {"time": "14:00-16:00", "title": "✏️ Practice", "type": "practice"},
            ])
            
            for block in day_schedule:
                block_type = block.get("type", "concept")
                css_class = f"block-{block_type}"
                
                st.markdown(
                    f"""<div class="timeline-block {css_class}">
                        <span style="font-weight: 500; opacity: 0.8;">{block['time']}</span>
                        <span style="margin-left: 0.5rem;">{block['title']}</span>
                    </div>""",
                    unsafe_allow_html=True
                )
    
    # Gap Summary
    st.markdown("---")
    st.markdown("**📊 Gap Analysis**")
    
    gap_cols = st.columns(3)
    with gap_cols[0]:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">3</div>
            <div class="metric-label">Deep Work</div>
        </div>
        """, unsafe_allow_html=True)
    
    with gap_cols[1]:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">5</div>
            <div class="metric-label">Standard</div>
        </div>
        """, unsafe_allow_html=True)
    
    with gap_cols[2]:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">8</div>
            <div class="metric-label">Micro</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================
# FOOTER
# ============================================

st.markdown("---")

footer_cols = st.columns(4)

with footer_cols[0]:
    if st.button("🔄 Optimize Week", use_container_width=True, type="primary"):
        st.toast("Optimizing your schedule...", icon="⚡")

with footer_cols[1]:
    if st.button("➕ Add Task", use_container_width=True):
        st.toast("Opening task dialog...", icon="📝")

with footer_cols[2]:
    if st.button("📊 Analytics", use_container_width=True):
        st.toast("Loading analytics...", icon="📈")

with footer_cols[3]:
    if st.button("🧹 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Version info
st.markdown(
    "<div style='text-align: center; color: #6b6b80; font-size: 0.8rem; padding: 1rem;'>"
    "AESA v1.0.0 | Powered by Constraint Satisfaction + AI"
    "</div>",
    unsafe_allow_html=True
)
