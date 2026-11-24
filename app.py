import streamlit as st
import psycopg2
import base64
import binascii
import hmac
import hashlib
import os
import re
from contextlib import contextmanager

from datetime import datetime, timezone


# =====================================================
# 1. OLDALBEÁLLÍTÁSOK
# =====================================================

st.set_page_config(
    page_title="Gazdikereső",
    page_icon="🐶",
    layout="wide"
)

MAX_IMAGE_SIZE = 5 * 1024 * 1024


# =====================================================
# 2. ADATBÁZIS KAPCSOLAT
# =====================================================

def get_connection():

    db_url = st.secrets.get("DB_URL")

    if not db_url:
        raise RuntimeError("Nincs beállítva a DB_URL!")

    return psycopg2.connect(
        db_url,
        connect_timeout=10,
        sslmode="require"
    )


@contextmanager
def database_connection():

    conn = get_connection()

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# 3. ADATBÁZIS LÉTREHOZÁSA ÉS FRISSÍTÉSE
# =====================================================

def init_database():

    with database_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dogs (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    size TEXT,
                    energy_level INTEGER,
                    needs_garden BOOLEAN DEFAULT FALSE,
                    kid_friendly BOOLEAN DEFAULT FALSE,
                    experience_required BOOLEAN DEFAULT FALSE,
                    shelter_name TEXT,
                    shelter_contact TEXT,
                    image_data TEXT
                )
            """)

            columns = {
                "size": "TEXT",
                "energy_level": "INTEGER",
                "needs_garden": "BOOLEAN DEFAULT FALSE",
                "kid_friendly": "BOOLEAN DEFAULT FALSE",
                "experience_required": "BOOLEAN DEFAULT FALSE",
                "shelter_name": "TEXT",
                "shelter_contact": "TEXT",
                "image_data": "TEXT"
            }

            for column, definition in columns.items():

                cursor.execute(
                    f"""
                    ALTER TABLE dogs
                    ADD COLUMN IF NOT EXISTS {column} {definition}
                    """
                )# =====================================================
# 4. KÉPEK KEZELÉSE
# =====================================================

def process_image(image_file):

    if image_file is None:
        return None

    image_data = image_file.getvalue()

    if len(image_data) > MAX_IMAGE_SIZE:
        raise ValueError("A kép maximum 5 MB lehet!")

    if image_file.type not in (
        "image/jpeg",
        "image/png"
    ):
        raise ValueError("Csak JPG és PNG képek tölthetők fel!")

    if not (
        image_data.startswith(b"\xff\xd8\xff")
        or image_data.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise ValueError("Érvénytelen képfájl!")

    return base64.b64encode(
        image_data
    ).decode("utf-8")


def decode_image(image_data):

    if not image_data:
        return None

    try:

        decoded = base64.b64decode(
            image_data,
            validate=True
        )

        if (
            decoded.startswith(b"\xff\xd8\xff")
            or decoded.startswith(b"\x89PNG\r\n\x1a\n")
        ):
            return decoded

        return None

    except (ValueError, binascii.Error):
        return None


# =====================================================
# 5. KUTYA MENTÉSE
# =====================================================

def save_dog(
    name,
    size,
    energy,
    garden,
    kids,
    exp,
    shelter_name,
    shelter_contact,
    image_base64
):

    with database_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO dogs (
                    name,
                    size,
                    energy_level,
                    needs_garden,
                    kid_friendly,
                    experience_required,
                    shelter_name,
                    shelter_contact,
                    image_data
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                name,
                size,
                energy,
                garden,
                kids,
                exp,
                shelter_name,
                shelter_contact,
                image_base64
            ))


# =====================================================
# 6. KUTYA TÖRLÉSE
# =====================================================

def delete_dog(dog_id):

    with database_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute(
                "DELETE FROM dogs WHERE id = %s",
                (dog_id,)
            )

            return cursor.rowcount > 0


# =====================================================
# 7. KUTYÁK LEKÉRDEZÉSE
# =====================================================

def get_all_dogs():

    with database_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
               SELECT
    d.id,
    d.name,
    d.size,
    d.energy_level,
    d.needs_garden,
    d.kid_friendly,
    d.experience_required,
    d.shelter_name,
    d.shelter_contact,
    d.image_data,
    CASE
        WHEN s.status = 'approved'
         AND s.plan = 'plus'
         AND s.plus_expires_at > NOW()
        THEN TRUE
        ELSE FALSE
    END AS is_plus
FROM dogs AS d
LEFT JOIN shelter_accounts AS s
    ON d.shelter_account_id = s.id
ORDER BY d.id DESC
            """)

            rows = cursor.fetchall()

        dogs = []

        for d in rows:

            dogs.append({
                "id": d[0],
                "name": d[1],
                "size": d[2] or "Nincs megadva",
                "energy_level": (
                    d[3] if d[3] is not None else 3
                ),
                "needs_garden": bool(d[4]),
                "kid_friendly": bool(d[5]),
                "experience_required": bool(d[6]),
                "shelter_name": d[7] or "Nincs megadva",
                "shelter_contact": d[8] or "Nincs megadva",
               "image_data": d[9],
               "is_plus": bool(d[10])
            })
        return dogs
