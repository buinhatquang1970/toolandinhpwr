import pandas as pd
import re
from geopy.distance import geodesic
import config
import numpy as np

# Cập nhật danh sách cột để nhận diện cột Địa điểm
EXCEL_COLUMNS = {
    "LICENSE_NO": "Số giấy phép", 
    "FREQUENCY": "Tần số phát",
    "BANDWIDTH": "Phương thức phát", 
    "LAT": "Vị trí anten: Vĩ độ",
    "LON": "Vị trí anten: Kinh độ", 
    "ADDRESS": "Địa điểm đặt thiết bị", # Ưu tiên cột này
    "PROVINCE_OLD": "Tỉnh thành",      # Dự phòng
    "ANTENNA_HEIGHT": "Kích thước anten" 
}

# --- HÀM BỔ TRỢ: CHUẨN HÓA TIẾNG VIỆT ---
def chuan_hoa_text(text):
    """
    Chuyển tiếng Việt có dấu thành không dấu, in hoa, xóa ký tự đặc biệt.
    Xử lý các tiền tố như 'TP.', 'Tỉnh', 'Thành phố'.
    """
    if pd.isna(text) or str(text).strip() == "":
        return ""
    
    text = str(text).strip().lower()
    
    # Bảng mã thay thế tiếng Việt
    patterns = {
        '[àáảãạăắằẳẵặâấầẩẫậ]': 'a',
        '[đ]': 'd',
        '[èéẻẽẹêếềểễệ]': 'e',
        '[ìíỉĩị]': 'i',
        '[òóỏõọôốồổỗộơớờởỡợ]': 'o',
        '[ùúủũụưứừửữự]': 'u',
        '[ỳýỷỹỵ]': 'y'
    }
    
    for regex, replace in patterns.items():
        text = re.sub(regex, replace, text)
    
    # Xóa các từ thừa chỉ đơn vị hành chính
    text = re.sub(r'thanh pho|tinh|tp\.|tp ', '', text)
    
    # Xóa ký tự đặc biệt và khoảng trắng thừa, chỉ giữ lại chữ và số
    text = re.sub(r'[^a-z0-9]', '', text)
    
    return text.upper()

