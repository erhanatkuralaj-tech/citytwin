import uuid

import math

from dataclasses import dataclass

from typing import Dict, List, Tuple, Optional
 
import streamlit as st

import folium

from streamlit_folium import st_folium
 
 
# -----------------------------

# Палитра объектов (панель слева)

# -----------------------------

PALETTE = [

    {"type": "Жилой комплекс", "emoji": "🏢", "hint": "Добавляет жителей и увеличивает поездки."},

    {"type": "Школа", "emoji": "🏫", "hint": "Лучше рядом с жильём и подальше от промзон."},

    {"type": "Парк", "emoji": "🌳", "hint": "Улучшает экологию и комфорт, особенно рядом с жильём."},

    {"type": "Спорткомплекс", "emoji": "🏟️", "hint": "Притягивает людей, лучше рядом с жильём и дорогами."},

    {"type": "Промышленный объект", "emoji": "🏭", "hint": "Даёт рабочие места, но ухудшает экологию рядом."},

    {"type": "Мост", "emoji": "🌉", "hint": "Улучшает связанность, полезен у “разрывов” маршрутов."},

]
 
DEFAULT_PARAMS = {

    "Жилой комплекс": {"residents": 1500},

    "Школа": {"capacity": 800},

    "Парк": {"green_factor": 0.25},

    "Спорткомплекс": {"visitors_per_day": 500},

    "Промышленный объект": {"emission": 120.0, "filters_eff": 0.0},

    "Мост": {"capacity_bonus": 200},

}
 
# Цвета/иконки маркеров (Folium)

MAP_STYLE = {

    "Школа": {"color": "blue", "fa": "graduation-cap"},

    "Жилой комплекс": {"color": "red", "fa": "home"},

    "Парк": {"color": "green", "fa": "tree"},

    "Спорткомплекс": {"color": "purple", "fa": "futbol"},

    "Промышленный объект": {"color": "gray", "fa": "industry"},

    "Мост": {"color": "orange", "fa": "road"},

}
 
# Центр Усть-Каменогорска (Өскемен)

DEFAULT_CENTER = (49.9483, 82.6285)
 
# Радиус анализа инфраструктуры вокруг точки (км)

ANALYSIS_RADIUS_KM = 1.5
 
 
# -----------------------------

# Data model

# -----------------------------

@dataclass

class CityObject:

    id: str

    obj_type: str

    lat: float

    lon: float

    params: Dict
 
 
def new_id() -> str:

    return uuid.uuid4().hex[:10]
 
 
def haversine_km(lat1, lon1, lat2, lon2) -> float:

    R = 6371.0

    p1, p2 = math.radians(lat1), math.radians(lat2)

    dphi = math.radians(lat2 - lat1)

    dl = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2

    return 2 * R * math.asin(math.sqrt(a))
 
 
def emoji_for_type(t: str) -> str:

    for item in PALETTE:

        if item["type"] == t:

            return item["emoji"]

    return "📍"
 
 
# -----------------------------

# Minimal UI styles

# -----------------------------

def inject_css():

    st.markdown(

        """
<style>

        .stApp { background: #fbfbfc; }
 
        .panel-card {

            background: white;

            border: 1px solid #eef0f4;

            border-radius: 14px;

            padding: 12px 12px;

            box-shadow: 0 4px 18px rgba(0,0,0,0.04);

            margin-bottom: 10px;

        }
 
        .muted { color: #6b7280; font-size: 13px; }
 
        .pm-box {

            background: #ffffff;

            border: 1px solid #eef0f4;

            border-radius: 14px;

            padding: 12px;

        }
 
        .pm-plus  { color: #0f766e; font-size: 13px; }

        .pm-minus { color: #9a3412; font-size: 13px; }
 
        .chip {

            display:inline-block; padding: 4px 8px; border-radius: 999px;

            border: 1px solid #eef0f4; background:#f9fafb; margin: 2px 4px 2px 0;

            font-size: 12px; color:#111827;

        }
</style>

        """,

        unsafe_allow_html=True

    )
 
 
# -----------------------------

# Location evaluation (pros/cons)

# -----------------------------