# =====================================================
# 8. PÁROSÍTÁSI RENDSZER
# =====================================================

def calculate_match_score(
    dog,
    app_housing,
    app_work,
    app_garden,
    app_kids,
    app_exp
):

    if dog["needs_garden"] and not app_garden:
        return 0

    if dog["experience_required"] and not app_exp:
        return 0

    if app_kids and not dog["kid_friendly"]:
        return 0

    score = 0

    # Kertigény
    score += 20

    # Gyerekbarát tulajdonság
    if app_kids and dog["kid_friendly"]:
        score += 20
    elif not app_kids:
        score += 20

    # Tapasztalat
    if dog["experience_required"] and app_exp:
        score += 20
    elif not dog["experience_required"]:
        score += 20

    # Lakhatás és méret
    if dog["size"] == "Nagy (L)":

        if app_housing == "Kertes ház":
            score += 20
        elif app_garden:
            score += 15
        else:
            score += 5

    else:
        score += 20

    # Energiaszint és egyedüllét
    energy = dog["energy_level"]

    if app_work <= 4:
        score += 20

    elif app_work <= 6:
        score += 15 if energy <= 3 else 10

    elif app_work <= 8:
        score += 15 if energy <= 2 else 5

    else:
        score += 10 if energy <= 2 else 0

    return min(100, max(0, int(score)))


# =====================================================
# 9. KUTYÁK PÁROSÍTÁSA
# =====================================================

def find_matches(
    dogs,
    housing,
    work,
    garden,
    kids,
    exp
):

    matches = []

    for dog in dogs:

        score = calculate_match_score(
            dog,
            housing,
            work,
            garden,
            kids,
            exp
        )

        if score >= 60:
            matches.append((score, dog))

    matches.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return matches


# =====================================================
# 10. KUTYA ADATLAP
# =====================================================

def render_dog_card(dog, score):

    with st.container(border=True):
        if dog.get("is_plus", False):
            st.success("⭐ Kiemelt kutyus – Menhely Plusz")
        col1, col2 = st.columns((1, 2))

        with col1:

            image = decode_image(
                dog.get("image_data")
            )

            if image:

                st.image(
                    image,
                    use_container_width=True
                )

            else:

                st.markdown("## 🐕")
                st.caption("Nincs feltöltött fotó")

        with col2:

            st.subheader(
                f"{dog['name']} – {score}%"
            )

            if score >= 90:
                st.success("🥇 Kiváló párosítás!")

            elif score >= 75:
                st.info("👍 Nagyon jó választás lehet!")

            else:
                st.warning("🐾 Érdemes megismerni!")

            st.write(f"**Méret:** {dog['size']}")

            st.write(
                f"**Energiaszint:** "
                f"{dog['energy_level']}/5"
            )

            st.write(
                f"**Kertigény:** "
                f"{'Igen' if dog['needs_garden'] else 'Nem'}"
            )

            st.write(
                f"**Gyerekbarát:** "
                f"{'Igen' if dog['kid_friendly'] else 'Nem'}"
            )

            st.write(
                f"**Tapasztalt gazdi szükséges:** "
                f"{'Igen' if dog['experience_required'] else 'Nem'}"
            )

            st.write(
                f"🏠 **Menhely:** {dog['shelter_name']}"
            )

            st.write(
                f"📞 **Elérhetőség:** "
                f"{dog['shelter_contact']}"
            )


# =====================================================
# 11. TALÁLATOK MEGJELENÍTÉSE
# =====================================================

def display_matches(matches):

    if not matches:

        st.warning(
            "Sajnos nincs megfelelő kutyatalálat."
        )

        return

    st.success(
        f"🎉 {len(matches)} kutyát találtunk!"
    )

    for score, dog in matches:

        render_dog_card(dog, score)


# =====================================================
# 12. ÉLES KUTYAKERESŐ
# =====================================================

def render_live_search():

    st.header(
        "🔍 Találd meg a tökéletes társat!"
    )

    col1, col2 = st.columns(2)

    with col1:

        app_name = st.text_input(
            "Jelentkező neve",
            key="live_name"
        )

        app_housing = st.selectbox(
            "Lakóhely típusa",
            ("Lakás", "Kertes ház"),
            key="live_housing"
        )

        app_work = st.slider(
            "Napi távol töltött órák",
            0, 12, 4,
            key="live_work"
        )

    with col2:

        app_garden = st.checkbox(
            "Van saját, biztonságos kertem",
            key="live_garden"
        )

        app_kids = st.checkbox(
            "Van kisgyermek a családban",
            key="live_kids"
        )

        app_exp = st.checkbox(
            "Tapasztalt kutyatartó vagyok",
            key="live_exp"
        )

    if st.button(
        "🔍 Hozzám illő kutyák keresése",
        type="primary",
        use_container_width=True
    ):

        try:

            dogs = get_all_dogs()

            if not dogs:

                st.info(
                    "Jelenleg nincs feltöltött kutya."
                )

                return

            matches = find_matches(
                dogs,
                app_housing,
                app_work,
                app_garden,
                app_kids,
                app_exp
            )

            st.subheader(
                f"✨ Riport: "
                f"{app_name.strip() or 'Jelentkező'} részére"
            )

            display_matches(matches)

        except Exception as e:

            st.error(
                f"Keresési hiba: {e}"
            )


