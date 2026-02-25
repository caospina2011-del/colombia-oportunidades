# Sistema de Monitoreo de Licitaciones - Colombia

Sistema automatizado para monitoreo de oportunidades de contratación pública en Colombia usando la API de datos.gov.co (Colombia Compra Eficiente).

## Características

- 🔍 **Filtrado inteligente**: Presupuestos entre 150M - 800M COP
- 📊 **Scoring automático**: Evaluación 0-100 basada en perfil de empresa
- 📧 **Reporte por email**: HTML semanal con prioridades
- ⚡ **Bajo consumo**: Filtros duros antes de análisis semántico
- 🔄 **Ejecución automática**: GitHub Actions los lunes 8 AM

## Perfil de Empresa

El sistema está configurado para **SD Soluciones Integrales de Ingeniería S.A.S.**

### Líneas de negocio principales:
- Media Tensión (prioridad 100%)
- Electricidad Industrial (95%)
- Mantenimiento Industrial (90%)
- Construcción (85%)
- Aire Acondicionado y Extracción (80%)
- Redes y Telecomunicaciones (75%)

### Rangos de interés:
- **Presupuesto ideal**: $300M - $500M COP
- **Flexibilidad**: ±20%
- **Geografía**: Bogotá D.C., Cundinamarca, Nacional

## Configuración

### Secrets de GitHub (requeridos)

1. Ve a Settings → Secrets and variables → Actions
2. Agrega estos secrets:

| Secret | Descripción |
|--------|-------------|
| `EMAIL_PASSWORD` | Contraseña de aplicación de Gmail (16 caracteres) |
| `REPORT_EMAIL` | Correo destino del reporte |

### Cómo obtener contraseña de aplicación Gmail

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. Seguridad → Verificación en 2 pasos (activar si no lo está)
3. Seguridad → Contraseñas de aplicación
4. Selecciona "Correo" → "Otro (nombre personalizado)"
5. Escribe: "Colombia Oportunidades"
6. Copia la contraseña de 16 caracteres

## Estructura del Proyecto

```
colombia-oportunidades/
├── .github/
│   └── workflows/
│       └── weekly-monitor.yml    # Configuración GitHub Actions
├── config/
│   ├── company_profile.json       # Perfil de tu empresa
│   └── scoring_config.json        # Configuración de scoring
├── src/
│   └── monitor.py                 # Script principal
├── data/
│   └── reporte_YYYYMMDD.html      # Reportes generados
└── README.md
```

## Cómo funciona el Scoring

El sistema evalúa cada oportunidad en estos factores:

| Factor | Peso | Descripción |
|--------|------|-------------|
| Afinidad técnica | 30% | Keywords en objeto del proceso |
| Presupuesto | 20% | Alineación con rangos ideales |
| Geografía | 10% | Ubicación del proyecto |
| Modalidad | 10% | Tipo de contratación |
| Entidad | 10% | Tipo de contratante |
| Complejidad | 10% | Nivel técnico estimado |
| Competencia | 5% | Riesgo de competencia |
| Timeline | 5% | Viabilidad de ejecución |

### Clasificación de prioridad:
- 🟢 **Alta**: Score ≥ 75
- 🟡 **Media**: Score 55-74
- 🔴 **Baja**: Score < 55

## API Utilizada

- **Fuente**: datos.gov.co (Colombia Compra Eficiente)
- **Dataset**: SECOP II - Procesos de Contratación
- **Endpoint**: Socrata Open Data API
- **Filtros**: Procesos activos, presupuesto 150M-800M COP

## Ejecución Manual

Puedes ejecutar el workflow manualmente desde GitHub:
1. Ve a Actions → "Monitoreo de Licitaciones Semanal"
2. Click en "Run workflow"
3. Selecciona branch "main"
4. Click en "Run workflow"

## Personalización

Para adaptar el sistema a otra empresa:

1. Modifica `config/company_profile.json` con tu información
2. Ajusta `config/scoring_config.json` según tus prioridades
3. Actualiza los secrets de GitHub con tu correo

## Limitaciones

- Máximo 20 oportunidades por ejecución (configurable)
- API datos.gov.co tiene rate limits (manejado con paginación)
- Scoring basado en análisis de texto, no en pliegos completos

## Soporte

Para reportar problemas o sugerir mejoras, abre un issue en el repositorio.

---
**Nota**: Este es un MVP. Validado el valor comercial, se puede escalar frecuencia, profundidad de análisis o integraciones adicionales.