def evaluate_location(obj_type: str, lat: float, lon: float, objs: List[CityObject]) -> Tuple[List[str], List[str]]:

    plus, minus = [], []
 
    def nearest_dist(t: str):

        candidates = [o for o in objs if o.obj_type == t]

        if not candidates:

            return None

        return min(haversine_km(lat, lon, o.lat, o.lon) for o in candidates)
 
    near_home = nearest_dist("Жилой комплекс")

    near_school = nearest_dist("Школа")

    near_park = nearest_dist("Парк")

    near_ind = nearest_dist("Промышленный объект")
 
    if not objs:

        plus.append("Это первая точка — удобно начать моделирование с базы района.")

        return plus, minus
 
    if obj_type == "Жилой комплекс":

        if near_school is None:

            minus.append("Поблизости нет школ — возможна перегрузка инфраструктуры.")

        elif near_school <= 1.5:

            plus.append("Школа рядом — лучше доступность.")

        else:

            minus.append("Школа далеко — увеличится нагрузка на транспорт.")
 
        if near_park is not None and near_park <= 1.2:

            plus.append("Рядом парк — выше комфорт и качество среды.")

        else:

            minus.append("Нет парка рядом — стоит добавить зелёную зону.")
 
        if near_ind is not None and near_ind <= 2.0:

            minus.append("Слишком близко к промзоне — риск хуже по экологии.")

        else:

            plus.append("Далеко от промзоны — лучше по экологии.")
 
    elif obj_type == "Школа":

        if near_home is None:

            minus.append("Нет жилья рядом — школа может быть “в пустоте”.")

        elif near_home <= 1.5:

            plus.append("Рядом жильё — школа будет востребована и удобна.")

        else:

            minus.append("Жильё далеко — детям придётся ездить, вырастет трафик.")
 
        if near_ind is not None and near_ind <= 2.5:

            minus.append("Близко к промзоне — нежелательно для школьной среды.")

        else:

            plus.append("Подальше от промзоны — лучше для здоровья и комфорта.")
 
    elif obj_type == "Парк":

        if near_home is not None and near_home <= 1.5:

            plus.append("Рядом жильё — парк даст максимальную пользу жителям.")

        else:

            plus.append("Парк улучшит район, но рядом с жильём эффект сильнее.")
 
        if near_ind is not None and near_ind <= 2.0:

            plus.append("Рядом промзона — парк частично компенсирует влияние загрязнения.")

            minus.append("Но шум/выбросы всё равно могут ощущаться.")

        else:

            plus.append("Чистая зона — парк усилит комфорт и привлекательность.")
 
    elif obj_type == "Промышленный объект":

        if near_home is not None and near_home <= 3.0:

            minus.append("Близко к жилью — риски по экологии и жалобы жителей.")

        else:

            plus.append("Далеко от жилья — меньше конфликтов по экологии.")
 
        if near_school is not None and near_school <= 3.5:

            minus.append("Близко к школе — нежелательное соседство.")

        else:

            plus.append("Далеко от школ — лучше для социальной среды.")
 
        plus.append("Плюс: рабочие места и экономическая активность.")

        minus.append("Минус: ухудшает качество воздуха вокруг (если нет фильтров).")
 
    elif obj_type == "Спорткомплекс":

        if near_home is not None and near_home <= 2.0:

            plus.append("Рядом жильё — удобный доступ для посетителей.")

        else:

            minus.append("Далеко от жилья — посещаемость может быть ниже.")
 
        if near_park is not None and near_park <= 1.5:

            plus.append("Рядом парк — хорошая связка для спорта и отдыха.")

        else:

            plus.append("Можно дополнить рядом парком для комфорта.")
 
    elif obj_type == "Мост":

        plus.append("Мост улучшает связанность и снижает объезды.")

        minus.append("Если нет разрыва маршрутов, эффект может быть слабее (в MVP упрощено).")
 
    if not plus:

        plus.append("Расположение выглядит допустимым для MVP-модели.")

    return plus, minus
 
 
def analyze_perimeter(lat: float, lon: float, objs: List[CityObject], radius_km: float = ANALYSIS_RADIUS_KM) -> Dict:

    around = []

    for o in objs:

        d = haversine_km(lat, lon, o.lat, o.lon)

        if d <= radius_km:

            around.append((o, d))
 
    counts = {}

    for o, _d in around:

        counts[o.obj_type] = counts.get(o.obj_type, 0) + 1
 
    # Оставляем только то, что ты хотела: без “жителей” и “вместимость школ”

    industry_emission = sum(

        float(o.params.get("emission", 0)) * (1.0 - float(o.params.get("filters_eff", 0)))

        for o, _d in around

        if o.obj_type == "Промышленный объект"

    )

    parks = counts.get("Парк", 0)
 
    return {

        "around": sorted(around, key=lambda x: x[1]),

        "counts": counts,

        "industry_emission": industry_emission,

        "parks": parks,

        "radius_km": radius_km,

    }
 
 
