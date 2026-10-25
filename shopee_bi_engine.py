import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class ShopeeBIEngine:
    def __init__(self, target_annual_profit=500_000_000, assumed_mp_tax_rate=0.24):
        """
        Inisialisasi Mesin Otomasi BI Shopee
        :param target_annual_profit: Target laba bersih tahunan (Rp) untuk Reverse Planning
        :param assumed_mp_tax_rate: Asumsi awal biaya gabungan Marketplace + PPh (Default: 24%)
        """
        self.target_annual_profit = target_annual_profit
        self.assumed_mp_tax_rate = assumed_mp_tax_rate

    # =========================================================================
    # TAHAP 1 & 3: AUDIT KUALITAS DATA & REKONSILIASI
    # =========================================================================
    def audit_data_quality(self, df_orders, df_sku, df_ads=None):
        audit_report = {}
        
        # Cek duplikasi & baris kosong
        audit_report['total_rows_raw'] = len(df_orders)
        audit_report['duplicate_order_ids'] = df_orders.duplicated(subset=['order_id']).sum() if 'order_id' in df_orders.columns else 0
        audit_report['missing_values_count'] = int(df_orders.isnull().sum().sum())
        
        # Filter pesanan selesai vs batal/retur
        if 'status_pesanan' in df_orders.columns:
            completed = df_orders[df_orders['status_pesanan'].str.lower().isin(['selesai', 'completed'])]
            cancelled_returned = df_orders[~df_orders['status_pesanan'].str.lower().isin(['selesai', 'completed'])]
            audit_report['completed_orders'] = len(completed)
            audit_report['cancelled_or_returned_orders'] = len(cancelled_returned)
            audit_report['return_cancel_rate'] = len(cancelled_returned) / max(len(df_orders), 1)
        else:
            audit_report['completed_orders'] = len(df_orders)
            audit_report['cancelled_or_returned_orders'] = 0
            audit_report['return_cancel_rate'] = 0.0

        # Rekonsiliasi Omzet Kotor vs Penjualan Bersih vs Dana Pencairan
        audit_report['gross_revenue'] = df_orders['omzet_kotor'].sum() if 'omzet_kotor' in df_orders.columns else 0
        audit_report['net_sales'] = df_orders['penjualan_bersih'].sum() if 'penjualan_bersih' in df_orders.columns else 0
        audit_report['payout_amount'] = df_orders['dana_pencairan'].sum() if 'dana_pencairan' in df_orders.columns else 0
        audit_report['unreconciled_gap'] = (
            audit_report['net_sales'] 
            - df_orders.get('total_biaya_mp', pd.Series([0])).sum()
            - audit_report['payout_amount']
        )
        return pd.DataFrame([audit_report])

    # =========================================================================
    # TAHAP 4: DIAGNOSIS PERFORMA TOKO BULANAN
    # =========================================================================
    def analyze_monthly_performance(self, df_monthly):
        df = df_monthly.copy()
        
        # Perhitungan metrik utama secara konsisten berbasis Penjualan Bersih
        df['mom_growth'] = df['penjualan_bersih'].pct_change().fillna(0)
        df['aov'] = df['penjualan_bersih'] / df['jumlah_pesanan_selesai'].replace(0, np.nan)
        df['ad_spend_ratio'] = df['biaya_iklan'] / df['penjualan_bersih'].replace(0, np.nan)
        df['mp_fee_ratio'] = df['total_biaya_mp'] / df['penjualan_bersih'].replace(0, np.nan)
        
        # Laba Kontribusi Setelah Iklan & Estimasi Laba Bersih
        df['laba_kontribusi_setelah_iklan'] = (
            df['penjualan_bersih'] 
            - df['hpp'] 
            - df['total_biaya_mp'] 
            - df['biaya_iklan']
        )
        df['estimasi_laba_bersih'] = df['laba_kontribusi_setelah_iklan'] - df['biaya_operasional']
        df['net_profit_margin'] = df['estimasi_laba_bersih'] / df['penjualan_bersih'].replace(0, np.nan)
        
        # Deteksi anomali: Omzet naik tapi laba turun
        df['profit_Growth_MoM'] = df['estimasi_laba_bersih'].pct_change().fillna(0)
        df['status_kesehatan'] = np.where(
            (df['mom_growth'] > 0) & (df['profit_Growth_MoM'] < 0),
            'WARNING: Omzet Naik tapi Laba Turun (Pertumbuhan Semu)',
            np.where(df['net_profit_margin'] < 0.05, 'KRITIS: Margin < 5%', 'SEHAT')
        )
        return df

    # =========================================================================
    # TAHAP 5: AUDIT PROFITABILITAS SETIAP SKU & KLASIFIKASI MATRIKS
    # =========================================================================
    def audit_sku_profitability(self, df_sku):
        df = df_sku.copy()
        
        # Penjualan bersih per unit
        df['penjualan_bersih_per_unit'] = df['harga_jual_aktual'] - df.get('diskon_penjual_per_unit', 0)
        df['penjualan_bersih_total'] = df['penjualan_bersih_per_unit'] * df['jumlah_terjual']
        
        # Komponen biaya per unit
        df['biaya_mp_per_unit'] = df['penjualan_bersih_per_unit'] * df['tarif_mp_aktual']
        df['pajak_per_unit'] = df['penjualan_bersih_per_unit'] * df.get('tarif_pph_aktual', 0.005)
        df['iklan_per_unit'] = df.get('biaya_iklan_langsung', 0) / df['jumlah_terjual'].replace(0, np.nan)
        df['iklan_per_unit'] = df['iklan_per_unit'].fillna(0)
        
        # Laba kontribusi sebelum & sesudah iklan
        df['laba_kontribusi_sebelum_iklan_unit'] = (
            df['penjualan_bersih_per_unit']
            - df['hpp_per_unit']
            - df['biaya_mp_per_unit']
            - df['pajak_per_unit']
            - df['biaya_kemasan_ops_per_unit']
        )
        df['laba_kontribusi_per_unit'] = df['laba_kontribusi_sebelum_iklan_unit'] - df['iklan_per_unit']
        df['margin_kontribusi'] = df['laba_kontribusi_per_unit'] / df['penjualan_bersih_per_unit'].replace(0, np.nan)
        df['total_kontribusi_laba'] = df['laba_kontribusi_per_unit'] * df['jumlah_terjual']
        
        # ROAS Impas & Batas Maksimum Biaya Iklan per Unit
        df['margin_sebelum_iklan_pct'] = df['laba_kontribusi_sebelum_iklan_unit'] / df['penjualan_bersih_per_unit'].replace(0, np.nan)
        df['roas_impas'] = np.where(df['margin_sebelum_iklan_pct'] > 0, 1 / df['margin_sebelum_iklan_pct'], np.inf)
        
        target_min_profit_pct = 0.10 # Target margin bersih minimal 10%
        df['batas_maks_iklan_per_unit'] = np.maximum(
            0, 
            df['laba_kontribusi_sebelum_iklan_unit'] - (df['penjualan_bersih_per_unit'] * target_min_profit_pct)
        )

        # Klasifikasi SKU (A-F)
        median_qty = df['jumlah_terjual'].median()
        median_profit = df['total_kontribusi_laba'].median()

        def classify_sku(row):
            if row['laba_kontribusi_per_unit'] <= 0 and row['jumlah_terjual'] >= median_qty:
                return 'E. Margin Trap SKU (Omzet Tinggi, Laba Tipis/Negatif)'
            elif row['total_kontribusi_laba'] >= median_profit and row['margin_kontribusi'] >= 0.15 and row['jumlah_terjual'] >= median_qty:
                return 'A. Hero SKU (Laba Tinggi & Permintaan Kuat)'
            elif row['jumlah_terjual'] >= median_qty * 1.3 and 0.05 <= row['margin_kontribusi'] < 0.15:
                return 'B/C. Traffic & Cash-Flow SKU (Perputaran Cepat)'
            elif row['margin_kontribusi'] >= 0.20 and row['jumlah_terjual'] < median_qty:
                return 'D. Growth SKU (Margin Tebal, Butuh Validasi Trafik)'
            else:
                return 'F. Dead Weight SKU (Perputaran Rendah / Tidak Layak)'

        df['kategori_sku'] = df.apply(classify_sku, axis=1)

        # Rekomendasi Tindakan Otomatis
        def recommend_action(row):
            kat = row['kategori_sku']
            if kat.startswith('A'):
                return 'Pertahankan, jaga ketersediaan stok, prioritaskan anggaran iklan'
            elif kat.startswith('E'):
                return 'STOP iklan berbayar, naikkan harga 5-10%, atau jadikan syarat bundling dengan Hero SKU'
            elif kat.startswith('D'):
                return 'Optimasi SEO judul/foto, uji iklan kata kunci spesifik dengan batas CPC ketat'
            elif kat.startswith('B/C'):
                return 'Pertahankan untuk akuisisi organik, batasi iklan, pasang cross-selling ke Hero SKU'
            else:
                return 'Cuci gudang (clearance sale), hentikan restock secara bertahap'

        df['rekomendasi_tindakan'] = df.apply(recommend_action, axis=1)
        return df.sort_values(by='total_kontribusi_laba', ascending=False)

    # =========================================================================
    # TAHAP 6: REKAYASA BIAYA MARKETPLACE DAN PPH (3 SKENARIO)
    # =========================================================================
    def simulate_marketplace_fees(self, net_sales, hpp, ad_spend, opex, actual_mp_tax_rate, total_units):
        scenarios = {
            'Skenario A (Asumsi Gabungan 24%)': self.assumed_mp_tax_rate,
            f'Skenario B (Audit Aktual {actual_mp_tax_rate*100:.1f}%)': actual_mp_tax_rate,
            f'Skenario C (Stress Test +3% -> {(actual_mp_tax_rate+0.03)*100:.1f}%)': actual_mp_tax_rate + 0.03
        }
        
        results = []
        avg_price_per_unit = net_sales / max(total_units, 1)
        hpp_per_unit = hpp / max(total_units, 1)
        opex_per_unit = opex / max(total_units, 1)
        target_net_margin = 0.12 # Contoh target margin bersih 12%

        for name, rate in scenarios.items():
            mp_and_tax_cost = net_sales * rate
            net_profit = net_sales - hpp - mp_and_tax_cost - ad_spend - opex
            net_margin = net_profit / max(net_sales, 1)
            profit_per_unit = net_profit / max(total_units, 1)
            
            # Harga jual minimum agar mencapai target margin bersih (tanpa ubah HPP & Opex)
            # Harga * (1 - rate - target_margin) = HPP_unit + Opex_unit + Iklan_unit
            ad_per_unit = ad_spend / max(total_units, 1)
            denom = 1 - rate - target_net_margin
            min_selling_price = (hpp_per_unit + opex_per_unit + ad_per_unit) / denom if denom > 0 else np.nan
            
            # Batas maksimum biaya iklan agar tetap mencapai target margin bersih
            max_ad_spend = max(0, net_sales * (1 - rate - target_net_margin) - hpp - opex)

            results.append({
                'Skenario': name,
                'Tarif_MP_dan_Pajak': rate,
                'Penjualan_Bersih': net_sales,
                'Biaya_MP_dan_PPh': mp_and_tax_cost,
                'HPP': hpp,
                'Biaya_Iklan': ad_spend,
                'Biaya_Operasional': opex,
                'Estimasi_Laba_Bersih': net_profit,
                'Margin_Bersih': net_margin,
                'Laba_Per_Unit': profit_per_unit,
                'Harga_Jual_Minimum_Target_12pct': min_selling_price,
                'Batas_Maksimum_Anggaran_Iklan': max_ad_spend
            })
        return pd.DataFrame(results)

    # =========================================================================
    # TAHAP 11: REVERSE PLANNING (LOGIKA TERBALIK DARI TARGET LABA)
    # =========================================================================
    def reverse_growth_planning(self, target_annual_profit, aov, avg_price_unit, hpp_ratio, mp_tax_ratio, fixed_opex_annual, conv_rate, paid_traffic_share=0.40, avg_cpc=350):
        """
        Menghitung mundur dari Target Laba -> Kebutuhan Kontribusi -> Penjualan -> Pesanan -> Trafik -> Maks Iklan
        """
        plans = []
        scenarios = [
            ('1. Konservatif (80% Target)', target_annual_profit * 0.8),
            ('2. Realistis / Dasar (100% Target)', target_annual_profit * 1.0),
            ('3. Agresif (130% Target)', target_annual_profit * 1.3)
        ]

        # Rasio margin kontribusi sebelum iklan = 1 - HPP_ratio - MP_Tax_ratio
        cm_before_ads_ratio = 1.0 - hpp_ratio - mp_tax_ratio

        for label, profit_goal in scenarios:
            # Laba Kontribusi Setelah Iklan yang dibutuhkan = Target Laba Bersih + Biaya Tetap Tahunan
            required_contribution_after_ads = profit_goal + fixed_opex_annual
            
            # Estimasi kebutuhan trafik dan biaya iklan iteratif berbasis konversi & CPC
            # Penjualan Bersih * cm_before_ads_ratio - Biaya Iklan = required_contribution_after_ads
            # Biaya Iklan = (Pesanan * paid_traffic_share / conv_rate) * avg_cpc
            # Pesanan = Penjualan Bersih / AOV
            ad_cost_per_rupiah_sales = (paid_traffic_share / max(conv_rate, 0.0001)) * avg_cpc / max(aov, 1)
            net_cm_after_ads_ratio = cm_before_ads_ratio - ad_cost_per_rupiah_sales

            if net_cm_after_ads_ratio <= 0:
                req_net_sales = np.nan
            else:
                req_net_sales = required_contribution_after_ads / net_cm_after_ads_ratio

            req_orders = req_net_sales / max(aov, 1)
            req_units = req_net_sales / max(avg_price_unit, 1)
            req_total_visitors = req_orders / max(conv_rate, 0.0001)
            req_paid_visitors = req_total_visitors * paid_traffic_share
            req_organic_visitors = req_total_visitors * (1 - paid_traffic_share)
            max_ad_budget = req_paid_visitors * avg_cpc
            
            # Kebutuhan modal kerja (asumsi siklus kas/perputaran stok 1.5 bulan HPP + Opex)
            working_capital_needed = ((req_net_sales * hpp_ratio) + fixed_opex_annual) * (1.5 / 12)

            plans.append({
                'Skenario_Reverse_Plan': label,
                'Target_Laba_Bersih_Tahunan': profit_goal,
                'Kebutuhan_Laba_Kontribusi': required_contribution_after_ads,
                'Target_Penjualan_Bersih_Tahunan': req_net_sales,
                'Target_Penjualan_Bersih_Bulanan_Rata2': req_net_sales / 12,
                'Kebutuhan_Pesanan_Tahunan': req_orders,
                'Kebutuhan_Unit_Terjual_Tahunan': req_units,
                'Kebutuhan_Total_Kunjungan_Trafik': req_total_visitors,
                'Kebutuhan_Trafik_Organik': req_organic_visitors,
                'Kebutuhan_Trafik_Iklan': req_paid_visitors,
                'Anggaran_Iklan_Maksimum_Tahunan': max_ad_budget,
                'Rasio_Iklan_Terhadap_Omzet_Maks': max_ad_budget / max(req_net_sales, 1),
                'Estimasi_Modal_Kerja_Siklus_45_Hari': working_capital_needed
            })

        return pd.DataFrame(plans)

    # =========================================================================
    # TAHAP 10: BREAKDOWN TARGET BULANAN DENGAN BOBOT MUSIMAN (SEASONALITY)
    # =========================================================================
    def generate_12_month_roadmap(self, annual_net_sales_target, annual_profit_target, hpp_ratio, mp_tax_ratio, ad_ratio, aov, avg_unit_price):
        # Bobot musiman e-commerce Indonesia (total = 100%)
        # Puncak di Ramadan/Lebaran (Maret/April) dan Harbolnas Q4 (10.10, 11.11, 12.12)
        seasonal_weights = [
            ('Januari', 0.065, 'Optimasi katalog, pembersihan Dead Weight SKU'),
            ('Februari', 0.070, 'Persiapan stok & kampanye pemanasan Ramadan'),
            ('Maret (Peak Ramadan)', 0.115, 'Scale-up Hero SKU & Bundling Hampers/Ramadan'),
            ('April (Lebaran)', 0.085, 'Fokus pemenuhan pesanan sebelum cuti & retensi'),
            ('Mei', 0.070, 'Re-evaluasi HPP supplier & efisiensi pasca-Lebaran'),
            ('Juni', 0.075, 'Kampanye pertengahan tahun (6.6) & uji Growth SKU'),
            ('Juli', 0.075, 'Back-to-school / gajian sale, optimasi konversi organik'),
            ('Agustus', 0.075, 'Kampanye Kemerdekaan (8.8), audit biaya program MP'),
            ('September', 0.080, '9.9 Super Shopping Day, penguncian stok Q4'),
            ('Oktober', 0.090, '10.10 Brand/Mall Fest, dorong AOV lewat cross-selling'),
            ('November', 0.100, '11.11 Big Sale, maksimalkan ROAS pada Hero SKU'),
            ('Desember', 0.100, '12.12 Birthday Sale & Year-End Clearance stok lambat')
        ]

        roadmap = []
        for month, weight, action in seasonal_weights:
            m_sales = annual_net_sales_target * weight
            m_profit = annual_profit_target * weight
            m_ads = m_sales * ad_ratio
            m_hpp = m_sales * hpp_ratio
            m_mp_fee = m_sales * mp_tax_ratio
            m_orders = m_sales / max(aov, 1)
            m_units = m_sales / max(avg_unit_price, 1)
            m_stock_buffer = m_units * 1.25 # Buffer stok 25%
            m_working_cap = m_hpp * 1.25 + m_ads

            roadmap.append({
                'Bulan': month,
                'Bobot_Musiman': weight,
                'Target_Penjualan_Bersih': m_sales,
                'Target_Laba_Bersih': m_profit,
                'Anggaran_Iklan_Maks': m_ads,
                'Batas_Biaya_MP_dan_Pajak': m_mp_fee,
                'Estimasi_HPP': m_hpp,
                'Target_Pesanan': round(m_orders),
                'Target_Unit_Terjual': round(m_units),
                'Kebutuhan_Stok_Unit_Buffer_25pct': round(m_stock_buffer),
                'Kebutuhan_Modal_Kerja_Bulanan': m_working_cap,
                'Fokus_Tindakan_Utama': action
            })
        return pd.DataFrame(roadmap)

    # =========================================================================
    # TAHAP 11G & 13: SIMULASI STRESS TEST KETAHANAN BISNIS
    # =========================================================================
    def run_stress_test(self, base_sales, base_hpp_ratio, base_mp_ratio, base_ad_spend, fixed_opex):
        base_hpp = base_sales * base_hpp_ratio
        base_mp = base_sales * base_mp_ratio
        base_profit = base_sales - base_hpp - base_mp - base_ad_spend - fixed_opex

        tests = [
            ('0. Baseline (Kondisi Normal)', 1.0, base_hpp_ratio, base_mp_ratio, 1.0),
            ('1. Omzet / Konversi Turun 10%', 0.90, base_hpp_ratio, base_mp_ratio, 1.0),
            ('2. HPP Supplier Naik 5%', 1.0, base_hpp_ratio * 1.05, base_mp_ratio, 1.0),
            ('3. Biaya Iklan Membengkak +20%', 1.0, base_hpp_ratio, base_mp_ratio, 1.20),
            ('4. Biaya Efektif Shopee Naik +2 Poin %', 1.0, base_hpp_ratio, base_mp_ratio + 0.02, 1.0),
            ('5. KOMBINASI BURUK (Omzet -10%, HPP +5%, Iklan +20%, MP +2%)', 0.90, base_hpp_ratio * 1.05, base_mp_ratio + 0.02, 1.20)
        ]

        rows = []
        for name, sales_mult, hpp_r, mp_r, ad_mult in tests:
            s_sales = base_sales * sales_mult
            s_hpp = s_sales * hpp_r
            s_mp = s_sales * mp_r
            s_ads = base_ad_spend * ad_mult
            s_profit = s_sales - s_hpp - s_mp - s_ads - fixed_opex
            s_margin = s_profit / max(s_sales, 1)

            status = 'AMAN' if s_profit > (base_profit * 0.5) else ('WASPADA (Laba Terpangkas >50%)' if s_profit > 0 else ' DEFISIT / RUGI ARUS KAS')

            rows.append({
                'Skenario_Stress_Test': name,
                'Penjualan_Bersih': s_sales,
                'HPP': s_hpp,
                'Biaya_MP_dan_Pajak': s_mp,
                'Biaya_Iklan': s_ads,
                'Biaya_Operasional_Tetap': fixed_opex,
                'Laba_Bersih': s_profit,
                'Selisih_Laba_vs_Baseline': s_profit - base_profit,
                'Margin_Laba_Bersih': s_margin,
                'Status_Ketahanan': status
            })
        return pd.DataFrame(rows)

    # =========================================================================
    # EKSPOR KE EXCEL MULTI-SHEET OTOMATIS
    # =========================================================================
    def export_full_audit_to_excel(self, filename, dict_dataframes):
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in dict_dataframes.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        print(f"[SUCCESS] Laporan Otomasi BI Shopee berhasil disimpan ke: {filename}")