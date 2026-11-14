import psycopg2
import base64
import streamlit as st

MENHELY_JELSZO = "menhely2026"

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"], connect_timeout=5)

def save_dog(name, size, energy, garden, kids, exp, shelter_name, shelter_contact, image_base64):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO dogs (name, size, energy_level, needs_garden, kid_friendly, experience_required, shelter_name, shelter_contact, image_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, size, energy, garden, kids, exp, shelter_name, shelter_contact, image_base64))
    conn.commit()
    cursor.close()
    conn.close()

def delete_dog(dog_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dogs WHERE id = %s", (dog_id,))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_dogs():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, size, energy_level, needs_garden, kid_friendly, experience_required, shelter_name, shelter_contact, image_data FROM dogs ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        dogs = list()
        for d_id, name, size, energy, garden, kids, exp, s_name, s_contact, img in rows:
            dogs.append(dict(id=d_id, name=name, size=size, energy_level=energy, needs_garden=garden, kid_friendly=kids, experience_required=exp, shelter_name=s_name or "Nincs megadva", shelter_contact=s_contact or "Nincs megadva", image_data=img))
        return dogs
    except Exception as e:
        st.warning(f"Adatbázis kapcsolat figyelmeztetés: {e}")
        return list()

def calculate_match_score(dog, app_housing, app_work, app_garden, app_kids, app_exp):
    if dog.get("needs_garden") and not app_garden:
        return 0
    if dog.get("experience_required") and not app_exp:
        return 0
    if app_kids and not dog.get("kid_friendly"):
        return 0
    score = 3
    if not (dog.get("energy_level") >= 4 and app_work > 6 and app_housing == "Lakás"):
        score += 1
    if not (dog.get("size") == "Nagy (L)" and app_housing == "Lakás" and not app_garden):
        score += 1
    return int((score / 5) * 100)

def render_dog_card(dog, score, is_demo=False):
    badge = "🥇 Tökéletes párosítás!" if score == 100 else "👍 Jó választás lehet"
    with st.container(border=True):
        c_img, c_info = st.columns((1, 2))
        with c_img:
            if dog.get("image_data"):
                st.image(base64.b64decode(dog.get("image_data")), use_container_width=True)
            else:
                st.markdown("🐕\n*(Nincs fotó)*")
        with c_info:
            st.subheader(f"{dog.get('name')} — {score}% ({badge})")
            st.write(f"**Méret:** {dog.get('size')} | **Energiaszint:** {dog.get('energy_level')}/5")
            st.write(f"**Kert igény:** {'Igen' if dog.get('needs_garden') else 'Nem'} | **Gyerekbarát:** {'Igen' if dog.get('kid_friendly') else 'Nem'} | **Tapasztalat:** {'Igen' if dog.get('experience_required') else 'Nem'}")
            if is_demo:
                st.info(f"🏠 **Szervezet:** {dog.get('shelter_name')} | 📞 **Elérhetőség:** {dog.get('shelter_contact')}")
            else:
                st.success(f"🏠 **Menhely / Szervezet:** {dog.get('shelter_name')}\n\n📞 **Elérhetőség:** {dog.get('shelter_contact')}")

def render_live_search():
    st.header("Találd meg a tökéletes társat!")
    col1, col2 = st.columns(2)
    with col1:
        app_name = st.text_input("Jelentkező neve", "Kovács Péter", key="live_name")
        app_housing = st.selectbox("Lakóhely típusa", ("Lakás", "Kertes ház"), key="live_house")
        app_work = st.slider("Napi távol töltött órák", 0, 12, 4, key="live_work")
    with col2:
        app_garden = st.checkbox("Van saját, biztonságos kertem", key="live_garden")
        app_kids = st.checkbox("Van kisgyermek a családban", key="live_kids")
        app_exp = st.checkbox("Tapasztalt kutyatartó vagyok", key="live_exp")

    if not st.button("🔍 Hozzám illő kutyák keresése", type="primary", key="live_search"):
        return

    dogs = get_all_dogs()
    if not dogs:
        st.info("Az éles menhelyi adatbázis jelenleg üres. Próbáld ki a rendszert a középső **Demó Mód** fülön!")
        return

    st.subheader(f"✨ Riport: {app_name} részére")
    matches = list()
    for d in dogs:
        s = calculate_match_score(d, app_housing, app_work, app_garden, app_kids, app_exp)
        if s >= 60:
            matches.append((s, d))
    matches.sort(key=lambda item: item, reverse=True)

    if not matches:
        st.warning("⚠️ Sajnos jelenleg nincs olyan kutyánk, aki biztonsággal passzolna az élethelyzetedhez.")
        return

    for score, dog in matches:
        render_dog_card(dog, score, is_demo=False)

def render_demo_tab():
    st.header("🧪 Interaktív Demó Mód (Jelszó nélkül)")
    st.info("ℹ️ **Kedves Állatvédők!** Itt jelszó nélkül, szabadon kipróbálhatják a rendszer működését. Az itt feltöltött tesztkutyák csak az Önök böngészőjében jelennek meg.")
    
    with st.expander("➕ 1. Lépés: Próbakutya feltöltése", expanded=True):
        with st.form("demo_dog_form", clear_on_submit=True):
            d_name = st.text_input("Tesztkutya neve", placeholder="Pl.: Buksi")
            col_ds1, col_ds2 = st.columns(2)
            with col_ds1:
                d_shelter = st.text_input("Szervezet neve", "Teszt Menhely")
            with col_ds2:
                d_contact = st.text_input("Elérhetőség", "+36 20 111 2222")
            d_size = st.selectbox("Kutya mérete", ("Kicsi (S)", "Közepes (M)", "Nagy (L)"))
            d_energy = st.slider("Energiaszint", 1, 5, 3)
            d_file = st.file_uploader("Tesztfotó feltöltése (opcionális)", type=("jpg", "jpeg", "png"))
            d_garden = st.checkbox("Kizárólag kertes házba költözhet")
            d_kids = st.checkbox("Gyerekbarát")
            d_exp = st.checkbox("Tapasztalt gazdit igényel")
            submitted_demo = st.form_submit_button("🧪 Próbakutya hozzáadása")
            
        if submitted_demo and not d_name.strip():
            st.error("Adjon meg egy nevet a tesztkutyának!")
        elif submitted_demo:
            d_img = base64.b64encode(d_file.read()).decode("utf-8") if d_file else None
            st.session_state.demo_dogs.insert(0, dict(name=d_name, size=d_size, energy_level=d_energy, needs_garden=d_garden, kid_friendly=d_kids, experience_required=d_exp, shelter_name=d_shelter, shelter_contact=d_contact, image_data=d_img))
            st.success(f"🎉 **{d_name}** bekerült a demó listába!")

    st.divider()
    st.subheader("🔍 2. Lépés: Tesztelje a párosítást!")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        demo_housing = st.selectbox("Teszt gazdi lakóhelye", ("Lakás", "Kertes ház"))
        demo_work = st.slider("Napi távol töltött órák", 0, 12, 4)
    with col_d2:
        demo_garden = st.checkbox("Van saját kertje")
        demo_kids = st.checkbox("Van kisgyermeke")
        demo_exp = st.checkbox("Tapasztalt kutyatartó")

    if not st.button("🚀 Demó párosítás indítása", type="primary"):
        return

    demo_matches = list()
    for d in st.session_state.demo_dogs:
        s = calculate_match_score(d, demo_housing, demo_work, demo_garden, demo_kids, demo_exp)
        if s >= 60:
            demo_matches.append((s, d))
    demo_matches.sort(key=lambda item: item, reverse=True)

    if not demo_matches:
        st.warning("A beállított élethelyzethez egyik demó kutya sem passzol.")
        return

    for score, dog in demo_matches:
        render_dog_card(dog, score, is_demo=True)

def render_admin_tab():
    st.header("Éles menhelyi nyilvántartás")
    password_input = st.text_input("Add meg a menhelyi jelszót:", type="password")
    
    if password_input == "":
        st.info("ℹ️ Ez a felület jelszóval védett.")
        return
    if password_input != MENHELY_JELSZO:
        st.error("❌ Hibás jelszó!")
        return

    st.success("🔓 Sikeres bejelentkezés!")
    with st.form("dog_form", clear_on_submit=True):
        dog_name = st.text_input("Kutya neve", placeholder="Pl.: Bodri")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            shelter_name = st.text_input("Menhely neve", placeholder="Pl.: Érdi Állatvédők")
        with col_s2:
            shelter_contact = st.text_input("Elérhetőség", placeholder="Pl.: +36 30 123 4567")
        dog_size = st.selectbox("Kutya mérete", ("Kicsi (S)", "Közepes (M)", "Nagy (L)"))
        dog_energy = st.slider("Energiaszint", 1, 5, 3)
        uploaded_file = st.file_uploader("Fotó feltöltése", type=("jpg", "jpeg", "png"))
        dog_garden = st.checkbox("Kizárólag kertes házba költözhet")
        dog_kids = st.checkbox("Gyerekbarát")
        dog_exp = st.checkbox("Tapasztalt gazdit igényel")
        submitted = st.form_submit_button("💾 Kutya mentése")

    if submitted and not dog_name.strip():
        st.error("Kérjük, adj meg egy nevet!")
    elif submitted:
        try:
            img_b64 = base64.b64encode(uploaded_file.read()).decode("utf-8") if uploaded_file else None
            save_dog(dog_name, dog_size, dog_energy, dog_garden, dog_kids, dog_exp, shelter_name, shelter_contact, img_b64)
            st.success(f"🎉 **{dog_name}** elmentve!")
        except Exception as e:
            st.error(f"Hiba a mentéskor: {e}")

    st.divider()
    current_dogs = get_all_dogs()
    for d in current_dogs:
        c1, c2 = st.columns((3, 1))
        with c1:
            st.write(f"🐾 **{d.get('name')}** — *{d.get('shelter_name')}*")
        with c2:
            if st.button("🗑️ Törlés", key=f"del_{d.get('id')}"):
                delete_dog(d.get('id'))
                st.rerun()

def main():
    st.set_page_config(page_title="Intelligens Állatmentő Rendszer", page_icon="🐾", layout="centered")
    st.session_state.setdefault("demo_dogs", list())
