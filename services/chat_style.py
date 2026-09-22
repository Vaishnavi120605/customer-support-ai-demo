"""Shared conversation presentation for both Streamlit screens."""
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
