import streamlit as st
import time
import random
import folium
from streamlit_folium import st_folium
import pandas as pd
import math
import json
import os

# --- 坐标系转换函数 ---  
def wgs84_to_gcj02(lat, lon):
    """WGS-84坐标系转GCJ-02坐标系"""
    if out_of_china(lat, lon):
        return lat, lon
    dLat, dLon = transform(lat, lon)
    radLat = lat * math.pi / 180
    magic = math.sin(radLat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtMagic) * math.pi)
    dLon = (dLon * 180) / (6378245.0 / sqrtMagic * math.cos(radLat) * math.pi)
    gcjLat = lat + dLat
    gcjLon = lon + dLon
    return gcjLat, gcjLon

def gcj02_to_wgs84(lat, lon):
    """GCJ-02坐标系转WGS-84坐标系"""
    if out_of_china(lat, lon):
        return lat, lon
    dLat, dLon = transform(lat, lon)
    radLat = lat * math.pi / 180
    magic = math.sin(radLat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtMagic) * math.pi)
    dLon = (dLon * 180) / (6378245.0 / sqrtMagic * math.cos(radLat) * math.pi)
    wgsLat = lat - dLat
    wgsLon = lon - dLon
    return wgsLat, wgsLon

def transform(lat, lon):
    """坐标系转换核心算法"""
    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 扁率
    dLat = transformLat(lon - 105.0, lat - 35.0)
    dLon = transformLon(lon - 105.0, lat - 35.0)
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * math.pi)
    dLon = (dLon * 180.0) / (a / sqrtMagic * math.cos(radLat) * math.pi)
    return dLat, dLon

def transformLat(x, y):
    """纬度转换"""
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def transformLon(x, y):
    """经度转换"""
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def out_of_china(lat, lon):
    """判断坐标是否在国内"""
    return not (73.66 < lon < 135.05 and 3.86 < lat < 53.55)

