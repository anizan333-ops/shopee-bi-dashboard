import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from shopee_bi_engine import ShopeeBIEngine

st.set_page_config(page_title="Shopee BI & Profit Optimization Tool", layout="wide")

st.title("🛒 Shopee Business Intelligence, Profit Optimization & Reverse Growth Planner")
st.markdown("""
**Standar Analisis:** *Senior E-commerce Analyst, CFO, Performance Marketing Strategist, Shopee Specialist & Reverse Planner.*  
Fokus utama: **Laba Bersih, Arus Kas, Ekonomi Unit SKU, dan Efisiensi Biaya (Bukan Sekadar Kejar Omzet).**
""")

# -------------------------------------------------------------------------
# SIDEBAR: PARAMETER CFO & REVERSE PLANNING
# -------------------------------------------------------------------------
st.sidebar.header("⚙️ Parameter Audit & Reverse Plan")
target_profit = st.sidebar.number_input("Target Laba Bersih Tahunan (Rp)", value=600_000_000, step=50_000_000)
assumed_mp_rate = st.sidebar.slider("Asumsi Awal Biaya Shopee + PPh (%)", min_value=10.0, max_value=35.0, value=24.0, step=0.5) / 100.0
actual_mp_rate = st.sidebar.slider("Hasil Audit Aktual Biaya Shopee + PPh (%)", min_value=8.0, max_value=30.0, value=18.5, step=0.5) / 100.0
conv_rate = st.sidebar.slider("Tingkat Konversi Toko (%)", min_value=0.5, max_value=10.0, value=2.5, step=0.1) / 100.0
avg_cpc = st.sidebar.number_input("Rata-rata CPC Iklan Shopee (Rp)", value=350, step=25)
paid_share = st.sidebar.slider("Proporsi Trafik Berbayar / Iklan (%)", min_value=10, max_value=90, value=35, step=5) / 100.0

engine = ShopeeBIEngine(target_annual_profit=target_profit, assumed_mp_tax_rate=assumed_mp_rate)

# -------------------------------------------------------------------------
# FUNGSI PEMBUAT TEMPLATE / DATA SIMULASI JIKA FILE BELUM DIUNGGAH
# -------------------------------------------------------------------------
def load_sample_data():
    df_monthly = pd.DataFrame({
        'bulan': ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'],
        'omzet_kotor': [180e6, 195e6, 310e6, 240e6, 190e6, 210e6, 205e6, 215e6, 230e6, 260e6, 320e6, 315e6],
        'penjualan_bersih': [165e6, 180e6, 285e6, 220e6, 175e6, 195e6, 190e6, 200e6, 212e6, 240e6, 290e6, 288e6],
        'jumlah_pesanan_selesai': [1100, 1200, 1850, 1450, 1150, 1280, 1250, 1310, 1380, 1550, 1950, 1920],
        'unit_terjual': [1650, 1800, 2900, 2200, 1750, 1950, 1900, 2000, 2120, 2400, 3000, 2950],
        'hpp': [82.5e6, 90e6, 142.5e6, 110e6, 87.5e6, 97.5e6, 95e6, 100e6, 106e6, 120e6, 148e6, 146e6],
        'total_biaya_mp': [29.7e6, 32.4e6, 51.3e6, 39.6e6, 31.5e6, 35.1e6, 34.2e6, 36.0e6, 38.16e6, 43.2e6, 55.1e6, 54.7e6],
        'biaya_iklan': [18e6, 20e6, 38e6, 28e6, 19e6, 21e6, 20e6, 22e6, 24e6, 29e6, 48e6, 46e6],
        'biaya_operasional': [15e6, 15e6, 18e6, 16e6, 15e6, 15e6, 15e6, 15e6, 16e6, 16e6, 19e6, 19e6]
    })

    df_sku = pd.DataFrame({
        'kode_sku': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004', 'SKU-005', 'SKU-006'],
        'nama_sku': [
            'Serum Wajah Brightening 30ml (Hero)',
            'Facial Wash Gentle 100ml (Traffic)',
            'Paket Glowing Lengkap 4-in-1 (Hero Bundling)',
            'Krim Malam Retinol 15g (Growth)',
            'Masker Wajah Sheet Mask (Margin Trap)',
            'Toner Mist Ukuran Lama (Dead Weight)'
        ],
        'harga_jual_aktual': [125000, 65000, 280000, 145000, 25000, 85000],
        'diskon_penjual_per_unit': [5000, 3000, 15000, 5000, 3000, 10000],
        'jumlah_terjual': [8500, 7200, 3200, 1400, 5800, 420],
        'hpp_per_unit': [48000, 31000, 110000, 52000, 14500, 48000],
        'tarif_mp_aktual': [0.18, 0.18, 0.18, 0.18, 0.18, 0.18],
        'tarif_pph_aktual': [0.005, 0.005, 0.005, 0.005, 0.005, 0.005],
        'biaya_kemasan_ops_per_unit': [2500, 2000, 4000, 2500, 1500, 2500],
        'biaya_iklan_langsung': [115e6, 45e6, 65e6, 25e6, 75e6, 10e6],
        'tingkat_retur_pct': [0.012, 0.015, 0.010, 0.018, 0.035, 0.045]
    })
    return df_monthly, df_sku

