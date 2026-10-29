# 🏛️ CTT - FISEI UTA: Agente de IA y Dashboard de Ventas

Sistema integral desarrollado para el **Centro de Capacitación Tecnológica en Capacitación y Soporte (CTT - FISEI)** de la **Facultad de Ingeniería en Sistemas, Electrónica e Industrial de la Universidad Técnica de Ambato (UTA)**.

El sistema combina:
1. **Agente de IA Consultor y Prospector de Ventas**: Opera vía **Telegram Bot** y mediante un **Simulador Interactivo Web**, respondiendo consultas académicas, identificando si el usuario es Estudiante UTA, Graduado o Público General para otorgar descuentos, detectando clientes con alta intención de compra (**"A Punto de Inscribirse" / Hot Leads**) y guiándolos al cierre de matrícula.
2. **Dashboard de Resultados y CRM de Admisiones**: Interfaz web moderna con estética dark-mode premium, glassmorphism, métricas en tiempo real, embudo de conversión, catálogo de cursos sincronizado directamente con [ctt-talleresfisei.uta.edu.ec](https://ctt-talleresfisei.uta.edu.ec/course.php) y validador de certificados digitales con código QR oficial.

---

## 🎯 Entregables a Evaluar

### 1. URL del Dashboard Generado (Localmente)
- **URL Principal:** [http://localhost:8000/](http://localhost:8000/)
- **Documentación Interactiva Swagger / OpenAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Estado del Servidor:** En ejecución activo en `http://localhost:8000`.

### 2. Bot de Telegram
El bot de Telegram está implementado con `python-telegram-bot` (v20+ async) en [`backend/telegram_bot.py`](backend/telegram_bot.py):
- **Comandos Principales:**
  - `/start`: Menú interactivo con Inline Keyboards para cursos, precios, temarios y validación.
  - `/cursos`: Lista interactiva de programas abiertos con carga horaria y modalidades.
  - `/precios`: Comparativa de aranceles institucionales (Estudiantes UTA con subsidio vs Público).
  - `/certificado <código>`: Consulta y validación inmediata de certificados oficiales con QR.
  - `/inscribirme`: Formulario oficial de matrícula institucional.
- **Configuración Rápida del Bot:**
  - Puedes ingresar tu `TELEGRAM_BOT_TOKEN` (obtenido de `@BotFather`) directamente en el archivo `.env` o desde la pestaña **"Configuración & Bot"** del Dashboard en el navegador con un solo clic.
- **Simulador Incorporado:**
  - En la esquina superior derecha del Dashboard haz clic en **"Probar Agente IA"** para abrir el teléfono Telegram simulado y probar la IA en tiempo real sin necesidad de configurar un token externo.

---

## 🏗️ Arquitectura de la Solución

```
Hackathon_2026/
├── backend/
│   ├── app.py                # Servidor FastAPI (REST API, WebSockets, archivos estáticos)
│   ├── database.py           # Base de datos SQLite (leads, chats, cursos, certificados)
│   ├── llm_agent.py          # Motor de IA: Análisis de intención, scoring y prospección
│   ├── telegram_bot.py       # Servicio del Bot de Telegram (Polling, Inline Keyboards)
│   └── seed_data.py          # Inicializador de cursos reales CTT-FISEI y prospectos demo
├── static/
│   ├── index.html            # Dashboard SPA responsive
│   ├── css/
│   │   └── dashboard.css     # Sistema de diseño (Dark Mode, Glassmorphism, Paleta UTA)
│   └── js/
│       ├── app.js            # Lógica central del Dashboard y CRM
│       ├── charts.js         # Gráficas analíticas interactivas (Chart.js)
│       └── simulator.js      # Cliente de prueba de Telegram dentro del navegador
├── tests/
│   ├── test_agent.py         # Pruebas unitarias de intención, scoring y cursos
│   ├── test_api.py           # Pruebas de integración de endpoints REST
│   └── test_telegram.py      # Pruebas del bot de Telegram
├── courses_catalog.json      # Catálogo extraído de ctt-talleresfisei.uta.edu.ec
├── scraper.py                # Extractor de datos en vivo de la UTA
├── run_server.py             # Lanzador unificado del servidor y base de datos
├── requirements.txt          # Dependencias Python
└── README.md                 # Documentación técnica
```

---

## 🚀 Puesta en Marcha

### Prerrequisitos
- Python 3.10+ (probado en Python 3.13)
- Navegador web moderno (Chrome, Edge, Firefox)

### 1. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 2. Iniciar el Servidor y Dashboard
```bash
python run_server.py
```
El servidor inicializará automáticamente la base de datos con los 18 cursos de CTT FISEI, certificados y prospectos de ejemplo, arrancando en `http://localhost:8000/`.

### 3. Ejecutar la Batería de Pruebas Automatizadas
```bash
python tests/test_agent.py
python tests/test_api.py
python tests/test_telegram.py
```
*Todas las pruebas se ejecutan con resultado OK.*

---

## 💡 Características Clave Desarrolladas

### 1. Centro de Cierre Rápido de Ventas ("Hot Leads")
- Detecta automáticamente cuando un usuario consulta por datos bancarios, pide el link de inscripción o manifiesta urgencia por inscribirse.
- Asigna un **Intent Score de 80% a 100%** y clasifica al prospecto como **`A PUNTO DE INSCRIBIRSE`**.
- El organizador tiene botones de acción inmediata:
  - 💬 **Chat Telegram Directo**: Enlace hacia `@username` del cliente.
  - 📱 **Chat WhatsApp Rápido**: Redirige a WhatsApp con mensaje de bienvenida prellenado.
  - ✍️ **Cerrar Venta / Marcar Inscrito**: Actualiza el embudo de ventas al instante.
  - 📝 **Notas de Cierre**: Espacio para registrar comprobantes bancarios, facturación o acuerdos.

### 2. Catálogo Oficial Sincronizado
- Información fiel obtenida directamente desde `https://ctt-talleresfisei.uta.edu.ec/course.php`:
  - **GitHub Certified: Agentic AI Developer (GH-600)** (32 horas, Zoom virtual)
  - **CCNA: Introducción a las redes Cisco** (70 horas, Híbrido en Talleres FISEI Campus Huachi)
  - **Preparación Linux Essentials**
  - **Fundamentos de Python 1 y 2**
  - **Certificación Arduino & Automatización**
  - **IA para Recursos Humanos**, entre otros.
- Diferenciación clara de tarifas:
  - Estudiantes UTA: *$40,00 - $120,00* (Subsidio universitario)
  - Graduados y Docentes UTA: *$50,00 - $150,00*
  - Público en General: *$60,00 - $180,00*

### 3. Verificación de Certificados Digitales
- Soporte para verificar códigos oficiales emitidos por el CTT FISEI (ejemplo de prueba: `UTA-CTT-2026-9041` a nombre de *Carlos Andrés Morales Ortiz*).
- Muestra cédula, horas académicas, nota de aprobación y enlace directo a la plataforma educativa de la UTA: `https://ctt-talleresfisei.uta.edu.ec/edu/mod/customcert/verify_certificate.php`.

### 4. Inteligencia Artificial Híbrida
- **Motor Experto CTT FISEI (Autónomo)**: Reconocimiento semántico de intenciones, extracción de teléfonos ecuatorianos, categorización de perfil y cálculo de probabilidad de cierre sin depender obligatoriamente de conexión a internet o saldo de API.
- **Soporte Gemini / OpenAI**: Si se suministra una `GEMINI_API_KEY` en el archivo `.env` o en la sección de Configuración, el sistema enriquece automáticamente las respuestas con el modelo generativo de Google Gemini.

---

## 📊 Métricas y KPIs en Vivo
- **Total Prospectos:** Contador consolidado de contactos registrados.
- **A Punto de Inscribirse:** Alerta visual destacada con badge rojo brillante.
- **Tasa de Conversión:** Porcentaje de alumnos efectivamente inscritos sobre el total de prospectos.
- **Interacciones Totales:** Volumen de mensajes procesados por el agente de IA.
- **Gráficas Chart.js:**
  - Cursos con mayor demanda de inscripción.
  - Embudo de conversión y distribución por tipo de público.
