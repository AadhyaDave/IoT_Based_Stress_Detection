"""
ESP32 & Physiological Sensor Simulator for Smart Monitoring System
Simulates AD8232 ECG sensor and MAX30102 pulse oximeter telemetry.
Sends 200 samples/sec batched every 1 second to the Flask backend.
"""

import sys
import time
import math
import random
import json
import urllib.request
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_URL = "http://localhost:5000/data"

def generate_ecg_sample(phase):
    """
    Generate synthetic ECG voltage (P-Q-R-S-T wave model) centered around ADC 1800.
    phase: 0.0 to 1.0 representing one heartbeat cardiac cycle.
    """
    baseline = 1800.0
    val = baseline

    # P wave (around phase 0.15 - 0.25)
    if 0.15 <= phase <= 0.25:
        p_p = (phase - 0.20) / 0.05
        val += 90.0 * math.exp(-p_p * p_p * 4)
    # Q wave (around phase 0.32 - 0.35)
    elif 0.32 <= phase <= 0.35:
        q_p = (phase - 0.34) / 0.02
        val -= 120.0 * math.exp(-q_p * q_p * 8)
    # R wave peak (around phase 0.35 - 0.40) - sharp spike
    elif 0.35 <= phase <= 0.40:
        r_p = (phase - 0.375) / 0.015
        val += 1100.0 * math.exp(-r_p * r_p * 6)
    # S wave drop (around phase 0.40 - 0.44)
    elif 0.40 <= phase <= 0.44:
        s_p = (phase - 0.42) / 0.02
        val -= 250.0 * math.exp(-s_p * s_p * 8)
    # T wave (around phase 0.55 - 0.70)
    elif 0.55 <= phase <= 0.70:
        t_p = (phase - 0.62) / 0.07
        val += 220.0 * math.exp(-t_p * t_p * 4)

    # Slight sensor baseline noise (±15 ADC counts)
    val += random.gauss(0, 15)
    return int(max(200, min(4000, val)))

def main():
    parser = argparse.ArgumentParser(description="Simulate ESP32 physiological sensor telemetry.")
    parser.add_argument("--url", default=SERVER_URL, help="Target backend /data URL")
    parser.add_argument("--stress", action="store_true", help="Simulate elevated heart rate / stress profile")
    args = parser.parse_args()

    print("==================================================================")
    print(" [*] SMART PHYSIOLOGICAL MONITORING SYSTEM - SENSOR SIMULATOR")
    print(f" Target Server : {args.url}")
    print(f" Profile       : {'STRESS' if args.stress else 'NORMAL / RELAXED'}")
    print(" Sending 200 ECG samples/sec (1-second batches)")
    print(" First ML prediction will fire after 60 seconds (12,000 samples)")
    print("==================================================================")

    sample_rate = 200  # 200 Hz
    phase = 0.0
    seconds_sent = 0

    base_bpm = 100 if args.stress else 72
    base_spo2 = 96 if args.stress else 98

    while True:
        cycle_start = time.time()
        batch_ecg = []

        # Current vitals with subtle realistic physiological fluctuation
        current_bpm = int(base_bpm + random.uniform(-2, 3))
        current_spo2 = int(base_spo2 + random.choice([0, 0, 1, -1]))
        current_spo2 = max(94, min(100, current_spo2))

        # Phase increment per sample based on BPM
        heart_rate_hz = current_bpm / 60.0
        phase_increment = heart_rate_hz / sample_rate

        for _ in range(sample_rate):
            sample = generate_ecg_sample(phase)
            batch_ecg.append(sample)
            phase = (phase + phase_increment) % 1.0

        payload = {
            "bpm": current_bpm,
            "spo2": current_spo2,
            "ecg": batch_ecg
        }

        try:
            req = urllib.request.Request(
                args.url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                seconds_sent += 1
                buffered = result.get("buffered", seconds_sent * 200)
                required = result.get("required", 12000)
                pct = min(100.0, (buffered / required) * 100)
                status_msg = f"[{seconds_sent:03d}s] BPM: {current_bpm} | SpO2: {current_spo2}% | Buffered: {buffered}/{required} ({pct:.1f}%)"
                print(status_msg)
        except Exception as e:
            print(f"[!] [Error transmitting batch]: {e}")

        elapsed = time.time() - cycle_start
        sleep_time = max(0.0, 1.0 - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
