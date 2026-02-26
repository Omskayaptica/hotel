import streamlit as st
import psycopg2
import pandas as pd
from datetime import date, timedelta
from contextlib import contextmanager

# ============================================================
#  КОНФИГУРАЦИЯ
# ============================================================
st.set_page_config(
    page_title="Hotel Booking System",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Кастомные стили
st.markdown("""
<style>
    /* Основной фон и шрифт */
    .main { background-color: #f8f9fb; }
    
    /* Карточки метрик */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    [data-testid="stMetric"] * {
        color: #1a1a2e !important;
    }
    [data-testid="stMetricValue"] {
        color: #1a1a2e !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #4a5568 !important;
    }
    
    /* Заголовок страницы */
    .page-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: white;
        padding: 28px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .page-header h1 { color: white; margin: 0; font-size: 2rem; }
    .page-header p  { color: #a0aec0; margin: 4px 0 0; font-size: 0.95rem; }

    /* Бейдж статуса */
    .badge-free     { background:#d4f4dd; color:#1a7f37; padding:3px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
    .badge-occupied { background:#fde8e8; color:#c0392b; padding:3px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }

    /* Кнопки */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    div[data-testid="stSidebar"] {
        background: #1a1a2e;
    }
    div[data-testid="stSidebar"] > div > div > div * { color: #e2e8f0 !important; }
    div[data-testid="stSidebar"] .stSelectbox label { color: #a0aec0 !important; }
    /* Не даём сайдбару перекрывать основной контент */
    section.main * { color: inherit; }
</style>
""", unsafe_allow_html=True)

DB_CONFIG = dict(
    dbname="hotel_db",
    user="postgres",
    password="1111",   # ← вынесите в .env / st.secrets в продакшене
    host="localhost",
    port="5432",
)

# ============================================================
#  ПОДКЛЮЧЕНИЕ К БД
# ============================================================
@contextmanager
def get_db():
    """Контекстный менеджер: соединение гарантированно закрывается."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_query(sql: str, params=None) -> pd.DataFrame:
    with get_db() as conn:
        return pd.read_sql(sql, conn, params=params)


def run_procedure(sql: str, params=None):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)

# ============================================================
#  ХЕЛПЕРЫ
# ============================================================
def status_badge(status: str) -> str:
    cls = "badge-free" if status == "Свободен" else "badge-occupied"
    return f'<span class="{cls}">{status}</span>'

# ============================================================
#  САЙДБАР
# ============================================================
with st.sidebar:
    st.markdown("## 🏨 Hotel System")
    st.markdown("---")
    menu_options = {
        "📊 Дашборд":            "dashboard",
        "🛏️ Обзор номеров":      "rooms",
        "📅 Забронировать":       "book",
        "👤 Регистрация гостя":  "guest",
        "📋 Бронирования":        "bookings",
        "🕓 История":             "history",
    }
    choice_label = st.selectbox("Раздел", list(menu_options.keys()), label_visibility="collapsed")
    choice = menu_options[choice_label]
    st.markdown("---")
    st.caption("Система управления отелем v2.0")

# ============================================================
#  ДАШБОРД
# ============================================================
if choice == "dashboard":
    st.markdown("""
    <div class="page-header">
        <h1>🏨 Панель управления</h1>
        <p>Добро пожаловать в систему бронирования</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Метрики ---
    rooms_df    = run_query("SELECT status FROM room_status_view")
    bookings_df = run_query("SELECT status, total_cost FROM bookings")

    total_rooms    = len(rooms_df)
    occupied_rooms = (rooms_df["status"] == "Занят").sum()
    free_rooms     = total_rooms - occupied_rooms
    active_bookings = (bookings_df["status"] == "active").sum()
    revenue = bookings_df.loc[bookings_df["status"] == "active", "total_cost"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🛏️ Всего номеров",     total_rooms)
    c2.metric("✅ Свободно",          free_rooms)
    c3.metric("🔴 Занято",            occupied_rooms)
    c4.metric("💰 Выручка (активные)", f"{revenue:,.0f} ₽")

    st.markdown("---")

    col1, col2 = st.columns(2)

    # График занятости
    with col1:
        st.subheader("Занятость номеров")
        occ_data = pd.DataFrame({
            "Статус": ["Свободен", "Занят"],
            "Кол-во": [free_rooms, occupied_rooms]
        })
        st.bar_chart(occ_data.set_index("Статус"), color=["#4CAF50"])

    # Выручка по типам номеров
    with col2:
        st.subheader("Выручка по типам номеров")
        rev_df = run_query("""
            SELECT rt.type_name, SUM(b.total_cost) AS выручка
            FROM bookings b
            JOIN rooms r ON b.room_id = r.room_id
            JOIN room_types rt ON r.type_id = rt.type_id
            WHERE b.status = 'active'
            GROUP BY rt.type_name
        """)
        if not rev_df.empty:
            st.bar_chart(rev_df.set_index("type_name"))
        else:
            st.info("Нет активных бронирований")

# ============================================================
#  ОБЗОР НОМЕРОВ
# ============================================================
elif choice == "rooms":
    st.markdown("""
    <div class="page-header">
        <h1>🛏️ Номерной фонд</h1>
        <p>Актуальный статус всех номеров</p>
    </div>
    """, unsafe_allow_html=True)

    df = run_query("SELECT room_number, type_name, price_per_night, status, free_from FROM room_status_view")

    # Фильтр
    filter_status = st.radio("Фильтр по статусу", ["Все", "Свободен", "Занят"], horizontal=True)
    if filter_status != "Все":
        df = df[df["status"] == filter_status]

    # Таблица с бейджами
    df["status_html"] = df["status"].apply(status_badge)
    df["price_per_night"] = df["price_per_night"].apply(lambda x: f"{x:,.0f} ₽")
    df["free_from"] = df["free_from"].fillna("—")

    st.dataframe(
        df[["room_number", "type_name", "price_per_night", "status", "free_from"]].rename(columns={
            "room_number":     "Номер",
            "type_name":       "Тип",
            "price_per_night": "Цена/ночь",
            "status":          "Статус",
            "free_from":       "Свободен с",
        }),
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
#  БРОНИРОВАНИЕ
# ============================================================
elif choice == "book":
    st.markdown("""
    <div class="page-header">
        <h1>📅 Новое бронирование</h1>
        <p>Оформите бронь для гостя</p>
    </div>
    """, unsafe_allow_html=True)

    rooms_df  = run_query("SELECT room_id, room_number, type_name, price_per_night, status FROM room_status_view")
    guests_df = run_query("SELECT guest_id, full_name FROM guests ORDER BY full_name")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Выбор номера")
        selected_room_no = st.selectbox(
            "Номер",
            rooms_df["room_number"].tolist(),
            format_func=lambda n: f"№{n} — {rooms_df[rooms_df['room_number']==n]['type_name'].values[0]}"
        )
        room_row = rooms_df[rooms_df["room_number"] == selected_room_no].iloc[0]
        r_id = int(room_row["room_id"])

        # Инфо о номере
        st.info(
            f"**Тип:** {room_row['type_name']}  \n"
            f"**Цена:** {room_row['price_per_night']:,.0f} ₽/ночь  \n"
            f"**Статус:** {room_row['status']}"
        )

        # Занятые периоды
        st.markdown("**📅 Занятые периоды:**")
        busy_df = run_query(
            "SELECT check_in, check_out FROM bookings WHERE room_id = %s AND status='active' AND check_out >= CURRENT_DATE ORDER BY check_in",
            params=(r_id,)
        )
        if busy_df.empty:
            st.success("Номер свободен на ближайшее время")
        else:
            for _, row in busy_df.iterrows():
                st.warning(f"🔴 {row['check_in']} → {row['check_out']}")

    with col2:
        st.subheader("Данные брони")
        with st.form("booking_form"):
            selected_guest = st.selectbox("Гость", guests_df["full_name"].tolist())
            date_in  = st.date_input("Дата заезда",  value=date.today(), min_value=date.today())
            date_out = st.date_input("Дата выезда",  value=date.today() + timedelta(days=1), min_value=date.today() + timedelta(days=1))

            # Предварительный расчёт стоимости
            if date_out > date_in:
                nights = (date_out - date_in).days
                cost   = nights * float(room_row["price_per_night"])
                st.metric("Предварительная стоимость", f"{cost:,.0f} ₽", f"{nights} ночей")

            submit = st.form_submit_button("✅ Подтвердить бронь", use_container_width=True)

            if submit:
                if date_out <= date_in:
                    st.error("Дата выезда должна быть позже даты заезда!")
                else:
                    try:
                        g_id = int(guests_df[guests_df["full_name"] == selected_guest]["guest_id"].values[0])
                        run_procedure("CALL make_booking(%s, %s, %s, %s)", (g_id, r_id, date_in, date_out))
                        st.success("🎉 Бронирование успешно оформлено!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

# ============================================================
#  РЕГИСТРАЦИЯ ГОСТЯ
# ============================================================
elif choice == "guest":
    st.markdown("""
    <div class="page-header">
        <h1>👤 Регистрация гостя</h1>
        <p>Добавьте нового гостя в систему</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        with st.form("guest_form"):
            name     = st.text_input("ФИО гостя")
            passport = st.text_input("Серия и номер паспорта")
            phone    = st.text_input("Номер телефона")
            submit   = st.form_submit_button("➕ Зарегистрировать", use_container_width=True)

            if submit:
                if not name or not passport:
                    st.error("ФИО и паспорт обязательны!")
                else:
                    try:
                        run_procedure(
                            "INSERT INTO guests (full_name, passport, phone) VALUES (%s, %s, %s)",
                            (name, passport, phone)
                        )
                        st.success(f"Гость **{name}** успешно зарегистрирован!")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

    with col2:
        st.subheader("Зарегистрированные гости")
        guests_df = run_query("SELECT full_name AS ФИО, passport AS Паспорт, phone AS Телефон FROM guests ORDER BY full_name")
        st.dataframe(guests_df, use_container_width=True, hide_index=True)

# ============================================================
#  ВСЕ БРОНИРОВАНИЯ + ОТМЕНА
# ============================================================
elif choice == "bookings":
    st.markdown("""
    <div class="page-header">
        <h1>📋 Активные бронирования</h1>
        <p>Управление текущими бронями</p>
    </div>
    """, unsafe_allow_html=True)

    df = run_query("""
        SELECT b.booking_id, g.full_name AS гость, r.room_number AS номер,
               b.check_in AS заезд, b.check_out AS выезд,
               b.total_cost AS стоимость, b.status AS статус
        FROM bookings b
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN rooms  r ON b.room_id  = r.room_id
        ORDER BY b.check_in DESC
    """)

    # Фильтр по статусу
    status_filter = st.radio("Статус", ["active", "cancelled", "Все"], horizontal=True)
    view_df = df if status_filter == "Все" else df[df["статус"] == status_filter]

    st.dataframe(view_df, use_container_width=True, hide_index=True)

    # Отмена бронирования
    st.markdown("---")
    st.subheader("❌ Отмена бронирования")
    active_df = df[df["статус"] == "active"]

    if active_df.empty:
        st.info("Нет активных бронирований для отмены.")
    else:
        booking_options = {
            f"#{row['booking_id']} — {row['гость']}, №{row['номер']} ({row['заезд']} → {row['выезд']})": row["booking_id"]
            for _, row in active_df.iterrows()
        }
        selected_label = st.selectbox("Выберите бронь для отмены", list(booking_options.keys()))
        if st.button("Отменить бронирование", type="primary"):
            try:
                run_procedure("CALL cancel_booking(%s)", (booking_options[selected_label],))
                st.success("Бронирование отменено.")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

# ============================================================
#  ИСТОРИЯ БРОНИРОВАНИЙ
# ============================================================
elif choice == "history":
    st.markdown("""
    <div class="page-header">
        <h1>🕓 История бронирований</h1>
        <p>Полный аудит всех действий</p>
    </div>
    """, unsafe_allow_html=True)

    df = run_query("""
        SELECT history_id AS id, booking_id, guest_name AS гость,
               room_number AS номер, check_in AS заезд, check_out AS выезд,
               total_cost AS стоимость, booking_status AS статус_брони,
               action AS действие, changed_at AS время
        FROM booking_history_view
    """)

    # Поиск по гостю
    search = st.text_input("🔍 Поиск по имени гостя")
    if search:
        df = df[df["гость"].str.contains(search, case=False, na=False)]

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Сводная статистика
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Всего действий в истории", len(df))
    with col2:
        if "действие" in df.columns:
            st.metric("Отменено бронирований", (df["действие"] == "cancelled").sum())