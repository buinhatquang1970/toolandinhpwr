import streamlit as st
import pandas as pd
from tool_tinh_toan import ToolAnDinhTanSo

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Công cụ Ấn định Tần số cho mạng dùng riêng", layout="wide")

# CSS TÙY CHỈNH NÂNG CAO
st.markdown("""
    <style>
        /* Tăng padding-top để không bị che bởi header */
        .block-container {
            padding-top: 1.5rem; 
            padding-bottom: 2rem;
        }
        h2 {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* 1. THU HẸP KHOẢNG CÁCH DỌC (Label và ô nhập sát nhau) */
        div[data-testid="stMarkdownContainer"] > p {
            margin-bottom: -3px !important;
            font-weight: 500;
        }
        
        /* 2. THU HẸP KHOẢNG CÁCH NGANG (Giữa các ô Độ/Phút/Giây) */
        [data-testid="stHorizontalBlock"] {
            gap: 0.1rem !important; /* Khoảng cách cực nhỏ */
        }
        
        /* 3. Tinh chỉnh Caption sát lên trên */
        .stCaption {
            font-size: 0.7rem;
            margin-top: -5px;
            color: #555;
        }

        /* 4. XỬ LÝ KHOẢNG CÁCH ĐƯỜNG KẺ NGANG VÀ TIÊU ĐỀ */
        hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        h3 {
            padding-top: 0.2rem !important;
            padding-bottom: 0.2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- HÀM CHUYỂN ĐỔI DMS -> DECIMAL ---
def dms_to_decimal(d, m, s):
    return d + (m / 60.0) + (s / 3600.0)

# Tiêu đề ứng dụng
st.markdown("<h2 style='text-align: center; color: #0068C9;'>CÔNG CỤ TÍNH TOÁN ẤN ĐỊNH TẦN SỐ MẠNG DÙNG RIÊNG</h2>", unsafe_allow_html=True)
st.markdown("---")

# =============================================================================
# PHẦN 1: THÔNG SỐ ĐẦU VÀO
# =============================================================================
st.subheader("1. THÔNG SỐ KỸ THUẬT & VỊ TRÍ MẠNG")

# --- HÀNG 1: TỌA ĐỘ VÀ ĐỊA ĐIỂM ---
# CẤU TRÚC MỚI: [Kinh độ] - [Trống1] - [Vĩ độ] - [Trống2] - [Tỉnh] - [TrốngCuối]
# Đã thêm col_sep2 để tách Vĩ độ và Tỉnh
col_grp1, col_sep1, col_grp2, col_sep2, col_grp3, col_spacer_h1 = st.columns([1.3, 0.2, 1.3, 0.2, 1.6, 5.4])

# --- 1. KINH ĐỘ (LONGITUDE) ---
with col_grp1:
    st.markdown("📍 **Kinh độ (Longitude)**")
    c1_d, c1_m, c1_s = st.columns([1, 1, 1.2])
    with c1_d:
        lon_d = st.number_input("Độ", min_value=0, max_value=180, value=105, step=1, key="lon_d", label_visibility="collapsed")
    with c1_m:
        lon_m = st.number_input("Phút", min_value=0, max_value=59, value=0, step=1, key="lon_m", label_visibility="collapsed")
    with c1_s:
        lon_s = st.number_input("Giây", min_value=0.0, max_value=59.99, value=0.0, step=0.1, format="%.2f", key="lon_s", label_visibility="collapsed")
    
    lon = dms_to_decimal(lon_d, lon_m, lon_s)
    st.caption(f"Dec: {lon:.5f}")

# --- Cột phân cách 1 ---
with col_sep1:
    st.write("") 

# --- 2. VĨ ĐỘ (LATITUDE) ---
with col_grp2:
    st.markdown("📍 **Vĩ độ (Latitude)**")
    c2_d, c2_m, c2_s = st.columns([1, 1, 1.2])
    with c2_d:
        lat_d = st.number_input("Độ", min_value=0, max_value=90, value=21, step=1, key="lat_d", label_visibility="collapsed")
    with c2_m:
        lat_m = st.number_input("Phút", min_value=0, max_value=59, value=0, step=1, key="lat_m", label_visibility="collapsed")
    with c2_s:
        lat_s = st.number_input("Giây", min_value=0.0, max_value=59.99, value=0.0, step=0.1, format="%.2f", key="lat_s", label_visibility="collapsed")
    
    lat = dms_to_decimal(lat_d, lat_m, lat_s)
    st.caption(f"Dec: {lat:.5f}")

# --- Cột phân cách 2 (Mới thêm để tách Vĩ độ và Tỉnh) ---
with col_sep2:
    st.write("") 

# --- 3. TỈNH THÀNH ---
with col_grp3:
    st.markdown("🏙️ **Tỉnh / Thành phố**")
    province = st.selectbox("Chọn Tỉnh/TP", 
                            ["-- Chọn Tỉnh/TP --", "HANOI", "HCM", "DANANG", "KHAC"], 
                            index=0, label_visibility="collapsed")

# --- HÀNG 2: THÔNG SỐ KỸ THUẬT ---
# ĐIỀU CHỈNH: Tăng cột c5 (Số lượng) lên 1.3 để không bị vỡ dòng tiêu đề
c1, c2, c3, c4, c5, c_spacer_h2 = st.columns([0.9, 0.9, 0.9, 1.3, 1.3, 4.7])

with c1:
    st.markdown("**Độ cao (m)**")
    h_anten = st.number_input("Độ cao", value=0.0, step=1.0, label_visibility="collapsed")
with c2:
    st.markdown("**Dải tần**")
    band = st.selectbox("Dải tần", ["VHF", "UHF"], label_visibility="collapsed")
with c3:
    st.markdown("**Băng thông**")
    bw = st.selectbox("Băng thông", [6.25, 12.5, 25.0], index=1, label_visibility="collapsed")
with c4:
    st.markdown("**Loại mạng**")
    mode = st.selectbox("Loại mạng", ["LAN", "WAN_SIMPLEX", "WAN_DUPLEX"], label_visibility="collapsed")
with c5:
    st.markdown("**Số lượng tần số**") # Ô này đã được nới rộng
    qty = st.number_input("Số lượng", value=1, min_value=1, label_visibility="collapsed")

st.markdown("---")

# =============================================================================
# PHẦN 2: DỮ LIỆU & XỬ LÝ
# =============================================================================
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("2. NẠP DỮ LIỆU ĐẦU VÀO")
    uploaded_file = st.file_uploader("📂 Tải lên file Excel dữ liệu (xlsx) trích xuất từ phần mềm cấp phép", 
                                     type=['xls', 'xlsx', 'csv'])
    
    if uploaded_file is not None:
        st.caption(f"✅ Đang sử dụng file: **{uploaded_file.name}**")

with col_right:
    st.subheader("3. TÍNH TOÁN TẦN SỐ KHẢ DỤNG")
    st.write("") 
    if uploaded_file is not None:
        btn_calc = st.button("TÍNH TOÁN TẦN SỐ", type="primary", use_container_width=True)
    else:
        st.info("⬅️ Vui lòng tải file dữ liệu lên trước")
        btn_calc = False

# =============================================================================
# PHẦN 3: HIỂN THỊ KẾT QUẢ
# =============================================================================
if btn_calc:
    # --- KIỂM TRA DỮ LIỆU ---
    error_msg = []
    if lon == 0.0: error_msg.append("Kinh độ chưa nhập hoặc bằng 0")
    if lat == 0.0: error_msg.append("Vĩ độ chưa nhập hoặc bằng 0")
    if province == "-- Chọn Tỉnh/TP --": error_msg.append("Thiếu Tỉnh/TP")
    
    if error_msg:
        st.error(f"⚠️ LỖI: {', '.join(error_msg)}")
    else:
        if h_anten == 0.0:
            st.warning("⚠️ Lưu ý: Độ cao Anten đang là 0m.")
            
        st.markdown("---")
        st.subheader("📊 KẾT QUẢ TÍNH TOÁN")
        
        with st.spinner(f'Đang tính toán trên file {uploaded_file.name}...'):
            try:
                # 1. Khởi tạo công cụ
                tool = ToolAnDinhTanSo(uploaded_file)
                
                # 2. Gom dữ liệu
                user_input = {
                    "lat": lat, "lon": lon,
                    "province_code": province, "antenna_height": h_anten,
                    "band": band, "bw": bw, "usage_mode": mode
                }
                
                # 3. Tính toán
                results = tool.tinh_toan(user_input)
                
                # 4. Hiển thị
                if not results:
                    st.error("❌ Không tìm thấy tần số khả dụng!")
                else:
                    df_res = pd.DataFrame(results)
                    df_res.columns = ["STT", "Tần số Khả dụng (MHz)", "Hệ số Tái sử dụng (Điểm)"]
                    df_res.set_index("STT", inplace=True)
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Số lượng tìm thấy", f"{len(results)}")
                    m2.metric("Tần số tốt nhất", f"{results[0]['frequency']} MHz")
                    
                    st.dataframe(df_res.head(qty), use_container_width=True)
                    
                    with st.expander("Xem danh sách đầy đủ"):
                        st.dataframe(df_res, use_container_width=True)
                        
            except Exception as e:
                st.error(f"Có lỗi xảy ra: {e}")