# =====================================================
# 13. DEMÓ MÓD
# =====================================================

def render_demo_tab():

    st.header(
        "🧪 Interaktív Demó Mód"
    )

    st.info(
        "A demó kutyák csak az aktuális munkamenetben jelennek meg."
    )

    with st.expander(
        "➕ Próbakutya feltöltése",
        expanded=True
    ):

        with st.form(
            "demo_form",
            clear_on_submit=True
        ):

            name = st.text_input(
                "Tesztkutya neve"
            )

            shelter = st.text_input(
                "Szervezet neve",
                "Teszt Menhely"
            )

            contact = st.text_input(
                "Elérhetőség",
                "+36 20 111 2222"
            )

            size = st.selectbox(
                "Kutya mérete",
                (
                    "Kicsi (S)",
                    "Közepes (M)",
                    "Nagy (L)"
                )
            )

            energy = st.slider(
                "Energiaszint",
                1, 5, 3
            )

            image_file = st.file_uploader(
                "Kutya fotója",
                type=["jpg", "jpeg", "png"],
                key="demo_image"
            )

            garden = st.checkbox(
                "Kizárólag kertes házba költözhet"
            )

            kids = st.checkbox(
                "Gyerekbarát"
            )

            exp = st.checkbox(
                "Tapasztalt gazdit igényel"
            )

            submitted = st.form_submit_button(
                "🧪 Próbakutya hozzáadása"
            )

        if submitted:

            if not name.strip():

                st.error(
                    "Add meg a kutya nevét!"
                )

            else:

                try:

                    image_data = process_image(
                        image_file
                    )

                    st.session_state.demo_dogs.insert(
                        0,
                        {
                            "id": None,
                            "name": name.strip(),
                            "size": size,
                            "energy_level": energy,
                            "needs_garden": garden,
                            "kid_friendly": kids,
                            "experience_required": exp,
                            "shelter_name": shelter.strip() or "Nincs megadva",
                            "shelter_contact": contact.strip() or "Nincs megadva",
                            "image_data": image_data
                        }
                    )

                    st.success(
                        f"{name} sikeresen hozzáadva!"
                    )

                except Exception as e:

                    st.error(
                        f"Feltöltési hiba: {e}"
                    )

    st.divider()

    st.subheader(
        "🔍 Demó párosítás"
    )

    col1, col2 = st.columns(2)

    with col1:

        housing = st.selectbox(
            "Gazdi lakóhelye",
            ("Lakás", "Kertes ház"),
            key="demo_housing"
        )

        work = st.slider(
            "Napi távol töltött órák",
            0, 12, 4,
            key="demo_work"
        )

    with col2:

        garden = st.checkbox(
            "Van saját kertje",
            key="demo_garden"
        )

        kids = st.checkbox(
            "Van kisgyermeke",
            key="demo_kids"
        )

        exp = st.checkbox(
            "Tapasztalt kutyatartó",
            key="demo_exp"
        )

    if st.button(
        "🚀 Demó párosítás indítása",
        type="primary",
        use_container_width=True
    ):

        matches = find_matches(
            st.session_state.demo_dogs,
            housing,
            work,
            garden,
            kids,
            exp
        )

        display_matches(matches)
# =====================================================
# 14. ADMIN BEJELENTKEZÉS
# =====================================================

def render_admin_login():

    password = st.secrets.get(
        "OWNER_ADMIN_PASSWORD",
        ""
    )

    if not password:

        st.session_state.admin_logged_in = False
        st.error(
            "Nincs beállítva az OWNER_ADMIN_PASSWORD titok!"
        )

        return False

    with st.form("admin_login_form"):

        password_input = st.text_input(
            "Tulajdonosi adminjelszó",
            type="password"
        )

        submitted = st.form_submit_button(
            "🔓 Bejelentkezés"
        )

    if submitted:

        if password_input and hmac.compare_digest(
            password_input,
            password
        ):

            st.session_state.admin_logged_in = True
            st.session_state.owner_auth_fingerprint = hashlib.sha256(password.encode("utf-8")).hexdigest()
            st.rerun()

        else:

            st.error("Hibás jelszó!")

    return st.session_state.get(
        "admin_logged_in",
        False
    )


# =====================================================
# 15. MENHELYI ADMINISZTRÁCIÓ
# =====================================================

