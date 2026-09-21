import io
import math

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# ตั้งค่าหน้าเว็บ
# ---------------------------------------------------------
st.set_page_config(page_title="Distance Dashboard", layout="wide")
st.title("📌 แดชบอร์ดนำเสนอข้อมูลระยะทาง")
st.caption("Dashboard สำหรับคำนวณและวิเคราะห์ระยะทางแบบ Euclidean — เชื่อมต่อข้อมูลจาก GitHub ได้")

DEFAULT_COLUMNS = ["point", "x1", "y1", "x2", "y2"]


# ---------------------------------------------------------
# ฟังก์ชันช่วยเหลือ
# ---------------------------------------------------------
def euclidean_distance(row) -> float:
    return math.sqrt((row["x2"] - row["x1"]) ** 2 + (row["y2"] - row["y1"]) ** 2)


@st.cache_data(show_spinner=False)
def load_csv_from_url(url: str) -> pd.DataFrame:
    """ดาวน์โหลดไฟล์ CSV จาก GitHub raw URL"""
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))


@st.cache_data(show_spinner=False)
def fetch_github_repo_stats(owner: str, repo: str) -> dict:
    """ดึงสถิติ repository จาก GitHub REST API"""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def ensure_distance_column(df: pd.DataFrame) -> pd.DataFrame:
    """ถ้ายังไม่มีคอลัมน์ distance ให้คำนวณเพิ่มให้"""
    df = df.copy()
    required = {"x1", "y1", "x2", "y2"}
    if required.issubset(df.columns) and "distance" not in df.columns:
        df["distance"] = df.apply(euclidean_distance, axis=1)
    return df


# ---------------------------------------------------------
# แถบด้านข้าง: แหล่งข้อมูล
# ---------------------------------------------------------
st.sidebar.header("⚙️ แหล่งข้อมูล")
source_mode = st.sidebar.radio(
    "เลือกแหล่งข้อมูล",
    options=["อัปโหลดไฟล์ CSV", "ดึงจาก GitHub (raw URL)", "ไฟล์ตัวอย่างในเครื่อง"],
)

df = None

if source_mode == "อัปโหลดไฟล์ CSV":
    uploaded = st.sidebar.file_uploader("เลือกไฟล์ distance.csv หรือ distance_output.csv", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded)

elif source_mode == "ดึงจาก GitHub (raw URL)":
    st.sidebar.caption(
        "ตัวอย่าง URL: https://raw.githubusercontent.com/<user>/<repo>/main/distance.csv"
    )
    github_url = st.sidebar.text_input("GitHub raw CSV URL")
    if github_url:
        try:
            df = load_csv_from_url(github_url)
        except Exception as e:
            st.sidebar.error(f"ดึงข้อมูลไม่สำเร็จ: {e}")

else:  # ไฟล์ตัวอย่างในเครื่อง
    local_path = st.sidebar.text_input("พาธไฟล์ในเครื่อง", value="distance_output.csv")
    try:
        df = pd.read_csv(local_path)
    except Exception as e:
        st.sidebar.error(f"ไม่พบไฟล์หรืออ่านไม่สำเร็จ: {e}")

# ---------------------------------------------------------
# ส่วนแสดงผลข้อมูลระยะห่าง
# ---------------------------------------------------------
if df is not None and not df.empty:
    df = ensure_distance_column(df)
    has_dist = "distance" in df.columns
    has_point = "point" in df.columns

    st.subheader("📊 สรุปผลข้อมูลระยะทาง")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("จำนวนจุดทั้งหมด", len(df))
    c2.metric("ระยะทางรวม", f"{df['distance'].sum():.2f}" if has_dist else "-")

    if has_dist and has_point:
        min_row = df.loc[df["distance"].idxmin()]
        max_row = df.loc[df["distance"].idxmax()]
        c3.metric("ระยะทางสั้นที่สุด", f"{min_row['distance']:.2f}", delta=f"{min_row['point']}")
        c4.metric("ระยะทางมากที่สุด", f"{max_row['distance']:.2f}", delta=f"{max_row['point']}")
    else:
        c3.metric("ระยะทางสั้นที่สุด", f"{df['distance'].min():.2f}" if has_dist else "-")
        c4.metric("ระยะทางมากที่สุด", f"{df['distance'].max():.2f}" if has_dist else "-")

    c5.metric("ระยะทางเฉลี่ย", f"{df['distance'].mean():.2f}" if has_dist else "-")

    st.subheader("📄 ข้อมูลระยะทาง")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if has_dist and has_point:
        st.subheader("📈 ระยะทางของแต่ละจุด")
        st.bar_chart(df.set_index("point")["distance"], y_label="Distance")

    if {"x1", "y1", "x2", "y2"}.issubset(df.columns):
        st.subheader("ตำแหน่งจุดที่ 1 และจุดที่ 2 บนกราฟ")
        plot_df = pd.DataFrame({
            "x": pd.concat([df["x1"], df["x2"]], ignore_index=True),
            "y": pd.concat([df["y1"], df["y2"]], ignore_index=True),
        })
        st.scatter_chart(plot_df, x="x", y="y")

    st.download_button(
        "⬇️ ดาวน์โหลดข้อมูล (พร้อมระยะห่าง) เป็น CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="distance_dashboard_output.csv",
        mime="text/csv",
    )
else:
    st.info("กรุณาเลือกแหล่งข้อมูลทางแถบด้านซ้าย เพื่อแสดงผลแดชบอร์ด")

# ---------------------------------------------------------
# ส่วนเชื่อมต่อ GitHub API แสดงสถิติ repository
# ---------------------------------------------------------
st.header("🐙 สถิติ GitHub Repository")

col_a, col_b = st.columns(2)
owner = col_a.text_input("GitHub owner / organization", value="streamlit")
repo = col_b.text_input("Repository name", value="streamlit")

if st.button("ดึงข้อมูล Repository"):
    try:
        stats = fetch_github_repo_stats(owner, repo)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⭐ Stars", stats.get("stargazers_count", "-"))
        c2.metric("🍴 Forks", stats.get("forks_count", "-"))
        c3.metric("🐛 Open Issues", stats.get("open_issues_count", "-"))
        c4.metric("👀 Watchers", stats.get("watchers_count", "-"))
        st.write(f"**คำอธิบาย:** {stats.get('description', '-')}")
        st.write(f"**ภาษาโค้ดหลัก:** {stats.get('language', '-')}")
        st.write(f"**ลิงก์:** {stats.get('html_url', '-')}")
    except Exception as e:
        st.error(f"ดึงข้อมูลจาก GitHub ไม่สำเร็จ: {e}")
