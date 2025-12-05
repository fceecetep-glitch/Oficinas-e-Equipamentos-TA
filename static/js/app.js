<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>Painel Estatístico - CERTA / FCEE</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    :root {
      --gov-red: #bf1e2e;
      --gov-green: #A1C84D;
      --gov-blue: #003c6c;
      --surface: #f8fafc;
      --shadow: 0 12px 30px rgba(0,0,0,0.12);
    }

    body, html {
      margin: 0;
      padding: 0;
      height: 100%;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(180deg, #f4f7fb 0%, #eef2f7 100%);
      color: #0f172a;
      font-size: 15px;
    }

    #map {
      height: 100vh;
      width: 100%;
    }

    /* CONTÊINER DO TÍTULO ENTRE ESQUERDA E PAINEL DIREITO */
    .top-bar {
      position: absolute;
      top: 14px;
      left: 12px;
      right: calc(12px + min(460px, 28vw) + 12px);
      z-index: 1000;
      padding: 0;
      border: none;
      box-shadow: none;
      text-align: center;
      pointer-events: none;
    }

    .top-bar-inner {
      background: white;
      padding: 10px 14px;
      box-shadow: var(--shadow);
      border-radius: 14px;
      border: 1px solid #e2e8f0;
      display: inline-flex;
      flex-direction: column;
      gap: 8px;
      font-size: 14px;
      max-width: 520px;
      width: auto;
      pointer-events: auto;
    }

    .top-bar-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .brand img {
      height: 40px;
      width: auto;
      border-radius: 6px;
    }

    .title {
      text-align: center;
      font-size: 17px;
      font-weight: 700;
      line-height: 1.3;
      color: #0f172a;
      flex: 0 1 auto;
      max-width: 360px;
    }

    .title .subtitle {
      font-weight: 500;
      display: block;
      margin-top: 2px;
      line-height: 1.25;
      font-size: 13px;
    }

    #searchBox {
      padding: 6px 9px;
      border-radius: 10px;
      border: 1px solid #cbd5e1;
      width: 80%;
      max-width: 260px;
      margin: 0 auto;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
      font-size: 12px;
    }

    .demographic-panel {
      position: absolute;
      top: 14px;
      right: 12px;
      bottom: 14px;
      left: auto;
      background: rgba(255,255,255,0.96);
      padding: 14px 14px 16px;
      box-shadow: var(--shadow);
      border-radius: 14px;
      z-index: 1000;
      backdrop-filter: blur(4px);
      border: 1px solid #e2e8f0;

      width: min(520px, 32vw);
      display: flex;
      flex-direction: column;
      gap: 8px;
      overflow: hidden;
    }

    .panel-scroll {
      flex: 1;
      overflow-y: auto;
      padding-right: 4px;
    }

    .card {
      background: #f7f9fb;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 12px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
      margin-top: 6px;
    }

    .card h4 {
      margin: 0 0 6px 0;
      color: var(--gov-blue);
      font-size: 16px;
      font-weight: 700;
    }

    .card .total {
      font-size: 17px;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 8px;
    }

    canvas {
      background: white;
      border-radius: 8px;
      width: 100% !important;
      display: block;
    }

    #chartFaixa { height: 170px !important; }
    #chartTipos { height: 150px !important; }
    #chartRegiao { height: 210px !important; }

    .panel-toggle {
      position: absolute;
      right: calc(12px + min(460px, 28vw));
      bottom: 20px;
      top: auto;
      transform: none;
      z-index: 1100;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 999px 0 0 999px;
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
      box-shadow: var(--shadow);
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }

    .panel-toggle span.icon {
      font-size: 14px;
    }

    @media (max-width: 760px) {
      .top-bar {
        left: 50%;
        right: auto;
        transform: translateX(-50%);
        width: 92%;
        text-align: center;
        pointer-events: none;
      }

      .top-bar-inner {
        max-width: none;
        width: 100%;
        display: flex;
        pointer-events: auto;
      }

      .top-bar-row {
        flex-direction: row;
        gap: 10px;
      }

      .brand img {
        height: 38px;
      }

      #searchBox {
        width: 100%;
        max-width: none;
      }

      .demographic-panel {
        position: static;
        width: calc(100% - 24px);
        max-width: none;
        margin: 10px auto 0 auto;
        top: auto;
        left: auto;
        right: auto;
        bottom: auto;
        height: auto;
        overflow: visible;
      }

      .panel-scroll {
        max-height: none;
        overflow: visible;
      }

      .panel-toggle {
        top: auto;
        bottom: 10px;
        right: 10px;
        border-radius: 999px;
        transform: none;
      }
    }
  </style>
</head>
<body>
  <div id="map"></div>

  <!-- BLOCO ESQUERDO: LOGOS + TÍTULO + BUSCA -->
  <div class="top-bar">
    <div class="top-bar-inner">
      <div class="top-bar-row">
        <div class="brand">
          <img src="static/img/govsc.jpg" alt="Governo de Santa Catarina">
        </div>
        <div class="title">
          <span>Painel Estatístico</span>
          <span class="subtitle">Fundação Catarinense de Educação Especial</span>
          <span class="subtitle">Capacitações e Recursos</span>
        </div>
        <div class="brand">
          <img src="static/img/fcee.jpg" alt="FCEE">
        </div>
      </div>
      <div style="margin-top:4px;">
        <input type="text" id="searchBox" placeholder="Buscar município...">
      </div>
    </div>
  </div>

  <!-- Botão para esconder/mostrar o painel -->
  <button id="togglePanel" class="panel-toggle">
    <span class="icon">⯈</span>
    <span class="label">Esconder painel</span>
  </button>

  <!-- PAINEL ÚNICO À DIREITA -->
  <div class="demographic-panel" id="demographicPanel">
    <div class="panel-scroll">
      <div class="card">
        <h4>Capacitações e recursos por faixa etária</h4>
        <canvas id="chartFaixa"></canvas>
      </div>

      <div class="card">
        <h4>Capacitações e recursos por tipo de deficiência</h4>
        <div class="total" id="totalTipos">Total: -</div>
        <canvas id="chartTipos"></canvas>
      </div>

      <div class="card">
        <h4>Capacitações e recursos por região de SC</h4>
        <canvas id="chartRegiao"></canvas>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>
  <script src="static/js/app.js"></script>

  <script>
    (function() {
      const panel = document.getElementById('demographicPanel');
      const btn = document.getElementById('togglePanel');
      const icon = btn.querySelector('.icon');
      const label = btn.querySelector('.label');

      btn.addEventListener('click', () => {
        const isHidden = panel.style.display === 'none';

        if (isHidden) {
          panel.style.display = '';
          icon.textContent = '⯈';
          label.textContent = 'Esconder painel';
        } else {
          panel.style.display = 'none';
          icon.textContent = '⯇';
          label.textContent = 'Mostrar painel';
        }
      });
    })();
  </script>
</body>
</html>