def render_admin_tab():

    st.header(
        "🔐 Tulajdonosi admin"
    )

    if not st.session_state.get(
        "admin_logged_in",
        False
    ):

        render_admin_login()
        return

    col1, col2 = st.columns((4, 1))

    with col1:

        st.success(
            "🔓 Sikeres bejelentkezés!"
        )

    with col2:

        if st.button("Kilépés"):

            st.session_state.admin_logged_in = False
            st.session_state.pop("owner_auth_fingerprint", None)
            st.rerun()

    st.subheader(
        "➕ Új kutya felvétele"
    )

    with st.form(
        "admin_dog_form",
        clear_on_submit=True
    ):

        name = st.text_input(
            "Kutya neve"
        )

        shelter = st.text_input(
            "Menhely neve"
        )

        contact = st.text_input(
            "Elérhetőség"
        )

        size = st.selectbox(
            "Kutya mérete",
            (
                "Kicsi (S)",
                "Közepes (M)",
                "Nagy (L)"
            )
        )

        energy = st.slider(
            "Energiaszint",
            1, 5, 3
        )

        image_file = st.file_uploader(
            "Kutya fotója",
            type=["jpg", "jpeg", "png"],
            key="admin_image"
        )

        garden = st.checkbox(
            "Kizárólag kertes házba költözhet"
        )

        kids = st.checkbox(
            "Gyerekbarát"
        )

        exp = st.checkbox(
            "Tapasztalt gazdit igényel"
        )

        submitted = st.form_submit_button(
            "💾 Kutya mentése",
            use_container_width=True
        )

    if submitted:

        if not name.strip():

            st.error(
                "Add meg a kutya nevét!"
            )

        else:

            try:

                image_data = process_image(
                    image_file
                )

                save_dog(
                    name.strip(),
                    size,
                    energy,
                    garden,
                    kids,
                    exp,
                    shelter.strip(),
                    contact.strip(),
                    image_data
                )

                st.success(
                    f"{name} sikeresen elmentve!"
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Mentési hiba: {e}"
                )

    st.divider()

    st.subheader(
        "🐾 Feltöltött kutyák"
    )

    try:

        dogs = get_all_dogs()

    except Exception as e:

        st.error(
            f"Adatbázis hiba: {e}"
        )

        return

    if not dogs:

        st.info(
            "Nincs még feltöltött kutya."
        )

        return

    for dog in dogs:

        with st.container(border=True):

            col1, col2 = st.columns((3, 1))

            with col1:

                st.write(
                    f"🐾 **{dog['name']}**"
                )

                st.caption(
                    f"{dog['shelter_name']} | {dog['size']}"
                )

            with col2:

                if st.button(
                    "🗑️ Törlés",
                    key=f"delete_{dog['id']}"
                ):

                    st.session_state.confirm_delete = dog["id"]

            if st.session_state.get(
                "confirm_delete"
            ) == dog["id"]:

                st.warning(
                    f"Biztosan törlöd {dog['name']} adatlapját?"
                )

                yes, no = st.columns(2)

                with yes:

                    if st.button(
                        "Igen, törlés",
                        key=f"confirm_{dog['id']}"
                    ):

                        try:

                            deleted = delete_dog(
                                dog["id"]
                            )

                            st.session_state.confirm_delete = None

                            if deleted:

                                st.success(
                                    "Kutya sikeresen törölve!"
                                )

                            else:

                                st.warning(
                                    "A kutya már nem található."
                                )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Törlési hiba: {e}"
                            )

                with no:

                    if st.button(
                        "Mégsem",
                        key=f"cancel_{dog['id']}"
                    ):

                        st.session_state.confirm_delete = None
                        st.rerun()



# =====================================================
# MENHELYI FIÓKOK – REGISZTRÁCIÓ ÉS JÓVÁHAGYÁS
# =====================================================

def init_shelter_accounts():
    # Külön tábla: a meglévő dogs tábla nem módosul.
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shelter_accounts (
                    id SERIAL PRIMARY KEY,
                    shelter_name TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT,
                    password_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)



def init_shelter_dog_ownership():
    """Existing dogs stay unassigned (NULL); only new shelter uploads get an owner."""
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE dogs
                ADD COLUMN IF NOT EXISTS shelter_account_id INTEGER
                REFERENCES shelter_accounts(id) ON DELETE RESTRICT
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_dogs_shelter_account_id
                ON dogs (shelter_account_id)
            """)



def get_approved_shelter(account_id):
    if not isinstance(account_id, int) or isinstance(account_id, bool):
        return None

    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE shelter_accounts
                SET plan = 'free',
                    plus_expires_at = NULL
                WHERE id = %s
                  AND plan = 'plus'
                  AND plus_expires_at IS NOT NULL
                  AND plus_expires_at <= NOW()
            """, (account_id,))

            conn.commit()

            cursor.execute("""
                SELECT id, shelter_name,
                       COALESCE(NULLIF(phone, ''), email),
                       plan, plus_expires_at
                FROM shelter_accounts
                WHERE id = %s
                  AND status = 'approved'
            """, (account_id,))

            return cursor.fetchone()



def get_shelter_dogs(account_id):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT d.id, d.name, d.size, d.energy_level,
                       d.needs_garden, d.kid_friendly, d.experience_required,
                       d.shelter_name, d.shelter_contact, d.image_data
                FROM dogs AS d
                JOIN shelter_accounts AS s ON s.id = d.shelter_account_id
                WHERE s.id = %s AND s.status = 'approved'
                ORDER BY d.id DESC
            """, (account_id,))
            return [dict(zip((
                'id', 'name', 'size', 'energy_level', 'needs_garden',
                'kid_friendly', 'experience_required', 'shelter_name',
                'shelter_contact', 'image_data'), row)) for row in cursor.fetchall()]


def save_shelter_dog(account_id, name, size, energy, garden, kids, exp, image_data):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO dogs
                    (name, size, energy_level, needs_garden, kid_friendly,
                     experience_required, shelter_name, shelter_contact,
                     image_data, shelter_account_id)
                SELECT %s, %s, %s, %s, %s, %s,
                       s.shelter_name, COALESCE(NULLIF(s.phone, ''), s.email),
                       %s, s.id
                FROM shelter_accounts AS s
                WHERE s.id = %s AND s.status = 'approved'
                RETURNING id
            """, (name, size, energy, garden, kids, exp, image_data, account_id))
            return cursor.fetchone() is not None