uploaded_file = st.file_uploader("📂 Unggah File Excel Performa Toko Shopee Anda (Sheet: `Monthly` dan `SKU`)", type=['xlsx'])

if uploaded_file:
    df_monthly = pd.read_excel(uploaded_file, sheet_name='Monthly')
    df_sku = pd.read_excel(uploaded_file, sheet_name='SKU')
    st.success("File berhasil diunggah dan direkonsiliasi!")
else:
    st.info("Menggunakan **Data Simulasi Toko Shopee** sebagai demonstrasi. Anda dapat mengunduh hasil Excel lengkap di bagian bawah.")
    df_monthly, df_sku = load_sample_data()

# Eksekusi Analisis
res_monthly = engine.analyze_monthly_performance(df_monthly)
res_sku = engine.audit_sku_profitability(df_sku)

tot_net_sales = res_monthly['penjualan_bersih'].sum()
tot_hpp = res_monthly['hpp'].sum()
tot_ads = res_monthly['biaya_iklan'].sum()
tot_opex = res_monthly['biaya_operasional'].sum()
tot_units = res_monthly['unit_terjual'].sum()
tot_orders = res_monthly['jumlah_pesanan_selesai'].sum()
avg_aov = tot_net_sales / max(tot_orders, 1)
avg_unit_price = tot_net_sales / max(tot_units, 1)

res_mp_sim = engine.simulate_marketplace_fees(tot_net_sales, tot_hpp, tot_ads, tot_opex, actual_mp_rate, tot_units)
res_reverse = engine.reverse_growth_planning(
    target_profit, avg_aov, avg_unit_price, 
    tot_hpp/tot_net_sales, actual_mp_rate, tot_opex, 
    conv_rate, paid_share, avg_cpc
)
res_roadmap = engine.generate_12_month_roadmap(
    res_reverse.loc[1, 'Target_Penjualan_Bersih_Tahunan'],
    target_profit, tot_hpp/tot_net_sales, actual_mp_rate,
    res_reverse.loc[1, 'Rasio_Iklan_Terhadap_Omzet_Maks'],
    avg_aov, avg_unit_price
)
res_stress = engine.run_stress_test(tot_net_sales, tot_hpp/tot_net_sales, actual_mp_rate, tot_ads, tot_opex)

# Tampilkan Tab Sesuai 13 Tahap Master Prompt
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Performa Bulanan & Laba Rugi",
    "📦 2. Audit SKU & Strategi Iklan",
    "🏦 3. Audit Biaya 24% & Pajak",
    "🔄 4. Reverse Planning & Target 12 Bulan",
    "🛡️ 5. Stress Test & Keputusan P1-P3"
])

with tab1:
    st.subheader("Tahap 4: Diagnosis Performa Bulanan & Kesehatan Pertumbuhan")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Penjualan Bersih", f"Rp {tot_net_sales:,.0f}")
    col2.metric("Estimasi Laba Bersih", f"Rp {res_monthly['estimasi_laba_bersih'].sum():,.0f}")
    col3.metric("Margin Laba Bersih Aktual", f"{(res_monthly['estimasi_laba_bersih'].sum()/tot_net_sales)*100:.1f}%")
    col4.metric("Rasio Iklan Terhadap Penjualan", f"{(tot_ads/tot_net_sales)*100:.1f}%")
    st.dataframe(res_monthly.style.format({
        'omzet_kotor': 'Rp {:,.0f}', 'penjualan_bersih': 'Rp {:,.0f}',
        'mom_growth': '{:.1%}', 'aov': 'Rp {:,.0f}', 'ad_spend_ratio': '{:.1%}',
        'mp_fee_ratio': '{:.1%}', 'estimasi_laba_bersih': 'Rp {:,.0f}', 'net_profit_margin': '{:.1%}'
    }))

