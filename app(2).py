import streamlit as st
import time
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="无人机心跳监控系统", layout="wide")

if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []

if 'sequence_number' not in st.session_state:
    st.session_state.sequence_number = 0

if 'last_receive_time' not in st.session_state:
    st.session_state.last_receive_time = time.time()

if 'is_connected' not in st.session_state:
    st.session_state.is_connected = True

def generate_heartbeat():
    st.session_state.sequence_number += 1
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.last_receive_time = time.time()
    return {
        "序号": st.session_state.sequence_number,
        "时间戳": timestamp,
        "状态": "正常",
        "系统时间": current_time
    }

def check_connection_timeout():
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_receive_time
    if time_since_last >= 3:
        st.session_state.is_connected = False
        current_time_obj = datetime.now()
        timestamp = current_time_obj.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "序号": st.session_state.sequence_number,
            "时间戳": timestamp,
            "状态": "超时",
            "系统时间": current_time_obj
        }
    st.session_state.is_connected = True
    return None

def simulate_heartbeat():
    timeout_data = check_connection_timeout()
    if timeout_data:
        st.session_state.heartbeat_data.append(timeout_data)
        return
    
    heartbeat = generate_heartbeat()
    st.session_state.heartbeat_data.append(heartbeat)
    
    if len(st.session_state.heartbeat_data) > 50:
        st.session_state.heartbeat_data = st.session_state.heartbeat_data[-50:]

st.title("🚁 无人机心跳监控系统")

col1, col2 = st.columns([3, 1])

with col2:
    st.subheader("连接状态")
    status_color = "green" if st.session_state.is_connected else "red"
    status_text = "🟢 正常" if st.session_state.is_connected else "🔴 超时"
    st.markdown(f"<h2 style='color:{status_color};text-align:center'>{status_text}</h2>", unsafe_allow_html=True)
    
    if not st.session_state.is_connected:
        st.error("⚠️ 警告：连续3秒未收到心跳，连接超时！")
    
    st.subheader("统计信息")
    total_count = len(st.session_state.heartbeat_data)
    normal_count = sum(1 for d in st.session_state.heartbeat_data if d["状态"] == "正常")
    timeout_count = total_count - normal_count
    st.metric("总心跳数", total_count)
    st.metric("正常心跳", normal_count)
    st.metric("超时次数", timeout_count)

with col1:
    st.subheader("心跳包时序图")
    
    if st.session_state.heartbeat_data:
        df = pd.DataFrame(st.session_state.heartbeat_data)
        df['颜色'] = df['状态'].apply(lambda x: 'green' if x == '正常' else 'red')
        
        fig = px.line(
            df,
            x='系统时间',
            y='序号',
            color='颜色',
            title='心跳包序号变化',
            labels={'系统时间': '时间', '序号': '心跳序号'},
            template='plotly_dark'
        )
        fig.update_traces(mode='markers+lines', line=dict(width=2), marker=dict(size=6))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("最新心跳记录")
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.info("等待心跳数据...")

placeholder = st.empty()

while True:
    simulate_heartbeat()
    
    with placeholder.container():
        with col2:
            status_color = "green" if st.session_state.is_connected else "red"
            status_text = "🟢 正常" if st.session_state.is_connected else "🔴 超时"
            st.markdown(f"<h2 style='color:{status_color};text-align:center'>{status_text}</h2>", unsafe_allow_html=True)
            
            if not st.session_state.is_connected:
                st.error("⚠️ 警告：连续3秒未收到心跳，连接超时！")
            
            total_count = len(st.session_state.heartbeat_data)
            normal_count = sum(1 for d in st.session_state.heartbeat_data if d["状态"] == "正常")
            timeout_count = total_count - normal_count
            st.metric("总心跳数", total_count)
            st.metric("正常心跳", normal_count)
            st.metric("超时次数", timeout_count)
        
        with col1:
            if st.session_state.heartbeat_data:
                df = pd.DataFrame(st.session_state.heartbeat_data)
                df['颜色'] = df['状态'].apply(lambda x: 'green' if x == '正常' else 'red')
                
                fig = px.line(
                    df,
                    x='系统时间',
                    y='序号',
                    color='颜色',
                    title='心跳包序号变化',
                    labels={'系统时间': '时间', '序号': '心跳序号'},
                    template='plotly_dark'
                )
                fig.update_traces(mode='markers+lines', line=dict(width=2), marker=dict(size=6))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("最新心跳记录")
                st.dataframe(df.tail(10), use_container_width=True)
    
    time.sleep(1)