def update_shelter_dog(account_id, dog_id, name, size, energy, garden, kids, exp,
                       new_image_data=None):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE dogs AS d
                SET name = %s, size = %s, energy_level = %s,
                    needs_garden = %s, kid_friendly = %s,
                    experience_required = %s,
                    image_data = COALESCE(%s, d.image_data)
                WHERE d.id = %s AND d.shelter_account_id = %s
                  AND EXISTS (
                      SELECT 1 FROM shelter_accounts AS s
                      WHERE s.id = %s AND s.status = 'approved'
                  )
            """, (name, size, energy, garden, kids, exp, new_image_data,
                  dog_id, account_id, account_id))
            return cursor.rowcount == 1


def delete_shelter_dog(account_id, dog_id):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM dogs AS d
                WHERE d.id = %s AND d.shelter_account_id = %s
                  AND EXISTS (
                      SELECT 1 FROM shelter_accounts AS s
                      WHERE s.id = %s AND s.status = 'approved'
                  )
            """, (dog_id, account_id, account_id))
            return cursor.rowcount == 1

def set_shelter_dog_featured(account_id, dog_id, featured):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, plan,
                       plus_expires_at > NOW()
                FROM shelter_accounts
                WHERE id = %s
                FOR UPDATE
            """, (account_id,))

            account = cursor.fetchone()

            if not account or account[0] != 'approved':
                return False

            if featured:
                if account[1] != 'plus' or not account[2]:
                    return False

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM dogs
                    WHERE shelter_account_id = %s
                    AND is_featured = TRUE
                    AND id <> %s
                """, (account_id, dog_id))

                if cursor.fetchone()[0] >= 5:
                    return False

            cursor.execute("""
                UPDATE dogs
                SET is_featured = %s
                WHERE id = %s
                AND shelter_account_id = %s
            """, (featured, dog_id, account_id))

            return cursor.rowcount == 1
def hash_shelter_password(password):
    salt = os.urandom(16)
    iterations = 600000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_shelter_password(password, stored):
    try:
        algorithm, count, salt_hex, digest_hex = stored.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        candidate = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), int(count)
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False

def change_shelter_password(account_id, old_password, new_password):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT password_hash
                FROM shelter_accounts
                WHERE id = %s AND status = 'approved'
                FOR UPDATE
            """, (account_id,))

            account = cursor.fetchone()

            if not account:
                return False

            if not verify_shelter_password(old_password, account[0]):
                return False

            new_hash = hash_shelter_password(new_password)

            cursor.execute("""
                UPDATE shelter_accounts
                SET password_hash = %s
                WHERE id = %s AND status = 'approved'
            """, (new_hash, account_id))

            conn.commit()
            return cursor.rowcount == 1
def register_shelter(shelter, contact, email, phone, password):
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO shelter_accounts
                    (shelter_name, contact_name, email, phone, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
            """, (shelter, contact, email, phone or None, hash_shelter_password(password)))
            return cursor.fetchone() is not None


def render_shelter_registration():
    st.header('🐾 Menhelyi regisztráció')
    st.info('A fiók csak a központi admin jóváhagyása után használható.')
    with st.form('shelter_registration_form', clear_on_submit=True):
        shelter = st.text_input('Menhely vagy szervezet neve *', max_chars=200)
        contact = st.text_input('Kapcsolattartó neve *', max_chars=200)
        email = st.text_input('E-mail-cím *', max_chars=254)
        phone = st.text_input('Telefonszám (nem kötelező)', max_chars=50)
        password = st.text_input('Jelszó (legalább 12 karakter) *', type='password')
        confirm = st.text_input('Jelszó megerősítése *', type='password')
        submit = st.form_submit_button('Jelentkezés elküldése')
    if submit:
        email = email.strip().lower()
        if not shelter.strip() or not contact.strip() or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            st.error('Add meg a szervezet nevét, a kapcsolattartót és egy érvényes e-mail-címet.')
        elif len(password) < 12 or password != confirm:
            st.error('A jelszavaknak egyezniük kell, és legalább 12 karakter hosszúnak kell lenniük.')
        else:
            try:
                created = register_shelter(shelter.strip(), contact.strip(), email, phone.strip(), password)
                if created:
                    st.success('Jelentkezés rögzítve. A fiók jóváhagyásra vár.')
                else:
                    st.warning('Ezzel az e-mail-címmel már létezik jelentkezés.')
            except Exception:
                st.error('A regisztráció most nem sikerült. Kérjük, próbáld újra később.')