# --- 航线规划辅助函数 ---
def calculate_distance(point1, point2):
    """计算两个点之间的距离（使用Haversine公式）"""
    lat1, lon1 = point1
    lat2, lon2 = point2
    
    # 地球半径（米）
    R = 6371000
    
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 差值
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine公式
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def point_in_polygon(point, polygon):
    """判断点是否在多边形内（使用射线法）"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(n+1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def line_intersects_polygon(line_start, line_end, polygon):
    """判断线段是否与多边形相交"""
    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i+1) % len(polygon)]
        if segments_intersect(line_start, line_end, p1, p2):
            return True
    return False

def segments_intersect(a1, a2, b1, b2):
    """判断两条线段是否相交"""
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    
    return ccw(a1, b1, b2) != ccw(a2, b1, b2) and ccw(a1, a2, b1) != ccw(a1, a2, b2)

def plan_route(a_point, b_point, obstacles, drone_height, safety_radius, route_option):
    """规划航线"""
    # 检查是否需要绕行
    need_detour = False
    obstacles_to_avoid = []
    
    for obstacle in obstacles:
        points = obstacle['points'] if isinstance(obstacle, dict) else obstacle
        height = obstacle.get('height', 0) if isinstance(obstacle, dict) else 0
        
        # 如果无人机飞行高度大于障碍物高度，可以直接飞跃
        if drone_height > height:
            continue
        
        # 检查航线是否与障碍物相交
        if line_intersects_polygon(a_point, b_point, points):
            need_detour = True
            obstacles_to_avoid.append(obstacle)
    
    if not need_detour:
        # 直接飞行
        return [a_point, b_point]
    
    # 需要绕行，根据选择的选项生成不同的航线
    if route_option == "向左绕行":
        return plan_left_detour(a_point, b_point, obstacles_to_avoid, safety_radius)
    elif route_option == "向右绕行":
        return plan_right_detour(a_point, b_point, obstacles_to_avoid, safety_radius)
    else:  # 最佳航线
        left_route = plan_left_detour(a_point, b_point, obstacles_to_avoid, safety_radius)
        right_route = plan_right_detour(a_point, b_point, obstacles_to_avoid, safety_radius)
        
        # 选择较短的航线
        left_distance = calculate_route_distance(left_route)
        right_distance = calculate_route_distance(right_route)
        
        return left_route if left_distance < right_distance else right_route

def calculate_route_distance(route):
    """计算航线总距离"""
    total_distance = 0
    for i in range(len(route)-1):
        total_distance += calculate_distance(route[i], route[i+1])
    return total_distance

def plan_left_detour(a_point, b_point, obstacles, safety_radius):
    """规划向左绕行的航线"""
    # 简化实现：在AB连线的左侧生成一个绕行点
    lat_a, lon_a = a_point
    lat_b, lon_b = b_point
    
    # 计算AB向量
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    
    # 计算垂直向量（向左）
    perp_lat = -delta_lon
    perp_lon = delta_lat
    
    # 归一化
    length = math.sqrt(perp_lat**2 + perp_lon**2)
    if length > 0:
        perp_lat /= length
        perp_lon /= length
    
    # 计算绕行点（距离AB连线一定距离）
    detour_distance = safety_radius * 2  # 安全距离的2倍
    mid_lat = (lat_a + lat_b) / 2
    mid_lon = (lon_a + lon_b) / 2
    
    # 转换距离为经纬度差（近似计算）
    # 1度纬度约为111320米
    # 1度经度在赤道约为111320米，随纬度增加而减小
    lat_offset = (detour_distance / 111320) * perp_lat
    lon_offset = (detour_distance / (111320 * math.cos(math.radians(mid_lat)))) * perp_lon
    
    detour_point = (mid_lat + lat_offset, mid_lon + lon_offset)
    
    return [a_point, detour_point, b_point]

def plan_right_detour(a_point, b_point, obstacles, safety_radius):
    """规划向右绕行的航线"""
    # 简化实现：在AB连线的右侧生成一个绕行点
    lat_a, lon_a = a_point
    lat_b, lon_b = b_point
    
    # 计算AB向量
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    
    # 计算垂直向量（向右）
    perp_lat = delta_lon
    perp_lon = -delta_lat
    
    # 归一化
    length = math.sqrt(perp_lat**2 + perp_lon**2)
    if length > 0:
        perp_lat /= length
        perp_lon /= length
    
    # 计算绕行点（距离AB连线一定距离）
    detour_distance = safety_radius * 2  # 安全距离的2倍
    mid_lat = (lat_a + lat_b) / 2
    mid_lon = (lon_a + lon_b) / 2
    
    # 转换距离为经纬度差（近似计算）
    lat_offset = (detour_distance / 111320) * perp_lat
    lon_offset = (detour_distance / (111320 * math.cos(math.radians(mid_lat)))) * perp_lon
    
    detour_point = (mid_lat + lat_offset, mid_lon + lon_offset)
    
    return [a_point, detour_point, b_point]

# --- 1. 页面配置 ---
st.set_page_config(page_title="无人机智能监控系统", layout="wide")

# --- 2. 初始化数据 ---
if 'points' not in st.session_state:
    st.session_state.points = []  # 存储心跳包数据
if 'a_point' not in st.session_state:
    st.session_state.a_point = None  # A点坐标
if 'b_point' not in st.session_state:
    st.session_state.b_point = None  # B点坐标
if 'obstacles' not in st.session_state:
    st.session_state.obstacles = []  # 存储障碍物数据 [{'points': [...], 'height': ...}]
if 'current_obstacle' not in st.session_state:
    st.session_state.current_obstacle = []  # 存储当前正在绘制的障碍物
if 'current_obstacle_height' not in st.session_state:
    st.session_state.current_obstacle_height = 10  # 当前障碍物高度默认值
if 'map_click_mode' not in st.session_state:
    st.session_state.map_click_mode = False  # 地图点击模式开关
if 'drone_height' not in st.session_state:
    st.session_state.drone_height = 20  # 无人机飞行高度默认值（米）
if 'safety_radius' not in st.session_state:
    st.session_state.safety_radius = 5  # 安全半径默认值（米）
if 'planned_route' not in st.session_state:
    st.session_state.planned_route = None  # 规划的航线
if 'route_option' not in st.session_state:
    st.session_state.route_option = "最佳航线"  # 航线选项

# --- 3. 侧边栏：页面选择 ---
st.sidebar.title("导航")
page = st.sidebar.radio("选择功能", ["航线规划", "飞行监控"])

# --- 4. 功能实现 ---
if page == "航线规划":
    st.title("📍 航线规划界面")

    # --- 坐标系选择 ---
    st.subheader("坐标系设置")
    coord_system = st.radio("输入坐标系", ["WGS-84", "GCJ-02 (高德/百度)"], index=1)
    st.info(f"当前选择坐标系：**{coord_system}**")

    # --- 获取当前位置 ---
    st.subheader("获取当前位置")
    st.markdown("""
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(showPosition, showError);
        } else {
            alert("浏览器不支持地理定位");
        }
    }
    function showPosition(position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        window.parent.postMessage({type: 'location', lat: lat, lon: lon}, '*');
    }
    function showError(error) {
        switch(error.code) {
            case error.PERMISSION_DENIED:
                alert("用户拒绝了地理定位请求");
                break;
            case error.POSITION_UNAVAILABLE:
                alert("位置信息不可用");
                break;
            case error.TIMEOUT:
                alert("获取位置超时");
                break;
            case error.UNKNOWN_ERROR:
                alert("发生未知错误");
                break;
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    if st.button("获取当前位置", on_click=lambda: st.markdown("<script>getLocation();</script>", unsafe_allow_html=True)):
        st.info("请允许浏览器访问您的位置...")
    
    # 处理从前端获取的位置数据
    if 'lat' in st.session_state and 'lon' in st.session_state:
        current_lat = st.session_state.lat
        current_lon = st.session_state.lon
        st.success(f"当前位置：({current_lat:.6f}, {current_lon:.6f})")

    # --- A点设置 ---
    st.subheader("起点 A")
    col1, col2 = st.columns(2)
    with col1:
        lat_a = st.number_input("纬度", value=32.2332, format="%.6f", key="lat_a")
    with col2:
        lon_a = st.number_input("经度", value=118.749, format="%.6f", key="lon_a")
    
    # 一键设置A点为当前位置
    if 'lat' in st.session_state and 'lon' in st.session_state:
        if st.button("设置 A 点为当前位置"):
            st.session_state.a_point = (st.session_state.lat, st.session_state.lon)
            st.success("A 点设置为当前位置成功！")
    
    if st.button("设置 A 点"):
        # 根据选择的坐标系进行转换
        if coord_system == "WGS-84":
            # 转换为GCJ-02用于显示
            transformed_lat, transformed_lon = wgs84_to_gcj02(lat_a, lon_a)
            st.session_state.a_point = (transformed_lat, transformed_lon)
        else:
            st.session_state.a_point = (lat_a, lon_a)
        st.success("A 点设置成功！")

    # --- B点设置 ---
    st.subheader("终点 B")
    col1, col2 = st.columns(2)
    with col1:
        lat_b = st.number_input("纬度", value=32.2343, format="%.6f", key="lat_b")
    with col2:
        lon_b = st.number_input("经度", value=118.750, format="%.6f", key="lon_b")
    
    # 一键设置B点为当前位置
    if 'lat' in st.session_state and 'lon' in st.session_state:
        if st.button("设置 B 点为当前位置"):
            st.session_state.b_point = (st.session_state.lat, st.session_state.lon)
            st.success("B 点设置为当前位置成功！")
    
    if st.button("设置 B 点"):
        # 根据选择的坐标系进行转换
        if coord_system == "WGS-84":
            # 转换为GCJ-02用于显示
            transformed_lat, transformed_lon = wgs84_to_gcj02(lat_b, lon_b)
            st.session_state.b_point = (transformed_lat, transformed_lon)
        else:
            st.session_state.b_point = (lat_b, lon_b)
        st.success("B 点设置成功！")

    # --- 障碍物圈选 ---
    st.subheader("🚧 障碍物圈选")
    
    # 障碍物高度设置
    st.subheader("障碍物高度设置")
    obstacle_height = st.number_input("障碍物高度 (米)", min_value=0.1, value=st.session_state.current_obstacle_height, step=0.5, key="obstacle_height")
    st.session_state.current_obstacle_height = obstacle_height
    
    # 地图点击模式
    st.subheader("地图点击模式")
    map_click_mode = st.checkbox("启用地图点击添加障碍物点", value=st.session_state.map_click_mode, key="map_click_mode")
    st.session_state.map_click_mode = map_click_mode
    
    if map_click_mode:
        st.info("已启用地图点击模式，请在地图上点击添加障碍物顶点")
    else:
        st.info("使用多边形圈选障碍物区域，点击地图上的点来添加障碍物顶点")
    
    # 障碍物点输入
    col1, col2 = st.columns(2)
    with col1:
        obs_lat = st.number_input("障碍物点纬度", value=32.2335, format="%.6f", key="obs_lat")
    with col2:
        obs_lon = st.number_input("障碍物点经度", value=118.7495, format="%.6f", key="obs_lon")
    
    # 控制按钮
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("添加障碍物点"):
            # 根据选择的坐标系进行转换
            if coord_system == "WGS-84":
                transformed_lat, transformed_lon = wgs84_to_gcj02(obs_lat, obs_lon)
                st.session_state.current_obstacle.append((transformed_lat, transformed_lon))
            else:
                st.session_state.current_obstacle.append((obs_lat, obs_lon))
            st.success(f"已添加点: ({obs_lat:.6f}, {obs_lon:.6f})")
    with col2:
        if st.button("完成障碍物"):
            if len(st.session_state.current_obstacle) >= 3:
                # 保存障碍物数据，包含点和高度
                obstacle_data = {
                    'points': st.session_state.current_obstacle.copy(),
                    'height': st.session_state.current_obstacle_height
                }
                st.session_state.obstacles.append(obstacle_data)
                st.session_state.current_obstacle = []
                st.success("障碍物圈选完成！")
            else:
                st.warning("障碍物至少需要3个点！")
    with col3:
        if st.button("清除当前障碍物"):
            st.session_state.current_obstacle = []
            st.success("已清除当前障碍物")
    with col4:
        if st.button("清除所有障碍物"):
            st.session_state.obstacles = []
            st.session_state.current_obstacle = []
            st.success("已清除所有障碍物")
    
    # --- 无人机参数设置 ---
    st.subheader("无人机参数设置")
    col1, col2 = st.columns(2)
    with col1:
        drone_height = st.number_input("无人机飞行高度 (米)", min_value=0.1, value=st.session_state.drone_height, step=1.0, key="drone_height")
        st.session_state.drone_height = drone_height
    with col2:
        safety_radius = st.number_input("安全半径 (米)", min_value=0.1, value=st.session_state.safety_radius, step=0.5, key="safety_radius")
        st.session_state.safety_radius = safety_radius
    
    # --- 航线规划选项 ---
    st.subheader("航线规划选项")
    route_option = st.radio(
        "选择航线类型",
        ["最佳航线", "向左绕行", "向右绕行"],
        index=["最佳航线", "向左绕行", "向右绕行"].index(st.session_state.route_option),
        key="route_option"
    )
    st.session_state.route_option = route_option
    
    # 规划航线按钮
    if st.button("规划航线"):
        if st.session_state.a_point and st.session_state.b_point:
            # 调用航线规划函数
            planned_route = plan_route(
                st.session_state.a_point,
                st.session_state.b_point,
                st.session_state.obstacles,
                st.session_state.drone_height,
                st.session_state.safety_radius,
                st.session_state.route_option
            )
            st.session_state.planned_route = planned_route
            
            # 计算航线距离
            route_distance = calculate_route_distance(planned_route)
            st.success(f"已规划{route_option}！航线距离：{route_distance:.2f}米")
        else:
            st.warning("请先设置 A 点和 B 点！")
    
    # 障碍物数据导入导出
    st.subheader("障碍物数据管理")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存障碍物数据为JSON"):
            if st.session_state.obstacles:
                # 准备保存的数据
                save_data = {
                    'obstacles': st.session_state.obstacles,
                    'a_point': st.session_state.a_point,
                    'b_point': st.session_state.b_point,
                    'drone_height': st.session_state.drone_height,
                    'safety_radius': st.session_state.safety_radius
                }
                # 生成文件名
                filename = f"obstacles_{time.strftime('%Y%m%d_%H%M%S')}.json"
                # 保存文件
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                st.success(f"障碍物数据已保存为: {filename}")
                # 提供下载链接
                with open(filename, 'r', encoding='utf-8') as f:
                    st.download_button(
                        label="下载JSON文件",
                        data=f.read(),
                        file_name=filename,
                        mime="application/json"
                    )
            else:
                st.warning("没有障碍物数据可保存！")
    with col2:
        uploaded_file = st.file_uploader("从JSON文件加载障碍物数据", type="json")
        if uploaded_file is not None:
            try:
                load_data = json.load(uploaded_file)
                if 'obstacles' in load_data:
                    st.session_state.obstacles = load_data['obstacles']
                    if 'a_point' in load_data:
                        st.session_state.a_point = load_data['a_point']
                    if 'b_point' in load_data:
                        st.session_state.b_point = load_data['b_point']
                    if 'drone_height' in load_data:
                        st.session_state.drone_height = load_data['drone_height']
                    if 'safety_radius' in load_data:
                        st.session_state.safety_radius = load_data['safety_radius']
                    st.success("障碍物数据加载成功！")
                else:
                    st.warning("JSON文件格式不正确，缺少obstacles字段！")
            except json.JSONDecodeError:
                st.error("JSON文件格式错误！")
    
    # 显示当前正在绘制的障碍物
    if st.session_state.current_obstacle:
        st.write("当前正在绘制的障碍物点:")
        for i, point in enumerate(st.session_state.current_obstacle):
            st.write(f"点 {i+1}: ({point[0]:.6f}, {point[1]:.6f})")
    
    # 显示已保存的障碍物
    if st.session_state.obstacles:
        st.write(f"已保存的障碍物数量: {len(st.session_state.obstacles)}")
    
    # --- 地图显示 ---
    st.subheader("地图显示")
    if st.session_state.a_point and st.session_state.b_point:
        # 创建卫星图地图（ArcGIS World Imagery）
        m = folium.Map(
            location=st.session_state.a_point,
            zoom_start=18,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='ArcGIS World Imagery'
        )

        # 添加地图点击事件
        if st.session_state.map_click_mode:
            m.add_child(folium.ClickForMarker(popup="点击添加障碍物点"))

        # 在地图上标记 A 点和 B 点
        folium.Marker(st.session_state.a_point, popup="起点 A", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(st.session_state.b_point, popup="终点 B", icon=folium.Icon(color="red")).add_to(m)

        # 画一条线连接 A 和 B
        folium.PolyLine([st.session_state.a_point, st.session_state.b_point], color="blue").add_to(m)

        # 显示当前正在绘制的障碍物
        if st.session_state.current_obstacle:
            # 显示障碍物顶点
            for i, point in enumerate(st.session_state.current_obstacle):
                folium.Marker(point, popup=f"障碍物点 {i+1}", icon=folium.Icon(color="yellow")).add_to(m)
            # 显示障碍物边
            if len(st.session_state.current_obstacle) > 1:
                folium.PolyLine(st.session_state.current_obstacle, color="yellow", dash_array="5, 5").add_to(m)

        # 显示已保存的障碍物
        for i, obstacle in enumerate(st.session_state.obstacles):
            # 显示障碍物多边形
            points = obstacle['points'] if isinstance(obstacle, dict) else obstacle
            height = obstacle.get('height', 0) if isinstance(obstacle, dict) else 0
            folium.Polygon(
                points,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.3,
                popup=f"障碍物 {i+1}\n高度: {height} 米"
            ).add_to(m)

        # 显示规划的航线
        if st.session_state.planned_route:
            folium.PolyLine(
                st.session_state.planned_route,
                color="green",
                weight=3,
                opacity=1,
                popup=f"规划航线\n距离: {calculate_route_distance(st.session_state.planned_route):.2f}米"
            ).add_to(m)
            # 标记航线点
            for i, point in enumerate(st.session_state.planned_route):
                if i == 0:
                    folium.Marker(point, popup="起点", icon=folium.Icon(color="green")).add_to(m)
                elif i == len(st.session_state.planned_route) - 1:
                    folium.Marker(point, popup="终点", icon=folium.Icon(color="red")).add_to(m)
                else:
                    folium.Marker(point, popup=f"途经点 {i}", icon=folium.Icon(color="blue")).add_to(m)

        # 在网页上显示地图
        map_data = st_folium(m, width=700, height=500, key="map")
        
        # 处理地图点击事件
        if st.session_state.map_click_mode and map_data and map_data.get('last_clicked'):
            lat = map_data['last_clicked']['lat']
            lon = map_data['last_clicked']['lng']
            # 添加点击的点到当前障碍物
            st.session_state.current_obstacle.append((lat, lon))
            st.success(f"已添加点: ({lat:.6f}, {lon:.6f})")
    else:
        st.warning("请先设置 A 点和 B 点！")

elif page == "飞行监控":
    st.title("📡 飞行监控界面")

    # --- 模拟心跳包数据 ---
    st.subheader("实时心跳包数据")
    if st.button("开始发送心跳包"):
        for i in range(10):  # 模拟发送 10 个数据包
            time.sleep(1)  # 每隔 1 秒发送一次
            # 模拟数据：序号、时间、经纬度（这里用随机数模拟无人机位置变化）
            seq = i + 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            lat = random.uniform(32.2330, 32.2350)  # 随机纬度
            lon = random.uniform(118.7480, 118.7510)  # 随机经度

            # 存储数据
            st.session_state.points.append({
                "序号": seq,
                "时间": timestamp,
                "纬度": lat,
                "经度": lon
            })

            # 在页面上显示最新一条数据
            st.write(f"序号: {seq}, 时间: {timestamp}, 位置: ({lat:.6f}, {lon:.6f})")

        st.success("心跳包发送完成！")

    # --- 显示历史数据 ---
    if st.session_state.points:
        st.subheader("历史数据表格")
        df = pd.DataFrame(st.session_state.points)
        st.dataframe(df)

        # --- 数据可视化 ---
        st.subheader("飞行轨迹图")
        # 如果有 A 点和 B 点，画地图
        if st.session_state.a_point and st.session_state.b_point:
            m = folium.Map(
                location=st.session_state.a_point,
                zoom_start=18,
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='ArcGIS World Imagery'
            )
            folium.Marker(st.session_state.a_point, popup="起点 A", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(st.session_state.b_point, popup="终点 B", icon=folium.Icon(color="red")).add_to(m)
            folium.PolyLine([st.session_state.a_point, st.session_state.b_point], color="blue").add_to(m)

            # 画出无人机飞行轨迹
            points = [(p["纬度"], p["经度"]) for p in st.session_state.points]
            if points:
                # 确保轨迹点使用正确的坐标系
                transformed_points = []
                for point in points:
                    # 假设原始数据是WGS-84，转换为GCJ-02
                    transformed_lat, transformed_lon = wgs84_to_gcj02(point[0], point[1])
                    transformed_points.append((transformed_lat, transformed_lon))
                folium.PolyLine(transformed_points, color="orange", weight=2.5, opacity=1).add_to(m)

            # 显示已保存的障碍物
            for i, obstacle in enumerate(st.session_state.obstacles):
                # 显示障碍物多边形
                points = obstacle['points'] if isinstance(obstacle, dict) else obstacle
                height = obstacle.get('height', 0) if isinstance(obstacle, dict) else 0
                folium.Polygon(
                    points,
                    color="red",
                    fill=True,
                    fill_color="red",
                    fill_opacity=0.3,
                    popup=f"障碍物 {i+1}\n高度: {height} 米"
                ).add_to(m)

            st_folium(m, width=700, height=500)
        else:
            st.warning("请先在""航线规划""页面设置 A 点和 B 点！")

# 添加JavaScript来处理位置信息
st.markdown("""
<script>
// 监听来自子页面的消息
window.addEventListener('message', function(event) {
    if (event.data.type === 'location') {
        // 发送位置数据到Streamlit
        fetch('/_stcore/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: 'set_state',
                key: 'lat',
                value: event.data.lat
            })
        });
        fetch('/_stcore/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: 'set_state',
                key: 'lon',
                value: event.data.lon
            })
        });
    }
});
</script>
""", unsafe_allow_html=True)