# -----------------------------

# Map marker click -> select object

# -----------------------------

def find_object_by_latlon(lat: float, lon: float, objs: List[CityObject], eps: float = 0.00035) -> Optional[CityObject]:

    best = None

    best_d = 1e18

    for o in objs:

        d = (o.lat - lat) ** 2 + (o.lon - lon) ** 2

        if d < best_d:

            best_d = d

            best = o

    if best and best_d <= eps * eps:

        return best

    return None
 
 
# -----------------------------

# State

# -----------------------------

def init_state():

    if "objects" not in st.session_state:

        st.session_state.objects = []

    if "mode" not in st.session_state:

        st.session_state.mode = "Добавить"

    if "palette_selected" not in st.session_state:

        st.session_state.palette_selected = "Жилой комплекс"

    if "selected_id" not in st.session_state:

        st.session_state.selected_id = None

    if "last_click" not in st.session_state:

        st.session_state.last_click = None

    if "map_selected_id" not in st.session_state:

        st.session_state.map_selected_id = None
 
 
def add_object(obj_type: str, lat: float, lon: float):

    o = CityObject(

        id=new_id(),

        obj_type=obj_type,

        lat=float(lat),

        lon=float(lon),

        params=dict(DEFAULT_PARAMS.get(obj_type, {}))

    )

    st.session_state.objects.append(o)

    st.session_state.selected_id = o.id

    st.session_state.map_selected_id = None
 
 
def delete_selected():

    sid = st.session_state.selected_id

    if not sid:

        return

    st.session_state.objects = [o for o in st.session_state.objects if o.id != sid]

    st.session_state.selected_id = st.session_state.objects[0].id if st.session_state.objects else None

    st.session_state.map_selected_id = None
 
 
def move_selected(lat: float, lon: float):

    sid = st.session_state.selected_id

    if not sid:

        return

    for o in st.session_state.objects:

        if o.id == sid:

            o.lat, o.lon = float(lat), float(lon)

            st.session_state.map_selected_id = None

            return
 
 
def get_selected_obj() -> Optional[CityObject]:

    sid = st.session_state.selected_id

    for o in st.session_state.objects:

        if o.id == sid:

            return o

    return None
 
 
# -----------------------------

# App

# -----------------------------

st.set_page_config(page_title="CityTwin — Өскемен", layout="wide")

inject_css()

init_state()
 
st.markdown("## 🏙️ CityTwin — цифровой двойник района (Өскемен / Усть-Каменогорск)")

st.markdown(

    "<div class='muted'>"

    "Слева: выберите режим и объект. Справа: клик по карте (добавить/переместить). "

    "Чтобы управлять объектом: кликните по маркеру на карте — появятся кнопки действий."

    "</div>",

    unsafe_allow_html=True

)
 
left, right = st.columns([1, 2], gap="large")
 
# -----------------------------

# Left: scrollable control panel (map stays visible)

# -----------------------------

