"""Shared conversation presentation adapted from Stitch Precision Slate."""
CHAT_STYLE = """
<style>
[data-testid="stToolbar"], [data-testid="stAppDeployButton"], #MainMenu {display:none !important;}
[data-testid="stChatMessage"] {
 width:fit-content !important; max-width:82%; margin:.4rem auto .4rem 0 !important;
 border-radius:18px 18px 18px 4px !important; box-shadow:0 4px 14px rgba(0,0,0,.12) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
 margin-left:auto !important; margin-right:0 !important; flex-direction:row-reverse;
 background:linear-gradient(135deg,#2459a6,#264a84) !important;
 border-color:#467cca !important; border-radius:18px 18px 4px 18px !important;
}
[data-testid="stChatMessage"] p {line-height:1.65;}
@media(max-width:640px) {[data-testid="stChatMessage"] {max-width:94%;}}
</style>
"""
CHAT_STYLE += """
<style>
.stApp,[data-testid="stHeader"],[data-testid="stBottom"] {background:#f8f9ff !important; color:#0b1c30 !important;}
.block-container {max-width:1600px !important; padding:1.2rem 2rem 5rem !important;}
h1,h2,h3,p,label,[data-testid="stCaptionContainer"] {color:#0b1c30;}
h2,h3 {font-size:1.1rem !important;}
[data-testid="stSidebar"] {background:#eff4ff !important; border-right:1px solid #dce5f3 !important;}
.brand-name {color:#0b1c30 !important;} .brand-kicker,.eyebrow,.queue-label {color:#0051d5 !important;}
.brand-copy {color:#657187 !important;}
.sidebar-card {background:#fff !important; border-color:#e1e8f3 !important; color:#657187 !important;}
.sidebar-card b {color:#0b1c30 !important;}
.hero,.console-hero {background:white !important; border:1px solid #e1e8f3 !important; box-shadow:none !important; padding:1rem 1.4rem !important; border-radius:12px !important;}
.hero h1,.console-hero h1 {font-size:1.5rem !important; color:#0b1c30 !important; line-height:1.3 !important;}
.hero p,.console-hero p {color:#657187 !important; font-size:.85rem !important;}
.console-hero .kicker {color:#0051d5 !important;}
.ai-state {background:#eff4ff !important; border-color:#d5e3ff !important; color:#184a91 !important;}
.human-state {background:#eaf7f2 !important; border-color:#c3e6d9 !important; color:#1a6751 !important;}
.support-state span {color:inherit !important;}
.stTextInput input,.stTextArea textarea,[data-testid="stSidebar"] .stTextInput input {background:#fff !important; color:#0b1c30 !important; border:1px solid #d6dfed !important; border-radius:8px !important;}
[data-baseweb="select"] > div {background:#fff !important; color:#0b1c30 !important; border-color:#d6dfed !important;}
.stButton > button,[data-testid="stFormSubmitButton"] > button {background:#eff4ff !important; color:#184a91 !important; border:1px solid #d9e5fa !important; border-radius:8px !important;}
.stButton > button p,[data-testid="stFormSubmitButton"] > button p {color:inherit !important;}
.stButton > button[kind="primary"],[data-testid="stFormSubmitButton"] > button {background:#131b2e !important; color:white !important;}
[data-testid="stMetric"] {background:white !important; border-color:#e1e8f3 !important; color:#0b1c30 !important;}
[data-testid="stChatMessage"] {max-width:68%; background:#fff !important; border:1px solid #e3e9f3 !important; border-radius:12px 12px 12px 3px !important; box-shadow:none !important; padding:.8rem 1rem !important;}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {background:#0051d5 !important; border-color:#0051d5 !important; border-radius:12px 12px 3px 12px !important;}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p {color:white !important;}
[data-testid="stChatMessage"] p {font-size:.9rem; line-height:1.6;}
[data-testid="stChatInput"] {background:#eff4ff !important; border:1px solid #d5e1f4 !important; box-shadow:none !important;}
[data-testid="stChatInput"] textarea {color:#0b1c30 !important;}
[data-testid="stForm"] {background:white; border:1px solid #e1e8f3; border-radius:12px;}
.desk-nav {display:flex; align-items:center; justify-content:space-between; padding:12px 18px; background:white; border:1px solid #e1e8f3; border-radius:12px; margin-bottom:18px; gap:16px;}
.desk-nav b {color:#0b1c30;} .desk-nav a {text-decoration:none; color:#536179; font-size:.8rem; padding:9px 14px; border-radius:7px;}
.desk-nav a.active {background:#131b2e; color:white;} .desk-nav span {color:#0051d5; font-size:.7rem;}
</style>
"""

def navigation(active: str) -> str:
    customer = 'active' if active == 'customer' else ''
    agent = 'active' if active == 'agent' else ''
    return f'''<nav class="desk-nav"><b>▣ Acme Support</b><div>
    <a class="{agent}" href="http://localhost:8502" target="_blank">Support Agent Dashboard</a>
    <a class="{customer}" href="http://localhost:8501" target="_blank">Customer Chat</a>
    </div><span>● SUPPORT DESK</span></nav>'''
