import streamlit as st
import pandas as pd
import altair as alt

# ========== CONFIG ==========
st.set_page_config(page_title="Hotel Dashboard", layout="wide")

# ========== HEADER ==========
st.markdown(
    """
    <div style="text-align:center; margin-top:-20px; margin-bottom:30px; width:100%;">
        <h1 style="margin-bottom:0;">Saray Pyramids Hotel</h1>
        <h4 style="color:gray; margin-top:5px;">Performance Dashboard</h4>
    </div>
    """,
    unsafe_allow_html=True
)

# ========== SIDEBAR ==========
currency = st.sidebar.radio("Currency", ["🇪🇬 EGP", "💵 USD"])
rate = 1 if "EGP" in currency else 1 / 50
symbol = "EGP" if "EGP" in currency else "USD"

booking_type = st.sidebar.radio("Booking Data", ["Past Bookings", "Future Bookings"])
file_name = "Saray Dashboard.xlsx" if booking_type == "Past Bookings" else "Saray_Future.xlsx"

view_by = st.sidebar.radio("View Charts By", ["Monthly", "Daily"])

# ========== LOAD DATA ==========
df = pd.read_excel(file_name, sheet_name="Raw Data")
df = df[df["Arrival2"].notna()]
df["ADR"] = pd.to_numeric(df["Net base rate"], errors='coerce') / pd.to_numeric(df["Nights"], errors='coerce')
df["ADR"] = df["ADR"].replace([float("inf"), -float("inf")], pd.NA)
df["TTV"] = df["TTV"] * rate
df["ADR"] = df["ADR"] * rate
df["Arrival Date"] = pd.to_datetime(df["Arrival2"], errors="coerce")
df["Arrival Month"] = df["Arrival Date"].dt.to_period("M").astype(str)

# ========== FILTERS ==========
filters = {
    "Room Type": "Type",
    "Arrival Month": "Arrival Month ",
    "Meal Plan": "Meal Plan",
    "Release Days": "Release Days",
    "Online vs Offline": "Online/Offline",
    "Arrival Year": "Arrival Year",
    "Channel": "Channel",
    "Nationality": "Nationality",
    "Created Year": "Created Year",
    "Created Month": "Created on Month"
}
for label, col in filters.items():
    if col in df.columns:
        values = st.sidebar.multiselect(label, df[col].dropna().unique())
        if values:
            df = df[df[col].isin(values)]

# ========== METRICS ==========
col1, col2, col3 = st.columns(3)
col1.metric("Total Revenue", f"{df['TTV'].sum():,.0f} {symbol}")
col2.metric("Average ADR", f"{df['ADR'].mean():,.0f} {symbol}")
col3.metric("Total Nights", f"{df['Nights'].sum():,.0f}")

# ========== SUMMARY CHARTS ==========
# ========== SUMMARY CHARTS ==========
st.markdown("## 📈 Revenue & Nights Over Time")

df["Arrival Date"] = pd.to_datetime(df["Arrival2"], errors="coerce")

if view_by == "Monthly":
    df["Period"] = df["Arrival Date"].dt.to_period("M").astype(str)
    df["SortKey"] = df["Arrival Date"].dt.month + df["Arrival Date"].dt.year * 100
    x_labels = df.sort_values("SortKey")["Period"].drop_duplicates().tolist()
    x_title = "Month"
else:
    df["Period"] = df["Arrival Date"].dt.strftime("%d %b %Y")
    df["SortKey"] = df["Arrival Date"]
    x_labels = df.sort_values("SortKey")["Period"].drop_duplicates().tolist()
    x_title = "Date"

df_grouped = df.groupby("Period").agg({
    "TTV": "sum",
    "Nights": "sum"
}).reindex(x_labels).reset_index().rename(columns={"index": "Period"})

col1, col2 = st.columns(2)

with col1:
    st.altair_chart(
        alt.Chart(df_grouped).mark_bar(color="#F58518").encode(
            x=alt.X("Period:O", title=x_title, sort=x_labels),
            y=alt.Y("TTV:Q", title=f"Revenue ({symbol})"),
            tooltip=["Period", alt.Tooltip("TTV", format=",.0f")]
        ).properties(title="Total Revenue", width='container', height=320),
        use_container_width=True
    )

with col2:
    st.altair_chart(
        alt.Chart(df_grouped).mark_bar(color="#1f77b4").encode(
            x=alt.X("Period:O", title=x_title, sort=x_labels),
            y=alt.Y("Nights:Q", title="Nights Sold"),
            tooltip=["Period", alt.Tooltip("Nights", format=",.0f")]
        ).properties(title="Total Nights", width='container', height=320),
        use_container_width=True
    )

# ========== FORMATTER ==========
def format_amount(val):
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"{val/1_000:.0f}K"
    else:
        return str(round(val))

