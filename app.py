
Gabriella Pásztor <pasztorg1968@gmail.com>
12:15 (4 órával ezelőtt)
címzett: én

python
import sqlite3
import streamlit as st

# --- ADATBÁZIS KEZELÉS (SQLite) ---
def init_db():
    """Létrehozza az adatbázist és a táblákat, ha még nem léteznek."""
    conn = sqlite3.connect("shelter.db")
    cursor = conn.cursor()
   
    # Kutyák tábla
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size TEXT,
            energy_level INTEGER,
            needs_garden INTEGER,
            kid_friendly INTEGER,
            experience_required INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_dog(name, size, energy, garden, kids, exp):
    """Elment egy új kutyát az adatbázisba."""
    conn = sqlite3.connect("shelter.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dogs (name, size, energy_level, needs_garden, kid_friendly, experience_required)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, size, energy, int(garden), int(kids), int(exp)))
    conn.commit()
    conn.close()

def get_all_dogs():
    """Lekéri az összes kutyát az adatbázisból."""
    conn = sqlite3.connect("shelter.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dogs")
    rows = cursor.fetchall()
    conn.close()
   
    dogs = []
    for row in rows:
        dogs.append({
            "id": row[0],
            "name": row[1],
            "size": row[2],
            "energy_level": row[3],
            "needs_garden": bool(row[4]),
            "kid_friendly": bool(row[5]),
            "experience_required": bool(row[6])
        })
    return dogs

# --- PÁROSÍTÓ ALGORITMUS ---
def calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp):
    """Kiszámítja az egyezési százalékot a jelentkező és a kutya között."""
    score = 0
    total_criteria = 5

    # 1. Kert kritérium (Kizáró ok)
    if dog["needs_garden"] and not app_garden:
        return 0
    score += 1

    # 2. Tapasztalat kritérium (Kizáró ok)
    if dog["experience_required"] and not app_exp:
        return 0
    score += 1

    # 3. Gyerek kompatibilitás (Kizáró ok)
    if app_kids and not dog["kid_friendly"]:
        return 0
    score += 1

    # 4. Energiaszint vs Munkaidő / Lakás
    if dog["energy_level"] >= 4 and app_work > 6 and app_housing == "Lakás":
        pass
    else:
        score += 1

    # 5. Lakásméret vs Kutya méret
    if dog["size"] == "Nagy (L)" and app_housing == "Lakás" and not app_garden:
        pass
    else:
        score += 1

    return int((score / total_criteria) * 100)

# --- WEBDIZÁJN ÉS FELÜLET (Streamlit) ---
def main():
    st.set_page_config(page_title="Intelligens Állatmentő Rendszer", page_icon="🐾", layout="centered")
    init_db()

    st.title("🐾 Intelligens Állatmentő & Párosító Rendszer")
    st.write("Nyugati mintára épült menhelyi menedzsment és gazdi-matching szoftver.")

    # Oldalsáv / Navigáció fülek
    tab1, tab2 = st.tabs(["📋 Gazdi Kereső (Matching)", "🐕 Menhelyi Nyilvántartás (Új kutya)"])

    # --- 1. FÜL: GAZDI MATCHING ---
    with tab1:
        st.header("Találd meg a tökéletes társat!")
        st.write("Töltsd ki az élethelyzeted, és az algoritmus megmutatja a hozzád illő kutyákat.")

        col1, col2 = st.columns(2)
        with col1:
            app_name = st.text_input("Jelentkező neve", "Kovács Péter")
            app_housing = st.selectbox("Lakóhely típusa", ["Lakás", "Kertes ház"])
            app_work = st.slider("Mennyi időt töltesz távol otthonról naponta? (óra)", 0, 12, 4)
       
        with col2:
            app_garden = st.checkbox("Van saját, biztonságos kertem", value=False)
            app_kids = st.checkbox("Van kisgyermek a családban", value=False)
            app_exp = st.checkbox("Tapasztalt kutyatartó vagyok (volt már problémás/nagytestű kutyám)", value=False)

        if st.button("🔍 Hozzám illő kutyák keresése", type="primary"):
            dogs = get_all_dogs()
            if not dogs:
                st.info("A menhely adatbázisa jelenleg üres. Kérjük, előbb vigyél fel kutyákat a második fülön!")
            else:
                st.subheader(f"✨ Riport: {app_name} részére")
               
                matches = []
                for dog in dogs:
                    score = calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp)
                    if score >= 60:  # Csak a biztonságos, 60% feletti egyezéseket mutatjuk
                        matches.append((dog, score))
               
                # Sorrendbe állítás a legmagasabb pontszám szerint
                matches.sort(key=lambda x: x[1], reverse=True)

                if not matches:
                    st.warning("⚠️ Sajnos jelenleg nincs olyan kutyánk, aki biztonsággal passzolna az élethelyzetedhez.")
                else:
                    for dog, score in matches:
                        # Vizuális visszajelzés a pontszám alapján
                        if score == 100:
                            badge = "🥇 Tökéletes párosítás!"
                        else:
                            badge = "👍 Jó választás lehet"
                       
                        st.info(f"**{dog['name']}** — **{score}%-os egyezés** ({badge})\n\n"
                                f"ℹ️ *Tulajdonságok:* Méret: {dog['size']} | Energiaszint: {dog['energy_level']}/5 | "
                                f"Kert igény: {'Igen' if dog['needs_garden'] else 'Nem'} | "
                                f"Gyerekbarát: {'Igen' if dog['kid_friendly'] else 'Nem'} | "
                                f"Tapasztalatot igényel: {'Igen' if dog['experience_required'] else 'Nem'}")

    # --- 2. FÜL: MENHELYI ADATBEVITEL ---
    with tab2:
        st.header("Új mentett kutya regisztrálása")
        st.write("Az itt elmentett adatok közvetlenül bekerülnek a `shelter.db` adatbázisba.")

        with st.form("dog_form", clear_on_submit=True):
            dog_name = st.text_input("Kutya neve / azonosítója", placeholder="Pl.: Bodri, Rex, 12-es kennel lakója")
            dog_size = st.selectbox("Kutya mérete", ["Kicsi (S)", "Közepes (M)", "Nagy (L)"])
            dog_energy = st.slider("Energiaszint (1: lusta/idős - 5: hiperaktív/munkakutya)", 1, 5, 3)
           
            st.write("Speciális igények:")
            dog_garden = st.checkbox("Kizárólag kertes házba költözhet (lakásba nem való)")
            dog_kids = st.checkbox("Gyerekbarát (bátran vihető kisgyerekes családba)")
            dog_exp = st.checkbox("Tapasztalt gazdit igényel (pl. domináns, szökős vagy rehabilitációt igénylő)")

            submitted = st.form_submit_with_submission_id(id="save_dog_btn") # unique submit component
            if submitted:
                if dog_name.strip() == "":
                    st.error("Kérjük, adj meg egy nevet a kutyának!")
                else:
                    save_dog(dog_name, dog_size, dog_energy, dog_garden, dog_kids, dog_exp)
                    st.success(f"🎉 **{dog_name}** sikeresen elmentve az adatbázisba!")

        # Jelenlegi állomány listázása az adatbázisból
        st.subheader("🏠 Jelenleg a menhelyen lévő kutyák:")
        current_dogs = get_all_dogs()
        if not current_dogs:
            st.text("Az adatbázis még nem tartalmaz kutyát.")
        else:
            for d in current_dogs:
                st.text(f"• {d['name']} (Méret: {d['size']}, Energia: {d['energy_level']}/5)")

if __name__ == "__main__":
    main()