def render_shelter_login():
    st.header('🔑 Menhelyi belépés')
    account_id = st.session_state.get('shelter_account_id')
    if account_id:
        try:
            account = get_approved_shelter(account_id)
        except Exception:
            st.error('A menhelyi fiók ellenőrzése jelenleg nem sikerült.')
            return
        if not account:
            st.session_state.shelter_account_id = None
            st.warning('A menhelyi fiók már nem aktív. Jelentkezz be újra.')
            return
        st.success(f'Sikeres menhelyi bejelentkezés: {account[1]}')
        if st.button('Menhelyi kijelentkezés'):
            st.session_state.shelter_account_id = None
            st.rerun()
        with st.expander("🔑 Jelszó módosítása"):
            with st.form("change_shelter_password_form"):
                old_password = st.text_input(
                    "Jelenlegi jelszó", type="password"
                )
                new_password = st.text_input(
                    "Új jelszó (legalább 12 karakter)", type="password"
                )
                confirm_password = st.text_input(
                    "Új jelszó megerősítése", type="password"
                )
                change_submit = st.form_submit_button("🔑 Jelszó módosítása")

                if change_submit:
                    if len(new_password) < 12:
                        st.error("Az új jelszónak legalább 12 karakteresnek kell lennie.")
                    elif new_password != confirm_password:
                        st.error("Az új jelszavak nem egyeznek.")
                    elif not old_password:
                        st.error("Add meg a jelenlegi jelszavadat.")
                    else:
                        try:
                            changed = change_shelter_password(
                                account_id, old_password, new_password
                            )
                            if changed:
                                st.success("A jelszó sikeresen megváltozott!")
                            else:
                                st.error("A jelenlegi jelszó hibás.")
                        except Exception:
                            st.error("A jelszómódosítás jelenleg nem sikerült.")

        render_shelter_dog_management(account)
        return
    with st.form('shelter_login_form'):
        email = st.text_input('Regisztrált e-mail-cím')
        password = st.text_input('Jelszó', type='password')
        submit = st.form_submit_button('Belépés')
    if submit:
        try:
            with database_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT id, password_hash, status FROM shelter_accounts WHERE email = %s', (email.strip().lower(),))
                    account = cursor.fetchone()
            if not account or not verify_shelter_password(password, account[1]):
                st.error('Hibás e-mail-cím vagy jelszó.')
            elif account[2] != 'approved':
                st.warning('A fiók még nem kapott jóváhagyást, vagy elutasításra került.')
            else:
                st.session_state.shelter_account_id = account[0]
                st.rerun()
        except Exception:
            st.error('A bejelentkezés jelenleg nem érhető el.')

