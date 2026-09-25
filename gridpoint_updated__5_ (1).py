from flask import Flask, jsonify, request, render_template_string
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
import os
import csv
import io
import json
import random
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from scipy.optimize import milp, LinearConstraint, Bounds
    from scipy.sparse import lil_matrix
    SCIPY_MILP_AVAILABLE = True
except Exception:
    milp = LinearConstraint = Bounds = lil_matrix = None
    SCIPY_MILP_AVAILABLE = False

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

CITIES = {
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "multiplier": 1.00},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "multiplier": 1.12},
    "Delhi": {"lat": 28.6139, "lon": 77.2090, "multiplier": 1.10},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "multiplier": 0.94},
    "Chennai": {"lat": 13.0827, "lon": 80.2707, "multiplier": 0.96},
    "Pune": {"lat": 18.5204, "lon": 73.8567, "multiplier": 0.92},
    "Kolkata": {"lat": 22.5726, "lon": 88.3639, "multiplier": 0.98},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714, "multiplier": 0.90},
    "Jaipur": {"lat": 26.9124, "lon": 75.7873, "multiplier": 0.91},
    "Surat": {"lat": 21.1702, "lon": 72.8311, "multiplier": 0.89},
    "Lucknow": {"lat": 26.8467, "lon": 80.9462, "multiplier": 0.90},
    "Kanpur": {"lat": 26.4499, "lon": 80.3319, "multiplier": 0.89},
    "Nagpur": {"lat": 21.1458, "lon": 79.0882, "multiplier": 0.88},
    "Indore": {"lat": 22.7196, "lon": 75.8577, "multiplier": 0.87},
    "Thane": {"lat": 19.2183, "lon": 72.9781, "multiplier": 1.05},
    "Bhopal": {"lat": 23.2599, "lon": 77.4126, "multiplier": 0.86},
    "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "multiplier": 0.88},
    "Patna": {"lat": 25.5941, "lon": 85.1376, "multiplier": 0.86},
    "Vadodara": {"lat": 22.3072, "lon": 73.1812, "multiplier": 0.87},
    "Ghaziabad": {"lat": 28.6692, "lon": 77.4538, "multiplier": 1.05},
    "Ludhiana": {"lat": 30.9010, "lon": 75.8573, "multiplier": 0.88},
    "Agra": {"lat": 27.1767, "lon": 78.0081, "multiplier": 0.86},
    "Nashik": {"lat": 19.9975, "lon": 73.7898, "multiplier": 0.86},
    "Faridabad": {"lat": 28.4089, "lon": 77.3178, "multiplier": 1.02},
    "Meerut": {"lat": 28.9845, "lon": 77.7064, "multiplier": 0.88},
    "Rajkot": {"lat": 22.3039, "lon": 70.8022, "multiplier": 0.85},
    "Kalyan": {"lat": 19.2437, "lon": 73.1355, "multiplier": 1.02},
    "Vasai-Virar": {"lat": 19.3919, "lon": 72.8397, "multiplier": 1.00},
    "Varanasi": {"lat": 25.3176, "lon": 82.9739, "multiplier": 0.84},
    "Srinagar": {"lat": 34.0837, "lon": 74.7973, "multiplier": 0.86},
    "Aurangabad": {"lat": 19.8762, "lon": 75.3433, "multiplier": 0.85},
    "Dhanbad": {"lat": 23.7957, "lon": 86.4304, "multiplier": 0.83},
    "Amritsar": {"lat": 31.6340, "lon": 74.8723, "multiplier": 0.85},
    "Navi Mumbai": {"lat": 19.0330, "lon": 73.0297, "multiplier": 1.03},
    "Ranchi": {"lat": 23.3441, "lon": 85.3096, "multiplier": 0.84},
    "Coimbatore": {"lat": 11.0168, "lon": 76.9558, "multiplier": 0.87},
    "Kochi": {"lat": 9.9312, "lon": 76.2673, "multiplier": 0.86},
    "Mysuru": {"lat": 12.2958, "lon": 76.6394, "multiplier": 0.84},
    "Guwahati": {"lat": 26.1445, "lon": 91.7362, "multiplier": 0.85},
    "Chandigarh": {"lat": 30.7333, "lon": 76.7794, "multiplier": 0.89},
    "Bhubaneswar": {"lat": 20.2961, "lon": 85.8245, "multiplier": 0.85},
    "Dehradun": {"lat": 30.3165, "lon": 78.0322, "multiplier": 0.84},
    "Thiruvananthapuram": {"lat": 8.5241, "lon": 76.9366, "multiplier": 0.84},
}


DEMO_NEIGHBORHOODS = [
    {"id": "N01", "name": "Indiranagar", "lat": 12.9784, "lon": 77.6408, "orders": 420},
    {"id": "N02", "name": "Koramangala", "lat": 12.9352, "lon": 77.6245, "orders": 510},
    {"id": "N03", "name": "HSR Layout", "lat": 12.9116, "lon": 77.6389, "orders": 380},
    {"id": "N04", "name": "BTM Layout", "lat": 12.9166, "lon": 77.6101, "orders": 350},
    {"id": "N05", "name": "Jayanagar", "lat": 12.9250, "lon": 77.5938, "orders": 330},
    {"id": "N06", "name": "JP Nagar", "lat": 12.9063, "lon": 77.5857, "orders": 290},
    {"id": "N07", "name": "Malleshwaram", "lat": 13.0035, "lon": 77.5703, "orders": 260},
    {"id": "N08", "name": "Rajajinagar", "lat": 12.9910, "lon": 77.5532, "orders": 300},
    {"id": "N09", "name": "Yeshwanthpur", "lat": 13.0281, "lon": 77.5400, "orders": 240},
    {"id": "N10", "name": "Hebbal", "lat": 13.0358, "lon": 77.5970, "orders": 280},
    {"id": "N11", "name": "Whitefield", "lat": 12.9698, "lon": 77.7499, "orders": 620},
    {"id": "N12", "name": "Marathahalli", "lat": 12.9591, "lon": 77.6974, "orders": 500},
    {"id": "N13", "name": "Bellandur", "lat": 12.9304, "lon": 77.6784, "orders": 470},
    {"id": "N14", "name": "Sarjapur Road", "lat": 12.9106, "lon": 77.6870, "orders": 410},
    {"id": "N15", "name": "Electronic City", "lat": 12.8458, "lon": 77.6602, "orders": 390},
    {"id": "N16", "name": "Banashankari", "lat": 12.9255, "lon": 77.5468, "orders": 280},
    {"id": "N17", "name": "Basavanagudi", "lat": 12.9435, "lon": 77.5747, "orders": 220},
    {"id": "N18", "name": "Vijayanagar", "lat": 12.9719, "lon": 77.5270, "orders": 270},
    {"id": "N19", "name": "Kalyan Nagar", "lat": 13.0290, "lon": 77.6400, "orders": 310},
    {"id": "N20", "name": "Kundalahalli", "lat": 12.9691, "lon": 77.7157, "orders": 360},
    {"id": "N21", "name": "Kadugodi", "lat": 12.9900, "lon": 77.7590, "orders": 230},
    {"id": "N22", "name": "Yelahanka", "lat": 13.1007, "lon": 77.5963, "orders": 240},
    {"id": "N23", "name": "RT Nagar", "lat": 13.0196, "lon": 77.5968, "orders": 250},
    {"id": "N24", "name": "Frazer Town", "lat": 12.9984, "lon": 77.6177, "orders": 235},
    {"id": "N25", "name": "Richmond Town", "lat": 12.9622, "lon": 77.6033, "orders": 245},
]

VEHICLES = {
    "bike": {"label": "Bike", "fuel": 45.0, "unit": "km/l", "emission": 0.082},
    "car": {"label": "Car / Van", "fuel": 15.0, "unit": "km/l", "emission": 0.192},
    "ev": {"label": "Electric Van", "fuel": 5.2, "unit": "km/kWh", "emission": 0.055},
    "truck": {"label": "Mini Truck", "fuel": 9.0, "unit": "km/l", "emission": 0.265},
}

BASE_HTML = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ title }} · GRIDPOINT</title>
  <meta name="theme-color" content="#07111f">
  <script>document.documentElement.dataset.theme=localStorage.getItem('gridpoint-theme')||'dark';</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <style>
    :root{--bg:#06101e;--surface:#0b1728;--surface2:#101f33;--surface3:#12253d;--line:rgba(157,184,214,.14);--text:#eef5ff;--muted:#92a7c0;--accent:#4ea1ff;--accent2:#67e8f9;--good:#39d98a;--warning:#ffbd66;--danger:#ff6b7d;--shadow:0 22px 65px rgba(0,0,0,.28);--radius:20px;--nav:rgba(6,16,30,.8);--field:#0c1b2d;--table-head:#0e1d30}
    html[data-theme=light]{--bg:#f4f8fc;--surface:#ffffff;--surface2:#eef4fa;--surface3:#e6eef7;--line:rgba(53,79,108,.14);--text:#132235;--muted:#60738a;--accent:#2478e5;--accent2:#12a9c7;--good:#159c62;--warning:#b76b00;--danger:#c9304d;--shadow:0 18px 50px rgba(26,52,79,.11);--nav:rgba(244,248,252,.86);--field:#ffffff;--table-head:#eaf1f8;color-scheme:light}
    html[data-theme=dark]{color-scheme:dark}
    html[data-theme=light] body{background:radial-gradient(circle at 20% -10%,rgba(36,120,229,.10),transparent 32%),radial-gradient(circle at 100% 30%,rgba(18,169,199,.07),transparent 26%),var(--bg)}
    html[data-theme=light] nav{background:var(--nav)}
    html[data-theme=light] .hero-card{background:linear-gradient(180deg,rgba(255,255,255,.98),rgba(247,250,253,.98))}
    html[data-theme=light] .demo-panel{background:linear-gradient(180deg,#ffffff,#f2f7fb)}
    html[data-theme=light] .select,html[data-theme=light] .input,html[data-theme=light] .textarea{background:var(--field);border-color:var(--line)}
    html[data-theme=light] .table th{background:var(--table-head);color:#61758c}
    html[data-theme=light] .table td{color:#26384d}
    html[data-theme=light] .btn.ghost{background:rgba(19,34,53,.025)}
    html[data-theme=light] .flow-box,html[data-theme=light] .suggestion,html[data-theme=light] .mini-stat{background:rgba(19,34,53,.025)}
    html[data-theme=light] .brand-mark{color:#fff}
    html[data-theme=light] .hero h1 span{background:linear-gradient(135deg,#132235,#2478e5);-webkit-background-clip:text;background-clip:text;color:transparent}
    html[data-theme=light] .eyebrow{color:#4c637a}
    html[data-theme=light] .top-badge{color:#526b82}
    html[data-theme=light] .upload-label{background:rgba(36,120,229,.035);border-color:rgba(36,120,229,.24)}
    html[data-theme=light] .upload-label:hover{background:rgba(36,120,229,.07);border-color:rgba(36,120,229,.48)}
    html[data-theme=light] .data-grid-shell{background:#f8fbff;border-color:rgba(53,79,108,.14)}
    html[data-theme=light] .data-grid-head{background:linear-gradient(180deg,#f4f8fc,#edf4fa);border-color:rgba(53,79,108,.11)}
    html[data-theme=light] .data-grid-row{background:#fff;border-color:rgba(53,79,108,.12)}
    html[data-theme=light] .data-grid-row input{background:#fff;color:#132235;border-color:rgba(53,79,108,.12)}
    html[data-theme=light] .data-grid-row input:focus{border-color:rgba(36,120,229,.36);box-shadow:0 0 0 3px rgba(36,120,229,.08)}
    html[data-theme=light] .footer-row{color:#60738a}
    html[data-theme=light] .premium-range{background:linear-gradient(180deg,rgba(36,120,229,.035),rgba(19,34,53,.012));box-shadow:inset 0 1px 0 rgba(255,255,255,.92),0 12px 32px rgba(26,52,79,.07)}
    html[data-theme=light] .range{background:linear-gradient(90deg,var(--accent) 0%,var(--accent2) var(--range-pct),#dbe5ef var(--range-pct),#dbe5ef 100%);box-shadow:inset 0 1px 2px rgba(33,57,80,.16),0 0 0 1px rgba(53,79,108,.05)}
    html[data-theme=light] .range::-webkit-slider-thumb,html[data-theme=light] .range::-moz-range-thumb{border-color:#fff;background:linear-gradient(145deg,#fff,#e7f6ff);box-shadow:0 5px 16px rgba(26,52,79,.18),0 0 0 5px rgba(36,120,229,.10)}
    html[data-theme=light] .range-float{background:#fff;border-color:rgba(36,120,229,.18);box-shadow:0 10px 24px rgba(26,52,79,.12);color:#132235}
    html[data-theme=light] .location-status{color:#526b82}
    html[data-theme=light] .location-status.good{color:#12824f}
    html[data-theme=light] .location-status.bad{color:#b92c46}
    html[data-theme=light] .control-kicker,html[data-theme=light] .field-help,html[data-theme=light] .metric .label,html[data-theme=light] .panel-head span{color:#65788c}
    html[data-theme=dark] .leaflet-layer.gp-arcgis{filter:brightness(.72) saturate(.72) contrast(1.04)}
    html[data-theme=dark] .leaflet-container{background:#0b1728}
    html[data-theme=dark] .leaflet-layer.gp-satellite{filter:brightness(.58) saturate(.78) contrast(1.08)}
    html[data-theme=light] .leaflet-tile-pane{filter:none}
    html[data-theme=light] .leaflet-layer.gp-satellite{filter:saturate(.92) contrast(1.02)}
    .leaflet-container{font-family:Inter,system-ui,sans-serif;background:#dfe8f2}
.optimizer-3d-wrap{position:relative;overflow:hidden;border-radius:20px}
.optimizer-3d-wrap .map{transition:filter .45s ease}
.optimizer-3d-wrap.is-3d .map{filter:saturate(1.05) contrast(1.02)}
.gp-3d-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:450;transition:opacity .18s ease}
.optimizer-3d-wrap .gp-3d-badge{position:absolute;right:12px;bottom:12px;z-index:460;padding:5px 9px;border-radius:9px;background:rgba(7,17,31,.72);color:#dbe8f7;font:800 8px Inter,sans-serif;letter-spacing:.08em;pointer-events:none}
html[data-theme=light] .optimizer-3d-wrap .gp-3d-badge{background:rgba(255,255,255,.9);color:#2b415a;box-shadow:0 6px 16px rgba(26,52,79,.12)}
.map-3d-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--surface2);color:var(--muted);border-radius:9px;padding:6px 9px;font:800 9px Inter,sans-serif;cursor:pointer}
.map-3d-toggle:hover,.map-3d-toggle.active{color:var(--text);border-color:rgba(103,232,249,.38);background:rgba(78,161,255,.09)}
html[data-theme=light] .map-3d-toggle{background:#fff;color:#536a81}
html[data-theme=light] .optimizer-3d-wrap.is-3d .map{filter:saturate(1.04) contrast(1.02)}

    .gp-map-control{backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,.18);box-shadow:0 12px 32px rgba(5,18,33,.18)!important}
    .gp-map-control .leaflet-control-layers-list{margin:7px 9px}
    .gp-map-control .leaflet-control-layers-toggle{width:38px;height:38px;background-size:20px}
    .gp-map-control .leaflet-control-layers{border-radius:14px;overflow:hidden}
    .gp-map-control .leaflet-control-layers-expanded{padding:7px 8px;line-height:1.7;font-size:11px}
    html[data-theme=dark] .gp-map-control .leaflet-control-layers-expanded{color:#eaf4ff}
    html[data-theme=light] .gp-map-control .leaflet-control-layers-expanded{color:#20354b}
    html[data-theme=light] .gp-map-control{background:rgba(255,255,255,.9);border-color:rgba(53,79,108,.14)}
    html[data-theme=dark] .gp-map-control{background:rgba(8,18,31,.84);border-color:rgba(157,184,214,.16)}
    html[data-theme=light] .leaflet-control-zoom a{background:#fff;color:#26384d;border-color:rgba(53,79,108,.14)}
    html[data-theme=light] .leaflet-control-attribution{background:rgba(255,255,255,.86);color:#53677b}
    html[data-theme=light] .leaflet-popup-content-wrapper,html[data-theme=light] .leaflet-popup-tip{background:#fff;color:#132235}
    html[data-theme=light] .leaflet-tooltip{background:#fff;color:#132235;border-color:rgba(53,79,108,.14);box-shadow:0 8px 24px rgba(26,52,79,.12)}
    html[data-theme=light] .card,html[data-theme=light] .panel,html[data-theme=light] .metric,html[data-theme=light] .compare-card,html[data-theme=light] .table-wrap,html[data-theme=light] .location-item,html[data-theme=light] .diagnostics>div,html[data-theme=light] .assumption-grid>div,html[data-theme=light] .market-kpis>div,html[data-theme=light] .formula-lines span,html[data-theme=light] .model-chip{background:rgba(255,255,255,.88);color:var(--text);box-shadow:0 14px 34px rgba(26,52,79,.06)}
    html[data-theme=light] .controls{background:rgba(255,255,255,.94)}
    html[data-theme=light] .field label{color:#4f647a}
    html[data-theme=light] .field label span{color:#2478e5}
    html[data-theme=light] .location-card{background:linear-gradient(180deg,rgba(36,120,229,.06),rgba(255,255,255,.96))}
    html[data-theme=light] .demo-panel{color:var(--text)}
    html[data-theme=light] .demo-panel>div:last-child{color:#60738a !important}
    html[data-theme=light] .compare-card.featured{background:linear-gradient(180deg,rgba(36,120,229,.08),rgba(18,169,199,.035))}
    html[data-theme=light] .decision-banner{background:linear-gradient(135deg,rgba(36,120,229,.08),rgba(18,169,199,.035))}
    html[data-theme=light] .formula-main{background:linear-gradient(135deg,rgba(36,120,229,.08),rgba(18,169,199,.035))}
    html[data-theme=light] .toast{background:#fff;color:#132235}
    html[data-theme=light] .select,html[data-theme=light] .input,html[data-theme=light] .textarea{color:#132235}
    html[data-theme=light] .btn{background:#eef4fa;color:#132235}
    html[data-theme=light] .btn.primary{color:#fff;background:linear-gradient(135deg,var(--accent),#1c5fd6);border-color:transparent;box-shadow:0 10px 26px rgba(36,120,229,.28)}html[data-theme=light] .btn.primary:hover{filter:brightness(1.05)}
    html[data-theme=light] .mini-btn{background:#eef4fa;color:#132235}
    html[data-theme=light] .network-data{background:linear-gradient(180deg,#ffffff,#f6f9fc) !important;border-color:var(--line) !important}
    html[data-theme=light] .data-editor-card{background:linear-gradient(180deg,rgba(36,120,229,.045),rgba(255,255,255,.96));box-shadow:0 12px 32px rgba(26,52,79,.07)}
    html[data-theme=light] .data-schema span{background:#f2f6fa;color:#5f7389}
    html[data-theme=light] .data-editor-wrap{background:#f7fafe;border-color:rgba(36,120,229,.18);box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 12px 26px rgba(26,52,79,.06)}
    html[data-theme=light] .data-editor-wrap .data-box{color:#1c2f43}
    html[data-theme=light] .data-editor-footer{background:#f1f6fa;border-top-color:rgba(53,79,108,.10)}
    html[data-theme=light] .import-success{background:linear-gradient(135deg,rgba(21,156,98,.08),rgba(36,120,229,.035));color:#137e51}html[data-theme=light] .demo-window{background:linear-gradient(145deg,#eef4fa,#ffffff);border-color:rgba(36,120,229,.14);box-shadow:0 20px 48px rgba(26,52,79,.10)}html[data-theme=light] .demo-window-bar{background:#f4f8fc;border-bottom-color:rgba(53,79,108,.10)}html[data-theme=light] .demo-window-bar i{box-shadow:none}html[data-theme=light] .demo-window-title{color:#60738a}html[data-theme=light] .demo-stage-card{border-color:rgba(53,79,108,.12);background:#f8fbff}html[data-theme=light] .demo-stage-card small,html[data-theme=light] .demo-stage-card span,html[data-theme=light] .demo-window-actions span{color:#64778d}html[data-theme=light] .demo-progress{background:#dde7f0}html[data-theme=light] .map-floating{background:rgba(255,255,255,.9);color:#1f3349;border-color:rgba(53,79,108,.12);box-shadow:0 10px 24px rgba(26,52,79,.10)}html[data-theme=light] .map-floating span{color:#64778d}
html[data-theme=light] .card,html[data-theme=light] .panel,html[data-theme=light] .controls,html[data-theme=light] .feature,html[data-theme=light] .info-card,html[data-theme=light] .data-import-card,html[data-theme=light] .data-editor-card,html[data-theme=light] .network-setting,html[data-theme=light] .location-item,html[data-theme=light] .suggestion,html[data-theme=light] .mini-stat,html[data-theme=light] .flow-box,html[data-theme=light] .compare-card,html[data-theme=light] .table-wrap{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
html[data-theme=light] .location-card,html[data-theme=light] .network-settings-shell{background:linear-gradient(145deg,rgba(36,120,229,.06),rgba(18,169,199,.025) 48%,rgba(255,255,255,.95))}
html[data-theme=light] .field label,html[data-theme=light] .range-title,html[data-theme=light] .data-editor-head p,html[data-theme=light] .data-editor-note,html[data-theme=light] .network-setting label,html[data-theme=light] .panel-head span,html[data-theme=light] .field-help{color:var(--muted)}
html[data-theme=light] .data-grid-shell{background:#f8fbff;border-color:rgba(53,79,108,.14);box-shadow:0 12px 30px rgba(26,52,79,.06)}
html[data-theme=light] .data-grid-head{background:linear-gradient(180deg,#f4f8fc,#eaf2f8);color:#526a82;border-color:rgba(53,79,108,.12);position:sticky;top:0;z-index:2}
html[data-theme=light] .data-grid-row{background:#fff;border-color:rgba(53,79,108,.12);box-shadow:0 4px 12px rgba(26,52,79,.035)}
html[data-theme=light] .data-grid-row input{background:#fff;color:#132235;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .network-table-row{background:#fff;border-color:rgba(53,79,108,.12);box-shadow:0 4px 12px rgba(26,52,79,.035)}
html[data-theme=light] .network-table-row input{background:#fff;color:#132235;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .network-table-head{color:#526a82}
html[data-theme=light] .network-file-status{color:#137e51}
html[data-theme=light] .format-chip{background:#eef7fb;border-color:rgba(36,120,229,.16);color:#157b91}
html[data-theme=light] .data-import-title span,html[data-theme=light] .data-import-title strong{color:var(--text)}
html[data-theme=light] .data-row-remove,html[data-theme=light] .network-row-remove{color:#60738a;background:#eef3f8;border-color:rgba(53,79,108,.10)}
html[data-theme=light] .network-kicker,html[data-theme=light] .data-editor-badge{color:#2378a1;background:rgba(36,120,229,.07);border-color:rgba(36,120,229,.15)}
html[data-theme=light] .table th{background:#eaf1f8;color:#60738a}
html[data-theme=light] .table td{color:#26384d;border-bottom-color:rgba(53,79,108,.09)}
html[data-theme=light] .table-wrap{background:#fff}
html[data-theme=light] .theme-toggle{background:#fff;border-color:rgba(53,79,108,.15)}
html[data-theme=light] .optimizer-tour-nav{background:#fff;color:#132235;border-color:rgba(53,79,108,.15)}
html[data-theme=light] .nav-links a:hover,html[data-theme=light] .nav-links a.active{background:rgba(36,120,229,.07);color:#132235}
html[data-theme=light] .panel-head h3,html[data-theme=light] .page-head h1,html[data-theme=light] h1,html[data-theme=light] h2,html[data-theme=light] h3,html[data-theme=light] h4{color:var(--text)}
html[data-theme=light] .table,html[data-theme=light] table{color:var(--text)}
html[data-theme=light] .map-style-switch button{background:#fff;color:#536a81;border-color:rgba(53,79,108,.14)}
html[data-theme=light] .map-style-switch button.active,html[data-theme=light] .map-style-switch button:hover{background:rgba(36,120,229,.08);color:#1d5fae}
html[data-theme=light] .leaflet-control-zoom a:hover{background:#eef4fa;color:#132235}
html[data-theme=light] .leaflet-control-layers-toggle{background-color:#fff}
html[data-theme=light] .leaflet-control-layers{background:#fff;color:#20354b}
html[data-theme=light] input::placeholder,html[data-theme=light] textarea::placeholder{color:#7b8da0;opacity:1}
html[data-theme=light] .btn.ghost:hover,html[data-theme=light] .mini-btn:hover{background:#eef4fa}
html[data-theme=light] footer{background:linear-gradient(180deg,transparent,rgba(226,235,244,.72));border-top-color:rgba(53,79,108,.10)}

html[data-theme=light] .upload-arrow,html[data-theme=light] .mini-btn{color:#2478e5}
html[data-theme=light] .range-float{background:#fff;color:#17324f;border-color:rgba(36,120,229,.18);box-shadow:0 9px 22px rgba(26,52,79,.14)}
html[data-theme=light] .network-setting .range-float{background:#fff;color:#17324f}

    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 20% -10%,rgba(78,161,255,.14),transparent 32%),radial-gradient(circle at 100% 30%,rgba(103,232,249,.08),transparent 26%),var(--bg);color:var(--text);font-family:Inter,sans-serif;min-height:100vh}.shell{width:min(1440px,calc(100% - 36px));margin:0 auto}
    nav{position:sticky;top:0;z-index:50;backdrop-filter:blur(18px);background:rgba(6,16,30,.8);border-bottom:1px solid var(--line)}.nav-inner{height:74px;display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{display:flex;align-items:center;gap:11px;text-decoration:none;color:var(--text)}.brand-mark{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 8px 25px rgba(78,161,255,.32);color:#06101e;font-weight:900}.brand-word{font-family:"Space Grotesk";font-size:21px;font-weight:700;letter-spacing:.3px}.nav-links{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.nav-links a{color:var(--muted);text-decoration:none;padding:10px 13px;border-radius:11px;font-size:13px;font-weight:600}.nav-links a:hover,.nav-links a.active{color:var(--text);background:rgba(255,255,255,.055)}.top-badge{display:flex;align-items:center;gap:8px;color:#bcd0e7;font-size:12px}.dot{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 16px rgba(57,217,138,.8)}.theme-toggle{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--surface2);color:var(--text);border-radius:12px;padding:8px 10px;cursor:pointer;font:inherit;font-size:11px;font-weight:700;transition:.2s ease;white-space:nowrap}.theme-toggle:hover{transform:translateY(-1px);border-color:rgba(78,161,255,.42)}.theme-toggle .theme-icon{width:22px;height:22px;border-radius:8px;display:grid;place-items:center;background:rgba(78,161,255,.11);color:var(--accent)}.theme-label{min-width:42px;text-align:left}
    main{padding:38px 0 78px}.hero{display:grid;grid-template-columns:1.15fr .85fr;gap:28px;align-items:stretch}.eyebrow{display:inline-flex;gap:8px;align-items:center;padding:7px 10px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.028);color:#bdd0e6;font-size:12px;font-weight:600}.hero h1{font-family:"Space Grotesk";font-size:clamp(42px,6vw,74px);line-height:.98;letter-spacing:-2.8px;margin:19px 0 18px;max-width:850px}.hero h1 span{background:linear-gradient(135deg,#ffffff,#6fdcff);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{font-size:17px;line-height:1.75;color:var(--muted);max-width:760px;margin:0}.hero-actions{display:flex;gap:11px;flex-wrap:wrap;margin-top:28px}.btn{border:0;color:var(--text);background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:12px 17px;font-size:13px;font-weight:700;cursor:pointer;transition:.2s transform,.2s border-color,.2s background}.btn:hover{transform:translateY(-1px);border-color:rgba(103,232,249,.35)}.btn.primary{background:linear-gradient(135deg,var(--accent),#3575ff);border-color:transparent;box-shadow:0 10px 28px rgba(53,117,255,.25)}.btn.ghost{background:rgba(255,255,255,.025)}.hero-card{background:linear-gradient(180deg,rgba(17,33,54,.94),rgba(10,24,40,.96));border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow);padding:18px;display:flex;flex-direction:column;justify-content:space-between;min-height:350px;overflow:hidden;position:relative}.hero-card:before{content:"";position:absolute;inset:-30% 30% 45% -15%;background:radial-gradient(circle,rgba(78,161,255,.2),transparent 65%)}.hero-card>*{position:relative;z-index:1}.home-map-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:10px}.home-map-title{font-size:11px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.home-map-sub{display:block;margin-top:4px;color:var(--muted);font-size:9px;line-height:1.45}.home-map-actions{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}.home-map-actions button{border:1px solid var(--line);background:rgba(255,255,255,.035);color:var(--muted);padding:6px 8px;border-radius:9px;font:700 8px Inter,sans-serif;cursor:pointer;transition:.25s ease}.home-map-actions button:hover,.home-map-actions button.active{color:var(--text);border-color:rgba(103,232,249,.35);background:rgba(78,161,255,.09)}.home-map-shell{position:relative}.mini-map{height:290px;border-radius:20px;overflow:hidden;border:1px solid var(--line);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 18px 45px rgba(0,0,0,.16)}.home-map-overlay{position:absolute;left:12px;top:12px;z-index:500;display:grid;grid-template-columns:repeat(2,auto);gap:6px;padding:7px;border:1px solid rgba(255,255,255,.16);border-radius:14px;background:rgba(6,16,30,.72);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 12px 28px rgba(0,0,0,.22);pointer-events:none}.home-map-overlay div{padding:7px 8px;border-radius:10px;background:rgba(255,255,255,.045)}.home-map-overlay span{display:block;color:#9eb5cc;font-size:7px;text-transform:uppercase;letter-spacing:.09em}.home-map-overlay strong{display:block;margin-top:2px;color:#eef7ff;font-size:11px}.home-map-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px;padding:9px 10px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.025);font-size:9px;color:var(--muted)}.home-map-bottom b{color:var(--text)}@keyframes gpPulse{0%{transform:scale(.8);opacity:.9;box-shadow:0 0 0 0 rgba(103,232,249,.28)}75%{transform:scale(1.9);opacity:0;box-shadow:0 0 0 16px rgba(103,232,249,0)}100%{opacity:0}}html[data-theme=light] .home-map-actions button{background:#fff;color:#60738a}html[data-theme=light] .home-map-overlay{background:rgba(255,255,255,.86);border-color:rgba(53,79,108,.14)}html[data-theme=light] .home-map-overlay div{background:rgba(36,120,229,.045)}html[data-theme=light] .home-map-overlay span{color:#63778d}html[data-theme=light] .home-map-overlay strong{color:#132235}.hero-stat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}.mini-stat{padding:11px 12px;border-radius:14px;background:rgba(255,255,255,.035);border:1px solid var(--line)}.mini-stat .k{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}.mini-stat strong{display:block;margin-top:5px;font-size:16px}
    .section-title{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:82px 0 20px}.section-title h2{font-family:"Space Grotesk";font-size:31px;margin:0;letter-spacing:-1px}.section-title p{margin:0;color:var(--muted);max-width:650px;line-height:1.6;font-size:14px}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}.feature{padding:20px}.feature-icon{width:41px;height:41px;border-radius:13px;display:grid;place-items:center;background:rgba(78,161,255,.1);color:#8ad7ff;font-weight:800;margin-bottom:15px}.feature h3{margin:0 0 7px;font-size:15px}.feature p{margin:0;color:var(--muted);line-height:1.65;font-size:13px}
    .demo-wrap{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px}.demo-steps{padding:20px}.step{display:flex;gap:13px;padding:14px 0;border-bottom:1px solid var(--line)}.step:last-child{border-bottom:0}.step-num{min-width:32px;height:32px;border-radius:10px;background:rgba(78,161,255,.11);display:grid;place-items:center;color:#84cfff;font-weight:800;font-size:12px}.step h4{margin:0 0 3px;font-size:14px}.step p{margin:0;color:var(--muted);font-size:12px;line-height:1.55}.demo-panel{padding:18px;background:linear-gradient(180deg,#0d1a2b,#091525);position:relative;overflow:hidden}.demo-panel:after{content:"";position:absolute;width:240px;height:240px;border-radius:50%;right:-90px;top:-100px;background:radial-gradient(circle,rgba(103,232,249,.12),transparent 65%)}.demo-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.demo-header strong{font-size:13px}.tag{padding:5px 8px;border-radius:999px;background:rgba(57,217,138,.09);color:#74e6a8;font-size:10px;font-weight:700}.flow{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px}.flow-box{padding:16px;border:1px solid var(--line);background:rgba(255,255,255,.026);border-radius:16px;min-height:110px}.flow-box .small{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.12em}.flow-box strong{font-size:25px;display:block;margin-top:7px}.flow-box span{display:block;color:#9ab0c9;font-size:11px;margin-top:4px}
    .page-head{display:flex;justify-content:space-between;align-items:end;gap:22px;margin-bottom:24px}.page-head h1{font-family:"Space Grotesk";font-size:42px;margin:0 0 8px;letter-spacing:-1.6px}.page-head p{margin:0;color:var(--muted);max-width:820px;line-height:1.7;font-size:14px}
    .optimizer-layout{display:grid;grid-template-columns:340px minmax(0,1fr);gap:18px;align-items:start}.controls{padding:18px;position:sticky;top:92px;height:max-content;max-height:calc(100vh - 112px);overflow:auto;scrollbar-width:thin}.controls::-webkit-scrollbar{width:7px}.controls::-webkit-scrollbar-thumb{background:rgba(103,232,249,.16);border-radius:999px}.optimizer-tour-launch{display:inline-flex;align-items:center;gap:7px}.optimizer-tour-launch:before{content:"✦";font-size:12px}.sla-card{margin-top:10px}.sla-card .range-stage{padding-top:27px}.controls h3{font-size:14px;margin:0 0 16px}.field{margin-bottom:14px}.field label{display:flex;justify-content:space-between;gap:10px;font-size:11px;color:#b8c9dc;margin-bottom:7px}.field label span{color:#73d4ff;font-weight:700}.select,.input,.textarea{width:100%;background:#0c1b2d;color:var(--text);border:1px solid var(--line);outline:0;border-radius:12px;padding:11px 12px;font:inherit;font-size:12px}.textarea{min-height:110px;resize:vertical}.select:focus,.input:focus,.textarea:focus{border-color:rgba(78,161,255,.5);box-shadow:0 0 0 3px rgba(78,161,255,.08)}.range-wrap{position:relative;padding-top:2px}.premium-range{padding:14px 14px 12px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.012));box-shadow:inset 0 1px 0 rgba(255,255,255,.025),0 10px 28px rgba(0,0,0,.08);transition:border-color .45s cubic-bezier(.22,1,.36,1),transform .45s cubic-bezier(.22,1,.36,1),box-shadow .45s cubic-bezier(.22,1,.36,1),background .45s ease,color .45s ease}.premium-range:hover{border-color:rgba(78,161,255,.34);box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 16px 34px rgba(0,0,0,.15);transform:translateY(-2px)}.range-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}.range-title{font-size:10px;color:var(--muted);font-weight:800;letter-spacing:.08em}.range-value{display:inline-flex;align-items:center;justify-content:center;min-width:64px;padding:7px 10px;border-radius:11px;border:1px solid rgba(78,161,255,.20);background:linear-gradient(135deg,rgba(78,161,255,.13),rgba(103,232,249,.08));color:var(--text);font-size:11px;font-weight:850;font-variant-numeric:tabular-nums;box-shadow:0 6px 16px rgba(0,0,0,.12);transition:transform .18s ease,background .25s ease,border-color .25s ease}.range-value.bump{transform:scale(1.045)}.range-stage{position:relative;padding:27px 5px 2px}.range{--range-pct:0%;appearance:none;-webkit-appearance:none;width:100%;height:7px;border:0;border-radius:999px;outline:0;cursor:pointer;background:linear-gradient(90deg,var(--accent) 0%,var(--accent2) var(--range-pct),rgba(255,255,255,.09) var(--range-pct),rgba(255,255,255,.09) 100%);box-shadow:inset 0 1px 2px rgba(0,0,0,.34),0 0 0 1px rgba(255,255,255,.035);transition:background .08s linear,box-shadow .25s ease,filter .25s ease}.range:hover{filter:brightness(1.06)}.range:focus-visible{box-shadow:0 0 0 6px rgba(78,161,255,.11),inset 0 1px 2px rgba(0,0,0,.34)}.range::-webkit-slider-runnable-track{height:7px;border:0;border-radius:999px;background:transparent}.range::-moz-range-track{height:7px;border:0;border-radius:999px;background:transparent}.range::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:22px;height:22px;margin-top:-7.5px;border-radius:50%;border:3px solid var(--surface);background:linear-gradient(145deg,#ffffff,#b7f6ff);box-shadow:0 7px 19px rgba(0,0,0,.34),0 0 0 5px rgba(78,161,255,.12);transition:transform .18s cubic-bezier(.22,1,.36,1),box-shadow .18s ease}.range:hover::-webkit-slider-thumb{transform:scale(1.08);box-shadow:0 9px 23px rgba(0,0,0,.38),0 0 0 6px rgba(78,161,255,.15)}.range:active::-webkit-slider-thumb{transform:scale(1.18)}.range::-moz-range-thumb{width:22px;height:22px;border-radius:50%;border:3px solid var(--surface);background:linear-gradient(145deg,#ffffff,#b7f6ff);box-shadow:0 7px 19px rgba(0,0,0,.34),0 0 0 5px rgba(78,161,255,.12)}.range-float{position:absolute;left:var(--range-pct);top:0;transform:translateX(-50%) translateY(0);padding:5px 8px;border:1px solid rgba(103,232,249,.18);border-radius:9px;background:#0d1b2c;color:#eaf5ff;font-size:9px;font-weight:850;line-height:1;white-space:nowrap;pointer-events:none;box-shadow:0 8px 22px rgba(0,0,0,.18);transition:left .08s linear,transform .18s cubic-bezier(.22,1,.36,1),opacity .2s ease}.range-stage:focus-within .range-float{transform:translateX(-50%) translateY(-2px)}.range-scale{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:8px;margin-top:10px;padding:0 1px}.range-scale span:nth-child(3){color:var(--text);font-weight:700}.range[disabled]{cursor:not-allowed;opacity:.46;filter:grayscale(.25)}.range[disabled]::-webkit-slider-thumb{cursor:not-allowed;transform:none;box-shadow:none}.range[disabled]::-moz-range-thumb{cursor:not-allowed;box-shadow:none}.range-note{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;padding:8px 10px;border-radius:10px;border:1px solid rgba(78,161,255,.12);background:rgba(78,161,255,.035);color:var(--muted);font-size:9px;line-height:1.4}.range-note b{color:var(--accent);font-size:9px}.advanced-settings{margin-top:4px;border:1px solid var(--line);border-radius:16px;background:var(--surface2);overflow:hidden}.advanced-settings summary{list-style:none;cursor:pointer;padding:12px 13px;font-size:10px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;justify-content:space-between}.advanced-settings summary::-webkit-details-marker{display:none}.advanced-settings summary:after{content:'+';font-size:15px;color:var(--accent)}.advanced-settings[open] summary:after{content:'−'}.advanced-settings .advanced-body{padding:0 13px 13px}.advanced-settings .field:last-child{margin-bottom:0}
    .location-card{padding:14px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(78,161,255,.055),rgba(255,255,255,.015));border-radius:15px;margin-bottom:14px}.location-status{font-size:12px;color:#bfd0e3;line-height:1.55}.location-status.good{color:#76e9a6}.location-status.bad{color:#ff9bab}.location-actions{display:flex;gap:7px;margin-top:10px}.warehouse-add-panel{margin-top:10px;padding:11px;border:1px solid rgba(103,232,249,.18);border-radius:13px;background:rgba(103,232,249,.035)}.warehouse-add-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.warehouse-add-head strong{font-size:11px}.warehouse-add-head span{font-size:9px;color:var(--muted)}.warehouse-add-actions{display:flex;gap:7px;margin-top:8px}.warehouse-add-actions .btn{flex:1;padding:9px 10px;font-size:10px}.warehouse-add-list{display:grid;gap:6px;margin-top:8px}.warehouse-add-item{display:flex;align-items:center;justify-content:space-between;gap:7px;padding:7px 8px;border:1px solid var(--line);border-radius:10px;background:rgba(255,255,255,.018);font-size:9px}.warehouse-add-item span{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.warehouse-add-item button{border:1px solid var(--line);background:var(--surface2);color:var(--muted);border-radius:7px;padding:4px 6px;cursor:pointer;font-size:9px}.warehouse-add-item button:hover{color:var(--danger);border-color:rgba(255,107,125,.35)}.map-add-mode{outline:2px solid rgba(103,232,249,.42);box-shadow:0 0 0 5px rgba(103,232,249,.08)}.location-actions .btn{padding:9px 11px;font-size:11px}.upload-label{display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px dashed rgba(103,232,249,.28);background:rgba(103,232,249,.03);border-radius:12px;cursor:pointer;transition:.2s}.upload-label:hover{border-color:rgba(103,232,249,.62);background:rgba(103,232,249,.06)}.upload-icon{width:27px;height:27px;border-radius:8px;display:grid;place-items:center;background:rgba(103,232,249,.1);color:#79e5ff}.upload-copy{min-width:0}.upload-copy strong{display:block;font-size:11px}.upload-copy span{display:block;color:var(--muted);font-size:9px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.upload-input{display:none}
.mini-btn{border:1px solid var(--line);background:var(--surface2);color:var(--text);border-radius:8px;padding:5px 7px;font-size:9px;font-weight:800;cursor:pointer}.mini-btn:hover{border-color:rgba(103,232,249,.45);transform:translateY(-1px)}

.control-kicker{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#7891aa;margin-bottom:5px}.field-help{margin-top:6px;color:#7189a3;font-size:10px;line-height:1.5}.scenario-row{display:flex;gap:5px;flex-wrap:wrap;margin:-3px 0 13px}.scenario-row .mini-btn{padding:6px 8px}.scenario-row .mini-btn:hover{border-color:rgba(78,161,255,.55);color:var(--accent)}.upload-arrow{margin-left:auto;font-size:9px;font-weight:800;color:var(--accent);padding:5px 7px;border-radius:8px;background:rgba(78,161,255,.08)}.upload-summary{margin-top:8px;padding:9px 10px;border:1px solid rgba(57,217,138,.18);border-radius:10px;background:rgba(57,217,138,.05);font-size:10px;color:#80dbaa;line-height:1.45}.upload-summary span{display:block;color:var(--muted);margin-top:2px}.optimize-main{width:100%;margin-top:5px}.decision-banner{margin-top:14px;padding:16px 18px;display:flex;justify-content:space-between;align-items:center;gap:18px;background:linear-gradient(135deg,rgba(78,161,255,.09),rgba(103,232,249,.035));border-color:rgba(78,161,255,.18)}.decision-kicker{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:800;margin-bottom:5px}.decision-banner strong{display:block;font-size:15px}.decision-banner #recommendationReason{display:block;color:var(--muted);font-size:11px;margin-top:4px}.decision-pills{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.decision-pills span{padding:7px 10px;border:1px solid var(--line);border-radius:999px;background:rgba(255,255,255,.02);font-size:9px;color:var(--muted);white-space:nowrap}.page-head-actions{display:flex;align-items:center;gap:8px}.optimizer-run-top{min-width:176px;box-shadow:0 12px 30px rgba(53,117,255,.24);font-size:12px;padding:13px 18px}.optimizer-run-top:disabled{opacity:.72;cursor:wait;transform:none}.top-two-section{margin-top:14px;padding:18px}.top-two-head{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;margin-bottom:14px}.top-two-head h3{margin:0;font-size:16px}.top-two-head p{margin:4px 0 0;color:var(--muted);font-size:10px;line-height:1.5}.top-two-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.top-two-card{position:relative;overflow:hidden;padding:17px;border:1px solid rgba(103,232,249,.18);border-radius:18px;background:linear-gradient(145deg,rgba(78,161,255,.095),rgba(103,232,249,.025));box-shadow:0 16px 38px rgba(0,0,0,.10)}.top-two-card::before{content:'';position:absolute;inset:-35% 35% 45% -18%;background:radial-gradient(circle,rgba(103,232,249,.14),transparent 64%);pointer-events:none}.top-two-card>*{position:relative;z-index:1}.top-two-rank{display:inline-flex;align-items:center;justify-content:center;min-width:30px;height:24px;padding:0 9px;border-radius:999px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#07111f;font-size:9px;font-weight:900;letter-spacing:.08em}.top-two-card h4{margin:10px 0 4px;font-size:18px;letter-spacing:-.02em}.top-two-card .site-meta{color:var(--muted);font-size:10px}.top-two-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:14px}.top-two-metrics div{padding:10px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.028)}.top-two-metrics span{display:block;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.09em}.top-two-metrics strong{display:block;margin-top:4px;font-size:12px}.top-two-badge{margin-top:12px;display:inline-flex;padding:6px 8px;border:1px solid rgba(57,217,138,.16);border-radius:999px;background:rgba(57,217,138,.06);color:#73e4a1;font-size:8px;font-weight:800}.top-two-empty{grid-column:1/-1;padding:22px;border:1px dashed var(--line);border-radius:16px;color:var(--muted);font-size:10px;text-align:center;background:rgba(255,255,255,.018)}html[data-theme=light] .optimizer-run-top{box-shadow:0 12px 30px rgba(36,120,229,.18)}html[data-theme=light] .top-two-card{background:linear-gradient(145deg,rgba(36,120,229,.07),rgba(18,169,199,.025));box-shadow:0 14px 34px rgba(26,52,79,.08)}html[data-theme=light] .top-two-card::before{background:radial-gradient(circle,rgba(36,120,229,.10),transparent 64%)}html[data-theme=light] .top-two-rank{color:#fff}html[data-theme=light] .top-two-badge{color:#137e51;background:rgba(21,156,98,.07)}
.insight-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:14px;margin-top:14px}.insight-card{padding:18px}.insight-card h3{margin:0;font-size:16px}.insight-card p{margin:5px 0 0;color:var(--muted);font-size:10px;line-height:1.6}.why-list{display:grid;gap:8px;margin-top:14px}.why-item{display:grid;grid-template-columns:34px 1fr;gap:9px;align-items:start;padding:10px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.018)}.why-rank{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#07111f;font-weight:900;font-size:10px}.why-item strong{display:block;font-size:11px}.why-item span{display:block;color:var(--muted);font-size:9px;line-height:1.45;margin-top:2px}.report-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.scenario-lab{margin-top:14px;padding:18px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.02),rgba(255,255,255,.008))}.scenario-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px}.scenario-card{padding:11px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.018)}.scenario-card span{display:block;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.08em}.scenario-card strong{display:block;font-size:13px;margin-top:5px}.scenario-card small{display:block;color:var(--muted);font-size:8px;margin-top:3px}.scenario-status{margin-top:10px;color:var(--muted);font-size:9px;line-height:1.5}.data-ready{display:inline-flex;gap:6px;align-items:center;padding:6px 9px;border-radius:999px;background:rgba(57,217,138,.07);border:1px solid rgba(57,217,138,.14);color:#73e4a1;font-size:8px;font-weight:800}.data-ready i{width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 9px currentColor}.recommendation-note{margin-top:9px;padding:10px 11px;border-left:3px solid var(--accent);border-radius:0 12px 12px 0;background:rgba(78,161,255,.045);font-size:9px;color:var(--muted);line-height:1.5}.frontier-hint{margin-top:7px;color:var(--muted);font-size:9px}.frontier-hint b{color:var(--text)}
html[data-theme=light] .insight-card,html[data-theme=light] .scenario-lab{background:var(--surface)}
@media(max-width:900px){.insight-grid{grid-template-columns:1fr}.scenario-cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.scenario-cards{grid-template-columns:1fr}}.chart-tall{height:430px}.chart-caption{font-size:10px;color:var(--muted);padding-top:10px}.map-legend{display:flex;gap:14px;flex-wrap:wrap;padding:10px 2px 0;color:var(--muted);font-size:9px}.map-legend span{display:inline-flex;align-items:center;gap:5px}.map-legend .legend-dot{display:inline-block;width:7px;height:7px}.demand-dot{background:#4ea1ff}.warehouse-dot{background:#67e8f9}.user-dot{background:#a78bfa}.compare-grid{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center}.compare-card{padding:15px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.02)}.compare-card.featured{background:linear-gradient(180deg,rgba(78,161,255,.07),rgba(103,232,249,.025));border-color:rgba(78,161,255,.25)}.compare-card span{display:block;font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em}.compare-card strong{display:block;font-size:22px;margin:7px 0}.compare-card small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.compare-arrow{color:var(--accent2);font-size:22px}.delta-row{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}.delta-row span{padding:7px 10px;border-radius:999px;background:rgba(57,217,138,.07);color:#73e4a1;border:1px solid rgba(57,217,138,.13);font-size:9px;font-weight:800}.diagnostics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.diagnostics>div,.assumption-grid>div{padding:11px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.02)}.diagnostics span,.assumption-grid span{display:block;color:var(--muted);font-size:9px}.diagnostics strong,.assumption-grid strong{display:block;margin-top:5px;font-size:12px}.assumption-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.formula-box{margin-top:9px;padding:12px;border-radius:13px;border:1px dashed rgba(103,232,249,.22);background:rgba(103,232,249,.03)}.formula-box strong{display:block;font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent2);margin-bottom:4px}.formula-box span{font-size:10px;color:var(--muted);line-height:1.55}.warehouse-top-row td{background:linear-gradient(90deg,rgba(78,161,255,.075),rgba(103,232,249,.025))}.warehouse-top-row td:first-child{position:relative}.warehouse-top-row td:first-child:before{content:'TOP';display:inline-flex;align-items:center;justify-content:center;margin-right:6px;padding:3px 5px;border-radius:999px;background:rgba(103,232,249,.12);color:var(--accent2);font-size:7px;font-weight:900;letter-spacing:.08em;vertical-align:middle}.util-cell{display:flex;align-items:center;gap:7px;min-width:95px}.util-cell>span{min-width:38px}.util-cell i{display:block;width:48px;height:5px;border-radius:99px;background:var(--surface3);overflow:hidden}.util-cell b{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--accent2))}.status-chip{display:inline-flex;padding:4px 7px;border-radius:999px;font-size:8px;font-weight:800}.status-chip.ok{background:rgba(57,217,138,.07);color:#73e4a1}.status-chip.warn{background:rgba(255,189,102,.08);color:#ffc36f}.empty-state{padding:15px;color:var(--muted);font-size:10px;line-height:1.5}.suggestion-main{min-width:0}.suggestion-main strong{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.suggestion-right{display:flex;align-items:end;gap:8px}.suggestion-right>span{margin:0}.suggestion-right .mini-btn{margin-top:4px}.leaflet-control-attribution{font-size:8px}
    .workspace{min-width:0}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{padding:16px 17px;min-width:0}.metric .label{font-size:10px;color:#8097af;text-transform:uppercase;letter-spacing:.1em}.metric strong{display:block;font-size:24px;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.metric small{display:block;color:#7a91a9;font-size:10px;margin-top:4px}.dashboard-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr);gap:14px;margin-top:14px}.panel{padding:16px;min-width:0}.panel-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:13px}.panel-head h3{font-size:14px;margin:0}.panel-head span{color:#7991aa;font-size:10px}.map{height:440px;border-radius:16px;overflow:hidden;border:1px solid var(--line)}.chart-box{height:440px;position:relative}.chart-box canvas{width:100%!important;height:100%!important}.legend-row{display:flex;gap:7px;flex-wrap:wrap}.legend-pill{display:inline-flex;align-items:center;gap:6px;color:#95abc2;font-size:9px}.legend-dot{width:7px;height:7px;border-radius:50%}.split-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.table-wrap{overflow:auto;max-height:350px;border:1px solid var(--line);border-radius:14px}.table{width:100%;border-collapse:collapse;min-width:520px}.table th,.table td{padding:10px 11px;border-bottom:1px solid var(--line);text-align:left;font-size:11px}.table th{position:sticky;top:0;background:#0e1d30;color:#93a9c0;font-size:9px;text-transform:uppercase;letter-spacing:.08em}.table td{color:#d8e5f2}.table tr:last-child td{border-bottom:0}.suggestions{display:grid;gap:8px}.suggestion{display:flex;justify-content:space-between;align-items:center;padding:11px;border:1px solid var(--line);background:rgba(255,255,255,.02);border-radius:13px}.suggestion strong{display:block;font-size:11px}.suggestion span{font-size:9px;color:var(--muted)}.suggestion-right{text-align:right}.suggestion-right strong{font-size:12px;color:#7fd8ff}.suggestion-right span{display:block;margin-top:2px}.toast{position:fixed;right:18px;bottom:18px;z-index:120;background:#0f2034;color:#edf6ff;border:1px solid var(--line);border-radius:14px;padding:12px 14px;box-shadow:var(--shadow);font-size:12px;display:none}.toast.show{display:block;animation:rise .25s ease}@keyframes rise{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}
    .page-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.info-card{padding:20px}.info-card h3{margin:0 0 7px;font-size:15px}.info-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.7}.info-card strong{font-size:28px;font-family:"Space Grotesk"}.warehouse-board{display:grid;grid-template-columns:1.05fr .95fr;gap:14px}.map-large{height:600px}.location-list{display:grid;gap:10px;max-height:600px;overflow:auto}.location-item{padding:14px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.02)}.location-item .row{display:flex;justify-content:space-between;gap:10px}.location-item strong{font-size:12px}.location-item span{font-size:10px;color:var(--muted)}.network-data{display:grid;grid-template-columns:.8fr 1.2fr;gap:12px;padding:12px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.025),rgba(255,255,255,.01))}.data-import-card{padding:14px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.02);min-width:0}.data-import-title{display:flex;align-items:center;gap:10px;margin-bottom:11px}.data-import-title strong{display:block;font-size:12px}.data-import-title span{display:block;color:var(--muted);font-size:9px;margin-top:2px}.data-import-icon{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:rgba(78,161,255,.1);color:var(--accent);font-size:15px}.format-chip{margin-top:9px;padding:8px 9px;border:1px solid rgba(103,232,249,.15);border-radius:9px;background:rgba(103,232,249,.035);font:700 9px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--accent2);overflow:auto;white-space:nowrap}.data-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}.data-box{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px;line-height:1.55}.data-editor-card{margin-top:2px;padding:13px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(180deg,rgba(78,161,255,.055),rgba(255,255,255,.018));box-shadow:0 10px 28px rgba(0,0,0,.06)}.data-editor-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px}.data-editor-head h4{margin:2px 0 4px;font-size:13px}.data-editor-head p{margin:0;color:var(--muted);font-size:10px;line-height:1.45}.data-editor-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 8px;border:1px solid rgba(103,232,249,.16);border-radius:999px;background:rgba(103,232,249,.04);color:var(--accent2);font-size:8px;font-weight:800;white-space:nowrap}.data-schema{display:grid;grid-template-columns:1.1fr 1fr 1fr 1fr;gap:5px;margin:8px 0 10px}.data-schema span{padding:7px 8px;border-radius:9px;border:1px solid var(--line);background:var(--surface2);color:var(--muted);font:700 8px/1 ui-monospace,SFMono-Regular,Consolas,monospace;text-align:center}.data-editor-wrap{position:relative;border:1px solid rgba(78,161,255,.2);border-radius:13px;overflow:hidden;background:rgba(5,14,27,.72);box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 14px 30px rgba(0,0,0,.08)}.data-editor-wrap .data-box{width:100%;min-height:126px;padding:12px 13px;background:transparent;border:0;outline:none;resize:vertical;color:#dce8f5}.data-editor-wrap .data-box:focus{box-shadow:inset 0 0 0 1px rgba(78,161,255,.38)}.data-editor-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 9px;border-top:1px solid rgba(255,255,255,.06);background:rgba(255,255,255,.018)}.data-editor-footer span{font-size:9px;color:var(--muted)}.import-success{display:flex;align-items:center;gap:9px;margin-top:8px;padding:10px 11px;border:1px solid rgba(57,217,138,.22);border-radius:12px;background:linear-gradient(135deg,rgba(57,217,138,.10),rgba(78,161,255,.035));color:#8ae3af;font-size:10px;line-height:1.4}.import-success .success-icon{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:rgba(57,217,138,.14);font-weight:900}.import-success strong{display:block;font-size:10px}.import-success span{display:block;color:var(--muted);margin-top:2px}.network-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.market-search{flex:1;min-width:180px}
.formula-panel{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px;align-items:stretch}.formula-main{padding:18px;border-radius:15px;background:linear-gradient(135deg,rgba(78,161,255,.09),rgba(103,232,249,.035));border:1px solid rgba(78,161,255,.16);font-family:"Space Grotesk";font-size:20px;line-height:1.35}.formula-lines{display:grid;gap:7px}.formula-lines span{padding:11px 12px;border:1px solid var(--line);border-radius:11px;background:rgba(255,255,255,.02);color:var(--muted);font-size:10px;line-height:1.45}
    footer{border-top:1px solid var(--line);padding:30px 0 44px;color:#6f859e;font-size:11px}.footer-row{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
.model-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:2px 0 15px}.model-chip{padding:9px 8px;border-radius:11px;border:1px solid var(--line);background:rgba(255,255,255,.022);text-align:center;font-size:9px;font-weight:800;color:var(--muted);letter-spacing:.04em}.model-chip b{display:block;color:var(--text);font-size:10px;margin-bottom:2px}.model-chip i{font-style:normal;color:#71d7b1}.solver-badge{display:inline-flex;align-items:center;gap:7px;padding:5px 8px;border-radius:999px;background:rgba(57,217,138,.07);border:1px solid rgba(57,217,138,.18);color:#78e5aa;font-size:9px;font-weight:800}.solver-badge:before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}.stress-lab{margin-top:14px;padding:16px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,rgba(167,139,250,.075),rgba(78,161,255,.035));box-shadow:0 14px 34px rgba(0,0,0,.07)}.stress-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.stress-head h3{margin:0 0 4px;font-size:14px}.stress-head p{margin:0;color:var(--muted);font-size:10px;line-height:1.5}.stress-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.stress-results{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stress-card{padding:11px 12px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.stress-card span{display:block;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.1em}.stress-card strong{display:block;margin-top:5px;font-size:15px}.stress-card small{display:block;margin-top:3px;color:var(--muted);font-size:9px}.stress-status{margin-top:10px;color:var(--muted);font-size:10px}.tour-launch-wrap{display:flex;align-items:center;gap:8px}.tour-launch-hint{padding:6px 9px;border:1px solid rgba(103,232,249,.18);border-radius:999px;background:rgba(103,232,249,.045);color:var(--accent2);font-size:8px;font-weight:800;letter-spacing:.03em}html[data-theme=light] .tour-launch-hint{background:rgba(36,120,229,.06);border-color:rgba(36,120,229,.15);color:#2167b8}html[data-theme=light] .stress-lab{background:linear-gradient(135deg,rgba(115,88,210,.055),rgba(36,120,229,.03))}html[data-theme=light] .optimizer-tour-card{background:linear-gradient(155deg,#ffffff,#f4f8fc);color:#17283a}@view-transition{navigation:auto}::view-transition-old(root){animation:gp-old-page .38s cubic-bezier(.22,1,.36,1) both}::view-transition-new(root){animation:gp-new-page .62s cubic-bezier(.22,1,.36,1) both}@keyframes gp-old-page{to{opacity:0;transform:scale(.988) translate3d(0,-6px,0);filter:blur(1.5px)}}.page-leaving{animation:gp-page-leave .2s cubic-bezier(.22,1,.36,1) forwards}@keyframes gp-page-leave{to{opacity:0;transform:translate3d(0,-6px,0) scale(.996)}}@keyframes gp-new-page{from{opacity:0;transform:translate3d(0,16px,0) scale(.996);filter:blur(2px)}to{opacity:1;transform:none;filter:none}}body{animation:gp-page-boot .7s cubic-bezier(.22,1,.36,1) both}@keyframes gp-page-boot{from{opacity:0;transform:translate3d(0,10px,0)}to{opacity:1;transform:none}}.reveal{--reveal-y:26px;--reveal-delay:0ms;opacity:0;transform:translate3d(0,var(--reveal-y),0) scale(.996);filter:blur(0);will-change:opacity,transform;backface-visibility:hidden;transform-style:preserve-3d}.reveal.is-visible{animation:gp-reveal-in .88s cubic-bezier(.16,1,.3,1) var(--reveal-delay) both}@keyframes gp-reveal-in{from{opacity:0;transform:translate3d(0,var(--reveal-y),0) scale(.985)}55%{opacity:.94;transform:translate3d(0,-2px,0) scale(1.004)}to{opacity:1;transform:none}}.reveal-stagger>*{opacity:0;transform:translate3d(0,20px,0) scale(.996)}.reveal-stagger.is-visible>*{animation:gp-child-reveal .72s cubic-bezier(.22,1,.36,1) calc(var(--child-delay,0ms)) both}@keyframes gp-child-reveal{from{opacity:0;transform:translate3d(0,20px,0) scale(.996)}to{opacity:1;transform:none}}.optimization-replay{animation:gp-result-replay .86s cubic-bezier(.22,1,.36,1) var(--replay-delay,0ms) both}.network-settings-shell{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(78,161,255,.08),rgba(103,232,249,.025) 45%,rgba(255,255,255,.015));border:1px solid rgba(78,161,255,.16);box-shadow:0 22px 55px rgba(0,0,0,.12)}.network-settings-shell:before{content:'';position:absolute;inset:-55% 55% 35% -12%;background:radial-gradient(circle,rgba(103,232,249,.18),transparent 62%);pointer-events:none}.network-settings-inner{position:relative;z-index:1}.network-settings-grid{display:grid;grid-template-columns:1.3fr 1fr 1fr 1fr;gap:10px}.network-setting{padding:13px;border:1px solid var(--line);border-radius:16px;background:var(--surface);box-shadow:0 8px 24px rgba(0,0,0,.05);transition:transform .35s cubic-bezier(.22,1,.36,1),border-color .35s ease,box-shadow .35s ease}.network-setting:hover{transform:translateY(-2px);border-color:rgba(78,161,255,.25);box-shadow:0 14px 32px rgba(0,0,0,.09)}.network-setting .range-stage{padding:26px 2px 0}.network-setting label{display:flex;justify-content:space-between;gap:8px;font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px}.network-setting label b{color:var(--text);font-size:11px;text-transform:none;letter-spacing:0}.network-setting .select,.network-setting .input{width:100%;height:40px}.network-settings-actions{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}.network-settings-actions p{margin:0;color:var(--muted);font-size:10px;line-height:1.5}.network-data-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.network-import-panel{min-height:240px}.network-table{display:grid;gap:6px}.network-table-head,.network-table-row{display:grid;grid-template-columns:34px 1.35fr .95fr .95fr .95fr 34px;gap:6px;align-items:center}.network-table-head{padding:0 6px 7px;color:var(--muted);font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;position:sticky;top:0;z-index:3;background:var(--surface);border-bottom:1px solid var(--line)}.network-table-row{padding:7px;border:1px solid var(--line);border-radius:12px;background:var(--surface);box-shadow:0 5px 14px rgba(0,0,0,.05);transition:transform .22s ease,border-color .22s ease}.network-table-row:hover{transform:translateY(-1px);border-color:rgba(78,161,255,.22)}.network-table-row input{height:36px;width:100%;border:1px solid var(--line);border-radius:10px;background:var(--surface2);color:var(--text);padding:0 9px;font:600 10px Inter,sans-serif;outline:none}.network-table-row input:focus{border-color:rgba(78,161,255,.45);box-shadow:0 0 0 3px rgba(78,161,255,.08)}.network-table-scroll{max-height:330px;overflow:auto;padding:4px 2px 2px}.network-row-index{width:26px;height:26px;margin:auto;display:grid;place-items:center;border-radius:8px;background:rgba(78,161,255,.09);color:var(--accent);font-size:9px;font-weight:800}.network-file-status{display:flex;align-items:flex-start;gap:9px;padding:9px 10px;border-radius:12px;border:1px solid rgba(57,217,138,.22);background:rgba(57,217,138,.07);font-size:10px;margin-top:9px;color:#80dca6}.network-file-status>span{font-size:15px;line-height:1}.network-file-status strong{display:block;color:var(--text);margin-bottom:2px}.map-stage{position:relative;border-radius:22px;overflow:hidden;border:1px solid var(--line);background:var(--surface2);box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}.map-stage .map{border-radius:22px}.map-floating{position:absolute;left:14px;top:14px;z-index:5;padding:8px 10px;border-radius:11px;background:rgba(7,17,31,.74);backdrop-filter:blur(15px);border:1px solid rgba(255,255,255,.12);color:#dbe8f7;font-size:9px;font-weight:800;letter-spacing:.04em}.map-floating span{color:#8da6bf;font-weight:500;margin-left:4px}
.map-style-switch{display:inline-flex;align-items:center;gap:4px;padding:4px;border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:12px;backdrop-filter:blur(14px)}
.map-style-switch button{border:0;background:transparent;color:var(--muted);padding:6px 8px;border-radius:9px;font:800 8px/1 Inter,sans-serif;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;transition:background .25s ease,color .25s ease,transform .25s ease;white-space:nowrap}
.map-style-switch button:hover{color:var(--text);transform:translateY(-1px)}
.map-style-switch button.active{background:linear-gradient(135deg,rgba(78,161,255,.18),rgba(103,232,249,.12));color:var(--text);box-shadow:0 4px 14px rgba(0,0,0,.10)}
html[data-theme=light] .map-style-switch{background:rgba(255,255,255,.88);box-shadow:0 8px 24px rgba(26,52,79,.08)}
html[data-theme=light] .map-style-switch button{color:#6a7d92}
html[data-theme=light] .map-style-switch button.active{background:linear-gradient(135deg,rgba(36,120,229,.10),rgba(18,169,199,.08));color:#1f3349}
.demo-window{position:relative;overflow:hidden;min-height:240px;background:linear-gradient(145deg,#0a1727,#10243b);border:1px solid rgba(103,232,249,.14);border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.25)}.demo-window-bar{display:flex;align-items:center;gap:6px;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.025)}.demo-window-bar i{width:7px;height:7px;border-radius:50%;background:#ff6b7d}.demo-window-bar i:nth-child(2){background:#ffbd66}.demo-window-bar i:nth-child(3){background:#39d98a}.demo-window-title{margin-left:5px;color:#9db5ce;font-size:9px;font-weight:800}.demo-window-body{padding:15px}.demo-progress{height:4px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden}.demo-progress b{display:block;width:22%;height:100%;background:linear-gradient(90deg,#4ea1ff,#67e8f9);border-radius:999px;transition:width .5s cubic-bezier(.22,1,.36,1)}.demo-stage{margin-top:13px;display:grid;grid-template-columns:1fr 1fr;gap:8px}.demo-stage-card{padding:14px;border:1px solid rgba(255,255,255,.08);border-radius:13px;background:rgba(255,255,255,.025);min-height:110px}.demo-stage-card small{color:#89a2bc;text-transform:uppercase;letter-spacing:.1em}.demo-stage-card strong{display:block;margin-top:7px;font-size:20px;font-family:"Space Grotesk"}.demo-stage-card span{display:block;margin-top:4px;color:#8ca6c1;font-size:9px}.demo-window-actions{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:10px}.demo-window-actions span{color:#8ca6c1;font-size:9px}@keyframes gp-result-replay{from{opacity:.25;transform:translate3d(0,18px,0) scale(.992);filter:blur(2px)}to{opacity:1;transform:none;filter:none}}.theme-surface-transition,body,nav,.card,.premium-range,.panel,.metric,.info-card,.location-card,.flow-box,.suggestion,.mini-stat,.compare-card,.table-wrap,.theme-toggle,.btn,.input,.select,.textarea{transition:background-color .42s ease,border-color .42s ease,color .42s ease,box-shadow .42s ease}.page-leaving{pointer-events:none}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal,.reveal-stagger>*{opacity:1;transform:none;filter:none;transition:none}::view-transition-old(root),::view-transition-new(root){animation:none}}.market-preview{padding:4px}.market-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.market-kpis>div{padding:15px;border:1px solid var(--line);border-radius:15px;background:rgba(255,255,255,.022)}.market-kpis span{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.11em}.market-kpis strong{display:block;font-size:20px;margin-top:5px}.market-actions{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}.market-actions span{color:var(--muted);font-size:11px;line-height:1.5}.market-loading{display:flex;align-items:center;gap:13px;padding:20px}.market-loading span{display:block;color:var(--muted);font-size:11px;margin-top:4px}.loading-ring{width:24px;height:24px;border-radius:50%;border:3px solid rgba(78,161,255,.15);border-top-color:var(--accent);animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}    
    .network-settings-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.network-setting{min-width:0}.network-setting .range-stage{padding-top:29px}.network-settings-shell{padding:18px}.network-settings-shell .panel-head{align-items:flex-start}.network-settings-actions{margin-top:12px}
    .network-demand-panel{padding:18px}.network-demand-toolbar{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:14px}.network-demand-title h3{margin:0;font-size:15px}.network-demand-title p{margin:4px 0 0;color:var(--muted);font-size:10px;line-height:1.5}.dataset-presets{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.dataset-preset{position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 13px;border:1px solid var(--line);border-radius:15px;background:var(--surface2);color:var(--text);text-align:left;cursor:pointer;transition:transform .35s cubic-bezier(.22,1,.36,1),border-color .35s ease,box-shadow .35s ease,background .35s ease}.dataset-preset:hover{transform:translateY(-2px);border-color:rgba(78,161,255,.3);box-shadow:0 15px 34px rgba(0,0,0,.09)}.dataset-preset.active{border-color:rgba(78,161,255,.5);box-shadow:0 0 0 3px rgba(78,161,255,.08),0 16px 34px rgba(0,0,0,.10);background:linear-gradient(135deg,rgba(78,161,255,.1),rgba(103,232,249,.04))}.dataset-preset strong{display:block;font-size:11px}.dataset-preset span{display:block;color:var(--muted);font-size:9px;margin-top:3px}.dataset-preset b{flex:none;padding:6px 8px;border-radius:9px;background:rgba(78,161,255,.1);color:var(--accent);font-size:8px;white-space:nowrap}.network-demand-body{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,.45fr);gap:12px;align-items:stretch}.demand-editor-shell{border:1px solid var(--line);border-radius:18px;background:var(--surface);overflow:hidden;box-shadow:0 12px 30px rgba(0,0,0,.06)}.demand-editor-head{display:grid;grid-template-columns:42px minmax(130px,1.45fr) minmax(115px,.9fr) minmax(115px,.9fr) minmax(130px,1fr) 42px;gap:6px;align-items:center;padding:10px 12px;background:linear-gradient(180deg,var(--surface2),rgba(255,255,255,.01));border-bottom:1px solid var(--line);color:var(--muted);font-size:8px;font-weight:900;text-transform:uppercase;letter-spacing:.1em}.demand-editor-body{max-height:360px;overflow:auto;padding:8px}.demand-editor-row{display:grid;grid-template-columns:42px minmax(130px,1.45fr) minmax(115px,.9fr) minmax(115px,.9fr) minmax(130px,1fr) 42px;gap:6px;align-items:center;padding:7px;border:1px solid transparent;border-radius:13px;transition:background .2s ease,border-color .2s ease,transform .2s ease}.demand-editor-row:hover{background:var(--surface2);border-color:var(--line);transform:translateX(1px)}.demand-editor-row input{width:100%;height:38px;border:1px solid var(--line);border-radius:10px;background:var(--field);color:var(--text);padding:0 10px;font:600 10px Inter,sans-serif;outline:none;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}.demand-editor-row input:focus{border-color:rgba(78,161,255,.48);box-shadow:0 0 0 4px rgba(78,161,255,.08)}.demand-row-index{width:28px;height:28px;display:grid;place-items:center;border-radius:9px;background:rgba(78,161,255,.08);color:var(--accent);font-size:9px;font-weight:900;margin:auto}.demand-remove{width:32px;height:32px;border:1px solid var(--line);border-radius:9px;background:transparent;color:var(--muted);font-size:16px;cursor:pointer;transition:all .2s ease}.demand-remove:hover{color:var(--danger);border-color:rgba(201,48,77,.3);background:rgba(201,48,77,.06)}.demand-editor-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 12px;border-top:1px solid var(--line);background:var(--surface2)}.demand-editor-foot span{color:var(--muted);font-size:9px}.demand-editor-actions{display:flex;gap:7px;flex-wrap:wrap}.demand-import-side{display:grid;gap:10px}.demand-import-card{padding:14px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(180deg,var(--surface),var(--surface2));box-shadow:0 12px 30px rgba(0,0,0,.05)}.demand-import-card .data-import-title{margin-bottom:9px}.dataset-status-panel{padding:12px;border-radius:14px;border:1px solid rgba(57,217,138,.2);background:rgba(57,217,138,.06)}.dataset-status-panel strong{display:block;font-size:10px;color:var(--text)}.dataset-status-panel span{display:block;margin-top:3px;color:var(--muted);font-size:9px;line-height:1.45}.network-settings-shell .network-settings-grid + .network-settings-grid{margin-top:10px!important}
    html[data-theme=light] .dataset-preset{background:#fff}
    html[data-theme=light] .network-settings-shell{background:linear-gradient(145deg,rgba(36,120,229,.06),rgba(18,169,199,.025),#fff)}
    html[data-theme=light] .demand-editor-head,html[data-theme=light] .demand-editor-foot{background:#f2f6fa}.network-settings-actions .btn{white-space:nowrap}
    @media(max-width:1080px){.hero{grid-template-columns:1fr}.grid4{grid-template-columns:repeat(2,1fr)}.optimizer-layout{grid-template-columns:1fr}.controls{position:relative;top:auto}.dashboard-grid{grid-template-columns:1fr}.split-grid{grid-template-columns:1fr}.warehouse-board{grid-template-columns:1fr}.map-large{height:430px}.market-kpis{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:1080px){.network-settings-grid{grid-template-columns:repeat(2,1fr)}.network-data-grid{grid-template-columns:1fr}}    @media(max-width:760px){.data-grid-head,.data-grid-row{grid-template-columns:28px 1.1fr .9fr .9fr .8fr 32px}.data-grid-head span:nth-child(2),.data-grid-row input:nth-child(2){display:none}.data-grid-head span:nth-child(3),.data-grid-row input:nth-child(3){display:none}.network-data{grid-template-columns:1fr}.network-settings-grid{grid-template-columns:1fr}.network-table-head,.network-table-row{grid-template-columns:28px 1.2fr 1fr 1fr 1fr 28px}.demo-stage{grid-template-columns:1fr}.shell{width:min(100% - 22px,1440px)}.nav-inner{height:auto;min-height:68px;padding:10px 0;align-items:flex-start}.nav-links{gap:2px}.nav-links a{font-size:11px;padding:8px}.top-badge{display:none}.hero h1{font-size:46px}.grid4,.page-grid{grid-template-columns:1fr}.demo-wrap{grid-template-columns:1fr}.flow{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.map{height:350px}.chart-box{height:350px}.page-head{display:block}.page-head .btn{margin-top:16px}.model-strip{grid-template-columns:repeat(2,1fr)}.market-kpis{grid-template-columns:1fr 1fr}.market-actions{display:block}.market-actions .btn{margin-bottom:10px}}
  
.optimizer-tour{position:fixed;inset:0;z-index:3000;pointer-events:none;opacity:0;visibility:hidden;transition:opacity .34s ease,visibility .34s ease}.optimizer-tour.is-open{opacity:1;visibility:visible}.optimizer-tour-backdrop{position:absolute;inset:0;background:rgba(2,9,18,.56);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);pointer-events:auto}.optimizer-tour-spotlight{position:fixed;z-index:3001;border:1px solid rgba(103,232,249,.65);border-radius:18px;box-shadow:0 0 0 9999px rgba(2,9,18,.48),0 0 0 5px rgba(78,161,255,.12),0 18px 55px rgba(0,0,0,.26);pointer-events:none;transition:top .48s cubic-bezier(.22,1,.36,1),left .48s cubic-bezier(.22,1,.36,1),width .48s cubic-bezier(.22,1,.36,1),height .48s cubic-bezier(.22,1,.36,1),opacity .22s ease}.optimizer-tour-card{position:fixed;z-index:3002;width:min(360px,calc(100vw - 36px));border:1px solid rgba(117,180,255,.18);border-radius:22px;background:linear-gradient(155deg,rgba(13,27,45,.99),rgba(8,18,31,.995));box-shadow:0 30px 90px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.035);padding:19px;pointer-events:auto;transform:translateY(12px) scale(.97);opacity:0;transition:left .5s cubic-bezier(.22,1,.36,1),top .5s cubic-bezier(.22,1,.36,1),transform .48s cubic-bezier(.22,1,.36,1),opacity .4s ease}.optimizer-tour.is-open .optimizer-tour-card{transform:none;opacity:1}.optimizer-tour-kicker{font-size:9px;color:#7fdcf0;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.optimizer-tour-title{margin:6px 0 5px;font-size:18px;letter-spacing:-.03em}.optimizer-tour-text{margin:0;color:var(--muted);font-size:11px;line-height:1.65}.optimizer-tour-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.optimizer-tour-close{width:30px;height:30px;border-radius:10px;border:1px solid var(--line);background:var(--surface2);color:var(--text);cursor:pointer;font-size:16px;flex:0 0 auto}.optimizer-tour-progress{display:flex;gap:5px;margin:15px 0}.optimizer-tour-progress i{display:block;height:4px;flex:1;border-radius:999px;background:rgba(255,255,255,.10);transition:background .25s ease}.optimizer-tour-progress i.is-active{background:linear-gradient(90deg,var(--accent),var(--accent2))}.optimizer-tour-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:16px}.optimizer-tour-footer .tour-skip{border:0;background:none;color:var(--muted);font:600 10px Inter,sans-serif;cursor:pointer;padding:8px 0}.optimizer-tour-actions{display:flex;gap:7px}.optimizer-tour-actions button{min-width:72px}.optimizer-tour-arrow{position:absolute;width:12px;height:12px;background:inherit;border-left:1px solid rgba(117,180,255,.18);border-top:1px solid rgba(117,180,255,.18);transform:rotate(45deg);display:none}.optimizer-tour-card[data-side="right"] .optimizer-tour-arrow{left:-7px;top:34px;display:block}.optimizer-tour-card[data-side="left"] .optimizer-tour-arrow{right:-7px;top:34px;transform:rotate(225deg);display:block}.optimizer-tour-card[data-side="bottom"] .optimizer-tour-arrow{top:-7px;left:34px;display:block}.optimizer-tour-card[data-side="top"] .optimizer-tour-arrow{bottom:-7px;left:34px;transform:rotate(225deg);display:block}html[data-theme=light] .optimizer-tour-backdrop{background:rgba(38,59,79,.25)}html[data-theme=light] .optimizer-tour-spotlight{box-shadow:0 0 0 9999px rgba(38,59,79,.23),0 0 0 5px rgba(36,120,229,.10),0 18px 55px rgba(26,52,79,.18)}html[data-theme=light] .optimizer-tour-card{background:linear-gradient(155deg,#ffffff,#f5f9fd);border-color:rgba(41,111,186,.15);box-shadow:0 30px 90px rgba(39,68,99,.18),inset 0 1px 0 rgba(255,255,255,.92)}

.optimizer-source-card{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(78,161,255,.07),rgba(103,232,249,.02));box-shadow:0 12px 28px rgba(0,0,0,.08)}.optimizer-source-card h4{margin:4px 0 4px;font-size:14px;letter-spacing:-.02em}.optimizer-source-card p{margin:0;color:var(--muted);font-size:10px;line-height:1.5}.source-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:8px}.source-metrics>div{padding:10px 11px;border:1px solid var(--line);border-radius:13px;background:var(--surface)}.source-metrics span{display:block;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.09em;font-weight:800}.source-metrics strong{display:block;margin-top:4px;color:var(--text);font-size:12px}@media(max-width:680px){.optimizer-source-card{align-items:flex-start;flex-direction:column}.optimizer-source-card .btn{width:100%}.source-metrics{grid-template-columns:1fr}}

.math-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}
.math-card{position:relative;padding:16px 15px 14px;border:1px solid var(--line);border-radius:17px;background:linear-gradient(145deg,rgba(78,161,255,.055),rgba(103,232,249,.018));overflow:hidden}
.math-card.wide{grid-column:1/-1}
.math-num{position:absolute;right:12px;top:10px;color:var(--accent,#67e8f9);font-size:9px;font-weight:900;letter-spacing:.12em}
.math-card h4{margin:0 28px 9px 0;font-size:12px;letter-spacing:.01em}
.math-card p{margin:9px 0 0;color:var(--muted);font-size:10px;line-height:1.65}
.math-formula{display:inline-block;padding:9px 11px;border:1px solid var(--line);border-radius:11px;background:var(--surface);color:var(--text);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;line-height:1.55}
.math-formula.large{font-size:11px;font-weight:700}
.math-subformula{margin-top:7px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px}
.logic-flow{display:flex;flex-wrap:wrap;align-items:center;gap:7px;padding:11px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.logic-flow span{padding:6px 8px;border-radius:8px;background:rgba(78,161,255,.09);font-size:9px;font-weight:800;color:var(--text)}
.logic-flow b{color:var(--accent,#67e8f9);font-size:12px}
.formula-note{margin-top:12px;padding:13px 14px;border-radius:14px;border:1px solid rgba(78,161,255,.22);background:linear-gradient(145deg,rgba(78,161,255,.09),rgba(103,232,249,.035));color:var(--muted);font-size:10px;line-height:1.7}
.formula-note strong{color:var(--text)}
.formula-note span{color:var(--text);font-weight:700}
@media(max-width:680px){.math-grid{grid-template-columns:1fr}.math-card.wide{grid-column:auto}.logic-flow{align-items:flex-start}.logic-flow b{display:none}}
/* ============ GRIDPOINT · 3D analytics ============ */
.analytics-3d .panel-head{align-items:flex-start}
.analytics-3d-tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.analytics-3d-tools .mini-btn.active{border-color:rgba(103,232,249,.5);color:var(--accent2)}
.analytics-3d-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.analytics-3d-card{position:relative;padding:15px;border:1px solid var(--line);border-radius:18px;background:var(--surface2);min-width:0}
.analytics-3d-card h4{margin:0 0 3px;font-size:13px;letter-spacing:-.01em}
.analytics-3d-card p{margin:0 0 11px;color:var(--muted);font-size:10px;line-height:1.55}
.analytics-3d-stage{position:relative;height:330px;border-radius:14px;background:radial-gradient(circle at 50% 16%,rgba(78,161,255,.10),transparent 64%);cursor:grab;touch-action:none;overflow:hidden}
.analytics-3d-stage.is-drag{cursor:grabbing}
.analytics-3d-stage canvas{display:block;width:100%;height:100%}
.analytics-3d-empty{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:22px;color:var(--muted);font-size:10px;line-height:1.6}
.analytics-3d-legend{display:flex;gap:13px;flex-wrap:wrap;margin-top:10px;color:var(--muted);font-size:9px;font-weight:800;letter-spacing:.04em}
.analytics-3d-legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;vertical-align:-1px}
html[data-theme=light] .analytics-3d-card{background:#fff;border-color:rgba(53,79,108,.12);box-shadow:0 10px 26px rgba(26,52,79,.05)}
html[data-theme=light] .analytics-3d-stage{background:radial-gradient(circle at 50% 16%,rgba(36,120,229,.085),transparent 64%)}
@media(max-width:980px){.analytics-3d-grid{grid-template-columns:1fr}.analytics-3d-stage{height:290px}}

/* ============ GRIDPOINT · light theme hardening (all pages) ============ */
html[data-theme=light] .eyebrow{background:rgba(36,120,229,.05);border-color:rgba(36,120,229,.16);color:#3d566f}
html[data-theme=light] .solver-badge{background:rgba(21,156,98,.08);border-color:rgba(21,156,98,.22);color:#127a4f}
html[data-theme=light] .model-chip{background:#fff;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .model-chip i{color:#0f8a5f}
html[data-theme=light] .metric small,html[data-theme=light] .metric .label{color:#63768b}
html[data-theme=light] .decision-kicker,html[data-theme=light] .data-ready,html[data-theme=light] .network-kicker{color:#2167b8}
html[data-theme=light] .decision-pills span{background:rgba(36,120,229,.07);border-color:rgba(36,120,229,.16);color:#1f4f7e}
html[data-theme=light] .top-two-card,html[data-theme=light] .why-item,html[data-theme=light] .scenario-card,html[data-theme=light] .stress-card,html[data-theme=light] .assumption-grid>div,html[data-theme=light] .diagnostics>div,html[data-theme=light] .network-preview-grid>div,html[data-theme=light] .source-metrics>div{background:#fff;border-color:rgba(53,79,108,.12);color:var(--text)}
html[data-theme=light] .top-two-card .site-meta,html[data-theme=light] .why-item span,html[data-theme=light] .scenario-card small,html[data-theme=light] .stress-card small,html[data-theme=light] .recommendation-note,html[data-theme=light] .scenario-status{color:#60738a}
html[data-theme=light] .top-two-rank,html[data-theme=light] .why-rank,html[data-theme=light] .top-two-badge{background:rgba(36,120,229,.09);color:#1d5fae}
html[data-theme=light] .empty-state,html[data-theme=light] .top-two-empty,html[data-theme=light] .chart-caption,html[data-theme=light] .map-legend,html[data-theme=light] .field-help,html[data-theme=light] .upload-summary span{color:#60738a}
html[data-theme=light] .status-chip.ok{background:rgba(21,156,98,.10);color:#11774c}
html[data-theme=light] .status-chip.warn{background:rgba(201,48,77,.09);color:#b32a44}
html[data-theme=light] .util-cell i{background:rgba(53,79,108,.12)}
html[data-theme=light] .warehouse-top-row td{background:rgba(36,120,229,.045)}
html[data-theme=light] .warehouse-add-panel,html[data-theme=light] .optimizer-source-card,html[data-theme=light] .advanced-settings,html[data-theme=light] .formula-box,html[data-theme=light] .upload-summary{background:linear-gradient(145deg,rgba(36,120,229,.045),rgba(255,255,255,.97));border-color:rgba(53,79,108,.12)}
html[data-theme=light] .warehouse-add-item{background:#fff;border-color:rgba(53,79,108,.12);color:var(--text)}
html[data-theme=light] .range-note{background:rgba(36,120,229,.05);border-color:rgba(36,120,229,.14)}
html[data-theme=light] .advanced-settings summary{color:#5a6e84}
html[data-theme=light] .math-card{background:linear-gradient(145deg,rgba(36,120,229,.05),rgba(18,169,199,.02));border-color:rgba(53,79,108,.12)}
html[data-theme=light] .math-formula,html[data-theme=light] .logic-flow{background:#fff;color:#17283a;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .math-num{color:#1f7fb8}
html[data-theme=light] .math-subformula,html[data-theme=light] .math-card p{color:#60738a}
html[data-theme=light] .logic-flow span{background:rgba(36,120,229,.08);color:#17283a}
html[data-theme=light] .logic-flow b{color:#1f7fb8}
html[data-theme=light] .formula-note{background:linear-gradient(145deg,rgba(36,120,229,.06),rgba(18,169,199,.025));border-color:rgba(36,120,229,.18);color:#5a6e84}
html[data-theme=light] .dataset-preset,html[data-theme=light] .demand-editor-shell,html[data-theme=light] .demand-import-card,html[data-theme=light] .dataset-status-panel,html[data-theme=light] .demand-editor-row{background:#fff;border-color:rgba(53,79,108,.12);color:var(--text)}
html[data-theme=light] .demand-editor-row input{background:#fff;color:#132235;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .demand-editor-row input:focus{border-color:rgba(36,120,229,.4);box-shadow:0 0 0 3px rgba(36,120,229,.08)}
html[data-theme=light] .demand-row-index{background:rgba(36,120,229,.09);color:#1d5fae}
html[data-theme=light] .demand-remove{background:#eef3f8;color:#60738a;border-color:rgba(53,79,108,.10)}
html[data-theme=light] .dataset-preset.active{border-color:rgba(36,120,229,.36);background:linear-gradient(145deg,rgba(36,120,229,.07),#fff)}
html[data-theme=light] .dataset-preset span span,html[data-theme=light] .network-demand-title p,html[data-theme=light] .dataset-status-panel span{color:#60738a}
html[data-theme=light] .market-loading strong{color:var(--text)}
html[data-theme=light] .market-actions span,html[data-theme=light] .location-item span{color:#60738a}
html[data-theme=light] .step h4,html[data-theme=light] .feature h3,html[data-theme=light] .info-card h3{color:var(--text)}
html[data-theme=light] .step p,html[data-theme=light] .feature p,html[data-theme=light] .section-title p,html[data-theme=light] .page-head p,html[data-theme=light] .hero p{color:#5c7087}
html[data-theme=light] .step-num{background:rgba(36,120,229,.09);color:#1d5fae}
html[data-theme=light] pre{color:#48607a}
html[data-theme=light] .loading-ring{border-color:rgba(36,120,229,.18);border-top-color:#2478e5}
/* lighter compositing in light mode – fewer blurred layers to repaint */
html[data-theme=light] .gp-map-control,html[data-theme=light] .map-style-switch,html[data-theme=light] .map-floating{backdrop-filter:none;-webkit-backdrop-filter:none}
html[data-theme=light] nav{backdrop-filter:blur(12px)}
.theme-surface-transition *{transition:background-color .32s ease,color .32s ease,border-color .32s ease!important}
@media(prefers-reduced-motion:reduce){.reveal,.reveal-stagger>*,.optimization-replay{animation:none!important;opacity:1!important;transform:none!important}}

.network-run-group{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.network-run-btn{min-width:210px;font-weight:800;letter-spacing:.01em;box-shadow:0 12px 30px rgba(78,161,255,.18)}
.network-run-btn:disabled{opacity:.65;cursor:progress}
html[data-theme=light] .network-run-btn{box-shadow:0 12px 26px rgba(36,120,229,.18)}
@media(max-width:700px){.network-settings-actions{flex-direction:column;align-items:stretch}.network-run-group{justify-content:stretch}.network-run-btn{flex:1}}
.network-settings-grid.cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}
@media(max-width:1080px){.network-settings-grid.cols-3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.network-settings-grid.cols-3{grid-template-columns:1fr}}

.optimizer-tour-nav.tour-pending{position:relative}
.optimizer-tour-nav.tour-pending:after{content:'';position:absolute;top:-3px;right:-3px;width:8px;height:8px;border-radius:50%;background:var(--accent2);animation:gp-tour-pulse 2.2s ease-out infinite}
@keyframes gp-tour-pulse{0%{box-shadow:0 0 0 0 rgba(103,232,249,.55)}70%{box-shadow:0 0 0 8px rgba(103,232,249,0)}100%{box-shadow:0 0 0 0 rgba(103,232,249,0)}}
body.tour-active{overflow:auto}
body.tour-active main{filter:none}

/* ============ GRIDPOINT map visualizer ============ */
.warehouse-pin{position:relative;width:44px;height:60px;display:flex;flex-direction:column;align-items:center;justify-content:flex-start}
.warehouse-pin .wp-ring{position:absolute;top:6px;left:50%;width:30px;height:30px;margin-left:-15px;border-radius:50%;border:2px solid var(--wcolor);opacity:.75;animation:gp-wp-pulse 2.4s cubic-bezier(.22,1,.36,1) infinite}
.warehouse-pin .wp-ring-2{animation-delay:1.2s}
.warehouse-pin.is-top .wp-ring{border-width:3px}
@keyframes gp-wp-pulse{0%{transform:scale(.55);opacity:.8}70%{transform:scale(1.85);opacity:0}100%{transform:scale(1.85);opacity:0}}
.warehouse-pin .wp-body{position:relative;z-index:2;width:30px;height:30px;border-radius:11px;display:grid;place-items:center;background:var(--wcolor);border:2px solid rgba(255,255,255,.92);box-shadow:0 8px 20px rgba(3,12,24,.45)}
.warehouse-pin.is-top .wp-body{width:34px;height:34px;border-radius:13px}
.warehouse-pin .wp-label{position:relative;z-index:2;margin-top:5px;padding:2px 7px;border-radius:999px;background:rgba(6,16,30,.85);color:#fff;font:800 9px Inter,sans-serif;letter-spacing:.06em;white-space:nowrap}
html[data-theme=light] .warehouse-pin .wp-label{background:rgba(255,255,255,.95);color:#16283c;box-shadow:0 4px 12px rgba(26,52,79,.18)}
.leaflet-custom-tooltip{background:rgba(8,18,31,.94)!important;border:1px solid rgba(157,184,214,.22)!important;border-radius:12px!important;box-shadow:0 14px 34px rgba(0,0,0,.34)!important;padding:0!important;color:#eaf4ff!important}
.leaflet-custom-tooltip:before{display:none!important}
html[data-theme=light] .leaflet-custom-tooltip{background:rgba(255,255,255,.97)!important;border-color:rgba(53,79,108,.16)!important;color:#16283c!important;box-shadow:0 14px 30px rgba(26,52,79,.16)!important}
.map-tooltip{padding:9px 11px;min-width:168px;font-family:Inter,sans-serif}
.map-tooltip .mtt-name{font-size:11px;font-weight:800;margin-bottom:6px;letter-spacing:-.01em}
.map-tooltip .mtt-row{display:flex;justify-content:space-between;gap:12px;font-size:9.5px;line-height:1.7}
.map-tooltip .mtt-row span{opacity:.68}
.map-tooltip .mtt-row b{font-weight:700}
.map-tooltip .mtt-oor{margin-top:6px;padding-top:5px;border-top:1px solid rgba(244,63,94,.28);color:#fb7185;font-size:9px;font-weight:700}
.nb-label div{display:inline-block;border:1px solid;color:#f1f5f9;font-size:9px;font-weight:600;padding:2px 6px;border-radius:5px;white-space:nowrap;transform:translate(10px,-8px);line-height:1.35}
.nb-label div span{display:block;font-size:8px;font-weight:800}
html[data-theme=light] .nb-label div{color:#16283c}
.assignment-line{pointer-events:none}
.cluster-legend{display:flex;gap:7px;flex-wrap:wrap;padding:11px 2px 0}
.cluster-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:var(--surface2);color:var(--text);font:800 9px Inter,sans-serif;cursor:pointer;transition:transform .2s ease,border-color .2s ease}
.cluster-chip:hover{transform:translateY(-1px);border-color:rgba(103,232,249,.45)}
.cluster-chip i{width:9px;height:9px;border-radius:50%;box-shadow:0 0 8px currentColor}
.cluster-chip b{color:var(--muted);font-weight:700;font-size:8.5px}
html[data-theme=light] .cluster-chip{background:#fff;border-color:rgba(53,79,108,.14)}
.map-add-mode{cursor:crosshair!important}
/* ============ warehouse count quick picker ============ */
.wh-count-card{margin-top:10px;padding:13px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(145deg,rgba(78,161,255,.06),rgba(103,232,249,.02))}
.wh-count-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}
.wh-count-head strong{font-size:11px;letter-spacing:-.01em}
.wh-count-head span{color:var(--muted);font-size:9px;font-weight:700}
.wh-count-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}
.wh-count-btn{padding:8px 0;border:1px solid var(--line);border-radius:10px;background:var(--surface2);color:var(--text);font:800 10px Inter,sans-serif;cursor:pointer;transition:transform .18s ease,border-color .18s ease,background .18s ease}
.wh-count-btn:hover{transform:translateY(-1px);border-color:rgba(103,232,249,.45)}
.wh-count-btn.active{background:linear-gradient(135deg,rgba(78,161,255,.22),rgba(103,232,249,.14));border-color:rgba(103,232,249,.5);color:var(--text)}
.wh-count-btn.wide{grid-column:span 2}
.wh-count-foot{margin-top:9px;color:var(--muted);font-size:9px;line-height:1.55}
html[data-theme=light] .wh-count-card{background:linear-gradient(145deg,rgba(36,120,229,.05),#fff);border-color:rgba(53,79,108,.12)}
html[data-theme=light] .wh-count-btn{background:#fff;border-color:rgba(53,79,108,.12)}
html[data-theme=light] .wh-count-btn.active{background:linear-gradient(135deg,rgba(36,120,229,.14),rgba(18,169,199,.09));border-color:rgba(36,120,229,.35);color:#16283c}

/* ============ GRIDPOINT · light-mode contrast fixes ============ */
html[data-theme=light] .feature-icon{background:rgba(36,120,229,.10);color:#1f6fd0}
html[data-theme=light] .tag{background:rgba(21,156,98,.11);color:#127a4f}
html[data-theme=light] .flow-box span{color:#5c7087}
html[data-theme=light] .upload-icon{background:rgba(18,169,199,.11);color:#157b91}
html[data-theme=light] .delta-row span{background:rgba(21,156,98,.09);color:#127a4f;border-color:rgba(21,156,98,.18)}
html[data-theme=light] .suggestion-right strong{color:#1d5fae}
html[data-theme=light] .optimizer-tour-kicker{color:#1f7fb8}

.upload-btn{position:relative;cursor:pointer}
.upload-input-hidden{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}

</style>
</head>
<body data-page="{{ active }}">
<nav>
  <div class="shell nav-inner">
    <a class="brand" href="/">
      <span class="brand-mark">G</span><span class="brand-word">GRIDPOINT</span>
    </a>
    <div class="nav-links">
      <a class="{{ 'active' if active == 'home' else '' }}" href="/">Overview</a>
      <a class="{{ 'active' if active == 'locations' else '' }}" href="/locations">Warehouse Network</a>
      <a class="{{ 'active' if active == 'optimizer' else '' }}" href="/optimizer">Optimizer</a>
      <a class="{{ 'active' if active == 'how' else '' }}" href="/how-it-works">How it works</a>
    </div>
    <div style="display:flex;align-items:center;gap:8px"><div class="top-badge"><span class="dot"></span>Optimization engine online</div>{% if active == 'optimizer' %}<button class="btn ghost optimizer-tour-nav" id="optimizerTourLaunch" type="button" aria-label="Open optimizer tour">✦ Tour</button>{% endif %}{% if active == 'locations' %}<button class="btn ghost optimizer-tour-nav" id="networkTourLaunch" type="button" aria-label="Open warehouse network tour">✦ Tour</button>{% endif %}<button id="themeToggle" class="theme-toggle" type="button" aria-label="Toggle light and dark mode"><span class="theme-icon" id="themeIcon">☾</span><span class="theme-label" id="themeLabel">Dark</span></button></div>
  </div>
</nav>
<main class="shell">{{ content|safe }}</main>
<footer><div class="shell footer-row"><span>GRIDPOINT · Warehouse location intelligence</span><span>ArcGIS basemaps · road-aware routing · browser location optional</span></div></footer>
<div id="toast" class="toast"></div>
<script>
function toast(message){const el=document.getElementById('toast'); if(!el)return; el.textContent=message; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),3200)}
function money(n){const v=Number(n)||0; return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(v)}
function num(n,d=0){const v=Number(n); return Number.isFinite(v)?v:d}
function km(n){return `${num(n).toFixed(1)} km`}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function safePick(...vals){for(const v of vals){if(Number.isFinite(Number(v)))return Number(v)}return 0}
function formatRangeValue(id,val){if(id==='capacity')return val.toLocaleString('en-IN');if(id==='radius')return `${val} km`;if(id==='growth')return `${val}%`;if(id==='slaMinutes')return `${val} min`;return val.toLocaleString('en-IN')}
function refreshRangeUI(id){const el=document.getElementById(id),target=document.getElementById(({maxWarehouses:'maxWhValue',exactWarehouses:'exactWhValue',capacity:'capacityValue',radius:'radiusValue',growth:'growthValue',slaMinutes:'slaMinutesValue'}[id]||''));if(!el)return;const min=Number(el.min||0),max=Number(el.max||100);let val=Number(el.value||0);val=Math.min(max,Math.max(min,val));el.value=String(val);const pct=max===min?0:((val-min)/(max-min))*100;el.style.setProperty('--range-pct',`${pct}%`);const stage=el.closest('.range-stage');if(stage){stage.style.setProperty('--range-pct',`${pct}%`);let float=stage.querySelector('.range-float');if(!float){float=document.createElement('span');float.className='range-float';stage.appendChild(float)}float.textContent=formatRangeValue(id,val)}if(target){const next=formatRangeValue(id,val);if(target.textContent!==next){target.textContent=next;target.classList.remove('bump');void target.offsetWidth;target.classList.add('bump');setTimeout(()=>target.classList.remove('bump'),180)}}}
function bindRange(id){const el=document.getElementById(id);if(!el)return;const sync=()=>refreshRangeUI(id);el.addEventListener('input',sync);el.addEventListener('change',sync);el.addEventListener('wheel',e=>{if(document.activeElement!==el)return;e.preventDefault();const step=Number(el.step||1);const dir=e.deltaY<0?1:-1;el.value=String(Math.min(Number(el.max),Math.max(Number(el.min),Number(el.value)+dir*step)));sync()},{passive:false});sync()}
function syncRange(id){const el=document.getElementById(id);if(el){el.dispatchEvent(new Event('input',{bubbles:true}));refreshRangeUI(id)}}
const gpMaps=[];
function currentTheme(){return document.documentElement.dataset.theme==='light'?'light':'dark'}
function currentMapStyle(){return localStorage.getItem('gridpoint-map-style')||'auto'}
const GP_CARTO_ATTR='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
const GP_ESRI_ATTR='Tiles © Esri — Sources: Esri, TomTom, Garmin, USGS, FAO, NOAA, and the GIS User Community';
const GP_MAP_STYLES={
  auto:{light:'light',dark:'dark'},
  light:{label:'Light',url:'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',sub:'abcd',cls:'gp-carto',attr:GP_CARTO_ATTR,maxZoom:20},
  dark:{label:'Dark',url:'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',sub:'abcd',cls:'gp-carto',attr:GP_CARTO_ATTR,maxZoom:20},
  streets:{label:'Roads',url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',cls:'gp-arcgis',attr:GP_ESRI_ATTR,maxZoom:19},
  satellite:{label:'Satellite',url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',cls:'gp-arcgis gp-satellite',attr:GP_ESRI_ATTR,maxZoom:19}
};
const mapAttribution=GP_ESRI_ATTR;
function resolvedMapStyle(){
  const saved=currentMapStyle();
  if(saved==='auto')return GP_MAP_STYLES.auto[currentTheme()]||'dark';
  return ['light','dark','streets','satellite'].includes(saved)?saved:'dark';
}
function addMapBasemap(map){
  const style=resolvedMapStyle();
  const cfg=GP_MAP_STYLES[style];
  const opts={maxZoom:cfg.maxZoom||19,tileSize:256,zoomOffset:0,attribution:cfg.attr||mapAttribution,className:cfg.cls||''};
  if(cfg.sub)opts.subdomains=cfg.sub;
  const layer=L.tileLayer(cfg.url,opts);
  layer.addTo(map);
  map._gpBaseLayer=layer;
  map._gpBaseMode='arcgis-raster';
  map._gpBaseStyle=style;
}
function mapStyleUrl(){return GP_MAP_STYLES[resolvedMapStyle()]?.url||GP_MAP_STYLES.dark.url}
function updateMapStyleButtons(){
  const style=currentMapStyle();
  document.querySelectorAll('[data-map-style]').forEach(btn=>btn.classList.toggle('active',btn.dataset.mapStyle===style));
}
function setMapStyle(style){
  const next=['auto','light','dark','streets','satellite'].includes(style)?style:'auto';
  localStorage.setItem('gridpoint-map-style',next);
  updateMapStyleButtons();
  refreshMapTiles(true);
}
function mapFactory(id,lat=12.9716,lon=77.5946,zoom=11){
  const map=L.map(id,{zoomControl:false,preferCanvas:true,fadeAnimation:true,zoomAnimation:true}).setView([lat,lon],zoom);
  L.control.zoom({position:'bottomright'}).addTo(map);
  addMapBasemap(map);
  gpMaps.push(map);
  map.whenReady(()=>setTimeout(()=>map.invalidateSize({pan:false}),80));
  return map;
}
function refreshMapTiles(force=false){
  gpMaps.forEach(map=>{
    if(!map)return;
    const nextStyle=resolvedMapStyle();
    if(!force && map._gpBaseStyle===nextStyle)return;
    const center=map.getCenter(),zoom=map.getZoom(),old=map._gpBaseLayer;
    if(old){try{map.removeLayer(old)}catch(e){}}
    addMapBasemap(map);
    map.setView(center,zoom,{animate:false});
    setTimeout(()=>map.invalidateSize({pan:false}),90);
  });
}
function applyTheme(theme){const next=theme==='light'?'light':'dark';const root=document.documentElement;root.classList.add('theme-surface-transition');root.dataset.theme=next;localStorage.setItem('gridpoint-theme',next);const meta=document.querySelector('meta[name=theme-color]');if(meta)meta.setAttribute('content',next==='light'?'#f4f8fc':'#06101e');const icon=document.getElementById('themeIcon');const label=document.getElementById('themeLabel');if(icon)icon.textContent=next==='light'?'☀':'☾';if(label)label.textContent=next==='light'?'Light':'Dark';requestAnimationFrame(()=>{refreshMapTiles(false);document.querySelectorAll('.range').forEach(el=>syncRange(el.id));if(typeof renderChart==='function'&&typeof optState!=='undefined'&&optState.chartData)renderChart(optState.chartData);document.querySelectorAll('.map').forEach(el=>{const id=el.id;const maps=gpMaps.filter(m=>m.getContainer()===el);maps.forEach(m=>m.invalidateSize())});window.dispatchEvent(new CustomEvent('gridpoint:themechange',{detail:{theme:next}}));});setTimeout(()=>root.classList.remove('theme-surface-transition'),520)}
function initThemeToggle(){const btn=document.getElementById('themeToggle');if(!btn)return;const theme=currentTheme();const icon=document.getElementById('themeIcon');const label=document.getElementById('themeLabel');if(icon)icon.textContent=theme==='light'?'☀':'☾';if(label)label.textContent=theme==='light'?'Light':'Dark';btn.addEventListener('click',()=>applyTheme(currentTheme()==='light'?'dark':'light'))}

initThemeToggle();
updateMapStyleButtons();
document.addEventListener('click',e=>{const btn=e.target.closest?.('[data-map-style]');if(btn)setMapStyle(btn.dataset.mapStyle)});
let gpLastScrollY=window.scrollY||0;let gpScrollDirection='down';let gpScrollRaf=0;window.addEventListener('scroll',()=>{if(gpScrollRaf)return;gpScrollRaf=requestAnimationFrame(()=>{const y=window.scrollY||0;gpScrollDirection=y>=gpLastScrollY?'down':'up';gpLastScrollY=y;gpScrollRaf=0})},{passive:true});
function initScrollAnimations(){
  if(window.gpRevealObserver){window.gpRevealObserver.disconnect();window.gpRevealObserver=null;}
  const page=document.body?.dataset?.page||'';
  const selectors={
    home:'.hero,.section-title,.grid4,.demo-wrap',
    optimizer:'.page-head,.optimizer-layout > .controls,.workspace > .metrics,.workspace > .decision-banner,.workspace > .top-two-section,.dashboard-grid > .card,.split-grid > .card,.workspace > .card',
    how:'.page-head,.page-grid > .card,.formula-panel,.how-note',
    locations:'[data-network-reveal]'
  };
  const selector=selectors[page];
  if(!selector)return;
  const targets=[...document.querySelectorAll(selector)];
  if(!targets.length)return;
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){targets.forEach(el=>el.classList.add('is-visible'));return}
  targets.forEach((el,i)=>{
    el.classList.remove('reveal','is-visible');
    el.style.removeProperty('--reveal-y');
    el.style.setProperty('--reveal-delay',`${Math.min(i*55,260)}ms`);
    el.dataset.revealIndex=String(i);
    const rect=el.getBoundingClientRect();
    el.style.setProperty('--reveal-y',rect.top < window.innerHeight * .5 ? '-24px' : '24px');
    el.classList.add('reveal');
  });
  const setOrigin=(el)=>{
    const rect=el.getBoundingClientRect();
    el.style.setProperty('--reveal-y',rect.top < window.innerHeight * .5 ? '-24px' : '24px');
  };
  window.gpRevealObserver=new IntersectionObserver(entries=>{
    entries.forEach(entry=>{
      const el=entry.target;
      if(entry.isIntersecting){
        setOrigin(el);
        el.classList.remove('is-visible');
        requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('is-visible')));
      }else if(entry.intersectionRatio===0){
        setOrigin(el);
        el.classList.remove('is-visible');
      }
    });
  },{threshold:0.12,rootMargin:'-8% 0px -8% 0px'});
  targets.forEach(el=>window.gpRevealObserver.observe(el));
  requestAnimationFrame(()=>targets.forEach(el=>{const rect=el.getBoundingClientRect();if(rect.top<window.innerHeight*.92&&rect.bottom>window.innerHeight*.08){setOrigin(el);requestAnimationFrame(()=>el.classList.add('is-visible'));}}));
}
function initPageLinks(){document.querySelectorAll('a[href^="/"]:not([target])').forEach(a=>a.addEventListener('click',event=>{if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;const href=a.getAttribute('href');if(!href||href.startsWith('/api/')||href==='#')return;if(!document.startViewTransition){event.preventDefault();document.body.classList.add('page-leaving');setTimeout(()=>{window.location.href=href},220)}}))}
history.scrollRestoration='manual';
if(!window.__gpInitialised){window.__gpInitialised=true;window.scrollTo(0,0);}
initScrollAnimations();
initPageLinks();
requestAnimationFrame(()=>{if(window.scrollY!==0)window.scrollTo({top:0,left:0,behavior:'auto'});});
window.addEventListener('pageshow',event=>{if(event.persisted){window.scrollTo({top:0,left:0,behavior:'auto'});requestAnimationFrame(()=>{initScrollAnimations();});}});
async function fetchJSON(url,opts={}){const r=await fetch(url,{headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts});const data=await r.json().catch(()=>({}));if(!r.ok||data.ok===false)throw new Error(data.error||'Request failed');return data}

{% if active == 'home' %}
const homeMap=mapFactory('homeMap',12.965,77.63,11);
const homeDemand=[[12.9784,77.6408,'Indiranagar',420],[12.9352,77.6245,'Koramangala',510],[12.9116,77.6389,'HSR Layout',380],[12.9698,77.7499,'Whitefield',620],[12.9591,77.6974,'Marathahalli',500],[12.9304,77.6784,'Bellandur',470],[12.8458,77.6602,'Electronic City',390],[12.9984,77.6177,'Frazer Town',235],[13.0358,77.5970,'Hebbal',280],[13.1007,77.5963,'Yelahanka',240],[12.9910,77.5532,'Rajajinagar',300],[12.9250,77.5938,'Jayanagar',330],[13.0035,77.5703,'Malleshwaram',260],[12.9166,77.6101,'BTM Layout',350],[12.9063,77.5857,'JP Nagar',290],[12.9719,77.5270,'Vijayanagar',270],[13.0290,77.6400,'Kalyan Nagar',310],[12.9691,77.7157,'Kundalahalli',360]];
const homeHubs=[[12.9352,77.6245,'Hub A · South'],[12.9698,77.7499,'Hub B · East'],[13.0035,77.5703,'Hub C · North-West']];
const homeBounds=[];
function haversineKmClient(a,b,c,d){const R=6371;const p1=a*Math.PI/180,p2=c*Math.PI/180,dp=(c-a)*Math.PI/180,dl=(d-b)*Math.PI/180;const x=Math.sin(dp/2)**2+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;return 2*R*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))}
homeDemand.forEach(p=>{const r=Math.max(4,Math.min(10,3.5+Math.sqrt(p[3])/7));const m=L.circleMarker([p[0],p[1]],{radius:r,color:'#4ea1ff',fillColor:'#67e8f9',fillOpacity:.42,weight:1}).addTo(homeMap);m.bindTooltip(`${p[2]} · ${p[3].toLocaleString('en-IN')} orders/day`);homeBounds.push([p[0],p[1]])});
const homeLines=[];
homeHubs.forEach(p=>{L.circle([p[0],p[1]],{radius:6200,color:'#67e8f9',weight:1,opacity:.20,fillColor:'#67e8f9',fillOpacity:.045}).addTo(homeMap);const m=L.circleMarker([p[0],p[1]],{radius:8,color:'#06101e',fillColor:'#67e8f9',fillOpacity:.96,weight:3}).addTo(homeMap);m.bindPopup(`<b>${p[2]}</b><br>Illustrative warehouse site<br>GRIDPOINT candidate network`);homeBounds.push([p[0],p[1]])});
homeDemand.forEach(p=>{let nearest=homeHubs[0],best=Infinity;homeHubs.forEach(h=>{const d=haversineKmClient(p[0],p[1],h[0],h[1]);if(d<best){best=d;nearest=h}});homeLines.push(L.polyline([[p[0],p[1]],[nearest[0],nearest[1]]],{color:'#67e8f9',weight:1,opacity:.13,dashArray:'3 8',lineCap:'round'}).addTo(homeMap))});
const cityPulse=L.circleMarker([12.9716,77.5946],{radius:9,color:'#a78bfa',fillColor:'#a78bfa',fillOpacity:.10,weight:2}).addTo(homeMap).bindPopup('<b>GRIDPOINT planning point</b><br>Demand → candidates → optimized network');homeBounds.push([12.9716,77.5946]);homeMap.fitBounds(homeBounds,{padding:[18,18],maxZoom:11});
let pulseOn=false;setInterval(()=>{pulseOn=!pulseOn;homeLines.forEach(line=>line.setStyle({opacity:pulseOn?.20:.09,dashOffset:pulseOn?'12':'0'}));cityPulse.setStyle({radius:pulseOn?12:9,fillOpacity:pulseOn?.16:.08})},1500);
const demoStages=[{step:'Demand',value:'25',text:'neighborhoods loaded',result:'CSV ready',rtext:'valid locations detected',hint:'1 · Load demand data',pct:22},{step:'Network',value:'8',text:'candidate sites',result:'K = 3',rtext:'network sizes tested',hint:'2 · Test candidate sites',pct:48},{step:'Optimize',value:'3',text:'warehouses selected',result:'−18%',rtext:'modeled delivery cost',hint:'3 · Assign demand',pct:78},{step:'Result',value:'96%',text:'demand covered',result:'₹7.1L',rtext:'modeled annual cost',hint:'4 · Compare baseline vs optimized',pct:100}];let demoIndex=0,demoTimer=null;function renderDemoStage(){const s=demoStages[demoIndex];const progress=document.getElementById('demoProgress');const a=document.getElementById('demoStepLabel');const b=document.getElementById('demoStageValue');const c=document.getElementById('demoStageText');const d=document.getElementById('demoResultValue');const e=document.getElementById('demoResultText');const f=document.getElementById('demoHint');if(progress)progress.style.width=`${s.pct}%`;if(a)a.textContent=s.step;if(b)b.textContent=s.value;if(c)c.textContent=s.text;if(d)d.textContent=s.result;if(e)e.textContent=s.rtext;if(f)f.textContent=s.hint}function playDemo(){if(demoTimer)clearInterval(demoTimer);demoIndex=0;renderDemoStage();demoTimer=setInterval(()=>{demoIndex+=1;if(demoIndex>=demoStages.length){clearInterval(demoTimer);demoTimer=null;return}renderDemoStage()},1900)}document.getElementById('playDemo')?.addEventListener('click',playDemo);renderDemoStage();
{% endif %}

{% if active == 'optimizer' %}
const optState={location:null,map:null,chart:null,chartData:null,warehouseLayer:[],neighborhoodLayer:[],lines:[],catchmentLayer:[],routeLayer:null,uploadRows:null,lastResult:null,manualWarehouses:[],addingWarehouse:false};
function loadManualWarehouses(){try{const rows=JSON.parse(localStorage.getItem('gridpoint-manual-warehouses')||'[]');optState.manualWarehouses=Array.isArray(rows)?rows.filter(w=>Number.isFinite(Number(w.lat))&&Number.isFinite(Number(w.lon))):[]}catch(e){optState.manualWarehouses=[]}renderManualWarehouses()}
function saveManualWarehouses(){localStorage.setItem('gridpoint-manual-warehouses',JSON.stringify(optState.manualWarehouses));renderManualWarehouses()}
function renderManualWarehouses(){const el=document.getElementById('manualWarehouseList');if(!el)return;el.innerHTML=optState.manualWarehouses.length?optState.manualWarehouses.map(w=>`<div class="warehouse-add-item"><span>● ${esc(w.name)} · ${num(w.lat).toFixed(5)}, ${num(w.lon).toFixed(5)}</span><button type="button" data-remove-manual="${esc(w.id)}">Remove</button></div>`).join(''):'<div class="field-help">No custom warehouses yet.</div>';el.querySelectorAll('[data-remove-manual]').forEach(b=>b.addEventListener('click',()=>{optState.manualWarehouses=optState.manualWarehouses.filter(w=>w.id!==b.dataset.removeManual);saveManualWarehouses();drawManualWarehouseMarkers()}));drawManualWarehouseMarkers()}
function drawManualWarehouseMarkers(){if(!optState.map)return;optState.manualWarehouses.forEach(w=>{});if(optState.manualWarehouseLayer)clearMapLayer(optState.manualWarehouseLayer);optState.manualWarehouseLayer=[];optState.manualWarehouses.forEach(w=>{const m=L.marker([num(w.lat),num(w.lon)],{title:w.name}).addTo(optState.map).bindPopup(`<b>${esc(w.name)}</b><br>Custom warehouse · will be used by the optimizer`);optState.manualWarehouseLayer.push(m)});}
function toggleAddWarehouseMode(){optState.addingWarehouse=!optState.addingWarehouse;const btn=document.getElementById('addWarehouseMode');if(btn)btn.textContent=optState.addingWarehouse?'Click map to place…':'+ Add warehouse';if(optState.map)optState.map.getContainer().classList.toggle('map-add-mode',optState.addingWarehouse);if(optState.addingWarehouse)toast('Click the map where you want the new warehouse.')} 
function handleWarehouseMapClick(e){if(!optState.addingWarehouse)return;const name=(window.prompt('Warehouse name','New Warehouse')||'').trim();if(!name){toast('Warehouse not added. Enter a name.');return}const w={id:`MANUAL-${Date.now()}`,name,lat:Number(e.latlng.lat.toFixed(6)),lon:Number(e.latlng.lng.toFixed(6)),source:'manual',required:true};optState.manualWarehouses.push(w);saveManualWarehouses();optState.addingWarehouse=false;const btn=document.getElementById('addWarehouseMode');if(btn)btn.textContent='+ Add warehouse';optState.map?.getContainer().classList.remove('map-add-mode');toast(`${name} added. It will be used in the next optimization.`)}
function rowToCsv(rows){return ['name,latitude,longitude,daily_orders',...(rows||[]).map(r=>[r.name,r.lat,r.lon,r.orders].map(v=>String(v??'').replaceAll('"','""')).join(','))].join('\n')}
function syncOptimizerDataLimit(){const count=optState.uploadRows?.length||0;const e=document.getElementById('maxWarehouses');if(!e)return;const max=Math.min(100,Math.max(1,count||100));e.max=String(max);if(Number(e.value)>max)e.value=String(max);syncRange('maxWarehouses');const scale=e.closest('.range-stage')?.querySelectorAll('.range-scale span');if(scale?.length===5){scale[0].textContent='1';scale[1].textContent=Math.max(1,Math.round(max*.25));scale[2].textContent=Math.max(1,Math.round(max*.5));scale[3].textContent=Math.max(1,Math.round(max*.75));scale[4].textContent=max}updateOptimizerSourceSummary()}
async function loadDefaultCityDataset(city){
  try{
    const d=await fetchJSON(`/api/locations?city=${encodeURIComponent(city)}`);
    if(!Array.isArray(d.locations)||!d.locations.length)return;
    optState.uploadRows=d.locations;
    const fs=document.getElementById('fileName');if(fs&&!localStorage.getItem('gridpoint-demand-filename'))fs.textContent=`${d.locations.length} demo demand locations loaded`;
    updateOptimizerSourceSummary();syncOptimizerDataLimit();applyBalancedDefaults(d.locations);showDemandPreview(d.locations,[cityData[city]?.lat||12.9716,cityData[city]?.lon||77.5946]);
  }catch(e){toast('Demo demand could not be loaded. The optimizer will use the market baseline.')}
}
function updateOptimizerSourceSummary(){const rows=optState.uploadRows||[];const title=document.getElementById('optimizerSourceTitle');const meta=document.getElementById('optimizerSourceMeta');const count=document.getElementById('optimizerSourceCount');const orders=document.getElementById('optimizerSourceOrders');const status=document.getElementById('optimizerSourceStatus');const label=localStorage.getItem('gridpoint-demand-label')||'Selected market demo';const total=rows.reduce((s,r)=>s+num(r.orders),0);if(title)title.textContent=label;if(meta)meta.textContent=rows.length?`${rows.length} demand locations are loaded and ready.`:'Using the selected market demand profile.';if(count)count.textContent=rows.length?rows.length.toLocaleString('en-IN'):'Market demo';if(orders)orders.textContent=rows.length?total.toLocaleString('en-IN'):'—';if(status)status.textContent=rows.length?'Loaded':'Ready'}
function applyBalancedDefaults(rows){const count=Math.max(1,rows?.length||25);const total=Math.max(1,(rows||[]).reduce((s,r)=>s+num(r.orders),0));const targetK=Math.min(Math.min(count,100),Math.max(2,Math.min(4,Math.ceil(Math.sqrt(count)))));const cap=Math.min(50000,Math.max(500,Math.ceil((total/Math.max(2,targetK))*1.15/100)*100));const maxEl=document.getElementById('maxWarehouses');const capEl=document.getElementById('capacity');if(maxEl)maxEl.value=Math.min(targetK,100);if(capEl)capEl.value=cap;const radiusEl=document.getElementById('radius');if(radiusEl)radiusEl.value=50;const growthEl=document.getElementById('growth');if(growthEl)growthEl.value=10;const slaEl=document.getElementById('slaMinutes');if(slaEl)slaEl.value=45;const traffic=document.getElementById('traffic');if(traffic)traffic.value='medium';const vehicle=document.getElementById('vehicle');if(vehicle)vehicle.value='car';const opening=document.getElementById('openingCost');if(opening)opening.value=4000000;const fuel=document.getElementById('fuelPrice');if(fuel)fuel.value=100;const mode=document.getElementById('selectionMode');if(mode)mode.value='auto';syncSelectionMode();['maxWarehouses','capacity','radius','growth','slaMinutes'].forEach(syncRange);syncOptimizerDataLimit();}
function showDemandPreview(rows,focus){if(!optState.map)return;clearMapLayer(optState.neighborhoodLayer);const points=rows||[];points.forEach(n=>{const radius=Math.max(4,Math.min(13,3.5+Math.sqrt(Math.max(0,num(n.orders)))/5));const marker=L.circleMarker([num(n.lat),num(n.lon)],{radius,color:'#4ea1ff',fillColor:'#67e8f9',fillOpacity:.42,weight:1}).addTo(optState.map);marker.bindTooltip(`${esc(n.name)} · ${num(n.orders).toLocaleString('en-IN')} orders/day`);optState.neighborhoodLayer.push(marker)});if(focus)optState.map.setView(focus,11,{animate:false});setTimeout(()=>optState.map.invalidateSize({pan:false}),60)}
const savedRows=JSON.parse(localStorage.getItem('gridpoint-demand-rows')||'null');if(Array.isArray(savedRows)&&savedRows.length){optState.uploadRows=savedRows;applyBalancedDefaults(savedRows);const fs=document.getElementById('fileName');const savedName=localStorage.getItem('gridpoint-demand-filename')||localStorage.getItem('gridpoint-demand-label')||'';if(fs)fs.textContent=savedName?`✓ ${savedName}`:`${savedRows.length} saved demand locations`;const us=document.getElementById('uploadSummary');if(us){us.style.display='block';us.innerHTML=`<div class="import-success"><span class="success-icon">✓</span><div><strong>Demand dataset ready</strong><span>${esc(savedName||`${savedRows.length} demand locations`)} · ${savedRows.length} valid locations loaded.</span></div></div>`}}updateOptimizerSourceSummary();
const optimizerTourSteps=[
  {target:'city',title:'1 · Choose your market',text:'Start with a city, your detected location, or a planning point. GRIDPOINT uses the selected demand profile as the starting network.',side:'right'},
  {target:'selectionMode',title:'2 · Let GRIDPOINT choose K',text:'Auto is the recommended starting mode. Choose Exact only when the business has already decided how many warehouses it wants.',side:'right'},
  {target:'capacity',title:'3 · Set maximum capacity',text:'This is the maximum daily order volume one warehouse can handle. GRIDPOINT uses it as a hard planning constraint.',side:'right'},
  {target:'radius',title:'4 · Set service reach',text:'Keep the maximum service radius realistic for your delivery network. The recommended starting point is 50 km.',side:'right'},
  {target:'growth',title:'5 · Plan for tomorrow',text:'Demand growth and the delivery target let you test a network that is ready for future volume, not only today’s demand.',side:'right'},
  {target:'optimizeBtnTop',title:'6 · Run GRIDPOINT',text:'Run the model once the settings are ready. The result highlights the recommended network and the top two selected sites.',side:'bottom'}
];
let optimizerTourIndex=0;
function positionOptimizerTour(){
  const tour=document.getElementById('optimizerTour'),spot=document.getElementById('optimizerTourSpotlight'),card=document.getElementById('optimizerTourCard');
  const step=optimizerTourSteps[optimizerTourIndex]; const target=document.getElementById(step.target); if(!tour||!spot||!card||!target)return;
  const r=target.getBoundingClientRect(),pad=8;
  spot.style.top=`${Math.max(10,r.top-pad)}px`;spot.style.left=`${Math.max(10,r.left-pad)}px`;spot.style.width=`${r.width+pad*2}px`;spot.style.height=`${r.height+pad*2}px`;
  let left=r.right+16,top=r.top,side='right';
  if(step.side==='top'){left=r.left;top=r.top-card.offsetHeight-16;side='top'}
  if(left+card.offsetWidth>window.innerWidth-14){left=Math.max(14,r.left-card.offsetWidth-16);side='left'}
  if(top<14){top=Math.min(window.innerHeight-card.offsetHeight-14,r.bottom+16);side='bottom'}
  if(top+card.offsetHeight>window.innerHeight-14){top=Math.max(14,window.innerHeight-card.offsetHeight-14)}
  card.style.left=`${left}px`;card.style.top=`${top}px`;card.dataset.side=side;
  const kicker=document.getElementById('optimizerTourKicker'),title=document.getElementById('optimizerTourTitle'),text=document.getElementById('optimizerTourText');
  const dots=[...document.querySelectorAll('.optimizer-tour-progress i')];
  if(kicker)kicker.textContent=`GUIDED TOUR · ${optimizerTourIndex+1} OF ${optimizerTourSteps.length}`;
  if(title)title.textContent=step.title;if(text)text.textContent=step.text;dots.forEach((d,i)=>d.classList.toggle('is-active',i===optimizerTourIndex));
  const back=document.getElementById('optimizerTourBack'),next=document.getElementById('optimizerTourNext');
  if(back)back.style.visibility=optimizerTourIndex===0?'hidden':'visible';if(next)next.textContent=optimizerTourIndex===optimizerTourSteps.length-1?'Finish':'Next';
}
const OPTIMIZER_TOUR_SKIP_KEY='gridpoint-optimizer-tour-v9-skip';
const OPTIMIZER_TOUR_SEEN_KEY='gridpoint-optimizer-tour-v9-seen';
function closeOptimizerTour(markSkipped=false){const el=document.getElementById('optimizerTour');if(!el)return;el.classList.remove('is-open');el.setAttribute('aria-hidden','true');document.body.classList.remove('tour-active');if(markSkipped)localStorage.setItem(OPTIMIZER_TOUR_SKIP_KEY,'1')}
function finishOptimizerTour(){localStorage.setItem(OPTIMIZER_TOUR_SEEN_KEY,'1');closeOptimizerTour(false)}
function openOptimizerTour(force=false){
  const el=document.getElementById('optimizerTour');if(!el)return;
  if(!force&&(localStorage.getItem(OPTIMIZER_TOUR_SKIP_KEY)==='1'||localStorage.getItem(OPTIMIZER_TOUR_SEEN_KEY)==='1'))return;
  optimizerTourIndex=0;el.classList.add('is-open');el.setAttribute('aria-hidden','false');document.body.classList.add('tour-active');
  const target=document.getElementById(optimizerTourSteps[0].target);target?.scrollIntoView({behavior:'smooth',block:'center'});
  setTimeout(()=>positionOptimizerTour(),360);
}
function advanceOptimizerTour(delta){
  const nextIndex=Math.min(optimizerTourSteps.length-1,Math.max(0,optimizerTourIndex+delta));
  if(nextIndex===optimizerTourIndex){if(delta>0)finishOptimizerTour();return}
  optimizerTourIndex=nextIndex;const target=document.getElementById(optimizerTourSteps[optimizerTourIndex].target);target?.scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>positionOptimizerTour(),420);
}
document.getElementById('optimizerTourNext')?.addEventListener('click',()=>advanceOptimizerTour(1));
document.getElementById('optimizerTourBack')?.addEventListener('click',()=>advanceOptimizerTour(-1));
document.getElementById('optimizerTourClose')?.addEventListener('click',()=>closeOptimizerTour(false));
document.getElementById('optimizerTourSkip')?.addEventListener('click',()=>closeOptimizerTour(true));
document.querySelector('.optimizer-tour-backdrop')?.addEventListener('click',()=>closeOptimizerTour(false));
document.getElementById('optimizerTourLaunch')?.addEventListener('click',()=>openOptimizerTour(true));
window.addEventListener('resize',()=>{if(document.getElementById('optimizerTour')?.classList.contains('is-open'))positionOptimizerTour()});
window.addEventListener('scroll',()=>{if(document.getElementById('optimizerTour')?.classList.contains('is-open'))positionOptimizerTour()},{passive:true});
const cityData={{ cities|tojson }};
const initialCity=new URLSearchParams(location.search).get('city');
if(initialCity&&cityData[initialCity])document.getElementById('city').value=initialCity;
setTimeout(async()=>{if(!optState.uploadRows?.length)await loadDefaultCityDataset(document.getElementById('city')?.value||'Bengaluru');openOptimizerTour(false)},650);
document.getElementById('city')?.addEventListener('change',()=>loadDefaultCityDataset(document.getElementById('city').value));
function setLocationStatus(text,mode=''){const el=document.getElementById('locationStatus');if(el){el.textContent=text;el.className='location-status '+mode}}
function clearMapLayer(list){list.forEach(x=>{try{optState.map.removeLayer(x)}catch(e){}});list.length=0}
function applyDetectedCity(city,label=''){
  const select=document.getElementById('city');
  const badge=document.getElementById('locationBadge');
  if(city&&typeof cityData!=='undefined'&&cityData[city]&&select){select.value=city;}
  if(badge){badge.textContent=city?`📍 ${city}`:'City mode';}
  if(label){setLocationStatus(label+(city?` · ${city}`:''),'good')}
}
async function loadNearby(lat,lon,city=''){
  optState.location={latitude:lat,longitude:lon};
  try{
    const d=await fetchJSON('/api/nearby',{method:'POST',body:JSON.stringify({latitude:lat,longitude:lon,city})});
    renderSuggestions(d.suggestions);
    applyDetectedCity(d.city||city,'Planning location');
    if(optState.map){clearMapLayer(optState.neighborhoodLayer);optState.map.setView([lat,lon],12);const m=L.circleMarker([lat,lon],{radius:10,color:'#67e8f9',fillColor:'#67e8f9',fillOpacity:.22,weight:2}).addTo(optState.map).bindPopup(`<b>Planning location</b><br>${esc(d.city||city||'India')}`);optState.neighborhoodLayer.push(m)}
    return d;
  }catch(e){toast(e.message);return null}
}
async function searchLocation(){
  const q=document.getElementById('locationQuery')?.value.trim();
  if(!q){toast('Enter a place or address in India.');return}
  try{const d=await fetchJSON(`/api/geocode?q=${encodeURIComponent(q)}`);const r=d.result;const nearby=await loadNearby(r.latitude,r.longitude);setLocationStatus(`Location selected: ${r.display_name}`+(nearby?.city?` · ${nearby.city}`:''),'good');if(optState.map)optState.map.setView([r.latitude,r.longitude],13)}catch(e){toast(e.message)}
}
async function showSuggestionRoute(lat,lon,name){
  if(!optState.location){toast('Set your current or searched location first.');return}
  try{const d=await fetchJSON(`/api/route?lat1=${optState.location.latitude}&lon1=${optState.location.longitude}&lat2=${lat}&lon2=${lon}`);if(optState.routeLayer)optState.map.removeLayer(optState.routeLayer);optState.routeLayer=L.geoJSON(d.route.geometry,{style:{color:'#67e8f9',weight:5,opacity:.86}}).addTo(optState.map);optState.map.fitBounds(optState.routeLayer.getBounds(),{padding:[30,30]});toast(`${name}: ${num(d.route.distance_km).toFixed(1)} km · ${num(d.route.duration_minutes).toFixed(0)} min`)}catch(e){toast(e.message)}
}
/* ================================================================
   GRIDPOINT map visualizer
   Every warehouse cluster is given its own colour from the palette;
   the map then renders colour-matched catchment rings, cluster hulls,
   hub pins and demand lines out to each assigned neighborhood.
   ================================================================ */
const GP_CLUSTER_COLORS=['#06b6d4','#3b82f6','#8b5cf6','#10b981','#f59e0b','#f43f5e','#ec4899','#14b8a6','#a855f7','#22d3ee','#84cc16','#fb923c','#e879f9','#34d399','#fbbf24'];
function gpClusterColor(i){return GP_CLUSTER_COLORS[((i%GP_CLUSTER_COLORS.length)+GP_CLUSTER_COLORS.length)%GP_CLUSTER_COLORS.length]}
function gpConvexHull(pts){
  if(pts.length<3)return pts;
  const cross=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);
  const sorted=[...pts].sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const lower=[],upper=[];
  for(const p of sorted){
    while(lower.length>=2&&cross(lower[lower.length-2],lower[lower.length-1],p)<=0)lower.pop();
    lower.push(p);
  }
  for(let k=sorted.length-1;k>=0;k--){
    const p=sorted[k];
    while(upper.length>=2&&cross(upper[upper.length-2],upper[upper.length-1],p)<=0)upper.pop();
    upper.push(p);
  }
  upper.pop();lower.pop();
  return lower.concat(upper);
}
function gpWarehousePin(color,rank,top){
  return L.divIcon({
    className:'',
    html:'<div class="warehouse-pin'+(top?' is-top':'')+'" style="--wcolor:'+color+'">'
      +'<div class="wp-ring"></div><div class="wp-ring wp-ring-2"></div>'
      +'<div class="wp-body"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div>'
      +'<div class="wp-label">W'+rank+'</div></div>',
    iconSize:[44,60],
    iconAnchor:[22,52]
  });
}
function gpKey(lat,lon){return num(lat).toFixed(5)+'|'+num(lon).toFixed(5)}
function gpMapTooltip(rows,title,color){
  return '<div class="map-tooltip"><div class="mtt-name"'+(color?' style="color:'+color+'"':'')+'>'+title+'</div>'
    +rows.map(r=>'<div class="mtt-row"><span>'+r[0]+'</span><b>'+r[1]+'</b></div>').join('')+'</div>';
}
function gpLayers(){
  optState.territoryLayer=optState.territoryLayer||[];
  optState.labelLayer=optState.labelLayer||[];
}
function gpShowLabels(){return localStorage.getItem('gridpoint-map-labels')==='1'}
function drawMap(data){
  gpLayers();
  const focus=data.location?.latitude!=null?[data.location.latitude,data.location.longitude]:[cityData[data.city]?.lat||12.9716,cityData[data.city]?.lon||77.5946];
  if(!optState.map)optState.map=mapFactory('optMap',focus[0],focus[1],11);
  bindPlanningMapClick();
  clearMapLayer(optState.warehouseLayer);clearMapLayer(optState.neighborhoodLayer);clearMapLayer(optState.lines);
  clearMapLayer(optState.catchmentLayer);clearMapLayer(optState.territoryLayer);clearMapLayer(optState.labelLayer);
  drawManualWarehouseMarkers();

  const warehouses=data.warehouses||[];
  const assignments=data.assignments||[];
  /* every warehouse gets its own colour, reused by every layer below */
  const colorById={},rankById={},indexById={};
  warehouses.forEach((w,i)=>{colorById[w.id]=gpClusterColor(i);rankById[w.id]=i+1;indexById[w.id]=i});
  const clusterOf={},feasibleOf={};
  assignments.forEach(a=>{
    const k=gpKey(a.neighborhood_lat,a.neighborhood_lon);
    clusterOf[k]=a.warehouse_id;
    feasibleOf[k]=!!a.feasible;
  });
  const topIds=new Set([...warehouses].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders)).slice(0,2).map(w=>w.id));
  const radiusM=num(data.summary?.radius_km,25)*1000;
  const labelsOn=gpShowLabels();

  /* ---- 1. cluster territories (convex hull of each cluster) ---- */
  warehouses.forEach(w=>{
    const color=colorById[w.id];
    const members=(data.neighborhoods||[]).filter(n=>clusterOf[gpKey(n.lat,n.lon)]===w.id).map(n=>[num(n.lat),num(n.lon)]);
    if(members.length<3)return;
    const hull=gpConvexHull(members);
    if(hull.length<3)return;
    const poly=L.polygon(hull,{color,fillColor:color,fillOpacity:.07,weight:1.5,opacity:.35,dashArray:'5 4',interactive:false}).addTo(optState.map);
    optState.territoryLayer.push(poly);
  });

  /* ---- 2. colour-coded catchment circles ---- */
  warehouses.forEach(w=>{
    const color=colorById[w.id];
    const ring=L.circle([num(w.lat),num(w.lon)],{radius:radiusM,color,weight:1.2,opacity:.3,dashArray:'6 6',fillColor:color,fillOpacity:.045,interactive:false}).addTo(optState.map);
    optState.catchmentLayer.push(ring);
  });

  /* ---- 3. demand lines, coloured by the serving warehouse ---- */
  const maxOrders=Math.max(1,...(data.neighborhoods||[]).map(n=>num(n.orders)));
  assignments.slice(0,400).forEach(a=>{
    const color=colorById[a.warehouse_id]||'#94a3b8';
    const line=L.polyline([[num(a.neighborhood_lat),num(a.neighborhood_lon)],[num(a.warehouse_lat),num(a.warehouse_lon)]],{
      color,
      weight:a.feasible?1.4+1.8*(num(a.orders)/maxOrders):2.4,
      opacity:a.feasible?.5:.7,
      dashArray:a.feasible?'6 5':'4 4',
      className:'assignment-line',
      interactive:false
    }).addTo(optState.map);
    optState.lines.push(line);
  });

  /* ---- 4. neighborhood markers in their cluster colour ---- */
  (data.neighborhoods||[]).forEach(n=>{
    const k=gpKey(n.lat,n.lon);
    const wid=clusterOf[k];
    const color=colorById[wid]||'#94a3b8';
    const oor=wid!=null&&feasibleOf[k]===false;
    const radius=6+(num(n.orders)/maxOrders)*12;
    const m=L.circleMarker([num(n.lat),num(n.lon)],{
      radius,color:oor?'#f43f5e':color,fillColor:color,fillOpacity:.75,weight:oor?2.5:1.5,dashArray:oor?'4 3':null
    }).addTo(optState.map);
    const rows=[['Location',num(n.lat).toFixed(4)+', '+num(n.lon).toFixed(4)],['Daily demand',num(n.orders).toLocaleString('en-IN')+' orders']];
    if(wid!=null)rows.push(['Cluster','Warehouse '+rankById[wid]+' · '+esc(warehouses[indexById[wid]]?.name||'')]);
    m.bindTooltip(gpMapTooltip(rows,esc(n.name),color)+(oor?'<div class="mtt-oor">&#9888; Outside delivery radius</div>':''),{className:'leaflet-custom-tooltip',sticky:true});
    optState.neighborhoodLayer.push(m);
    if(labelsOn){
      const icon=L.divIcon({className:'nb-label',html:'<div style="border-color:'+color+'88;background:'+color+'22">'+esc(n.name)+'<span style="color:'+color+'">'+num(n.orders).toLocaleString('en-IN')+' ord</span></div>',iconAnchor:[0,0]});
      const lb=L.marker([num(n.lat),num(n.lon)],{icon,interactive:false,zIndexOffset:-10}).addTo(optState.map);
      optState.labelLayer.push(lb);
    }
  });

  /* ---- 5. warehouse hub pins ---- */
  warehouses.forEach(w=>{
    const color=colorById[w.id];
    const rank=rankById[w.id];
    const served=assignments.filter(a=>a.warehouse_id===w.id).length;
    const pin=L.marker([num(w.lat),num(w.lon)],{icon:gpWarehousePin(color,rank,topIds.has(w.id)),zIndexOffset:100}).addTo(optState.map);
    pin.bindTooltip(gpMapTooltip([
      ['Location',num(w.lat).toFixed(4)+', '+num(w.lon).toFixed(4)],
      ['Cluster load',num(w.assigned_orders).toLocaleString('en-IN')+' orders'],
      ['Neighborhoods',String(served)],
      ['Utilization',num(w.utilization_pct).toFixed(1)+'%'],
      ['Cost / day',money(w.daily_delivery_cost)]
    ],'W'+rank+' · '+esc(w.name),color),{className:'leaflet-custom-tooltip',sticky:true,offset:[0,-40]});
    pin.bindPopup('<b>'+esc(w.name)+'</b><br>Orders: '+num(w.assigned_orders).toLocaleString('en-IN')+'/day<br>Utilization: '+num(w.utilization_pct).toFixed(1)+'%');
    optState.warehouseLayer.push(pin);
  });

  /* ---- 6. planning location ---- */
  if(data.location?.latitude!=null){
    const u=L.circleMarker([data.location.latitude,data.location.longitude],{radius:10,color:'#67e8f9',fillColor:'#67e8f9',fillOpacity:.18,weight:2})
      .addTo(optState.map).bindPopup('<b>Selected planning location</b>');
    optState.neighborhoodLayer.push(u);
  }

  /* ---- 7. frame the result ---- */
  const bounds=[...(data.neighborhoods||[]).map(n=>[num(n.lat),num(n.lon)]),...warehouses.map(w=>[num(w.lat),num(w.lon)])];
  if(bounds.length)optState.map.fitBounds(L.latLngBounds(bounds).pad(0.15),{maxZoom:13});
  else optState.map.setView(focus,11);
  gpRenderClusterLegend(warehouses,colorById,rankById,assignments);
  setTimeout(()=>optState.map.invalidateSize({pan:false}),80);
}
function gpRenderClusterLegend(warehouses,colorById,rankById,assignments){
  const el=document.getElementById('clusterLegend');
  if(!el)return;
  if(!warehouses.length){el.innerHTML='';return}
  el.innerHTML=warehouses.map(w=>{
    const served=assignments.filter(a=>a.warehouse_id===w.id).length;
    return '<button type="button" class="cluster-chip" data-cluster-lat="'+num(w.lat)+'" data-cluster-lon="'+num(w.lon)+'"><i style="background:'+colorById[w.id]+'"></i>W'+rankById[w.id]+' · '+esc(w.name)+'<b>'+served+' zones</b></button>';
  }).join('');
  el.querySelectorAll('[data-cluster-lat]').forEach(btn=>btn.addEventListener('click',()=>{
    optState.map?.flyTo([Number(btn.dataset.clusterLat),Number(btn.dataset.clusterLon)],13,{duration:.9});
  }));
}

function renderSuggestions(items){
  const el=document.getElementById('suggestions');if(!el)return;
  el.innerHTML=(items||[]).slice(0,8).map((x,i)=>`<div class="suggestion"><div class="suggestion-main"><strong>${i+1}. ${esc(x.name)}</strong><span>${esc(x.reason||'Recommended warehouse location')}</span></div><div class="suggestion-right"><strong>${km(x.distance_km)}</strong><span>≈ ${num(x.drive_minutes).toFixed(0)} min</span><button class="mini-btn" onclick="showSuggestionRoute(${num(x.lat)},${num(x.lon)},'${esc(x.name).replace(/'/g,"\\'")}')">Route</button></div></div>`).join('')||'<div class="empty-state">Search a place, allow location, or choose a city to get ranked warehouse recommendations.</div>';
}
function renderChart(data){
  const ctx=document.getElementById('costChart');if(!ctx)return;optState.chartData=data;if(optState.chart)optState.chart.destroy();
  const light=currentTheme()==='light';const points=data.tradeoff_points||[];const labels=points.map(p=>p.k);const costs=points.map(p=>p.annual_total_cost);const delivery=points.map(p=>num(p.daily_delivery_cost)*365);const opening=points.map(p=>num(p.opening_cost));const selected=num(data.summary?.warehouse_count,1);const rec=num(data.recommendation?.recommended_k,selected);
  const grid=light?'rgba(68,93,117,.12)':'rgba(255,255,255,.06)';const tick=light?'#64778d':'#7890a8';const text=light?'#26384d':'#eef5ff';const tooltip=light?'#ffffff':'#0b1c2e';const totalColor=light?'#2478e5':'#6ecbff';const deliveryColor=light?'#13a58a':'#55e0b2';const openingColor=light?'#c47a17':'#ffbd66';
  const gradient=ctx.getContext('2d').createLinearGradient(0,0,0,380);gradient.addColorStop(0,light?'rgba(36,120,229,.25)':'rgba(78,161,255,.30)');gradient.addColorStop(1,light?'rgba(36,120,229,0)':'rgba(78,161,255,0)');
  const recommendedData=labels.map((k,i)=>k===rec?costs[i]:null);
  optState.chart=new Chart(ctx,{type:'line',data:{labels,datasets:[{label:'Total modeled cost',data:costs,borderColor:totalColor,backgroundColor:gradient,fill:true,tension:.34,borderWidth:2.8,pointRadius:0,pointHoverRadius:6},{label:'Delivery + fuel',data:delivery,borderColor:deliveryColor,backgroundColor:'transparent',fill:false,tension:.34,borderWidth:1.8,borderDash:[6,5],pointRadius:0},{label:'Warehouse opening',data:opening,borderColor:openingColor,backgroundColor:'transparent',fill:false,tension:.24,borderWidth:1.7,borderDash:[3,4],pointRadius:0},{label:'Recommended K',data:recommendedData,borderColor:'#67e8f9',backgroundColor:'#67e8f9',showLine:false,pointRadius:6,pointHoverRadius:9}]},options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:true,position:'top',align:'start',labels:{color:text,font:{size:9,weight:'700'},boxWidth:10,boxHeight:10,usePointStyle:true,padding:12}},tooltip:{backgroundColor:tooltip,borderColor:light?'rgba(36,120,229,.18)':'rgba(255,255,255,.12)',borderWidth:1,titleColor:text,bodyColor:light?'#60738a':'#bcd0e7',padding:12,displayColors:true,callbacks:{title:c=>`K = ${c[0]?.label||''} warehouses`,label:c=>`${c.dataset.label}: ${money(c.raw)}`}}},scales:{x:{grid:{color:grid},ticks:{color:tick,font:{size:9},maxTicksLimit:12}},y:{grid:{color:grid},ticks:{color:tick,font:{size:9},callback:v=>v>=10000000?`₹${(v/10000000).toFixed(1)}Cr`:v>=100000?`₹${(v/100000).toFixed(1)}L`:`₹${Math.round(v/1000)}k`},beginAtZero:true}}},onClick:(evt,active)=>{const p=active?.[0];if(!p)return;const k=labels[p.index];const allowed=Math.min(100,optState.uploadRows?.length||100);document.getElementById('selectionMode').value='exact';syncSelectionMode();const el=document.getElementById('maxWarehouses');if(el){el.max=String(allowed);el.value=Math.min(Number(k),allowed);syncRange('maxWarehouses')}toast(`K = ${k} selected. Run optimization to apply this point.`)}});
}

function renderBeforeAfterChart(data){
  const ctx=document.getElementById('beforeAfterChart');
  if(!ctx||typeof Chart==='undefined')return;
  if(optState.beforeAfterChart)optState.beforeAfterChart.destroy();
  const light=currentTheme()==='light';
  const tick=light?'#64778d':'#7890a8';
  const grid=light?'rgba(68,93,117,.12)':'rgba(255,255,255,.06)';
  const baseline=num(data.baseline?.annual_total_cost);
  const optimized=num(data.summary?.optimized_annual_cost);
  const max=Math.max(baseline,optimized,1);
  optState.beforeAfterChart=new Chart(ctx,{
    type:'bar',
    data:{
      labels:['Baseline','Optimized'],
      datasets:[{
        label:'Annual modeled cost',
        data:[baseline,optimized],
        borderRadius:9,
        borderSkipped:false,
        backgroundColor:light?['rgba(196,122,23,.72)','rgba(36,120,229,.78)']:['rgba(255,189,102,.72)','rgba(78,161,255,.78)'],
        borderWidth:1
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{callbacks:{label:c=>`Annual cost: ${money(c.raw)}`}}
      },
      scales:{
        x:{grid:{display:false},ticks:{color:tick,font:{size:10,weight:'700'}}},
        y:{
          beginAtZero:true,
          max:max*1.18,
          grid:{color:grid},
          ticks:{color:tick,font:{size:9},callback:v=>v>=10000000?`₹${(v/10000000).toFixed(1)}Cr`:v>=100000?`₹${(v/100000).toFixed(1)}L`:`₹${Math.round(v/1000)}k`}
        }
      }
    }
  });
}
function renderTopTwo(data){
  const grid=document.getElementById('topTwoGrid'),badge=document.getElementById('topTwoBadge'),why=document.getElementById('whySelected');
  if(!grid)return;
  const rows=[...(data.warehouses||[])].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders)).slice(0,2);
  if(!rows.length){grid.innerHTML='<div class="top-two-empty">No selected warehouses were returned by the optimizer.</div>';if(badge)badge.textContent='No result';if(why)why.innerHTML='<div class="top-two-empty">Run the optimizer to explain the selected sites.</div>';return}
  if(badge)badge.textContent=`${rows.length} sites highlighted`;
  grid.innerHTML=rows.map((w,i)=>{const reason=i===0?'Highest modeled demand coverage among selected sites.': 'Second-highest modeled demand coverage among selected sites.';return `<article class="top-two-card optimization-replay" style="--replay-delay:${i*90}ms"><span class="top-two-rank">#${i+1}</span><h4>${esc(w.name)}</h4><div class="site-meta">${num(w.assigned_orders).toLocaleString('en-IN')} orders/day served · ${num(w.utilization_pct).toFixed(1)}% capacity utilization</div><div class="top-two-metrics"><div><span>Demand cover</span><strong>${num(w.coverage_pct).toFixed(1)}%</strong></div><div><span>Weighted km</span><strong>${num(w.weighted_distance_km).toFixed(0)}</strong></div><div><span>Cost / day</span><strong>${money(w.daily_delivery_cost)}</strong></div></div><div class="recommendation-note">${reason} The selection balances weighted distance, opening cost, capacity and service radius.</div><span class="top-two-badge">Selected by GRIDPOINT</span></article>`}).join('');
  if(why)why.innerHTML=rows.map((w,i)=>`<div class="why-item"><span class="why-rank">#${i+1}</span><div><strong>${esc(w.name)}</strong><span>${num(w.assigned_orders).toLocaleString('en-IN')} orders/day served · ${num(w.utilization_pct).toFixed(1)}% capacity utilization · ${num(w.coverage_pct).toFixed(1)}% demand cover · ${num(w.weighted_distance_km).toFixed(0)} weighted order-km.</span></div></div>`).join('')+'<div class="recommendation-note">Top-two cards are a presentation ranking of the selected optimal network, not a separate optimization objective.</div>';
}
function downloadDecisionReport(){
  if(!optState.lastResult){toast('Run the optimizer first.');return} const d=optState.lastResult,s=d.summary||{},r=d.recommendation||{},b=d.baseline||{},diag=d.diagnostics||{},top=[...(d.warehouses||[])].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders)).slice(0,2);
  const html=`<!doctype html><html><head><meta charset="utf-8"><title>GRIDPOINT Decision Report</title><style>body{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#18263a}h1{margin-bottom:4px}small{color:#6b7d92}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}.card{padding:14px;border:1px solid #dbe4ef;border-radius:12px}.card b{display:block;font-size:20px;margin-top:5px}table{width:100%;border-collapse:collapse;margin-top:14px}th,td{padding:9px;border-bottom:1px solid #e6ecf3;text-align:left;font-size:12px}th{background:#f4f8fc}.note{padding:12px;background:#f4f8fc;border-radius:10px;margin-top:14px}</style></head><body><h1>GRIDPOINT Optimization Report</h1><small>${new Date().toLocaleString()}</small><div class="grid"><div class="card">Recommended K<b>${num(r.recommended_k)}</b></div><div class="card">Annual cost<b>${money(d.costs?.annual_total_cost)}</b></div><div class="card">Coverage<b>${num(s.coverage_pct).toFixed(1)}%</b></div><div class="card">Avg ETA<b>${num(s.avg_drive_minutes).toFixed(1)} min</b></div></div><div class="note"><b>Objective:</b> Minimize demand-weighted delivery cost + warehouse opening cost while respecting capacity, service radius and operating assumptions.<br><b>Baseline:</b> ${money(b.annual_total_cost)} annual modeled cost · <b>Optimized:</b> ${money(s.optimized_annual_cost)} · <b>Savings:</b> ${num(s.savings_pct).toFixed(1)}%</div><h2>Top selected sites</h2><table><tr><th>Rank</th><th>Warehouse</th><th>Orders/day</th><th>Utilization</th><th>Demand cover</th><th>Weighted km</th></tr>${top.map((w,i)=>`<tr><td>#${i+1}</td><td>${esc(w.name)}</td><td>${num(w.assigned_orders)}</td><td>${num(w.utilization_pct).toFixed(1)}%</td><td>${num(w.coverage_pct).toFixed(1)}%</td><td>${num(w.weighted_distance_km).toFixed(0)}</td></tr>`).join('')}</table><h2>Model assumptions</h2><p>Vehicle: ${esc(s.vehicle)} · Traffic: ${esc(s.traffic)} · Radius: ${num(s.radius_km).toFixed(0)} km · Capacity/site: ${num(s.capacity_per_warehouse).toLocaleString('en-IN')} · Demand/day: ${num(s.total_orders_per_day).toLocaleString('en-IN')} · Solver: ${esc(s.solver||diag.solver||'—')}</p><h2>Assignments</h2><table><tr><th>Neighborhood</th><th>Warehouse</th><th>Orders</th><th>Distance</th><th>ETA</th><th>Status</th></tr>${(d.assignments||[]).slice(0,500).map(a=>`<tr><td>${esc(a.neighborhood_name)}</td><td>${esc(a.warehouse_name)}</td><td>${num(a.orders)}</td><td>${num(a.distance_km).toFixed(2)} km</td><td>${num(a.drive_minutes).toFixed(0)} min</td><td>${esc(a.status)}</td></tr>`).join('')}</table></body></html>`; const blob=new Blob([html],{type:'text/html;charset=utf-8'}); const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='gridpoint-decision-report.html';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),600); toast('Decision report downloaded.');
}
function renderTables(data){
  const wh=document.getElementById('warehouseTable');
  const warehouseRows=[...(data.warehouses||[])]; const topIds=new Set([...warehouseRows].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders)).slice(0,2).map(w=>w.id));
  wh.innerHTML=warehouseRows.map((w,i)=>`<tr class="${topIds.has(w.id)?'warehouse-top-row':''}"><td>${i+1}</td><td><strong>${esc(w.name)}</strong></td><td>${num(w.assigned_orders).toLocaleString('en-IN')}</td><td><div class="util-cell"><span>${num(w.utilization_pct).toFixed(1)}%</span><i><b style="width:${Math.min(100,Math.max(0,num(w.utilization_pct)))}%"></b></i></div></td><td>${num(w.coverage_pct).toFixed(1)}%</td><td>${num(w.weighted_distance_km).toFixed(0)}</td><td>${money(w.daily_delivery_cost)}</td></tr>`).join('')||'<tr><td colspan="7">No warehouse result yet.</td></tr>';
  const as=document.getElementById('assignmentTable');
  as.innerHTML=(data.assignments||[]).slice(0,300).map(a=>`<tr><td>${esc(a.neighborhood_name)}</td><td>${esc(a.warehouse_name)}</td><td>${num(a.orders).toLocaleString('en-IN')}</td><td>${km(a.distance_km)}</td><td>${num(a.drive_minutes).toFixed(0)} min</td><td><span class="status-chip ${a.feasible?'ok':'warn'}">${esc(a.status)}</span></td></tr>`).join('')||'<tr><td colspan="6">No assignments yet.</td></tr>';
  document.getElementById('assignmentCountLabel').textContent=`${(data.assignments||[]).length} locations`;
  document.getElementById('warehouseCountLabel').textContent=`${(data.warehouses||[]).length} selected`;
}
function playOptimizationCompletion(){
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({top:0,behavior:reduced?'auto':'smooth'});
  const targets=[...document.querySelectorAll('main .page-head, main .optimizer-layout > *, main .workspace > .top-two-section, main .top-two-card, main .dashboard-grid > *, main .split-grid > *')].slice(0,14);
  if(reduced){targets.forEach(el=>el.classList.add('is-visible'));return;}
  targets.forEach((el,i)=>{el.classList.remove('optimization-replay');void el.offsetWidth;el.style.setProperty('--replay-delay',`${Math.min(i*55,260)}ms`);el.classList.add('optimization-replay')});
}
function renderResult(data){
  optState.lastResult=data;
  const s=data.summary||{},c=data.costs||{},b=data.baseline||{},d=data.diagnostics||{},r=data.recommendation||{};
  document.getElementById('totalCost').textContent=money(safePick(c.annual_total_cost,c.total_cost,c.totalCost,data.metrics?.total_cost));
  document.getElementById('dailyCost').textContent=money(safePick(c.daily_delivery_cost,c.total_delivery_cost,c.totalDeliveryCost,data.metrics?.total_delivery_cost));
  document.getElementById('distance').textContent=`${num(s.weighted_distance_km).toLocaleString('en-IN',{maximumFractionDigits:0})} order-km`;
  document.getElementById('warehouses').textContent=num(s.warehouse_count);
  document.getElementById('warehouseDecision').textContent=s.selection_mode==='auto'?`recommended K = ${num(s.recommended_warehouse_count)}`:`exact K requested`;
  document.getElementById('recommendationText').textContent=`Use ${num(r.recommended_k)} warehouse${num(r.recommended_k)===1?'':'s'} under the current assumptions.`;
  document.getElementById('recommendationReason').textContent=r.reason||'';
  document.getElementById('coveragePill').textContent=`Coverage ${num(s.coverage_pct).toFixed(1)}%`;
  document.getElementById('capacityPill').textContent=`Max utilization ${num(s.capacity_utilization_max_pct).toFixed(1)}%`;
  document.getElementById('radiusPill').textContent=s.radius_violations?`${num(s.radius_violations)} radius issues`:'Radius satisfied';
  document.getElementById('baselineCost').textContent=money(b.annual_total_cost);
  document.getElementById('optimizedCost').textContent=money(s.optimized_annual_cost);
  document.getElementById('baselineDistance').textContent=`Avg ${num(b.avg_distance_per_order_km).toFixed(1)} km/order`;
  document.getElementById('optimizedDistance').textContent=`Avg ${num(s.avg_distance_per_order_km).toFixed(1)} km/order`;
  document.getElementById('baselineCoverage').textContent=`Coverage ${num(b.coverage_pct).toFixed(1)}%`;
  document.getElementById('optimizedCoverage').textContent=`Coverage ${num(s.coverage_pct).toFixed(1)}%`;
  document.getElementById('savings').textContent=`${num(s.savings_pct).toFixed(1)}% lower modeled cost`;
  document.getElementById('distanceSavings').textContent=`${(num(b.avg_distance_per_order_km)>0?Math.max(0,100*(b.avg_distance_per_order_km-num(s.avg_distance_per_order_km))/b.avg_distance_per_order_km):0).toFixed(1)}% shorter avg distance`;
  document.getElementById('capacityStatus').textContent=d.capacity_status||'—';document.getElementById('radiusStatus').textContent=d.radius_status||'—';
  const slaEl=document.getElementById('slaCoverage');if(slaEl)slaEl.textContent=`${num(s.sla_coverage_pct).toFixed(1)}% ≤ ${num(s.sla_target_minutes).toFixed(0)}m`;
  document.getElementById('avgUtilization').textContent=`${num(s.capacity_utilization_avg_pct).toFixed(1)}%`;document.getElementById('maxUtilization').textContent=`${num(s.capacity_utilization_max_pct).toFixed(1)}%`;document.getElementById('unservedOrders').textContent=num(s.unserved_orders).toLocaleString('en-IN');document.getElementById('avgDriveTime').textContent=`${num(s.avg_drive_minutes).toFixed(1)} min`;document.getElementById('fuelDaily').textContent=money(s.energy_cost_daily);document.getElementById('emissions').textContent=`${num(s.estimated_emissions_kg_daily).toFixed(0)} kg/day`;document.getElementById('resilience').textContent=`${num(s.network_resilience_pct).toFixed(1)}%`;
  document.getElementById('assumptionVehicle').textContent=s.vehicle||'—';document.getElementById('assumptionTraffic').textContent=s.traffic||'—';document.getElementById('assumptionRadius').textContent=`${num(s.radius_km).toFixed(0)} km`;document.getElementById('assumptionCapacity').textContent=num(s.capacity_per_warehouse).toLocaleString('en-IN');document.getElementById('assumptionDemand').textContent=num(s.total_orders_per_day).toLocaleString('en-IN');document.getElementById('assumptionCandidates').textContent=num(d.candidate_count);document.getElementById('assumptionFuel').textContent=money(s.energy_cost_daily)+' / day';document.getElementById('assumptionSolver').textContent=s.solver||d.solver||'Heuristic';
  document.getElementById('recommendedKLabel').textContent=`Recommended K = ${num(r.recommended_k)}`;document.getElementById('chartCaption').textContent=`${num(r.tested_up_to)} network sizes evaluated · opening cost + delivery cost + constraint penalty.`;document.getElementById('mapStatus').textContent=`${num(s.warehouse_count)} sites · ${num(s.coverage_pct).toFixed(0)}% demand coverage`;document.getElementById('locationBadge').textContent=data.location?.permission==='granted'?'Location active':`India · ${data.city||'City mode'}`;document.getElementById('modelStatus').textContent=[d.data_status,d.routing_mode||d.diagnostics?.routing_mode].filter(Boolean).join(' · ')||'—';const sb=document.getElementById('solverBadge');if(sb)sb.textContent=s.solver||d.solver||'Constraint-aware heuristic';
  renderSuggestions(data.nearest_warehouses);drawMap(data);renderTopTwo(data);renderTables(data);renderChart(data);renderBeforeAfterChart(data);
}
async function requestLocation(){
  if(!navigator.geolocation){setLocationStatus('Geolocation is not supported by this browser.','bad');return}
  setLocationStatus('Requesting browser location permission…');
  navigator.geolocation.getCurrentPosition(async pos=>{
    const d=await loadNearby(pos.coords.latitude,pos.coords.longitude);
    applyDetectedCity(d?.city||'','Current location detected');
    if(d?.city)toast(`GRIDPOINT detected ${d.city} as your nearest supported market.`);
  },err=>{let msg='Location access was denied. Use Search location or click the map instead.';if(err.code===1)msg='Location access is blocked. Allow location for this site in your browser permissions, then try again.';if(err.code===2)msg='Your location could not be determined. Check device location services or use Search location.';if(err.code===3)msg='Location request timed out. Use Search location or try again.';setLocationStatus(msg,'bad');toast('Location permission is optional — GRIDPOINT can work with any Indian city or map point.')},{enableHighAccuracy:true,timeout:12000,maximumAge:60000});
}
function clearLocation(){optState.location=null;setLocationStatus('Live location cleared. Using selected market or map location.','good');document.getElementById('locationBadge').textContent='City mode'}
function syncSelectionMode(){const mode=document.getElementById('selectionMode').value;const field=document.getElementById('warehouseCountField');const el=document.getElementById('maxWarehouses');if(field)field.style.display=mode==='exact'?'block':'none';if(el){el.disabled=mode!=='exact';el.closest('.premium-range')?.classList.toggle('is-disabled',mode!=='exact')}syncRange('maxWarehouses')}
function showDemandPreview(rows,focus){
  if(!optState.map)return;
  clearMapLayer(optState.neighborhoodLayer);
  const points=rows||[];
  points.forEach(n=>{const radius=Math.max(4,Math.min(13,3.5+Math.sqrt(Math.max(0,num(n.orders)))/5));const marker=L.circleMarker([num(n.lat),num(n.lon)],{radius,color:'#4ea1ff',fillColor:'#67e8f9',fillOpacity:.42,weight:1}).addTo(optState.map);marker.bindTooltip(`${esc(n.name)} · ${num(n.orders).toLocaleString('en-IN')} orders/day`);optState.neighborhoodLayer.push(marker)});
  if(focus)optState.map.setView(focus,11,{animate:false});
  setTimeout(()=>optState.map.invalidateSize({pan:false}),60);
}
async function runOptimization(){
  const mode=document.getElementById('selectionMode').value;const datasetCount=Math.max(1,optState.uploadRows?.length||25);const internalMax=Math.min(100,datasetCount);const selectedK=Math.min(internalMax,Math.max(1,Number(document.getElementById('maxWarehouses').value)||3));const payload={city:document.getElementById('city').value,selectionMode:mode,exactWarehouses:selectedK,capacity:Number(document.getElementById('capacity').value),openingCost:Number(document.getElementById('openingCost').value),demandGrowth:Number(document.getElementById('growth').value)/100,traffic:document.getElementById('traffic').value,variableCost:Number(document.getElementById('variableCost').value),radius:Number(document.getElementById('radius').value),maxWarehouses:internalMax,fuelPrice:Number(document.getElementById('fuelPrice').value),vehicle:document.getElementById('vehicle').value,slaMinutes:Number(document.getElementById('slaMinutes').value),userLatitude:optState.location?.latitude??null,userLongitude:optState.location?.longitude??null,neighborhoods:optState.uploadRows||null,manualWarehouses:optState.manualWarehouses||[]};
  try{const btn=document.getElementById('optimizeBtnTop');btn.disabled=true;btn.textContent='Optimizing network…';const data=await fetchJSON('/api/optimize',{method:'POST',body:JSON.stringify(payload)});renderResult(data);toast(`GRIDPOINT selected ${data.summary.warehouse_count} warehouse${data.summary.warehouse_count===1?'':'s'}.`);btn.disabled=false;btn.textContent='Run optimization';setTimeout(playOptimizationCompletion,120)}catch(e){toast(e.message);const btn=document.getElementById('optimizeBtnTop');btn.disabled=false;btn.textContent='Run optimization'}
}
function downloadResults(){
  if(!optState.lastResult){toast('Run the optimizer first.');return}
  const rows=[['Neighborhood','Warehouse','Orders/day','Distance km','Drive minutes','Daily cost','Status']];(optState.lastResult.assignments||[]).forEach(a=>rows.push([a.neighborhood_name,a.warehouse_name,a.orders,a.distance_km,a.drive_minutes,a.daily_cost,a.status]));
  const csv=rows.map(r=>r.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='gridpoint-optimization-results.csv';a.click();URL.revokeObjectURL(a.href);toast('Results CSV downloaded.');
}
function bindPlanningMapClick(){if(!optState.map||optState.map._gpPlanningClickBound)return;optState.map._gpPlanningClickBound=true;optState.map.on('click',e=>{if(optState.addingWarehouse){handleWarehouseMapClick(e);return}loadNearby(e.latlng.lat,e.latlng.lng);setLocationStatus('Map location selected.','good')})}
document.getElementById('detectLocation').addEventListener('click',requestLocation);
document.getElementById('clearLocation').addEventListener('click',clearLocation);
document.getElementById('searchLocation').addEventListener('click',searchLocation);
document.getElementById('locationQuery').addEventListener('keydown',e=>{if(e.key==='Enter')searchLocation()});
document.getElementById('optimizeBtnTop').addEventListener('click',runOptimization);
document.getElementById('addWarehouseMode').addEventListener('click',toggleAddWarehouseMode);document.getElementById('clearWarehouses').addEventListener('click',()=>{if(!optState.manualWarehouses.length){toast('No custom warehouses to clear.');return}if(confirm('Remove all custom warehouses?')){optState.manualWarehouses=[];saveManualWarehouses()}});loadManualWarehouses();
document.getElementById('downloadBtn').addEventListener('click',downloadResults);
document.getElementById('downloadMathCsv')?.addEventListener('click',downloadMathLogicCsv);
document.getElementById('downloadReport')?.addEventListener('click',downloadDecisionReport);document.getElementById('downloadReportInline')?.addEventListener('click',downloadDecisionReport);
document.getElementById('setBestDefaults')?.addEventListener('click',()=>{applyBalancedDefaults(optState.uploadRows||[]);toast('Balanced defaults restored. Run optimization to calculate the actual optimum.')});
document.getElementById('selectionMode').addEventListener('change',syncSelectionMode);
document.getElementById('maxWarehouses').addEventListener('input',()=>syncRange('maxWarehouses'));
document.getElementById('city').addEventListener('change',async()=>{const selected=document.getElementById('city').value;const c=cityData[selected];clearLocation();if(c){applyDetectedCity(selected,`Using ${selected} market center`);if(optState.map)optState.map.setView([c.lat,c.lon],11);await loadDefaultCityDataset(selected);await loadNearby(c.lat,c.lon,selected)}});
async function runStressScenario(kind){if(!optState.uploadRows?.length&&!optState.lastResult){toast('Run the main optimization first.');return}const status=document.getElementById('stressStatus');const box=document.getElementById('stressResults');if(!status||!box)return;const mode=document.getElementById('selectionMode').value;const datasetCount=Math.max(1,optState.uploadRows?.length||25);const internalMax=Math.min(100,datasetCount);const selectedK=Math.min(internalMax,Math.max(1,Number(document.getElementById('maxWarehouses').value)||3));const base={city:document.getElementById('city').value,selectionMode:mode,exactWarehouses:selectedK,capacity:Number(document.getElementById('capacity').value),openingCost:Number(document.getElementById('openingCost').value),demandGrowth:Number(document.getElementById('growth').value)/100,traffic:document.getElementById('traffic').value,variableCost:Number(document.getElementById('variableCost').value),radius:Number(document.getElementById('radius').value),maxWarehouses:internalMax,fuelPrice:Number(document.getElementById('fuelPrice').value),vehicle:document.getElementById('vehicle').value,slaMinutes:Number(document.getElementById('slaMinutes').value),userLatitude:optState.location?.latitude??null,userLongitude:optState.location?.longitude??null,neighborhoods:optState.uploadRows||null,manualWarehouses:optState.manualWarehouses||[]};if(kind==='demand')base.demandGrowth=Math.max(base.demandGrowth,.25);if(kind==='traffic')base.traffic='peak';if(kind==='radius')base.radius=Math.max(3,Math.round(base.radius*.55));if(kind==='failure'){const top=[...(optState.lastResult?.warehouses||[])].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders))[0];if(top)base.blockedWarehouseId=top.id;}status.textContent='Running scenario…';box.querySelectorAll('.scenario-card strong').forEach(e=>e.textContent='…');try{const d=await fetchJSON('/api/optimize',{method:'POST',body:JSON.stringify(base)});const s=d.summary||{};box.innerHTML=`<div class="scenario-card"><span>Annual cost</span><strong>${money(d.costs?.annual_total_cost)}</strong><small>${d.recommendation?.recommended_k||s.warehouse_count} warehouses</small></div><div class="scenario-card"><span>Coverage</span><strong>${num(s.coverage_pct).toFixed(1)}%</strong><small>${num(s.unserved_orders).toLocaleString('en-IN')} constrained orders</small></div><div class="scenario-card"><span>Avg ETA</span><strong>${num(s.avg_drive_minutes).toFixed(1)} min</strong><small>${esc(d.summary?.vehicle||base.vehicle)}</small></div><div class="scenario-card"><span>Network</span><strong>${num(s.warehouse_count)}</strong><small>${kind==='failure'?'After outage':'Scenario result'}</small></div>`;status.textContent=`Scenario: ${kind==='demand'?'+25% demand':kind==='traffic'?'Peak traffic':kind==='radius'?'55% tighter service radius':'Highest-demand warehouse outage'} · same constrained model, new conditions.`}catch(e){status.textContent=e.message;toast(e.message)}}document.querySelectorAll('.stress-btn').forEach(btn=>btn.addEventListener('click',()=>runStressScenario(btn.dataset.stress)));
document.querySelectorAll('.scenario').forEach(btn=>btn.addEventListener('click',()=>{document.getElementById('growth').value=btn.dataset.growth;syncRange('growth')}));

async function gpLoadDemandCsv(file){
  if(!file)return;
  const fn=document.getElementById('fileName');if(fn)fn.textContent=file.name;
  try{
    const fd=new FormData();fd.append('file',file);
    const r=await fetch('/api/upload',{method:'POST',body:fd});
    const d=await r.json();
    if(!r.ok||!d.ok)throw new Error(d.error||'Upload failed');
    optState.uploadRows=d.rows;
    localStorage.setItem('gridpoint-demand-rows',JSON.stringify(d.rows));
    localStorage.setItem('gridpoint-demand-label',file.name);
    localStorage.setItem('gridpoint-demand-filename',file.name);
    updateOptimizerSourceSummary();
    showDemandPreview(d.rows);
    const summary=document.getElementById('uploadSummary');
    if(summary){summary.style.display='block';summary.innerHTML=`<div class="import-success"><span class="success-icon">✓</span><div><strong>File loaded successfully</strong><span>${esc(file.name)} · ${d.count} valid locations ready for optimization.</span></div></div>`}
    syncOptimizerDataLimit();
    toast(`CSV loaded · ${d.count} locations ready.`);
    document.getElementById('warehouseAddPanel')?.scrollIntoView({behavior:'smooth',block:'nearest'});
  }catch(err){toast(err.message)}
}
document.getElementById('csvInput').addEventListener('change',e=>{gpLoadDemandCsv(e.target.files[0]);e.target.value=''});
document.getElementById('csvInputTop')?.addEventListener('change',e=>{gpLoadDemandCsv(e.target.files[0]);e.target.value=''});['maxWarehouses','capacity','radius','growth','slaMinutes'].forEach(id=>bindRange(id));
syncSelectionMode();['maxWarehouses','capacity','radius','growth','slaMinutes'].forEach(syncRange);
const bootCity=cityData[document.getElementById('city').value];
if(bootCity){
  optState.map=mapFactory('optMap',bootCity.lat,bootCity.lon,11);
  bindPlanningMapClick();
  if(optState.uploadRows?.length){showDemandPreview(optState.uploadRows,[bootCity.lat,bootCity.lon]);syncOptimizerDataLimit();}
  else{loadDefaultCityDataset(document.getElementById('city').value);}
  loadNearby(bootCity.lat,bootCity.lon,document.getElementById('city').value);
}

/* ================================================================
   GRIDPOINT · 3D map overlay
   Real extruded geometry drawn on a canvas above the Leaflet panes.
   The canvas is pointer-events:none, so clicks, tooltips, popups and
   the "add warehouse" flow keep working on the untouched 2D map.
   ================================================================ */
const GP_PALETTE=['#67e8f9','#4ea1ff','#a78bfa','#fb7185','#34d399','#fbbf24','#38bdf8','#f472b6'];
const gpMap3D={on:localStorage.getItem('gridpoint-optimizer-3d')!=='0',canvas:null,ctx:null,badge:null,map:null,points:[],sites:[],links:[],raf:0};
function gp3DSchedule(){
  if(gpMap3D.raf)return;
  gpMap3D.raf=requestAnimationFrame(()=>{gpMap3D.raf=0;gp3DDraw()});
}
function gp3DEnsure(){
  const map=optState.map;
  if(!map)return null;
  if(gpMap3D.canvas&&gpMap3D.map===map)return gpMap3D.canvas;
  const host=document.getElementById('optimizer3dWrap')||map.getContainer();
  const c=document.createElement('canvas');
  c.className='gp-3d-canvas';
  host.appendChild(c);
  const badge=document.createElement('div');
  badge.className='gp-3d-badge';
  badge.textContent='3D EXTRUSION · HEIGHT = DAILY ORDERS';
  host.appendChild(badge);
  gpMap3D.canvas=c;gpMap3D.ctx=c.getContext('2d');gpMap3D.badge=badge;gpMap3D.map=map;
  map.on('move zoom viewreset resize moveend zoomend load',gp3DSchedule);
  map.on('zoomstart',()=>{c.style.opacity='0'});
  map.on('zoomend',()=>{c.style.opacity='1';gp3DSchedule()});
  window.addEventListener('resize',gp3DSchedule);
  window.addEventListener('gridpoint:themechange',gp3DSchedule);
  gp3DApplyVisibility();
  return c;
}
function gp3DApplyVisibility(){
  const wrap=document.getElementById('optimizer3dWrap');
  if(wrap)wrap.classList.toggle('is-3d',gpMap3D.on);
  if(gpMap3D.canvas)gpMap3D.canvas.style.display=gpMap3D.on?'block':'none';
  if(gpMap3D.badge)gpMap3D.badge.style.display=gpMap3D.on?'block':'none';
  const btn=document.getElementById('optimizer3dToggle');
  if(btn){
    btn.classList.toggle('active',gpMap3D.on);
    btn.setAttribute('aria-pressed',String(gpMap3D.on));
    btn.textContent=gpMap3D.on?'◈ 3D':'□ Flat';
  }
  const status=document.getElementById('mapStatus');
  if(status&&!optState.lastResult)status.textContent=gpMap3D.on?'3D Leaflet map':'Flat Leaflet map';
}
function gp3DSetPoints(points,sites,links){
  gpMap3D.points=(points||[]).filter(p=>Number.isFinite(num(p.lat))&&Number.isFinite(num(p.lon)));
  gpMap3D.sites=sites||[];
  gpMap3D.links=links||[];
  gp3DEnsure();
  gp3DSchedule();
}
function gp3DFromResult(data){
  const sites=(data.warehouses||[]).map((w,i)=>({lat:num(w.lat),lon:num(w.lon),name:w.name,orders:num(w.assigned_orders),color:GP_PALETTE[i%GP_PALETTE.length]}));
  const links=(data.assignments||[]).slice(0,220).map(a=>({a:[num(a.neighborhood_lat),num(a.neighborhood_lon)],b:[num(a.warehouse_lat),num(a.warehouse_lon)],ok:!!a.feasible}));
  gp3DSetPoints((data.neighborhoods||[]).map(n=>({lat:num(n.lat),lon:num(n.lon),name:n.name,orders:num(n.orders)})),sites,links);
}
function gp3DColumn(ctx,b,light){
  const rx=b.r,ry=Math.max(1.6,b.r*0.42),top=b.y-b.h;
  ctx.save();
  ctx.globalAlpha=light?0.16:0.26;
  ctx.fillStyle=light?'#1b3550':'#000000';
  ctx.beginPath();ctx.ellipse(b.x+rx*0.35,b.y+ry*0.35,rx*1.05,ry*1.05,0,0,Math.PI*2);ctx.fill();
  ctx.restore();
  const grad=ctx.createLinearGradient(b.x-rx,top,b.x+rx,b.y);
  grad.addColorStop(0,b.side);
  grad.addColorStop(0.55,b.color);
  grad.addColorStop(1,b.shade);
  ctx.beginPath();
  ctx.ellipse(b.x,b.y,rx,ry,0,0,Math.PI);
  ctx.lineTo(b.x-rx,top);
  ctx.ellipse(b.x,top,rx,ry,0,Math.PI,0,true);
  ctx.closePath();
  ctx.fillStyle=grad;ctx.globalAlpha=b.alpha;ctx.fill();
  ctx.globalAlpha=1;
  ctx.beginPath();ctx.ellipse(b.x,top,rx,ry,0,0,Math.PI*2);
  ctx.fillStyle=b.cap;ctx.fill();
  ctx.lineWidth=b.kind==='w'?1.6:0.9;
  ctx.strokeStyle=light?'rgba(255,255,255,.85)':'rgba(255,255,255,.55)';
  ctx.stroke();
  if(b.kind==='w'&&b.label){
    ctx.font='800 9px Inter,sans-serif';
    const w=ctx.measureText(b.label).width+12;
    const ly=top-ry-16;
    ctx.globalAlpha=.94;
    ctx.fillStyle=light?'rgba(255,255,255,.96)':'rgba(8,18,31,.88)';
    ctx.beginPath();
    if(ctx.roundRect)ctx.roundRect(b.x-w/2,ly,w,15,7);else ctx.rect(b.x-w/2,ly,w,15);
    ctx.fill();
    ctx.globalAlpha=1;
    ctx.fillStyle=light?'#1d3550':'#eaf4ff';
    ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText(b.label,b.x,ly+8);
    ctx.beginPath();ctx.moveTo(b.x,ly+15);ctx.lineTo(b.x,top-ry);
    ctx.strokeStyle=b.color;ctx.lineWidth=1;ctx.stroke();
  }
}
function gp3DDraw(){
  const map=gpMap3D.map,c=gpMap3D.canvas,ctx=gpMap3D.ctx;
  if(!map||!c||!ctx)return;
  const size=map.getSize();
  const dpr=Math.min(2,window.devicePixelRatio||1);
  if(c.width!==Math.round(size.x*dpr)||c.height!==Math.round(size.y*dpr)){
    c.width=Math.round(size.x*dpr);c.height=Math.round(size.y*dpr);
  }
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,size.x,size.y);
  if(!gpMap3D.on)return;
  const light=currentTheme()==='light';
  const zoom=map.getZoom();
  const hs=Math.max(0.5,Math.min(1.85,(zoom-6.4)/4.2));
  const maxOrders=Math.max(1,...gpMap3D.points.map(p=>num(p.orders)),...gpMap3D.sites.map(w=>num(w.orders)));
  const inView=pt=>pt.x>-140&&pt.y>-220&&pt.x<size.x+140&&pt.y<size.y+140;
  ctx.lineCap='round';
  gpMap3D.links.forEach(l=>{
    const a=map.latLngToContainerPoint(l.a),b=map.latLngToContainerPoint(l.b);
    if(!inView(a)&&!inView(b))return;
    ctx.beginPath();
    ctx.moveTo(a.x,a.y);
    ctx.quadraticCurveTo((a.x+b.x)/2,(a.y+b.y)/2-Math.min(90,Math.hypot(b.x-a.x,b.y-a.y)*0.28),b.x,b.y);
    ctx.strokeStyle=l.ok?(light?'rgba(36,120,229,.16)':'rgba(103,232,249,.17)'):(light?'rgba(201,48,77,.4)':'rgba(255,107,125,.45)');
    ctx.lineWidth=l.ok?1:1.8;
    ctx.setLineDash(l.ok?[]:[4,4]);
    ctx.stroke();
    ctx.setLineDash([]);
  });
  const bars=[];
  gpMap3D.points.forEach(p=>{
    const pt=map.latLngToContainerPoint([num(p.lat),num(p.lon)]);
    if(!inView(pt))return;
    const share=Math.sqrt(Math.max(0,num(p.orders))/maxOrders);
    bars.push({x:pt.x,y:pt.y,h:(9+64*share)*hs,r:Math.max(2.8,3+5.5*share)*hs,kind:'d',alpha:.88,
      color:light?'#3f8fe0':'#3d8fe8',side:light?'#7db6ef':'#6fb6ff',shade:light?'#2a6cb5':'#22527f',cap:light?'#8fd0f5':'#8fdcff'});
  });
  gpMap3D.sites.forEach(w=>{
    const pt=map.latLngToContainerPoint([num(w.lat),num(w.lon)]);
    if(!inView(pt))return;
    const share=Math.sqrt(Math.max(0,num(w.orders))/maxOrders);
    bars.push({x:pt.x,y:pt.y,h:(48+92*share)*hs,r:Math.max(6,7+6*share)*hs,kind:'w',alpha:.95,label:w.name,
      color:w.color||'#67e8f9',side:'#ffffff',shade:light?'#1d4f7d':'#0b2438',cap:w.color||'#67e8f9'});
  });
  bars.sort((a,b)=>a.y-b.y);
  bars.forEach(b=>gp3DColumn(ctx,b,light));
}
const gp3dBtn=document.getElementById('optimizer3dToggle');
if(gp3dBtn){
  gp3dBtn.addEventListener('click',()=>{
    gpMap3D.on=!gpMap3D.on;
    localStorage.setItem('gridpoint-optimizer-3d',gpMap3D.on?'1':'0');
    gp3DApplyVisibility();
    gp3DSchedule();
    toast(gpMap3D.on?'3D view on · column height shows daily orders.':'Flat map view.');
  });
}
gp3DApplyVisibility();

/* keep the 3D layer in sync with the existing render pipeline */
const gpOrigDrawMap=drawMap;
drawMap=function(data){gpOrigDrawMap(data);gp3DFromResult(data)};

/* ================================================================
   GRIDPOINT · 3D analytics engine
   Dependency-free isometric renderer: rotatable cuboid bar charts
   drawn with painter's algorithm on a 2D canvas.
   ================================================================ */
function gpHexRgb(hex){
  const h=String(hex||'#4ea1ff').replace('#','');
  const v=h.length===3?h.split('').map(x=>x+x).join(''):h;
  return [parseInt(v.slice(0,2),16),parseInt(v.slice(2,4),16),parseInt(v.slice(4,6),16)];
}
function gpShade(hex,factor,alpha){
  const c=gpHexRgb(hex).map(v=>Math.max(0,Math.min(255,Math.round(v*factor))));
  return 'rgba('+c[0]+','+c[1]+','+c[2]+','+(alpha==null?1:alpha)+')';
}
function gpCube(canvasId,stageId){
  const canvas=document.getElementById(canvasId),stage=document.getElementById(stageId);
  if(!canvas||!stage)return null;
  const ctx=canvas.getContext('2d');
  const st={yaw:-0.62,pitch:0.5,zoom:1,spin:false,data:null,raf:0,hover:null,drag:null};
  const LIGHT_DIR=[0.48,0.74,-0.47];
  function project(x,y,z,g){
    const cy=Math.cos(st.yaw),sy=Math.sin(st.yaw);
    const X=x*cy-z*sy,Z=x*sy+z*cy;
    const cp=Math.cos(st.pitch),sp=Math.sin(st.pitch);
    const Y=y*cp-Z*sp,depth=y*sp+Z*cp;
    return {x:g.cx+X*g.scale,y:g.cy-Y*g.scale,d:depth};
  }
  function normalLight(nx,ny,nz){
    const cy=Math.cos(st.yaw),sy=Math.sin(st.yaw);
    const rx=nx*cy-nz*sy,rz=nx*sy+nz*cy;
    const dot=rx*LIGHT_DIR[0]+ny*LIGHT_DIR[1]+rz*LIGHT_DIR[2];
    return 0.5+0.55*Math.max(0,dot);
  }
  function schedule(){
    if(st.raf)return;
    st.raf=requestAnimationFrame(()=>{st.raf=0;draw()});
  }
  function resize(){
    const r=stage.getBoundingClientRect();
    const dpr=Math.min(2,window.devicePixelRatio||1);
    const w=Math.max(40,Math.round(r.width*dpr)),h=Math.max(40,Math.round(r.height*dpr));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
    ctx.setTransform(dpr,0,0,dpr,0,0);
    return {w:r.width,h:r.height};
  }
  function niceMax(v){
    if(!(v>0))return 1;
    const exp=Math.pow(10,Math.floor(Math.log10(v)));
    const n=v/exp;
    const step=n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10;
    return step*exp;
  }
  function draw(){
    const box=resize();
    ctx.clearRect(0,0,box.w,box.h);
    const d=st.data;
    if(!d||!d.categories.length)return;
    const light=currentTheme()==='light';
    const axis=light?'rgba(53,79,108,.5)':'rgba(190,214,240,.55)';
    const grid=light?'rgba(53,79,108,.16)':'rgba(190,214,240,.14)';
    const txt=light?'#4d6379':'#93a9c1';
    const g={cx:box.w/2,cy:box.h*0.66,scale:Math.min(box.w,box.h)*0.44*st.zoom};
    const n=d.categories.length,m=d.series.length;
    let peak=0;
    d.series.forEach(se=>se.values.forEach(v=>{if(Number.isFinite(v)&&v>peak)peak=v}));
    const top=niceMax(peak);
    const P=(x,y,z)=>project(x,y,z,g);
    /* floor */
    ctx.lineWidth=1;
    ctx.strokeStyle=grid;
    for(let i=0;i<=n;i++){
      const x=-1+(2/n)*i;
      const a=P(x,0,-0.6),b=P(x,0,0.6);
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    }
    for(let j=0;j<=m;j++){
      const z=-0.6+(1.2/m)*j;
      const a=P(-1,0,z),b=P(1,0,z);
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    }
    /* value axis at the back-left edge */
    const ticks=4;
    ctx.font='700 9px Inter,sans-serif';
    ctx.textAlign='right';ctx.textBaseline='middle';
    for(let t=0;t<=ticks;t++){
      const y=t/ticks;
      const a=P(-1,y,-0.6),b=P(1,y,-0.6);
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.strokeStyle=t===0?axis:grid;ctx.stroke();
      ctx.fillStyle=txt;
      ctx.fillText(d.format?d.format(top*y):String(Math.round(top*y)),a.x-7,a.y);
    }
    /* bars as cuboids, painter's algorithm over every face */
    const faces=[],labels=[];
    const bw=(2/n)*0.3,bd=(1.2/m)*0.3;
    d.categories.forEach((cat,i)=>{
      const cxm=-1+(2/n)*(i+0.5);
      d.series.forEach((se,j)=>{
        const raw=Number(se.values[i]);
        if(!Number.isFinite(raw))return;
        const hy=Math.max(0.004,Math.min(1,raw/top));
        const czm=-0.6+(1.2/m)*(j+0.5);
        const x0=cxm-bw,x1=cxm+bw,z0=czm-bd,z1=czm+bd;
        const v=[[x0,0,z0],[x1,0,z0],[x1,0,z1],[x0,0,z1],[x0,hy,z0],[x1,hy,z0],[x1,hy,z1],[x0,hy,z1]].map(q=>P(q[0],q[1],q[2]));
        const quads=[
          {idx:[4,5,6,7],nrm:[0,1,0]},
          {idx:[0,1,5,4],nrm:[0,0,-1]},
          {idx:[1,2,6,5],nrm:[1,0,0]},
          {idx:[2,3,7,6],nrm:[0,0,1]},
          {idx:[3,0,4,7],nrm:[-1,0,0]}
        ];
        quads.forEach(q=>{
          const pts=q.idx.map(k=>v[k]);
          const depth=pts.reduce((a2,pp)=>a2+pp.d,0)/pts.length;
          faces.push({pts,depth,color:gpShade(se.color,normalLight(q.nrm[0],q.nrm[1],q.nrm[2]),0.94)});
        });
        labels.push({pt:{x:(v[4].x+v[6].x)/2,y:(v[4].y+v[6].y)/2},value:raw});
      });
    });
    faces.sort((a,b)=>a.depth-b.depth);
    faces.forEach(f=>{
      ctx.beginPath();
      ctx.moveTo(f.pts[0].x,f.pts[0].y);
      for(let k=1;k<f.pts.length;k++)ctx.lineTo(f.pts[k].x,f.pts[k].y);
      ctx.closePath();
      ctx.fillStyle=f.color;ctx.fill();
      ctx.strokeStyle=light?'rgba(255,255,255,.55)':'rgba(255,255,255,.12)';
      ctx.lineWidth=0.7;ctx.stroke();
    });
    if(n*m<=12){
      ctx.font='800 8px Inter,sans-serif';
      ctx.textAlign='center';ctx.textBaseline='bottom';
      ctx.fillStyle=light?'#31465c':'#c6d8ec';
      labels.forEach(l=>ctx.fillText(d.format?d.format(l.value):String(Math.round(l.value)),l.pt.x,l.pt.y-4));
    }
    /* category labels along the front edge */
    ctx.font='700 9px Inter,sans-serif';
    ctx.textAlign='center';ctx.textBaseline='top';
    ctx.fillStyle=txt;
    const every=Math.ceil(n/12);
    d.categories.forEach((cat,i)=>{
      if(i%every)return;
      const pt=P(-1+(2/n)*(i+0.5),0,0.74);
      const label=String(cat);
      ctx.fillText(label.length>12?label.slice(0,11)+'…':label,pt.x,pt.y+3);
    });
    if(d.axisLabel){
      ctx.textAlign='center';ctx.textBaseline='bottom';
      ctx.fillStyle=txt;ctx.font='800 9px Inter,sans-serif';
      ctx.fillText(d.axisLabel,box.w/2,box.h-4);
    }
  }
  /* rotate / zoom */
  stage.addEventListener('pointerdown',e=>{
    st.drag={x:e.clientX,y:e.clientY};
    stage.classList.add('is-drag');
    stage.setPointerCapture?.(e.pointerId);
  });
  stage.addEventListener('pointermove',e=>{
    if(!st.drag)return;
    st.yaw+=(e.clientX-st.drag.x)*0.0095;
    st.pitch=Math.max(0.1,Math.min(1.15,st.pitch+(e.clientY-st.drag.y)*0.006));
    st.drag={x:e.clientX,y:e.clientY};
    schedule();
  });
  const stop=()=>{st.drag=null;stage.classList.remove('is-drag')};
  stage.addEventListener('pointerup',stop);
  stage.addEventListener('pointerleave',stop);
  stage.addEventListener('pointercancel',stop);
  stage.addEventListener('wheel',e=>{
    e.preventDefault();
    st.zoom=Math.max(0.6,Math.min(1.9,st.zoom*(e.deltaY<0?1.08:0.93)));
    schedule();
  },{passive:false});
  window.addEventListener('resize',schedule);
  window.addEventListener('gridpoint:themechange',schedule);
  function spinLoop(){
    if(!st.spin)return;
    st.yaw+=0.004;
    draw();
    requestAnimationFrame(spinLoop);
  }
  return {
    setData(data){st.data=data;schedule()},
    reset(){st.yaw=-0.62;st.pitch=0.5;st.zoom=1;schedule()},
    setSpin(on){st.spin=on;if(on)requestAnimationFrame(spinLoop);else schedule()},
    redraw:schedule
  };
}
const gpCostCube=gpCube('costCube','costCubeStage');
const gpSiteCube=gpCube('siteCube','siteCubeStage');
function gpMoneyShort(v){
  const n=num(v);
  if(Math.abs(n)>=10000000)return '₹'+(n/10000000).toFixed(1)+'Cr';
  if(Math.abs(n)>=100000)return '₹'+(n/100000).toFixed(1)+'L';
  if(Math.abs(n)>=1000)return '₹'+Math.round(n/1000)+'k';
  return '₹'+Math.round(n);
}
function gpLegend(id,series){
  const el=document.getElementById(id);
  if(!el)return;
  el.innerHTML=series.map(x=>'<span><i style="background:'+x.color+'"></i>'+esc(x.name)+'</span>').join('');
}
function render3DAnalytics(data){
  const light=currentTheme()==='light';
  const points=data.tradeoff_points||[];
  const status=document.getElementById('analytics3dStatus');
  const caption=document.getElementById('analytics3dCaption');
  if(gpCostCube&&points.length){
    const series=[
      {name:'Annual total',color:light?'#2478e5':'#4ea1ff',values:points.map(p=>num(p.annual_total_cost))},
      {name:'Delivery + fuel',color:light?'#13a58a':'#34d399',values:points.map(p=>num(p.daily_delivery_cost)*365)},
      {name:'Warehouse opening',color:light?'#c47a17':'#fbbf24',values:points.map(p=>num(p.opening_cost))}
    ];
    gpCostCube.setData({categories:points.map(p=>'K='+p.k),series,format:gpMoneyShort,axisLabel:'network size (K warehouses)'});
    gpLegend('costCubeLegend',series);
    const empty=document.getElementById('costCubeEmpty');if(empty)empty.style.display='none';
  }
  const sites=[...(data.warehouses||[])].sort((a,b)=>num(b.assigned_orders)-num(a.assigned_orders)).slice(0,10);
  if(gpSiteCube&&sites.length){
    const cap=num(data.summary?.capacity_per_warehouse);
    const series=[
      {name:'Assigned orders / day',color:light?'#2478e5':'#67e8f9',values:sites.map(w=>num(w.assigned_orders))},
      {name:'Spare capacity',color:light?'#7358d2':'#a78bfa',values:sites.map(w=>Math.max(0,cap-num(w.assigned_orders)))}
    ];
    gpSiteCube.setData({categories:sites.map(w=>w.name),series,format:v=>Math.round(v).toLocaleString('en-IN'),axisLabel:'selected warehouses'});
    gpLegend('siteCubeLegend',series);
    const empty=document.getElementById('siteCubeEmpty');if(empty)empty.style.display='none';
  }
  if(status)status.textContent=points.length+' network sizes · '+sites.length+' selected sites · drag any view to rotate';
  if(caption)caption.textContent='Rendered from the same optimization run as the tables above. Height is the value, depth is the measure, width is the network size or site.';
}
function downloadAnalyticsCsv(){
  if(!optState.lastResult){toast('Run the optimizer first.');return}
  const d=optState.lastResult;
  const rows=[['View','Category','Measure','Value']];
  (d.tradeoff_points||[]).forEach(p=>{
    rows.push(['Cost landscape','K='+p.k,'Annual total cost',num(p.annual_total_cost).toFixed(2)]);
    rows.push(['Cost landscape','K='+p.k,'Delivery + fuel (annual)',(num(p.daily_delivery_cost)*365).toFixed(2)]);
    rows.push(['Cost landscape','K='+p.k,'Warehouse opening cost',num(p.opening_cost).toFixed(2)]);
  });
  const cap=num(d.summary?.capacity_per_warehouse);
  (d.warehouses||[]).forEach(w=>{
    rows.push(['Warehouse load',w.name,'Assigned orders / day',num(w.assigned_orders).toFixed(0)]);
    rows.push(['Warehouse load',w.name,'Spare capacity',Math.max(0,cap-num(w.assigned_orders)).toFixed(0)]);
    rows.push(['Warehouse load',w.name,'Utilization %',num(w.utilization_pct).toFixed(2)]);
  });
  gpSaveCsv(rows,'gridpoint-3d-analytics.csv','3D analytics CSV downloaded.');
}
function gpSaveCsv(rows,filename,message){
  const csv=rows.map(r=>r.map(v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"').join(',')).join('\n');
  const blob=new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=filename;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),600);
  toast(message||'CSV downloaded.');
}
document.getElementById('analytics3dCsv')?.addEventListener('click',downloadAnalyticsCsv);
document.getElementById('analytics3dReset')?.addEventListener('click',()=>{gpCostCube?.reset();gpSiteCube?.reset()});
document.getElementById('analytics3dSpin')?.addEventListener('click',e=>{
  const on=!e.currentTarget.classList.contains('active');
  e.currentTarget.classList.toggle('active',on);
  e.currentTarget.textContent=on?'Stop rotation':'Auto-rotate';
  gpCostCube?.setSpin(on);gpSiteCube?.setSpin(on);
});

/* ================================================================
   Maths & Logic CSV — the formulas plus the live model values
   ================================================================ */
const GP_MATH_ROWS=[
  ['01','Demand growth','New Orders = Original Orders x (1 + Growth)','500 daily orders at 10% growth become 550.'],
  ['02','Distance','d = 2R asin(sqrt(sin^2(dphi/2) + cos(phi1) cos(phi2) sin^2(dlambda/2)))','Haversine distance between a demand point and a warehouse.'],
  ['03','Delivery cost','Delivery = Orders x Distance x Variable cost','More orders or longer distance raise the daily delivery cost.'],
  ['04','Fuel / energy cost','Fuel = Orders x Distance / Efficiency x Fuel price','Vehicle efficiency and fuel price set the extra operating cost.'],
  ['05','Objective','Annual total = (Daily delivery + Daily penalty) x 365 + Opening cost','The optimizer minimizes this value.'],
  ['06','Capacity constraint','Assigned orders <= Warehouse capacity','A warehouse never takes more orders than its capacity.'],
  ['07','Service radius','Assignment distance <= Maximum radius','A demand point is feasible inside the allowed radius.'],
  ['08','Coverage','Coverage % = Feasible orders / Total orders x 100','Share of demand served with no constraint violation.'],
  ['09','Utilization','Utilization % = Assigned orders / Capacity x 100','800 orders in a 1,000-order site is 80% utilization.'],
  ['10','Optimization logic','Demand -> Candidates -> Distance matrix -> Feasible assignments -> Cost -> Best network','MILP where eligible, otherwise a constraint-aware heuristic.']
];
function downloadMathLogicCsv(){
  const rows=[['Section','#','Concept','Formula','Explanation']];
  GP_MATH_ROWS.forEach(r=>rows.push(['Maths & Logic',r[0],r[1],r[2],r[3]]));
  const d=optState.lastResult;
  if(d){
    const s=d.summary||{},c=d.costs||{},r=d.recommendation||{},b=d.baseline||{};
    const live=[
      ['Recommended warehouses (K)',num(r.recommended_k)],
      ['Selected warehouses',num(s.warehouse_count)],
      ['Total demand / day',num(s.total_orders_per_day)],
      ['Capacity per warehouse',num(s.capacity_per_warehouse)],
      ['Service radius (km)',num(s.radius_km)],
      ['Weighted distance (order-km/day)',num(s.weighted_distance_km).toFixed(2)],
      ['Daily delivery cost (INR)',num(c.daily_delivery_cost).toFixed(2)],
      ['Annual total cost (INR)',num(c.annual_total_cost).toFixed(2)],
      ['Baseline annual cost (INR)',num(b.annual_total_cost).toFixed(2)],
      ['Modeled saving (%)',num(s.savings_pct).toFixed(2)],
      ['Coverage (%)',num(s.coverage_pct).toFixed(2)],
      ['Average utilization (%)',num(s.capacity_utilization_avg_pct).toFixed(2)],
      ['Average drive time (min)',num(s.avg_drive_minutes).toFixed(2)],
      ['Vehicle',s.vehicle||''],
      ['Traffic',s.traffic||''],
      ['Solver',s.solver||d.diagnostics?.solver||'']
    ];
    live.forEach(x=>rows.push(['Live model value','','',x[0],x[1]]));
  }else{
    rows.push(['Live model value','','','Status','Run the optimizer to include live values in this export.']);
  }
  gpSaveCsv(rows,'gridpoint-maths-and-logic.csv','Maths & Logic CSV downloaded.');
}

/* ================================================================
   Guided tour · runs once per visitor unless it is skipped
   ================================================================ */
if(localStorage.getItem('gridpoint-tour-release')!=='v10'){
  localStorage.setItem('gridpoint-tour-release','v10');
  localStorage.removeItem(OPTIMIZER_TOUR_SKIP_KEY);
  localStorage.removeItem(OPTIMIZER_TOUR_SEEN_KEY);
}
optimizerTourSteps.push(
  {target:'optimizer3dToggle',title:'7 · 3D network map',text:'The map draws every demand point and selected warehouse as an extruded column, so height shows daily orders. Switch back to Flat any time.',side:'bottom'},
  {target:'analytics3dSection',title:'8 · 3D data analytics',text:'After a run, the cost landscape and warehouse load are rendered as rotatable 3D charts. Drag to rotate, scroll to zoom.',side:'top'},
  {target:'maths-logic',title:'9 · Maths & Logic',text:'Every formula behind the result is listed here, and the CSV button exports the formulas together with the live model values.',side:'top'}
);
const gpTourProgress=document.querySelector('.optimizer-tour-progress');
if(gpTourProgress)gpTourProgress.innerHTML=optimizerTourSteps.map(()=>'<i></i>').join('');
const gpTourLaunch=document.getElementById('optimizerTourLaunch');
if(gpTourLaunch&&localStorage.getItem(OPTIMIZER_TOUR_SEEN_KEY)!=='1')gpTourLaunch.classList.add('tour-pending');
document.addEventListener('keydown',e=>{
  const open=document.getElementById('optimizerTour')?.classList.contains('is-open');
  if(!open)return;
  if(e.key==='Escape')closeOptimizerTour(false);
  if(e.key==='ArrowRight')advanceOptimizerTour(1);
  if(e.key==='ArrowLeft')advanceOptimizerTour(-1);
});
/* second attempt in case the first fired before the layout settled */
setTimeout(()=>{
  const el=document.getElementById('optimizerTour');
  if(el&&!el.classList.contains('is-open'))openOptimizerTour(false);
},1500);

/* prime the 3D layer with whatever demand is already loaded */
setTimeout(()=>{
  if(!optState.lastResult&&optState.uploadRows?.length)gp3DSetPoints(optState.uploadRows,[],[]);
},900);

/* ================================================================
   Map labels toggle
   ================================================================ */
const gpLabelsBtn=document.getElementById('mapLabelsToggle');
function gpSyncLabelsBtn(){
  if(!gpLabelsBtn)return;
  const on=gpShowLabels();
  gpLabelsBtn.classList.toggle('active',on);
  gpLabelsBtn.setAttribute('aria-pressed',String(on));
  gpLabelsBtn.textContent=on?'\u2691 Labels on':'\u2691 Labels';
}
if(gpLabelsBtn){
  gpSyncLabelsBtn();
  gpLabelsBtn.addEventListener('click',()=>{
    localStorage.setItem('gridpoint-map-labels',gpShowLabels()?'0':'1');
    gpSyncLabelsBtn();
    if(optState.lastResult)drawMap(optState.lastResult);
    else if(optState.uploadRows?.length)showDemandPreview(optState.uploadRows);
  });
}

/* ================================================================
   Warehouse count quick picker (Network settings)
   ================================================================ */
function gpCountOptions(){
  const max=Math.max(1,Math.min(100,optState.uploadRows?.length||100));
  const base=[1,2,3,4,5,6,8,10];
  return base.filter(v=>v<=max);
}
function gpRenderCountPicker(){
  const grid=document.getElementById('whCountGrid');
  if(!grid)return;
  const mode=document.getElementById('selectionMode')?.value||'auto';
  const current=Number(document.getElementById('maxWarehouses')?.value||3);
  const opts=gpCountOptions();
  grid.innerHTML='<button type="button" class="wh-count-btn wide'+(mode==='auto'?' active':'')+'" data-count="auto">Auto</button>'
    +opts.map(v=>'<button type="button" class="wh-count-btn'+(mode==='exact'&&current===v?' active':'')+'" data-count="'+v+'">'+v+'</button>').join('')
    +'<button type="button" class="wh-count-btn wide" data-count="more">More \u2026</button>';
  grid.querySelectorAll('[data-count]').forEach(btn=>btn.addEventListener('click',()=>gpPickCount(btn.dataset.count)));
  const state=document.getElementById('whCountState');
  if(state)state.textContent=mode==='auto'?'AUTO':'EXACT \u00b7 '+current;
  const foot=document.getElementById('whCountFoot');
  const field=document.getElementById('warehouseCountField');
  if(field)field.style.display=mode==='exact'?'block':'none';
  if(foot)foot.textContent=mode==='auto'
    ? 'Auto lets GRIDPOINT search for the best K across every feasible network size.'
    : 'Locked to '+current+' warehouse'+(current===1?'':'s')+'. The slider below fine-tunes the exact count up to '+Math.max(1,Math.min(100,optState.uploadRows?.length||100))+'.';
}
function gpPickCount(value){
  const mode=document.getElementById('selectionMode');
  const slider=document.getElementById('maxWarehouses');
  if(!mode||!slider)return;
  if(value==='auto'){
    mode.value='auto';
    syncSelectionMode();
    gpRenderCountPicker();
    toast('Auto mode: GRIDPOINT will recommend the network size.');
    return;
  }
  if(value==='more'){
    mode.value='exact';
    syncSelectionMode();
    gpRenderCountPicker();
    document.getElementById('warehouseCountField')?.scrollIntoView({behavior:'smooth',block:'center'});
    slider.focus();
    toast('Use the slider to set any count up to '+slider.max+'.');
    return;
  }
  const max=Number(slider.max||100);
  mode.value='exact';
  syncSelectionMode();
  slider.value=String(Math.min(max,Math.max(1,Number(value))));
  syncRange('maxWarehouses');
  gpRenderCountPicker();
}
document.getElementById('selectionMode')?.addEventListener('change',gpRenderCountPicker);
document.getElementById('maxWarehouses')?.addEventListener('input',gpRenderCountPicker);
const gpOrigSyncLimit=syncOptimizerDataLimit;
syncOptimizerDataLimit=function(){gpOrigSyncLimit();gpRenderCountPicker()};
gpRenderCountPicker();

/* CSV shortcut in the page header */
document.getElementById('downloadMathCsvTop')?.addEventListener('click',downloadMathLogicCsv);

/* ================================================================
   Preview markers use the same visualizer styling before a run
   ================================================================ */
function gpDrawPreview(rows,focus){
  if(!optState.map)return;
  gpLayers();
  clearMapLayer(optState.neighborhoodLayer);clearMapLayer(optState.labelLayer);
  clearMapLayer(optState.lines);clearMapLayer(optState.catchmentLayer);clearMapLayer(optState.territoryLayer);
  const points=rows||[];
  const maxOrders=Math.max(1,...points.map(n=>num(n.orders)));
  const labelsOn=gpShowLabels();
  points.forEach(n=>{
    const radius=6+(num(n.orders)/maxOrders)*12;
    const m=L.circleMarker([num(n.lat),num(n.lon)],{radius,color:'#94a3b8',fillColor:'#4ea1ff',fillOpacity:.6,weight:1.4}).addTo(optState.map);
    m.bindTooltip(gpMapTooltip([
      ['Location',num(n.lat).toFixed(4)+', '+num(n.lon).toFixed(4)],
      ['Daily demand',num(n.orders).toLocaleString('en-IN')+' orders'],
      ['Cluster','Run the optimizer']
    ],esc(n.name)),{className:'leaflet-custom-tooltip',sticky:true});
    optState.neighborhoodLayer.push(m);
    if(labelsOn){
      const icon=L.divIcon({className:'nb-label',html:'<div style="border-color:#4ea1ff88;background:#4ea1ff22">'+esc(n.name)+'<span style="color:#67e8f9">'+num(n.orders).toLocaleString('en-IN')+' ord</span></div>',iconAnchor:[0,0]});
      optState.labelLayer.push(L.marker([num(n.lat),num(n.lon)],{icon,interactive:false,zIndexOffset:-10}).addTo(optState.map));
    }
  });
  const legend=document.getElementById('clusterLegend');
  if(legend)legend.innerHTML='';
  if(points.length)optState.map.fitBounds(L.latLngBounds(points.map(n=>[num(n.lat),num(n.lon)])).pad(0.15),{maxZoom:12});
  else if(focus)optState.map.setView(focus,11,{animate:false});
  setTimeout(()=>optState.map.invalidateSize({pan:false}),60);
}
showDemandPreview=function(rows,focus){gpDrawPreview(rows,focus);gp3DSetPoints(rows||[],[],[])};
if(optState.uploadRows?.length&&optState.map)gpDrawPreview(optState.uploadRows);

/* ---- keep analytics + 3D map in sync with every optimization ---- */
const gpOrigRenderResult=renderResult;
renderResult=function(data){
  gpOrigRenderResult(data);
  try{render3DAnalytics(data)}catch(err){console.warn('3D analytics',err)}
};

{% endif %}
{% if active == 'locations' %}
const cityData={{ cities|tojson }};
const locationState={rows:[],result:null,custom:false,layers:[],lines:[]};
const locMap=mapFactory('locationsMap',22.5,79.0,4.7);const cityEntries=Object.entries(cityData);
function clearLocationVisuals(){locationState.layers.forEach(x=>{try{locMap.removeLayer(x)}catch(e){}});locationState.layers=[];locationState.lines=[]}
function drawNetworkTable(rows){const list=rows&&rows.length?rows:[{name:'Whitefield',lat:12.9698,lon:77.7499,orders:2400},{name:'Indiranagar',lat:12.9784,lon:77.6408,orders:1800},{name:'Electronic City',lat:12.8458,lon:77.6602,orders:3200}];const body=document.getElementById('networkTableBody');if(!body)return;body.innerHTML=list.map((r,i)=>`<div class="demand-editor-row" data-row="${i}"><span class="demand-row-index">${i+1}</span><input class="n-name" value="${esc(r.name||'')}" placeholder="Whitefield"><input class="n-lat" value="${esc(r.lat??'')}" placeholder="12.9698" inputmode="decimal"><input class="n-lon" value="${esc(r.lon??'')}" placeholder="77.7499" inputmode="decimal"><input class="n-orders" value="${esc(r.orders??'')}" placeholder="2400" inputmode="numeric"><button class="demand-remove" type="button" data-network-remove="${i}" aria-label="Remove location">×</button></div>`).join('');body.querySelectorAll('[data-network-remove]').forEach(b=>b.addEventListener('click',()=>{b.closest('.demand-editor-row')?.remove();locationState.custom=true;syncNetworkDataLimit();updateNetworkEditorMeta()}));body.querySelectorAll('input').forEach(inp=>inp.addEventListener('input',()=>{locationState.custom=true;syncNetworkDataLimit();updateNetworkEditorMeta()}));syncNetworkDataLimit();updateNetworkEditorMeta()}
function updateNetworkEditorMeta(){const rows=readNetworkTable();const meta=document.getElementById('networkEditorMeta');if(meta)meta.textContent=`${rows.length} editable locations · max ${Math.min(100,Math.max(1,rows.length||100))} warehouses`}
function readNetworkTable(){return [...document.querySelectorAll('#networkTableBody .demand-editor-row')].map(r=>({name:r.querySelector('.n-name')?.value.trim()||'',lat:r.querySelector('.n-lat')?.value.trim()||'',lon:r.querySelector('.n-lon')?.value.trim()||'',orders:r.querySelector('.n-orders')?.value.trim()||''})).filter(r=>r.name||r.lat||r.lon||r.orders)}
function formatNetworkRange(id,value){if(id==='networkCapacity')return Number(value).toLocaleString('en-IN');if(id==='networkRadius')return `${value} km`;return value}
function updateNetworkRangeScale(id){const e=document.getElementById(id);if(!e)return;const scale=e.closest('.network-setting')?.querySelector('.range-scale');if(!scale)return;const max=Number(e.max||100);const vals=[Number(e.min||1),Math.round(max*.25),Math.round(max*.5),Math.round(max*.75),max];scale.innerHTML=vals.map(v=>`<span>${id==='networkRadius'?`${v} km`:v>=1000?`${(v/1000).toFixed(v%1000?1:0)}k`:v.toLocaleString('en-IN')}</span>`).join('')}
function syncNetworkRange(id){const e=document.getElementById(id);if(!e)return;const min=Number(e.min||0),max=Number(e.max||100);let value=Math.min(max,Math.max(min,Number(e.value||0)));e.value=String(value);const pct=((value-min)/Math.max(1,max-min))*100;e.style.setProperty('--range-pct',`${pct}%`);const stage=e.closest('.range-stage');if(stage){stage.style.setProperty('--range-pct',`${pct}%`);let fl=stage.querySelector('.range-float');if(!fl){fl=document.createElement('span');fl.className='range-float';stage.appendChild(fl)}fl.textContent=formatNetworkRange(id,value)}const out=document.getElementById(({networkCapacity:'networkCapacityValue',networkRadius:'networkRadiusValue'}[id]||''));if(out)out.textContent=formatNetworkRange(id,value);updateNetworkRangeScale(id)}
function syncNetworkDataLimit(){const manualRows=readNetworkTable();const count=locationState.custom?manualRows.length:(locationState.rows?.length||manualRows.length);const max=Math.min(100,Math.max(1,count||100));const status=document.getElementById('networkDataStatus');if(status&&count)status.textContent=`${count} locations · up to ${max} warehouses`;return max}
['networkCapacity','networkRadius'].forEach(id=>{document.getElementById(id)?.addEventListener('input',()=>syncNetworkRange(id));syncNetworkRange(id)});
document.getElementById('networkSelectionMode').addEventListener('change',()=>{document.getElementById('networkModeValue').textContent='Auto'});
function showRowsOnMap(rows,focus=null){clearLocationVisuals();if(!rows?.length)return;const bounds=[];rows.forEach(n=>{const radius=Math.max(4,Math.min(12,3.5+Math.sqrt(Math.max(0,n.orders))/5));const m=L.circleMarker([n.lat,n.lon],{radius,color:'#4ea1ff',fillColor:'#67e8f9',fillOpacity:.52,weight:1.2}).addTo(locMap).bindTooltip(`${esc(n.name)} · ${num(n.orders).toLocaleString('en-IN')} orders/day`);locationState.layers.push(m);bounds.push([n.lat,n.lon])});if(focus){const p=L.circleMarker([focus[0],focus[1]],{radius:9,color:'#67e8f9',fillColor:'#67e8f9',fillOpacity:.18,weight:2}).addTo(locMap).bindPopup('<b>Planning location</b>');locationState.layers.push(p);bounds.push(focus)}if(bounds.length)locMap.fitBounds(bounds,{padding:[35,35],maxZoom:12});setTimeout(()=>locMap.invalidateSize(),80)}
function showResultOnMap(result){showRowsOnMap(result.neighborhoods,result.location?.latitude!=null?[result.location.latitude,result.location.longitude]:null);const colors=['#67e8f9','#4ea1ff','#a78bfa','#fb7185','#34d399','#fbbf24','#38bdf8','#f472b6'];(result.warehouses||[]).forEach((w,i)=>{const color=colors[i%colors.length];const marker=L.circleMarker([w.lat,w.lon],{radius:10,color:'#ffffff',fillColor:color,fillOpacity:.92,weight:2}).addTo(locMap).bindPopup(`<b>${esc(w.name)}</b><br>${num(w.assigned_orders).toLocaleString('en-IN')} orders/day<br>${num(w.utilization_pct).toFixed(1)}% utilization`);locationState.layers.push(marker);const circle=L.circle([w.lat,w.lon],{radius:num(result.summary?.radius_km)*1000,color,weight:1,fillColor:color,fillOpacity:.035,dashArray:'5 7'}).addTo(locMap);locationState.layers.push(circle)});(result.assignments||[]).forEach(a=>{const color=a.feasible?'#4ea1ff':'#ff6b7d';const line=L.polyline([[a.neighborhood_lat,a.neighborhood_lon],[a.warehouse_lat,a.warehouse_lon]],{color,weight:a.feasible?1:2,opacity:a.feasible?.18:.55,dashArray:a.feasible?null:'4 4'}).addTo(locMap);locationState.lines.push(line)})}
function renderMarketList(filter=''){const q=filter.toLowerCase().trim();const filtered=cityEntries.filter(([name])=>name.toLowerCase().includes(q));document.getElementById('marketCountLabel').textContent=`${filtered.length} markets`;const box=document.getElementById('locationList');box.innerHTML=filtered.map(([name,c],i)=>`<div class="location-item network-market-enter" style="animation-delay:${Math.min(i*45,240)}ms"><div class="row"><strong>${esc(name)}</strong><span>${i<8?'Major market':'Indian market'}</span></div><div style="margin:5px 0 9px;color:#7189a3;font-size:10px">${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}</div><div style="display:flex;gap:6px"><button class="mini-btn market-analyze" data-market="${esc(name)}">Analyze network</button><button class="mini-btn market-open" data-market="${esc(name)}">Open model</button></div></div>`).join('')||'<div class="empty-state">No market matches that search.</div>';box.querySelectorAll('.market-analyze').forEach(btn=>btn.addEventListener('click',()=>analyzeMarket(btn.dataset.market)));box.querySelectorAll('.market-open').forEach(btn=>btn.addEventListener('click',()=>openOptimizerWithRows(cityRows(btn.dataset.market),btn.dataset.market)))}
async function cityRows(name){const d=await fetchJSON(`/api/locations?city=${encodeURIComponent(name)}`);return d.locations||[]}
function networkPayload(rows,label){const mode='auto';const limit=Math.min(100,Math.max(1,(rows||[]).length||100));return {city:label||'Custom India dataset',selectionMode:mode,maxWarehouses:limit,exactWarehouses:Math.min(4,limit),capacity:Number(document.getElementById('networkCapacity').value),openingCost:Number(document.getElementById('networkOpeningCost').value),radius:Number(document.getElementById('networkRadius').value),variableCost:12,fuelPrice:Number(document.getElementById('networkFuelPrice').value),vehicle:document.getElementById('networkVehicle').value,traffic:document.getElementById('networkTraffic').value,demandGrowth:0,neighborhoods:rows}}
async function optimizeRows(rows,label,custom=false){if(!rows?.length){toast('No valid demand data found.');return}locationState.rows=rows;locationState.custom=custom;drawNetworkTable(rows);showRowsOnMap(rows);document.getElementById('networkDataStatus').textContent=`${rows.length} locations loaded`;syncNetworkDataLimit();const labelEl=document.getElementById('marketPreviewLabel');const box=document.getElementById('marketPreview');labelEl.textContent=`${label||'Custom data'} · optimizing`;box.innerHTML='<div class="market-loading"><div class="loading-ring"></div><div><strong>Running GRIDPOINT</strong><span>Testing warehouse counts and constrained assignments with your network settings.</span></div></div>';try{const d=await fetchJSON('/api/optimize',{method:'POST',body:JSON.stringify(networkPayload(rows,label))});locationState.result=d;showResultOnMap(d);document.getElementById('networkOpenOptimizer').disabled=false;const ss=d.summary||{};const rr=d.recommendation||{};const dd=d.diagnostics||{};labelEl.textContent=`${label||'Custom data'} · optimized`;box.classList.remove('network-solution-replay');void box.offsetWidth;box.classList.add('network-solution-replay');box.innerHTML=`<div class="network-preview-grid"><div><span>Recommended K</span><strong>${num(rr.recommended_k)}</strong></div><div><span>Annual cost</span><strong>${money(d.costs?.annual_total_cost)}</strong></div><div><span>Coverage</span><strong>${num(ss.coverage_pct).toFixed(1)}%</strong></div><div><span>Avg distance</span><strong>${num(ss.avg_distance_per_order_km).toFixed(1)} km</strong></div><div><span>Resilience</span><strong>${num(ss.network_resilience_pct).toFixed(1)}%</strong></div></div><div class="market-actions"><span>${esc(rr.reason||'')}</span><span>${esc(dd.capacity_status||'')} · ${esc(dd.radius_status||'')} · ${esc(dd.solver||'')}</span></div>`;toast(`GRIDPOINT optimized ${label||'your network'} · ${num(rr.recommended_k)} warehouse${num(rr.recommended_k)===1?'':'s'}.`);setTimeout(()=>document.getElementById('marketPreview')?.scrollIntoView({behavior:'smooth',block:'center'}),120)}catch(e){box.innerHTML=`<div class="empty-state">${esc(e.message)}</div>`;labelEl.textContent=`${label||'Custom data'} · failed`;toast(e.message)}}
async function analyzeMarket(name){try{const city=cityData[name];if(city)locMap.setView([city.lat,city.lon],11);const rows=await cityRows(name);await optimizeRows(rows,name,false)}catch(e){toast(e.message)}}
function parseSimpleText(text){return fetchJSON('/api/parse-data',{method:'POST',body:JSON.stringify({text:String(text||'').trim()})})}
async function useNetworkTable(){try{const rows=readNetworkTable();if(!rows.length){toast('Add at least one location.');return}const d=await parseSimpleText(['name,latitude,longitude,daily_orders',...rows.map(r=>[r.name,r.lat,r.lon,r.orders].join(','))].join('\n'));document.getElementById('networkUploadStatus').innerHTML=`<div class="network-file-status"><span>✓</span><div><strong>Data accepted successfully</strong>${d.count} valid locations are ready. GRIDPOINT is optimizing now.</div></div>`;localStorage.setItem('gridpoint-demand-rows',JSON.stringify(d.rows));localStorage.setItem('gridpoint-demand-label','Entered demand dataset');localStorage.setItem('gridpoint-demand-filename','Entered on GRIDPOINT');await optimizeRows(d.rows,'Entered demand',true)}catch(e){toast(e.message)}}
function openOptimizerWithRows(rowsOrPromise,label){Promise.resolve(rowsOrPromise).then(rows=>{localStorage.setItem('gridpoint-demand-rows',JSON.stringify(rows));localStorage.setItem('gridpoint-demand-label',label);window.location='/optimizer?imported=1'})}
async function loadPresetDataset(city,runOptimization=true){try{document.querySelectorAll('.dataset-preset').forEach(b=>b.classList.toggle('active',b.dataset.preset===city));const rows=await cityRows(city);locationState.rows=rows;locationState.custom=false;drawNetworkTable(rows);showRowsOnMap(rows,[cityData[city].lat,cityData[city].lon]);document.getElementById('networkDataStatus').textContent=`${city} demo ready · ${rows.length} locations`;document.getElementById('networkDatasetHint').textContent=`${rows.length} demand zones are loaded. Change rows or network settings, then optimize.`;if(runOptimization)await optimizeRows(rows,city,false)}catch(e){toast(e.message)}}

document.getElementById('networkAddRow').addEventListener('click',()=>{const rows=readNetworkTable();rows.push({name:'',lat:'',lon:'',orders:''});locationState.custom=true;drawNetworkTable(rows);const last=document.querySelector('#networkTableBody .demand-editor-row:last-child .n-name');last?.focus();last?.scrollIntoView({behavior:'smooth',block:'center'});syncNetworkDataLimit()});
document.getElementById('networkUseManual').addEventListener('click',useNetworkTable);
document.querySelectorAll('.dataset-preset').forEach(btn=>btn.addEventListener('click',()=>loadPresetDataset(btn.dataset.preset,true)));
document.getElementById('networkOptimizeButton').addEventListener('click',async e=>{
  const btn=e.currentTarget,label=btn.textContent;
  const rows=readNetworkTable();
  const use=rows.length?rows:(locationState.rows||[]);
  if(!use.length){toast('Add demand rows or pick a dataset first.');return}
  btn.disabled=true;btn.textContent='Optimizing network…';
  try{await optimizeRows(use,'Current network',locationState.custom)}
  finally{btn.disabled=false;btn.textContent=label;document.querySelector('.network-reveal-solution')?.scrollIntoView({behavior:'smooth',block:'center'})}
});
document.getElementById('networkResetSettings').addEventListener('click',()=>{document.getElementById('networkSelectionMode').value='auto';document.getElementById('networkCapacity').value=1500;document.getElementById('networkRadius').value=35;document.getElementById('networkVehicle').value='car';document.getElementById('networkTraffic').value='medium';document.getElementById('networkOpeningCost').value=4000000;document.getElementById('networkFuelPrice').value=100;syncNetworkDataLimit();syncNetworkRange('networkCapacity');syncNetworkRange('networkRadius');document.getElementById('networkModeValue').textContent='Auto';toast('Network settings restored.')});
async function gpLoadNetworkCsv(file){
  if(!file)return;
  const fn=document.getElementById('networkFileName');if(fn)fn.textContent=file.name;
  try{
    const text=await file.text();
    const d=await parseSimpleText(text);
    const status=document.getElementById('networkUploadStatus');
    if(status)status.innerHTML=`<div class="network-file-status"><span>✓</span><div><strong>File loaded successfully</strong>${esc(file.name)} · ${d.count} valid locations. Processing your network now.</div></div>`;
    localStorage.setItem('gridpoint-demand-rows',JSON.stringify(d.rows));
    localStorage.setItem('gridpoint-demand-label',file.name);
    localStorage.setItem('gridpoint-demand-filename',file.name);
    locationState.rows=d.rows;locationState.custom=true;
    drawNetworkTable(d.rows);
    toast(`CSV loaded · ${d.count} locations ready.`);
    await optimizeRows(d.rows,file.name,true);
  }catch(err){
    const status=document.getElementById('networkUploadStatus');
    if(status)status.innerHTML='';
    toast(err.message);
  }
}
document.getElementById('networkCsvInput').addEventListener('change',e=>{gpLoadNetworkCsv(e.target.files[0]);e.target.value=''});
document.getElementById('networkCsvInputTop')?.addEventListener('change',e=>{gpLoadNetworkCsv(e.target.files[0]);e.target.value=''});
document.getElementById('networkOpenOptimizer').addEventListener('click',()=>{if(locationState.rows.length)openOptimizerWithRows(locationState.rows,document.getElementById('marketPreviewLabel').textContent.split(' · ')[0])});
document.getElementById('downloadTemplate').addEventListener('click',()=>{const text='name,latitude,longitude,daily_orders\nWhitefield,12.9698,77.7499,2400\nIndiranagar,12.9784,77.6408,1800\nElectronic City,12.8458,77.6602,3200';const blob=new Blob([text],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='gridpoint-demand-template.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500)});
cityEntries.forEach(([name,c])=>{const m=L.circleMarker([c.lat,c.lon],{radius:5,color:'#4ea1ff',fillColor:'#67e8f9',fillOpacity:.5,weight:1.2}).addTo(locMap);m.bindTooltip(name);m.on('click',()=>loadPresetDataset(name,true))});
renderMarketList();document.getElementById('marketSearch').addEventListener('input',e=>renderMarketList(e.target.value));
loadPresetDataset('Bengaluru',false);
/* ================================================================
   Warehouse Network guided tour
   Three steps: dataset, network settings (auto K), and
   the Run & optimize button. Auto-runs once per visitor unless
   skipped, same behaviour as the Optimizer tour.
   ================================================================ */
const networkTourSteps=[
  {target:'datasetPresets',title:'1 \u00b7 Choose a dataset',text:'Pick a ready city demo, load your own CSV with the button up top, or edit rows directly in the table below \u2014 every path feeds the same optimizer.',side:'bottom'},
  {target:'networkSelectionMode',title:'2 \u00b7 Network settings',text:'Warehouse Network runs in auto mode: GRIDPOINT tests different network sizes and picks the best number of warehouses for you. Adjust capacity, radius, vehicle and cost settings around it.',side:'right'},
  {target:'networkOptimizeButton',title:'3 \u00b7 Run & optimize',text:'This solves the same constrained model as the full Optimizer using the network settings and demand above. The result appears just below the map.',side:'top'}
];
let networkTourIndex=0;
function positionNetworkTour(){
  const tour=document.getElementById('networkTour'),spot=document.getElementById('networkTourSpotlight'),card=document.getElementById('networkTourCard');
  const step=networkTourSteps[networkTourIndex];const target=document.getElementById(step.target);if(!tour||!spot||!card||!target)return;
  const r=target.getBoundingClientRect(),pad=8;
  spot.style.top=`${Math.max(10,r.top-pad)}px`;spot.style.left=`${Math.max(10,r.left-pad)}px`;spot.style.width=`${r.width+pad*2}px`;spot.style.height=`${r.height+pad*2}px`;
  let left=r.right+16,top=r.top,side='right';
  if(step.side==='top'){left=r.left;top=r.top-card.offsetHeight-16;side='top'}
  if(step.side==='bottom'){left=r.left;top=r.bottom+16;side='bottom'}
  if(left+card.offsetWidth>window.innerWidth-14){left=Math.max(14,r.left-card.offsetWidth-16);side='left'}
  if(top<14){top=Math.min(window.innerHeight-card.offsetHeight-14,r.bottom+16);side='bottom'}
  if(top+card.offsetHeight>window.innerHeight-14){top=Math.max(14,window.innerHeight-card.offsetHeight-14)}
  card.style.left=`${left}px`;card.style.top=`${top}px`;card.dataset.side=side;
  const kicker=document.getElementById('networkTourKicker'),title=document.getElementById('networkTourTitle'),text=document.getElementById('networkTourText');
  const dots=[...document.querySelectorAll('#networkTour .optimizer-tour-progress i')];
  if(kicker)kicker.textContent=`GUIDED TOUR \u00b7 ${networkTourIndex+1} OF ${networkTourSteps.length}`;
  if(title)title.textContent=step.title;if(text)text.textContent=step.text;dots.forEach((d,i)=>d.classList.toggle('is-active',i===networkTourIndex));
  const back=document.getElementById('networkTourBack'),next=document.getElementById('networkTourNext');
  if(back)back.style.visibility=networkTourIndex===0?'hidden':'visible';if(next)next.textContent=networkTourIndex===networkTourSteps.length-1?'Finish':'Next';
}
const NETWORK_TOUR_SKIP_KEY='gridpoint-network-tour-v1-skip';
const NETWORK_TOUR_SEEN_KEY='gridpoint-network-tour-v1-seen';
function closeNetworkTour(markSkipped=false){const el=document.getElementById('networkTour');if(!el)return;el.classList.remove('is-open');el.setAttribute('aria-hidden','true');document.body.classList.remove('tour-active');if(markSkipped)localStorage.setItem(NETWORK_TOUR_SKIP_KEY,'1')}
function finishNetworkTour(){localStorage.setItem(NETWORK_TOUR_SEEN_KEY,'1');closeNetworkTour(false)}
function openNetworkTour(force=false){
  const el=document.getElementById('networkTour');if(!el)return;
  if(!force&&(localStorage.getItem(NETWORK_TOUR_SKIP_KEY)==='1'||localStorage.getItem(NETWORK_TOUR_SEEN_KEY)==='1'))return;
  networkTourIndex=0;el.classList.add('is-open');el.setAttribute('aria-hidden','false');document.body.classList.add('tour-active');
  const target=document.getElementById(networkTourSteps[0].target);target?.scrollIntoView({behavior:'smooth',block:'center'});
  setTimeout(()=>positionNetworkTour(),360);
}
function advanceNetworkTour(delta){
  const nextIndex=Math.min(networkTourSteps.length-1,Math.max(0,networkTourIndex+delta));
  if(nextIndex===networkTourIndex){if(delta>0)finishNetworkTour();return}
  networkTourIndex=nextIndex;const target=document.getElementById(networkTourSteps[networkTourIndex].target);target?.scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>positionNetworkTour(),420);
}
document.getElementById('networkTourNext')?.addEventListener('click',()=>advanceNetworkTour(1));
document.getElementById('networkTourBack')?.addEventListener('click',()=>advanceNetworkTour(-1));
document.getElementById('networkTourClose')?.addEventListener('click',()=>closeNetworkTour(false));
document.getElementById('networkTourSkip')?.addEventListener('click',()=>closeNetworkTour(true));
document.querySelector('#networkTour .optimizer-tour-backdrop')?.addEventListener('click',()=>closeNetworkTour(false));
document.getElementById('networkTourLaunch')?.addEventListener('click',()=>openNetworkTour(true));
window.addEventListener('resize',()=>{if(document.getElementById('networkTour')?.classList.contains('is-open'))positionNetworkTour()});
window.addEventListener('scroll',()=>{if(document.getElementById('networkTour')?.classList.contains('is-open'))positionNetworkTour()},{passive:true});
document.addEventListener('keydown',e=>{
  const open=document.getElementById('networkTour')?.classList.contains('is-open');
  if(!open)return;
  if(e.key==='Escape')closeNetworkTour(false);
  if(e.key==='ArrowRight')advanceNetworkTour(1);
  if(e.key==='ArrowLeft')advanceNetworkTour(-1);
});
const networkTourLaunchBtn=document.getElementById('networkTourLaunch');
if(networkTourLaunchBtn&&localStorage.getItem(NETWORK_TOUR_SEEN_KEY)!=='1')networkTourLaunchBtn.classList.add('tour-pending');
setTimeout(()=>openNetworkTour(false),900);
{% endif %}
</script>
</body>
</html>
'''

HOME = r'''
<section class="hero">
  <div>
    <span class="eyebrow">● Warehouse network intelligence for India</span>
    <h1>Place warehouses <span>where the network works harder.</span></h1>
    <p>GRIDPOINT combines demand, distance, capacity, traffic and location signals to find a warehouse network that balances delivery effort and infrastructure cost.</p>
    <div class="hero-actions"><a class="btn primary" href="/locations">Warehouse network check for any business →</a><a class="btn ghost" href="#demo">See the workflow</a></div>
  </div>
  <div class="hero-card"><div class="home-map-head"><div><div class="home-map-title">GRIDPOINT network view</div><span class="home-map-sub">Demand clusters · candidate hubs · delivery reach</span></div><div class="home-map-actions"><button type="button" data-map-style="auto">Network</button><button type="button" data-map-style="satellite">Satellite</button><button type="button" data-map-style="light">Light</button></div></div><div class="home-map-shell"><div class="mini-map" id="homeMap"></div><div class="home-map-overlay"><div><span>Demand nodes</span><strong>25</strong></div><div><span>Objective</span><strong>Weighted</strong></div><div><span>Network</span><strong>Multi-site</strong></div><div><span>Road model</span><strong>Ready</strong></div></div></div><div class="home-map-bottom"><span><b>Demand</b> → candidate sites → optimized network</span><span>● Interactive demo</span></div><div class="hero-stat-row"><div class="mini-stat"><div class="k">Decision</div><strong>Best K</strong></div><div class="mini-stat"><div class="k">Constraint</div><strong>Capacity</strong></div><div class="mini-stat"><div class="k">Service</div><strong>Radius + ETA</strong></div></div></div>
</section>
<div class="section-title"><div><h2>What GRIDPOINT optimizes</h2><p>Every control changes the trade-off between fixed warehouse cost and delivery cost.</p></div></div>
<section class="grid4"><div class="card feature"><div class="feature-icon">01</div><h3>Demand-aware sites</h3><p>High-order neighborhoods get more weight when selecting candidate warehouse locations.</p></div><div class="card feature"><div class="feature-icon">02</div><h3>Multi-warehouse routing</h3><p>Use one site or spread demand across multiple warehouses, from one site to a practical 100-site warehouse plan.</p></div><div class="card feature"><div class="feature-icon">03</div><h3>Capacity & radius</h3><p>Control how much each warehouse can handle and how far it may serve a neighborhood.</p></div><div class="card feature"><div class="feature-icon">04</div><h3>Cost intelligence</h3><p>See baseline vs optimized delivery distance, opening cost and annual operating cost.</p></div></section>
<section id="demo" class="section-title"><div><h2>How to use GRIDPOINT</h2><p>A small interactive demo on the main page shows the same flow a judge will see in the real optimizer.</p></div></section>
<section class="demo-wrap"><div class="card demo-steps"><div class="step"><div class="step-num">1</div><div><h4>Choose a city or use your location</h4><p>Browser geolocation is optional. If permission is denied, city mode still works.</p></div></div><div class="step"><div class="step-num">2</div><div><h4>Load demand data</h4><p>Use the demo data or upload a CSV with neighborhood, latitude, longitude and daily orders.</p></div></div><div class="step"><div class="step-num">3</div><div><h4>Set network limits</h4><p>Adjust warehouse count, capacity, service radius, traffic and vehicle assumptions.</p></div></div><div class="step"><div class="step-num">4</div><div><h4>Run optimization</h4><p>GRIDPOINT compares your baseline network with the optimized network and explains the trade-off.</p></div></div></div><div class="card demo-panel"><div class="demo-header"><strong>GRIDPOINT mini demo</strong><button class="mini-btn" id="playDemo" type="button">Play demo</button></div><div class="demo-window"><div class="demo-window-bar"><i></i><i></i><i></i><span class="demo-window-title">GRIDPOINT · optimization run</span></div><div class="demo-window-body"><div class="demo-progress"><b id="demoProgress"></b></div><div class="demo-stage"><div class="demo-stage-card"><small id="demoStepLabel">Demand</small><strong id="demoStageValue">25</strong><span id="demoStageText">neighborhoods loaded</span></div><div class="demo-stage-card"><small>Result</small><strong id="demoResultValue">—</strong><span id="demoResultText">waiting for optimization</span></div></div><div class="demo-window-actions"><span id="demoHint">Load demand → choose K → optimize</span><a class="mini-btn" href="/locations">Warehouse network check</a></div></div></div></div></section>
<section class="section-title"><div><span class="eyebrow">● REAL-WORLD READY</span><h2>Built for an actual logistics decision.</h2><p>GRIDPOINT keeps the decision simple for an operator while leaving room to connect real demand and routing data behind the scenes.</p></div></section>
<section class="grid4"><div class="card feature"><div class="feature-icon">R1</div><h3>Fresh demand input</h3><p>Replace the demo with a CSV or connect your order system later. Every optimization run uses the current demand snapshot.</p></div><div class="card feature"><div class="feature-icon">R2</div><h3>Road-aware planning</h3><p>Use road distance and travel-time lookups instead of treating every location pair as a straight line.</p></div><div class="card feature"><div class="feature-icon">R3</div><h3>Operational guardrails</h3><p>Capacity, maximum service radius, delivery target, vehicle and traffic assumptions keep recommendations usable.</p></div><div class="card feature"><div class="feature-icon">R4</div><h3>Decision after the model</h3><p>Compare baseline vs optimized cost, inspect the top two sites, test shocks and export the decision result.</p></div></section>
<section class="section-title"><div><h2>What makes GRIDPOINT different</h2><p>Useful extensions that make the same optimization engine feel like a planning product, not only a map.</p></div></section>
<section class="grid4"><div class="card feature"><div class="feature-icon">05</div><h3>Failure simulation</h3><p>Remove a selected warehouse and estimate how much demand loses coverage.</p></div><div class="card feature"><div class="feature-icon">06</div><h3>Demand shock</h3><p>Stress-test the network before committing to new infrastructure.</p></div><div class="card feature"><div class="feature-icon">07</div><h3>SLA coverage</h3><p>Track the share of demand reachable inside a target delivery time.</p></div><div class="card feature"><div class="feature-icon">08</div><h3>Explainable decisions</h3><p>Show why a site was selected and what cost or distance it improves.</p></div></section>
'''

OPTIMIZER = r'''
<div class="page-head"><div><span class="eyebrow">● Network design studio</span><h1>Warehouse optimizer</h1><p>Use real coordinates, demand-weighted cost and constraint-aware optimization to build a warehouse network for any Indian market.</p></div><div class="page-head-actions"><span class="eyebrow" id="locationBadge">📍 Bengaluru · Demo ready</span><a class="btn ghost" href="#maths-logic">Maths &amp; Logic ↓</a><label class="btn ghost upload-btn" for="csvInputTop" title="Load a demand CSV (name, latitude, longitude, daily_orders)">↑ Load CSV<input class="upload-input-hidden" id="csvInputTop" type="file" accept=".csv,text/csv"></label><button class="btn ghost" id="downloadMathCsvTop" type="button" title="Download the maths, logic and live model values as CSV">⤓ CSV</button><a class="btn ghost" href="/locations">India network</a><button class="btn primary optimizer-run-top" id="optimizeBtnTop" type="button">Run optimization <span aria-hidden="true">→</span></button></div></div>
<div class="optimizer-layout">
  <aside class="card controls">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px"><h3>Network settings</h3><span class="solver-badge">Recommended defaults</span></div>
    <div class="location-card"><div class="control-kicker">Location access</div><div id="locationStatus" class="location-status">Waiting for optional browser location permission.</div><div class="location-actions"><button class="btn primary" id="detectLocation">Use my location</button><button class="btn ghost" id="clearLocation" type="button">Clear</button></div></div>
    <div class="field"><label>Search anywhere in India <span>live geocoding</span></label><div style="display:flex;gap:7px"><input class="input" id="locationQuery" placeholder="Whitefield, Bengaluru / Andheri, Mumbai" style="flex:1"><button class="btn ghost" id="searchLocation" type="button">Search</button></div><div class="field-help">Press Search or Enter. You can also click the map to choose a planning point.</div></div>
    <div class="warehouse-add-panel" id="warehouseAddPanel"><div class="warehouse-add-head"><strong>Custom warehouses</strong><span>add a site directly on the map</span></div><div class="warehouse-add-actions"><button class="btn primary" id="addWarehouseMode" type="button">+ Add warehouse</button><button class="btn ghost" id="clearWarehouses" type="button">Clear all</button></div><div class="field-help">Click <b>Add warehouse</b>, then click the map. The site is saved and included as a required warehouse in the next optimization.</div><div id="manualWarehouseList" class="warehouse-add-list"></div></div>
    <div class="field"><label>Market <span>demo baseline</span></label><select class="select" id="city">__CITY_OPTIONS__</select></div>
    <div class="field data-entry"><div class="optimizer-source-card"><div><div class="control-kicker">ACTIVE DEMAND SOURCE</div><h4 id="optimizerSourceTitle">Bengaluru demo</h4><p id="optimizerSourceMeta">25 locations · balanced demo demand ready.</p></div><a class="btn ghost" href="/locations">Manage demand →</a></div><div class="source-metrics"><div><span>Locations</span><strong id="optimizerSourceCount">—</strong></div><div><span>Orders / day</span><strong id="optimizerSourceOrders">—</strong></div><div><span>Data status</span><strong id="optimizerSourceStatus">Ready</strong></div></div><div class="field-help" style="margin-top:8px">Upload or edit demand in Warehouse Network. The optimizer keeps the selected dataset synchronized.</div></div>
    <div class="field"><label>Warehouse strategy <span>recommended</span></label><select class="select" id="selectionMode"><option value="auto" selected>Auto · let GRIDPOINT choose K</option><option value="exact">Exact · choose K yourself</option></select><div class="range-note"><span>Recommended for most networks</span><b>AUTO</b></div></div>
    <div class="wh-count-card" id="warehouseCountCard">
      <div class="wh-count-head"><strong>Warehouse count</strong><span id="whCountState">AUTO</span></div>
      <div class="wh-count-grid" id="whCountGrid"></div>
      <div class="wh-count-foot" id="whCountFoot">Auto lets GRIDPOINT search for the best K. Pick a number to lock the network size, or use More for larger networks.</div>
    </div>
    <div class="premium-range" id="warehouseCountField" style="margin-top:10px;display:none"><div class="range-head"><span class="range-title">NUMBER OF WAREHOUSES</span><b class="range-value" id="maxWhValue">3</b></div><div class="range-stage"><input class="range" id="maxWarehouses" type="range" min="1" max="100" value="3"><div class="range-scale"><span>1</span><span>25</span><span>50</span><span>75</span><span>100</span></div></div><div class="field-help">Choose the exact number of warehouses GRIDPOINT should place.</div></div>
    <div class="premium-range" style="margin-top:10px"><div class="range-head"><span class="range-title">MAX CAPACITY / WAREHOUSE</span><b class="range-value" id="capacityValue">5,000</b></div><div class="range-stage"><input class="range" id="capacity" type="range" min="500" max="50000" step="100" value="5000"><div class="range-scale"><span>500</span><span>10k</span><span>20k</span><span>35k</span><span>50k</span></div></div><div class="field-help">Maximum daily orders one warehouse can handle.</div></div>
    <div class="premium-range" style="margin-top:10px"><div class="range-head"><span class="range-title">MAX SERVICE RADIUS</span><b class="range-value" id="radiusValue">50 km</b></div><div class="range-stage"><input class="range" id="radius" type="range" min="10" max="200" step="5" value="50"><div class="range-scale"><span>10 km</span><span>50</span><span>100</span><span>150</span><span>200</span></div></div><div class="field-help">Maximum road-distance radius for an assignment.</div></div>
    <div class="premium-range" style="margin-top:10px"><div class="range-head"><span class="range-title">CUSTOMER DEMAND GROWTH</span><b class="range-value" id="growthValue">10%</b></div><div class="range-stage"><input class="range" id="growth" type="range" min="0" max="100" value="10"><div class="range-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div></div></div>
    <div class="premium-range sla-card"><div class="range-head"><span class="range-title">DELIVERY TARGET</span><b class="range-value" id="slaMinutesValue">45 min</b></div><div class="range-stage"><input class="range" id="slaMinutes" type="range" min="15" max="120" step="5" value="45"><div class="range-scale"><span>15m</span><span>30m</span><span>45m</span><span>60m</span><span>120m</span></div></div><div class="field-help">Share of daily demand reachable within the target time.</div></div>
    <div class="model-strip"><div class="model-chip"><b>Multi-site</b><i>ACTIVE</i></div><div class="model-chip"><b>Capacity</b><i>ENFORCED</i></div><div class="model-chip"><b>Radius</b><i>ENFORCED</i></div><div class="model-chip"><b>Vehicle</b><i>MODELED</i></div><div class="model-chip"><b>Traffic</b><i>ETA</i></div><div class="model-chip"><b>Trade-off</b><i>SEARCHED</i></div></div>
    <div class="scenario-row"><button class="mini-btn scenario" data-growth="0">Current</button><button class="mini-btn scenario" data-growth="10">+10%</button><button class="mini-btn scenario" data-growth="25">+25%</button><button class="mini-btn scenario" data-growth="50">+50%</button><button class="mini-btn scenario" data-growth="100">+100%</button></div>
    <div class="field"><label>Traffic <span>affects ETA</span></label><select class="select" id="traffic"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="peak">Peak</option></select></div>
    <div class="field"><label>Vehicle <span>operating model</span></label><select class="select" id="vehicle"><option value="bike">Bike</option><option value="car" selected>Car / Van</option><option value="ev">Electric Van</option><option value="truck">Mini Truck</option></select></div>
    <details class="advanced-settings"><summary>Advanced cost assumptions</summary><div class="advanced-body">
      <div class="field"><label>Delivery cost <span>₹ / order / km</span></label><input class="input" id="variableCost" type="number" min="0.1" step="0.5" value="12"></div>
      <div class="field"><label>Opening cost <span>₹ / warehouse</span></label><input class="input" id="openingCost" type="number" min="0" step="50000" value="4000000"></div>
      <div class="field"><label>Fuel / energy price <span>₹ / unit</span></label><input class="input" id="fuelPrice" type="number" min="1" step="1" value="100"></div>
    </div></details>
    <div class="field"><label>Demand file</label><label class="upload-label" for="csvInput"><span class="upload-icon">↥</span><span class="upload-copy"><strong>Upload demand CSV</strong><span id="fileName">Simple CSV · name, latitude, longitude, daily_orders</span></span><span class="upload-arrow">Choose</span></label><input class="upload-input" id="csvInput" type="file" accept=".csv,text/csv"></div>
    <div id="uploadSummary" class="upload-summary" style="display:none"></div>
    <div class="field-help" style="margin-top:8px;padding:10px 11px;border:1px dashed var(--line);border-radius:12px;background:rgba(78,161,255,.035)"><strong style="color:var(--text);display:block;margin-bottom:3px">Ready to optimize</strong>Use the single Run optimization button at the top-right when your settings are ready.</div>
    <button class="btn ghost optimize-main" id="downloadBtn" type="button">Download results CSV</button>
  </aside>
<div class="optimizer-tour" id="optimizerTour" aria-hidden="true"><div class="optimizer-tour-backdrop"></div><div class="optimizer-tour-spotlight" id="optimizerTourSpotlight"></div><div class="optimizer-tour-card" id="optimizerTourCard" role="dialog" aria-labelledby="optimizerTourTitle"><span class="optimizer-tour-arrow"></span><div class="optimizer-tour-top"><div><div class="optimizer-tour-kicker" id="optimizerTourKicker">GUIDED TOUR · 1 OF 6</div><h3 class="optimizer-tour-title" id="optimizerTourTitle">Choose your market</h3><p class="optimizer-tour-text" id="optimizerTourText">Start with a city, your detected location, or a planning point on the map.</p></div><button class="optimizer-tour-close" id="optimizerTourClose" type="button" aria-label="Close tour">×</button></div><div class="optimizer-tour-progress"><i></i><i></i><i></i><i></i><i></i><i></i></div><div class="optimizer-tour-footer"><button class="tour-skip" id="optimizerTourSkip" type="button">Skip tour</button><div class="optimizer-tour-actions"><button class="btn ghost" id="optimizerTourBack" type="button">Back</button><button class="btn primary" id="optimizerTourNext" type="button">Next</button></div></div></div></div>
  <section class="workspace">
    <div class="metrics"><div class="card metric"><div class="label">Annual total cost</div><strong id="totalCost">—</strong><small>delivery + opening + constraint penalties</small></div><div class="card metric"><div class="label">Daily weighted delivery</div><strong id="dailyCost">—</strong><small>fuel + order-distance cost</small></div><div class="card metric"><div class="label">Weighted distance</div><strong id="distance">—</strong><small>order-km per day</small></div><div class="card metric"><div class="label">Selected sites</div><strong id="warehouses">—</strong><small id="warehouseDecision">awaiting optimization</small></div></div>
    <div class="decision-banner card"><div><div class="decision-kicker">GRIDPOINT recommendation</div><strong id="recommendationText">Choose settings and run the model.</strong><span id="recommendationReason">Balanced demo defaults are loaded. Run the model to calculate the recommended network.</span></div><div class="decision-pills"><span id="coveragePill">Coverage —</span><span id="capacityPill">Capacity —</span><span id="radiusPill">Radius —</span></div></div>
    <section class="card top-two-section"><div class="top-two-head"><div><div class="decision-kicker">TOP 2 SELECTED SITES</div><h3>Highest-demand warehouse coverage</h3><p>These are the two selected warehouses serving the most daily orders in the optimized network.</p></div><span class="solver-badge" id="topTwoBadge">Waiting for result</span></div><div id="topTwoGrid" class="top-two-grid"><div class="top-two-empty">Run GRIDPOINT to reveal the top two selected warehouse sites.</div></div></section>
    <div class="insight-grid">
      <section class="card insight-card"><div class="panel-head"><div><h3>Why these locations?</h3><span>Explainable warehouse selection</span></div><span class="data-ready"><i></i> MODEL EXPLAINED</span></div><div id="whySelected" class="why-list"><div class="top-two-empty">Run the optimizer to see why the highlighted sites were chosen.</div></div></section>
      <section class="card insight-card"><div class="panel-head"><div><h3>Decision report</h3><span>Ready for your hackathon demo</span></div></div><p>Export the optimized assignments, assumptions, selected sites and decision summary as a shareable HTML report.</p><div class="report-actions"><button class="btn primary" id="downloadReport" type="button">Download decision report</button><button class="btn ghost" id="setBestDefaults" type="button">Restore balanced defaults</button></div><div id="defaultHint" class="recommendation-note">Balanced defaults are preloaded. They are starting assumptions; GRIDPOINT still computes the actual optimum from your data.</div></section>
    </div>
    <div class="dashboard-grid"><div class="card panel"><div class="panel-head"><div><h3>Network map</h3><span>Premium basemap · demand-weighted markers · service areas</span></div><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end"><div class="map-style-switch" aria-label="Map style"><button type="button" data-map-style="auto">Auto</button><button type="button" data-map-style="streets">Roads</button><button type="button" data-map-style="satellite">Satellite</button><button type="button" data-map-style="light">Light</button><button type="button" data-map-style="dark">Dark</button></div><button class="map-3d-toggle active" id="optimizer3dToggle" type="button" aria-pressed="true">◈ 3D</button><button class="map-3d-toggle" id="mapLabelsToggle" type="button" aria-pressed="false">⚑ Labels</button><span id="mapStatus">Cluster map</span></div></div><div class="optimizer-3d-wrap is-3d" id="optimizer3dWrap"><div class="map" id="optMap"></div></div><div class="cluster-legend" id="clusterLegend"></div><div class="map-legend"><span><i class="legend-dot demand-dot"></i>Demand location</span><span><i class="legend-dot warehouse-dot"></i>Selected warehouse</span><span><i class="legend-dot user-dot"></i>Planning location</span></div></div><div class="card panel"><div class="panel-head"><div><h3>Infrastructure vs delivery cost</h3><span>Annual total across tested K</span></div><div style="display:flex;align-items:center;gap:8px"><span id="solverBadge" class="solver-badge">Solver ready</span><span id="recommendedKLabel">—</span></div></div><div class="chart-box chart-tall"><canvas id="costChart"></canvas></div><div class="chart-caption" id="chartCaption">Auto mode searches for the lowest total annual network cost.</div></div></div>
    <div class="split-grid"><div class="card panel"><div class="panel-head"><div><h3>Before → after</h3><span>single-site baseline vs optimized network</span></div></div><div class="compare-grid"><div class="compare-card"><span>Baseline</span><strong id="baselineCost">—</strong><small id="baselineDistance">—</small><small id="baselineCoverage">—</small></div><div class="compare-arrow">→</div><div class="compare-card featured"><span>GRIDPOINT</span><strong id="optimizedCost">—</strong><small id="optimizedDistance">—</small><small id="optimizedCoverage">—</small></div></div><div class="chart-box" style="height:230px;margin-top:14px"><canvas id="beforeAfterChart"></canvas></div><div class="delta-row"><span id="savings">—</span><span id="distanceSavings">—</span></div></div><div class="card panel"><div class="panel-head"><div><h3>Operational diagnostics</h3><span>Constraint-aware network health</span></div></div><div class="diagnostics"><div><span>Capacity</span><strong id="capacityStatus">—</strong></div><div><span>Radius</span><strong id="radiusStatus">—</strong></div><div><span>Avg utilization</span><strong id="avgUtilization">—</strong></div><div><span>Max utilization</span><strong id="maxUtilization">—</strong></div><div><span>Unserved / constrained</span><strong id="unservedOrders">—</strong></div><div><span>Avg drive time</span><strong id="avgDriveTime">—</strong></div><div><span>SLA coverage</span><strong id="slaCoverage">—</strong></div><div><span>Fuel / energy / day</span><strong id="fuelDaily">—</strong></div><div><span>Daily emissions</span><strong id="emissions">—</strong></div><div><span>Network resilience</span><strong id="resilience">—</strong></div></div></div></div>
    <section class="scenario-lab" data-optimizer-extra><div class="stress-head"><div><h3>Scenario lab</h3><p>Test the network before you commit: demand surge, peak traffic, tighter radius or the loss of the highest-demand warehouse.</p></div><span class="solver-badge">WHAT-IF</span></div><div class="stress-actions"><button class="mini-btn stress-btn" data-stress="demand">+25% demand</button><button class="mini-btn stress-btn" data-stress="traffic">Peak traffic</button><button class="mini-btn stress-btn" data-stress="radius">Tight radius</button><button class="mini-btn stress-btn" data-stress="failure">Warehouse outage</button></div><div id="stressResults" class="scenario-cards"><div class="scenario-card"><span>Annual cost</span><strong>—</strong><small>Run a scenario</small></div><div class="scenario-card"><span>Coverage</span><strong>—</strong><small>Demand served</small></div><div class="scenario-card"><span>Avg ETA</span><strong>—</strong><small>Drive time</small></div><div class="scenario-card"><span>Network</span><strong>—</strong><small>Warehouse count</small></div></div><div class="scenario-status" id="stressStatus">Run an optimization first, then test a scenario. The warehouse-outage case removes the current highest-demand selected site from the candidate pool and re-optimizes.</div></section><div class="split-grid"><div class="card panel"><div class="panel-head"><div><h3>Nearby warehouse recommendations</h3><span>ranked by road distance + demand coverage</span></div></div><div id="suggestions" class="suggestions"></div></div><div class="card panel"><div class="panel-head"><div><h3>Model assumptions</h3><span id="modelStatus">—</span></div></div><div class="assumption-grid"><div><span>Vehicle</span><strong id="assumptionVehicle">—</strong></div><div><span>Traffic</span><strong id="assumptionTraffic">—</strong></div><div><span>Radius</span><strong id="assumptionRadius">—</strong></div><div><span>Capacity / site</span><strong id="assumptionCapacity">—</strong></div><div><span>Demand / day</span><strong id="assumptionDemand">—</strong></div><div><span>Candidates</span><strong id="assumptionCandidates">—</strong></div><div><span>Fuel / energy</span><strong id="assumptionFuel">—</strong></div><div><span>Solver</span><strong id="assumptionSolver">—</strong></div></div><div class="formula-box"><strong>Objective</strong><span>Weighted delivery cost + warehouse opening cost + constraint penalty.</span></div></div></div>
    <div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>Selected warehouses</h3><span>Demand coverage, capacity and daily economics</span></div><div style="display:flex;gap:8px;align-items:center"><span id="warehouseCountLabel">—</span><button class="mini-btn" id="downloadReportInline" type="button">Report</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>#</th><th>Warehouse</th><th>Orders/day</th><th>Utilization</th><th>Demand cover</th><th>Weighted km</th><th>Cost/day</th></tr></thead><tbody id="warehouseTable"></tbody></table></div></div>
    <div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>Neighborhood assignments</h3><span>Constraint status shown for every location</span></div><span id="assignmentCountLabel">—</span></div><div class="table-wrap"><table class="table"><thead><tr><th>Neighborhood</th><th>Warehouse</th><th>Orders</th><th>Distance</th><th>Drive</th><th>Status</th></tr></thead><tbody id="assignmentTable"></tbody></table></div></div>
<section class="card panel analytics-3d" id="analytics3dSection" style="margin-top:14px">
  <div class="panel-head">
    <div><h3>Data analytics · 3D</h3><span id="analytics3dStatus">Run the optimizer to build the 3D analytics</span></div>
    <div class="analytics-3d-tools">
      <button class="mini-btn" id="analytics3dSpin" type="button">Auto-rotate</button>
      <button class="mini-btn" id="analytics3dReset" type="button">Reset view</button>
      <button class="mini-btn" id="analytics3dCsv" type="button">Analytics CSV</button>
    </div>
  </div>
  <div class="analytics-3d-grid">
    <div class="analytics-3d-card">
      <h4>Cost landscape across K</h4>
      <p>Annual total, delivery + fuel and warehouse opening cost for every network size the optimizer tested. Drag to rotate, scroll to zoom.</p>
      <div class="analytics-3d-stage" id="costCubeStage"><canvas id="costCube"></canvas><div class="analytics-3d-empty" id="costCubeEmpty">Run optimization to render this 3D view.</div></div>
      <div class="analytics-3d-legend" id="costCubeLegend"></div>
    </div>
    <div class="analytics-3d-card">
      <h4>Warehouse load vs spare capacity</h4>
      <p>Each selected warehouse as a 3D column: assigned daily orders against the capacity still available under the current constraints.</p>
      <div class="analytics-3d-stage" id="siteCubeStage"><canvas id="siteCube"></canvas><div class="analytics-3d-empty" id="siteCubeEmpty">Run optimization to render this 3D view.</div></div>
      <div class="analytics-3d-legend" id="siteCubeLegend"></div>
    </div>
  </div>
  <div class="chart-caption" id="analytics3dCaption">The 3D views are rendered from the same optimization result as the tables above.</div>
</section>

<div class="card panel" style="margin-top:14px" id="maths-logic">
  <div class="panel-head">
    <div><h3>Maths &amp; Logic</h3><span>the calculations behind GRIDPOINT</span></div>
    <div style="display:flex;align-items:center;gap:8px"><span>optimization model</span><button class="mini-btn" id="downloadMathCsv" type="button">CSV</button></div>
  </div>
  <p style="margin:0 0 14px;color:var(--muted);font-size:12px;line-height:1.75">
    GRIDPOINT combines distance, demand, delivery cost, fuel cost, warehouse capacity and service radius to choose a warehouse network with the lowest modeled annual total cost.
  </p>

  <div class="math-grid">
    <div class="math-card">
      <div class="math-num">01</div>
      <h4>Demand Growth</h4>
      <div class="math-formula">New Orders = Original Orders × (1 + Growth)</div>
      <p>If demand growth is 10%, 500 daily orders become 500 × 1.10 = 550.</p>
    </div>

    <div class="math-card">
      <div class="math-num">02</div>
      <h4>Distance</h4>
      <div class="math-formula">d = 2R sin<sup>−1</sup>(√[sin²(Δφ/2) + cosφ₁ cosφ₂ sin²(Δλ/2)])</div>
      <p>The Haversine formula calculates the geographical distance between a demand point and a warehouse using latitude and longitude.</p>
    </div>

    <div class="math-card">
      <div class="math-num">03</div>
      <h4>Delivery Cost</h4>
      <div class="math-formula">Delivery = Orders × Distance × Variable Cost</div>
      <p>More orders or longer delivery distances increase the daily delivery cost.</p>
    </div>

    <div class="math-card">
      <div class="math-num">04</div>
      <h4>Fuel / Energy Cost</h4>
      <div class="math-formula">Fuel = Orders × Distance ÷ Efficiency × Fuel Price</div>
      <p>The vehicle efficiency and fuel or energy price determine the additional operating cost.</p>
    </div>

    <div class="math-card wide">
      <div class="math-num">05</div>
      <h4>Total Annual Cost — Main Objective</h4>
      <div class="math-formula large">Annual Total = (Daily Delivery + Daily Penalty) × 365 + Opening Cost</div>
      <div class="math-subformula">Opening Cost = Number of Warehouses × Cost per Warehouse</div>
      <p>The optimizer tries to <strong>minimize</strong> this value. A network with more warehouses may reduce delivery cost, but it also increases opening cost.</p>
    </div>

    <div class="math-card">
      <div class="math-num">06</div>
      <h4>Capacity Constraint</h4>
      <div class="math-formula">Assigned Orders ≤ Warehouse Capacity</div>
      <p>A warehouse cannot be assigned more orders than its configured capacity.</p>
    </div>

    <div class="math-card">
      <div class="math-num">07</div>
      <h4>Service Radius</h4>
      <div class="math-formula">Assignment Distance ≤ Maximum Radius</div>
      <p>A demand point is feasible when its selected warehouse is within the allowed service radius.</p>
    </div>

    <div class="math-card">
      <div class="math-num">08</div>
      <h4>Coverage</h4>
      <div class="math-formula">Coverage % = Feasible Orders ÷ Total Orders × 100</div>
      <p>This shows what percentage of modeled demand is served without a capacity or radius violation.</p>
    </div>

    <div class="math-card">
      <div class="math-num">09</div>
      <h4>Warehouse Utilization</h4>
      <div class="math-formula">Utilization % = Assigned Orders ÷ Capacity × 100</div>
      <p>For example, 800 assigned orders in a 1,000-order warehouse gives 80% utilization.</p>
    </div>

    <div class="math-card wide logic-card">
      <div class="math-num">10</div>
      <h4>Optimization Logic</h4>
      <div class="logic-flow">
        <span>Demand</span><b>→</b><span>Candidate Sites</span><b>→</b><span>Distance Matrix</span><b>→</b><span>Feasible Assignments</span><b>→</b><span>Cost Calculation</span><b>→</b><span>Best Warehouse Network</span>
      </div>
      <p>The model tests possible warehouse counts, checks capacity and radius constraints, calculates the annual total cost, and selects the network with the lowest modeled objective under the chosen settings. For eligible problem sizes, GRIDPOINT can use an exact MILP solver; otherwise it uses a constraint-aware heuristic.</p>
    </div>
  </div>

  <div class="formula-note">
    <strong>Core optimization idea:</strong>
    Minimize <span>delivery cost + fuel cost + warehouse opening cost + constraint penalty</span>
    while respecting <span>capacity</span> and <span>service-radius</span> constraints.
  </div>
</div>

  </section>
</div>
'''

LOCATIONS = r'''
<section class="page-head" data-network-reveal><div><span class="eyebrow">● India network studio</span><h1>Warehouse network</h1><p>Load your own demand, tune the network in one place, and get the optimized warehouse solution without leaving this page.</p></div><div class="page-head-actions"><span class="solver-badge">Vector map · no API key</span><label class="btn ghost upload-btn" for="networkCsvInputTop" title="Load a demand CSV (name, latitude, longitude, daily_orders)">↑ Load CSV<input class="upload-input-hidden" id="networkCsvInputTop" type="file" accept=".csv,text/csv"></label><a class="btn primary" href="/optimizer">Open full optimizer →</a></div></section>
<section class="card network-settings-shell" data-network-reveal><div class="network-settings-inner"><div class="panel-head"><div><h3>Network setup</h3><span>Configure the model before the map</span></div><span id="networkDataStatus">Demo data ready</span></div><div class="network-settings-grid cols-3"><div class="network-setting"><label>Warehouse mode <b id="networkModeValue">Auto</b></label><select class="select" id="networkSelectionMode"><option value="auto" selected>Auto · best K</option></select></div><div class="network-setting"><label>Max capacity / warehouse <b id="networkCapacityValue">5,000</b></label><div class="range-stage"><input class="range" id="networkCapacity" type="range" min="500" max="50000" step="100" value="5000"><div class="range-scale"><span>500</span><span>10k</span><span>20k</span><span>35k</span><span>50k</span></div></div></div><div class="network-setting"><label>Max service radius <b id="networkRadiusValue">50 km</b></label><div class="range-stage"><input class="range" id="networkRadius" type="range" min="10" max="200" step="5" value="50"><div class="range-scale"><span>10</span><span>50</span><span>100</span><span>150</span><span>200</span></div></div></div></div><div class="network-settings-grid" style="margin-top:10px"><div class="network-setting"><label>Vehicle <b>operations</b></label><select class="select" id="networkVehicle"><option value="bike">Bike</option><option value="car" selected>Car / Van</option><option value="ev">Electric Van</option><option value="truck">Mini Truck</option></select></div><div class="network-setting"><label>Traffic <b>ETA model</b></label><select class="select" id="networkTraffic"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option><option value="peak">Peak</option></select></div><div class="network-setting"><label>Opening cost <b>₹ / warehouse</b></label><input class="input" id="networkOpeningCost" type="number" min="0" step="50000" value="4000000"></div><div class="network-setting"><label>Fuel / energy price <b>₹ / unit</b></label><input class="input" id="networkFuelPrice" type="number" min="1" step="1" value="100"></div></div><div class="network-settings-actions"><p>These values drive the same constrained warehouse-selection model used by the full Optimizer. Press <b>Run &amp; optimize</b> to solve the network with the demand below.</p><div class="network-run-group"><button class="btn ghost" id="networkResetSettings" type="button">Reset</button><button class="btn primary network-run-btn" id="networkOptimizeButton" type="button">Run &amp; optimize network →</button></div></div></div></section>
<section class="card network-demand-panel" data-network-reveal>
  <div class="network-demand-toolbar">
    <div class="network-demand-title"><div class="control-kicker">DEMAND DATASET</div><h3>Enter neighborhood demand</h3><p>Choose a ready dataset, upload the four-column CSV, or edit locations directly. Every option uses the same optimizer.</p></div>
    <span class="data-editor-badge">4 fields · ready to optimize</span>
  </div>
  <div class="dataset-presets" id="datasetPresets">
    <button class="dataset-preset active" type="button" data-preset="Bengaluru"><span><strong>Bengaluru demo</strong><span>25 demand zones · balanced</span></span><b>Use & optimize</b></button>
    <button class="dataset-preset" type="button" data-preset="Mumbai"><span><strong>Mumbai demo</strong><span>40 demand zones · metro spread</span></span><b>Use & optimize</b></button>
    <button class="dataset-preset" type="button" data-preset="Delhi"><span><strong>Delhi demo</strong><span>40 demand zones · NCR pattern</span></span><b>Use & optimize</b></button>
  </div>
  <div class="network-demand-body" style="margin-top:12px">
    <div class="demand-editor-shell">
      <div class="demand-editor-head"><span>#</span><span>Neighborhood</span><span>Latitude</span><span>Longitude</span><span>Orders / day</span><span></span></div>
      <div id="networkTableBody" class="demand-editor-body"></div>
      <div class="demand-editor-foot"><span id="networkEditorMeta">Bengaluru demo · ready</span><div class="demand-editor-actions"><button class="mini-btn" id="networkAddRow" type="button">+ Add location</button><button class="mini-btn" id="networkUseManual" type="button">Use table & optimize</button></div></div>
    </div>
    <div class="demand-import-side">
      <div class="demand-import-card"><div class="data-import-title"><span class="data-import-icon">↥</span><div><strong>Upload CSV</strong><span>Exact same four fields as the table</span></div></div><label class="upload-label" for="networkCsvInput"><span class="upload-copy"><strong id="networkFileName">Choose a .csv file</strong><span>name · latitude · longitude · daily_orders</span></span><span class="upload-arrow">Choose file</span></label><input class="upload-input" id="networkCsvInput" type="file" accept=".csv,text/csv"><div id="networkUploadStatus"></div><div class="format-chip">name,latitude,longitude,daily_orders</div><button class="mini-btn" id="downloadTemplate" type="button" style="margin-top:8px;width:100%">Download CSV template</button></div>
      <div class="dataset-status-panel"><strong id="networkDataStatus">Bengaluru demo ready</strong><span id="networkDatasetHint">Three built-in datasets are available. Pick one above or enter your own rows.</span></div>
    </div>
  </div>
</section>
<div class="warehouse-board" data-network-reveal><div class="panel-head"><div><h3>India demand map</h3><span>Premium basemap · demand points · warehouse catchments</span></div><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end"><div class="map-style-switch" aria-label="Map style"><button type="button" data-map-style="auto">Auto</button><button type="button" data-map-style="streets">Roads</button><button type="button" data-map-style="satellite">Satellite</button><button type="button" data-map-style="light">Light</button><button type="button" data-map-style="dark">Dark</button></div><span class="solver-badge">ArcGIS basemap</span></div></div><div class="map-stage"><div class="map-floating">GRIDPOINT MAP <span>· live road-ready</span></div><div id="locationsMap" class="map map-large"></div></div><div class="map-legend"><span><i class="legend-dot demand-dot"></i>Demand</span><span><i class="legend-dot warehouse-dot"></i>Warehouse</span><span><i class="legend-dot user-dot"></i>Planning point</span></div></div><div class="card panel"><div class="panel-head"><div><h3>Indian markets</h3><span>Click Analyze to run the model</span></div><span id="marketCountLabel">40+ markets</span></div><div class="network-tools"><input class="input market-search" id="marketSearch" placeholder="Search market…"><span class="field-help">Clicking a market loads its demand profile.</span></div><div id="locationList" class="location-list" style="margin-top:10px"></div></div>
<div class="card panel network-reveal-solution" data-network-reveal style="margin-top:14px"><div class="panel-head"><div><h3>Optimized solution</h3><span id="marketPreviewLabel">Choose a market, upload data, or use the table above</span></div><div class="network-tools"><button class="btn ghost" id="networkOpenOptimizer" type="button" disabled>Open in optimizer →</button></div></div><div id="marketPreview" class="market-preview"><div class="empty-state">Your recommended warehouses, assignments, coverage, cost, distance and resilience will appear here after processing.</div></div></div>
<div class="optimizer-tour" id="networkTour" aria-hidden="true"><div class="optimizer-tour-backdrop"></div><div class="optimizer-tour-spotlight" id="networkTourSpotlight"></div><div class="optimizer-tour-card" id="networkTourCard" role="dialog" aria-labelledby="networkTourTitle"><span class="optimizer-tour-arrow"></span><div class="optimizer-tour-top"><div><div class="optimizer-tour-kicker" id="networkTourKicker">GUIDED TOUR &middot; 1 OF 3</div><h3 class="optimizer-tour-title" id="networkTourTitle">Choose a dataset</h3><p class="optimizer-tour-text" id="networkTourText">Start from a ready demo, upload your own CSV, or type rows into the table below.</p></div><button class="optimizer-tour-close" id="networkTourClose" type="button" aria-label="Close tour">&times;</button></div><div class="optimizer-tour-progress"><i></i><i></i><i></i></div><div class="optimizer-tour-footer"><button class="tour-skip" id="networkTourSkip" type="button">Skip tour</button><div class="optimizer-tour-actions"><button class="btn ghost" id="networkTourBack" type="button">Back</button><button class="btn primary" id="networkTourNext" type="button">Next</button></div></div></div></div>
'''

HOW = r'''
<div class="page-head"><div><span class="eyebrow">● Explainable optimization</span><h1>How GRIDPOINT works</h1><p>From demand points to an operational warehouse network, every step is visible so the result can be explained to a customer, judge or logistics team.</p></div></div>
<div class="page-grid"><div class="card info-card"><strong>01</strong><h3>Load demand</h3><p>Upload neighborhood or customer demand with coordinates and daily orders. GRIDPOINT validates coordinates, removes duplicate points and reports data quality before optimization.</p></div><div class="card info-card"><strong>02</strong><h3>Generate candidate sites</h3><p>Demand-heavy locations, geographically diverse demand points, network grid points and your selected planning location become candidate warehouse sites.</p></div><div class="card info-card"><strong>03</strong><h3>Test warehouse counts</h3><p>Auto mode evaluates the network from 1 up to your search limit and selects the K with the lowest modeled annual total. Exact mode lets you force a specific K.</p></div><div class="card info-card"><strong>04</strong><h3>Assign demand</h3><p>Each neighborhood is assigned to a selected warehouse while the model checks capacity and maximum service radius. Violations are surfaced instead of hidden.</p></div><div class="card info-card"><strong>05</strong><h3>Model operations</h3><p>Vehicle efficiency, fuel or energy price and traffic assumptions affect delivery economics and estimated travel time. Small networks can be refined with live OSRM road distances.</p></div><div class="card info-card"><strong>06</strong><h3>Explain the result</h3><p>GRIDPOINT shows the recommended K, baseline vs optimized cost, demand coverage, warehouse utilization, assignments, candidate recommendations and the full infrastructure trade-off curve.</p></div></div>
<div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>Optimization objective</h3><span>weighted by daily demand</span></div><span>facility location + assignment</span></div><div class="formula-panel"><div class="formula-main">Minimize <b>delivery cost + opening cost + constraint penalty</b></div><div class="formula-lines"><span>Delivery cost = Σ(orderᵢ × distanceᵢⱼ × variable cost)</span><span>Fuel cost = Σ(orderᵢ × distanceᵢⱼ ÷ vehicle efficiency × fuel price)</span><span>Opening cost = warehouse count × cost per warehouse</span><span>Radius constraint = assignment distance ≤ maximum service radius</span><span>Capacity constraint = assigned orders ≤ warehouse capacity</span></div></div></div>
<div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>Infrastructure vs delivery trade-off</h3><span>Why GRIDPOINT searches for K</span></div></div><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.75">More warehouses generally reduce the distance between demand and inventory, but each additional site increases infrastructure cost. The cost curve in the optimizer makes that trade-off visible and identifies the minimum modeled annual total under the current assumptions.</p></div>
<div class="card panel" style="margin-top:14px" id="location"><div class="panel-head"><div><h3>Location and map services</h3><span>real-time web services</span></div></div><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.75">Browser geolocation is optional. Place search uses Nominatim, map rendering uses ArcGIS basemap tile services through Leaflet, with OSRM road routing for nearby/selected routes. The public services do not require a Google Maps API key. For production at scale, use an infrastructure-backed geocoding/routing provider or your own routing stack with rate limits and monitoring.</p></div>
<div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>CSV format</h3><span>keep it simple</span></div></div><pre style="margin:0;color:#9fb4ca;font-size:11px;line-height:1.7;overflow:auto">name,latitude,longitude,daily_orders
Whitefield,12.9698,77.7499,2400
Indiranagar,12.9784,77.6408,1800
Electronic City,12.8458,77.6602,3200</pre><div class="field-help" style="margin-top:10px">Only four columns are needed: name, latitude, longitude and daily_orders.</div></div>
<div class="card panel" style="margin-top:14px"><div class="panel-head"><div><h3>Real-world readiness</h3><span>what is live vs supplied</span></div></div><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.75">ArcGIS basemap tiles, address search, browser coordinates and road-route lookups are live services. The optimization becomes a true business model when you feed GRIDPOINT your own demand data, warehouse costs, fleet assumptions and service constraints. The built-in Indian city datasets are deterministic demonstration data, not live customer orders.</p></div>
'''


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))


def as_float(value, default=0.0):
    try:
        v = float(value)
        return v if v == v else default
    except Exception:
        return default


def city_neighborhoods(city):
    base = CITIES.get(city, CITIES["Bengaluru"])
    if city == "Bengaluru":
        return [dict(x) for x in DEMO_NEIGHBORHOODS]
    rng = random.Random(sum(ord(c) for c in city))
    rows = []
    multiplier = float(base.get("multiplier", 1.0))
    for i in range(40):
        angle = rng.random() * 6.283185307
        radius = 0.018 + rng.random() * 0.14
        lat = base["lat"] + cos(angle) * radius
        lon = base["lon"] + sin(angle) * radius
        orders = int((180 + rng.random() * 620) * multiplier)
        rows.append({"id": f"{city[:2].upper()}{i+1:03d}", "name": f"Zone {i+1}", "lat": lat, "lon": lon, "orders": max(1, orders)})
    return rows


def normalize_rows(rows, limit=1000):
    out = []
    seen = set()
    errors = []
    for i, row in enumerate(rows[:limit]):
        try:
            name = str(row.get("name") or row.get("neighborhood") or row.get("location") or f"Zone {i+1}").strip()
            lat = as_float(row.get("lat") or row.get("latitude"), 999)
            lon = as_float(row.get("lon") or row.get("lng") or row.get("longitude"), 999)
            orders = int(as_float(row.get("orders") or row.get("daily_orders") or row.get("demand"), -1))
            if not name or not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or orders < 0:
                errors.append({"row": i + 2, "message": "Invalid name, coordinates, or daily orders."})
                continue
            key = (round(lat, 6), round(lon, 6))
            if key in seen:
                errors.append({"row": i + 2, "message": "Duplicate coordinates skipped."})
                continue
            seen.add(key)
            out.append({"id": str(row.get("id") or f"N{i+1:04d}"), "name": name, "lat": lat, "lon": lon, "orders": orders})
        except Exception as exc:
            errors.append({"row": i + 2, "message": f"Could not parse row: {exc}"})
    return out, errors


def parse_simple_csv_text(text):
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return [], [{"row": 1, "message": "No data entered."}]
    lines = [line for line in text.split("\n") if line.strip()]
    if lines and lines[0].lower().replace(" ", "") != "name,latitude,longitude,daily_orders" and not lines[0].lower().startswith("name,"):
        text = "name,latitude,longitude,daily_orders\n" + text
    reader = csv.DictReader(io.StringIO(text))
    return normalize_rows(list(reader))


def load_rows(payload):
    rows = payload.get("neighborhoods")
    if isinstance(rows, list) and rows:
        normalized, _ = normalize_rows(rows)
        if normalized:
            return normalized
    return city_neighborhoods(str(payload.get("city") or "Bengaluru"))


def nearest_city(lat, lon):
    return min(CITIES.items(), key=lambda item: haversine_km(lat, lon, item[1]["lat"], item[1]["lon"]))


def candidate_points(neighborhoods, max_candidates=100, user_lat=None, user_lon=None):
    max_candidates = max(1, min(1000, int(max_candidates)))
    ranked = sorted(neighborhoods, key=lambda x: x["orders"], reverse=True)
    candidates = []
    seen = set()

    def add(pid, name, lat, lon, source="demand"):
        if len(candidates) >= max_candidates:
            return
        key = (round(float(lat), 5), round(float(lon), 5))
        if key in seen:
            return
        seen.add(key)
        candidates.append({"id": str(pid), "name": str(name), "lat": float(lat), "lon": float(lon), "source": source})

    if user_lat is not None and user_lon is not None:
        add("USER", "Current location", user_lat, user_lon, "current_location")

    for n in ranked[: min(12, len(ranked))]:
        add(f"D-{n['id']}", f"{n['name']} logistics site", n["lat"], n["lon"], "high_demand")

    target_count = min(max_candidates, max(25, min(max_candidates, len(ranked) * 3)))
    if target_count > 200:
        for n in ranked:
            if len(candidates) >= target_count:
                break
            add(f"D2-{n['id']}", f"{n['name']} candidate", n["lat"], n["lon"], "demand_point")
    else:
        while len(candidates) < target_count and ranked:
            best = None
            best_score = -1
            for n in ranked:
                if any(abs(n["lat"] - c["lat"]) < 0.0002 and abs(n["lon"] - c["lon"]) < 0.0002 for c in candidates):
                    continue
                min_dist = min(haversine_km(n["lat"], n["lon"], c["lat"], c["lon"]) for c in candidates) if candidates else 999
                score = min_dist * (1 + n["orders"] / max(1, ranked[0]["orders"]))
                if score > best_score:
                    best_score = score
                    best = n
            if not best:
                break
            add(f"F-{best['id']}", f"{best['name']} coverage site", best["lat"], best["lon"], "farthest_demand")

    if ranked and len(candidates) < target_count:
        total_orders = sum(n["orders"] for n in ranked)
        center_lat = sum(n["lat"] * n["orders"] for n in ranked) / max(1, total_orders)
        center_lon = sum(n["lon"] * n["orders"] for n in ranked) / max(1, total_orders)
        lat_vals = [n["lat"] for n in ranked]
        lon_vals = [n["lon"] for n in ranked]
        span_lat = max(0.20, max(lat_vals) - min(lat_vals))
        span_lon = max(0.20, max(lon_vals) - min(lon_vals))
        side = max(7, int((target_count - len(candidates)) ** 0.5) + 2)
        step_lat = span_lat / max(4, side - 1)
        step_lon = span_lon / max(4, side - 1)
        half = side // 2
        for gy in range(-half, half + 1):
            for gx in range(-half, half + 1):
                if len(candidates) >= target_count:
                    break
                lat = center_lat + gy * step_lat
                lon = center_lon + gx * step_lon
                add(f"G-{gy}-{gx}", f"Grid site {len(candidates)+1}", lat, lon, "grid")
            if len(candidates) >= target_count:
                break

    return candidates[:max_candidates]


GEOCODE_CACHE = {}


def fetch_json_url(url, timeout=8, headers=None):
    req_headers = {"User-Agent": "GRIDPOINT/3.0 (warehouse optimization platform)"}
    if headers:
        req_headers.update(headers)
    req = Request(url, headers=req_headers, method="GET")
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode_place(query):
    query = str(query or "").strip()
    if not query:
        raise ValueError("Enter a place, address, locality, or city in India.")
    cache_key = query.lower()
    cached = GEOCODE_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached["time"] < 3600:
        return cached["data"]
    params = urlencode({"q": f"{query}, India", "format": "json", "limit": 1, "countrycodes": "in", "addressdetails": 1})
    data = fetch_json_url(f"https://nominatim.openstreetmap.org/search?{params}")
    if not data:
        raise ValueError("No matching Indian location was found.")
    item = data[0]
    result = {"latitude": as_float(item.get("lat")), "longitude": as_float(item.get("lon")), "display_name": item.get("display_name") or query, "type": item.get("type") or "place", "address": item.get("address") or {}}
    GEOCODE_CACHE[cache_key] = {"time": now, "data": result}
    return result


def road_route(lat1, lon1, lat2, lon2):
    coords = f"{float(lon1)},{float(lat1)};{float(lon2)},{float(lat2)}"
    params = urlencode({"overview": "full", "geometries": "geojson", "steps": "false"})
    data = fetch_json_url(f"https://router.project-osrm.org/route/v1/driving/{coords}?{params}", timeout=10)
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("No drivable route was found between these locations.")
    route = data["routes"][0]
    return {"distance_km": as_float(route.get("distance")) / 1000.0, "duration_minutes": as_float(route.get("duration")) / 60.0, "geometry": route.get("geometry") or {}}


def road_table(origin_lat, origin_lon, destinations):
    if not destinations:
        return []
    coords = [f"{origin_lon},{origin_lat}"] + [f"{x['lon']},{x['lat']}" for x in destinations[:12]]
    params = urlencode({"sources": "0", "destinations": ";".join(str(i) for i in range(1, len(coords))), "annotations": "distance,duration"})
    try:
        data = fetch_json_url(f"https://router.project-osrm.org/table/v1/driving/{';'.join(coords)}?{params}", timeout=12)
        distances = (data.get("distances") or [[]])[0]
        durations = (data.get("durations") or [[]])[0]
        out = []
        for i, item in enumerate(destinations[:12]):
            out.append({"distance_km": as_float(distances[i]) / 1000.0 if i < len(distances) and distances[i] is not None else None, "drive_minutes": as_float(durations[i]) / 60.0 if i < len(durations) and durations[i] is not None else None})
        return out
    except Exception:
        return []


def refine_with_live_road_distances(neighborhoods, selected_indices, candidates, base_matrix):
    if len(neighborhoods) > 250 or len(selected_indices) > 12:
        return base_matrix, "Fast road-adjusted geospatial estimate"
    refined = [row[:] for row in base_matrix]
    batch_size = 60
    live_ok = False
    for start in range(0, len(neighborhoods), batch_size):
        batch = neighborhoods[start:start + batch_size]
        coords = [f"{candidates[j]['lon']},{candidates[j]['lat']}" for j in selected_indices]
        coords += [f"{n['lon']},{n['lat']}" for n in batch]
        source_end = len(selected_indices)
        try:
            params = urlencode({"sources": ";".join(str(i) for i in range(source_end)), "destinations": ";".join(str(i) for i in range(source_end, len(coords))), "annotations": "distance,duration"})
            data = fetch_json_url(f"https://router.project-osrm.org/table/v1/driving/{';'.join(coords)}?{params}", timeout=18)
            distances = data.get("distances") or []
            if len(distances) != len(selected_indices):
                continue
            for source_pos, candidate_idx in enumerate(selected_indices):
                row = distances[source_pos] or []
                for offset, value in enumerate(row):
                    if value is not None and start + offset < len(refined) and candidate_idx < len(refined[start + offset]):
                        refined[start + offset][candidate_idx] = as_float(value) / 1000.0
            live_ok = True
        except Exception:
            live_ok = False
            break
    return refined, "Live OSRM road distances" if live_ok else "Fast road-adjusted geospatial estimate"


def build_distance_matrix(neighborhoods, candidates):
    return [[haversine_km(n["lat"], n["lon"], c["lat"], c["lon"]) * 1.18 for c in candidates] for n in neighborhoods]


def greedy_site_sequence(neighborhoods, candidates, matrix):
    if not candidates:
        return []
    total_orders = max(1, sum(n["orders"] for n in neighborhoods))
    selected = []
    remaining = set(range(len(candidates)))
    first = min(remaining, key=lambda j: sum(neighborhoods[i]["orders"] * matrix[i][j] for i in range(len(neighborhoods))) / total_orders)
    selected.append(first)
    remaining.remove(first)
    nearest = [matrix[i][first] for i in range(len(neighborhoods))]
    while remaining:
        best_j = None
        best_gain = -1.0
        for j in remaining:
            gain = 0.0
            for i, n in enumerate(neighborhoods):
                current = nearest[i]
                d = matrix[i][j]
                if d < current:
                    gain += n["orders"] * (current - d)
            if gain > best_gain:
                best_gain = gain
                best_j = j
        if best_j is None:
            break
        selected.append(best_j)
        remaining.remove(best_j)
        for i in range(len(neighborhoods)):
            if matrix[i][best_j] < nearest[i]:
                nearest[i] = matrix[i][best_j]
    return selected


def assign_network(neighborhoods, selected_indices, candidates, matrix, capacity, radius, traffic_factor, variable_cost, fuel_price, vehicle):
    remaining = {j: float(capacity) for j in selected_indices}
    assigned = []
    route_speed = {"bike": 26, "car": 34, "ev": 32, "truck": 27}.get(vehicle.get("key", "car"), 34) / traffic_factor
    efficiency = max(0.1, float(vehicle.get("fuel", 15)))
    for i, n in sorted(enumerate(neighborhoods), key=lambda x: x[1]["orders"], reverse=True):
        within = [(matrix[i][j], j) for j in selected_indices if matrix[i][j] <= radius]
        feasible = [(d, j) for d, j in within if remaining[j] >= n["orders"]]
        status = "OK"
        if feasible:
            d, j = min(feasible, key=lambda x: x[0])
        elif within:
            d, j = min(within, key=lambda x: x[0])
            status = "Capacity exceeded"
        else:
            all_sites = [(matrix[i][j], j) for j in selected_indices]
            d, j = min(all_sites, key=lambda x: x[0]) if all_sites else (9999, None)
            status = "Outside service radius"
            if j is not None and remaining[j] < n["orders"]:
                status = "Capacity + radius"
        if j is None:
            continue
        remaining[j] = max(0.0, remaining[j] - n["orders"])
        drive_minutes = d / max(1, route_speed) * 60
        base_delivery_cost = n["orders"] * d * variable_cost
        fuel_energy_cost = n["orders"] * d / efficiency * fuel_price
        delivery_cost = base_delivery_cost + fuel_energy_cost
        assigned.append({
            "neighborhood_id": n["id"],
            "neighborhood_name": n["name"],
            "neighborhood_lat": n["lat"],
            "neighborhood_lon": n["lon"],
            "warehouse_id": candidates[j]["id"],
            "warehouse_name": candidates[j]["name"],
            "warehouse_lat": candidates[j]["lat"],
            "warehouse_lon": candidates[j]["lon"],
            "orders": n["orders"],
            "distance_km": d,
            "drive_minutes": drive_minutes,
            "daily_cost": delivery_cost,
            "base_delivery_cost": base_delivery_cost,
            "fuel_cost": fuel_energy_cost,
            "status": status,
            "feasible": status == "OK",
        })
    return assigned


def assign_network_from_map(neighborhoods, selected_indices, candidates, matrix, assignment_map, capacity, radius, variable_cost, fuel_price, vehicle):
    route_speed = {"bike": 26, "car": 34, "ev": 32, "truck": 27}.get(vehicle.get("key", "car"), 34)
    efficiency = max(0.1, float(vehicle.get("fuel", 15)))
    assigned = []
    for i, n in enumerate(neighborhoods):
        j = assignment_map.get(i)
        if j not in selected_indices:
            continue
        d = float(matrix[i][j])
        within_radius = d <= radius + 1e-9
        drive_minutes = d / max(1, route_speed) * 60
        base_delivery_cost = n["orders"] * d * variable_cost
        fuel_energy_cost = n["orders"] * d / efficiency * fuel_price
        assigned.append({
            "neighborhood_id": n["id"],
            "neighborhood_name": n["name"],
            "neighborhood_lat": n["lat"],
            "neighborhood_lon": n["lon"],
            "warehouse_id": candidates[j]["id"],
            "warehouse_name": candidates[j]["name"],
            "warehouse_lat": candidates[j]["lat"],
            "warehouse_lon": candidates[j]["lon"],
            "orders": n["orders"],
            "distance_km": d,
            "drive_minutes": drive_minutes,
            "daily_cost": base_delivery_cost + fuel_energy_cost,
            "base_delivery_cost": base_delivery_cost,
            "fuel_cost": fuel_energy_cost,
            "status": "OK" if within_radius else "Outside service radius",
            "feasible": within_radius,
        })
    return assigned


def solve_fixed_assignment(neighborhoods, selected_indices, matrix, capacity, radius, variable_cost, fuel_price, vehicle):
    if not SCIPY_MILP_AVAILABLE:
        return None
    n = len(neighborhoods)
    selected = list(selected_indices)
    m = len(selected)
    if n == 0 or m == 0 or n * m > 25000:
        return None
    efficiency = max(0.1, float(vehicle.get("fuel", 15)))
    c = [0.0] * (n * m)
    lower = [0.0] * (n * m)
    upper = [1.0] * (n * m)
    integrality = [1] * (n * m)
    for i, node in enumerate(neighborhoods):
        for local_j, global_j in enumerate(selected):
            d = float(matrix[i][global_j])
            x = i * m + local_j
            c[x] = node["orders"] * d * (variable_cost + fuel_price / efficiency) * 365.0
            if d > radius:
                upper[x] = 0.0
    row_count = n + m
    A = lil_matrix((row_count, n * m), dtype=float)
    lb = [0.0] * row_count
    ub = [0.0] * row_count
    row = 0
    for i in range(n):
        for local_j in range(m):
            A[row, i * m + local_j] = 1.0
        lb[row] = ub[row] = 1.0
        row += 1
    for local_j, _global_j in enumerate(selected):
        for i, node in enumerate(neighborhoods):
            A[row, i * m + local_j] = node["orders"]
        lb[row] = -float("inf")
        ub[row] = float(capacity)
        row += 1
    try:
        result = milp(c=c, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(A.tocsr(), lb, ub), options={"time_limit": 8.0, "mip_rel_gap": 0.01, "presolve": True})
    except Exception:
        return None
    if not getattr(result, "success", False):
        return None
    values = result.x
    assignment_map = {}
    for i in range(n):
        start = i * m
        local_j = max(range(m), key=lambda jj: values[start + jj])
        if values[start + local_j] < 0.5:
            return None
        assignment_map[i] = selected[local_j]
    return assignment_map


def evaluate_solution(neighborhoods, candidate_indices, candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, assignment_map=None):
    assignments = assign_network_from_map(neighborhoods, candidate_indices, candidates, matrix, assignment_map, capacity, radius, variable_cost, fuel_price, vehicle) if assignment_map is not None else assign_network(neighborhoods, candidate_indices, candidates, matrix, capacity, radius, traffic_factor, variable_cost, fuel_price, vehicle)
    total_orders = max(1, sum(n["orders"] for n in neighborhoods))
    feasible_orders = sum(a["orders"] for a in assignments if a["feasible"])
    weighted_distance = sum(a["orders"] * a["distance_km"] for a in assignments)
    daily_delivery = sum(a["daily_cost"] for a in assignments)
    opening_total = len(candidate_indices) * opening_cost
    violation_orders = sum(a["orders"] for a in assignments if not a["feasible"])
    penalty_daily = violation_orders * max(1.0, variable_cost) * max(radius, 1.0) * 4
    annual_total = daily_delivery * 365 + opening_total + penalty_daily * 365
    return {"assignments": assignments,"daily_delivery": daily_delivery,"weighted_distance": weighted_distance,"annual_total": annual_total,"penalty_daily": penalty_daily,"feasible_orders": feasible_orders,"coverage_pct": 100 * feasible_orders / total_orders,"violation_orders": violation_orders}


def fast_ranked_site_sequence(neighborhoods, candidates, matrix, limit):
    if not candidates:
        return []
    limit = min(max(1, int(limit)), len(candidates), max(1, len(neighborhoods)))
    scored = []
    for j in range(len(candidates)):
        score = 0.0
        for i, node in enumerate(neighborhoods):
            score += node["orders"] / (1.0 + float(matrix[i][j]))
        scored.append((score, j))
    scored.sort(reverse=True)
    return [j for _, j in scored[:limit]]


def trial_warehouse_counts(limit, selection_mode, exact_k):
    limit = max(1, int(limit))
    if selection_mode == "exact":
        return [max(1, min(limit, int(exact_k)))]
    if limit <= 120:
        return list(range(1, limit + 1))
    checkpoints = [1,2,3,4,5,6,8,10,12,16,20,25,30,40,50,60,75,90,100,125,150,200,250,350,500,750,1000]
    return sorted(set(k for k in checkpoints if k <= limit) | {limit})


def constraint_aware_site_sequence(neighborhoods, candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, limit):
    limit = min(max(1, int(limit)), len(candidates), max(1, len(neighborhoods)))
    if limit > 120 or len(candidates) > 160:
        return fast_ranked_site_sequence(neighborhoods, candidates, matrix, limit)
    remaining = set(range(len(candidates)))
    selected = []
    for step in range(limit):
        best = None
        best_score = float("inf")
        pool = remaining
        if step >= 24 and len(pool) > 32:
            pool = sorted(pool, key=lambda j: sum(neighborhoods[i]["orders"] * matrix[i][j] for i in range(len(neighborhoods))))[:32]
        for j in pool:
            ev = evaluate_solution(neighborhoods, selected + [j], candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle)
            if ev["annual_total"] < best_score:
                best_score = ev["annual_total"]
                best = j
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)
    return selected


def solve_milp_network(neighborhoods, candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, exact_k=None, max_sites=None):
    if not SCIPY_MILP_AVAILABLE:
        return None
    n = len(neighborhoods)
    m = len(candidates)
    if n == 0 or m == 0 or n * m > 25000:
        return None
    if exact_k is not None and (exact_k < 1 or exact_k > min(m, n)):
        return None
    efficiency = max(0.1, float(vehicle.get("fuel", 15)))
    var_count = n * m + m
    c = [0.0] * var_count
    lower = [0.0] * var_count
    upper = [1.0] * var_count
    integrality = [1] * var_count
    for i, node in enumerate(neighborhoods):
        for j in range(m):
            d = matrix[i][j]
            x = i * m + j
            c[x] = node["orders"] * d * (variable_cost + fuel_price / efficiency) * 365.0
            if d > radius:
                upper[x] = 0.0
    for j in range(m):
        c[n * m + j] = opening_cost
    extra = 1
    row_count = n + m + n * m + m + extra
    A = lil_matrix((row_count, var_count), dtype=float)
    lb = [0.0] * row_count
    ub = [0.0] * row_count
    row = 0
    for i in range(n):
        for j in range(m):
            A[row, i * m + j] = 1.0
        lb[row] = ub[row] = 1.0
        row += 1
    for j in range(m):
        for i, node in enumerate(neighborhoods):
            A[row, i * m + j] = node["orders"]
        A[row, n * m + j] = -float(capacity)
        lb[row] = -float("inf")
        ub[row] = 0.0
        row += 1
    for i in range(n):
        for j in range(m):
            A[row, i * m + j] = 1.0
            A[row, n * m + j] = -1.0
            lb[row] = -float("inf")
            ub[row] = 0.0
            row += 1
    for j in range(m):
        for i in range(n):
            A[row, i * m + j] = 1.0
        A[row, n * m + j] = -1.0
        lb[row] = 0.0
        ub[row] = float("inf")
        row += 1
    for j in range(m):
        A[row, n * m + j] = 1.0
    if exact_k is not None:
        lb[row] = ub[row] = float(exact_k)
    else:
        lb[row] = -float("inf")
        ub[row] = float(max_sites if max_sites is not None else m)
    try:
        result = milp(c=c, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(A.tocsr(), lb, ub), options={"time_limit": 10.0, "mip_rel_gap": 0.02, "presolve": True})
    except Exception:
        return None
    if not getattr(result, "success", False):
        return None
    values = result.x
    selected = [j for j in range(m) if values[n * m + j] > 0.5]
    if not selected:
        return None
    return {"selected_indices": selected, "solver": "Exact MILP · HiGHS", "objective": float(result.fun), "status": str(getattr(result, "message", "Solved"))}


def optimize_payload(payload):
    city = str(payload.get("city") or "Bengaluru")
    neighborhoods = load_rows(payload)
    growth = max(0.0, min(2.0, as_float(payload.get("demandGrowth"), 0.0)))
    neighborhoods = [dict(n, orders=max(1, round(n["orders"] * (1 + growth)))) for n in neighborhoods]
    capacity = max(1, as_float(payload.get("capacity"), 1000))
    radius = max(10, min(200, as_float(payload.get("radius"), 50)))
    variable_cost = max(0.1, as_float(payload.get("variableCost"), 12))
    opening_cost = max(0, as_float(payload.get("openingCost"), 4000000))
    fuel_price = max(1, as_float(payload.get("fuelPrice"), 100))
    vehicle_key = str(payload.get("vehicle") or "car")
    vehicle = dict(VEHICLES.get(vehicle_key, VEHICLES["car"]), key=vehicle_key)
    traffic_key = str(payload.get("traffic") or "medium")
    traffic_factor = {"low": 1.0, "medium": 1.12, "high": 1.28, "peak": 1.50}.get(traffic_key, 1.12)
    user_lat = payload.get("userLatitude")
    user_lon = payload.get("userLongitude")
    user_lat = None if user_lat in (None, "") else as_float(user_lat)
    user_lon = None if user_lon in (None, "") else as_float(user_lon)
    max_wh = max(1, min(100, int(as_float(payload.get("maxWarehouses"), min(100, len(neighborhoods))))))
    selection_mode = str(payload.get("selectionMode") or "auto")

    candidates = candidate_points(neighborhoods, max_candidates=min(1000, max(25, len(neighborhoods)*3)), user_lat=user_lat, user_lon=user_lon)
    manual_warehouses = payload.get("manualWarehouses") or []
    manual_ids = []
    for i, item in enumerate(manual_warehouses if isinstance(manual_warehouses, list) else []):
        try:
            lat = as_float(item.get("lat")); lon = as_float(item.get("lon"))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            wid = str(item.get("id") or f"MANUAL-{i+1}")
            if any(str(c.get("id")) == wid for c in candidates):
                continue
            candidates.append({"id": wid, "name": str(item.get("name") or f"Custom Warehouse {i+1}"), "lat": lat, "lon": lon, "source": "manual", "required": True})
            manual_ids.append(wid)
        except Exception:
            continue
    blocked_id = str(payload.get("blockedWarehouseId") or "").strip()
    if blocked_id:
        candidates = [c for c in candidates if str(c.get("id")) != blocked_id]
    matrix = build_distance_matrix(neighborhoods, candidates)
    candidate_limit = min(max_wh, len(candidates), max(1, len(neighborhoods)))
    if candidate_limit < 1:
        raise ValueError("At least one warehouse candidate is required.")
    exact_k = max(1, min(candidate_limit, int(as_float(payload.get("exactWarehouses"), min(4, candidate_limit)))))
    sla_minutes = max(10.0, min(180.0, as_float(payload.get("slaMinutes"), 45.0)))

    sequence = constraint_aware_site_sequence(neighborhoods, candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, candidate_limit)
    manual_indices = [i for i, c in enumerate(candidates) if str(c.get("id")) in manual_ids]
    if manual_indices:
        # Custom map-added warehouses are explicit operator choices: keep them in the selected network.
        sequence = manual_indices + [j for j in sequence if j not in manual_indices]
        candidate_limit = max(candidate_limit, len(manual_indices))
        max_wh = max(max_wh, len(manual_indices))
    candidate_limit = min(max(candidate_limit, len(manual_indices)), len(candidates))
    evaluations = {k: evaluate_solution(neighborhoods, sequence[:k], candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle) for k in trial_warehouse_counts(candidate_limit, selection_mode, exact_k)}

    solver = "Constraint-aware heuristic"
    milp_result = None
    exact_target = exact_k if selection_mode == "exact" else None
    if len(neighborhoods) * len(candidates) <= 25000:
        milp_result = solve_milp_network(neighborhoods, candidates, matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, exact_k=exact_target, max_sites=candidate_limit)
    if milp_result:
        selected_indices = milp_result["selected_indices"]
        selected_k = len(selected_indices)
        recommended_k = selected_k if selection_mode == "auto" else min(evaluations, key=lambda k: evaluations[k]["annual_total"])
        solver = milp_result["solver"]
    else:
        recommended_k = min(evaluations, key=lambda k: evaluations[k]["annual_total"]) if evaluations else 1
        selected_k = min(exact_k if selection_mode == "exact" else recommended_k, candidate_limit)
        selected_indices = sequence[:selected_k]

    if manual_indices:
        # Rebuild the final selected set so every manually added warehouse is actually used.
        target_k = max(len(manual_indices), selected_k)
        target_k = min(target_k, candidate_limit)
        selected_indices = manual_indices + [j for j in sequence if j not in manual_indices][:max(0, target_k-len(manual_indices))]
        selected_k = len(selected_indices)
        recommended_k = max(recommended_k, len(manual_indices))

    final_matrix, routing_mode = refine_with_live_road_distances(neighborhoods, selected_indices, candidates, matrix)
    fixed_assignment = solve_fixed_assignment(neighborhoods, selected_indices, final_matrix, capacity, radius, variable_cost, fuel_price, vehicle)
    selected_eval = evaluate_solution(neighborhoods, selected_indices, candidates, final_matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle, assignment_map=fixed_assignment) if fixed_assignment is not None else evaluate_solution(neighborhoods, selected_indices, candidates, final_matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle)
    if selected_k in evaluations:
        evaluations[selected_k] = selected_eval

    total_orders = sum(n["orders"] for n in neighborhoods)
    baseline_capacity = capacity
    baseline_center_index = min(range(len(candidates)), key=lambda j: sum(neighborhoods[i]["orders"] * matrix[i][j] for i in range(len(neighborhoods))))
    baseline_matrix, _ = refine_with_live_road_distances(neighborhoods, [baseline_center_index], candidates, matrix)
    baseline_eval = evaluate_solution(neighborhoods, [baseline_center_index], candidates, baseline_matrix, baseline_capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle)

    selected_rows = []
    for idx in selected_indices:
        w = candidates[idx]
        own = [a for a in selected_eval["assignments"] if a["warehouse_id"] == w["id"]]
        assigned_orders = sum(a["orders"] for a in own)
        feasible_orders = sum(a["orders"] for a in own if a["feasible"])
        weighted_km = sum(a["orders"] * a["distance_km"] for a in own)
        selected_rows.append({**w, "assigned_orders": assigned_orders, "feasible_orders": feasible_orders, "capacity": capacity, "utilization_pct": 100 * assigned_orders / max(1, capacity), "coverage_pct": 100 * feasible_orders / max(1, total_orders), "over_capacity": assigned_orders > capacity, "daily_distance_km": sum(a["distance_km"] for a in own), "weighted_distance_km": weighted_km, "daily_delivery_cost": sum(a["daily_cost"] for a in own)})

    resilience_pct = 100.0
    resilience_detail = {"warehouse_id": None, "warehouse_name": None, "coverage_pct": 100.0, "annual_total_cost": selected_eval["annual_total"]}
    if len(selected_indices) > 1 and selected_rows:
        top_site = max(selected_rows, key=lambda w: w.get("assigned_orders", 0), default=None)
        remaining_sites = [idx for idx in selected_indices if not top_site or candidates[idx]["id"] != top_site.get("id")]
        if remaining_sites:
            stress = evaluate_solution(neighborhoods, remaining_sites, candidates, final_matrix, capacity, radius, traffic_factor, variable_cost, opening_cost, fuel_price, vehicle)
            resilience_pct = stress["coverage_pct"]
            resilience_detail = {"warehouse_id": top_site.get("id"), "warehouse_name": top_site.get("name"), "coverage_pct": stress["coverage_pct"], "annual_total_cost": stress["annual_total"]}

    nearest = []
    if user_lat is not None and user_lon is not None:
        ranked = sorted(candidates, key=lambda x: haversine_km(user_lat, user_lon, x["lat"], x["lon"]))[:10]
        routes = road_table(user_lat, user_lon, ranked)
        for i, w in enumerate(ranked):
            straight = haversine_km(user_lat, user_lon, w["lat"], w["lon"]) * 1.18
            route = routes[i] if i < len(routes) else {}
            local_orders = sum(n["orders"] for n in neighborhoods if haversine_km(n["lat"], n["lon"], w["lat"], w["lon"]) <= radius)
            nearest.append({**w, "distance_km": route.get("distance_km") or straight, "drive_minutes": route.get("drive_minutes") or (straight / 30) * 60, "demand_within_radius": local_orders, "demand_share_pct": 100 * local_orders / max(1, total_orders), "reason": f"Covers {100 * local_orders / max(1, total_orders):.1f}% of modeled demand within {radius:.0f} km"})
    else:
        center = CITIES.get(city, CITIES["Bengaluru"])
        ranked = sorted(candidates, key=lambda x: haversine_km(center["lat"], center["lon"], x["lat"], x["lon"]))[:10]
        for w in ranked:
            d = haversine_km(center["lat"], center["lon"], w["lat"], w["lon"]) * 1.18
            local_orders = sum(n["orders"] for n in neighborhoods if haversine_km(n["lat"], n["lon"], w["lat"], w["lon"]) <= radius)
            nearest.append({**w, "distance_km": d, "drive_minutes": (d / 30) * 60, "demand_within_radius": local_orders, "demand_share_pct": 100 * local_orders / max(1, total_orders), "reason": f"Covers {100 * local_orders / max(1, total_orders):.1f}% of modeled demand within {radius:.0f} km"})

    tradeoff_points = [{"k": k, "annual_total_cost": round(evaluations[k]["annual_total"]), "daily_delivery_cost": round(evaluations[k]["daily_delivery"], 2), "coverage_pct": round(evaluations[k]["coverage_pct"], 2), "opening_cost": round(k * opening_cost)} for k in sorted(evaluations)]
    weighted_distance = selected_eval["weighted_distance"]
    avg_distance = weighted_distance / max(1, total_orders)
    weighted_drive_time = sum(a["orders"] * a["drive_minutes"] for a in selected_eval["assignments"])
    avg_drive_time = weighted_drive_time / max(1, total_orders)
    sla_orders = sum(a["orders"] for a in selected_eval["assignments"] if a.get("feasible") and a.get("drive_minutes", 1e9) <= sla_minutes)
    sla_coverage_pct = 100 * sla_orders / max(1, total_orders)
    baseline_sla_orders = sum(a["orders"] for a in baseline_eval["assignments"] if a.get("feasible") and a.get("drive_minutes", 1e9) <= sla_minutes)
    baseline_sla_pct = 100 * baseline_sla_orders / max(1, total_orders)
    baseline_savings_pct = 100 * (baseline_eval["annual_total"] - selected_eval["annual_total"]) / max(1, baseline_eval["annual_total"])
    carbon_factor = float(vehicle.get("emission", 0.192))
    carbon_kg = weighted_distance * carbon_factor
    energy_units = weighted_distance / max(0.1, float(vehicle.get("fuel", 15)))
    energy_cost_daily = energy_units * fuel_price
    max_util = max((w["utilization_pct"] for w in selected_rows), default=0)
    avg_util = sum(w["utilization_pct"] for w in selected_rows) / max(1, len(selected_rows))

    objective_description = "minimize Σ(order_i × distance_ij × (delivery_cost_per_order_km + fuel_price ÷ vehicle_efficiency)) + warehouse_opening_cost + constraint_penalty"
    summary = {"warehouse_count": selected_k, "recommended_warehouse_count": recommended_k, "selection_mode": selection_mode, "total_orders_per_day": total_orders, "weighted_distance_km": weighted_distance, "avg_distance_per_order_km": avg_distance, "total_distance_km": weighted_distance, "avg_drive_minutes": avg_drive_time, "sla_target_minutes": sla_minutes, "sla_coverage_pct": sla_coverage_pct, "baseline_sla_coverage_pct": baseline_sla_pct, "baseline_annual_cost": baseline_eval["annual_total"], "optimized_annual_cost": selected_eval["annual_total"], "savings_pct": baseline_savings_pct, "coverage_pct": selected_eval["coverage_pct"], "feasible_demand_pct": selected_eval["coverage_pct"], "unserved_orders": selected_eval["violation_orders"], "capacity_utilization_avg_pct": avg_util, "capacity_utilization_max_pct": max_util, "capacity_violations": sum(1 for a in selected_eval["assignments"] if "Capacity" in a["status"]), "radius_violations": sum(1 for a in selected_eval["assignments"] if "radius" in a["status"].lower()), "energy_cost_daily": energy_cost_daily, "estimated_emissions_kg_daily": carbon_kg, "network_resilience_pct": resilience_pct, "vehicle": vehicle["label"], "traffic": traffic_key, "traffic_factor": traffic_factor, "radius_km": radius, "capacity_per_warehouse": capacity, "routing_mode": routing_mode, "solver": solver, "objective": "Weighted delivery cost + warehouse opening cost + constraint penalty", "objective_description": objective_description}
    daily_delivery = selected_eval["daily_delivery"]
    costs = {"daily_delivery_cost": daily_delivery, "monthly_delivery_cost": daily_delivery * 30, "annual_delivery_cost": daily_delivery * 365, "opening_cost_total": selected_k * opening_cost, "constraint_penalty_annual": selected_eval["penalty_daily"] * 365, "annual_total_cost": selected_eval["annual_total"], "total": selected_eval["annual_total"], "total_cost": selected_eval["annual_total"], "totalCost": selected_eval["annual_total"], "total_delivery_cost": daily_delivery, "totalDeliveryCost": daily_delivery, "fuel_cost_daily": energy_cost_daily, "fuel_cost_annual": energy_cost_daily * 365}
    diagnostics = {"capacity_status": "Healthy" if max_util <= 90 else ("Near capacity" if max_util <= 100 else "Over capacity"), "radius_status": "Healthy" if summary["radius_violations"] == 0 else "Some neighborhoods exceed service radius", "data_status": f"{len(neighborhoods)} demand locations modeled", "candidate_count": len(candidates), "manual_warehouse_count": len(manual_ids), "routing_mode": routing_mode, "solver": solver, "resilience_pct": resilience_pct, "resilience_detail": resilience_detail, "weighted_objective": True, "sla_target_minutes": sla_minutes, "sla_coverage_pct": sla_coverage_pct, "objective_description": objective_description}
    return {"ok": True, "city": city, "location": {"latitude": user_lat, "longitude": user_lon, "permission": "granted" if user_lat is not None and user_lon is not None else "not_used"}, "neighborhoods": neighborhoods, "warehouses": selected_rows, "assignments": selected_eval["assignments"], "nearest_warehouses": nearest, "summary": summary, "costs": costs, "metrics": {"total_cost": selected_eval["annual_total"], "totalCost": selected_eval["annual_total"], "total_delivery_cost": daily_delivery, "totalDeliveryCost": daily_delivery, "costs": costs}, "tradeoff_curve": [p["annual_total_cost"] for p in tradeoff_points], "tradeoff_points": tradeoff_points, "baseline": {"annual_total_cost": baseline_eval["annual_total"], "warehouse_count": 1, "avg_distance_per_order_km": baseline_eval["weighted_distance"] / max(1, total_orders), "coverage_pct": baseline_eval["coverage_pct"], "sla_coverage_pct": baseline_sla_pct}, "recommendation": {"recommended_k": recommended_k, "reason": f"{solver} selected {recommended_k} warehouse{'s' if recommended_k != 1 else ''} under the current demand, opening-cost, capacity, radius, vehicle and fuel assumptions.", "tested_up_to": candidate_limit}, "diagnostics": diagnostics}

def render_page(content, active, title):
    city_options = ''.join(f'<option value="{name}"{" selected" if name == "Bengaluru" else ""}>{name}</option>' for name in CITIES)
    content = content.replace('__CITY_OPTIONS__', city_options)
    return render_template_string(BASE_HTML, content=content, active=active, title=title, cities=CITIES)


@app.get("/")
def home():
    return render_page(HOME, "home", "Overview")


@app.get("/optimizer")
def optimizer():
    return render_page(OPTIMIZER, "optimizer", "Optimizer")


@app.get("/locations")
def locations():
    return render_page(LOCATIONS, "locations", "Warehouse Network")


@app.get("/how-it-works")
def how_it_works():
    return render_page(HOW, "how", "How it works")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "gridpoint", "map_requires_api_key": False, "map_stack": "Leaflet + ArcGIS basemap tiles", "routing": "OSRM", "geocoding": "Nominatim", "data_mode": "CSV or in-page entry"})


@app.get("/api/cities")
def cities():
    return jsonify({"ok": True, "cities": CITIES})


@app.get("/api/locations")
def locations_api():
    city = request.args.get("city", "Bengaluru")
    rows = city_neighborhoods(city)
    return jsonify({"ok": True, "city": city, "locations": rows})


@app.post("/api/nearby")
def nearby():
    payload = request.get_json(silent=True) or {}
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    city = str(payload.get("city") or "").strip()
    if lat in (None, "") or lon in (None, ""):
        if city in CITIES:
            lat, lon = CITIES[city]["lat"], CITIES[city]["lon"]
        else:
            return jsonify({"ok": False, "error": "Latitude and longitude are required."}), 400
    lat, lon = as_float(lat), as_float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"ok": False, "error": "Invalid coordinates."}), 400
    city_name, city_meta = nearest_city(lat, lon)
    neighborhoods = city_neighborhoods(city or city_name) if city in CITIES else city_neighborhoods(city_name)
    candidates = candidate_points(neighborhoods, 100, lat, lon)
    ranked = sorted(candidates, key=lambda w: haversine_km(lat, lon, w["lat"], w["lon"]))
    nearest = road_table(lat, lon, ranked[:12])
    suggestions = []
    for i, w in enumerate(ranked[:8]):
        fallback_distance = haversine_km(lat, lon, w["lat"], w["lon"]) * 1.22
        route_info = nearest[i] if i < len(nearest) else {}
        suggestions.append({
            "id": w["id"], "name": w["name"], "lat": w["lat"], "lon": w["lon"],
            "distance_km": route_info.get("distance_km") or fallback_distance,
            "drive_minutes": route_info.get("drive_minutes") or (fallback_distance / 30) * 60,
            "reason": "Road-network candidate near your location",
        })
    return jsonify({"ok": True, "latitude": lat, "longitude": lon, "city": city_name, "suggestions": suggestions})


@app.get("/api/geocode")
def geocode_api():
    try:
        result = geocode_place(request.args.get("q", ""))
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/route")
def route_api():
    try:
        lat1 = as_float(request.args.get("lat1"))
        lon1 = as_float(request.args.get("lon1"))
        lat2 = as_float(request.args.get("lat2"))
        lon2 = as_float(request.args.get("lon2"))
        result = road_route(lat1, lon1, lat2, lon2)
        return jsonify({"ok": True, "route": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/parse-data")
def parse_data_api():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    rows, errors = parse_simple_csv_text(text)
    if not rows:
        message = errors[0].get("message") if errors else "No valid demand locations were found."
        return jsonify({"ok": False, "error": message, "errors": errors[:25]}), 400
    duplicate_count = sum(1 for item in errors if "Duplicate" in item.get("message", ""))
    invalid_count = len(errors) - duplicate_count
    return jsonify({
        "ok": True,
        "rows": rows,
        "count": len(rows),
        "valid_count": len(rows),
        "duplicate_count": duplicate_count,
        "invalid_count": invalid_count,
        "errors": errors[:25],
    })


@app.post("/api/optimize")
def optimize_api():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(optimize_payload(payload))
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Optimization failed: {exc}"}), 400


@app.post("/api/market-optimize")
def market_optimize():
    payload = request.get_json(silent=True) or {}
    city = str(payload.get("city") or "Bengaluru")
    rows = city_neighborhoods(city)
    total_orders = sum(r["orders"] for r in rows)
    quick_payload = {"city": city, "selectionMode": "auto", "maxWarehouses": max(2, min(12, max(2, len(rows) // 4))), "exactWarehouses": 3, "capacity": max(1200, int(total_orders / 5) + 200), "radius": 35, "variableCost": 12, "openingCost": 4000000, "fuelPrice": 100, "vehicle": "car", "traffic": "medium", "demandGrowth": 0, "slaMinutes": 45, "neighborhoods": rows}
    try:
        return jsonify(optimize_payload(quick_payload))
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Market optimization failed: {exc}"}), 400


@app.post("/api/upload")
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "No file uploaded."}), 400
    raw = file.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return jsonify({"ok": False, "error": "The CSV is missing a header row."}), 400
    rows, errors = normalize_rows(list(reader))
    if not rows:
        return jsonify({"ok": False, "error": "No valid demand locations were found in the CSV."}), 400
    duplicate_count = sum(1 for item in errors if "Duplicate" in item.get("message", ""))
    invalid_count = len(errors) - duplicate_count
    return jsonify({"ok": True, "rows": rows, "count": len(rows), "valid_count": len(rows), "duplicate_count": duplicate_count, "invalid_count": invalid_count, "errors": errors[:25]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