with left:

    panel = st.container(height=760)  # панель скроллится внутри себя

    with panel:

        st.markdown('<div class="panel-card">', unsafe_allow_html=True)

        st.markdown("### 🎛️ Панель управления")

        st.session_state.mode = st.radio(

            "Выберите, что хотите сделать на карте:",

            ["Добавить", "Переместить", "Удалить"],

            index=["Добавить", "Переместить", "Удалить"].index(st.session_state.mode)

        )

        st.markdown(

            "<div class='muted'>"

            "• Добавить: выбери объект → клик по карте<br>"

            "• Переместить: выбери объект → клик по новой точке<br>"

            "• Удалить: выбери объект → удалить (кнопкой в окне на карте или слева)"

            "</div>",

            unsafe_allow_html=True

        )

        st.markdown("</div>", unsafe_allow_html=True)
 
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)

        st.markdown("#### 🧩 Объекты (выберите, что добавить)")

        st.markdown('<div class="muted">Нажмите на объект → он станет активным → кликните по карте.</div>', unsafe_allow_html=True)
 
        for item in PALETTE:

            t = item["type"]

            label = f'{item["emoji"]}  {t}'

            help_text = item["hint"]

            active = (st.session_state.palette_selected == t)
 
            if active:

                st.button(label, key=f"pal_{t}", type="primary", help=help_text, use_container_width=True)

            else:

                if st.button(label, key=f"pal_{t}", help=help_text, use_container_width=True):

                    st.session_state.palette_selected = t

                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
 
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)

        st.markdown("#### 📌 Объекты на карте")

        if st.session_state.objects:

            options = [(o.id, f'{emoji_for_type(o.obj_type)} {o.obj_type} — ({o.lat:.5f}, {o.lon:.5f})')

                       for o in st.session_state.objects]
 
            idx = 0

            if st.session_state.selected_id:

                for i, (oid, _) in enumerate(options):

                    if oid == st.session_state.selected_id:

                        idx = i

                        break
 
            chosen = st.selectbox(

                "Выберите объект (для перемещения/удаления):",

                options=list(range(len(options))),

                index=idx,

                format_func=lambda i: options[i][1],

                key="obj_select"

            )

            st.session_state.selected_id = options[chosen][0]
 
            colA, colB = st.columns(2)

            with colA:

                if st.button("🗑️ Удалить выбранный", use_container_width=True):

                    delete_selected()

                    st.rerun()

            with colB:

                st.caption("Или нажмите маркер на карте → кнопки действий.")

        else:

            st.info("Пока пусто. Выберите объект и кликните по карте справа.")

        st.markdown("</div>", unsafe_allow_html=True)
 
        # Pros/Cons

        st.markdown('<div class="pm-box">', unsafe_allow_html=True)

        st.markdown("#### ✅ Плюсы / ⚠️ Минусы")

        st.markdown('<div class="muted">Оценка для выбранного объекта или последней точки клика.</div>', unsafe_allow_html=True)
 
        sel = get_selected_obj()

        if sel:

            p, m = evaluate_location(sel.obj_type, sel.lat, sel.lon, [o for o in st.session_state.objects if o.id != sel.id])

            st.markdown(f"**Выбран:** {emoji_for_type(sel.obj_type)} {sel.obj_type}")

        elif st.session_state.last_click:

            lat, lon = st.session_state.last_click

            t = st.session_state.palette_selected

            p, m = evaluate_location(t, lat, lon, st.session_state.objects)

            st.markdown(f"**Точка:** ({lat:.5f}, {lon:.5f}) для {emoji_for_type(t)} {t}")

        else:

            p, m = (["Выберите объект или кликните по карте, чтобы получить оценку."], [])
 
        for s in p:

            st.markdown(f'<div class="pm-plus">+ {s}</div>', unsafe_allow_html=True)

        for s in m:

            st.markdown(f'<div class="pm-minus">– {s}</div>', unsafe_allow_html=True)
 
        st.markdown("</div>", unsafe_allow_html=True)
 
        # Perimeter analysis (without residents/capacity lines)

        st.markdown('<div class="panel-card">', unsafe_allow_html=True)

        st.markdown("#### 📊 Анализ расположения и изменений инфраструктуры в периметре")

        st.markdown(

            f"<div class='muted'>Окружение в радиусе <b>{ANALYSIS_RADIUS_KM:.1f} км</b> от выбранного объекта/точки.</div>",

            unsafe_allow_html=True

        )
 
        if sel:

            base_lat, base_lon = sel.lat, sel.lon

            base_label = f"{emoji_for_type(sel.obj_type)} {sel.obj_type}"

        elif st.session_state.last_click:

            base_lat, base_lon = st.session_state.last_click

            t = st.session_state.palette_selected

            base_label = f"{emoji_for_type(t)} {t} (план)"

        else:

            base_lat, base_lon = DEFAULT_CENTER

            base_label = "Точка не выбрана"
 
        st.write(f"**Точка анализа:** {base_label}")

        result = analyze_perimeter(base_lat, base_lon, st.session_state.objects, ANALYSIS_RADIUS_KM)
 
        chips = []

        for k, v in sorted(result["counts"].items()):

            chips.append(f"{emoji_for_type(k)} {k}: {v}")

        if chips:

            st.markdown(" ".join([f"<span class='chip'>{c}</span>" for c in chips]), unsafe_allow_html=True)

        else:

            st.caption("В радиусе пока нет объектов.")
 
        # Только нужные выводы

        if result["industry_emission"] > 0:

            st.info(f"🏭 Поблизости есть промвлияние (условно): **{result['industry_emission']:.0f}**.")

        if result["parks"] == 0:

            st.warning("🌳 В радиусе нет парков — можно добавить зелёную зону.")

        else:

            st.success(f"🌳 Парков в радиусе: **{result['parks']}** — это поддерживает экологию и комфорт.")
 
        if result["around"]:

            st.caption("Ближайшие объекты:")

            for o, d in result["around"][:6]:

                st.write(f"- {emoji_for_type(o.obj_type)} {o.obj_type} — **{d:.2f} км**")
 
        st.markdown("</div>", unsafe_allow_html=True)
 
 