def render_shelter_dog_management(account):
    account_id, shelter_name, contact, plan, plus_expires_at = account

    from datetime import datetime, timezone

    plus_active = (
        plan == 'plus'
        and plus_expires_at is not None
        and plus_expires_at > datetime.now(timezone.utc)
    )

    if plus_active:
        st.success("⭐ Aktív előfizetés: Menhely Plusz")
        st.info(
            f"📅 Előfizetés lejárata: "
            f"{plus_expires_at.strftime('%Y.%m.%d.')}"
        )
    else:
        st.info("🐾 Jelenlegi csomag: Ingyenes")
    st.subheader('🐾 Saját kutyáim')
    st.caption('Csak az ehhez a menhelyi fiókhoz tartozó kutyák jelennek meg itt. '
               'A korábban feltöltött, fiókhoz nem rendelt kutyák változatlanok maradnak.')

    with st.expander('➕ Új kutya feltöltése', expanded=True):
        with st.form('shelter_new_dog_form', clear_on_submit=True):
            name = st.text_input('Kutya neve *', max_chars=200, key='shelter_new_name')
            st.text_input('Menhely neve', value=shelter_name, disabled=True)
            st.text_input('Kapcsolat', value=contact, disabled=True)
            size = st.selectbox('Kutya mérete', ('Kicsi (S)', 'Közepes (M)', 'Nagy (L)'), key='shelter_new_size')
            energy = st.slider('Energiaszint', 1, 5, 3, key='shelter_new_energy')
            garden = st.checkbox('Kizárólag kertes házba költözhet', key='shelter_new_garden')
            kids = st.checkbox('Gyerekbarát', key='shelter_new_kids')
            exp = st.checkbox('Tapasztalt gazdit igényel', key='shelter_new_exp')
            image_file = st.file_uploader('Kutya fotója', type=['jpg', 'jpeg', 'png'], key='shelter_new_image')
            submitted = st.form_submit_button('💾 Kutya mentése')
        if submitted:
            if not name.strip():
                st.error('Add meg a kutya nevét!')
            else:
                try:
                    image_data = process_image(image_file)
                    if save_shelter_dog(account_id, name.strip(), size, energy,
                                        garden, kids, exp, image_data):
                        st.success('A kutya sikeresen elmentve!')
                        st.rerun()
                    else:
                        st.error('A menhelyi fiók nem jogosult a feltöltésre.')
                except Exception as exc:
                    st.error('A mentés nem sikerült. Kérjük, próbáld újra később.')

    try:
        dogs = get_shelter_dogs(account_id)
    except Exception as exc:
        st.error('A saját kutyák lekérése nem sikerült.')
        return
    if not dogs:
        st.info('Még nem töltöttél fel kutyát ezzel a menhelyi fiókkal.')
        return

    for dog in dogs:
        dog_id = dog['id']
        with st.expander(f"🐕 {dog['name']} (#{dog_id})"):
            existing_image = decode_image(dog.get('image_data'))
            if existing_image:
                st.image(existing_image, width=220)
            with st.form(f'shelter_edit_form_{dog_id}'):
                name = st.text_input('Kutya neve', value=dog['name'], max_chars=200,
                                     key=f'shelter_edit_name_{dog_id}')
                sizes = ('Kicsi (S)', 'Közepes (M)', 'Nagy (L)')
                size = st.selectbox('Kutya mérete', sizes,
                                    index=sizes.index(dog['size']) if dog['size'] in sizes else 1,
                                    key=f'shelter_edit_size_{dog_id}')
                energy = st.slider('Energiaszint', 1, 5,
                                   int(dog['energy_level']) if dog['energy_level'] in range(1, 6) else 3,
                                   key=f'shelter_edit_energy_{dog_id}')
                garden = st.checkbox('Kizárólag kertes házba költözhet',
                                     value=bool(dog['needs_garden']), key=f'shelter_edit_garden_{dog_id}')
                kids = st.checkbox('Gyerekbarát', value=bool(dog['kid_friendly']),
                                   key=f'shelter_edit_kids_{dog_id}')
                exp = st.checkbox('Tapasztalt gazdit igényel',
                                  value=bool(dog['experience_required']), key=f'shelter_edit_exp_{dog_id}')
                new_image = st.file_uploader('Új fotó (nem kötelező; a régi megmarad)',
                                             type=['jpg', 'jpeg', 'png'],
                                             key=f'shelter_edit_image_{dog_id}')
                submitted = st.form_submit_button('💾 Módosítások mentése')
            if submitted:
                if not name.strip():
                    st.error('Add meg a kutya nevét!')
                else:
                    try:
                        new_image_data = process_image(new_image)
                        updated = update_shelter_dog(account_id, dog_id, name.strip(), size,
                                                     energy, garden, kids, exp, new_image_data)
                        if updated:
                            st.success('A kutya adatai frissültek.')
                            st.rerun()
                        else:
                            st.error('A kutya nem található a saját fiókodban, vagy nincs jogosultságod.')
                    except Exception as exc:
                        st.error('A módosítás nem sikerült.')
            st.markdown("**⭐ Kiemelt gazdikereső**")

            if not plus_active:
                st.button(
                    "🔒 Kutya kiemelése",
                    key=f"featured_locked_{dog_id}",
                    disabled=True
                )
                st.caption(
                    "Ez a funkció a Menhely Plusz csomagban érhető el."
                )
            else:
                try:
                    with database_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                SELECT is_featured
                                FROM dogs
                                WHERE id = %s
                                AND shelter_account_id = %s
                            """, (dog_id, account_id))
                            result = cursor.fetchone()

                    if result is not None:
                        featured = bool(result[0])

                        if featured:
                            st.success("⭐ Kiemelt kutya")

                        label = (
                            "Kiemelés megszüntetése"
                            if featured
                            else "⭐ Kutya kiemelése"
                        )

                        if st.button(
                            label,
                            key=f"featured_toggle_{dog_id}"
                        ):
                            if set_shelter_dog_featured(
                                account_id, dog_id, not featured
                            ):
                                st.rerun()
                            else:
                                st.warning(
                                    "A kiemelés nem módosítható. "
                                    "Maximum 5 kiemelt kutya engedélyezett, "
                                    "aktív Plusz előfizetéssel."
                                )

                except Exception:
                    st.error("A kiemelés kezelése nem sikerült.")
            confirm = st.checkbox('Biztosan törölni szeretném ezt a kutyát',
                                  key=f'shelter_confirm_delete_{dog_id}')
            if st.button('🗑️ Saját kutya törlése', key=f'shelter_delete_{dog_id}',
                         disabled=not confirm):
                try:
                    if delete_shelter_dog(account_id, dog_id):
                        st.success('A kutya törölve.')
                        st.rerun()
                    else:
                        st.error('A kutya nem törölhető ebből a menhelyi fiókból.')
                except Exception as exc:
                    st.error('A törlés nem sikerült.')


def render_shelter_approvals():
    st.header('🛡️ Menhelyek jóváhagyása')
    # Jóváhagyást kizárólag a tulajdonosi admin végezhet.
    if not st.session_state.get('admin_logged_in', False):
        st.info('A jóváhagyáshoz először jelentkezz be a Tulajdonosi admin fülön.')
        return
    try:
        with database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, shelter_name, contact_name, email, phone, created_at
                    FROM shelter_accounts WHERE status = 'pending'
                    ORDER BY created_at ASC
                """)
                pending = cursor.fetchall()
    except Exception:
        st.error('A jelentkezések lekérése nem sikerült.')
        return
    if not pending:
        st.info('Jelenleg nincs jóváhagyásra váró menhely.')
    for account_id, shelter, contact, email, phone, created in pending:
        with st.container(border=True):
            st.subheader(shelter)
            st.write(f'Kapcsolattartó: {contact}')
            st.write(f'E-mail: {email}')
            st.write(f'Telefon: {phone or "Nincs megadva"}')
            st.caption(f'Jelentkezés: {created:%Y-%m-%d %H:%M}')
            decision = st.radio('Döntés', ['Még nem döntöttem', 'Jóváhagyás', 'Elutasítás'], key=f'decision_{account_id}')
            if st.button('Döntés mentése', key=f'save_decision_{account_id}'):
                if not st.session_state.get('admin_logged_in', False):
                    st.error('Nincs tulajdonosi jogosultság.')
                    return
                status = {'Jóváhagyás': 'approved', 'Elutasítás': 'rejected'}.get(decision)
                if not status:
                    st.warning('Válassz jóváhagyást vagy elutasítást.')
                else:
                    try:
                        with database_connection() as conn:
                            with conn.cursor() as cursor:
                            
                                cursor.execute("""
                        UPDATE shelter_accounts
                        SET status = %s,
                            plan = CASE
                                WHEN %s = 'approved' AND plus_expires_at IS NULL
                                THEN 'plus'
                                ELSE plan
                            END,
                            plus_expires_at = CASE
                                WHEN %s = 'approved' AND plus_expires_at IS NULL
                                THEN NOW() + INTERVAL '30 days'
                                ELSE plus_expires_at
                            END
                        WHERE id = %s AND status = 'pending'
                    """, (status, status, status, account_id))

                        st.rerun()
                    except Exception:
                        st.error('A döntés mentése nem sikerült.')




