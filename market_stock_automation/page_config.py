import streamlit as st

st.title("⚙️ Figyelt Részvények Beállítása")
st.write("Itt adhatsz hozzá új részvényeket a bothoz, vagy távolíthatod el a régieket. A beállítások azonnal mentődnek a felhő lemezére.")

# Aktuális kosár beolvasása
tickers = st.session_state.AVAILABLE_TICKERS

st.markdown("### 📋 Jelenleg figyelt részvényeid kosara:")
cols = st.columns(4)
for idx, t in enumerate(tickers):
    with cols[idx % 4]:
        # Minden részvény mellé teszünk egy piros törlés gombot
        if st.button(f"❌ Töröl: {t}", key=f"del_{t}", use_container_width=True):
            st.session_state.AVAILABLE_TICKERS.remove(t)
            st.session_state.save_tickers_to_disk()
            st.success(f"{t} sikeresen eltávolítva a rendszerből!")
            st.rerun()

st.markdown("---")
st.markdown("### ➕ Új részvény hozzáadása")
new_ticker = st.text_input("Írd be a részvény pontos Ticker kódját (pl. SFIX, ASML, BMW, AAPL):").upper().strip()

if st.button("➕ RÉSZVÉNY HOZZÁADÁSA A BOTHODHOZ", use_container_width=True):
    if new_ticker:
        if new_ticker not in st.session_state.AVAILABLE_TICKERS:
            st.session_state.AVAILABLE_TICKERS.append(new_ticker)
            st.session_state.save_tickers_to_disk()
            st.success(f"✅ {new_ticker} sikeresen felvéve a figyelt kosárba!")
            st.rerun()
        else:
            st.warning("Ez a részvény már benne van a kosaradban!")
    else:
        st.error("Kérlek, írj be egy érvényes kódot!")