# -----------------------------

# Right: map + small action window when marker clicked

# -----------------------------

with right:

    # Мини-окно действий (появляется после клика по маркеру)

    sel = get_selected_obj()

    if sel and st.session_state.map_selected_id == sel.id:

        st.markdown(

            f"""
<div class="panel-card" style="margin-bottom:10px;">
<div class="muted">Вы выбрали объект на карте</div>
<div style="font-size:15px; font-weight:600; color:#111827;">

                {emoji_for_type(sel.obj_type)} {sel.obj_type}
</div>
</div>

            """,

            unsafe_allow_html=True

        )

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:

            if st.button("🗑️ Удалить", use_container_width=True):

                delete_selected()

                st.rerun()

        with c2:

            if st.button("📍 Переместить", use_container_width=True):

                st.session_state.mode = "Переместить"

                st.rerun()

        with c3:

            st.caption("Перемещение: кликните новое место на карте.")
 
    # Карта

    m = folium.Map(location=DEFAULT_CENTER, zoom_start=13, control_scale=True)
 
    # Маркеры с цветами

    for o in st.session_state.objects:

        style = MAP_STYLE.get(o.obj_type, {"color": "cadetblue", "fa": "info-sign"})

        popup = (

            f"{emoji_for_type(o.obj_type)} {o.obj_type}<br>"

            f"id: {o.id}<br>"

            f"{o.lat:.5f}, {o.lon:.5f}"

        )

        folium.Marker(

            location=[o.lat, o.lon],

            popup=folium.Popup(popup, max_width=300),

            tooltip=f"{emoji_for_type(o.obj_type)} {o.obj_type}",

            icon=folium.Icon(color=style["color"], icon=style["fa"], prefix="fa"),

        ).add_to(m)
 
    st_map = st_folium(m, height=680, width=None)
 
    # Клик по маркеру -> выбираем объект и показываем мини-окно действий

    if st_map and st_map.get("last_object_clicked"):

        olat = float(st_map["last_object_clicked"]["lat"])

        olon = float(st_map["last_object_clicked"]["lng"])

        clicked_obj = find_object_by_latlon(olat, olon, st.session_state.objects)

        if clicked_obj:

            st.session_state.selected_id = clicked_obj.id

            st.session_state.map_selected_id = clicked_obj.id

            st.rerun()
 
    # Клик по карте (не по маркеру)

    if st_map and st_map.get("last_clicked"):

        lat = float(st_map["last_clicked"]["lat"])

        lon = float(st_map["last_clicked"]["lng"])

        st.session_state.last_click = (lat, lon)
 
        if st.session_state.mode == "Добавить":

            add_object(st.session_state.palette_selected, lat, lon)

            st.rerun()
 
        elif st.session_state.mode == "Переместить":

            if st.session_state.selected_id:

                move_selected(lat, lon)

                st.rerun()
 
        elif st.session_state.mode == "Удалить":

            st.info("Удаление: кликните по маркеру → нажмите «Удалить» в маленьком окне.")
 
    st.markdown(

        "<div class='muted'>"

        "<b>Подсказка:</b> Добавить → выберите объект слева → клик по карте. "

        "Переместить → выберите объект (или клик по маркеру) → клик по новой точке. "

        "Удалить → клик по маркеру → кнопка «Удалить»."

        "</div>",

        unsafe_allow_html=True

    )

 