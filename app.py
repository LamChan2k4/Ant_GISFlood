import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(layout="wide", page_title="SENSE-CENTRAL SWARM UI")

# Tùy chỉnh CSS để Dashboard trông "chiến" hơn
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ SENSE-CENTRAL SWARM: Mạng lưới Cứu hộ Bầy đàn")
st.caption("Khu vực mô phỏng: Lưu vực Sông Hương - Phường Vỹ Dạ, TP. Huế")

# --- KHỞI TẠO DỮ LIỆU ĐỊA DANH THỰC TẾ (HUE) ---
# Tọa độ các điểm trọng yếu tại Huế
locations = {
    "Đập Đá": [16.4678, 107.5995, 0.3],    # Rất thấp
    "Cầu Đập Đá": [16.4690, 107.6010, 0.4], 
    "Vỹ Dạ 1": [16.4660, 107.6050, 0.5],
    "Vỹ Dạ 2": [16.4630, 107.6080, 0.6],
    "Cồn Hến": [16.4730, 107.5980, 0.2],   # Cực thấp, dễ cô lập
    "Phường Phú Hội": [16.4650, 107.5920, 1.2] # Cao ráo hơn
}

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/swarm.png", width=80)
    st.header("Trạm Chỉ huy Swarm")
    
    # 1. Giả lập nước dâng
    flood_meter = st.slider("🌊 Mực nước lũ (mét)", 0.0, 3.0, 0.6, 0.1)
    
    # 2. Chọn loại "Kiến"
    ant_mode = st.selectbox("🤖 Đội hình Swarm", 
                            ["Kiến Xe Tải (Truck-Bot)", "Kiến Cano (Aqua-Bot)", "Drone Tiếp Tế"])
    
    # 3. Sự cố thực tế
    st.subheader("⚠️ Giả lập tình huống")
    node_destroyed = st.checkbox("Mất kết nối Node Đập Đá (Node 0)")
    
    st.divider()
    st.info("Thuật toán: ACO (Ant Colony Optimization) cải biên với Trọng số Thủy văn thực tế.")

# --- XỬ LÝ LOGIC SWARM ---
data_nodes = []
for i, (name, coords) in enumerate(locations.items()):
    elev = coords[2]
    is_active = False if (node_destroyed and i == 0) else True
    
    # Tính toán nồng độ Pheromone (độ ưu tiên đường đi)
    # Càng đi được dễ dàng, pheromone càng cao
    depth = flood_meter - elev
    
    # Logic màu sắc Node dựa trên trạng thái ngập
    color = [0, 255, 0, 150] # Xanh: An toàn
    if depth > 0.5: color = [255, 0, 0, 200] # Đỏ: Ngập nặng
    if not is_active: color = [100, 100, 100, 255] # Xám: Hỏng

    data_nodes.append({
        "name": name,
        "lat": coords[0], "lon": coords[1],
        "depth": max(0, round(depth, 2)),
        "color": color,
        "active": is_active
    })

df = pd.DataFrame(data_nodes)

# Tạo các tuyến đường Pheromone (Edges) giữa các Node
edges = []
for i in range(len(df)):
    for j in range(i+1, len(df)):
        n1, n2 = df.iloc[i], df.iloc[j]
        
        # Chỉ vẽ đường nếu cả 2 node đang active
        if n1['active'] and n2['active']:
            avg_depth = (n1['depth'] + n2['depth']) / 2
            path_color = [255, 255, 255, 50] # Trắng mờ: Không đi được
            width = 1
            
            # Logic "Đàn kiến đa nhân cách"
            can_go = False
            if ant_mode == "Kiến Xe Tải (Truck-Bot)" and avg_depth < 0.4:
                path_color = [255, 165, 0, 200]; width = 4; can_go = True
            elif ant_mode == "Kiến Cano (Aqua-Bot)" and avg_depth >= 0.5:
                path_color = [0, 191, 255, 200]; width = 6; can_go = True
            elif ant_mode == "Drone Tiếp Tế":
                path_color = [138, 43, 226, 150]; width = 2; can_go = True
            
            if can_go:
                edges.append({
                    "source": [n1['lon'], n1['lat']],
                    "target": [n2['lon'], n2['lat']],
                    "color": path_color,
                    "width": width
                })

# --- VISUALIZATION ---
view_state = pdk.ViewState(latitude=16.4677, longitude=107.5995, zoom=14, pitch=50)

# Layer điểm (Node AIoT)
node_layer = pdk.Layer(
    "ScatterplotLayer", df,
    get_position="[lon, lat]",
    get_fill_color="color",
    get_radius=40,
    pickable=True
)

# Layer nhãn tên
text_layer = pdk.Layer(
    "TextLayer", df,
    get_position="[lon, lat]",
    get_text="name",
    get_size=16,
    get_color=[255, 255, 255],
    get_alignment_baseline="'bottom'"
)

# Layer Pheromone đường đi
path_layer = pdk.Layer(
    "LineLayer", edges,
    get_source_position="source",
    get_target_position="target",
    get_color="color",
    get_width="width",
    highlight_color=[255, 255, 0],
    picking_radius=10
)

# Render bản đồ
col_map, col_info = st.columns([3, 1])

with col_map:
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/dark-v10',
        initial_view_state=view_state,
        layers=[path_layer, node_layer, text_layer],
        tooltip={"text": "{name}\nĐộ ngập: {depth}m"}
    ))

with col_info:
    st.subheader("Dòng chảy Swarm")
    if node_destroyed:
        st.warning("📡 ĐỨT GÃY TÍN HIỆU tại Node Đập Đá. Các kiến ảo đang thực hiện tính toán lại Pheromone (Self-healing)...")
    
    st.write(f"Đội hình hiện tại: **{ant_mode}**")
    st.metric("Tuyến đường khả thi", f"{len(edges)} paths")
    
    # Progress bar mô phỏng nồng độ pheromone trung bình
    st.write("Mật độ Pheromone vùng lũ:")
    st.progress(min(len(edges) * 10, 100))
    
    if st.button("♻️ Gửi cấu hình xuống Node"):
        with st.spinner("Đang đẩy Firmware TinyML xuống các ESP32..."):
            time.sleep(2)
            st.success("Đồng bộ hóa thành công!")

# --- FOOTER DATA ---
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pin Node trung bình", "85%", "Li-Po")
c2.metric("Latency (LoRa)", "120ms", "-10ms")
c3.metric("Chính xác (TinyML)", "92%", "XAI")
c4.metric("Dân số hỗ trợ", "1,200", "Người")