def render_shelter_plus_admin():
    st.subheader("⭐ Menhely Plusz kezelése")

    if not st.session_state.get("admin_logged_in", False):
        st.warning("Ehhez tulajdonosi bejelentkezés szükséges.")
        return

    try:
        with database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, shelter_name, email, plan, plus_expires_at
                    FROM shelter_accounts
                    WHERE status = 'approved'
                    ORDER BY shelter_name
                """)
                shelters = cursor.fetchall()
    except Exception:
        st.error("A menhelyek lekérdezése nem sikerült.")
        return

    if not shelters:
        st.info("Jelenleg nincs jóváhagyott menhely.")
        return

    for account_id, name, email, plan, expires_at in shelters:
        with st.container(border=True):
            st.write(f"**{name}**")
            st.caption(f"📧 E-mail: {email}")
            active = (
                plan == "plus"
                and expires_at is not None
                and expires_at > datetime.now(timezone.utc)
            )

            if active:
                st.success(f"Plusz aktív eddig: {expires_at:%Y-%m-%d}")
            else:
                st.info("Ingyenes csomag")

            if st.button(
                "⭐ 30 napos Plusz aktiválása",
                key=f"activate_plus_{account_id}"
            ):
                try:
                    with database_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE shelter_accounts
                                SET plan = 'plus',
                                    plus_expires_at =
                                        NOW() + INTERVAL '30 days'
                                WHERE id = %s
                                  AND status = 'approved'
                            """, (account_id,))
                    st.success("A 30 napos Plusz aktiválva!")
                    st.rerun()
                except Exception:
                    st.error("Az aktiválás nem sikerült.")

def expire_shelter_plus():
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE shelter_accounts
                SET plan = 'free'
                WHERE plan = 'plus'
                  AND plus_expires_at IS NOT NULL
                  AND plus_expires_at <= NOW()
            """)

# =====================================================
# 16. FŐPROGRAM
# =====================================================

def main():
    expire_shelter_plus()
    if "demo_dogs" not in st.session_state:
        st.session_state.demo_dogs = []

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    owner_secret = st.secrets.get("OWNER_ADMIN_PASSWORD", "")
    owner_fingerprint = hashlib.sha256(owner_secret.encode("utf-8")).hexdigest() if owner_secret else None
    if st.session_state.get("admin_logged_in") and (
        not owner_fingerprint or st.session_state.get("owner_auth_fingerprint") != owner_fingerprint
    ):
        st.session_state.admin_logged_in = False

    if "confirm_delete" not in st.session_state:
        st.session_state.confirm_delete = None

    st.title(
        "🐶 Gazdikereső"
    )

    st.subheader(
        "Találd meg a hozzád legjobban illő négylábú társat!"
    )

    st.write(
        "Segítünk összekötni a gazdijelölteket "
        "a szerető otthonra váró kutyákkal."
    )

    try:

        init_database()

    except Exception as e:

        st.error(
            f"Az adatbázis nem érhető el: {e}"
        )

        st.info(
            "Ellenőrizd a DB_URL beállítását "
            "és az adatbázis elérhetőségét."
        )

        return

    try:
        init_shelter_accounts()
        init_shelter_dog_ownership()
        expire_shelter_plus()
    except Exception:
        st.error("A menhelyi fiókok és a kutyák adatbázisa nem érhető el.")
        return
   
    

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 Kutyakereső",
        "🧪 Demó mód",
        "🔐 Tulajdonosi admin",
        "📝 Menhelyi regisztráció",
        "🔑 Menhelyi belépés",
        "🛡️ Jóváhagyások"
    ])

    with tab1:

        render_live_search()

    with tab2:

        render_demo_tab()

    with tab3:

        render_admin_tab()

    with tab4:
        render_shelter_registration()

    with tab5:
        render_shelter_login()

    with tab6:
        render_shelter_approvals()
        
        render_shelter_plus_admin()



# =====================================================
# 17. PROGRAM INDÍTÁSA
# =====================================================

if __name__ == "__main__":

    main()