# ========== CHART HELPER ==========
def create_bar_chart(data, x, y, label, title, color, format_y=False, sort_order=None):
    x_encoding = alt.X(
        x,
        sort=sort_order if sort_order else alt.EncodingSortField(field=y.split(":")[0], order="descending")
    )

    bar = alt.Chart(data).mark_bar(color=color).encode(
        x=x_encoding,
        y=alt.Y(y, title=f"{title.split(' ')[0]} ({symbol})" if format_y else title.split(" ")[0]),
        tooltip=[x, alt.Tooltip(y, title=y.split(":")[0], format=",.0f")]
    ).properties(width='container', height=320)

    text = alt.Chart(data).mark_text(dy=-10, fontSize=10, fontWeight="bold").encode(
        x=x_encoding, y=y, text=label
    )

    return alt.layer(bar, text).properties(title=title).configure_title(fontSize=16, anchor='start')

# ========== CHART GROUP ==========
def chart_group(df, group_by, titles, colors, top_n=None, sort_order=None):
    col1, col2, col3 = st.columns(3)

    # Nights
    group_nights = df.groupby(group_by)["Nights"].sum().reset_index()
    group_nights[group_by] = group_nights[group_by].astype(str)
    if top_n:
        group_nights = group_nights.sort_values("Nights", ascending=False).head(top_n)
    group_nights["Label"] = group_nights["Nights"].apply(lambda x: f"{x:,.0f}")
    if group_nights.empty:
        with col1:
            st.warning(f"No data for {titles[0]}")
    else:
        with col1:
            st.altair_chart(
                create_bar_chart(group_nights, f"{group_by}:N", "Nights:Q", "Label", titles[0], colors[0], sort_order=sort_order),
                use_container_width=True
            )

    # ADR
    group_adr = df.groupby(group_by)["ADR"].mean().reset_index()
    group_adr[group_by] = group_adr[group_by].astype(str)
    if top_n:
        group_adr = group_adr.sort_values("ADR", ascending=False).head(top_n)
    group_adr["Label"] = group_adr["ADR"].apply(lambda x: f"{x:,.0f}")
    if group_adr.empty:
        with col2:
            st.warning(f"No data for {titles[1]}")
    else:
        with col2:
            st.altair_chart(
                create_bar_chart(group_adr, f"{group_by}:N", "ADR:Q", "Label", titles[1], colors[1], format_y=True, sort_order=sort_order),
                use_container_width=True
            )

    # TTV
    group_ttv = df.groupby(group_by)["TTV"].sum().reset_index()
    group_ttv[group_by] = group_ttv[group_by].astype(str)
    if top_n:
        group_ttv = group_ttv.sort_values("TTV", ascending=False).head(top_n)
    group_ttv["Label"] = group_ttv["TTV"].apply(format_amount)
    if group_ttv.empty:
        with col3:
            st.warning(f"No data for {titles[2]}")
    else:
        with col3:
            st.altair_chart(
                create_bar_chart(group_ttv, f"{group_by}:N", "TTV:Q", "Label", titles[2], colors[2], format_y=True, sort_order=sort_order),
                use_container_width=True
            )

# ========== CHART SECTIONS ==========

st.subheader("📊 Channels Detailed Split")
chart_group(df, "Channel", ["Nights Sold by Channel", "ADR by Channel", "Revenue by Channel"],
            ["#1f77b4", "#4C78A8", "#F58518"], top_n=10)

st.markdown(" ")
st.subheader("🛏️ Room Types Detailed Split")
chart_group(df, "Type", ["Nights Sold by Room Type", "ADR by Room Type", "Revenue by Room Type"],
            ["#1f77b4", "#4C78A8", "#F58518"])

st.markdown(" ")
st.subheader("🍽️ Meal Plan Detailed Split")
chart_group(df, "Meal Plan", ["Nights Sold by Meal Plan", "ADR by Meal Plan", "Revenue by Meal Plan"],
            ["#1f77b4", "#4C78A8", "#F58518"])

st.markdown(" ")
st.subheader("🌍 Region Detailed Split")
if "Region" in df.columns:
    chart_group(df, "Region", ["Nights Sold by Region", "ADR by Region", "Revenue by Region"],
                ["#1f77b4", "#4C78A8", "#F58518"], top_n=10)

# ========== ⏳ Release Days Group Detailed Split ==========
st.markdown(" ")
st.subheader("⏳ Release Days Detailed Split")

release_days_order = [
    "0-1 Days", "2-3 Days", "4-7 Days", "8-14 Days",
    "15-30 Days", "31-60 Days", "61-90 Days", "91+ Days"
]

if "Release Days" in df.columns:
    df["Release Days Group"] = pd.cut(df["Release Days"], 
        bins=[-1, 1, 3, 7, 14, 30, 60, 90, float('inf')],
        labels=release_days_order
    )

if "Release Days Group" in df.columns:
    chart_group(
        df,
        "Release Days Group",
        ["Nights Sold by Release Days", "ADR by Release Days", "Revenue by Release Days"],
        ["#1f77b4", "#4C78A8", "#F58518"],
        sort_order=release_days_order
    )