with tab2:
    st.subheader("Tahap 5 & 7: Matriks Profitabilitas SKU, ROAS Impas & Batas Iklan")
    st.dataframe(res_sku[[
        'kode_sku', 'nama_sku', 'jumlah_terjual', 'penjualan_bersih_per_unit',
        'laba_kontribusi_per_unit', 'margin_kontribusi', 'total_kontribusi_laba',
        'roas_impas', 'batas_maks_iklan_per_unit', 'kategori_sku', 'rekomendasi_tindakan'
    ]].style.format({
        'penjualan_bersih_per_unit': 'Rp {:,.0f}',
        'laba_kontribusi_per_unit': 'Rp {:,.0f}',
        'margin_kontribusi': '{:.1%}',
        'total_kontribusi_laba': 'Rp {:,.0f}',
        'roas_impas': '{:.2f}x',
        'batas_maks_iklan_per_unit': 'Rp {:,.0f}'
    }))

with tab3:
    st.subheader("Tahap 6: Simulasi Rekayasa Biaya Marketplace & PPh (Uji Asumsi 24% vs Aktual)")
    st.dataframe(res_mp_sim.style.format({
        'Tarif_MP_dan_Pajak': '{:.1%}', 'Penjualan_Bersih': 'Rp {:,.0f}',
        'Biaya_MP_dan_PPh': 'Rp {:,.0f}', 'Estimasi_Laba_Bersih': 'Rp {:,.0f}',
        'Margin_Bersih': '{:.1%}', 'Laba_Per_Unit': 'Rp {:,.0f}',
        'Harga_Jual_Minimum_Target_12pct': 'Rp {:,.0f}', 'Batas_Maksimum_Anggaran_Iklan': 'Rp {:,.0f}'
    }))

with tab4:
    st.subheader("Tahap 11: Reverse Planning (Logika Terbalik: Target Laba ➡️ Kebutuhan Omzet & Trafik)")
    st.dataframe(res_reverse.style.format({
        'Target_Laba_Bersih_Tahunan': 'Rp {:,.0f}', 'Kebutuhan_Laba_Kontribusi': 'Rp {:,.0f}',
        'Target_Penjualan_Bersih_Tahunan': 'Rp {:,.0f}', 'Target_Penjualan_Bersih_Bulanan_Rata2': 'Rp {:,.0f}',
        'Kebutuhan_Pesanan_Tahunan': '{:,.0f}', 'Kebutuhan_Total_Kunjungan_Trafik': '{:,.0f}',
        'Anggaran_Iklan_Maksimum_Tahunan': 'Rp {:,.0f}', 'Rasio_Iklan_Terhadap_Omzet_Maks': '{:.1%}',
        'Estimasi_Modal_Kerja_Siklus_45_Hari': 'Rp {:,.0f}'
    }))
    st.subheader("Tahap 10: Breakdown Target 12 Bulan (Berbobot Musiman / Seasonality)")
    st.dataframe(res_roadmap.style.format({
        'Bobot_Musiman': '{:.1%}', 'Target_Penjualan_Bersih': 'Rp {:,.0f}',
        'Target_Laba_Bersih': 'Rp {:,.0f}', 'Anggaran_Iklan_Maks': 'Rp {:,.0f}',
        'Kebutuhan_Modal_Kerja_Bulanan': 'Rp {:,.0f}'
    }))

with tab5:
    st.subheader("Tahap 11G: Simulasi Stress Test Ketahanan Bisnis")
    st.dataframe(res_stress.style.format({
        'Penjualan_Bersih': 'Rp {:,.0f}', 'HPP': 'Rp {:,.0f}',
        'Biaya_MP_dan_Pajak': 'Rp {:,.0f}', 'Biaya_Iklan': 'Rp {:,.0f}',
        'Laba_Bersih': 'Rp {:,.0f}', 'Selisih_Laba_vs_Baseline': 'Rp {:,.0f}',
        'Margin_Laba_Bersih': '{:.1%}'
    }))

# Tombol Download Excel Lengkap
output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    res_monthly.to_excel(writer, sheet_name='1_Performa_Bulanan', index=False)
    res_sku.to_excel(writer, sheet_name='2_Audit_SKU_dan_Iklan', index=False)
    res_mp_sim.to_excel(writer, sheet_name='3_Simulasi_Biaya_24pct', index=False)
    res_reverse.to_excel(writer, sheet_name='4_Reverse_Planning', index=False)
    res_roadmap.to_excel(writer, sheet_name='5_Target_12_Bulan', index=False)
    res_stress.to_excel(writer, sheet_name='6_Stress_Test', index=False)

st.download_button(
    label="📥 Download Hasil Audit & Reverse Planning Lengkap (.xlsx)",
    data=output.getvalue(),
    file_name="Audit_BI_Shopee_Reverse_Plan.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)