import pandas as pd
from geopy.distance import geodesic
import config # Import file config ở trên

# === CẤU HÌNH MAPPING CỘT EXCEL ===
# Bạn hãy sửa các giá trị bên phải cho đúng với Tiêu đề cột trong file Excel của bạn
EXCEL_COLUMNS = {
    "LICENSE_NO": "Số GP",          # Tên cột chứa số giấy phép
    "FREQUENCY": "Tần số phát",     # Tên cột chứa tần số (MHz)
    "BANDWIDTH": "Độ rộng kênh",    # Tên cột chứa băng thông (kHz)
    "LAT": "Vĩ độ",                 # Tên cột Vĩ độ
    "LON": "Kinh độ",               # Tên cột Kinh độ
    "ANTENNA_HEIGHT": "Độ cao anten", # Tên cột độ cao anten (m)
    "PROVINCE": "Tỉnh/TP"           # Tên cột Tỉnh thành
}

class ToolAnDinhTanSo:
    def __init__(self, excel_path):
        print(f"Đang đọc dữ liệu từ file: {excel_path}...")
        try:
            # Đọc file Excel hoặc CSV
            if excel_path.endswith('.csv'):
                self.df = pd.read_csv(excel_path)
            else:
                self.df = pd.read_excel(excel_path)
            
            # Chuẩn hóa dữ liệu: Đổi tên cột về chuẩn chung để code dễ xử lý
            self.df = self.df.rename(columns={
                EXCEL_COLUMNS["FREQUENCY"]: "freq",
                EXCEL_COLUMNS["BANDWIDTH"]: "bw",
                EXCEL_COLUMNS["LAT"]: "lat",
                EXCEL_COLUMNS["LON"]: "lon",
                EXCEL_COLUMNS["PROVINCE"]: "province",
                EXCEL_COLUMNS["ANTENNA_HEIGHT"]: "h_anten"
            })
            
            # Xóa các dòng dữ liệu rác (thiếu tọa độ hoặc tần số)
            self.df = self.df.dropna(subset=['freq', 'lat', 'lon'])
            print(f"Đã tải thành công {len(self.df)} giấy phép vào bộ nhớ.")
            
        except Exception as e:
            print(f"LỖI ĐỌC FILE: {e}")
            self.df = pd.DataFrame() # Tạo bảng rỗng nếu lỗi

    def xac_dinh_kich_ban(self, input_data):
        """ Xác định Scenario Code dựa trên Input người dùng """
        mode = input_data['usage_mode']
        h = input_data['antenna_height']
        prov = input_data['province_code']
        
        if "WAN" in mode and "SIMPLEX" in mode: return "WAN_SIMPLEX"
        if "WAN" in mode and "DUPLEX" in mode: return "WAN_DUPLEX"
        
        big_cities = ["HANOI", "HCM", "DANANG", "HÀ NỘI", "HỒ CHÍ MINH", "ĐÀ NẴNG"]
        # Chuẩn hóa chuỗi để so sánh (viết hoa)
        if prov.upper() in big_cities:
            return "LAN_BIG_CITY_HIGH" if h > 15 else "LAN_BIG_CITY_LOW"
        return "LAN_PROVINCE"

    def tinh_toan(self, user_input):
        """
        Hàm xử lý chính.
        user_input = { 'lat': ..., 'lon': ..., 'band': 'VHF', 'bw': 12.5, ... }
        """
        results = []
        scenario = self.xac_dinh_kich_ban(user_input)
        
        # 1. Tạo danh sách tần số giả định để kiểm tra (Candidate)
        # Trong thực tế, đoạn này sẽ lấy từ config.FREQUENCY_ALLOCATION
        # Ở đây tôi ví dụ kiểm tra 1 tần số người dùng nhập hoặc 1 dải
        candidates = [148.000, 148.025, 148.050] # Ví dụ
        
        print(f"Bắt đầu tính toán cho kịch bản: {scenario}")
        
        for f_check in candidates:
            is_usable = True
            reuse_count = 0
            
            # --- TỐI ƯU HÓA: PRE-FILTER ---
            # Chỉ lấy các giấy phép có tần số lân cận (+- 0.05 MHz) để đỡ phải tính khoảng cách hết
            # Và nằm trong hộp tọa độ sơ bộ (+- 2 độ ~ 200km)
            df_subset = self.df[
                (abs(self.df['freq'] - f_check) <= 0.05) & 
                (abs(self.df['lat'] - user_input['lat']) < 1.5) &
                (abs(self.df['lon'] - user_input['lon']) < 1.5)
            ]
            
            # Vòng lặp kiểm tra từng giấy phép trong danh sách đã lọc
            for index, row in df_subset.iterrows():
                # Tính khoảng cách địa lý (km)
                dist_km = geodesic((user_input['lat'], user_input['lon']), 
                                   (row['lat'], row['lon'])).km
                
                # Tính Delta F (kHz)
                delta_f = abs(f_check - row['freq']) * 1000 
                delta_f_norm = self.normalize_delta_f(delta_f) # Quy về 0, 6.25, 12.5
                
                # Lấy khoảng cách yêu cầu từ Config
                try:
                    rule = config.REUSE_MATRIX[scenario][user_input['bw']][delta_f_norm]
                    req_dist = rule[0] if user_input['band'] == 'VHF' else rule[1]
                except KeyError:
                    req_dist = 150.0 # Mặc định an toàn nếu không tìm thấy luật
                
                # SO SÁNH
                if dist_km < req_dist:
                    is_usable = False
                    # print(f"Nhiễu với GP tại {dist_km:.2f}km (Yêu cầu {req_dist}km)")
                    break
                else:
                    reuse_count += 1
            
            if is_usable:
                results.append({
                    "frequency": f_check,
                    "reuse_factor": reuse_count
                })
        
        # Sắp xếp kết quả
        results.sort(key=lambda x: x['reuse_factor'], reverse=True)
        return results

    def normalize_delta_f(self, val):
        """ Quy đổi delta f về các mốc 0, 6.25, 12.5, 25 để tra bảng """
        # Logic làm tròn đơn giản, cần tinh chỉnh theo quy định thực tế
        if val < 3: return 0
        if val < 9: return 6.25
        if val < 15: return 12.5
        if val < 22: return 18.75
        return 25

# === CHẠY THỬ ===
if __name__ == "__main__":
    # Đường dẫn file Excel của bạn
    file_path = "Sample data pWR.xls - Sheet1.csv" 
    
    tool = ToolAnDinhTanSo(file_path)
    
    # Input giả lập từ giao diện Web
    input_mau = {
        "lat": 21.02, "lon": 105.85, # Hà Nội
        "province_code": "HANOI",
        "antenna_height": 20,
        "band": "VHF",
        "bw": 12.5,
        "usage_mode": "LAN"
    }
    
    kq = tool.tinh_toan(input_mau)
    print("Kết quả tần số khả dụng:", kq)