import streamlit as st
from logic import processa_messaggio
from state import ProfiloUtente

st.set_page_config(page_title="Chef AI + Critic", layout="wide")

if "stato_profilo" not in st.session_state:
    st.session_state.stato_profilo = ProfiloUtente()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: MONITORAGGIO TOKEN ---
with st.sidebar:
    st.header("📊 Monitoraggio Token")
    budget = st.session_state.stato_profilo.budget_token
    consumati = st.session_state.stato_profilo.token_totali
    percentuale = min(consumati / budget, 1.0)
    
    st.progress(percentuale)
    st.write(f"Token Usati: {consumati} / {budget}")
    
    if percentuale > 0.8:
        st.warning("Attenzione: Stai per esaurire i token gratuiti!")

    st.divider()
    st.subheader("🛒 Dispensa")
    for ing in st.session_state.stato_profilo.ingredienti:
        st.caption(f"- {ing.nome}")

# --- CHAT ---
st.title("👨‍🍳 Mediterranean AI Agent")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Cosa cuciniamo?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Lo Chef sta scrivendo e il Critico sta controllando..."):
        risposta, nuovo_stato = processa_messaggio(prompt, st.session_state.stato_profilo)
        st.session_state.stato_profilo = nuovo_stato
        
        st.session_state.messages.append({"role": "assistant", "content": risposta})
        with st.chat_message("assistant"):
            st.markdown(risposta)
    
    st.rerun()