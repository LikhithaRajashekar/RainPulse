import os
import sqlite3
import h5py
import numpy as np
import pandas as pd

class RainPulseCompactor:
    def __init__(self, raw_dir="./data/01_ISRO_GSMaP/raw", db_path="rainpulse_staging.db"):
        self.raw_dir = raw_dir
        self.db_path = db_path

    def extract_rainfall_scalar(self, file_path):
        """Safely parses raw ISRO HDF5 matrix structure and clips Odisha coordinates"""
        try:
            with h5py.File(file_path, 'r') as f:
                # Target the default precipitation group key in GSMaP Level-3 datasets
                for key in f.keys():
                    if 'precip' in key.lower() or 'rain' in key.lower():
                        grid = np.array(f[key])
                        # Bound mapping vectors roughly clipping the Odisha territory
                        odisha_matrix = grid[180:240, 750:820]
                        # Clean out default fill values or negative telemetry flags
                        clean_matrix = np.where(odisha_matrix < 0, 0.0, odisha_matrix)
                        return round(float(np.mean(clean_matrix)), 4)
                return 0.0
        except Exception as e:
            return None

    def run_pipeline(self):
        print("\n⚡ [RAINPULSE COMPACTING MATRIX PIPELINE ACTIVE]")
        print("-" * 65)
        
        if not os.path.exists(self.raw_dir):
            print(f"❌ Target path mismatch. Folder not found: {self.raw_dir}")
            return
            
        raw_files = sorted([f for f in os.listdir(self.raw_dir) if f.endswith('.h5')])
        print(f"📦 Identified {len(raw_files)} raw telemetry packets locally.")
        
        odisha_records = []
        
        for file_name in raw_files:
            # Extract timestamp directly from the filename parameter grid (YYMMDDHH)
            # Example parsing anchor: GPMMRG_MAP_2607280000...
            try:
                ts_part = file_name.split('_')[2]
                day = ts_part[4:6]
                hour = ts_part[6:8]
                timestamp_iso = f"2026-07-{day}T{hour}:00:00Z"
            except:
                timestamp_iso = "2026-07-28T00:00:00Z"
                
            full_path = os.path.join(self.raw_dir, file_name)
            rain_rate = self.extract_rainfall_scalar(full_path)
            
            if rain_rate is not None:
                # To simulate the dynamic Novelty 1 Radar Failure at peak intensity (July 28, 12:00)
                is_radar_fault = ("28" in file_name and "1200" in file_name)
                
                odisha_records.append({
                    "event_id": "ODISHA_FLOOD_2026",
                    "region_name": "Odisha Coastal Delta (Mahanadi Basin)",
                    "timestamp": timestamp_iso,
                    "satellite_mm_hr": round(rain_rate * 0.97, 2),
                    "radar_mm_hr": 0.0 if is_radar_fault else round(rain_rate * 1.02, 2),
                    "aws_gauge_mm_hr": round(rain_rate, 2),
                    "nwp_forecast_mm_hr": round(rain_rate * 0.91, 2),
                    "river_stage_meters": round(3.1 + (rain_rate * 0.04), 2),
                    "critical_assets": "National Highway 16, Cuttack General Hospital, Delta Primary School"
                })
                print(f" -> [COMPRESSED] Packet: {file_name[:24]}... | Extracted Scalar: {rain_rate:.2f} mm/hr")

        # Save to local SQLite edge staging tables
        if odisha_records:
            df = pd.DataFrame(odisha_records)
            conn = sqlite3.connect(self.db_path)
            df.to_sql("event_telemetry", conn, if_exists="append", index=False)
            conn.close()
            print("-" * 65)
            print(f"✅ SUCCESS: {len(odisha_records)} historical lines saved to master caching database.")
            print(f"📁 Database Location: '{self.db_path}' (Ready for clean GitHub commit!)")

if __name__ == "__main__":
    # Matches your exact directory structure visible in your explorer sidebar
    compactor = RainPulseCompactor(raw_dir="./data/01_ISRO_GSMaP/raw")
    compactor.run_pipeline()