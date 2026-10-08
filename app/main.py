import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from app.core.config import settings
from app.core.errors import GeospatialAPIException
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("geospatial_api")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# 🌍 Geospatial File Measurement API

Production-ready backend API that accepts Shapefiles (.zip) and KML files,
extracts geospatial features, handles Coordinate Reference Systems (CRS) appropriately,
and computes accurate metric measurements for features:

- 📐 **Polygons & MultiPolygons**: Area (m², hectares, km², acres) and perimeter
- 📏 **LineStrings & MultiLineStrings**: Length (meters, kilometers)
- 📍 **Points & MultiPoints**: Gracefully recognized with measurement-not-applicable indicator
- 🌐 **Automated CRS Projection**: Automatically transforms geographic coordinates (e.g. EPSG:4326 degrees) to optimal local UTM metric projections before calculating Euclidean measurements.
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(GeospatialAPIException)
async def geospatial_exception_handler(request: Request, exc: GeospatialAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.message}
    )


# Include API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def interactive_dashboard():
    """
    Interactive web UI for testing file uploads and viewing instant measurements.
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Geospatial File Measurement API</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 46, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --accent: #10b981;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --danger: #ef4444;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background-image: radial-gradient(circle at 15% 50%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.08) 0%, transparent 40%);
    }
    header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      backdrop-filter: blur(12px);
    }
    .logo { display: flex; align-items: center; gap: 0.75rem; font-size: 1.25rem; font-weight: 700; }
    .badge {
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .nav-links a {
      color: var(--text-muted);
      text-decoration: none;
      margin-left: 1.5rem;
      font-size: 0.9rem;
      transition: color 0.2s;
    }
    .nav-links a:hover { color: var(--primary); }
    main {
      flex: 1;
      max-width: 1100px;
      margin: 2rem auto;
      padding: 0 1.5rem;
      width: 100%;
    }
    .hero { text-align: center; margin-bottom: 2.5rem; }
    .hero h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #fff 40%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { color: var(--text-muted); font-size: 1.05rem; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 2rem; }
    @media(min-width: 768px) { .grid { grid-template-columns: 400px 1fr; } }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 1rem;
      padding: 1.75rem;
      backdrop-filter: blur(16px);
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }
    .card h2 { font-size: 1.2rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
    .upload-box {
      border: 2px dashed rgba(56, 189, 248, 0.3);
      border-radius: 0.75rem;
      padding: 2rem 1.5rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      background: rgba(56, 189, 248, 0.02);
    }
    .upload-box:hover, .upload-box.dragover {
      border-color: var(--primary);
      background: rgba(56, 189, 248, 0.06);
    }
    .btn {
      width: 100%;
      background: linear-gradient(135deg, var(--primary), var(--primary-hover));
      color: #0b0f19;
      font-weight: 700;
      padding: 0.75rem 1rem;
      border: none;
      border-radius: 0.5rem;
      margin-top: 1rem;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .code-box {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      background: #06090e;
      padding: 1rem;
      border-radius: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.05);
      overflow-x: auto;
      max-height: 480px;
    }
    .summary-card {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1rem;
    }
    .metric {
      background: rgba(255, 255, 255, 0.03);
      padding: 0.75rem;
      border-radius: 0.5rem;
      border: 1px solid var(--card-border);
    }
    .metric-label { font-size: 0.75rem; color: var(--text-muted); }
    .metric-value { font-size: 1.1rem; font-weight: 700; color: var(--primary); margin-top: 0.2rem; }
    .status-pill {
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .status-completed { background: rgba(16, 185, 129, 0.15); color: var(--accent); }
    .status-failed { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>📐</span> Geospatial Measurement API
      <span class="badge">v1.0.0</span>
    </div>
    <div class="nav-links">
      <a href="/docs" target="_blank">Swagger OpenAPI Docs</a>
      <a href="/redoc" target="_blank">ReDoc</a>
      <a href="/health" target="_blank">Health</a>
    </div>
  </header>

  <main>
    <div class="hero">
      <h1>Geospatial File Measurement Service</h1>
      <p>Upload Shapefile (.zip) or KML (.kml) to inspect features and compute accurate metric measurements</p>
    </div>

    <div class="grid">
      <div>
        <div class="card">
          <h2>📤 Upload Geospatial File</h2>
          <div class="upload-box" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📁</div>
            <p style="font-weight: 600; margin-bottom: 0.25rem;">Click to select or drag & drop</p>
            <p style="font-size: 0.8rem; color: var(--text-muted);">Supports .zip (Shapefiles) and .kml</p>
            <input type="file" id="fileInput" accept=".zip,.kml" style="display:none" onchange="handleFileSelect(event)">
          </div>
          <p id="selectedFileName" style="font-size: 0.85rem; color: var(--primary); margin-top: 0.75rem; text-align: center;"></p>
          <button class="btn" id="uploadBtn" disabled onclick="submitUpload()">Process & Measure</button>
        </div>

        <div class="card" style="margin-top: 1.5rem;">
          <h2>📌 API Reference</h2>
          <div style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.6;">
            <p><strong>POST</strong> <code style="color:var(--primary)">/api/files/</code> - Upload .zip or .kml</p>
            <p><strong>GET</strong> <code style="color:var(--primary)">/api/files/{id}/</code> - Metadata & status</p>
            <p><strong>GET</strong> <code style="color:var(--primary)">/api/files/{id}/measurements/</code> - Metric measurements</p>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>📊 Measurement Results <span id="fileBadge"></span></h2>
        <div id="summaryContainer" style="display:none;">
          <div class="summary-card">
            <div class="metric"><div class="metric-label">Features</div><div class="metric-value" id="mFeatures">0</div></div>
            <div class="metric"><div class="metric-label">Measured</div><div class="metric-value" id="mMeasured">0</div></div>
            <div class="metric"><div class="metric-label">Total Area (ha)</div><div class="metric-value" id="mArea">0</div></div>
            <div class="metric"><div class="metric-label">Total Length (m)</div><div class="metric-value" id="mLength">0</div></div>
          </div>
        </div>
        <pre class="code-box" id="jsonOutput">// Upload a .zip or .kml file to inspect measurements here...</pre>
      </div>
    </div>
  </main>

  <script>
    let selectedFile = null;
    function handleFileSelect(e) {
      if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        document.getElementById('selectedFileName').textContent = "Selected: " + selectedFile.name;
        document.getElementById('uploadBtn').disabled = false;
      }
    }
    
    // Drag & drop
    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        selectedFile = e.dataTransfer.files[0];
        document.getElementById('selectedFileName').textContent = "Selected: " + selectedFile.name;
        document.getElementById('uploadBtn').disabled = false;
      }
    });

    async function submitUpload() {
      if (!selectedFile) return;
      const btn = document.getElementById('uploadBtn');
      const out = document.getElementById('jsonOutput');
      btn.disabled = true;
      btn.textContent = "Processing Features & CRS...";
      out.textContent = "Uploading and processing geometry features...";

      const formData = new FormData();
      formData.append("file", selectedFile);

      try {
        const res = await fetch("/api/files/", { method: "POST", body: formData });
        const data = await res.json();
        
        if (!res.ok) {
          out.textContent = JSON.stringify(data, null, 2);
          btn.disabled = false;
          btn.textContent = "Process & Measure";
          return;
        }

        // Fetch detailed measurements
        const measRes = await fetch(`/api/files/${data.id}/measurements/`);
        const measData = await measRes.json();
        out.textContent = JSON.stringify(measData, null, 2);

        // Update summary cards
        document.getElementById('summaryContainer').style.display = 'block';
        document.getElementById('mFeatures').textContent = measData.total_features;
        document.getElementById('mMeasured').textContent = measData.measured_features_count;
        document.getElementById('mArea').textContent = (measData.summary.total_area_hectares || 0).toFixed(2);
        document.getElementById('mLength').textContent = (measData.summary.total_length_meters || 0).toFixed(1);
        document.getElementById('fileBadge').innerHTML = `<span class="status-pill status-completed">${data.filename} (${data.id})</span>`;

      } catch (err) {
        out.textContent = "Error: " + err.message;
      } finally {
        btn.disabled = false;
        btn.textContent = "Process & Measure";
      }
    }
  </script>
</body>
</html>
    """


@app.get("/api", tags=["Root"])
async def api_root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "endpoints": {
            "upload_file": "POST /api/files/",
            "get_file_info": "GET /api/files/{id}/",
            "get_measurements": "GET /api/files/{id}/measurements/",
            "list_files": "GET /api/files/"
        }
    }