class ToolAnDinhTanSo:
    def __init__(self, excel_file):
        file_name = ""
        if hasattr(excel_file, 'name'):
            file_name = excel_file.name
            file_source = excel_file
        elif isinstance(excel_file, str):
            file_name = excel_file
            file_source = excel_file
        print(f"--- ĐỌC DB: {file_name} ---")
        try:
            # Đọc file
            if file_name.lower().endswith('.csv'): self.df = pd.read_csv(file_source)
            else:
                try: self.df = pd.read_excel(file_source, engine='openpyxl')
                except: 
                    try: self.df = pd.read_excel(file_source, engine='xlrd')
                    except: self.df = pd.read_excel(file_source)

            # Chuẩn hóa tên cột
            self.df.columns = self.df.columns.str.strip()
            rename_map = {}
            for key, col_name in EXCEL_COLUMNS.items():
                if col_name in self.df.columns:
                    rename_map[col_name] = {
                        "LICENSE_NO": "license", 
                        "FREQUENCY": "raw_freq",
                        "BANDWIDTH": "raw_bw", 
                        "LAT": "raw_lat",
                        "LON": "raw_lon", 
                        "ADDRESS": "raw_address",  # Map cột địa điểm
                        "PROVINCE_OLD": "raw_province_col",
                        "ANTENNA_HEIGHT": "h_anten"
                    }.get(key, key)
            
            # Logic tìm cột tự động nếu tên không khớp 100%
            if "raw_freq" not in rename_map.values():
                 for c in self.df.columns:
                     if "Tần số" in c and "phát" in c: rename_map[c] = "raw_freq"; break
            
            # Tìm cột địa điểm nếu chưa thấy
            if "raw_address" not in rename_map.values():
                for c in self.df.columns:
                    c_lower = c.lower()
                    if "địa điểm" in c_lower or "địa chỉ" in c_lower or "nơi đặt" in c_lower:
                        rename_map[c] = "raw_address"
                        break

            self.df = self.df.rename(columns=rename_map)
            
            self.clean_data()
            print(f"-> Đã tải và làm sạch {len(self.df)} hồ sơ.")
            
        except Exception as e:
            print(f"LỖI KHI ĐỌC FILE: {e}")
            self.df = pd.DataFrame() 

    def convert_dms_to_decimal(self, dms_str):
        if pd.isna(dms_str): return None
        s_in = str(dms_str).upper().strip()
        try:
            val = float(s_in.replace(',', '.'))
            if 0 < abs(val) < 180: return val
        except: pass
        nums = re.findall(r"(\d+)[.,]?(\d*)", s_in)
        valid_nums = []
        for n in nums:
            if n[0]: 
                val_str = n[0] + ("." + n[1] if n[1] else "")
                valid_nums.append(float(val_str))
        if len(valid_nums) >= 3:
            d, m, s = valid_nums[0], valid_nums[1], valid_nums[2]
            if d > 180 or m >= 60: return None
            return d + m/60 + s/3600
        return None

    def parse_bandwidth(self, emission_code):
        if pd.isna(emission_code): return 12.5
        code = str(emission_code).upper()
        if "16K" in code: return 25.0
        if "11K" in code or "8K5" in code: return 12.5
        if "4K0" in code: return 6.25
        return 12.5

    def clean_data(self):
        cleaned_rows = []
        # Kiểm tra xem có cột raw_address không, nếu không thì dùng cột tỉnh cũ hoặc để trống
        has_address = 'raw_address' in self.df.columns
        
        for idx, row in self.df.iterrows():
            lat = self.convert_dms_to_decimal(row.get('raw_lat'))
            lon = self.convert_dms_to_decimal(row.get('raw_lon'))
            if lat is None or lon is None: continue 
            
            bw = self.parse_bandwidth(row.get('raw_bw'))
            clean_freq = str(row.get('raw_freq', '')).replace(',', '.').replace('MHZ', '').replace('MHz', '').replace(';', ' ')
            
            # --- XỬ LÝ TÁCH TỈNH TỪ ĐỊA CHỈ ---
            raw_prov_extracted = ""
            if has_address:
                raw_addr = str(row.get('raw_address', ''))
                # Tách bằng dấu phẩy
                parts = raw_addr.split(',')
                if len(parts) > 0:
                    # Lấy phần tử cuối cùng (Thường là Tỉnh/Thành phố)
                    raw_prov_extracted = parts[-1]
                else:
                    raw_prov_extracted = raw_addr
            else:
                # Fallback nếu không tìm thấy cột địa chỉ thì dùng cột Tỉnh thành cũ
                raw_prov_extracted = str(row.get('raw_province_col', ''))

            # Chuẩn hóa (Xóa khoảng trắng, TP., dấu câu -> HANOI)
            clean_prov = chuan_hoa_text(raw_prov_extracted)
            
            freqs = []
            for item in clean_freq.split():
                try:
                    f = float(item)
                    if f > 10: freqs.append(f)
                except: pass
            
            net_type = "LAN"
            license_str = str(row.get('license', '')).upper()
            if "WAN" in license_str: 
                net_type = "WAN_SIMPLEX" 
            
            for f in freqs:
                cleaned_rows.append({
                    "freq": f, 
                    "bw": bw, 
                    "lat": lat, 
                    "lon": lon,
                    "province": clean_prov,    # Giá trị dùng để so sánh (VD: DANANG)
                    "raw_extracted": raw_prov_extracted, # Giá trị cắt được từ địa chỉ (để debug)
                    "h_anten": 20,
                    "net_type": net_type 
                })
        self.df = pd.DataFrame(cleaned_rows)

    def xac_dinh_kich_ban_user(self, user_input):
        mode = user_input.get('usage_mode', 'LAN')
        h = float(user_input.get('antenna_height', 0))
        prov_code = str(user_input.get('province_code', '')).upper()
        
        # 1. Xác định Thành phố lớn theo đúng tài liệu
        big_cities = ["HANOI", "HCM", "DANANG", "HOCHIMINH", "THANHPHOHOCHIMINH"] 
        user_prov_clean = chuan_hoa_text(prov_code)
        is_big_city = any(c == user_prov_clean for c in big_cities)
        
        # 2. Xử lý Logic Mạng WAN (Tách riêng Simplex/Duplex để tra đúng bảng Mục 3)
        if "WAN" in mode:
            if "SIMPLEX" in mode: 
                return ("WAN_SIMPLEX", "WAN_SIMPLEX")
            else:
                return ("WAN_DUPLEX", "WAN_DUPLEX")
        
        # 3. Xử lý Logic Mạng LAN
        if is_big_city:
            if h > 15:
                return ("LAN", "LAN_BIG_CITY_HIGH")
            else:
                return ("LAN", "LAN_BIG_CITY_LOW")
        else:
            return ("LAN", "LAN_PROVINCE")

    def get_required_distance(self, band, user_mode_tuple, db_net_type, tx_bw, delta_f, rx_bw):
        user_main_mode, user_scenario_key = user_mode_tuple
        matrix = None
        table_key = None
        
        is_intra_lan = ("LAN" in user_main_mode and "LAN" in db_net_type)
        is_intra_wan = ("WAN" in user_main_mode and "WAN" in db_net_type)
        
        if is_intra_lan or is_intra_wan:
            matrix = config.MATRIX_VHF if band == 'VHF' else config.MATRIX_UHF
            table_key = user_scenario_key
            if is_intra_wan and band == 'VHF': table_key = "WAN"
        else:
            matrix = config.MATRIX_CROSS
            if "LAN" in user_main_mode and "WAN_SIMPLEX" in db_net_type: table_key = "LAN_VS_WAN_SIMPLEX"
            elif "LAN" in user_main_mode and "WAN_DUPLEX" in db_net_type: table_key = "LAN_VS_WAN_DUPLEX"
            elif "WAN_SIMPLEX" in user_main_mode and "LAN" in db_net_type: table_key = "WAN_SIMPLEX_VS_LAN"
            elif "WAN_DUPLEX" in user_main_mode and "LAN" in db_net_type: table_key = "WAN_DUPLEX_VS_LAN"
            else: return 150.0

        if not matrix: return 150.0
        table_tx = matrix.get(table_key, {}).get(tx_bw)
        if not table_tx: table_tx = matrix.get(table_key, {}).get(12.5, {})

        val = abs(delta_f)
        if val < 3: key_d = 0
        elif val < 9: key_d = 6.25
        elif val < 15: key_d = 12.5
        elif val < 21: key_d = 18.75
        elif val < 30: key_d = 25.0
        else: return 0.0

        row_delta = table_tx.get(key_d, {})
        if rx_bw <= 9: key_rx = 6.25
        elif rx_bw <= 18: key_rx = 12.5
        else: key_rx = 25.0
        return row_delta.get(key_rx, 150.0)

    # --- ĐÃ SỬA LẠI HÀM NÀY ĐỂ CHẶN TẦN SỐ TỪ EXCEL NẾU SAI QUY HOẠCH ---
    def generate_candidates(self, band, bw, usage_mode):
        candidates = []
        allocations = config.FREQUENCY_ALLOCATION_VHF if band == 'VHF' else config.FREQUENCY_ALLOCATION_UHF
        step_mhz = bw / 1000.0 
        
        # 1. Sinh tần số từ QUY HOẠCH (Config)
        for start, end, modes, _ in allocations:
            if usage_mode in modes:
                curr = start
                while curr <= end:
                    in_res = any(r_s <= curr <= r_e for r_s, r_e, _ in config.RESTRICTED_RANGES)
                    if not in_res: candidates.append(round(curr, 5))
                    curr += step_mhz
        
        # 2. Lấy thêm tần số từ EXCEL (NHƯNG PHẢI CHECK LẠI QUY HOẠCH)
        # Nếu quy hoạch không cho phép Mode này, thì tần số trong Excel cũng không được lấy.
        if not self.df.empty:
            existing = self.df['freq'].unique()
            for f in existing:
                # Kiểm tra xem tần số f này có nằm trong bất kỳ dải nào CHO PHÉP mode hiện tại không
                is_valid_mode = False
                for start, end, modes, _ in allocations:
                    if start <= f <= end:
                        if usage_mode in modes:
                            is_valid_mode = True
                            break
                
                # Chỉ thêm nếu tần số đó hợp lệ với Quy hoạch
                if is_valid_mode:
                    candidates.append(f)
                    
        return sorted(list(set(candidates)))

    def tinh_toan(self, user_input):
        if self.df.empty: return []
        results = []
        
        user_mode_tuple = self.xac_dinh_kich_ban_user(user_input)
        band = user_input['band']
        bw = user_input['bw']
        mode = user_input['usage_mode']
        
        raw_input_prov = str(user_input.get('province_code', ''))
        user_province_clean = chuan_hoa_text(raw_input_prov)
        
        print(f"\n--- BẮT ĐẦU TÍNH TOÁN ---")
        print(f"User Input: '{raw_input_prov}' -> Đã chuẩn hóa: '{user_province_clean}'")
        
        candidates = self.generate_candidates(band, bw, mode)
        
        # Nếu danh sách rỗng (do quy hoạch chặn), trả về ngay
        if not candidates:
            return []

        df_freqs = self.df['freq'].values
        df_provinces = self.df['province'].values 
        
        debug_printed = False 

        for f_check in candidates:
            df_subset = self.df[np.abs(self.df['freq'] - f_check) < 0.035]
            is_usable = True
            
            for _, row in df_subset.iterrows():
                try:
                    dist_km = geodesic((user_input['lat'], user_input['lon']), 
                                       (row['lat'], row['lon'])).km
                except: continue
                
                delta_f = abs(f_check - row['freq']) * 1000
                rx_bw = row['bw']
                db_net_type = row['net_type'] 
                req_dist = self.get_required_distance(band, user_mode_tuple, db_net_type, bw, delta_f, rx_bw)
                if dist_km < req_dist:
                    is_usable = False
                    break 
            
            if is_usable:
                mask_freq_exact = np.abs(df_freqs - f_check) < 0.00001
                if "LAN" in mode:
                    mask_province = (df_provinces == user_province_clean)
                    count = np.sum(mask_freq_exact & mask_province)
                    if count > 0 and not debug_printed:
                        debug_printed = True
                else: 
                    count = np.sum(mask_freq_exact)
                    if count > 0 and not debug_printed:
                        debug_printed = True
                
                results.append({"frequency": f_check, "reuse_factor": int(count)})
        
        results.sort(key=lambda x: x['reuse_factor'], reverse=True)
        
        for i, item in enumerate(results):
            new_item = {
                "STT": i + 1,
                "frequency": item["frequency"],
                "reuse_factor": item["reuse_factor"]
            }
            results[i] = new_item
            
        return results